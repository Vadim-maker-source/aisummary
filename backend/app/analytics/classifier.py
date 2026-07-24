"""Category classification: LLM-first with a deterministic rule-based fallback.

Rule-based fallback (role file section 6.2):

1. lower-case the query;
2. count how many distinct keyword stems of each category appear;
3. pick the category with the highest count;
4. single leader -> confidence 0.70 if score >= 2, else 0.60;
5. tie or zero score -> ``other`` with confidence 0.30;
6. automation potential comes from the category mapping.

LLM path (00_SHARED_CONTRACT.md section 8.1): send only ``classifier_text``,
require strict JSON, validate with Pydantic. On timeout / HTTP error ->
``llm_unavailable`` + fallback; on invalid JSON / schema -> ``llm_invalid_response``
+ fallback. When the endpoint is simply not configured we use the fallback
silently (offline mode is not an error).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from . import llm_client
from .categories import CATEGORY_KEYWORDS, automation_for
from .prompts import LLM_ALLOWED_PROBLEM_REASONS, build_classification_messages
from .schemas import (
    AnalyticsWarning,
    AutomationPotential,
    Category,
    LLMClassification,
    QueryProblemReason,
)

LOW_CONFIDENCE_THRESHOLD = 0.65

_CONFIDENCE_STRONG = 0.70
_CONFIDENCE_WEAK = 0.60
_CONFIDENCE_OTHER = 0.30

_LLM_ALLOWED_REASONS = {QueryProblemReason(r) for r in LLM_ALLOWED_PROBLEM_REASONS}
_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.IGNORECASE | re.DOTALL)


@dataclass
class ClassificationOutcome:
    category: Category
    confidence: float
    automation_potential: AutomationPotential
    llm_problem_reasons: List[QueryProblemReason] = field(default_factory=list)
    warnings: List[AnalyticsWarning] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Rule-based fallback
# --------------------------------------------------------------------------- #
def rule_based_classify(query: str) -> Tuple[Category, float]:
    text = (query or "").lower()
    scores = {
        category: sum(1 for stem in stems if stem in text)
        for category, stems in CATEGORY_KEYWORDS.items()
    }

    max_score = max(scores.values()) if scores else 0
    if max_score == 0:
        return Category.other, _CONFIDENCE_OTHER

    # A short request that simultaneously activates three or more unrelated
    # task types is a multi-intent request, not a reliable single category.
    positive_categories = sum(1 for score in scores.values() if score > 0)
    if positive_categories >= 3 and max_score <= 2:
        return Category.other, _CONFIDENCE_OTHER

    leaders = [category for category, score in scores.items() if score == max_score]
    if len(leaders) != 1:
        return Category.other, _CONFIDENCE_OTHER

    leader = leaders[0]
    confidence = _CONFIDENCE_STRONG if max_score >= 2 else _CONFIDENCE_WEAK
    return leader, confidence


def _fallback_outcome(query: str, warnings: List[AnalyticsWarning]) -> ClassificationOutcome:
    category, confidence = rule_based_classify(query)
    return ClassificationOutcome(
        category=category,
        confidence=confidence,
        automation_potential=automation_for(category),
        llm_problem_reasons=[],
        warnings=warnings,
    )


# --------------------------------------------------------------------------- #
# LLM response parsing
# --------------------------------------------------------------------------- #
def _extract_json_object(text: str) -> Optional[dict]:
    if not text:
        return None
    stripped = text.strip()

    fenced = _JSON_FENCE_RE.search(stripped)
    if fenced:
        candidate = fenced.group(1)
    else:
        start = stripped.find("{")
        end = stripped.rfind("}")
        candidate = stripped[start : end + 1] if start != -1 and end > start else stripped

    try:
        obj = json.loads(candidate)
    except (ValueError, TypeError):
        return None
    return obj if isinstance(obj, dict) else None


def parse_classification(content: str) -> Optional[LLMClassification]:
    obj = _extract_json_object(content)
    if obj is None:
        return None
    try:
        return LLMClassification.model_validate(obj)
    except Exception:
        return None


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #
async def classify(classifier_text: str) -> ClassificationOutcome:
    # Offline mode: not configured, or nothing to classify -> silent fallback.
    if not classifier_text.strip() or not llm_client.is_configured():
        return _fallback_outcome(classifier_text, [])

    try:
        content = await llm_client.chat_completion(build_classification_messages(classifier_text))
    except llm_client.LLMError:
        return _fallback_outcome(classifier_text, [AnalyticsWarning.llm_unavailable])

    parsed = parse_classification(content)
    if parsed is None:
        return _fallback_outcome(classifier_text, [AnalyticsWarning.llm_invalid_response])

    llm_problems = [
        reason for reason in parsed.problem_reasons if reason in _LLM_ALLOWED_REASONS
    ]
    return ClassificationOutcome(
        category=parsed.category,
        confidence=float(parsed.confidence),
        # Automation potential is a business rule, not a model prediction.
        # Keeping it deterministic prevents the same category from receiving
        # different values across requests or model versions.
        automation_potential=automation_for(parsed.category),
        llm_problem_reasons=llm_problems,
        warnings=[],
    )
