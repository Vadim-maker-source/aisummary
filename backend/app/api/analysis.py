from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.models.entities import (
    AgentEvent,
    AnalysisRun,
    ImportJob,
    Scenario,
    ScenarioMember,
)
from app.models.enums import AnalysisStatus
from app.models.enums import AnalysisRunStatus
from app.schemas.dashboard import (
    AnalysisRunAccepted,
    ReprocessAccepted,
    ResetAnalyticsRequest,
    ResetAnalyticsResponse,
)

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post(
    "/recluster",
    response_model=AnalysisRunAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def recluster(
    session: AsyncSession = Depends(get_db_session),
) -> AnalysisRunAccepted:
    run = AnalysisRun(
        status=AnalysisRunStatus.PENDING.value,
        algorithm_version="tfidf-agg-v1",
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return AnalysisRunAccepted(run_id=run.id, status=run.status)


@router.post(
    "/reprocess",
    response_model=ReprocessAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def reprocess_all_events(
    session: AsyncSession = Depends(get_db_session),
) -> ReprocessAccepted:
    """Queue all stored events after classifier or taxonomy changes."""

    count = int((await session.scalar(select(func.count(AgentEvent.id)))) or 0)
    await session.execute(
        delete(ScenarioMember).where(
            ScenarioMember.scenario_id.in_(
                select(Scenario.id)
                .join(AnalysisRun, AnalysisRun.id == Scenario.analysis_run_id)
                .where(AnalysisRun.is_current.is_(True))
            )
        )
    )
    await session.execute(
        update(AgentEvent).values(
            analysis_status=AnalysisStatus.PENDING.value,
            analysis_error=None,
        )
    )
    await session.commit()
    return ReprocessAccepted(queued_events=count)


@router.post(
    "/reset",
    response_model=ResetAnalyticsResponse,
)
async def reset_analytics_data(
    payload: ResetAnalyticsRequest,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> ResetAnalyticsResponse:
    """Delete all imported analytics data while preserving the database schema."""

    if not settings.allow_data_reset:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Data reset is disabled by the server administrator",
        )

    active_imports = int(
        (
            await session.scalar(
                select(func.count(ImportJob.id)).where(
                    ImportJob.status.in_(("pending", "processing"))
                )
            )
        )
        or 0
    )
    processing_events = int(
        (
            await session.scalar(
                select(func.count(AgentEvent.id)).where(
                    AgentEvent.analysis_status == AnalysisStatus.PROCESSING.value
                )
            )
        )
        or 0
    )
    if active_imports or processing_events:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Wait for active imports and analysis tasks to finish "
                "before resetting data"
            ),
        )

    deleted_events = int(
        (await session.scalar(select(func.count(AgentEvent.id)))) or 0
    )
    deleted_imports = int(
        (await session.scalar(select(func.count(ImportJob.id)))) or 0
    )
    deleted_runs = int(
        (await session.scalar(select(func.count(AnalysisRun.id)))) or 0
    )

    await session.execute(delete(AnalysisRun))
    await session.execute(delete(AgentEvent))
    await session.execute(delete(ImportJob))
    await session.commit()
    return ResetAnalyticsResponse(
        deleted_events=deleted_events,
        deleted_imports=deleted_imports,
        deleted_analysis_runs=deleted_runs,
    )

