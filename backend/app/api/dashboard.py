from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models.enums import Category
from app.schemas.dashboard import (
    CategorySummaryResponse,
    CategoryListResponse,
    DashboardSummary,
    DecisionSupportResponse,
    EffectivenessResponse,
    ProblemListResponse,
    ScenarioListResponse,
    ScenarioTrendResponse,
    TimelineResponse,
)
from app.services import dashboard as dashboard_service
from app.services.report_export import ReportFormat, build_report

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def summary(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> DashboardSummary:
    return await dashboard_service.get_summary(
        session,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/categories", response_model=CategoryListResponse)
async def categories(
    session: AsyncSession = Depends(get_db_session),
) -> CategoryListResponse:
    return await dashboard_service.get_categories(session)


@router.get("/category-summaries", response_model=CategorySummaryResponse)
async def category_summaries(
    session: AsyncSession = Depends(get_db_session),
) -> CategorySummaryResponse:
    return await dashboard_service.get_category_summaries(session)


@router.get("/decision-support", response_model=DecisionSupportResponse)
async def decision_support(
    session: AsyncSession = Depends(get_db_session),
) -> DecisionSupportResponse:
    return await dashboard_service.get_decision_support(session)


@router.get("/scenarios", response_model=ScenarioListResponse)
async def scenarios(
    category: Category | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
) -> ScenarioListResponse:
    return await dashboard_service.list_scenarios(
        session,
        category=category.value if category else None,
        page=page,
        page_size=page_size,
    )


@router.get("/timeline", response_model=TimelineResponse)
async def timeline(
    session: AsyncSession = Depends(get_db_session),
) -> TimelineResponse:
    return await dashboard_service.get_timeline(session)


@router.get("/problems", response_model=ProblemListResponse)
async def problems(
    session: AsyncSession = Depends(get_db_session),
) -> ProblemListResponse:
    return await dashboard_service.get_problems(session)


@router.get("/scenario-trends", response_model=ScenarioTrendResponse)
async def scenario_trends(
    window_days: int = Query(default=7, ge=2, le=90),
    session: AsyncSession = Depends(get_db_session),
) -> ScenarioTrendResponse:
    return await dashboard_service.get_scenario_trends(
        session,
        window_days=window_days,
    )


@router.get("/effectiveness", response_model=EffectivenessResponse)
async def effectiveness(
    dimension: Literal["agent_id", "team", "direction"] = "agent_id",
    session: AsyncSession = Depends(get_db_session),
) -> EffectivenessResponse:
    return await dashboard_service.get_effectiveness(
        session,
        dimension=dimension,
    )


@router.get("/report")
async def report(
    format: ReportFormat = Query(default="pdf"),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    artifact = await build_report(session, format)
    return Response(
        content=artifact.content,
        media_type=artifact.media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{artifact.filename}"',
        },
    )

