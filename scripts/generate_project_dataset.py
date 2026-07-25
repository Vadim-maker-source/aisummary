"""Generate the reproducible Prompt Radar demo and validation datasets.

The scenario catalog is the source of business use cases. This script enriches
those use cases with dimensions and outcomes needed by the dashboard, adds the
two categories missing from the analyst delivery, and creates deterministic
query-quality edge cases that the real backend can verify.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SOURCE_CATALOG_PATH = DATA_DIR / "scenario_catalog_source.json"
CATALOG_PATH = DATA_DIR / "scenario_catalog.json"
SEED = 20260725
BASE_DAY = datetime(2026, 6, 3, 8, 0, tzinfo=timezone.utc)
SOURCE_TOPIC_COUNT = 31
DEMO_VARIANTS = 20
VALIDATION_VARIANTS = 5
OVERSIZED_TOPIC_COUNT = 12
SUPPORTED_CONTEXT_TOKENS = 100_000
OVERSIZED_PROMPT_TOKENS = 100_001
OVERSIZED_CONTEXT_CHARS = 410_000

MODELS = ("DeepSeek-V4-Flash", "GigaChat-Pro", "YandexGPT-4")
AGENTS = (
    "mail-copilot",
    "knowledge-assistant",
    "work-management-agent",
    "developer-assistant",
)

CATEGORY_CUES = {
    "text_generation": "Напиши и сформулируй текст",
    "information_search": "Найди через поиск и собери информацию",
    "summarization": "Подготовь краткое саммари, сводку и итоги",
    "data_analysis": "Проведи анализ данных, таблицы, SQL и метрик",
    "code_assistance": "Помоги с кодом Python, traceback и FastAPI",
    "reporting_export": "Сформируй отчёт, выгрузку и экспорт в Excel",
    "task_management": "Создай задачу или тикет Jira Project",
    "monitoring_automation": "Настрой периодический мониторинг, отслеживание и уведомление",
    "calendar_planning": "Запланируй встречу в календаре, найди слот и расписание",
    "knowledge_explanation": "Объясни, расскажи почему и что это такое",
    "non_work_general": "Давай поболтаем и пообщаемся о фильме",
    "other": "Неясная формулировка без деталей",
}

CATEGORY_DIMENSIONS = {
    "text_generation": ("Продажи", "Аккаунт-менеджеры"),
    "information_search": ("Корпоративные сервисы", "База знаний"),
    "summarization": ("Корпоративные сервисы", "Совместная работа"),
    "data_analysis": ("Аналитика", "BI"),
    "code_assistance": ("ИТ", "Разработка"),
    "reporting_export": ("Аналитика", "Отчётность"),
    "task_management": ("Проектный бизнес", "Управление проектами"),
    "monitoring_automation": ("Корпоративные сервисы", "Автоматизация"),
    "calendar_planning": ("Корпоративные сервисы", "Офис руководителя"),
    "knowledge_explanation": ("Корпоративные сервисы", "Обучение"),
    "non_work_general": ("Общие вопросы", "Вне рабочих процессов"),
    "other": ("Не определено", "Не определено"),
}

AMBIGUOUS_QUERIES = {
    "summarization": "Сделай короткие итоги того материала.",
    "information_search": "Найди по ним всё нужное.",
    "monitoring_automation": "Проверяй это регулярно и сообщай, если что.",
    "reporting_export": "Выгрузи это в привычном формате.",
    "text_generation": "Оформи это так же, как обычно.",
    "task_management": "Сделай с этой задачей то же самое.",
    "calendar_planning": "Поставь это туда же на удобное время.",
    "data_analysis": "Посмотри эти данные и скажи, что там.",
    "knowledge_explanation": "Объясни мне вот это.",
    "code_assistance": "Исправь это в коде.",
    "non_work_general": "Давай поговорим об этом.",
    "other": "Сделай что-нибудь полезное.",
}

MULTI_INTENT_TAILS = {
    "summarization": "и после этого создай встречу в календаре.",
    "information_search": "и после этого выгрузи найденное в Excel.",
    "monitoring_automation": "и после этого подготовь разовый отчёт.",
    "reporting_export": "и затем настрой еженедельный мониторинг результата.",
    "text_generation": "и затем создай задачу в Jira для согласования.",
    "task_management": "и после этого напиши письмо исполнителю.",
    "calendar_planning": "и после этого выгрузи список участников в Excel.",
    "data_analysis": "и после этого создай задачу по найденным отклонениям.",
    "knowledge_explanation": "и после этого запланируй обучающую встречу.",
    "code_assistance": "и после этого создай задачу в Jira.",
    "non_work_general": "и после этого составь рабочий отчёт.",
    "other": "и после этого выгрузи результат в Excel.",
}

EXTRA_TOPICS = (
    {
        "source_topic_id": None,
        "supplemental_topic_id": "S04",
        "scenario_label": "python_traceback_debugging",
        "scenario_name": "Разбор ошибок Python",
        "expected_category": "code_assistance",
        "definition": "Помощь с диагностикой traceback и исправлением Python-кода.",
        "representative_queries": [
            "Разбери Python traceback, найди причину ошибки и предложи исправление кода.",
            "Помоги отладить исключение в Python и объясни проблемную строку.",
            "Исправь ошибку в функции Python по приложенному traceback.",
        ],
        "validation_queries": [
            "Почему этот Python-код падает с traceback и как его исправить?",
            "Проведи отладку исключения Python и покажи корректный вариант функции.",
        ],
        "is_supplemental": True,
    },
    {
        "source_topic_id": None,
        "supplemental_topic_id": "S05",
        "scenario_label": "api_backend_implementation",
        "scenario_name": "Разработка backend API",
        "expected_category": "code_assistance",
        "definition": "Разработка и улучшение backend API и интеграций.",
        "representative_queries": [
            "Напиши endpoint FastAPI с валидацией Pydantic и обработкой ошибок.",
            "Помоги реализовать асинхронный API на FastAPI и PostgreSQL.",
            "Проведи рефакторинг backend-кода API и добавь тесты.",
        ],
        "validation_queries": [
            "Реализуй безопасный FastAPI endpoint и тесты для него.",
            "Как улучшить этот backend API на Python и PostgreSQL?",
        ],
        "is_supplemental": True,
    },
    {
        "source_topic_id": None,
        "supplemental_topic_id": "S06",
        "scenario_label": "unclassified_request",
        "scenario_name": "Неопределённый запрос",
        "expected_category": "other",
        "definition": "Запросы, для которых нельзя надёжно определить рабочую задачу.",
        "representative_queries": [
            "Сделай что-нибудь полезное.",
            "Помоги с этим без дополнительных пояснений.",
            "Нужно получить какой-нибудь результат.",
        ],
        "validation_queries": [
            "Сделай что-нибудь.",
            "Помоги мне с этим.",
        ],
        "is_supplemental": True,
    },
)

CONTEXT_SENTENCE = (
    "Синтетический корпоративный контекст содержит документы, историю "
    "переписки, роли участников и служебные метаданные без реальных "
    "персональных данных. "
)


def _read_catalog() -> list[dict[str, Any]]:
    catalog = json.loads(SOURCE_CATALOG_PATH.read_text(encoding="utf-8"))
    for topic in catalog:
        if topic["scenario_label"] == "non_work_conversation":
            topic["expected_category"] = "non_work_general"
    existing = {topic["scenario_label"] for topic in catalog}
    catalog.extend(
        dict(topic)
        for topic in EXTRA_TOPICS
        if topic["scenario_label"] not in existing
    )
    return catalog


def _topic_key(topic: dict[str, Any]) -> str:
    return str(
        topic.get("source_topic_id")
        or topic.get("supplemental_topic_id")
        or topic["scenario_label"]
    ).lower()


def _query_seed(topic: dict[str, Any], variant: int, *, validation: bool) -> str:
    key = "validation_queries" if validation else "representative_queries"
    seeds = [str(value).strip() for value in topic.get(key, []) if str(value).strip()]
    if not seeds:
        seeds = [str(topic["definition"]).strip()]
    return seeds[variant % len(seeds)].rstrip(".!?")


def _regular_query(
    topic: dict[str, Any],
    variant: int,
    *,
    validation: bool,
) -> str:
    base = _query_seed(
        topic,
        0 if validation else variant,
        validation=validation,
    )
    cue = CATEGORY_CUES[topic["expected_category"]]
    if validation:
        templates = (
            f"{cue}: {base}.",
            f"{cue}: пожалуйста, {base[:1].lower() + base[1:]}.",
            f"{cue}: {base}. Укажи результат кратко.",
            f"{cue}: {base}. Перечисли использованные источники.",
            f"{cue}: {base}. Не придумывай отсутствующие сведения.",
        )
    else:
        templates = (
            f"{base}.",
            f"Пожалуйста, {base[:1].lower() + base[1:]}.",
            f"{base}. Укажи результат кратко.",
            f"Рабочая задача: {base[:1].lower() + base[1:]}.",
            f"{base}. Перечисли следующие действия.",
            f"Нужно выполнить сценарий «{topic['scenario_name']}»: {base[:1].lower() + base[1:]}.",
            f"{base}. Используй только доступные корпоративные данные.",
            f"Помоги сотруднику: {base[:1].lower() + base[1:]}.",
        )
    return templates[variant % len(templates)]


def _demo_query(
    topic: dict[str, Any],
    topic_index: int,
    variant: int,
) -> tuple[str, str | None]:
    source_topic = topic_index < SOURCE_TOPIC_COUNT
    base = _regular_query(topic, variant, validation=False)
    if source_topic and variant == 16:
        return (
            f"{base} Используй те же параметры и список получателей, что в прошлый раз.",
            "missing_context",
        )
    if source_topic and variant == 17:
        return AMBIGUOUS_QUERIES[topic["expected_category"]], "ambiguous"
    if source_topic and variant == 18:
        return f"{base.rstrip('.')} {MULTI_INTENT_TAILS[topic['expected_category']]}", "multiple_intents"
    if topic_index < OVERSIZED_TOPIC_COUNT and variant == 19:
        return base, "oversized_context"
    return base, None


def _message_content(
    query: str,
    *,
    index: int,
    oversized: bool,
) -> str:
    if oversized:
        context = (
            CONTEXT_SENTENCE
            * math.ceil(OVERSIZED_CONTEXT_CHARS / len(CONTEXT_SENTENCE))
        )[:OVERSIZED_CONTEXT_CHARS]
        return f"<context>{context}</context><user_query>{query}</user_query>"
    if index % 4 == 0:
        context = CONTEXT_SENTENCE * (2 + index % 3)
        return f"<context>{context}</context><user_query>{query}</user_query>"
    return query


def _day_for(topic_index: int, variant: int) -> int:
    fraction = (variant + 1) / (DEMO_VARIANTS + 1)
    trend = topic_index % 3
    if trend == 0:
        return min(48, int(48 * math.sqrt(fraction)))
    if trend == 1:
        return min(48, int(48 * (fraction**2)))
    return (topic_index * 13 + variant * 11) % 49


def _response(
    topic: dict[str, Any],
    index: int,
    *,
    oversized: bool,
) -> tuple[dict[str, Any] | None, str, int | None, int | None, bool | None, int | None]:
    answered = index % 6 == 0 or oversized
    if not answered:
        return None, "unknown", None, None, None, None
    failed = index % 37 == 0
    prompt_tokens = OVERSIZED_PROMPT_TOKENS if oversized else 1_500 + index % 700
    completion_tokens = 140 + index % 90
    response = {
        "content": (
            f"Синтетический результат сценария «{topic['scenario_name']}». "
            "Указаны выводы, ограничения и следующие действия."
        ),
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }
    return (
        response,
        "error" if failed else "success",
        1_200 + index % 23 * 180,
        2 if failed else 4 + index % 2,
        not failed,
        0 if failed else 12 + index % 8 * 6,
    )


def _event(
    topic: dict[str, Any],
    topic_index: int,
    variant: int,
    query: str,
    problem_reason: str | None,
    *,
    split: str,
) -> dict[str, Any]:
    index = topic_index * 100 + variant
    oversized = problem_reason == "oversized_context"
    direction, team = CATEGORY_DIMENSIONS[topic["expected_category"]]
    response, status, latency, rating, completed, minutes = _response(
        topic,
        index,
        oversized=oversized,
    )
    occurred_at = BASE_DAY + timedelta(
        days=_day_for(topic_index, variant) if split == "demo" else variant * 7,
        hours=index % 10,
        minutes=index * 7 % 60,
    )
    prefix = "demo" if split == "demo" else "val"
    messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": "Ты — корпоративный ИИ-ассистент. Не выдумывай факты.",
        }
    ]
    if index % 9 == 0:
        messages.extend(
            [
                {"role": "user", "content": "Помоги с рабочей задачей."},
                {"role": "assistant", "content": "Уточните задачу и ожидаемый результат."},
            ]
        )
    messages.append(
        {
            "role": "user",
            "content": _message_content(query, index=index, oversized=oversized),
        }
    )
    return {
        "external_id": f"{prefix}-{_topic_key(topic)}-v{variant + 1:02d}",
        "agent_id": AGENTS[topic_index % len(AGENTS)],
        "user_id": f"user-{index % 53 + 1:03d}",
        "team": team,
        "direction": direction,
        "is_synthetic": True,
        "occurred_at": occurred_at.isoformat().replace("+00:00", "Z"),
        "request": {
            "model": MODELS[index % len(MODELS)],
            "stream": bool(index % 2),
            "messages": messages,
        },
        "response": response,
        "execution_status": status,
        "latency_ms": latency,
        "rating": rating,
        "task_completed": completed,
        "estimated_minutes_saved": minutes,
    }


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as output:
        for row in rows:
            output.write(json.dumps(row, ensure_ascii=False) + "\n")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate() -> dict[str, Any]:
    catalog = _read_catalog()
    demo_events: list[dict[str, Any]] = []
    validation_events: list[dict[str, Any]] = []
    demo_truth: list[dict[str, Any]] = []
    demo_labels: dict[str, dict[str, str]] = {}
    validation_labels: list[dict[str, str]] = []
    manifest_rows: list[dict[str, Any]] = []

    for topic_index, topic in enumerate(catalog):
        for variant in range(DEMO_VARIANTS):
            query, reason = _demo_query(topic, topic_index, variant)
            event = _event(
                topic,
                topic_index,
                variant,
                query,
                reason,
                split="demo",
            )
            demo_events.append(event)
            demo_labels[event["external_id"]] = {
                "category": topic["expected_category"],
                "scenario_label": topic["scenario_label"],
            }
            demo_truth.append(
                {
                    "external_id": event["external_id"],
                    "query": query,
                    "category": topic["expected_category"],
                    "scenario_label": topic["scenario_label"],
                    "supplied_topic": topic_index < SOURCE_TOPIC_COUNT,
                    "intended_problem_reason": reason,
                }
            )
            manifest_rows.append(
                {
                    "external_id": event["external_id"],
                    "split": "demo",
                    "source_topic_id": topic.get("source_topic_id"),
                    "supplemental_topic_id": topic.get("supplemental_topic_id"),
                    "expected_category": topic["expected_category"],
                    "expected_scenario_label": topic["scenario_label"],
                    "variant_type": reason or "regular",
                    "intended_problem_reason": reason,
                    "effective_query": query,
                    "last_user_content_chars": len(
                        event["request"]["messages"][-1]["content"]
                    ),
                }
            )

        for variant in range(VALIDATION_VARIANTS):
            query = _regular_query(topic, variant, validation=True)
            event = _event(
                topic,
                topic_index,
                variant,
                query,
                None,
                split="validation",
            )
            validation_events.append(event)
            validation_labels.append(
                {
                    "external_id": event["external_id"],
                    "query": query,
                    "expected_category": topic["expected_category"],
                    "expected_scenario_label": topic["scenario_label"],
                }
            )
            manifest_rows.append(
                {
                    "external_id": event["external_id"],
                    "split": "validation",
                    "source_topic_id": topic.get("source_topic_id"),
                    "supplemental_topic_id": topic.get("supplemental_topic_id"),
                    "expected_category": topic["expected_category"],
                    "expected_scenario_label": topic["scenario_label"],
                    "variant_type": "independent_validation",
                    "intended_problem_reason": None,
                    "effective_query": query,
                    "last_user_content_chars": len(
                        event["request"]["messages"][-1]["content"]
                    ),
                }
            )

    _write_json(CATALOG_PATH, catalog)
    _write_jsonl(DATA_DIR / "demo_events.jsonl", demo_events)
    _write_jsonl(DATA_DIR / "validation_events.jsonl", validation_events)
    _write_json(DATA_DIR / "demo_labels.json", demo_labels)
    _write_json(DATA_DIR / "demo_truth.json", demo_truth)
    _write_json(DATA_DIR / "validation_labels.json", validation_labels)
    _write_json(
        DATA_DIR / "generation_manifest.json",
        {
            "generator": "scripts/generate_project_dataset.py",
            "seed": SEED,
            "generated_at": "2026-07-25T00:00:00Z",
            "demo_count": len(demo_events),
            "validation_count": len(validation_events),
            "records": manifest_rows,
        },
    )

    category_distribution = Counter(
        row["expected_category"]
        for row in manifest_rows
        if row["split"] == "demo"
    )
    files = {}
    for name in (
        "demo_events.jsonl",
        "validation_events.jsonl",
        "demo_labels.json",
        "demo_truth.json",
        "validation_labels.json",
        "scenario_catalog.json",
        "generation_manifest.json",
    ):
        path = DATA_DIR / name
        files[name] = {
            "sha256": _sha256(path),
            "bytes": path.stat().st_size,
        }
    metadata = {
        "seed": SEED,
        "demo_count": len(demo_events),
        "validation_count": len(validation_events),
        "source_topic_count": SOURCE_TOPIC_COUNT,
        "supplemental_topic_count": len(catalog) - SOURCE_TOPIC_COUNT,
        "category_count": len(category_distribution),
        "categories": sorted(category_distribution),
        "demo_category_distribution": dict(sorted(category_distribution.items())),
        "scenario_count_including_other": len(
            {topic["scenario_label"] for topic in catalog}
        ),
        "timestamp_span_days": 49,
        "oversized_count": sum(
            row["intended_problem_reason"] == "oversized_context"
            for row in manifest_rows
        ),
        "ambiguous_count": sum(
            row["intended_problem_reason"] == "ambiguous"
            for row in manifest_rows
        ),
        "multiple_intents_count": sum(
            row["intended_problem_reason"] == "multiple_intents"
            for row in manifest_rows
        ),
        "missing_context_count": sum(
            row["intended_problem_reason"] == "missing_context"
            for row in manifest_rows
        ),
        "files": files,
    }
    _write_json(DATA_DIR / "dataset_metadata.json", metadata)
    _write_json(
        DATA_DIR / "demo_manifest.json",
        {
            "profile": "demo",
            "events": len(demo_events),
            "source_topics": SOURCE_TOPIC_COUNT,
            "supplemental_topics": len(catalog) - SOURCE_TOPIC_COUNT,
            "target_max_supported_prompt_tokens": SUPPORTED_CONTEXT_TOKENS,
            "oversized_edge_prompt_tokens": OVERSIZED_PROMPT_TOKENS,
            "is_synthetic": True,
        },
    )
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    print(json.dumps(generate(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
