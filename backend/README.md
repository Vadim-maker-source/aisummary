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

- `file`: `.csv` or `.jsonl` for large datasets, `.json` or `.txt`;
- `agent_id`: optional identifier used when a raw request has no `agent_id`.

Two input shapes are supported.

Canonical analytics event:

```json
{
  "external_id": "request-001",
  "agent_id": "corporate-agent",
  "user_id": "user-42",
  "team": "CRM-аналитика",
  "direction": "Продажи",
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

`user_id`, `team` and `direction` enable effectiveness breakdowns in the CTO
dashboard. `response`, `execution_status`, `latency_ms` and `rating` enable
agent-quality metrics. If they are absent, the API reports that coverage is
unavailable instead of inventing an effectiveness score.

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
form field `agent_id` and wraps the payload into `request`. JSONL and CSV are
processed row by row. CSV accepts flat columns such as `user_query`, `team`,
`agent_answer` and `execution_status`. The upload limit is 512 MB.

## 100k context handling

Prompts up to and including 100,000 tokens are supported and are not marked as
oversized. Provider-reported `usage.prompt_tokens` is authoritative. If usage
is unavailable, the backend uses a conservative 400,000-character fallback.
For classification, the backend extracts the last `<user_query>` block. If it
is absent, `<context>` blocks are removed and the remaining instruction is
classified, so a 100k document is not copied into the LLM classification call.

