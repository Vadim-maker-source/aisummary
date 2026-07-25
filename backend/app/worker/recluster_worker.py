from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select, update

from app.core.database import async_session_factory
from app.models.entities import (
    AgentEvent,
    AnalysisRun,
    EventAnalysis,
    Scenario,
    ScenarioMember,
)
from app.models.enums import AnalysisRunStatus, AnalysisStatus
from app.schemas.internal import ScenarioDiscoveryPayload
from app.services.analytics_gateway import discover_scenarios


async def claim_pending_run_id() -> UUID | None:
    async with async_session_factory() as session:
        async with session.begin():
            run = await session.scalar(
                select(AnalysisRun)
                .where(
                    AnalysisRun.status == AnalysisRunStatus.PENDING.value
                )
                .order_by(AnalysisRun.created_at, AnalysisRun.id)
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            if run is None:
                return None

            if run.trigger_import_id is not None:
                unfinished = int(
                    (
                        await session.scalar(
                            select(func.count(AgentEvent.id)).where(
                                AgentEvent.import_id
                                == run.trigger_import_id,
                                AgentEvent.analysis_status.in_(
                                    [
                                        AnalysisStatus.PENDING.value,
                                        AnalysisStatus.PROCESSING.value,
                                    ]
                                ),
                            )
                        )
                    )
                    or 0
                )
                if unfinished:
                    return None

            run.status = AnalysisRunStatus.PROCESSING.value
            return run.id


async def process_run(run_id: UUID) -> None:
    async with async_session_factory() as session:
        rows = (
            await session.execute(
                select(EventAnalysis)
                .join(AgentEvent, AgentEvent.id == EventAnalysis.event_id)
                .where(
                    AgentEvent.analysis_status
                    == AnalysisStatus.COMPLETED.value
                )
                .order_by(EventAnalysis.event_id)
            )
        ).scalars().all()
        records = [
            {
                "event_id": str(analysis.event_id),
                "effective_query": analysis.effective_user_query,
                "category": analysis.category,
                "classification_confidence": float(
                    analysis.classification_confidence
                ),
                "query_problem_reasons": analysis.query_problem_reasons,
            }
            for analysis in rows
        ]

        try:
            raw_result = await discover_scenarios(records)
            result = ScenarioDiscoveryPayload.model_validate(raw_result)

            async with session.begin_nested():
                run = await session.get(
                    AnalysisRun,
                    run_id,
                    with_for_update=True,
                )
                if run is None:
                    return

                for discovered in result.scenarios:
                    scenario = Scenario(
                        analysis_run_id=run.id,
                        category=discovered.category.value,
                        name=discovered.name,
                        summary=discovered.summary,
                        representative_queries=(
                            discovered.representative_queries
                        ),
                        common_problems=discovered.common_problems,
                        automation_potential=(
                            discovered.automation_potential.value
                        ),
                        suggested_action=discovered.suggested_action,
                    )
                    session.add(scenario)
                    await session.flush()
                    for event_id in discovered.member_event_ids:
                        session.add(
                            ScenarioMember(
                                scenario_id=scenario.id,
                                event_id=event_id,
                                similarity=None,
                            )
                        )

                await session.execute(
                    update(AnalysisRun)
                    .where(
                        AnalysisRun.is_current.is_(True),
                        AnalysisRun.id != run.id,
                    )
                    .values(is_current=False)
                )
                run.algorithm_version = result.algorithm_version
                run.status = AnalysisRunStatus.COMPLETED.value
                run.is_current = True
                run.finished_at = datetime.now(UTC)
                run.error_message = None
            await session.commit()
        except Exception as exc:
            await session.rollback()
            run = await session.get(AnalysisRun, run_id)
            if run is not None:
                run.status = AnalysisRunStatus.FAILED.value
                run.is_current = False
                run.error_message = (
                    f"{type(exc).__name__}: {str(exc)[:500]}"
                )
                run.finished_at = datetime.now(UTC)
                await session.commit()


async def process_next_run() -> int:
    run_id = await claim_pending_run_id()
    if run_id is None:
        return 0
    await process_run(run_id)
    return 1

