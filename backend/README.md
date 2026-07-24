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

