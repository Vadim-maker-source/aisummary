# Контур — frontend

Next.js-панель аналитики запросов к ИИ-агентам.

## Запуск

Требуется Node.js 20.9 или новее.

```bash
npm install
copy .env.example .env.local
npm run dev
```

Приложение откроется на `http://localhost:3000`.

## Переменные окружения

```text
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_USE_MOCK_DATA=true
```

- `NEXT_PUBLIC_USE_MOCK_DATA=true` включает mock-ответы точной формы API.
- Для реального backend установите `NEXT_PUBLIC_USE_MOCK_DATA=false`.
- Для ручной проверки пустых состояний в mock-режиме можно задать
  `NEXT_PUBLIC_MOCK_EMPTY=true`.
- Для ручной проверки ошибок API можно задать `NEXT_PUBLIC_MOCK_ERROR=true`.

## Проверки

```bash
npm run lint
npm run build
```

## Маршруты

- `/dashboard`
- `/dashboard/scenarios`
- `/dashboard/scenarios/[id]`
- `/dashboard/requests`
- `/imports`
