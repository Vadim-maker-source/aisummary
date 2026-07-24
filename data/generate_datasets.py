"""Generate datasets for the KROK prompt-radar case.

``quick`` is compact and suitable for development. ``compliant`` uses the
case's 100k-token average target. Both profiles explicitly mark synthetic data.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

DATA_DIR = Path(__file__).resolve().parent
BASE_DAY = datetime(2026, 6, 1, 8, 0, tzinfo=timezone.utc)
MODELS = ["DeepSeek-V4-Flash", "GigaChat-Pro", "YandexGPT-4"]
AGENTS = ["mail-copilot", "knowledge-assistant", "work-management-agent"]


@dataclass(frozen=True)
class Topic:
    label: str
    category: str
    intent: str
    volume: int
    trend: str
    direction: str
    team: str
    supplied: bool = True


# All 35 business scenarios from the supplied case, plus 3 control scenarios.
TOPICS = [
    Topic("daily_mail_digest", "summarization", "подготовить структурированную сводку важных писем за прошедший день по заданному шаблону", 28, "growing", "Корпоративные сервисы", "Офис руководителя"),
    Topic("client_group_research", "information_search", "собрать по компании-клиенту директоров дочерних обществ и сведения о выигранных сделках", 14, "stable", "Продажи", "Аккаунт-менеджеры"),
    Topic("unanswered_price_requests", "monitoring_automation", "настроить автоматический мониторинг и отслеживать письма с запросом расчёта цены, на которые не ответили в течение двух часов", 25, "growing", "Продажи", "Коммерческие предложения"),
    Topic("mail_monitoring_rules", "monitoring_automation", "создать периодическое задание мониторинга почты по заданным правилам", 20, "stable", "Корпоративные сервисы", "Автоматизация"),
    Topic("won_tenders_notifications", "monitoring_automation", "настроить мониторинг и еженедельно уведомлять фокус-группу о продажах с выигранными тендерами", 18, "growing", "Продажи", "Тендерный отдел"),
    Topic("crm_digest_to_email", "monitoring_automation", "настроить периодический мониторинг, собирать аналитику из CRM и отправлять её на почту фокус-группе", 22, "growing", "Продажи", "CRM-аналитика"),
    Topic("project_team_vendor_owner", "information_search", "найти состав проектной команды и ответственное за вендора направление", 13, "stable", "Проектный бизнес", "Ресурсный менеджмент"),
    Topic("crm_criteria_search", "information_search", "собрать информацию из CRM по заданным критериям", 24, "stable", "Продажи", "CRM-аналитика"),
    Topic("company_open_source_summary", "information_search", "найти сведения о компании в открытых источниках и подготовить аналитическую сводку", 27, "growing", "Продажи", "Аккаунт-менеджеры"),
    Topic("client_excel_report", "reporting_export", "собрать информацию по клиенту, сформировать единый отчёт и экспортировать его в Excel", 19, "stable", "Продажи", "Отчётность"),
    Topic("crm_fields_to_excel", "reporting_export", "выгрузить выбранные поля из CRM в документ Excel", 26, "stable", "Продажи", "CRM-аналитика"),
    Topic("coolfeedback_manager_review", "text_generation", "сформулировать и написать отзыв руководителя в CoolFeedback по тезисам и договорённостям после мониторинга", 12, "growing", "HR", "Развитие сотрудников"),
    Topic("pre_monitoring_note", "task_management", "записать заметку в анкету перед мониторингом сотрудника", 10, "stable", "HR", "Развитие сотрудников"),
    Topic("isup_ticket_edit", "task_management", "создать новый тикет или отредактировать существующий тикет в ИСУП", 21, "stable", "Проектный бизнес", "Управление проектами"),
    Topic("weekly_tender_report", "reporting_export", "подготовить еженедельный отчёт о выигранных тендерах за последние семь дней", 23, "growing", "Продажи", "Тендерный отдел"),
    Topic("jira_assigned_tasks", "task_management", "показать список задач Jira, назначенных на текущего сотрудника", 30, "stable", "ИТ", "Разработка"),
    Topic("jira_priority_tasks", "task_management", "показать задачи Jira с фильтрацией по приоритету", 17, "declining", "ИТ", "Разработка"),
    Topic("manager_observations", "task_management", "зафиксировать наблюдения руководителя о работе сотрудника", 11, "growing", "HR", "Руководители"),
    Topic("analysis_export_excel", "reporting_export", "сформировать отчёт и экспортировать результаты анализа в Excel для передачи коллегам", 18, "stable", "Аналитика", "BI"),
    Topic("generic_excel_export", "reporting_export", "выгрузить рабочие данные в Excel для внешнего анализа и отчётности", 20, "stable", "Аналитика", "BI"),
    Topic("supplier_blog_search", "information_search", "быстро найти актуальную информацию о поставщиках в корпоративном блоге", 9, "declining", "Закупки", "Поставщики"),
    Topic("confluence_process_search", "information_search", "найти описание рабочего процесса в Confluence", 29, "growing", "Корпоративные сервисы", "База знаний"),
    Topic("leader_calendar_slot", "calendar_planning", "найти свободное время в календаре руководителя и запланировать встречу", 24, "stable", "Корпоративные сервисы", "Офис руководителя"),
    Topic("confirm_task_completion", "task_management", "подтвердить выполнение задачи и закрыть завершённую работу", 15, "stable", "Проектный бизнес", "Управление проектами"),
    Topic("task_history_completion", "task_management", "добавить задачу в историю и отметить её выполненной", 14, "declining", "Проектный бизнес", "Управление проектами"),
    Topic("large_meeting_room", "calendar_planning", "найти свободную переговорную для встречи с большим количеством участников", 16, "growing", "Корпоративные сервисы", "Офис руководителя"),
    Topic("client_thread_reply", "text_generation", "прочитать переписку с клиентом, сформулировать и написать содержательный ответ", 31, "growing", "Продажи", "Аккаунт-менеджеры"),
    Topic("discussion_notes", "summarization", "записать итоги обсуждения с коллегами и выделить договорённости", 22, "stable", "Корпоративные сервисы", "Совместная работа"),
    Topic("client_contacts", "information_search", "найти контакты клиента по названию компании", 20, "stable", "Продажи", "Аккаунт-менеджеры"),
    Topic("large_group_meeting", "calendar_planning", "создать встречу для большого списка коллег и найти общий свободный слот", 18, "growing", "Корпоративные сервисы", "Офис руководителя"),
    Topic("meeting_body_attachment", "information_search", "найти информацию, приложенную текстом в теле встречи", 8, "stable", "Корпоративные сервисы", "Совместная работа"),
    Topic("post_meeting_reminders", "calendar_planning", "создать в календаре напоминания по договорённостям после встречи и сгруппировать запланированные дела", 19, "growing", "Корпоративные сервисы", "Персональная продуктивность"),
    Topic("tomorrow_meetings", "calendar_planning", "показать список встреч на следующий день для подготовки", 23, "stable", "Корпоративные сервисы", "Персональная продуктивность"),
    Topic("email_to_project_ticket", "task_management", "создать и актуализировать тикеты Project на основе входящих писем", 26, "growing", "Проектный бизнес", "Управление проектами"),
    Topic("isup_project_status_monitoring", "monitoring_automation", "настроить мониторинг, периодически контролировать статусы проектов в ИСУП и сообщать о важных переходах", 24, "growing", "Проектный бизнес", "Управление проектами"),
    Topic("control_chitchat", "other", "обсудить нерабочую тему без бизнес-задачи", 10, "stable", "Не указано", "Не указано", False),
    Topic("control_vague", "other", "сделать что-нибудь полезное без контекста и критериев результата", 10, "stable", "Не указано", "Не указано", False),
    Topic("control_multi_intent", "other", "одновременно найти клиента, написать письмо, создать встречу и выгрузить отчёт", 10, "stable", "Не указано", "Не указано", False),
]

PREFIXES = [
    "Помоги",
    "Нужно",
    "Пожалуйста, помоги",
    "Хочу",
    "Требуется",
    "Сможешь",
    "Прошу",
    "Необходимо",
]
DETAILS = ["Укажи источник каждого результата.", "Сделай результат кратким и структурированным.", "Если данных не хватает, перечисли, что нужно уточнить.", "Сохрани деловой стиль и выдели следующие действия.", "Не придумывай отсутствующие сведения."]
CONTEXT = " ".join([
    "Контекст содержит выдержки из корпоративной базы знаний, переписки и описаний процессов.",
    "Данные могут включать проекты, роли участников, историю изменений и внутренние комментарии.",
    "Необходимо учитывать ограничения доступа и использовать только приложенные сведения.",
    "Результат должен быть проверяемым, структурированным и пригодным для дальнейшей работы.",
]) + " "


def query_for(topic: Topic, variant: int) -> str:
    return f"{PREFIXES[variant % len(PREFIXES)]} {topic.intent}. {DETAILS[variant % len(DETAILS)]}"


def content_for(query: str, target_tokens: int) -> str:
    target_chars = max(len(query), int(target_tokens * 3.1))
    context = (CONTEXT * math.ceil(target_chars / len(CONTEXT)))[:target_chars]
    return f"<context>\n{context}\n</context>\n<user_query>\n{query}\n</user_query>"


def day_for(topic: Topic, variant: int) -> int:
    fraction = (variant + 1) / (topic.volume + 1)
    if topic.trend == "growing":
        return min(41, int(41 * math.sqrt(fraction)))
    if topic.trend == "declining":
        return min(41, int(41 * (fraction**2)))
    return (variant * 11 + topic.volume * 3) % 42


def event_for(topic: Topic, topic_index: int, variant: int, target_tokens: int, answers: bool) -> dict:
    query = query_for(topic, variant)
    index = topic_index * 1000 + variant
    occurred_at = BASE_DAY + timedelta(days=day_for(topic, variant), hours=index % 9, minutes=index * 7 % 60)
    answered = answers and index % 6 == 0
    failed = answered and index % 29 == 0
    response = None
    if answered:
        response = {
            "content": f"Результат по задаче «{topic.intent}». Собраны доступные данные, ограничения и следующие действия.",
            "usage": {"prompt_tokens": target_tokens, "completion_tokens": 180, "total_tokens": target_tokens + 180},
        }
    return {
        "external_id": f"krok-{topic.label}-{variant:03d}",
        "agent_id": AGENTS[topic_index % len(AGENTS)],
        "user_id": f"user-{index % 47 + 1:03d}",
        "team": topic.team,
        "direction": topic.direction,
        "is_synthetic": True,
        "occurred_at": occurred_at.isoformat().replace("+00:00", "Z"),
        "request": {
            "model": MODELS[index % len(MODELS)],
            "stream": bool(index % 2),
            "messages": [
                {"role": "system", "content": "Ты — корпоративный ИИ-ассистент. Не выдумывай факты."},
                {"role": "user", "content": content_for(query, target_tokens)},
            ],
        },
        "response": response,
        "execution_status": "error" if failed else ("success" if answered else "unknown"),
        "latency_ms": 1800 + index % 17 * 220 if answered else None,
        "rating": 2 if failed else (4 + index % 2 if answered else None),
    }


def pairs(target_tokens: int, answers: bool) -> Iterable[tuple[dict, dict]]:
    for topic_index, topic in enumerate(TOPICS):
        for variant in range(topic.volume):
            event = event_for(topic, topic_index, variant, target_tokens, answers)
            yield event, {
                "external_id": event["external_id"],
                "query": query_for(topic, variant),
                "category": topic.category,
                "scenario_label": topic.label,
                "supplied_topic": topic.supplied,
                "target_prompt_tokens": target_tokens,
            }


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as output:
        for row in rows:
            output.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_quick() -> dict:
    generated = list(pairs(1_500, True))
    events, truth = [x[0] for x in generated], [x[1] for x in generated]
    labels = {row["external_id"]: {"category": row["category"], "scenario_label": row["scenario_label"]} for row in truth}
    validation, validation_labels = [], {}
    for index, topic in enumerate(TOPICS):
        for variant in range(3):
            external_id = f"validation-{index:02d}-{variant}"
            validation.append({"external_id": external_id, "query": query_for(topic, variant + 50), "expected_category": topic.category})
            validation_labels[external_id] = topic.label
    write_jsonl(DATA_DIR / "demo_events.jsonl", events)
    (DATA_DIR / "demo_labels.json").write_text(json.dumps(labels, ensure_ascii=False, indent=2), encoding="utf-8")
    (DATA_DIR / "demo_truth.json").write_text(json.dumps(truth, ensure_ascii=False, indent=2), encoding="utf-8")
    write_jsonl(DATA_DIR / "validation_events.jsonl", validation)
    (DATA_DIR / "validation_labels.json").write_text(json.dumps(validation_labels, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = {"profile": "quick", "events": len(events), "supplied_topics": 35, "control_topics": 3, "target_average_prompt_tokens": 1_500, "is_synthetic": True}
    (DATA_DIR / "demo_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def write_compliant(output: Path) -> dict:
    output.parent.mkdir(parents=True, exist_ok=True)
    generated = pairs(100_000, False)
    count = 0
    with output.open("w", encoding="utf-8", newline="\n") as stream:
        for event, _truth in generated:
            stream.write(json.dumps(event, ensure_ascii=False) + "\n")
            count += 1
    manifest = {"profile": "compliant", "events": count, "supplied_topics": 35, "control_topics": 3, "target_average_prompt_tokens": 100_000, "is_synthetic": True, "output": str(output)}
    output.with_suffix(".manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=["quick", "compliant"], default="quick")
    parser.add_argument("--output", type=Path, default=DATA_DIR / "compliant_events_100k.jsonl")
    args = parser.parse_args()
    manifest = write_quick() if args.profile == "quick" else write_compliant(args.output)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
