from __future__ import annotations

import json
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


def parse_import_rows(filename: str, content: bytes) -> list[object]:
    text = content.decode("utf-8-sig")
    suffix = Path(filename).suffix.lower()
    if suffix == ".json":
        payload = json.loads(text)
        if not isinstance(payload, list):
            raise ValueError("JSON import must contain an array of events")
        return payload
    if suffix == ".jsonl":
        return [
            json.loads(line)
            for line in text.splitlines()
            if line.strip()
        ]
    raise ValueError("Only .json and .jsonl files are supported")


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
) -> None:
    async with async_session_factory() as session:
        job = await session.get(ImportJob, import_id)
        if job is None:
            return
        job.status = ImportStatus.PROCESSING.value
        await session.commit()

        try:
            rows = parse_import_rows(filename, content)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            job.status = ImportStatus.FAILED.value
            job.error_log = [{"row": None, "detail": str(exc)}]
            job.finished_at = datetime.now(UTC)
            await session.commit()
            return

        job.total_rows = len(rows)
        await session.commit()

        errors: list[dict[str, object]] = []
        processed = 0
        for row_number, row in enumerate(rows, start=1):
            try:
                event_data = EventCreate.model_validate(row)
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

