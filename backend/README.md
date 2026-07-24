# AI-agent analytics backend

## Local development

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

API documentation: `http://localhost:8000/docs`.

## Import format

`POST /api/v1/imports` accepts `multipart/form-data`:

- `file`: `.jsonl` (recommended for large datasets), `.json` or `.txt`;
- `agent_id`: optional identifier used when a raw request has no `agent_id`.

Two input shapes are supported.

Canonical analytics event:

```json
{
  "external_id": "request-001",
  "agent_id": "corporate-agent",
  "occurred_at": "2026-07-25T12:00:00Z",
  "request": {
    "model": "DeepSeek-V4-Flash",
    "stream": true,
    "messages": [
      {"role": "user", "content": "Сделай краткую сводку"}
    ]
  },
  "response": null,
  "execution_status": "unknown"
}
```

Raw OpenAI-compatible request:

```json
{
  "model": "DeepSeek-V4-Flash",
  "stream": true,
  "stream_options": {"include_usage": true},
  "messages": [
    {"role": "user", "content": "Сделай краткую сводку"}
  ]
}
```

For raw requests the importer generates a stable `external_id`, applies the
form field `agent_id` and wraps the payload into `request`. JSONL is processed
line by line and can contain one object per line. The upload limit is 512 MB.

