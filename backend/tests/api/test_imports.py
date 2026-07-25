import json
from pathlib import Path

from app.schemas.events import EventCreate
from app.services.imports import (
    iter_import_rows,
    normalize_import_row,
    parse_import_rows,
)


def test_parse_json_array():
    content = json.dumps([{"external_id": "1"}, {"external_id": "2"}]).encode()

    rows = parse_import_rows("events.json", content)

    assert len(rows) == 2


def test_parse_jsonl():
    content = b'{"external_id":"1"}\n\n{"external_id":"2"}\n'

    rows = parse_import_rows("events.jsonl", content)

    assert len(rows) == 2


def test_parse_single_raw_json_object():
    content = json.dumps(
        {
            "model": "test-model",
            "stream": True,
            "messages": [{"role": "user", "content": "Привет"}],
        }
    ).encode()

    rows = parse_import_rows("request.json", content)

    assert len(rows) == 1
    assert rows[0]["messages"][0]["content"] == "Привет"


def test_parse_txt_with_raw_openai_request():
    content = json.dumps(
        {
            "model": "test-model",
            "stream": True,
            "stream_options": {"include_usage": True},
            "messages": [{"role": "user", "content": "Привет"}],
        }
    ).encode()

    rows = parse_import_rows("request.txt", content)
    normalized = normalize_import_row(
        rows[0],
        filename="request.txt",
        row_number=1,
        default_agent_id="uploaded-agent",
    )
    event = EventCreate.model_validate(normalized)

    assert event.agent_id == "uploaded-agent"
    assert event.external_id.startswith("import-")
    assert event.request.model == "test-model"
    assert event.request.model_extra == {
        "stream_options": {"include_usage": True}
    }


def test_iter_jsonl_keeps_processing_after_invalid_line(tmp_path: Path):
    path = tmp_path / "events.jsonl"
    path.write_text(
        '{"messages":[{"role":"user","content":"one"}]}\n'
        "not-json\n"
        '{"messages":[{"role":"user","content":"two"}]}\n',
        encoding="utf-8",
    )

    rows = list(iter_import_rows(path.name, path))

    assert len(rows) == 3
    assert rows[0][1]["messages"][0]["content"] == "one"
    assert rows[1][1] is None
    assert "Invalid JSON" in rows[1][2]
    assert rows[2][1]["messages"][0]["content"] == "two"


def test_iter_jsonl_streams_event_with_100k_context(tmp_path: Path):
    path = tmp_path / "events-100k.jsonl"
    context = "Контекст. " * 31_000
    event = {
        "external_id": "context-100k",
        "agent_id": "test-agent",
        "request": {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"<context>{context}</context>"
                        "<user_query>Собери отчёт по тендерам</user_query>"
                    ),
                }
            ]
        },
        "response": {
            "content": "Готово",
            "usage": {
                "prompt_tokens": 100_000,
                "completion_tokens": 100,
                "total_tokens": 100_100,
            },
        },
    }
    path.write_text(
        json.dumps(event, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    rows = list(iter_import_rows(path.name, path))
    normalized = normalize_import_row(
        rows[0][1],
        filename=path.name,
        row_number=rows[0][0],
        default_agent_id="imported-agent",
    )
    validated = EventCreate.model_validate(normalized)

    assert len(rows) == 1
    assert validated.response is not None
    assert validated.response.usage is not None
    assert validated.response.usage.prompt_tokens == 100_000


def test_rejects_unknown_extension():
    try:
        parse_import_rows("events.csv", b"data")
    except ValueError as exc:
        assert "Only .json, .jsonl and .txt" in str(exc)
    else:
        raise AssertionError("ValueError was not raised")


async def test_uploads_raw_txt_request_end_to_end(client):
    raw = json.dumps(
        {
            "model": "test-model",
            "stream": False,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "<context>Документ</context>"
                        "<user_query>Сделай краткую сводку</user_query>"
                    ),
                }
            ],
        },
        ensure_ascii=False,
    ).encode("utf-8")

    response = await client.post(
        "/api/v1/imports",
        files={"file": ("request.txt", raw, "text/plain")},
        data={"agent_id": "txt-agent"},
    )

    assert response.status_code == 202
    import_id = response.json()["id"]
    status_response = await client.get(f"/api/v1/imports/{import_id}")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "completed"
    assert status_response.json()["processed_rows"] == 1
    assert status_response.json()["failed_rows"] == 0

    events_response = await client.get("/api/v1/events")
    assert events_response.status_code == 200
    assert events_response.json()["total"] == 1
    assert events_response.json()["items"][0]["agent_id"] == "txt-agent"

