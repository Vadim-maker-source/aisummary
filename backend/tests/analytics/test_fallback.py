"""LLM-failure / fallback tests (acceptance section 5.8, role file section 12).

The LLM is always mocked; nothing here touches the network or needs an API key.
"""

from __future__ import annotations

import pytest

from app.analytics import llm_client
from app.analytics.public import analyze_event, discover_scenarios
from app.analytics.schemas import (
    AnalysisInput,
    AnalyticsWarning,
    Category,
    EventAnalysisResult,
    Message,
    ScenarioDiscoveryResult,
    ScenarioInputRecord,
)

pytestmark = pytest.mark.asyncio


def _inp(content="Выгрузи отчёт по продажам в Excel"):
    return AnalysisInput(event_id="e", messages=[Message(role="user", content=content)])


async def test_llm_unavailable_falls_back_without_raising(monkeypatch):
    async def timeout_completion(messages):
        raise llm_client.LLMError("timeout")

    monkeypatch.setattr(llm_client, "is_configured", lambda: True)
    monkeypatch.setattr(llm_client, "chat_completion", timeout_completion)

    result = await analyze_event(_inp(), [])
    assert isinstance(result, EventAnalysisResult)
    assert result.category == Category.reporting_export  # rule-based fallback
    assert AnalyticsWarning.llm_unavailable in result.warnings


async def test_llm_invalid_response_warning(monkeypatch):
    async def garbage_completion(messages):
        return "<html>not json</html>"

    monkeypatch.setattr(llm_client, "is_configured", lambda: True)
    monkeypatch.setattr(llm_client, "chat_completion", garbage_completion)

    result = await analyze_event(_inp(), [])
    assert AnalyticsWarning.llm_invalid_response in result.warnings
    assert result.category == Category.reporting_export


async def test_not_configured_emits_no_llm_warning():
    # Env is cleared by the autouse fixture -> offline mode, no LLM warnings.
    result = await analyze_event(_inp(), [])
    assert AnalyticsWarning.llm_unavailable not in result.warnings
    assert AnalyticsWarning.llm_invalid_response not in result.warnings
    assert result.category == Category.reporting_export


async def test_full_pipeline_assignment_with_mocked_llm(monkeypatch):
    # With the LLM classifying as calendar_planning, assignment to a known
    # calendar scenario succeeds end-to-end.
    async def calendar_completion(messages):
        return '{"category": "calendar_planning", "confidence": 0.9, "automation_potential": "high"}'

    monkeypatch.setattr(llm_client, "is_configured", lambda: True)
    monkeypatch.setattr(llm_client, "chat_completion", calendar_completion)

    from app.analytics.schemas import KnownScenario

    known = KnownScenario(
        id="33333333-3333-4333-8333-333333333333",
        category=Category.calendar_planning,
        name="Подбор времени встречи",
        representative_queries=[
            "Найди общий свободный слот для встречи",
            "Подбери время, когда все участники свободны",
        ],
    )
    result = await analyze_event(_inp("Найди свободное время для общей встречи"), [known])
    assert result.category == Category.calendar_planning
    assert result.scenario_id == known.id
    assert result.scenario_confidence is not None


async def test_summarizer_fallback_offline():
    records = [
        ScenarioInputRecord(event_id="s1", effective_query="Сделай краткую сводку писем за день", category=Category.summarization),
        ScenarioInputRecord(event_id="s2", effective_query="Сделай краткую сводку почты за день", category=Category.summarization),
        ScenarioInputRecord(event_id="s3", effective_query="Подготовь краткую сводку писем за сутки", category=Category.summarization),
    ]
    result = await discover_scenarios(records)
    assert len(result.scenarios) >= 1
    scenario = result.scenarios[0]
    assert scenario.name.startswith("Сценарий: ")
    assert scenario.suggested_action == "Провести ручной анализ сценария"
    assert "кластер" not in scenario.name.lower()
    assert len(scenario.name) <= 80


async def test_public_functions_return_exact_models():
    event_result = await analyze_event(_inp(), [])
    assert isinstance(event_result, EventAnalysisResult)
    assert event_result.classifier_version == "v1"

    discovery_result = await discover_scenarios([])
    assert isinstance(discovery_result, ScenarioDiscoveryResult)
    assert discovery_result.algorithm_version == "tfidf-agg-v1"
