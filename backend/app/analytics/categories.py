"""Category enumeration helpers, rule-based keyword groups and the
category -> automation-potential mapping.

Keyword *stems* are matched as case-insensitive substrings against the
lower-cased query (see :mod:`analytics.classifier`). Stems intentionally omit
inflectional endings so that, e.g., ``"встреч"`` matches ``"встреча"``,
``"встречи"``, ``"встрече"`` …
"""

from __future__ import annotations

from typing import Dict, List

from .schemas import AutomationPotential, Category

# All categories that are allowed to be *predicted*. ``other`` is the fallback
# bucket and is always allowed as an output but never has keywords.
ALLOWED_CATEGORIES: List[Category] = list(Category)

# Ordered dict of keyword stems per category. Order is irrelevant for scoring
# (ties always collapse to ``other``) but kept stable for determinism.
CATEGORY_KEYWORDS: Dict[Category, List[str]] = {
    Category.calendar_planning: ["встреч", "календар", "слот", "переговорн", "напоминан"],
    Category.monitoring_automation: ["монитор", "периодическ", "уведом", "отслеж"],
    Category.task_management: ["задач", "тикет", "jira", "project", "исуп"],
    Category.reporting_export: ["отчет", "отчёт", "excel", "выгруз", "экспорт"],
    Category.summarization: ["саммари", "сводк", "кратк", "итог"],
    Category.information_search: ["найди", "поиск", "собери информац", "контакты"],
    Category.data_analysis: ["анализ данных", "таблиц", "sql", "метрик"],
    Category.text_generation: ["напиши", "сформулируй", "письмо", "отзыв"],
    Category.knowledge_explanation: ["объясни", "расскажи", "почему", "что такое"],
}

# Category -> automation potential (00_SHARED_CONTRACT.md / role file section 6.6)
_AUTOMATION_POTENTIAL: Dict[Category, AutomationPotential] = {
    Category.monitoring_automation: AutomationPotential.high,
    Category.task_management: AutomationPotential.high,
    Category.calendar_planning: AutomationPotential.high,
    Category.reporting_export: AutomationPotential.high,
    Category.text_generation: AutomationPotential.medium,
    Category.information_search: AutomationPotential.medium,
    Category.summarization: AutomationPotential.medium,
    Category.data_analysis: AutomationPotential.medium,
    Category.knowledge_explanation: AutomationPotential.low,
    Category.other: AutomationPotential.low,
}


def automation_for(category: Category) -> AutomationPotential:
    """Return the deterministic automation potential for a category."""

    return _AUTOMATION_POTENTIAL.get(category, AutomationPotential.low)
