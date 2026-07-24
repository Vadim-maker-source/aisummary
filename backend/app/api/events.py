from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models.enums import AnalysisStatus, Category
from app.repositories.events import get_event_view
from app.schemas.events import (
    EventAccepted,
    EventCreate,
    EventDetail,
    EventListResponse,
)
from app.services import events as event_service

router = APIRouter(prefix="/events", tags=["events"])


@router.post(
    "",
    response_model=EventAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_event(
    payload: EventCreate,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
) -> EventAccepted:
    result, duplicate = await event_service.create_event(session, payload)
    if duplicate:
        response.status_code = status.HTTP_200_OK
    return result


@router.get("", response_model=EventListResponse)
async def list_events(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    category: Category | None = None,
    scenario_id: UUID | None = None,
    analysis_status: AnalysisStatus | None = None,
    has_query_problem: bool | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> EventListResponse:
    return await event_service.list_events(
        session,
        page=page,
        page_size=page_size,
        category=category.value if category else None,
        scenario_id=scenario_id,
        analysis_status=analysis_status.value if analysis_status else None,
        has_query_problem=has_query_problem,
    )


@router.get("/{event_id}", response_model=EventDetail)
async def get_event(
    event_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> EventDetail:
    view = await get_event_view(session, event_id)
    if view is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event_service.to_event_detail(view)

