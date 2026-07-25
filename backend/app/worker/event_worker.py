from __future__ import annotations

import asyncio
from uuid import UUID

from sqlalchemy import delete, select

from app.core.database import async_session_factory
from app.models.entities import (
    AgentEvent,
    AnalysisRun,
    EventAnalysis,
    Scenario,
    ScenarioMember,
)
from app.models.enums import AnalysisStatus
from app.repositories.events import get_current_scenarios
from app.schemas.internal import EventAnalysisResultPayload
from app.services.analytics_gateway import analyze_event


async def claim_pending_event_ids(batch_size: int) -> list[UUID]:
    async with async_session_factory() as session:
        async with session.begin():
            events = list(
                (
                    await session.scalars(
                        select(AgentEvent)
                        .where(
                            AgentEvent.analysis_status
                            == AnalysisStatus.PENDING.value
                        )
                        .order_by(AgentEvent.received_at, AgentEvent.id)
                        .limit(batch_size)
                        .with_for_update(skip_locked=True)
                    )
                ).all()
            )
            for event in events:
                event.analysis_status = AnalysisStatus.PROCESSING.value
                event.analysis_error = None
        return [event.id for event in events]


async def process_event(event_id: UUID) -> None:
    async with async_session_factory() as session:
        event = await session.get(AgentEvent, event_id)
        if event is None:
            return

        current_scenarios = await get_current_scenarios(session)
        known_scenarios = [
            {
                "id": str(scenario.id),
                "category": scenario.category,
                "name": scenario.name,
                "representative_queries": scenario.representative_queries,
            }
            for scenario in current_scenarios
        ]
        data = {
            "event_id": str(event.id),
            "messages": event.raw_request.get("messages", []),
            "model": event.model,
            "prompt_tokens": event.prompt_tokens,
        }

        try:
            raw_result = await analyze_event(data, known_scenarios)
            result = EventAnalysisResultPayload.model_validate(raw_result)

            async with session.begin_nested():
                existing = await session.scalar(
                    select(EventAnalysis).where(
                        EventAnalysis.event_id == event.id
                    )
                )
                if existing is None:
                    existing = EventAnalysis(event_id=event.id)
                    session.add(existing)
                existing.effective_user_query = result.effective_query
                existing.category = result.category.value
                existing.classification_confidence = (
                    result.classification_confidence
                )
                existing.query_problem_reasons = [
                    item.value for item in result.query_problem_reasons
                ]
                existing.automation_potential = (
                    result.automation_potential.value
                )
                existing.warnings = [item.value for item in result.warnings]
                existing.classifier_version = result.classifier_version

                if result.scenario_id is not None:
                    scenario = await session.scalar(
                        select(Scenario)
                        .join(
                            AnalysisRun,
                            AnalysisRun.id == Scenario.analysis_run_id,
                        )
                        .where(
                            Scenario.id == result.scenario_id,
                            AnalysisRun.is_current.is_(True),
                        )
                    )
                    if scenario is not None:
                        await session.execute(
                            delete(ScenarioMember)
                            .where(ScenarioMember.event_id == event.id)
                            .where(
                                ScenarioMember.scenario_id.in_(
                                    select(Scenario.id)
                                    .join(
                                        AnalysisRun,
                                        AnalysisRun.id
                                        == Scenario.analysis_run_id,
                                    )
                                    .where(AnalysisRun.is_current.is_(True))
                                )
                            )
                        )
                        session.add(
                            ScenarioMember(
                                scenario_id=scenario.id,
                                event_id=event.id,
                                similarity=result.scenario_confidence,
                            )
                        )

                event.analysis_status = AnalysisStatus.COMPLETED.value
                event.analysis_error = None
            await session.commit()
        except Exception as exc:
            await session.rollback()
            event = await session.get(AgentEvent, event_id)
            if event is not None:
                event.analysis_status = AnalysisStatus.FAILED.value
                event.analysis_error = (
                    f"{type(exc).__name__}: {str(exc)[:500]}"
                )
                await session.commit()


async def process_event_batch(
    batch_size: int,
    concurrency: int = 4,
) -> int:
    event_ids = await claim_pending_event_ids(batch_size)
    semaphore = asyncio.Semaphore(max(1, concurrency))

    async def bounded_process(event_id: UUID) -> None:
        async with semaphore:
            await process_event(event_id)

    await asyncio.gather(*(bounded_process(event_id) for event_id in event_ids))
    return len(event_ids)

