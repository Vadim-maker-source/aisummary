from app.services.analytics_gateway import analyze_event


async def test_extracts_nested_user_query():
    content = """
    <context>Не использовать этот текст как вопрос.</context>
    <user_query>
      Сделай краткую сводку писем
    </user_query>
    """

    result = await analyze_event(
        {
            "event_id": "11111111-1111-4111-8111-111111111111",
            "messages": [{"role": "user", "content": content}],
            "model": None,
            "prompt_tokens": None,
        },
        [],
    )

    assert result["effective_query"] == "Сделай краткую сводку писем"
    assert result["category"] == "summarization"
    assert result["classification_confidence"] == 0.7


async def test_missing_user_message_is_unclassified():
    result = await analyze_event(
        {
            "event_id": "11111111-1111-4111-8111-111111111111",
            "messages": [{"role": "system", "content": "System"}],
            "model": None,
            "prompt_tokens": None,
        },
        [],
    )

    assert result["effective_query"] == ""
    assert result["category"] == "other"
    assert "no_user_message" in result["warnings"]
    assert "unclassified" in result["query_problem_reasons"]

