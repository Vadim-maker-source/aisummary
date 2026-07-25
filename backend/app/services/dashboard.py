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
    CategorySummaryItem,
    CategorySummaryResponse,
    DashboardSummary,
    DecisionRecommendation,
    DecisionSupportResponse,
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

CATEGORY_PURPOSES = {
    "text_generation": "создания и редактирования рабочих текстов",
    "information_search": "поиска и сбора информации из внутренних и внешних источников",
    "summarization": "быстрого получения кратких выводов из писем, встреч и документов",
    "data_analysis": "анализа таблиц, метрик и SQL-задач",
    "code_assistance": "разработки, отладки и объяснения программного кода",
    "reporting_export": "подготовки отчётов и выгрузок в рабочие форматы",
    "task_management": "создания, изменения и контроля рабочих задач",
    "monitoring_automation": "регулярного мониторинга событий и уведомлений",
    "calendar_planning": "планирования встреч, слотов и напоминаний",
    "knowledge_explanation": "объяснения понятий и обучения сотрудников",
    "non_work_general": "общения и вопросов, не связанных с рабочими процессами",
    "other": "запросов, для которых пока недостаточно данных для уверенной классификации",
}

TRAINING_ACTIONS = {
    "ambiguous": "Показать примеры однозначных формулировок: объект, действие и ожидаемый результат.",
    "missing_context": "Научить указывать источник данных, период, ограничения и формат результата.",
    "multiple_intents": "Научить разделять составную задачу на последовательные запросы.",
    "unsupported_task": "Объяснить границы агента и доступные интеграции.",
    "low_classification_confidence": "Разобрать реальные запросы команды и закрепить шаблон постановки задачи.",
    "unclassified": "Провести короткий разбор новых сценариев и дополнить каталог примерами.",
}

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


async def get_category_summaries(
    session: AsyncSession,
) -> CategorySummaryResponse:
    category_rows = await dashboard_repository.get_category_counts(session)
    total = sum(count for _, count in category_rows)
    scenarios, _ = await dashboard_repository.list_current_scenarios(
        session,
        category=None,
        page=1,
        page_size=1_000,
    )
    decision_rows = await dashboard_repository.get_decision_rows(session)

    scenarios_by_category: dict[str, list] = defaultdict(list)
    for scenario, request_count in scenarios:
        scenarios_by_category[str(scenario.category)].append(
            (scenario, request_count)
        )

    problems_by_category: dict[str, Counter[str]] = defaultdict(Counter)
    queries_by_category: dict[str, list[str]] = defaultdict(list)
    for row in decision_rows:
        category = str(row[12]) if row[12] else None
        if category is None:
            continue
        problems_by_category[category].update(row[9] or [])
        query = str(row[13] or "").strip()
        if query and query not in queries_by_category[category]:
            queries_by_category[category].append(query)

    items: list[CategorySummaryItem] = []
    for category, count in category_rows:
        category_scenarios = scenarios_by_category.get(category, [])
        top_names = [
            scenario.name
            for scenario, _ in category_scenarios[:3]
        ]
        representatives: list[str] = []
        for scenario, _ in category_scenarios:
            for query in scenario.representative_queries:
                if query not in representatives:
                    representatives.append(query)
                if len(representatives) == 3:
                    break
            if len(representatives) == 3:
                break
        if not representatives:
            representatives = queries_by_category.get(category, [])[:3]

        purpose = CATEGORY_PURPOSES.get(category, "решения рабочих задач")
        if top_names:
            summary = (
                f"Сотрудники используют ИИ для {purpose}. "
                f"Наиболее частые сценарии: {', '.join(top_names)}."
            )
        else:
            summary = (
                f"Сотрудники используют ИИ для {purpose}. "
                "Устойчивые сценарии появятся после накопления похожих запросов."
            )
        items.append(
            CategorySummaryItem(
                category=category,
                request_count=count,
                percentage=round((count / total * 100) if total else 0, 1),
                purpose=purpose,
                summary=summary,
                top_scenarios=top_names,
                representative_queries=representatives,
                top_problems=[
                    PROBLEM_LABELS.get(code, code)
                    for code, _ in problems_by_category[category].most_common(3)
                ],
            )
        )
    return CategorySummaryResponse(items=items)


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
        completion_values = [row[10] for row in group if row[10] is not None]
        completed = sum(1 for value in completion_values if value is True)
        saved_minutes = sum(int(row[11] or 0) for row in group)
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
                task_completion_rate=(
                    round(completed / len(completion_values) * 100, 1)
                    if completion_values
                    else None
                ),
                value_evidence_coverage=round(
                    len(completion_values) / total * 100,
                    1,
                ),
                estimated_hours_saved=round(saved_minutes / 60, 1),
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


async def get_decision_support(
    session: AsyncSession,
) -> DecisionSupportResponse:
    rows = await dashboard_repository.get_decision_rows(session)
    scenarios, _ = await dashboard_repository.list_current_scenarios(
        session,
        category=None,
        page=1,
        page_size=1_000,
    )
    recommendations: list[DecisionRecommendation] = []
    limitations: list[str] = []

    # Where to train users: prefer teams, then directions, and keep evidence
    # tied to real recurring formulation problems.
    training_groups: dict[str, list[tuple]] = defaultdict(list)
    for row in rows:
        scope = row[1] or row[2]
        if scope:
            training_groups[str(scope)].append(row)
    if not training_groups:
        limitations.append(
            "Нельзя определить, где обучать пользователей: поля team и direction не заполнены."
        )
    for scope, group in training_groups.items():
        counts: Counter[str] = Counter()
        examples: dict[str, list[str]] = defaultdict(list)
        for row in group:
            for code in row[9] or []:
                if code not in TRAINING_ACTIONS:
                    continue
                counts[code] += 1
                query = str(row[13] or "").strip()
                if query and query not in examples[code]:
                    examples[code].append(query)
        if not counts:
            continue
        code, count = counts.most_common(1)[0]
        rate = count / len(group) * 100
        if count < 2 and rate < 20:
            continue
        recommendations.append(
            DecisionRecommendation(
                kind="training",
                priority="high" if rate >= 25 else "medium",
                title=f"Обучить пользователей: {scope}",
                evidence=(
                    f"{count} из {len(group)} запросов ({rate:.1f}%) содержат "
                    f"проблему «{PROBLEM_LABELS.get(code, code)}»."
                ),
                action=TRAINING_ACTIONS[code],
                scope=scope,
                affected_requests=count,
                examples=examples[code][:3],
            )
        )

    # Which agents to develop: only evidence from observed answers/outcomes.
    by_agent: dict[str, list[tuple]] = defaultdict(list)
    for row in rows:
        if row[0]:
            by_agent[str(row[0])].append(row)
    agent_evidence = False
    for agent, group in by_agent.items():
        observed = [
            row for row in group
            if row[4] in {"success", "error"}
            or row[5] is not None
            or row[6] is not None
            or row[10] is not None
        ]
        if not observed:
            continue
        agent_evidence = True
        failures = sum(
            1 for row in observed
            if row[4] == "error"
            or (row[6] is not None and float(row[6]) <= 2)
            or row[10] is False
        )
        if failures == 0:
            continue
        rate = failures / len(observed) * 100
        examples = [
            str(row[13])
            for row in observed
            if row[13]
            and (
                row[4] == "error"
                or (row[6] is not None and float(row[6]) <= 2)
                or row[10] is False
            )
        ][:3]
        recommendations.append(
            DecisionRecommendation(
                kind="agent",
                priority="high" if rate >= 20 else "medium",
                title=f"Развить агента: {agent}",
                evidence=(
                    f"{failures} из {len(observed)} наблюдаемых результатов "
                    f"({rate:.1f}%) завершились ошибкой, низкой оценкой или "
                    "невыполненной задачей."
                ),
                action=(
                    "Разобрать неуспешные примеры, проверить интеграции и добавить "
                    "регрессионные тесты для повторяющихся сценариев."
                ),
                scope=agent,
                affected_requests=failures,
                examples=examples,
            )
        )
    if not agent_evidence:
        limitations.append(
            "Нельзя рекомендовать развитие агентов: нет ответов, статусов, оценок или task_completed."
        )

    # What to automate: high-potential scenarios ranked by observed demand.
    for scenario, request_count in scenarios:
        if str(scenario.automation_potential) != "high":
            continue
        recommendations.append(
            DecisionRecommendation(
                kind="automation",
                priority="high" if request_count >= 10 else "medium",
                title=f"Автоматизировать: {scenario.name}",
                evidence=(
                    f"{request_count} похожих запросов; сценарий повторяемый "
                    "и имеет высокий потенциал автоматизации."
                ),
                action=scenario.suggested_action,
                scope=str(scenario.category),
                affected_requests=request_count,
                examples=list(scenario.representative_queries[:3]),
            )
        )

    priority_order = {"high": 0, "medium": 1, "low": 2}
    kind_order = {"agent": 0, "training": 1, "automation": 2}
    recommendations.sort(
        key=lambda item: (
            priority_order[item.priority],
            kind_order[item.kind],
            -item.affected_requests,
            item.title,
        )
    )
    if not any(row[10] is not None for row in rows):
        limitations.append(
            "Реальная экономия времени не доказана: передавайте task_completed и estimated_minutes_saved."
        )
    return DecisionSupportResponse(
        items=recommendations[:15],
        data_limitations=limitations,
    )

