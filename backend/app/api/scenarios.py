from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.schemas.dashboard import ScenarioDetail
from app.services import dashboard as dashboard_service

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.get("/{scenario_id}", response_model=ScenarioDetail)
async def scenario_detail(
    scenario_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> ScenarioDetail:
    result = await dashboard_service.get_scenario(session, scenario_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return result

