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

from typing import Iterable, List

from .classifier import LOW_CONFIDENCE_THRESHOLD
from .schemas import Category, QueryProblemReason

# Canonical order == enum declaration order.
_PROBLEM_ORDER: List[QueryProblemReason] = list(QueryProblemReason)


def build_problem_reasons(
    *,
    category: Category,
    confidence: float,
    extraction_problems: Iterable[QueryProblemReason],
    llm_problems: Iterable[QueryProblemReason],
) -> List[QueryProblemReason]:
    collected = set(extraction_problems) | set(llm_problems)

    if confidence < LOW_CONFIDENCE_THRESHOLD:
        collected.add(QueryProblemReason.low_classification_confidence)
    if category == Category.other:
        collected.add(QueryProblemReason.unclassified)

    return [reason for reason in _PROBLEM_ORDER if reason in collected]
