"""Classification tests: rule-based fallback + LLM path (acceptance 5.4-5.5)."""

from __future__ import annotations

import pytest

from app.analytics import llm_client
from app.analytics.classifier import classify, rule_based_classify
from app.analytics.public import analyze_event
from app.analytics.schemas import (
    AnalysisInput,
    AnalyticsWarning,
    AutomationPotential,
    Category,
    Message,
    QueryProblemReason,
)


def _inp(content):
    return AnalysisInput(event_id="e", messages=[Message(role="user", content=content)])


# --------------------------------------------------------------------------- #
# Rule-based fallback (sync)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "query,expected",
    [
        ("Найди общий слот для встречи", Category.calendar_planning),
        ("Создай периодический мониторинг писем", Category.monitoring_automation),
        ("Добавь тикет в Jira", Category.task_management),
        ("Выгрузи отчёт в Excel", Category.reporting_export),
        ("Сделай краткое саммари документа", Category.summarization),
        ("Найди контакты клиента", Category.information_search),
        ("Проведи анализ данных таблицы", Category.data_analysis),
        ("Напиши деловое письмо", Category.text_generation),
        ("Объясни почему возникает ошибка", Category.knowledge_explanation),
        ("Поговорим о чём-нибудь", Category.other),
    ],
)
def test_rule_fallback_each_category(query, expected):
    category, _confidence = rule_based_classify(query)
    assert category == expected


def test_tie_produces_other():
    category, confidence = rule_based_classify("Найди и напиши")
    assert category == Category.other
    assert confidence == 0.30


def test_single_strong_leader_confidence():
    # score >= 2 -> 0.70
    _c, confidence = rule_based_classify("Найди общий слот для встречи")
    assert confidence == 0.70


def test_single_weak_leader_confidence():
    # score == 1 -> 0.60
    category, confidence = rule_based_classify("Составь SQL-запрос")
    assert category == Category.data_analysis
    assert confidence == 0.60


@pytest.mark.asyncio
async def test_tie_problem_reasons_via_analyze_event():
    result = await analyze_event(_inp("Найди и напиши"), [])
    assert result.category == Category.other
    assert result.classification_confidence == 0.30
    assert QueryProblemReason.low_classification_confidence in result.query_problem_reasons
    assert QueryProblemReason.unclassified in result.query_problem_reasons
    # canonical enum order: low_classification_confidence before unclassified
    assert result.query_problem_reasons == [
        QueryProblemReason.low_classification_confidence,
        QueryProblemReason.unclassified,
    ]


@pytest.mark.asyncio
async def test_low_confidence_problem_present_but_classified():
    result = await analyze_event(_inp("Составь SQL-запрос"), [])
    assert result.category == Category.data_analysis
    assert result.classification_confidence == 0.60
    assert QueryProblemReason.low_classification_confidence in result.query_problem_reasons
    assert QueryProblemReason.unclassified not in result.query_problem_reasons


@pytest.mark.asyncio
async def test_automation_potential_mapping():
    high = await analyze_event(_inp("Найди общий слот для встречи"), [])
    assert high.automation_potential == AutomationPotential.high
    low = await analyze_event(_inp("Объясни почему возникает ошибка"), [])
    assert low.automation_potential == AutomationPotential.low
    medium = await analyze_event(_inp("Напиши деловое письмо"), [])
    assert medium.automation_potential == AutomationPotential.medium


# --------------------------------------------------------------------------- #
# LLM path (mocked; never touches the network)
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_llm_success(monkeypatch):
    async def fake_completion(messages):
        return (
            '{"category": "calendar_planning", "confidence": 0.93, '
            '"problem_reasons": ["ambiguous"], "automation_potential": "high"}'
        )

    monkeypatch.setattr(llm_client, "is_configured", lambda: True)
    monkeypatch.setattr(llm_client, "chat_completion", fake_completion)

    outcome = await classify("Найди окно для общей встречи")
    assert outcome.category == Category.calendar_planning
    assert outcome.confidence == 0.93
    assert outcome.automation_potential == AutomationPotential.high
    assert QueryProblemReason.ambiguous in outcome.llm_problem_reasons
    assert outcome.warnings == []


@pytest.mark.asyncio
async def test_llm_success_filters_disallowed_problem_reasons(monkeypatch):
    async def fake_completion(messages):
        # unclassified is a deterministic reason and must NOT be accepted from the LLM
        return (
            '{"category": "data_analysis", "confidence": 0.8, '
            '"problem_reasons": ["unclassified", "multiple_intents"], '
            '"automation_potential": "medium"}'
        )

    monkeypatch.setattr(llm_client, "is_configured", lambda: True)
    monkeypatch.setattr(llm_client, "chat_completion", fake_completion)

    outcome = await classify("Проанализируй таблицу и посчитай метрики")
    assert QueryProblemReason.multiple_intents in outcome.llm_problem_reasons
    assert QueryProblemReason.unclassified not in outcome.llm_problem_reasons


@pytest.mark.asyncio
async def test_llm_cannot_override_automation_business_rule(monkeypatch):
    async def fake_completion(messages):
        return (
            '{"category": "summarization", "confidence": 0.95, '
            '"problem_reasons": [], "automation_potential": "high"}'
        )

    monkeypatch.setattr(llm_client, "is_configured", lambda: True)
    monkeypatch.setattr(llm_client, "chat_completion", fake_completion)

    outcome = await classify("Сделай краткую сводку писем")
    assert outcome.category == Category.summarization
    assert outcome.automation_potential == AutomationPotential.medium


@pytest.mark.asyncio
async def test_llm_invalid_json_falls_back(monkeypatch):
    async def fake_completion(messages):
        return "это точно не JSON"

    monkeypatch.setattr(llm_client, "is_configured", lambda: True)
    monkeypatch.setattr(llm_client, "chat_completion", fake_completion)

    outcome = await classify("Выгрузи отчёт по продажам в Excel")
    assert AnalyticsWarning.llm_invalid_response in outcome.warnings
    assert outcome.category == Category.reporting_export  # rule-based fallback


@pytest.mark.asyncio
async def test_llm_category_out_of_enum_falls_back(monkeypatch):
    async def fake_completion(messages):
        return '{"category": "totally_made_up", "confidence": 0.9, "automation_potential": "high"}'

    monkeypatch.setattr(llm_client, "is_configured", lambda: True)
    monkeypatch.setattr(llm_client, "chat_completion", fake_completion)

    outcome = await classify("Добавь тикет в Jira")
    assert AnalyticsWarning.llm_invalid_response in outcome.warnings
    assert outcome.category == Category.task_management
