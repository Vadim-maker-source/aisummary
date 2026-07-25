"""Assemble the ordered, de-duplicated list of query problem reasons.

Deterministic reasons:
- ``oversized_context``          -> prompt_tokens > 100000, or more than
                                    400000 context characters when exact usage
                                    is unavailable (detected during extraction)
- ``low_classification_confidence`` -> confidence < 0.65
- ``unclassified``               -> category == other

The LLM may additionally contribute ``ambiguous``, ``missing_context``,
``multiple_intents`` and ``unsupported_task`` (already filtered by the
classifier). The final list is de-duplicated and ordered by the canonical
``QueryProblemReason`` enum declaration order.
"""

from __future__ import annotations

import re
from typing import Iterable, List

from .classifier import LOW_CONFIDENCE_THRESHOLD
from .schemas import Category, QueryProblemReason

# Canonical order == enum declaration order.
_PROBLEM_ORDER: List[QueryProblemReason] = list(QueryProblemReason)

_MISSING_CONTEXT_PATTERNS = (
    re.compile(r"\bкак\s+в\s+прошл(?:ый|ом)\s+раз", re.IGNORECASE),
    re.compile(r"\bте\s+же\s+(?:параметры|настройки|данные|получатели)", re.IGNORECASE),
    re.compile(r"\bиз\s+(?:этого|того)\s+(?:файла|документа|материала)\b", re.IGNORECASE),
)
_VAGUE_REFERENCE_RE = re.compile(
    r"\b(?:это|этого|этой|эти|того|так\s+же|туда\s+же|по\s+ним|"
    r"привычном\s+формате|"
    r"всё\s+нужное|что-нибудь|что\s+нибудь)\b",
    re.IGNORECASE,
)
_ACTION_MARKERS = {
    "search": ("найд", "поиск", "собер", "информац"),
    "write": ("напиш", "сформулир", "ответ"),
    "schedule": ("встреч", "календар", "слот", "напоминан"),
    "export": ("выгруз", "экспорт", "excel", "отчёт", "отчет"),
    "monitor": ("монитор", "отслеж", "периодическ", "уведом"),
    "task": ("задач", "тикет", "jira", "project", "исуп"),
    "summarize": ("сводк", "саммари", "итог", "резюм"),
    "analyze": ("анализ", "метрик", "sql", "таблиц"),
}
_MULTI_INTENT_CONNECTOR_RE = re.compile(
    r"\b(?:и\s+после\s+этого|а\s+затем|и\s+затем|одновременно|"
    r"после\s+этого|а\s+также)\b",
    re.IGNORECASE,
)


def deterministic_query_problem_reasons(
    query: str,
) -> List[QueryProblemReason]:
    """Return query-quality problems that are safe to detect without an LLM.

    The rules intentionally use high-precision markers. They do not attempt to
    replace semantic LLM judgement; they make common corporate-log failures
    observable in offline and degraded modes.
    """

    text = re.sub(r"\s+", " ", query or "").strip()
    lowered = text.lower()
    reasons: set[QueryProblemReason] = set()

    if any(pattern.search(text) for pattern in _MISSING_CONTEXT_PATTERNS):
        reasons.add(QueryProblemReason.missing_context)

    if (
        len(text) <= 80
        and _VAGUE_REFERENCE_RE.search(text)
    ):
        reasons.add(QueryProblemReason.ambiguous)

    active_actions = sum(
        1
        for stems in _ACTION_MARKERS.values()
        if any(stem in lowered for stem in stems)
    )
    if active_actions >= 1 and _MULTI_INTENT_CONNECTOR_RE.search(text):
        reasons.add(QueryProblemReason.multiple_intents)

    return [
        reason
        for reason in _PROBLEM_ORDER
        if reason in reasons
    ]


def build_problem_reasons(
    *,
    query: str,
    category: Category,
    confidence: float,
    extraction_problems: Iterable[QueryProblemReason],
    llm_problems: Iterable[QueryProblemReason],
) -> List[QueryProblemReason]:
    collected = (
        set(extraction_problems)
        | set(llm_problems)
        | set(deterministic_query_problem_reasons(query))
    )

    if confidence < LOW_CONFIDENCE_THRESHOLD:
        collected.add(QueryProblemReason.low_classification_confidence)
    if category == Category.other:
        collected.add(QueryProblemReason.unclassified)

    return [reason for reason in _PROBLEM_ORDER if reason in collected]
