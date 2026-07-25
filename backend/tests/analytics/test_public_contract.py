"""Contract-shape tests: the public results must match 00_SHARED_CONTRACT.md."""

from __future__ import annotations

import pytest

from app.analytics.public import analyze_event, discover_scenarios
from app.analytics.schemas import (
    AnalysisInput,
    AutomationPotential,
    Category,
    DiscoveredScenario,
    Message,
    QueryProblemReason,
    ScenarioInputRecord,
)

pytestmark = pytest.mark.asyncio


async def test_event_analysis_result_shape():
    result = await analyze_event(
        AnalysisInput(
            event_id="0e2b1d1c-b3bf-4889-aad8-88ea395e5e23",
            messages=[Message(role="user", content="Найди общий слот для встречи")],
        ),
        [],
    )
    dumped = result.model_dump()
    expected_keys = {
        "effective_query",
        "category",
        "classification_confidence",
        "scenario_id",
        "scenario_confidence",
        "query_problem_reasons",
        "automation_potential",
        "warnings",
        "classifier_version",
    }
    assert set(dumped) == expected_keys
    assert 0.0 <= result.classification_confidence <= 1.0
    assert isinstance(result.category, Category)
    assert isinstance(result.automation_potential, AutomationPotential)
    assert all(isinstance(p, QueryProblemReason) for p in result.query_problem_reasons)
    assert result.scenario_id is None  # nullable when no scenarios given


async def test_no_user_message_confidence_zero():
    result = await analyze_event(
        AnalysisInput(event_id="x", messages=[Message(role="assistant", content="Привет")]),
        [],
    )
    assert result.effective_query == ""
    assert result.category == Category.other
    assert result.classification_confidence == 0.0


async def test_discovery_result_shape_and_limits():
    # Build a category with > 10 tight variants to check representative cap.
    records = [
        ScenarioInputRecord(
            event_id=f"c-{i}",
            effective_query=f"Найди общий свободный слот для встречи участника {i}",
            category=Category.calendar_planning,
        )
        for i in range(14)
    ]
    result = await discover_scenarios(records)
    dumped = result.model_dump()
    assert set(dumped) == {"scenarios", "unclustered_event_ids", "algorithm_version"}
    assert result.algorithm_version == "tfidf-agg-v1"
    assert len(result.scenarios) >= 1
    for scenario in result.scenarios:
        assert isinstance(scenario, DiscoveredScenario)
        assert len(scenario.representative_queries) <= 10
        assert len(scenario.name) <= 80
        assert len(scenario.summary) <= 500
        assert len(scenario.suggested_action) <= 500
