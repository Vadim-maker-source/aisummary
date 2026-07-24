# Промпт-радар

Аналитика запросов к корпоративным ИИ-агентам: классификация задач,
обнаружение сценариев использования, саммари, проблемы, динамика и
эффективность по агентам, командам и направлениям.

## Что входит

- FastAPI API и worker;
- PostgreSQL и Alembic;
- LLM-классификация через OpenAI-compatible API;
- устойчивый fallback без внешней модели;
- группировка TF-IDF + agglomerative clustering;
- Next.js CTO-дашборд;
- импорт `.json`, `.jsonl`, `.txt`;
- генератор по всем 35 сценариям из кейса;
- отдельный профиль запросов со средним целевым контекстом 100k токенов.

## Быстрый запуск через Docker

Создайте `.env` из `.env.example` и задайте безопасные значения:

```powershell
Copy-Item .env.example .env
docker compose --profile full up --build
```

После запуска:

- дашборд: `http://localhost:3000/dashboard`;
- API: `http://localhost:8000`;
- Swagger: `http://localhost:8000/docs`.

## Локальный запуск

Backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

Worker в отдельном терминале:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m app.worker.runner
```

Frontend:

```powershell
cd frontend
npm ci
npm run dev
```

## Датасеты

Быстрый профиль:

```powershell
python data\generate_datasets.py --profile quick
```

Профиль с целевым средним контекстом 100k токенов:

```powershell
python data\generate_datasets.py --profile compliant
```

Для большого файла используйте JSONL-импорт: он читается построчно.

## Формат события

```json
{
  "external_id": "request-001",
  "agent_id": "mail-copilot",
  "user_id": "user-42",
  "team": "CRM-аналитика",
  "direction": "Продажи",
  "occurred_at": "2026-07-25T12:00:00Z",
  "request": {
    "model": "DeepSeek-V4-Flash",
    "stream": false,
    "messages": [
      {"role": "user", "content": "Собери отчёт по тендерам"}
    ]
  },
  "response": {
    "content": "Готовый отчёт...",
    "usage": {
      "prompt_tokens": 1200,
      "completion_tokens": 200,
      "total_tokens": 1400
    }
  },
  "execution_status": "success",
  "latency_ms": 2400,
  "rating": 5
}
```

`team`, `direction`, `user_id`, ответ, статус, latency и rating необязательны.
Если их нет, дашборд честно показывает, что соответствующая аналитика
недоступна.

## Проверка

```powershell
cd backend
pytest -q

cd ..\frontend
npm run lint
npm run build
```
