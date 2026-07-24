from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from statistics import fmean
from typing import Literal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import EventAnalysis
from app.repositories import dashboard as dashboard_repository
from app.schemas.dashboard import (
    CategoryItem,
    CategoryListResponse,
    DashboardSummary,
    EffectivenessItem,
    EffectivenessResponse,
    ProblemItem,
    ProblemListResponse,
    ScenarioDetail,
    ScenarioListItem,
    ScenarioListResponse,
    TimelineItem,
    TimelineResponse,
    ScenarioTrendItem,
    ScenarioTrendResponse,
)

PROBLEM_LABELS = {
    "ambiguous": "Неоднозначная формулировка",
    "missing_context": "Недостаточно контекста",
    "multiple_intents": "Несколько задач в одном запросе",
    "oversized_context": "Слишком большой контекст",
    "unsupported_task": "Неподдерживаемая задача",
    "low_classification_confidence": "Низкая уверенность классификации",
    "unclassified": "Не удалось классифицировать",
    "execution_error": "Ошибка выполнения агента",
    "low_rating": "Низкая оценка ответа",
    "empty_answer": "Пустой ответ агента",
}


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


async def get_problems(session: AsyncSession) -> ProblemListResponse:
    rows = await dashboard_repository.get_problem_rows(session)
    query_counts: Counter[str] = Counter()
    agent_counts: Counter[str] = Counter()
    answer_observations = 0

    for reasons, execution_status, agent_answer, rating in rows:
        query_counts.update(str(reason) for reason in (reasons or []))
        if (
            execution_status in {"success", "error"}
            or agent_answer is not None
            or rating is not None
        ):
            answer_observations += 1
        if execution_status == "error":
            agent_counts["execution_error"] += 1
        if rating is not None and float(rating) <= 2:
            agent_counts["low_rating"] += 1
        if execution_status == "success" and not (agent_answer or "").strip():
            agent_counts["empty_answer"] += 1

    total = len(rows)
    items = [
        ProblemItem(
            code=code,
            label=PROBLEM_LABELS.get(code, code),
            count=count,
            percentage=round((count / total * 100) if total else 0, 1),
            kind=kind,
        )
        for kind, counts in (("query", query_counts), ("agent", agent_counts))
        for code, count in counts.most_common()
    ]
    items.sort(key=lambda item: (-item.count, item.label))
    return ProblemListResponse(
        items=items,
        total_requests=total,
        agent_quality_available=answer_observations > 0,
    )


async def get_scenario_trends(
    session: AsyncSession,
    *,
    window_days: int,
) -> ScenarioTrendResponse:
    rows = await dashboard_repository.get_scenario_trend_rows(session)
    if not rows:
        return ScenarioTrendResponse(
            available=False,
            window_days=window_days,
            date_from=None,
            date_to=None,
            items=[],
        )

    dates = [row[3].date() for row in rows]
    date_to = max(dates)
    current_start = date_to - timedelta(days=window_days - 1)
    previous_start = current_start - timedelta(days=window_days)
    available = min(dates) <= previous_start

    scenario_meta: dict[UUID, tuple[str, str]] = {}
    current_counts: Counter[UUID] = Counter()
    previous_counts: Counter[UUID] = Counter()
    for scenario_id, name, category, occurred_at in rows:
        scenario_meta[scenario_id] = (name, category)
        event_date = occurred_at.date()
        if current_start <= event_date <= date_to:
            current_counts[scenario_id] += 1
        elif previous_start <= event_date < current_start:
            previous_counts[scenario_id] += 1

    items: list[ScenarioTrendItem] = []
    for scenario_id, (name, category) in scenario_meta.items():
        current = current_counts[scenario_id]
        previous = previous_counts[scenario_id]
        if current == 0 and previous == 0:
            continue
        if previous == 0 and current > 0:
            growth = None
            trend = "new"
        else:
            growth = round(((current - previous) / previous) * 100, 1)
            if growth >= 10:
                trend = "growing"
            elif growth <= -10:
                trend = "declining"
            else:
                trend = "stable"
        items.append(
            ScenarioTrendItem(
                id=scenario_id,
                name=name,
                category=category,
                current_count=current,
                previous_count=previous,
                growth_percent=growth,
                trend=trend,
            )
        )

    trend_priority = {"new": 3, "growing": 2, "stable": 1, "declining": 0}
    items.sort(
        key=lambda item: (
            -trend_priority[item.trend],
            -(item.growth_percent or 0),
            -item.current_count,
            item.name,
        )
    )
    return ScenarioTrendResponse(
        available=available,
        window_days=window_days,
        date_from=current_start,
        date_to=date_to,
        items=items,
    )


async def get_effectiveness(
    session: AsyncSession,
    *,
    dimension: Literal["agent_id", "team", "direction"],
) -> EffectivenessResponse:
    rows = await dashboard_repository.get_effectiveness_rows(session)
    index = {"agent_id": 0, "team": 1, "direction": 2}[dimension]
    grouped: dict[str, list[tuple]] = defaultdict(list)
    populated = 0
    for row in rows:
        value = row[index]
        if value:
            grouped[str(value)].append(row)
            populated += 1

    items: list[EffectivenessItem] = []
    for name, group in grouped.items():
        total = len(group)
        analyzed = sum(1 for row in group if row[8] is not None)
        problematic = sum(1 for row in group if row[9])
        known_statuses = [
            row[4] for row in group if row[4] in {"success", "error"}
        ]
        successes = sum(1 for status in known_statuses if status == "success")
        answers = sum(1 for row in group if row[5] is not None)
        ratings = [float(row[6]) for row in group if row[6] is not None]
        latencies = [float(row[7]) for row in group if row[7] is not None]
        users = {str(row[3]) for row in group if row[3]}
        items.append(
            EffectivenessItem(
                name=name,
                total_requests=total,
                analyzed_requests=analyzed,
                problem_rate=round(
                    (problematic / analyzed * 100) if analyzed else 0,
                    1,
                ),
                success_rate=(
                    round(successes / len(known_statuses) * 100, 1)
                    if known_statuses
                    else None
                ),
                answer_coverage=round(answers / total * 100, 1),
                average_rating=round(fmean(ratings), 2) if ratings else None,
                average_latency_ms=(
                    round(fmean(latencies), 1) if latencies else None
                ),
                unique_users=len(users) if users else None,
            )
        )
    items.sort(key=lambda item: (-item.total_requests, item.name))
    coverage = round((populated / len(rows) * 100) if rows else 0, 1)
    return EffectivenessResponse(
        dimension=dimension,
        available=bool(items),
        coverage_percent=coverage,
        items=items,
    )

