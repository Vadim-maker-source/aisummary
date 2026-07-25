# Промпт-радар — преддемонстрационный отчёт

Источник: воспроизводимый синтетический `data/demo_events.jsonl`.
После импорта интерфейс пересчитает те же показатели по PostgreSQL.

## Ключевые показатели

- Запросов: 740
- Категорий: 12
- Сценариев в эталонной разметке: 35
- Событий с ответом: 136
- Ошибок выполнения: 3
- Подтверждённых выполнений: 133
- Синтетическая оценка сэкономленного времени: 68.8 ч

## Категории

| Категория | Запросы | Доля |
|---|---:|---:|
| `information_search` | 140 | 18.9% |
| `task_management` | 120 | 16.2% |
| `calendar_planning` | 100 | 13.5% |
| `monitoring_automation` | 80 | 10.8% |
| `text_generation` | 80 | 10.8% |
| `reporting_export` | 60 | 8.1% |
| `summarization` | 40 | 5.4% |
| `code_assistance` | 40 | 5.4% |
| `data_analysis` | 20 | 2.7% |
| `knowledge_explanation` | 20 | 2.7% |
| `non_work_general` | 20 | 2.7% |
| `other` | 20 | 2.7% |


## Топ сценариев

| Сценарий | Запросы |
|---|---:|
| `weekly_won_tenders_digest` | 40 |
| `excel_data_export` | 40 |
| `daily_email_digest` | 20 |
| `client_company_360` | 20 |
| `monitor_unanswered_price_requests` | 20 |
| `project_team_vendor_owner` | 20 |
| `company_open_source_research` | 20 |
| `crm_client_excel_report` | 20 |
| `manager_feedback_coolfeedback` | 20 |
| `pre_monitoring_employee_note` | 20 |


## Ограничение

Данные, ответы и экономия времени синтетические. Для доказательства реальной
эффективности после пилота нужны обезличенные production-логи и подтверждённые
пользователями результаты.
