from __future__ import annotations

import importlib
import re
from collections.abc import Sequence
from typing import Any

from app.core.context_limits import context_exceeds_supported_limit


_CONTEXT_RE = re.compile(
    r"<context\b[^>]*>.*?</context>",
    flags=re.IGNORECASE | re.DOTALL,
)


def _normalize_query(messages: Sequence[dict[str, Any]]) -> tuple[str, list[str]]:
    warnings: list[str] = []
    user_messages = [
        str(message.get("content", ""))
        for message in messages
        if message.get("role") == "user"
    ]
    if not user_messages:
        return "", ["no_user_message"]
    content = user_messages[-1]
    matches = re.findall(
        r"<user_query>(.*?)</user_query>",
        content,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if matches:
        query = matches[-1]
    else:
        without_context = _CONTEXT_RE.sub(" ", content)
        query = without_context if without_context.strip() else content
    query = re.sub(r"\s+", " ", query).strip()
    if len(query) > 8000:
        query = f"{query[:4000]} {query[-4000:]}"
        warnings.append("query_truncated")
    return query, warnings


def _fallback_category(query: str) -> tuple[str, float, str]:
    groups = {
        "calendar_planning": ["встреч", "календар", "слот", "переговорн", "напоминан"],
        "monitoring_automation": ["монитор", "периодическ", "уведом", "отслеж"],
        "task_management": ["задач", "тикет", "jira", "project", "исуп"],
        "reporting_export": ["отчет", "отчёт", "excel", "выгруз", "экспорт"],
        "summarization": ["саммари", "сводк", "кратк", "итог"],
        "information_search": ["найди", "поиск", "собери информац", "контакты"],
        "data_analysis": ["анализ данных", "таблиц", "sql", "метрик"],
        "text_generation": ["напиши", "сформулируй", "письмо", "отзыв"],
        "knowledge_explanation": ["объясни", "расскажи", "почему", "что такое"],
        "non_work_general": [
            "поболта",
            "пообща",
            "анекдот",
            "шутк",
            "космос",
            "фильм",
            "сериал",
            "рецепт",
        ],
    }
    lowered = query.lower()
    scores = {
        category: sum(keyword in lowered for keyword in keywords)
        for category, keywords in groups.items()
    }
    best_score = max(scores.values(), default=0)
    leaders = [
        category for category, score in scores.items() if score == best_score
    ]
    if best_score == 0 or len(leaders) != 1:
        return "other", 0.3, "low"
    category = leaders[0]
    confidence = 0.7 if best_score >= 2 else 0.6
    if category in {
        "monitoring_automation",
        "task_management",
        "calendar_planning",
        "reporting_export",
    }:
        potential = "high"
    elif category in {"knowledge_explanation", "non_work_general"}:
        potential = "low"
    else:
        potential = "medium"
    return category, confidence, potential


async def analyze_event(
    data: dict[str, Any],
    known_scenarios: list[dict[str, Any]],
) -> dict[str, Any]:
    try:
        module = importlib.import_module("app.analytics.public")
        schemas = importlib.import_module("app.analytics.schemas")
    except ModuleNotFoundError as exc:
        if exc.name not in {
            "app.analytics",
            "app.analytics.public",
            "app.analytics.schemas",
        }:
            raise
        module = None

    if module is not None:
        analysis_input = schemas.AnalysisInput.model_validate(data)
        scenario_inputs = [
            schemas.KnownScenario.model_validate(item)
            for item in known_scenarios
        ]
        result = await module.analyze_event(
            analysis_input,
            scenario_inputs,
        )
        if hasattr(result, "model_dump"):
            return result.model_dump(mode="json")
        return dict(result)

    query, warnings = _normalize_query(data.get("messages", []))
    category, confidence, potential = _fallback_category(query)
    problems: list[str] = []
    total_context_chars = sum(
        len(str(message.get("content", "")))
        for message in data.get("messages", [])
    )
    prompt_tokens = data.get("prompt_tokens")
    if context_exceeds_supported_limit(
        total_context_chars=total_context_chars,
        prompt_tokens=int(prompt_tokens) if prompt_tokens is not None else None,
    ):
        problems.append("oversized_context")
    if confidence < 0.65:
        problems.append("low_classification_confidence")
    if category == "other":
        problems.append("unclassified")
    warnings.append("llm_unavailable")
    return {
        "effective_query": query,
        "category": category,
        "classification_confidence": confidence,
        "scenario_id": None,
        "scenario_confidence": None,
        "query_problem_reasons": problems,
        "automation_potential": potential,
        "warnings": warnings,
        "classifier_version": "backend-fallback-v1",
    }


async def discover_scenarios(
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    try:
        module = importlib.import_module("app.analytics.public")
        schemas = importlib.import_module("app.analytics.schemas")
    except ModuleNotFoundError as exc:
        if exc.name not in {
            "app.analytics",
            "app.analytics.public",
            "app.analytics.schemas",
        }:
            raise
        module = None

    if module is not None:
        scenario_records = [
            schemas.ScenarioInputRecord.model_validate(item)
            for item in records
        ]
        result = await module.discover_scenarios(scenario_records)
        if hasattr(result, "model_dump"):
            return result.model_dump(mode="json")
        return dict(result)

    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        if record["category"] != "other":
            grouped.setdefault(record["category"], []).append(record)

    scenarios = []
    unclustered: list[str] = []
    for category, items in sorted(grouped.items()):
        if len(items) < 3:
            unclustered.extend(str(item["event_id"]) for item in items)
            continue
        representative = [item["effective_query"] for item in items[:10]]
        scenarios.append(
            {
                "category": category,
                "name": f"Сценарий: {representative[0][:60]}",
                "summary": representative[0],
                "representative_queries": representative,
                "member_event_ids": [str(item["event_id"]) for item in items],
                "common_problems": [],
                "automation_potential": "medium",
                "suggested_action": "Провести ручной анализ сценария",
            }
        )
    return {
        "scenarios": scenarios,
        "unclustered_event_ids": unclustered,
        "algorithm_version": "backend-fallback-v1",
    }

