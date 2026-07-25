from __future__ import annotations

import hashlib
import json
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

SUPPORTED_IMPORT_SUFFIXES = {".json", ".jsonl", ".txt"}
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
    raise ValueError("Only .json, .jsonl and .txt files are supported")


def iter_import_rows(
    filename: str,
    path: Path,
) -> Iterator[tuple[int, object | None, str | None]]:
    """Yield ``(row_number, value, error)`` tuples from an import file.

    JSONL is parsed line by line so a dataset containing 100k-token requests
    does not need to fit in process memory. JSON and TXT may contain a single
    pretty-printed object or an array and are intended for smaller samples.
    """

    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_IMPORT_SUFFIXES:
        raise ValueError("Only .json, .jsonl and .txt files are supported")

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

    content = path.read_bytes()
    rows = parse_import_rows(filename, content)
    for row_number, row in enumerate(rows, start=1):
        yield row_number, row, None


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

