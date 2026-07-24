"""Build a reproducible one-sixth demo subset with synthetic agent answers."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent
SOURCE_PATH = DATA_DIR / "demo_events.jsonl"
TRUTH_PATH = DATA_DIR / "demo_truth.json"
OUTPUT_PATH = DATA_DIR / "demo_events_one_sixth_answered.jsonl"


def _after(query: str, marker: str, fallback: str) -> str:
    _, separator, tail = query.partition(marker)
    return tail.strip(" .") if separator and tail.strip(" .") else fallback


def answer_for(label: str, query: str) -> str:
    if label == "cal_meeting_slot":
        return (
            "Помогу подобрать время. Пришлите список участников, желаемую "
            "длительность встречи и допустимый диапазон дат. Если календари "
            "подключены, проверю пересечение свободных интервалов."
        )
    if label == "cal_reschedule":
        return (
            "Уточните название текущей встречи, новый день и точное время с "
            "часовым поясом. После подтверждения можно перенести событие и "
            "уведомить участников."
        )
    if label == "cal_reminder":
        subject = _after(query, "о ", "событии")
        return (
            f"Для напоминания о {subject} нужны дата, время и часовой пояс. "
            "Также укажите, за сколько минут или часов прислать уведомление."
        )
    if label == "mon_email":
        sender = _after(query, "от ", "нужного отправителя")
        return (
            f"Можно настроить мониторинг писем от {sender}. Уточните почтовый "
            "ящик, период проверки, дополнительные фильтры и канал уведомлений."
        )
    if label == "mon_price":
        subject = _after(query, "по ", "выбранному объекту")
        return (
            f"Для отслеживания цен по {subject} укажите источник данных, "
            "периодичность проверки и условие уведомления: любое изменение "
            "или превышение заданного порога."
        )
    if label == "mon_deadline":
        subject = _after(query, "дедлайнов ", "задачи")
        return (
            f"Настрою контроль дедлайна {subject}. Нужны дата завершения, "
            "частота проверки и интервалы напоминаний, например за 7, 3 и 1 день."
        )
    if label == "task_jira":
        target = _after(query, "для ", "команды")
        return (
            f"Для создания задачи в Jira для {target} пришлите проект, заголовок, "
            "описание, исполнителя, приоритет и срок. После этого подготовлю "
            "точные поля задачи."
        )
    if label == "task_ticket":
        subject = _after(query, "по ", "задаче")
        return (
            f"Уточните идентификатор тикета по {subject}, новый статус и "
            "комментарий к изменению. Без номера задачи нельзя безопасно "
            "обновить нужную запись."
        )
    if label == "task_project":
        subject = _after(query, "для ", "проекта")
        return (
            f"Черновой план для {subject}: определить цель и владельца, собрать "
            "требования, разбить работу на этапы, назначить исполнителей, "
            "поставить сроки и контрольные точки, затем провести приёмку."
        )
    if label == "rep_excel_sales":
        period = _after(query, "за ", "указанный период").replace(" в Excel", "")
        return (
            f"Подготовлю Excel-отчёт по продажам за {period}. Нужен источник "
            "данных и состав колонок. Базово включу дату, товар, менеджера, "
            "количество, выручку, скидку и итоговую сумму."
        )
    if label == "rep_pdf_summary":
        subject = query.removeprefix("Сформируй сводный отчёт по ").split(
            " и экспортируй"
        )[0]
        return (
            f"Для PDF-отчёта по {subject} пришлите исходные данные и период. "
            "Предлагаю структуру: ключевые показатели, динамика, отклонения, "
            "выводы и рекомендации."
        )
    if label == "rep_csv_export":
        subject = query.removeprefix(
            "Экспортируй выгрузку данных дашборда по "
        ).removesuffix(" в CSV")
        return (
            f"Для CSV-выгрузки по {subject} уточните период и фильтры. "
            "Файл сформирую в UTF-8 с заголовками колонок и ISO-датами."
        )
    if label == "sum_document":
        subject = _after(query, "документа ", "документа")
        return (
            f"Пришлите текст или файл {subject}. Я выделю цель, ключевые тезисы, "
            "цифры, решения и открытые вопросы, затем подготовлю краткое саммари."
        )
    if label == "sum_emails":
        period = _after(query, "за ", "выбранный период")
        return (
            f"Для сводки писем за {period} нужен доступ к сообщениям или их "
            "выгрузка. Сгруппирую переписку по темам, решениям, задачам, "
            "ответственным и срокам."
        )
    if label == "sum_meeting_notes":
        subject = _after(query, "встречи ", "встречи")
        return (
            f"Пришлите протокол или расшифровку {subject}. Итог оформлю блоками: "
            "решения, задачи, ответственные, сроки, риски и вопросы без ответа."
        )
    if label == "info_company":
        company = _after(query, "компании ", "компании")
        return (
            f"Для справки о компании {company} проверю официальный сайт, "
            "профиль деятельности, продукты, руководство, реквизиты и свежие "
            "публичные упоминания. Уточните, нужен краткий профиль или due diligence."
        )
    if label == "info_contacts":
        target = _after(query, "контакты ", "нужного человека")
        return (
            f"Уточните организацию и роль для поиска контактов {target}. "
            "Я буду использовать только разрешённые корпоративные или открытые "
            "источники и укажу источник найденных данных."
        )
    if label == "info_docs":
        subject = _after(query, "по теме ", "заданной теме")
        return (
            f"Для поиска документов по теме «{subject}» укажите доступные "
            "хранилища и желаемый период. Результат можно вернуть списком: "
            "название, ссылка, дата, автор и краткая аннотация."
        )
    if label == "data_table":
        subject = _after(query, "по ", "данным")
        return (
            f"Для анализа таблицы по {subject} загрузите CSV/XLSX и опишите "
            "целевую метрику. Проверю структуру, пропуски, выбросы, динамику, "
            "сегменты и статистически заметные отклонения."
        )
    if label == "data_metrics":
        subject = _after(query, "по ", "данным")
        return (
            f"Для расчёта метрик по {subject} нужны период, источник и определения "
            "показателей. Начну с объёма, уникальных объектов, конверсии, "
            "среднего значения, медианы и динамики относительно прошлого периода."
        )
    if label == "data_sql":
        subject = _after(query, "по ", "данным")
        return (
            f"Без схемы таблиц нельзя написать точный SQL по {subject}. "
            "Пришлите DDL или названия таблиц, ключей и нужных полей. "
            "После этого составлю запрос с параметрами и поясню план выполнения."
        )
    if label == "text_letter":
        target = _after(query, "для ", "получателя")
        return (
            f"Тема: Обсуждение дальнейших шагов\n\n"
            f"Добрый день!\n\nПредлагаю согласовать дальнейшие действия с "
            f"{target}. Подскажите, пожалуйста, удобное время и ответственного "
            "со стороны получателя.\n\nС уважением,\n[Имя]"
        )
    if label == "text_reply":
        subject = _after(query, "по ", "вопросу")
        return (
            f"Добрый день!\n\nСпасибо за сообщение по {subject}. Мы получили "
            "информацию и проверяем детали. Вернёмся с подтверждением и "
            "следующими шагами до [дата].\n\nС уважением,\n[Имя]"
        )
    if label == "text_post":
        subject = _after(query, "про ", "выбранную тему")
        return (
            f"{subject.capitalize()} меняет привычные подходы к работе: помогает "
            "ускорять процессы, прозрачнее принимать решения и снижать количество "
            "ручных операций. Главное — начинать с понятной задачи и измеримого результата."
        )
    if label == "text_review":
        subject = _after(query, "о ", "сервисе")
        return (
            f"Опыт использования {subject} в целом оказался положительным. "
            "Понравились понятный процесс и предсказуемый результат. Из улучшений "
            "я бы отметил более подробные уведомления и прозрачное описание сроков."
        )
    if label == "kn_what":
        term = _after(query, "что такое ", "этот термин").lower()
        definitions = {
            "вебхук": (
                "Вебхук — это HTTP-уведомление, которое одна система автоматически "
                "отправляет другой при наступлении события. Получатель публикует URL, "
                "а отправитель вызывает его, например после оплаты заказа."
            ),
            "репликация": (
                "Репликация — копирование и синхронизация данных между несколькими "
                "узлами. Она повышает доступность и скорость чтения, но требует "
                "контроля задержек и согласованности копий."
            ),
            "идемпотентность": (
                "Идемпотентность означает, что повторное выполнение одной операции "
                "даёт тот же итоговый эффект. В API это защищает от создания дублей "
                "при повторной отправке запроса."
            ),
        }
        return definitions.get(
            term,
            f"{term.capitalize()} — техническое понятие, для точного объяснения "
            "которого нужен контекст использования и ожидаемый уровень детализации.",
        )
    if label == "kn_how":
        if "балансировщик" in query.lower():
            return (
                "Балансировщик принимает входящие соединения и распределяет их "
                "между здоровыми экземплярами приложения. Он проверяет health-check, "
                "выбирает узел по алгоритму и исключает недоступные серверы."
            )
        return (
            "Система прав обычно строится из субъектов, ресурсов, действий и правил. "
            "Пользователю назначают роли, роли содержат разрешения, а каждое действие "
            "проверяется по принципу минимально необходимых привилегий."
        )
    if label == "kn_why":
        lowered = query.lower()
        if "таймаут" in lowered:
            return (
                "Таймаут возникает, когда операция не завершается за установленное "
                "время. Частые причины: медленный внешний сервис, перегрузка, блокировки "
                "БД, проблемы сети или слишком короткий лимит ожидания."
            )
        if "зависание" in lowered:
            return (
                "Зависание обычно связано с взаимной блокировкой, бесконечным циклом, "
                "ожиданием I/O без таймаута или исчерпанием пула ресурсов. Начните со "
                "стеков потоков, логов и метрик CPU, памяти и соединений."
            )
        return (
            "Повреждение файла возможно из-за незавершённой записи, сбоя диска, "
            "неверной кодировки, параллельного изменения или ошибки передачи. "
            "Проверьте контрольную сумму, логи записи и резервную копию."
        )
    if label == "other_chitchat":
        subject = _after(query, "о ", "чём-нибудь интересном")
        return (
            f"Давай поговорим о {subject}. Что тебе интереснее: последние новости, "
            "практический опыт или просто обмен мнениями?"
        )
    if label == "other_multi_intent":
        subject = _after(query, "по ", "вопросу")
        return (
            f"Здесь две задачи: найти корректные контакты клиента и подготовить "
            f"письмо по {subject}. Уточните компанию, получателя и желаемый результат "
            "письма — выполню их последовательно."
        )
    if label == "other_vague":
        return (
            "Нужно немного больше контекста: какой результат требуется, какие данные "
            "можно использовать, какой срок и что считается успешным выполнением?"
        )
    raise ValueError(f"Unsupported scenario label: {label}")


def approximate_tokens(text: str) -> int:
    return max(1, round(len(text) / 4))


def main() -> None:
    source_rows = [
        json.loads(line)
        for line in SOURCE_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    truth_by_id = {
        row["external_id"]: row
        for row in json.loads(TRUTH_PATH.read_text(encoding="utf-8"))
    }

    answered_rows = []
    for source in source_rows[5::6]:
        truth = truth_by_id[source["external_id"]]
        answer = answer_for(truth["scenario_label"], truth["query"])
        row = deepcopy(source)
        row["external_id"] = f"answered-{source['external_id']}"
        row["agent_id"] = "synthetic-demo-agent-with-answers"
        prompt_text = "\n".join(
            message["content"] for message in row["request"]["messages"]
        )
        prompt_tokens = approximate_tokens(prompt_text)
        completion_tokens = approximate_tokens(answer)
        row["response"] = {
            "content": answer,
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
        }
        row["execution_status"] = "success"
        row["latency_ms"] = 350 + len(answer) * 3
        answered_rows.append(row)

    OUTPUT_PATH.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False) + "\n"
            for row in answered_rows
        ),
        encoding="utf-8",
    )
    print(f"Created {OUTPUT_PATH} with {len(answered_rows)} answered events")


if __name__ == "__main__":
    main()
