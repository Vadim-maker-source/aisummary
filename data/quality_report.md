# Dataset Quality Report

Статус: **PASS**

## Структура и покрытие

- Demo: 740 событий.
- Validation: 185 событий.
- Категории: 12 из 12.
- Сценарии: 35.
- Ответы агента: 136.
- Подтверждённые выполнения: 133.
- Синтетическая оценка экономии: 68.8 ч.
- Ошибки схемы: 0.
- Повторяющиеся ID: 0.
- Ошибки effective-query extraction: 0.
- Точные пересечения demo/validation: 0.

## Edge cases, проверенные backend

| Причина | Заложено | Обнаружено | Recall |
|---|---:|---:|---:|
| `ambiguous` | 31 | 31 | 1.0000 |
| `missing_context` | 31 | 31 | 1.0000 |
| `multiple_intents` | 31 | 31 | 1.0000 |
| `oversized_context` | 12 | 12 | 1.0000 |


## Offline baseline настоящего backend

| Метрика | Результат | Минимум |
|---|---:|---:|
| Category accuracy | 0.9514 | 0.75 |
| Unclassified rate | 0.0541 | — |
| Scenario pairwise precision | 0.9937 | — |
| Scenario pairwise recall | 0.7634 | — |
| Scenario pairwise F1 | 0.8634 | 0.65 |

Метрики рассчитаны функциями `backend/app/analytics` с отключённым LLM.
Validation labels не передаются классификатору. Показатели экономии времени
синтетические и проверяют механику дашборда, а не реальную отдачу бизнеса.
