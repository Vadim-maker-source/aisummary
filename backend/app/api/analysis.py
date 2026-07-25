from fastapi import APIRouter, Depends, status
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models.entities import AgentEvent, AnalysisRun, Scenario, ScenarioMember
from app.models.enums import AnalysisStatus
from app.models.enums import AnalysisRunStatus
from app.schemas.dashboard import AnalysisRunAccepted, ReprocessAccepted

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

