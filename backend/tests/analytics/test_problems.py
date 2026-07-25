from app.analytics.problems import deterministic_query_problem_reasons
from app.analytics.schemas import QueryProblemReason


def _values(query: str) -> set[str]:
    return {
        reason.value
        for reason in deterministic_query_problem_reasons(query)
    }


def test_detects_missing_context_reference():
    assert QueryProblemReason.missing_context.value in _values(
        "Сделай сводку. Используй те же параметры, что в прошлый раз."
    )


def test_detects_short_ambiguous_reference():
    assert QueryProblemReason.ambiguous.value in _values(
        "Оформи это так же, как обычно."
    )


def test_detects_multiple_intents():
    assert QueryProblemReason.multiple_intents.value in _values(
        "Найди контакты клиента и после этого выгрузи найденное в Excel."
    )


def test_does_not_mark_a_specific_single_intent():
    assert _values(
        "Найди контакты компании КРОК в корпоративном справочнике."
    ) == set()
