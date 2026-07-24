from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import EventAnalysis
from app.repositories import dashboard as dashboard_repository
from app.schemas.dashboard import (
    CategoryItem,
    CategoryListResponse,
    DashboardSummary,
    ScenarioDetail,
    ScenarioListItem,
    ScenarioListResponse,
    TimelineItem,
    TimelineResponse,
)


async def get_summary(
    session: AsyncSession,
    *,
    date_from: datetime | None,
    date_to: datetime | None,
) -> DashboardSummary:
    values = await dashboard_repository.get_summary_counts(
        session,
        date_from=date_from,
        date_to=date_to,
    )
    return DashboardSummary(**values)


async def get_categories(session: AsyncSession) -> CategoryListResponse:
    rows = await dashboard_repository.get_category_counts(session)
    total = int((await session.scalar(select(func.count(EventAnalysis.id)))) or 0)
    return CategoryListResponse(
        items=[
            CategoryItem(
                category=category,
                request_count=count,
                percentage=round((count / total * 100) if total else 0, 1),
            )
            for category, count in rows
        ]
    )


def to_scenario_list_item(scenario, request_count: int) -> ScenarioListItem:
    return ScenarioListItem(
        id=scenario.id,
        category=scenario.category,
        name=scenario.name,
        summary=scenario.summary,
        request_count=request_count,
        automation_potential=scenario.automation_potential,
        common_problems=scenario.common_problems,
        suggested_action=scenario.suggested_action,
    )


async def list_scenarios(
    session: AsyncSession,
    *,
    category: str | None,
    page: int,
    page_size: int,
) -> ScenarioListResponse:
    rows, total = await dashboard_repository.list_current_scenarios(
        session,
        category=category,
        page=page,
        page_size=page_size,
    )
    return ScenarioListResponse(
        items=[
            to_scenario_list_item(scenario, request_count)
            for scenario, request_count in rows
        ],
        page=page,
        page_size=page_size,
        total=total,
    )


async def get_scenario(
    session: AsyncSession,
    scenario_id: UUID,
) -> ScenarioDetail | None:
    row = await dashboard_repository.get_current_scenario(session, scenario_id)
    if row is None:
        return None
    scenario, request_count = row
    return ScenarioDetail(
        **to_scenario_list_item(scenario, request_count).model_dump(),
        representative_queries=scenario.representative_queries,
    )


async def get_timeline(session: AsyncSession) -> TimelineResponse:
    rows = await dashboard_repository.get_timeline(session)
    return TimelineResponse(
        items=[
            TimelineItem(
                date=date_value,
                request_count=request_count,
                query_problem_count=query_problem_count,
            )
            for date_value, request_count, query_problem_count in rows
        ]
    )

