from pathlib import Path
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models.entities import ImportJob
from app.schemas.imports import ImportAccepted, ImportStatusResponse
from app.services.imports import create_import_job, process_import

router = APIRouter(prefix="/imports", tags=["imports"])

MAX_IMPORT_BYTES = 50 * 1024 * 1024


@router.post(
    "",
    response_model=ImportAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_import(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db_session),
) -> ImportAccepted:
    filename = file.filename or "events.jsonl"
    if Path(filename).suffix.lower() not in {".json", ".jsonl"}:
        raise HTTPException(
            status_code=415,
            detail="Only .json and .jsonl files are supported",
        )
    content = await file.read(MAX_IMPORT_BYTES + 1)
    if len(content) > MAX_IMPORT_BYTES:
        raise HTTPException(status_code=413, detail="Import file is too large")

    job = await create_import_job(session, filename=filename)
    background_tasks.add_task(process_import, job.id, filename, content)
    return ImportAccepted(id=job.id, status=job.status)


@router.get("/{import_id}", response_model=ImportStatusResponse)
async def get_import(
    import_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> ImportStatusResponse:
    job = await session.get(ImportJob, import_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Import not found")
    return ImportStatusResponse(
        id=job.id,
        filename=job.filename,
        status=job.status,
        total_rows=job.total_rows,
        processed_rows=job.processed_rows,
        failed_rows=job.failed_rows,
        errors=job.error_log,
    )

