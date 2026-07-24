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
    }

