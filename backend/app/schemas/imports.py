from uuid import UUID

from pydantic import BaseModel

from app.models.enums import ImportStatus


class ImportAccepted(BaseModel):
    id: UUID
    status: ImportStatus


class ImportStatusResponse(BaseModel):
    id: UUID
    filename: str
    status: ImportStatus
    total_rows: int
    processed_rows: int
    failed_rows: int
    errors: list[dict[str, object]]

