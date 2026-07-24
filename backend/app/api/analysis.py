from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models.entities import AnalysisRun
from app.models.enums import AnalysisRunStatus
from app.schemas.dashboard import AnalysisRunAccepted

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

