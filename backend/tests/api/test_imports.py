import json

from app.services.imports import parse_import_rows


def test_parse_json_array():
    content = json.dumps([{"external_id": "1"}, {"external_id": "2"}]).encode()

    rows = parse_import_rows("events.json", content)

    assert len(rows) == 2


def test_parse_jsonl():
    content = b'{"external_id":"1"}\n\n{"external_id":"2"}\n'

    rows = parse_import_rows("events.jsonl", content)

    assert len(rows) == 2


def test_rejects_unknown_extension():
    try:
        parse_import_rows("events.csv", b"data")
    except ValueError as exc:
        assert "Only .json and .jsonl" in str(exc)
    else:
        raise AssertionError("ValueError was not raised")

