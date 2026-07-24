from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.entities import (
    AgentEvent,
    AnalysisRun,
    EventAnalysis,
    Scenario,
    ScenarioMember,
)


@dataclass(slots=True)
class EventView:
    event: AgentEvent
    analysis: EventAnalysis | None
    scenario: Scenario | None


def current_scenario_subquery():
    return (
        select(
            ScenarioMember.event_id.label("event_id"),
            Scenario.id.label("scenario_id"),
        )
        .join(Scenario, Scenario.id == ScenarioMember.scenario_id)
        .join(AnalysisRun, AnalysisRun.id == Scenario.analysis_run_id)
        .where(AnalysisRun.is_current.is_(True))
        .subquery()
    )


async def find_by_external_key(
    session: AsyncSession,
    *,
    agent_id: str,
    external_id: str,
) -> AgentEvent | None:
    return await session.scalar(
        select(AgentEvent).where(
            AgentEvent.agent_id == agent_id,
            AgentEvent.external_id == external_id,
        )
    )


async def get_event_view(
    session: AsyncSession,
    event_id: UUID,
) -> EventView | None:
    current_member = current_scenario_subquery()
    scenario_alias = aliased(Scenario)
    row = (
        await session.execute(
            select(AgentEvent, EventAnalysis, scenario_alias)
            .outerjoin(EventAnalysis, EventAnalysis.event_id == AgentEvent.id)
            .outerjoin(
                current_member,
                current_member.c.event_id == AgentEvent.id,
            )
            .outerjoin(
                scenario_alias,
                scenario_alias.id == current_member.c.scenario_id,
            )
            .where(AgentEvent.id == event_id)
        )
    ).one_or_none()
    if row is None:
        return None
    return EventView(event=row[0], analysis=row[1], scenario=row[2])


def build_event_list_query(
    *,
    category: str | None,
    scenario_id: UUID | None,
    analysis_status: str | None,
    has_query_problem: bool | None,
) -> tuple[Select, Select]:
    current_member = current_scenario_subquery()
    scenario_alias = aliased(Scenario)

    base = (
        select(AgentEvent, EventAnalysis, scenario_alias)
        .outerjoin(EventAnalysis, EventAnalysis.event_id == AgentEvent.id)
        .outerjoin(current_member, current_member.c.event_id == AgentEvent.id)
        .outerjoin(
            scenario_alias,
            scenario_alias.id == current_member.c.scenario_id,
        )
    )

    count_query = (
        select(func.count(func.distinct(AgentEvent.id)))
        .select_from(AgentEvent)
        .outerjoin(EventAnalysis, EventAnalysis.event_id == AgentEvent.id)
        .outerjoin(current_member, current_member.c.event_id == AgentEvent.id)
        .outerjoin(
            scenario_alias,
            scenario_alias.id == current_member.c.scenario_id,
        )
    )

    conditions = []
    if category is not None:
        conditions.append(EventAnalysis.category == category)
    if scenario_id is not None:
        conditions.append(scenario_alias.id == scenario_id)
    if analysis_status is not None:
        conditions.append(AgentEvent.analysis_status == analysis_status)
    if has_query_problem is True:
        conditions.extend(
            [
                EventAnalysis.id.is_not(None),
                EventAnalysis.query_problem_reasons != [],
            ]
        )
    elif has_query_problem is False:
        conditions.extend(
            [
                EventAnalysis.id.is_not(None),
                EventAnalysis.query_problem_reasons == [],
            ]
        )

    if conditions:
        base = base.where(*conditions)
        count_query = count_query.where(*conditions)

    return base, count_query


async def list_event_views(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    category: str | None,
    scenario_id: UUID | None,
    analysis_status: str | None,
    has_query_problem: bool | None,
) -> tuple[list[EventView], int]:
    query, count_query = build_event_list_query(
        category=category,
        scenario_id=scenario_id,
        analysis_status=analysis_status,
        has_query_problem=has_query_problem,
    )
    query = (
        query.order_by(
            func.coalesce(AgentEvent.occurred_at, AgentEvent.received_at).desc(),
            AgentEvent.id,
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await session.execute(query)).all()
    total = int((await session.scalar(count_query)) or 0)
    return [
        EventView(event=row[0], analysis=row[1], scenario=row[2]) for row in rows
    ], total


async def get_current_scenarios(session: AsyncSession) -> list[Scenario]:
    return list(
        (
            await session.scalars(
                select(Scenario)
                .join(AnalysisRun, AnalysisRun.id == Scenario.analysis_run_id)
                .where(AnalysisRun.is_current.is_(True))
                .order_by(Scenario.id)
            )
        ).all()
    )

