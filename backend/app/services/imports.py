from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.entities import AnalysisRun, ImportJob
from app.models.enums import AnalysisRunStatus, ImportStatus
from app.schemas.events import EventCreate
from app.services.events import create_event

SUPPORTED_IMPORT_SUFFIXES = {".json", ".jsonl", ".txt", ".csv"}
CSV_FIELD_SIZE_LIMIT = 64 * 1024 * 1024
_EVENT_METADATA_KEYS = {
    "external_id",
    "agent_id",
    "user_id",
    "team",
    "direction",
    "is_synthetic",
    "occurred_at",
    "response",
    "execution_status",
    "latency_ms",
    "rating",
    "task_completed",
    "estimated_minutes_saved",
}
_CSV_QUERY_COLUMNS = (
    "user_query",
    "query",
    "question",
    "prompt",
    "request_text",
    "user_message",
    "text",
    "content",
)
_CSV_RESPONSE_COLUMNS = (
    "response",
    "agent_answer",
    "answer",
    "response_text",
    "assistant_answer",
)
_CSV_BOOLEAN_COLUMNS = ("is_synthetic", "task_completed")
_CSV_USAGE_COLUMNS = ("prompt_tokens", "completion_tokens", "total_tokens")
_CSV_COLUMN_ALIASES = {
    "id": "external_id",
    "agent": "agent_id",
    "user": "user_id",
    "timestamp": "occurred_at",
    "date": "occurred_at",
    "created_at": "occurred_at",
    "status": "execution_status",
    "запрос": "user_query",
    "вопрос": "user_query",
    "текст_запроса": "user_query",
    "ответ": "agent_answer",
    "текст_ответа": "agent_answer",
    "агент": "agent_id",
    "пользователь": "user_id",
    "команда": "team",
    "направление": "direction",
    "дата": "occurred_at",
    "статус": "execution_status",
}


def _rows_from_json_payload(payload: object) -> list[object]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return [payload]
    raise ValueError("JSON import must contain an event object or an array of events")


def parse_import_rows(filename: str, content: bytes) -> list[object]:
    """Parse an in-memory import.

    This helper is kept for small files and unit tests. Production JSONL
    imports use :func:`iter_import_rows` and never load the whole file.
    """

    text = content.decode("utf-8-sig")
    suffix = Path(filename).suffix.lower()
    if suffix in {".json", ".txt"}:
        try:
            return _rows_from_json_payload(json.loads(text))
        except json.JSONDecodeError:
            if suffix != ".txt":
                raise
            return [
                json.loads(line)
                for line in text.splitlines()
                if line.strip()
            ]
    if suffix == ".jsonl":
        return [
            json.loads(line)
            for line in text.splitlines()
            if line.strip()
        ]
    if suffix == ".csv":
        source = io.StringIO(text, newline="")
        return [
            normalize_csv_row(row)
            for row in _iter_csv_rows(source)
        ]
    raise ValueError("Only .json, .jsonl, .txt and .csv files are supported")


def iter_import_rows(
    filename: str,
    path: Path,
) -> Iterator[tuple[int, object | None, str | None]]:
    """Yield ``(row_number, value, error)`` tuples from an import file.

    JSONL and CSV are parsed row by row so a dataset containing 100k-token
    requests does not need to fit in process memory. JSON and TXT may contain a
    single pretty-printed object or an array and are intended for smaller
    samples.
    """

    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_IMPORT_SUFFIXES:
        raise ValueError(
            "Only .json, .jsonl, .txt and .csv files are supported"
        )

    if suffix == ".jsonl":
        with path.open("r", encoding="utf-8-sig") as source:
            logical_row = 0
            for physical_line, line in enumerate(source, start=1):
                if not line.strip():
                    continue
                logical_row += 1
                try:
                    yield logical_row, json.loads(line), None
                except json.JSONDecodeError as exc:
                    yield logical_row, None, (
                        f"Invalid JSON on physical line {physical_line}: {exc}"
                    )
        return

    if suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as source:
            for row_number, row in enumerate(
                _iter_csv_rows(source),
                start=1,
            ):
                try:
                    yield row_number, normalize_csv_row(row), None
                except (TypeError, ValueError) as exc:
                    yield row_number, None, str(exc)
        return

    content = path.read_bytes()
    rows = parse_import_rows(filename, content)
    for row_number, row in enumerate(rows, start=1):
        yield row_number, row, None


def _iter_csv_rows(source) -> Iterator[dict[str, str]]:
    csv.field_size_limit(CSV_FIELD_SIZE_LIMIT)
    sample = source.read(32 * 1024)
    source.seek(0)
    if not sample.strip():
        raise ValueError("CSV import is empty")
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel

    reader = csv.DictReader(source, dialect=dialect)
    if not reader.fieldnames:
        raise ValueError("CSV import must contain a header row")
    normalized_headers = [
        _normalize_csv_header(header or "")
        for header in reader.fieldnames
    ]
    if not any(normalized_headers):
        raise ValueError("CSV import must contain named columns")
    if len(set(normalized_headers)) != len(normalized_headers):
        raise ValueError("CSV import contains duplicate column names")

    for row in reader:
        clean = {
            _normalize_csv_header(str(key)): value.strip()
            for key, value in row.items()
            if key is not None
            and value is not None
            and value.strip() != ""
        }
        if not clean:
            continue
        yield clean


def normalize_csv_row(row: dict[str, str]) -> dict[str, object]:
    """Convert a flat CSV row into the canonical event structure."""

    normalized: dict[str, object] = {}
    for key in (
        "external_id",
        "agent_id",
        "user_id",
        "team",
        "direction",
        "occurred_at",
        "execution_status",
        "latency_ms",
        "rating",
        "estimated_minutes_saved",
    ):
        if key in row:
            normalized[key] = row[key]
    for key in _CSV_BOOLEAN_COLUMNS:
        if key in row:
            normalized[key] = _parse_csv_bool(row[key], column=key)

    request_value = row.get("request")
    messages_value = row.get("messages")
    query_value = _first_csv_value(row, _CSV_QUERY_COLUMNS)
    if request_value:
        parsed_request = _parse_optional_json(request_value, column="request")
        if isinstance(parsed_request, dict):
            request = parsed_request
        elif parsed_request is not None:
            raise ValueError("CSV column request must contain a JSON object")
        else:
            request = {
                "messages": [{"role": "user", "content": request_value}]
            }
    elif messages_value:
        messages = _parse_required_json(messages_value, column="messages")
        if not isinstance(messages, list):
            raise ValueError("CSV column messages must contain a JSON array")
        request = {"messages": messages}
    elif query_value:
        request = {
            "messages": [{"role": "user", "content": query_value}]
        }
    else:
        raise ValueError(
            "CSV row must contain request, messages, user_query, query, "
            "question, prompt, request_text, user_message, text or content"
        )

    if "model" in row and "model" not in request:
        request["model"] = row["model"]
    if "stream" in row and "stream" not in request:
        request["stream"] = _parse_csv_bool(row["stream"], column="stream")
    normalized["request"] = request

    response_value = _first_csv_value(row, _CSV_RESPONSE_COLUMNS)
    response: dict[str, object] | None = None
    if response_value:
        parsed_response = _parse_optional_json(
            response_value,
            column="response",
        )
        if isinstance(parsed_response, dict):
            response = parsed_response
        elif parsed_response is not None:
            raise ValueError("CSV response must be text or a JSON object")
        else:
            response = {"content": response_value}

    usage = {
        key: int(row[key])
        for key in _CSV_USAGE_COLUMNS
        if key in row
    }
    if usage:
        response = response or {"content": None}
        existing_usage = response.get("usage")
        if isinstance(existing_usage, dict):
            response["usage"] = {**existing_usage, **usage}
        else:
            response["usage"] = usage
    if response is not None:
        normalized["response"] = response
    return normalized


def _first_csv_value(
    row: dict[str, str],
    columns: tuple[str, ...],
) -> str | None:
    return next((row[column] for column in columns if row.get(column)), None)


def _parse_optional_json(value: str, *, column: str) -> object | None:
    stripped = value.strip()
    if not stripped.startswith(("{", "[")):
        return None
    return _parse_required_json(stripped, column=column)


def _parse_required_json(value: str, *, column: str) -> object:
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"CSV column {column} contains invalid JSON: {exc}"
        ) from exc


def _parse_csv_bool(value: str, *, column: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "y", "да"}:
        return True
    if normalized in {"false", "0", "no", "n", "нет"}:
        return False
    raise ValueError(
        f"CSV column {column} must be true/false, 1/0, yes/no or да/нет"
    )


def _normalize_csv_header(value: str) -> str:
    normalized = re.sub(r"[\s-]+", "_", value.strip().lower())
    return _CSV_COLUMN_ALIASES.get(normalized, normalized)


def normalize_import_row(
    row: object,
    *,
    filename: str,
    row_number: int,
    default_agent_id: str,
) -> dict[str, object]:
    """Convert canonical events and raw OpenAI requests to ``EventCreate``."""

    if not isinstance(row, dict):
        raise TypeError("Import row must be a JSON object")

    normalized = dict(row)
    if "request" not in normalized:
        if "messages" not in normalized:
            raise ValueError(
                "Import row must contain either request.messages or top-level messages"
            )
        request = {
            key: value
            for key, value in normalized.items()
            if key not in _EVENT_METADATA_KEYS
        }
        normalized = {
            key: value
            for key, value in normalized.items()
            if key in _EVENT_METADATA_KEYS
        }
        normalized["request"] = request

    canonical = json.dumps(
        row,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    digest = hashlib.sha256(
        f"{filename}:{row_number}:{canonical}".encode("utf-8")
    ).hexdigest()[:32]
    normalized.setdefault("external_id", f"import-{digest}")
    normalized.setdefault("agent_id", default_agent_id)
    return normalized


async def create_import_job(
    session: AsyncSession,
    *,
    filename: str,
) -> ImportJob:
    job = ImportJob(
        filename=filename,
        status=ImportStatus.PENDING.value,
        error_log=[],
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


async def process_import(
    import_id: UUID,
    filename: str,
    content: bytes,
    default_agent_id: str = "imported-agent",
) -> None:
    """Backward-compatible in-memory entry point used by older callers."""

    import tempfile

    suffix = Path(filename).suffix.lower()
    with tempfile.NamedTemporaryFile(
        mode="wb",
        suffix=suffix,
        prefix="analytics-compat-",
        delete=False,
    ) as staged:
        staged.write(content)
        staged_path = Path(staged.name)
    await process_import_file(
        import_id,
        filename,
        staged_path,
        default_agent_id,
    )


async def process_import_file(
    import_id: UUID,
    filename: str,
    staged_path: Path,
    default_agent_id: str = "imported-agent",
) -> None:
    async with async_session_factory() as session:
        try:
            job = await session.get(ImportJob, import_id)
            if job is None:
                return
            job.status = ImportStatus.PROCESSING.value
            await session.commit()

            errors: list[dict[str, object]] = []
            processed = 0
            total = 0
            for row_number, row, parse_error in iter_import_rows(
                filename,
                staged_path,
            ):
                total += 1
                if parse_error is not None:
                    errors.append({"row": row_number, "detail": parse_error})
                    continue
                try:
                    normalized = normalize_import_row(
                        row,
                        filename=filename,
                        row_number=row_number,
                        default_agent_id=default_agent_id,
                    )
                    event_data = EventCreate.model_validate(normalized)
                    await create_event(
                        session,
                        event_data,
                        import_id=import_id,
                    )
                    processed += 1
                except (ValidationError, TypeError, ValueError) as exc:
                    errors.append(
                        {
                            "row": row_number,
                            "detail": str(exc),
                        }
                    )

            job = await session.get(ImportJob, import_id)
            if job is None:
                return
            job.total_rows = total
            job.processed_rows = processed
            job.failed_rows = len(errors)
            job.error_log = errors
            job.status = ImportStatus.COMPLETED.value
            job.finished_at = datetime.now(UTC)

            run = AnalysisRun(
                trigger_import_id=import_id,
                status=AnalysisRunStatus.PENDING.value,
                algorithm_version="tfidf-agg-v1",
            )
            session.add(run)
            await session.commit()
        except Exception as exc:
            await session.rollback()
            job = await session.get(ImportJob, import_id)
            if job is not None:
                job.status = ImportStatus.FAILED.value
                job.error_log = [
                    {
                        "row": None,
                        "detail": f"{type(exc).__name__}: {str(exc)}",
                    }
                ]
                job.finished_at = datetime.now(UTC)
                await session.commit()
        finally:
            staged_path.unlink(missing_ok=True)

