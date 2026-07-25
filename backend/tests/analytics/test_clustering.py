"""Scenario discovery / clustering tests (acceptance section 5.7)."""

from __future__ import annotations

import numpy as np
import pytest

from app.analytics import embedding_client
from app.analytics.public import discover_scenarios
from app.analytics.schemas import (
    Category,
    QueryProblemReason,
    ScenarioInputRecord,
)

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def disable_real_embeddings(monkeypatch):
    monkeypatch.setattr(embedding_client, "is_configured", lambda: False)

CALENDAR = [
    "Найди общий свободный слот для встречи команды",
    "Найди общий свободный слот для встречи коллег",
    "Найди свободный слот для общей встречи",
]
SUMMARIES = [
    "Сделай краткую сводку писем за день",
    "Сделай краткую сводку почты за день",
    "Подготовь краткую сводку писем за сутки",
]


def _records():
    records = []
    for i, q in enumerate(CALENDAR):
        records.append(ScenarioInputRecord(event_id=f"cal-{i}", effective_query=q, category=Category.calendar_planning))
    for i, q in enumerate(SUMMARIES):
        records.append(ScenarioInputRecord(event_id=f"sum-{i}", effective_query=q, category=Category.summarization))
    return records


async def test_clustering_basic():
    result = await discover_scenarios(_records())
    categories = {s.category for s in result.scenarios}
    assert Category.calendar_planning in categories
    assert Category.summarization in categories
    assert result.algorithm_version == "tfidf-agg-v1"


async def test_clustering_no_scenario_mixes_categories():
    result = await discover_scenarios(_records())
    for scenario in result.scenarios:
        prefix = "cal-" if scenario.category == Category.calendar_planning else "sum-"
        assert all(member.startswith(prefix) for member in scenario.member_event_ids)


async def test_clustering_is_deterministic():
    first = await discover_scenarios(_records())
    second = await discover_scenarios(_records())

    def signature(res):
        return sorted(
            (s.category.value, s.name, tuple(sorted(s.member_event_ids))) for s in res.scenarios
        )

    assert signature(first) == signature(second)
    assert sorted(first.unclustered_event_ids) == sorted(second.unclustered_event_ids)


async def test_cluster_smaller_than_three_goes_unclustered():
    # Only two unique queries in a category -> no scenario, both unclustered.
    records = [
        ScenarioInputRecord(event_id="a", effective_query="Составь SQL-запрос по продажам", category=Category.data_analysis),
        ScenarioInputRecord(event_id="b", effective_query="Составь SQL-запрос по выручке", category=Category.data_analysis),
    ]
    result = await discover_scenarios(records)
    assert result.scenarios == []
    assert set(result.unclustered_event_ids) == {"a", "b"}


async def test_small_outlier_cluster_unclustered():
    # 3 tight calendar queries form a scenario; 2 unrelated ones fall out.
    records = [
        ScenarioInputRecord(event_id="c1", effective_query="Найди общий свободный слот для встречи команды", category=Category.calendar_planning),
        ScenarioInputRecord(event_id="c2", effective_query="Найди общий свободный слот для встречи коллег", category=Category.calendar_planning),
        ScenarioInputRecord(event_id="c3", effective_query="Найди общий свободный слот для встречи отдела", category=Category.calendar_planning),
        ScenarioInputRecord(event_id="o1", effective_query="Поставь напоминание про день рождения", category=Category.calendar_planning),
        ScenarioInputRecord(event_id="o2", effective_query="Перенеси корпоратив на следующий квартал", category=Category.calendar_planning),
    ]
    result = await discover_scenarios(records)
    assert len(result.scenarios) == 1
    members = set(result.scenarios[0].member_event_ids)
    assert members == {"c1", "c2", "c3"}
    assert set(result.unclustered_event_ids) == {"o1", "o2"}


async def test_other_category_excluded():
    records = _records() + [
        ScenarioInputRecord(event_id="oth-1", effective_query="Поговорим о жизни", category=Category.other),
        ScenarioInputRecord(event_id="oth-2", effective_query="Мне немного скучно", category=Category.other),
    ]
    result = await discover_scenarios(records)
    all_members = {m for s in result.scenarios for m in s.member_event_ids}
    assert "oth-1" not in all_members and "oth-2" not in all_members
    assert "oth-1" not in result.unclustered_event_ids
    assert "oth-2" not in result.unclustered_event_ids


async def test_duplicate_queries_keep_all_memberships():
    # 3 unique queries but one is duplicated across two events.
    records = [
        ScenarioInputRecord(event_id="d1", effective_query="Сделай краткую сводку писем за день", category=Category.summarization),
        ScenarioInputRecord(event_id="d2", effective_query="Сделай краткую сводку писем за день", category=Category.summarization),
        ScenarioInputRecord(event_id="d3", effective_query="Сделай краткую сводку почты за день", category=Category.summarization),
        ScenarioInputRecord(event_id="d4", effective_query="Подготовь краткую сводку писем за сутки", category=Category.summarization),
    ]
    result = await discover_scenarios(records)
    assert len(result.scenarios) == 1
    members = set(result.scenarios[0].member_event_ids)
    assert members == {"d1", "d2", "d3", "d4"}  # duplicate d1/d2 both retained


async def test_empty_input():
    result = await discover_scenarios([])
    assert result.scenarios == []
    assert result.unclustered_event_ids == []
    assert result.algorithm_version == "tfidf-agg-v1"


async def test_semantic_clustering_can_bridge_category_errors(monkeypatch):
    records = [
        ScenarioInputRecord(
            event_id="mail-1",
            effective_query="Сделай сводку почты",
            category=Category.summarization,
        ),
        ScenarioInputRecord(
            event_id="mail-2",
            effective_query="Подведи итоги писем",
            category=Category.summarization,
        ),
        ScenarioInputRecord(
            event_id="mail-3",
            effective_query="Кратко перескажи входящие",
            category=Category.reporting_export,
        ),
        ScenarioInputRecord(
            event_id="meet-1",
            effective_query="Найди слот для встречи",
            category=Category.calendar_planning,
        ),
        ScenarioInputRecord(
            event_id="meet-2",
            effective_query="Подбери время в календаре",
            category=Category.calendar_planning,
        ),
        ScenarioInputRecord(
            event_id="meet-3",
            effective_query="Когда команда свободна",
            category=Category.calendar_planning,
        ),
    ]
    vectors = np.asarray(
        [
            [1.0, 0.00],
            [0.99, 0.01],
            [0.98, 0.02],
            [0.00, 1.0],
            [0.01, 0.99],
            [0.02, 0.98],
        ]
    )
    monkeypatch.setattr(embedding_client, "is_configured", lambda: True)

    async def fake_embeddings(_texts):
        return vectors

    monkeypatch.setattr(embedding_client, "embed_texts", fake_embeddings)
    result = await discover_scenarios(records)

    assert result.algorithm_version == "qwen-embedding-agg-v2"
    assert len(result.scenarios) == 2
    scenario_members = [
        set(scenario.member_event_ids)
        for scenario in result.scenarios
    ]
    assert {"mail-1", "mail-2", "mail-3"} in scenario_members
    assert {"meet-1", "meet-2", "meet-3"} in scenario_members
    mail = next(
        scenario
        for scenario in result.scenarios
        if "mail-1" in scenario.member_event_ids
    )
    assert mail.category == Category.summarization


async def test_problematic_requests_are_not_used_for_discovery(monkeypatch):
    records = [
        ScenarioInputRecord(
            event_id=f"good-{index}",
            effective_query=f"Сделай сводку писем, вариант {index}",
            category=Category.summarization,
        )
        for index in range(3)
    ]
    records.append(
        ScenarioInputRecord(
            event_id="ambiguous",
            effective_query="Сделай это",
            category=Category.summarization,
            classification_confidence=0.9,
            query_problem_reasons=[QueryProblemReason.ambiguous],
        )
    )
    monkeypatch.setattr(embedding_client, "is_configured", lambda: True)

    async def fake_embeddings(texts):
        assert len(texts) == 3
        return np.asarray(
            [[1.0, 0.0], [0.99, 0.01], [0.98, 0.02]]
        )

    monkeypatch.setattr(embedding_client, "embed_texts", fake_embeddings)
    result = await discover_scenarios(records)

    assert len(result.scenarios) == 1
    assert "ambiguous" not in result.scenarios[0].member_event_ids
    assert "ambiguous" in result.unclustered_event_ids


async def test_embedding_failure_falls_back_to_tfidf(monkeypatch):
    monkeypatch.setattr(embedding_client, "is_configured", lambda: True)

    async def fail_embeddings(_texts):
        raise embedding_client.EmbeddingError("temporary failure")

    monkeypatch.setattr(embedding_client, "embed_texts", fail_embeddings)
    result = await discover_scenarios(_records())

    assert result.algorithm_version == "tfidf-agg-v1"
    assert len(result.scenarios) == 2
