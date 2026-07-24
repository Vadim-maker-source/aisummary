from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import (
    AgentEvent,
    AnalysisRun,
    EventAnalysis,
    Scenario,
    ScenarioMember,
)


def event_date_conditions(
    date_from: datetime | None,
    date_to: datetime | None,
) -> list:
    conditions = []
    if date_from is not None:
        conditions.append(AgentEvent.occurred_at >= date_from)
    if date_to is not None:
        conditions.append(AgentEvent.occurred_at < date_to)
    return conditions


async def get_summary_counts(
    session: AsyncSession,
    *,
    date_from: datetime | None,
    date_to: datetime | None,
) -> dict[str, int | float]:
    conditions = event_date_conditions(date_from, date_to)

    total = int(
        (
            await session.scalar(
                select(func.count(AgentEvent.id)).where(*conditions)
            )
        )
        or 0
    )
    analyzed = int(
        (
            await session.scalar(
                select(func.count(EventAnalysis.id))
                .join(AgentEvent, AgentEvent.id == EventAnalysis.event_id)
                .where(*conditions)
            )
        )
        or 0
    )
    pending = int(
        (
            await session.scalar(
                select(func.count(AgentEvent.id)).where(
                    *conditions,
                    AgentEvent.analysis_status.in_(["pending", "processing"]),
                )
            )
        )
        or 0
    )
    failed = int(
        (
            await session.scalar(
                select(func.count(AgentEvent.id)).where(
                    *conditions,
                    AgentEvent.analysis_status == "failed",
                )
            )
        )
        or 0
    )
    category_count = int(
        (
            await session.scalar(
                select(func.count(func.distinct(EventAnalysis.category)))
                .join(AgentEvent, AgentEvent.id == EventAnalysis.event_id)
                .where(*conditions)
            )
        )
        or 0
    )
    unclassified = int(
        (
            await session.scalar(
                select(func.count(EventAnalysis.id))
                .join(AgentEvent, AgentEvent.id == EventAnalysis.event_id)
                .where(*conditions, EventAnalysis.category == "other")
            )
        )
        or 0
    )
    problematic = int(
        (
            await session.scalar(
                select(func.count(EventAnalysis.id))
                .join(AgentEvent, AgentEvent.id == EventAnalysis.event_id)
                .where(
                    *conditions,
                    EventAnalysis.query_problem_reasons != [],
                )
            )
        )
        or 0
    )
    scenario_count = int(
        (
            await session.scalar(
                select(func.count(Scenario.id))
                .join(AnalysisRun, AnalysisRun.id == Scenario.analysis_run_id)
                .where(AnalysisRun.is_current.is_(True))
            )
        )
        or 0
    )
    return {
        "total_requests": total,
        "analyzed_requests": analyzed,
        "pending_requests": pending,
        "failed_requests": failed,
        "category_count": category_count,
        "scenario_count": scenario_count,
        "unclassified_count": unclassified,
        "query_problem_rate": round(
            (problematic / analyzed * 100) if analyzed else 0,
            1,
        ),
    }


async def get_category_counts(
    session: AsyncSession,
) -> list[tuple[str, int]]:
    rows = (
        await session.execute(
            select(EventAnalysis.category, func.count(EventAnalysis.id))
            .group_by(EventAnalysis.category)
            .order_by(func.count(EventAnalysis.id).desc(), EventAnalysis.category)
        )
    ).all()
    return [(str(row[0]), int(row[1])) for row in rows]


async def list_current_scenarios(
    session: AsyncSession,
    *,
    category: str | None,
    page: int,
    page_size: int,
) -> tuple[list[tuple[Scenario, int]], int]:
    conditions = [AnalysisRun.is_current.is_(True)]
    if category is not None:
        conditions.append(Scenario.category == category)

    base = (
        select(Scenario, func.count(ScenarioMember.event_id).label("request_count"))
        .join(AnalysisRun, AnalysisRun.id == Scenario.analysis_run_id)
        .outerjoin(
            ScenarioMember,
            ScenarioMember.scenario_id == Scenario.id,
        )
        .where(*conditions)
        .group_by(Scenario.id)
    )
    count_query = (
        select(func.count(Scenario.id))
        .join(AnalysisRun, AnalysisRun.id == Scenario.analysis_run_id)
        .where(*conditions)
    )
    rows = (
        await session.execute(
            base.order_by(
                func.count(ScenarioMember.event_id).desc(),
                Scenario.name,
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    total = int((await session.scalar(count_query)) or 0)
    return [(row[0], int(row[1])) for row in rows], total


async def get_current_scenario(
    session: AsyncSession,
    scenario_id: UUID,
) -> tuple[Scenario, int] | None:
    row = (
        await session.execute(
            select(
                Scenario,
                func.count(ScenarioMember.event_id).label("request_count"),
            )
            .join(AnalysisRun, AnalysisRun.id == Scenario.analysis_run_id)
            .outerjoin(
                ScenarioMember,
                ScenarioMember.scenario_id == Scenario.id,
            )
            .where(
                AnalysisRun.is_current.is_(True),
                Scenario.id == scenario_id,
            )
            .group_by(Scenario.id)
        )
    ).one_or_none()
    if row is None:
        return None
    return row[0], int(row[1])


async def get_timeline(
    session: AsyncSession,
) -> list[tuple[object, int, int]]:
    event_date = func.date(AgentEvent.occurred_at)
    problem_case = case(
        (EventAnalysis.query_problem_reasons != [], 1),
        else_=0,
    )
    rows = (
        await session.execute(
            select(
                event_date.label("date"),
                func.count(AgentEvent.id).label("request_count"),
                func.sum(problem_case).label("query_problem_count"),
            )
            .outerjoin(EventAnalysis, EventAnalysis.event_id == AgentEvent.id)
            .where(AgentEvent.occurred_at.is_not(None))
            .group_by(event_date)
            .order_by(event_date)
        )
    ).all()
    return [
        (row[0], int(row[1]), int(row[2] or 0))
        for row in rows
    ]

