"""Prompt builders for the LLM paths (classification & scenario summary).

Prompts are intentionally strict: the model must reply with a single JSON
object and nothing else. The allowed enum values are injected so the model
cannot invent categories or reasons outside the contract.
"""

from __future__ import annotations

from typing import Dict, List

from .categories import ALLOWED_CATEGORIES
from .schemas import Category

# Problem reasons the LLM is allowed to contribute (deterministic reasons are
# added by the module itself, never by the model).
LLM_ALLOWED_PROBLEM_REASONS = [
    "ambiguous",
    "missing_context",
    "multiple_intents",
    "unsupported_task",
]

_AUTOMATION_VALUES = ["low", "medium", "high"]


def build_classification_messages(classifier_text: str) -> List[Dict[str, str]]:
    categories = ", ".join(c.value for c in ALLOWED_CATEGORIES)
    reasons = ", ".join(LLM_ALLOWED_PROBLEM_REASONS)
    automation = ", ".join(_AUTOMATION_VALUES)

    system = (
        "Ты — детерминированный классификатор пользовательских запросов к "
        "корпоративным ИИ-агентам. Ты анализируешь ТОЛЬКО сам запрос "
        "пользователя, а не ответ агента. Никогда не утверждай, что ответ "
        "агента неправильный или содержит галлюцинации. Верни строго один "
        "JSON-объект без пояснений и без markdown."
    )
    user = (
        "Классифицируй запрос пользователя.\n\n"
        f"Запрос:\n\"\"\"\n{classifier_text}\n\"\"\"\n\n"
        "Верни JSON строго такой формы:\n"
        "{\n"
        '  "category": <одна из категорий>,\n'
        '  "confidence": <число от 0 до 1>,\n'
        '  "problem_reasons": [<подмножество допустимых причин, может быть пустым>],\n'
        '  "automation_potential": <low|medium|high>\n'
        "}\n\n"
        f"Допустимые category: {categories}.\n"
        f"Допустимые problem_reasons: {reasons}.\n"
        f"Допустимые automation_potential: {automation}.\n"
        "Если запрос не подходит ни под одну содержательную категорию, верни "
        '"other". Ответ — только JSON.'
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def build_summary_messages(category: Category, representative_queries: List[str]) -> List[Dict[str, str]]:
    queries_block = "\n".join(f"- {q}" for q in representative_queries)
    automation = ", ".join(_AUTOMATION_VALUES)

    system = (
        "Ты — аналитик, который описывает сценарии использования корпоративных "
        "ИИ-агентов на основе похожих пользовательских запросов. Ты описываешь "
        "НАМЕРЕНИЯ пользователей, а не качество ответов агента, и никогда не "
        "утверждаешь, что ответ агента неправильный. Верни строго один "
        "JSON-объект без markdown."
    )
    user = (
        f"Категория сценария: {category.value}.\n"
        "Репрезентативные запросы пользователей этого сценария:\n"
        f"{queries_block}\n\n"
        "Опиши сценарий и верни JSON строго такой формы:\n"
        "{\n"
        '  "name": <короткое название, до 80 символов, без слова «Кластер»>,\n'
        '  "summary": <описание намерения пользователей, до 500 символов>,\n'
        '  "common_problems": [<типичные проблемы формулировок, может быть пустым>],\n'
        '  "automation_potential": <low|medium|high>,\n'
        '  "suggested_action": <что стоит автоматизировать/улучшить, до 500 символов>\n'
        "}\n\n"
        f"Допустимые automation_potential: {automation}.\n"
        "Название должно отражать суть запросов, а не быть словом «Кластер». "
        "Ответ — только JSON."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
