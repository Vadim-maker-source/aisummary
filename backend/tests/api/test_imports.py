import csv
import io
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


def test_parse_flat_csv_with_semicolon_and_utf8_bom():
    content = (
        "\ufeffexternal_id;Агент;Запрос;Команда;Ответ;"
        "Статус;task_completed;estimated_minutes_saved;"
        "prompt_tokens;completion_tokens;total_tokens\n"
        "csv-1;mail-agent;Сделай сводку писем;Продажи;Готово;"
        "success;да;30;100000;200;100200\n"
    ).encode("utf-8")

    rows = parse_import_rows("events.csv", content)
    normalized = normalize_import_row(
        rows[0],
        filename="events.csv",
        row_number=1,
        default_agent_id="fallback-agent",
    )
    event = EventCreate.model_validate(normalized)

    assert event.external_id == "csv-1"
    assert event.agent_id == "mail-agent"
    assert event.team == "Продажи"
    assert event.request.messages[0].content == "Сделай сводку писем"
    assert event.response is not None
    assert event.response.content == "Готово"
    assert event.response.usage is not None
    assert event.response.usage.prompt_tokens == 100_000
    assert event.task_completed is True
    assert event.estimated_minutes_saved == 30


def test_parse_csv_messages_json_and_quoted_commas():
    stream = io.StringIO()
    writer = csv.DictWriter(
        stream,
        fieldnames=["external_id", "messages", "model"],
    )
    writer.writeheader()
    writer.writerow(
        {
            "external_id": "csv-messages-1",
            "messages": json.dumps(
                [
                    {
                        "role": "user",
                        "content": "Сравни продажи, расходы и прибыль",
                    }
                ],
                ensure_ascii=False,
            ),
            "model": "test-model",
        }
    )

    rows = parse_import_rows("events.csv", stream.getvalue().encode("utf-8"))
    normalized = normalize_import_row(
        rows[0],
        filename="events.csv",
        row_number=1,
        default_agent_id="csv-agent",
    )
    event = EventCreate.model_validate(normalized)

    assert event.request.model == "test-model"
    assert event.request.messages[0].content == (
        "Сравни продажи, расходы и прибыль"
    )


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


def test_iter_csv_streams_event_with_100k_context(tmp_path: Path):
    path = tmp_path / "events-100k.csv"
    context = "Контекст. " * 31_000
    messages = [
        {
            "role": "user",
            "content": (
                f"<context>{context}</context>"
                "<user_query>Собери отчёт по тендерам</user_query>"
            ),
        }
    ]
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(
            target,
            fieldnames=[
                "external_id",
                "messages",
                "prompt_tokens",
                "completion_tokens",
                "total_tokens",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "external_id": "csv-context-100k",
                "messages": json.dumps(messages, ensure_ascii=False),
                "prompt_tokens": 100_000,
                "completion_tokens": 100,
                "total_tokens": 100_100,
            }
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


def test_iter_csv_keeps_processing_after_invalid_row(tmp_path: Path):
    path = tmp_path / "events.csv"
    path.write_text(
        "external_id,user_query\n"
        "csv-valid-1,Найди документы\n"
        "csv-invalid-1,\n"
        "csv-valid-2,Составь отчёт\n",
        encoding="utf-8",
    )

    rows = list(iter_import_rows(path.name, path))

    assert len(rows) == 3
    assert rows[0][1]["request"]["messages"][0]["content"] == "Найди документы"
    assert rows[1][1] is None
    assert "must contain" in rows[1][2]
    assert rows[2][1]["request"]["messages"][0]["content"] == "Составь отчёт"


def test_rejects_unknown_extension():
    try:
        parse_import_rows("events.xlsx", b"data")
    except ValueError as exc:
        assert "Only .json, .jsonl, .txt and .csv" in str(exc)
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


async def test_uploads_csv_dataset_end_to_end(client):
    stream = io.StringIO()
    writer = csv.DictWriter(
        stream,
        fieldnames=[
            "external_id",
            "user_query",
            "team",
            "direction",
            "agent_answer",
            "execution_status",
        ],
    )
    writer.writeheader()
    writer.writerow(
        {
            "external_id": "csv-e2e-1",
            "user_query": "Составь отчёт по продажам",
            "team": "BI",
            "direction": "Продажи",
            "agent_answer": "Отчёт готов",
            "execution_status": "success",
        }
    )
    writer.writerow(
        {
            "external_id": "csv-e2e-2",
            "user_query": "Найди регламент согласования",
            "team": "Юристы",
            "direction": "Бэк-офис",
            "agent_answer": "Документ найден",
            "execution_status": "success",
        }
    )

    response = await client.post(
        "/api/v1/imports",
        files={
            "file": (
                "dataset.csv",
                stream.getvalue().encode("utf-8"),
                "text/csv",
            )
        },
        data={"agent_id": "csv-agent"},
    )

    assert response.status_code == 202
    import_id = response.json()["id"]
    status_response = await client.get(f"/api/v1/imports/{import_id}")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "completed"
    assert status_response.json()["processed_rows"] == 2
    assert status_response.json()["failed_rows"] == 0

    events_response = await client.get("/api/v1/events")
    assert events_response.status_code == 200
    assert events_response.json()["total"] == 2

