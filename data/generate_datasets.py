"""Deterministic synthetic dataset generator for the analytics MVP.

Produces (all under ``data/``):
  - demo_events.jsonl        list of EventCreate objects (contract section 5.2)
  - demo_labels.json         external_id -> {category, scenario_label} ground truth
                             (sidecar, NOT fed to the analyzer; used by metrics)
  - validation_events.jsonl  {external_id, query, expected_category}
  - validation_labels.json   external_id -> expected_scenario_label

Design goals:
  * 31 source topics (28 real-category + 3 "other"), >= 16 formulations each;
  * keyword-rich phrasings so the rule-based classifier is correct offline;
  * tight intra-topic / distinct cross-topic phrasings so char-ngram TF-IDF
    clusters each topic separately;
  * >= 465 events, unique external_id, timestamps spread over >= 30 days,
    >= 10 oversized examples, >= 20 ambiguous / multi-intent examples;
  * response always null (no agent answers are synthesised);
  * agent_id == "synthetic-demo-agent".

Run:  PYTHONPATH=backend python3 data/generate_datasets.py
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List

DATA_DIR = Path(__file__).resolve().parent
AGENT_ID = "synthetic-demo-agent"
BASE_DAY = datetime(2026, 6, 8, tzinfo=timezone.utc)  # ~46 days before 2026-07-24
MODELS = ["DeepSeek-V4-Flash", "GigaChat-Pro", "YandexGPT-4", "T-lite", "Qwen2.5-72B", "Llama-3.1-70B"]
N_PER_TOPIC = 16

# --------------------------------------------------------------------------- #
# Slot pools (each >= 16 values; none contain category keyword stems unless the
# template intends them to).
# --------------------------------------------------------------------------- #
WHO = ["команды", "коллег", "отдела продаж", "руководителей", "партнёров",
       "проектной группы", "бухгалтерии", "подрядчика", "топ-менеджеров",
       "юристов", "аналитиков", "заказчика", "службы поддержки", "HR-отдела",
       "маркетологов", "дизайнеров"]
WHEN = ["понедельник", "вторник", "среду", "четверг", "пятницу", "следующую неделю",
        "утро", "вечер", "14:00", "10 утра", "после обеда", "конец недели",
        "завтра", "послезавтра", "начало месяца", "ближайшие дни"]
EVENT = ["созвоне", "планёрке", "презентации", "обеде", "конференции", "тренинге",
         "собеседовании", "дежурстве", "отпуске", "командировке", "корпоративе",
         "вебинаре", "звонке", "интервью", "демонстрации", "экскурсии"]
WHAT_PRICE = ["ноутбуков", "серверов", "авиабилетов", "поставщиков", "сырья",
              "акций компании", "валюты", "конкурентов", "облачных услуг",
              "подписок", "комплектующих", "топлива", "металлов", "недвижимости",
              "логистики", "аренды"]
WHAT_TASK = ["интеграции", "релиза", "бэклога", "инцидента", "доработки", "миграции",
             "тестирования", "онбординга", "закупки", "аудита", "рефакторинга",
             "поставки", "внедрения", "обновления", "поддержки", "исправления"]
WHAT_PROJECT = ["нового сайта", "мобильного приложения", "CRM-системы", "склада",
                "портала", "маркетплейса", "дашборда", "публичного API", "биллинга",
                "документооборота", "чат-бота", "витрины", "личного кабинета",
                "платёжного шлюза", "системы доставки", "базы знаний"]
PERIOD = ["сегодня", "вчера", "эту неделю", "прошлую неделю", "месяц", "квартал",
          "март", "апрель", "май", "июнь", "полугодие", "год",
          "последние 7 дней", "выходные", "праздники", "первый квартал"]
WHAT_REP = ["продажам", "выручке", "расходам", "марже", "конверсии", "трафику",
            "заявкам", "отгрузкам", "закупкам", "возвратам", "KPI", "воронке",
            "филиалам", "менеджерам", "регионам", "категориям"]
WHAT_DOC = ["договора", "политики", "инструкции", "регламента", "статьи",
            "презентации", "протокола", "спецификации", "мануала", "обзора",
            "исследования", "методички", "гайда", "должностной", "брифа", "устава"]
WHAT_MEET = ["планёрки", "ретро", "созвона", "воркшопа", "совещания", "стратсессии",
             "питча", "демо", "стендапа", "брейнсторма", "ревью", "синка",
             "интервью", "защиты", "консилиума", "переклички"]
WHAT_ORG = ["Ромашка", "Технопром", "СеверСталь", "АгроХолдинг", "МедиаГрупп",
            "ФинТех", "СтройИнвест", "ЭкоЛогистика", "НефтеГаз", "ТрансСервис",
            "БиоФарм", "ЦифроБанк", "ТелекомПлюс", "ЭнергоСбыт", "АвтоМир", "ГидроМаш"]
WHAT_TOPIC = ["импортозамещения", "кибербезопасности", "ИИ в бизнесе",
              "удалённой работы", "ESG-повестки", "блокчейна", "интернет-маркетинга",
              "цепочек поставок", "налоговой реформы", "стартап-экосистемы",
              "венчурных инвестиций", "бизнес-процессов", "облачных платформ",
              "больших данных", "робототехники", "цифровой трансформации"]
WHAT_DATA = ["продаж", "пользователей", "трафика", "заказов", "платежей", "логов",
             "кликов", "сессий", "подписчиков", "отказов", "конверсий", "выручки",
             "остатков", "обращений", "доставок", "регистраций"]
WHAT_PROD = ["новом смартфоне", "ноутбуке", "наушниках", "сервисе доставки",
             "приложении", "подписке", "онлайн-курсе", "отеле", "ресторане",
             "автомобиле", "фитнес-клубе", "банке", "страховке", "маркетплейсе",
             "провайдере", "кофейне"]
WHAT_ERR = ["ошибка 500", "таймаут запроса", "утечка памяти", "дедлок",
            "сбой синхронизации", "потеря пакетов", "краш приложения", "зависание",
            "сбой авторизации", "переполнение диска", "конфликт версий",
            "сбой оплаты", "отказ сервиса", "повреждение файла", "сбой импорта",
            "падение сервера"]
WHAT_TERM = ["кэш", "контейнеризация", "индекс базы", "вебхук", "очередь сообщений",
             "балансировщик нагрузки", "микросервис", "токен доступа", "шифрование",
             "репликация", "виртуализация", "шлюз приложений", "непрерывная поставка",
             "нормализация", "шардирование", "идемпотентность"]
WHAT_SYS = ["кэш", "планировщик", "сборщик мусора", "очередь сообщений",
            "система логирования", "балансировщик нагрузки", "конвейер сборки",
            "оркестратор", "кэширующий слой", "механизм блокировок", "движок поиска",
            "система прав", "шина событий", "кластер", "процесс репликации", "буфер обмена"]
NEUTRAL = ["сделке", "договору", "заказу", "поставке", "оплате", "обращению",
           "клиенту", "проекту", "вопросу", "запросу", "услуге", "продукту",
           "тарифу", "гарантии", "возврату", "счёту"]
CHAT = ["жизни", "погоде", "планах на выходные", "хобби", "путешествиях", "кино",
        "музыке", "спорте", "книгах", "еде", "природе", "космосе", "истории",
        "будущем", "искусстве", "фотографии"]
VAGUE = ["Помоги мне разобраться с этим", "Сделай как считаешь нужным",
         "Разберись с этим сам", "Сделай что-нибудь полезное", "Продолжи как раньше",
         "Сделай на своё усмотрение", "Займись этим", "Действуй по обстоятельствам",
         "Сделай всё необходимое", "Возьми это на себя", "Реши как лучше",
         "Организуй это самостоятельно", "Доведи до готовности", "Сделай красиво",
         "Приведи в порядок", "Оформи как обычно"]

# --------------------------------------------------------------------------- #
# Topic definitions: (label, category, template with a single {} slot, pool)
# --------------------------------------------------------------------------- #
TOPICS = [
    # calendar_planning
    ("cal_meeting_slot", "calendar_planning", "Найди общий свободный слот для встречи {}", WHO),
    ("cal_reschedule", "calendar_planning", "Перенеси встречу в календаре на {}", WHEN),
    ("cal_reminder", "calendar_planning", "Поставь напоминание о {}", EVENT),
    # monitoring_automation
    ("mon_email", "monitoring_automation", "Настрой периодический мониторинг входящих писем от {}", WHO),
    ("mon_price", "monitoring_automation", "Отслеживай изменение цен и присылай уведомления по {}", WHAT_PRICE),
    ("mon_deadline", "monitoring_automation", "Настрой периодические уведомления о приближении дедлайнов {}", WHAT_TASK),
    # task_management
    ("task_jira", "task_management", "Создай задачу в Jira для {}", WHO),
    ("task_ticket", "task_management", "Обнови статус задачи и тикета по {}", WHAT_TASK),
    ("task_project", "task_management", "Составь план задач в системе project для {}", WHAT_PROJECT),
    # reporting_export
    ("rep_excel_sales", "reporting_export", "Выгрузи отчёт по продажам за {} в Excel", PERIOD),
    ("rep_pdf_summary", "reporting_export", "Сформируй сводный отчёт по {} и экспортируй в PDF", WHAT_REP),
    ("rep_csv_export", "reporting_export", "Экспортируй выгрузку данных дашборда по {} в CSV", WHAT_REP),
    # summarization
    ("sum_document", "summarization", "Сделай краткое саммари документа {}", WHAT_DOC),
    ("sum_meeting_notes", "summarization", "Подготовь краткую сводку итогов встречи по итогам {}", WHAT_MEET),
    ("sum_emails", "summarization", "Сделай краткую сводку писем за {}", PERIOD),
    # information_search
    ("info_contacts", "information_search", "Найди контакты {}", WHO),
    ("info_company", "information_search", "Найди и собери информацию о компании {}", WHAT_ORG),
    ("info_docs", "information_search", "Организуй поиск и найди документы по теме {}", WHAT_TOPIC),
    # data_analysis
    ("data_sql", "data_analysis", "Составь SQL-запрос к таблице базы данных по {}", WHAT_DATA),
    ("data_metrics", "data_analysis", "Посчитай ключевые метрики и проведи анализ данных по {}", WHAT_DATA),
    ("data_table", "data_analysis", "Проведи анализ данных таблицы по {}", WHAT_DATA),
    # text_generation
    ("text_letter", "text_generation", "Напиши деловое письмо для {}", WHO),
    ("text_reply", "text_generation", "Сформулируй ответное письмо по {}", NEUTRAL),
    ("text_review", "text_generation", "Напиши развёрнутый отзыв о {}", WHAT_PROD),
    ("text_post", "text_generation", "Напиши и сформулируй текст поста для соцсетей про {}", WHAT_TOPIC),
    # knowledge_explanation
    ("kn_why", "knowledge_explanation", "Объясни, почему возникает {}", WHAT_ERR),
    ("kn_what", "knowledge_explanation", "Расскажи, что такое {}", WHAT_TERM),
    ("kn_how", "knowledge_explanation", "Объясни и расскажи, как устроен {}", WHAT_SYS),
    # other
    ("other_chitchat", "other", "Давай просто пообщаемся о {}", CHAT),
    ("other_multi_intent", "other", "Найди контакты клиента и напиши им письмо по {}", NEUTRAL),
    ("other_vague", "other", "{}", VAGUE),
]


def _queries_for(template: str, pool: List[str], n: int) -> List[str]:
    out: List[str] = []
    i = 0
    while len(out) < n:
        value = pool[i % len(pool)]
        suffix = "" if i < len(pool) else f" (вариант {i // len(pool) + 1})"
        candidate = template.format(value) + suffix
        if candidate not in out:
            out.append(candidate)
        i += 1
        if i > n * 4:  # safety
            break
    return out


def _timestamp(index: int) -> str:
    # Spread across ~46 days, cycling hours for realism.
    day = index % 46
    hour = 8 + (index % 10)
    minute = (index * 7) % 60
    ts = BASE_DAY + timedelta(days=day, hours=hour - 8, minutes=minute)
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


def _oversized_content(query: str) -> str:
    filler = ("Ниже приведён большой технический контекст, скопированный из "
              "корпоративной базы знаний и переписки. ") * 750
    return (
        "### Задача\nИспользуй приведённый контекст для ответа.\n"
        f"<context>\n{filler}\n</context>\n"
        f"<user_query>\n{query}\n</user_query>"
    )


def _messages_for(index: int, query: str, oversized: bool) -> List[Dict[str, str]]:
    if oversized:
        return [{"role": "user", "content": _oversized_content(query)}]
    kind = index % 5
    if kind == 0:
        return [{"role": "user", "content": query}]
    if kind == 1:
        return [{"role": "system", "content": "Ты — корпоративный ассистент."},
                {"role": "user", "content": query}]
    if kind == 2:
        return [{"role": "user", "content": "Здравствуйте, есть вопрос."},
                {"role": "assistant", "content": "Конечно, слушаю вас."},
                {"role": "user", "content": query}]
    if kind == 3:
        ctx = "Небольшая справочная заметка по теме запроса для контекста."
        return [{"role": "user",
                 "content": f"### Контекст\n<context>\n{ctx}\n</context>\n"
                            f"<user_query>\n{query}\n</user_query>"}]
    return [{"role": "system", "content": "Отвечай кратко и по делу."},
            {"role": "user", "content": query}]


def _event(index: int, external_id: str, query: str, oversized: bool) -> Dict:
    return {
        "external_id": external_id,
        "agent_id": AGENT_ID,
        "occurred_at": _timestamp(index),
        "request": {
            "model": MODELS[index % len(MODELS)],
            "stream": bool(index % 2),
            "messages": _messages_for(index, query, oversized),
        },
        "response": None,
        "execution_status": "unknown",
        "latency_ms": None,
        "rating": None,
    }


def build_demo():
    events: List[Dict] = []
    labels: Dict[str, Dict[str, str]] = {}
    # (query, category, scenario_label) truth for metrics
    truth: List[Dict[str, str]] = []

    idx = 0
    # base formulations
    per_topic_queries: Dict[str, List[str]] = {}
    for label, category, template, pool in TOPICS:
        queries = _queries_for(template, pool, N_PER_TOPIC)
        per_topic_queries[label] = (category, queries)  # type: ignore
        for q in queries:
            ext = f"demo-{idx:05d}"
            events.append(_event(idx, ext, q, oversized=False))
            labels[ext] = {"category": category, "scenario_label": label}
            truth.append({"external_id": ext, "query": q, "category": category,
                          "scenario_label": label, "oversized": False})
            idx += 1

    # oversized extras: one per selected real-category topic (>= 15 total)
    oversized_labels = [lbl for lbl, cat, _t, _p in TOPICS if cat != "other"][:15]
    for label in oversized_labels:
        category, queries = per_topic_queries[label]  # type: ignore
        q = queries[0]
        ext = f"demo-{idx:05d}"
        events.append(_event(idx, ext, q, oversized=True))
        labels[ext] = {"category": category, "scenario_label": label}
        truth.append({"external_id": ext, "query": q, "category": category,
                      "scenario_label": label, "oversized": True})
        idx += 1

    return events, labels, truth


def build_validation():
    # 5 fresh formulations for a spread of real-category topics (>= 60 records).
    chosen = [t for t in TOPICS if t[1] != "other"]
    records = []
    labels: Dict[str, str] = {}
    vidx = 0
    for label, category, template, pool in chosen:
        # take slot values from the tail so they differ from demo's head usage
        vals = list(reversed(pool))[:5]
        for value in vals:
            query = template.format(value)
            ext = f"val-{vidx:03d}"
            records.append({"external_id": ext, "query": query, "expected_category": category})
            labels[ext] = label
            vidx += 1
            if vidx >= 140:
                break
    return records, labels


def write_all():
    events, demo_labels, truth = build_demo()
    val_records, val_labels = build_validation()

    (DATA_DIR / "demo_events.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in events) + "\n", encoding="utf-8")
    (DATA_DIR / "demo_labels.json").write_text(
        json.dumps(demo_labels, ensure_ascii=False, indent=2), encoding="utf-8")
    (DATA_DIR / "demo_truth.json").write_text(
        json.dumps(truth, ensure_ascii=False, indent=2), encoding="utf-8")
    (DATA_DIR / "validation_events.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in val_records) + "\n", encoding="utf-8")
    (DATA_DIR / "validation_labels.json").write_text(
        json.dumps(val_labels, ensure_ascii=False, indent=2), encoding="utf-8")

    return events, demo_labels, truth, val_records, val_labels


if __name__ == "__main__":
    events, demo_labels, truth, val_records, val_labels = write_all()
    n_topics = len(set(t["scenario_label"] for t in truth))
    n_oversized = sum(1 for t in truth if t["oversized"])
    n_ambig = sum(1 for t in truth if t["scenario_label"] in ("other_multi_intent", "other_chitchat", "other_vague"))
    print(f"demo_events: {len(events)} | topics: {n_topics} | oversized: {n_oversized} "
          f"| other(ambig/vague/multi): {n_ambig}")
    print(f"validation_events: {len(val_records)} | validation scenario labels: {len(set(val_labels.values()))}")
    days = sorted(set(e['occurred_at'][:10] for e in events))
    print(f"distinct days: {len(days)} ({days[0]} .. {days[-1]})")
    # min formulations per topic
    from collections import Counter
    per = Counter(t["scenario_label"] for t in truth)
    print("min formulations/topic:", min(per.values()), "| max:", max(per.values()))
