from app.worker.event_worker import process_event_batch


def event_payload(
    *,
    external_id: str = "acceptance-1",
    content: str = "Найди общий слот для встречи",
) -> dict:
    return {
        "external_id": external_id,
        "agent_id": "acceptance-agent",
        "occurred_at": "2026-07-24T10:00:00Z",
        "request": {
            "model": "test-model",
            "stream": False,
            "messages": [{"role": "user", "content": content}],
        },
        "response": None,
        "execution_status": "unknown",
        "latency_ms": None,
        "rating": None,
    }


async def test_health(client):
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_event_is_idempotent(client):
    first = await client.post("/api/v1/events", json=event_payload())
    second = await client.post("/api/v1/events", json=event_payload())

    assert first.status_code == 202
    assert first.json()["duplicate"] is False
    assert second.status_code == 200
    assert second.json()["duplicate"] is True
    assert second.json()["id"] == first.json()["id"]

    events = await client.get("/api/v1/events")
    assert events.status_code == 200
    assert events.json()["total"] == 1


async def test_worker_persists_analysis(client):
    created = await client.post("/api/v1/events", json=event_payload())
    event_id = created.json()["id"]

    assert await process_event_batch(20) == 1

    response = await client.get(f"/api/v1/events/{event_id}")
    payload = response.json()
    assert response.status_code == 200
    assert payload["analysis_status"] == "completed"
    assert payload["effective_user_query"] == "Найди общий слот для встречи"
    assert payload["category"] == "calendar_planning"
    assert payload["classification_confidence"] == 0.7
    assert payload["warnings"] == []


async def test_event_validation(client):
    payload = event_payload()
    payload["request"]["messages"] = []

    response = await client.post("/api/v1/events", json=payload)

    assert response.status_code == 422


async def test_dashboard_summary(client):
    await client.post("/api/v1/events", json=event_payload())
    await process_event_batch(20)

    response = await client.get("/api/v1/dashboard/summary")

    assert response.status_code == 200
    assert response.json() == {
        "total_requests": 1,
        "analyzed_requests": 1,
        "pending_requests": 0,
        "failed_requests": 0,
        "category_count": 1,
        "scenario_count": 0,
        "unclassified_count": 0,
        "query_problem_rate": 0.0,
        "response_count": 0,
        "rated_count": 0,
        "timestamped_count": 1,
        "dimensioned_count": 0,
        "synthetic_requests": 0,
        "value_observation_count": 0,
        "completed_task_count": 0,
        "estimated_hours_saved": 0.0,
    }


async def test_business_dimensions_and_effectiveness(client):
    payload = event_payload(external_id="dimensions-1")
    payload.update(
        {
            "user_id": "user-1",
            "team": "CRM-аналитика",
            "direction": "Продажи",
            "is_synthetic": True,
            "response": {
                "content": "Готовый ответ",
                "usage": {
                    "prompt_tokens": 1000,
                    "completion_tokens": 50,
                    "total_tokens": 1050,
                },
            },
            "execution_status": "success",
            "latency_ms": 1200,
            "rating": 5,
            "task_completed": True,
            "estimated_minutes_saved": 45,
        }
    )
    await client.post("/api/v1/events", json=payload)
    await process_event_batch(20)

    summary = (await client.get("/api/v1/dashboard/summary")).json()
    assert summary["response_count"] == 1
    assert summary["rated_count"] == 1
    assert summary["dimensioned_count"] == 1
    assert summary["synthetic_requests"] == 1
    assert summary["value_observation_count"] == 1
    assert summary["completed_task_count"] == 1
    assert summary["estimated_hours_saved"] == 0.8

    response = await client.get(
        "/api/v1/dashboard/effectiveness",
        params={"dimension": "direction"},
    )
    assert response.status_code == 200
    assert response.json()["available"] is True
    assert response.json()["items"][0]["name"] == "Продажи"
    assert response.json()["items"][0]["success_rate"] == 100.0
    assert response.json()["items"][0]["average_rating"] == 5.0
    assert response.json()["items"][0]["task_completion_rate"] == 100.0
    assert response.json()["items"][0]["estimated_hours_saved"] == 0.8

    decisions = await client.get("/api/v1/dashboard/decision-support")
    assert decisions.status_code == 200
    assert decisions.json()["data_limitations"] == []


async def test_non_work_request_has_explicit_category(client):
    await client.post(
        "/api/v1/events",
        json=event_payload(
            external_id="non-work-1",
            content="Давай просто пообщаемся о космосе",
        ),
    )
    await process_event_batch(20)

    response = await client.get("/api/v1/events")

    assert response.status_code == 200
    assert response.json()["items"][0]["category"] == "non_work_general"


async def test_category_summary_explains_purpose_and_examples(client):
    await client.post("/api/v1/events", json=event_payload())
    await process_event_batch(20)

    response = await client.get("/api/v1/dashboard/category-summaries")

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["category"] == "calendar_planning"
    assert item["purpose"]
    assert item["summary"]
    assert item["representative_queries"] == ["Найди общий слот для встречи"]


async def test_openai_compatible_response_is_normalized(client):
    payload = event_payload(external_id="openai-response-1")
    payload.update(
        {
            "response": {
                "id": "chatcmpl-test",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "Готовый ответ модели",
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 100_000,
                    "completion_tokens": 125,
                    "total_tokens": 100_125,
                },
            },
            "execution_status": "success",
        }
    )

    created = await client.post("/api/v1/events", json=payload)
    assert created.status_code == 202

    response = await client.get(f"/api/v1/events/{created.json()['id']}")
    assert response.status_code == 200
    assert response.json()["prompt_tokens"] == 100_000
    assert response.json()["completion_tokens"] == 125
    assert response.json()["total_tokens"] == 100_125

