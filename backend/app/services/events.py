from __future__ import annotations

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import AgentEvent
from app.models.enums import AnalysisStatus
from app.repositories import events as event_repository
from app.repositories.events import EventView
from app.schemas.events import (
    EventAccepted,
    EventCreate,
    EventDetail,
    EventListItem,
    EventListResponse,
    ScenarioReference,
)


async def create_event(
    session: AsyncSession,
    data: EventCreate,
    *,
    import_id: UUID | None = None,
) -> tuple[EventAccepted, bool]:
    existing = await event_repository.find_by_external_key(
        session,
        agent_id=data.agent_id,
        external_id=data.external_id,
    )
    if existing is not None:
        return (
            EventAccepted(
                id=existing.id,
                duplicate=True,
                analysis_status=AnalysisStatus(existing.analysis_status),
            ),
            True,
        )

    usage = data.response.usage if data.response else None
    event = AgentEvent(
        external_id=data.external_id,
        agent_id=data.agent_id,
        user_id=data.user_id,
        team=data.team,
        direction=data.direction,
        is_synthetic=data.is_synthetic,
        import_id=import_id,
        model=data.request.model,
        stream=data.request.stream,
        raw_request=data.request.model_dump(mode="json"),
        raw_response=(
            data.response.model_dump(mode="json") if data.response else None
        ),
        agent_answer=data.response.content if data.response else None,
        execution_status=data.execution_status.value,
        latency_ms=data.latency_ms,
        rating=data.rating,
        task_completed=data.task_completed,
        estimated_minutes_saved=data.estimated_minutes_saved,
        prompt_tokens=usage.prompt_tokens if usage else None,
        completion_tokens=usage.completion_tokens if usage else None,
        total_tokens=usage.total_tokens if usage else None,
        occurred_at=data.occurred_at,
        analysis_status=AnalysisStatus.PENDING.value,
    )
    session.add(event)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing = await event_repository.find_by_external_key(
            session,
            agent_id=data.agent_id,
            external_id=data.external_id,
        )
        if existing is None:
            raise
        return (
            EventAccepted(
                id=existing.id,
                duplicate=True,
                analysis_status=AnalysisStatus(existing.analysis_status),
            ),
            True,
        )

    await session.refresh(event)
    return (
        EventAccepted(
            id=event.id,
            duplicate=False,
            analysis_status=AnalysisStatus.PENDING,
        ),
        False,
    )


def to_event_list_item(view: EventView) -> EventListItem:
    analysis = view.analysis
    scenario = view.scenario
    return EventListItem(
        id=view.event.id,
        external_id=view.event.external_id,
        agent_id=view.event.agent_id,
        user_id=view.event.user_id,
        team=view.event.team,
        direction=view.event.direction,
        is_synthetic=view.event.is_synthetic,
        occurred_at=view.event.occurred_at,
        received_at=view.event.received_at,
        effective_user_query=(
            analysis.effective_user_query if analysis else None
        ),
        category=analysis.category if analysis else None,
        scenario=(
            ScenarioReference(id=scenario.id, name=scenario.name)
            if scenario
            else None
        ),
        classification_confidence=(
            float(analysis.classification_confidence) if analysis else None
        ),
        query_problem_reasons=(
            analysis.query_problem_reasons if analysis else None
        ),
        automation_potential=(
            analysis.automation_potential if analysis else None
        ),
        analysis_status=view.event.analysis_status,
    )


def to_event_detail(view: EventView) -> EventDetail:
    item = to_event_list_item(view)
    return EventDetail(
        **item.model_dump(),
        model=view.event.model,
        stream=view.event.stream,
        execution_status=view.event.execution_status,
        latency_ms=view.event.latency_ms,
        rating=float(view.event.rating) if view.event.rating is not None else None,
        task_completed=view.event.task_completed,
        estimated_minutes_saved=view.event.estimated_minutes_saved,
        prompt_tokens=view.event.prompt_tokens,
        completion_tokens=view.event.completion_tokens,
        total_tokens=view.event.total_tokens,
        warnings=view.analysis.warnings if view.analysis else None,
    )


async def list_events(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    category: str | None,
    scenario_id: UUID | None,
    analysis_status: str | None,
    has_query_problem: bool | None,
) -> EventListResponse:
    views, total = await event_repository.list_event_views(
        session,
        page=page,
        page_size=page_size,
        category=category,
        scenario_id=scenario_id,
        analysis_status=analysis_status,
        has_query_problem=has_query_problem,
    )
    return EventListResponse(
        items=[to_event_list_item(view) for view in views],
        page=page,
        page_size=page_size,
        total=total,
    )

