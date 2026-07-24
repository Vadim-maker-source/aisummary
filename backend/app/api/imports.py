import tempfile
from pathlib import Path
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models.entities import ImportJob
from app.schemas.imports import ImportAccepted, ImportStatusResponse
from app.services.imports import create_import_job, process_import_file

router = APIRouter(prefix="/imports", tags=["imports"])

SUPPORTED_IMPORT_SUFFIXES = {".json", ".jsonl", ".txt"}
MAX_IMPORT_BYTES = 512 * 1024 * 1024
UPLOAD_CHUNK_BYTES = 1024 * 1024


@router.post(
    "",
    response_model=ImportAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_import(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    agent_id: str = Form(default="imported-agent", min_length=1, max_length=255),
    session: AsyncSession = Depends(get_db_session),
) -> ImportAccepted:
    filename = file.filename or "events.jsonl"
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_IMPORT_SUFFIXES:
        raise HTTPException(
            status_code=415,
            detail="Only .json, .jsonl and .txt files are supported",
        )
    agent_id = agent_id.strip()
    if not agent_id:
        raise HTTPException(status_code=422, detail="agent_id must not be blank")

    staging_dir = Path(tempfile.gettempdir()) / "ai-agent-analytics-imports"
    staging_dir.mkdir(parents=True, exist_ok=True)
    staged_path: Path | None = None
    total_bytes = 0
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            suffix=suffix,
            prefix="analytics-",
            dir=staging_dir,
            delete=False,
        ) as staged:
            staged_path = Path(staged.name)
            while chunk := await file.read(UPLOAD_CHUNK_BYTES):
                total_bytes += len(chunk)
                if total_bytes > MAX_IMPORT_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail="Import file is too large (maximum 512 MB)",
                    )
                staged.write(chunk)
    except Exception:
        if staged_path is not None:
            staged_path.unlink(missing_ok=True)
        raise
    finally:
        await file.close()

    if total_bytes == 0:
        staged_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Import file is empty")

    job = await create_import_job(session, filename=filename)
    background_tasks.add_task(
        process_import_file,
        job.id,
        filename,
        staged_path,
        agent_id,
    )
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

