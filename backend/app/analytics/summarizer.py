"""Name & summarize a discovered cluster (LLM-first, deterministic fallback).

LLM path returns name / summary / common_problems / automation_potential /
suggested_action. Output is sanitised: name <= 80 chars and must not contain
the word "Кластер"; summary and suggested_action <= 500 chars.

Fallback (00_SHARED_CONTRACT.md section 8.2):
- name: ``"Сценарий: " + first 60 chars of the first representative query``;
- summary: the first representative query;
- common_problems: ``[]``;
- suggested_action: ``"Провести ручной анализ сценария"``.
The contract fallback does not specify automation potential, so we use the
deterministic category mapping.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from . import llm_client
from .categories import automation_for
from .classifier import _extract_json_object
from .prompts import build_summary_messages
from .schemas import AutomationPotential, Category, LLMScenarioSummary

NAME_MAX = 80
SUMMARY_MAX = 500
ACTION_MAX = 500
_FALLBACK_ACTION = "Провести ручной анализ сценария"
_FORBIDDEN_NAME_TOKEN = "кластер"


@dataclass
class ScenarioMeta:
    name: str
    summary: str
    common_problems: List[str] = field(default_factory=list)
    automation_potential: AutomationPotential = AutomationPotential.low
    suggested_action: str = _FALLBACK_ACTION


def _fallback_name(representative_queries: List[str]) -> str:
    first = representative_queries[0] if representative_queries else ""
    return ("Сценарий: " + first[:60]).strip()


def fallback_meta(category: Category, representative_queries: List[str]) -> ScenarioMeta:
    first = representative_queries[0] if representative_queries else ""
    return ScenarioMeta(
        name=_fallback_name(representative_queries),
        summary=first,
        common_problems=[],
        automation_potential=automation_for(category),
        suggested_action=_FALLBACK_ACTION,
    )


def parse_summary(content: str) -> Optional[LLMScenarioSummary]:
    obj = _extract_json_object(content)
    if obj is None:
        return None
    try:
        return LLMScenarioSummary.model_validate(obj)
    except Exception:
        return None


def _sanitize(
    parsed: LLMScenarioSummary,
    category: Category,
    representative_queries: List[str],
) -> ScenarioMeta:
    name = (parsed.name or "").strip()
    if not name or _FORBIDDEN_NAME_TOKEN in name.lower():
        name = _fallback_name(representative_queries)
    name = name[:NAME_MAX].strip()

    summary = (parsed.summary or "").strip()[:SUMMARY_MAX]
    if not summary:
        summary = (representative_queries[0] if representative_queries else "")[:SUMMARY_MAX]

    action = (parsed.suggested_action or "").strip()[:ACTION_MAX] or _FALLBACK_ACTION

    common_problems = [str(p).strip() for p in parsed.common_problems if str(p).strip()]

    return ScenarioMeta(
        name=name,
        summary=summary,
        common_problems=common_problems,
        automation_potential=automation_for(category),
        suggested_action=action,
    )


async def summarize_cluster(
    category: Category,
    representative_queries: List[str],
) -> ScenarioMeta:
    if representative_queries and llm_client.is_configured():
        try:
            content = await llm_client.chat_completion(
                build_summary_messages(category, representative_queries)
            )
        except llm_client.LLMError:
            content = None
        if content is not None:
            parsed = parse_summary(content)
            if parsed is not None:
                return _sanitize(parsed, category, representative_queries)

    return fallback_meta(category, representative_queries)
