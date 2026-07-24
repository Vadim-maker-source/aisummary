"""Scenario assignment tests (acceptance section 5.6, role file section 8)."""

from __future__ import annotations

from app.analytics.scenario_assignment import ASSIGNMENT_THRESHOLD, assign_scenario
from app.analytics.schemas import AnalyticsWarning, Category, KnownScenario

CALENDAR_SCENARIO = KnownScenario(
    id="22222222-2222-4222-8222-222222222222",
    category=Category.calendar_planning,
    name="Подбор времени встречи",
    representative_queries=[
        "Найди общий свободный слот для встречи",
        "Подбери время, когда все участники свободны",
    ],
)


def test_assignment_above_threshold():
    scenario_id, score, warnings = assign_scenario(
        "Найди свободное время для общей встречи",
        Category.calendar_planning,
        [CALENDAR_SCENARIO],
    )
    assert scenario_id == CALENDAR_SCENARIO.id
    assert score is not None and score >= ASSIGNMENT_THRESHOLD
    assert warnings == []


def test_assignment_below_threshold_returns_warning():
    scenario_id, score, warnings = assign_scenario(
        "Закажи пиццу в офис на обед",
        Category.calendar_planning,
        [CALENDAR_SCENARIO],
    )
    assert scenario_id is None
    assert score is None
    assert AnalyticsWarning.no_matching_scenario in warnings


def test_assignment_never_crosses_category():
    # A different-category query must never be assigned to this scenario.
    scenario_id, score, warnings = assign_scenario(
        "Найди общий свободный слот для встречи",  # calendar-looking text …
        Category.data_analysis,  # … but analysed as a different category
        [CALENDAR_SCENARIO],
    )
    assert scenario_id is None
    assert score is None
    assert warnings == []  # no candidates in this category -> assignment N/A


def test_assignment_tie_breaks_on_smallest_uuid():
    reps = ["Подбери общий свободный слот для встречи команды"]
    scenario_high = KnownScenario(
        id="ffffffff-ffff-4fff-8fff-ffffffffffff",
        category=Category.calendar_planning,
        name="B",
        representative_queries=reps,
    )
    scenario_low = KnownScenario(
        id="00000000-0000-4000-8000-000000000000",
        category=Category.calendar_planning,
        name="A",
        representative_queries=list(reps),
    )
    scenario_id, score, _warnings = assign_scenario(
        "Подбери общий свободный слот для встречи команды",
        Category.calendar_planning,
        [scenario_high, scenario_low],
    )
    assert scenario_id == scenario_low.id  # lexicographically smaller UUID wins


def test_assignment_no_known_scenarios():
    scenario_id, score, warnings = assign_scenario(
        "Найди общий свободный слот для встречи",
        Category.calendar_planning,
        [],
    )
    assert scenario_id is None
    assert score is None
    assert warnings == []
