# End-to-end Database Quality Report

Статус: **PASS**

## Целостность

- Событий: 740 из 740.
- Потеряно: 0.
- Лишних: 0.
- Анализ завершён: 740.
- Строк результатов анализа: 740.
- Ошибок анализа: 0.

## Фактический pipeline PostgreSQL

- Алгоритм: `qwen-embedding-agg-v2`.
- Сценариев: 45.
- Membership: 635.
- Category accuracy: 0.8595.
- Scenario pairwise precision: 0.7950.
- Scenario pairwise recall: 0.7224.
- Scenario pairwise F1: 0.7570.
- Coverage обычных запросов: 0.9642.
- Средняя чистота кластеров: 0.9199.

Метрики рассчитаны по текущему `is_current` analysis run в PostgreSQL.
Данные синтетические, поэтому отчёт проверяет качество аналитического pipeline,
но не доказывает реальную экономию времени или ROI.
