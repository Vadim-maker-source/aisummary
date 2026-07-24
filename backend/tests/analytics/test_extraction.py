"""Effective-query extraction tests (acceptance section 5.1-5.3, role file 5/12)."""

from __future__ import annotations

import pytest

from app.analytics.extraction import (
    CLASSIFIER_MAX_CHARS,
    extract_effective_query,
)
from app.analytics.schemas import (
    AnalysisInput,
    AnalyticsWarning,
    Message,
    QueryProblemReason,
)


def _inp(messages, prompt_tokens=None):
    return AnalysisInput(event_id="e", messages=messages, model=None, prompt_tokens=prompt_tokens)


def test_extraction_simple():
    result = extract_effective_query(
        _inp([Message(role="user", content="  Найди   общий слот\nдля встречи  ")])
    )
    assert result.effective_query == "Найди общий слот для встречи"
    assert result.has_user_message is True
    assert result.warnings == []


def test_extraction_from_user_query_tag():
    content = (
        "### Task\nИспользуй контекст.\n"
        "<context>\nБольшой технический документ.\n</context>\n"
        "<user_query>\nКакая интеграция используется и для чего?\n</user_query>"
    )
    result = extract_effective_query(_inp([Message(role="user", content=content)]))
    assert result.effective_query == "Какая интеграция используется и для чего?"
    assert "документ" not in result.effective_query  # никакого текста из <context>


def test_extraction_chooses_last_user_message():
    result = extract_effective_query(
        _inp(
            [
                Message(role="user", content="Первый вопрос"),
                Message(role="assistant", content="Ответ"),
                Message(role="user", content="Второй вопрос"),
            ]
        )
    )
    assert result.effective_query == "Второй вопрос"


def test_extraction_chooses_last_user_query_tag():
    content = (
        "<user_query>Первый запрос</user_query> шум "
        "<user_query>Второй запрос</user_query>"
    )
    result = extract_effective_query(_inp([Message(role="user", content=content)]))
    assert result.effective_query == "Второй запрос"


def test_extraction_multiline_user_query_tag():
    content = "<user_query>\nСколько стоит\nинтеграция\nс 1С?\n</user_query>"
    result = extract_effective_query(_inp([Message(role="user", content=content)]))
    assert result.effective_query == "Сколько стоит интеграция с 1С?"


def test_extraction_case_insensitive_tag():
    content = "<USER_QUERY>Верхний регистр тега</USER_QUERY>"
    result = extract_effective_query(_inp([Message(role="user", content=content)]))
    assert result.effective_query == "Верхний регистр тега"


def test_no_user_message():
    result = extract_effective_query(
        _inp(
            [
                Message(role="system", content="Ты ассистент"),
                Message(role="assistant", content="Привет"),
            ]
        )
    )
    assert result.has_user_message is False
    assert result.effective_query == ""
    assert AnalyticsWarning.no_user_message in result.warnings


def test_whitespace_normalization():
    result = extract_effective_query(
        _inp([Message(role="user", content="\t Собери\n\n  данные   \t по  продажам \n")])
    )
    assert result.effective_query == "Собери данные по продажам"


def test_truncation_builds_8000_char_classifier_text():
    long_query = "А" * 9000
    result = extract_effective_query(_inp([Message(role="user", content=long_query)]))
    # effective query keeps the full text …
    assert len(result.effective_query) == 9000
    # … while classifier text is the first 4000 + last 4000 characters.
    assert len(result.classifier_text) == CLASSIFIER_MAX_CHARS
    assert AnalyticsWarning.query_truncated in result.warnings


def test_no_truncation_at_boundary():
    query = "Б" * CLASSIFIER_MAX_CHARS  # exactly 8000 -> no truncation
    result = extract_effective_query(_inp([Message(role="user", content=query)]))
    assert len(result.classifier_text) == CLASSIFIER_MAX_CHARS
    assert AnalyticsWarning.query_truncated not in result.warnings


def test_oversized_context_by_length():
    content = "п" * 20001
    result = extract_effective_query(_inp([Message(role="user", content=content)]))
    assert QueryProblemReason.oversized_context in result.problems


def test_oversized_context_counts_system_tool_and_history_messages():
    result = extract_effective_query(
        _inp(
            [
                Message(role="system", content="с" * 9000),
                Message(role="tool", content="д" * 12000),
                Message(role="user", content="Короткий вопрос"),
            ]
        )
    )
    assert result.effective_query == "Короткий вопрос"
    assert QueryProblemReason.oversized_context in result.problems


def test_oversized_context_by_prompt_tokens():
    result = extract_effective_query(
        _inp([Message(role="user", content="короткий запрос")], prompt_tokens=50001)
    )
    assert QueryProblemReason.oversized_context in result.problems


def test_not_oversized_for_normal_input():
    result = extract_effective_query(
        _inp([Message(role="user", content="обычный короткий запрос")], prompt_tokens=1000)
    )
    assert QueryProblemReason.oversized_context not in result.problems
