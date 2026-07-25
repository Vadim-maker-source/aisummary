from __future__ import annotations

import csv
import io
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import dashboard

ReportFormat = Literal["pdf", "md", "csv", "json"]

CATEGORY_LABELS = {
    "text_generation": "Генерация текста",
    "information_search": "Поиск информации",
    "summarization": "Саммаризация",
    "data_analysis": "Анализ данных",
    "code_assistance": "Помощь с кодом",
    "reporting_export": "Отчёты и экспорт",
    "task_management": "Управление задачами",
    "monitoring_automation": "Мониторинг",
    "calendar_planning": "Планирование",
    "knowledge_explanation": "Объяснение знаний",
    "non_work_general": "Нерабочие и общие вопросы",
    "other": "Другое",
}

RECOMMENDATION_LABELS = {
    "automation": "Автоматизация",
    "agent": "Развитие агента",
    "training": "Обучение пользователей",
}


@dataclass(frozen=True)
class ReportArtifact:
    content: bytes
    media_type: str
    filename: str


async def build_report(
    session: AsyncSession,
    report_format: ReportFormat,
) -> ReportArtifact:
    generated_at = datetime.now(UTC)
    report = await _collect_report(session, generated_at)
    stamp = generated_at.strftime("%Y%m%d-%H%M%S")

    if report_format == "json":
        content = json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8")
        media_type = "application/json"
    elif report_format == "csv":
        content = _render_csv(report)
        media_type = "text/csv; charset=utf-8"
    elif report_format == "md":
        content = _render_markdown(report).encode("utf-8")
        media_type = "text/markdown; charset=utf-8"
    else:
        content = _render_pdf(report)
        media_type = "application/pdf"

    return ReportArtifact(
        content=content,
        media_type=media_type,
        filename=f"prompt-radar-report-{stamp}.{report_format}",
    )


async def _collect_report(
    session: AsyncSession,
    generated_at: datetime,
) -> dict:
    summary = await dashboard.get_summary(
        session,
        date_from=None,
        date_to=None,
    )
    categories = await dashboard.get_category_summaries(session)
    problems = await dashboard.get_problems(session)
    trends = await dashboard.get_scenario_trends(session, window_days=7)
    scenarios = await dashboard.list_scenarios(
        session,
        category=None,
        page=1,
        page_size=100,
    )
    decisions = await dashboard.get_decision_support(session)
    effectiveness = {
        dimension: (
            await dashboard.get_effectiveness(
                session,
                dimension=dimension,
            )
        ).model_dump(mode="json")
        for dimension in ("direction", "team", "agent_id")
    }
    return {
        "generated_at": generated_at.isoformat(),
        "summary": summary.model_dump(mode="json"),
        "categories": categories.model_dump(mode="json")["items"],
        "problems": problems.model_dump(mode="json"),
        "scenario_trends": trends.model_dump(mode="json"),
        "scenarios": scenarios.model_dump(mode="json"),
        "decision_support": decisions.model_dump(mode="json"),
        "effectiveness": effectiveness,
    }


def _render_csv(report: dict) -> bytes:
    stream = io.StringIO()
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["Раздел", "Показатель", "Значение", "Описание"])
    for key, value in report["summary"].items():
        writer.writerow(["Сводка", key, value, ""])
    for item in report["categories"]:
        writer.writerow(
            [
                "Категории",
                CATEGORY_LABELS.get(item["category"], item["category"]),
                item["request_count"],
                item["summary"],
            ]
        )
    for item in report["problems"]["items"]:
        writer.writerow(
            ["Проблемы", item["label"], item["count"], f'{item["percentage"]}%']
        )
    for item in report["scenarios"]["items"]:
        writer.writerow(
            [
                "Сценарии",
                item["name"],
                item["request_count"],
                item["summary"],
            ]
        )
    for item in report["decision_support"]["items"]:
        writer.writerow(
            [
                "Рекомендации",
                item["title"],
                item["affected_requests"],
                f'{item["evidence"]} {item["action"]}',
            ]
        )
    return ("\ufeff" + stream.getvalue()).encode("utf-8")


def _render_markdown(report: dict) -> str:
    summary = report["summary"]
    lines = [
        "# Промпт-радар — аналитический отчёт",
        "",
        f"Сформирован: {report['generated_at']}",
        "",
        "## Ключевые показатели",
        "",
        f"- Запросов: {summary['total_requests']}",
        f"- Проанализировано: {summary['analyzed_requests']}",
        f"- Категорий: {summary['category_count']}",
        f"- Сценариев: {summary['scenario_count']}",
        f"- Доля проблемных запросов: {summary['query_problem_rate']}%",
        f"- Подтверждённых выполнений: {summary['completed_task_count']}",
        f"- Оценка сэкономленного времени: {summary['estimated_hours_saved']} ч",
        "",
        "## Категории",
        "",
        "| Категория | Запросы | Доля | Что делают пользователи |",
        "|---|---:|---:|---|",
    ]
    for item in report["categories"]:
        lines.append(
            "| "
            f"{CATEGORY_LABELS.get(item['category'], item['category'])} | "
            f"{item['request_count']} | {item['percentage']}% | "
            f"{_md_cell(item['summary'])} |"
        )

    lines.extend(
        [
            "",
            "## Топ проблем",
            "",
            "| Проблема | Количество | Доля |",
            "|---|---:|---:|",
        ]
    )
    for item in report["problems"]["items"]:
        lines.append(
            f"| {_md_cell(item['label'])} | {item['count']} | "
            f"{item['percentage']}% |"
        )

    lines.extend(["", "## Сценарии", ""])
    for item in report["scenarios"]["items"]:
        lines.extend(
            [
                f"### {item['name']}",
                "",
                f"{item['summary']}",
                "",
                f"- Категория: {CATEGORY_LABELS.get(item['category'], item['category'])}",
                f"- Запросов: {item['request_count']}",
                f"- Потенциал автоматизации: {item['automation_potential']}",
                f"- Следующее действие: {item['suggested_action']}",
                "",
            ]
        )

    lines.extend(["## Рекомендации", ""])
    for item in report["decision_support"]["items"]:
        lines.extend(
            [
                f"### {item['title']}",
                "",
                f"**Основание:** {item['evidence']}",
                "",
                f"**Действие:** {item['action']}",
                "",
            ]
        )
    for limitation in report["decision_support"]["data_limitations"]:
        lines.append(f"> Ограничение данных: {limitation}")
    return "\n".join(lines).strip() + "\n"


def _md_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _render_pdf(report: dict) -> bytes:
    regular_path, bold_path = _font_paths()
    pdfmetrics.registerFont(TTFont("ReportRegular", str(regular_path)))
    pdfmetrics.registerFont(TTFont("ReportBold", str(bold_path)))

    stream = io.BytesIO()
    document = SimpleDocTemplate(
        stream,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title="Промпт-радар - аналитический отчёт",
        author="Промпт-радар",
    )
    base = getSampleStyleSheet()
    title = ParagraphStyle(
        "ReportTitle",
        parent=base["Title"],
        fontName="ReportBold",
        fontSize=20,
        leading=25,
        textColor=colors.HexColor("#18181B"),
        alignment=TA_CENTER,
        spaceAfter=6 * mm,
    )
    heading = ParagraphStyle(
        "ReportHeading",
        parent=base["Heading2"],
        fontName="ReportBold",
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#18181B"),
        spaceBefore=4 * mm,
        spaceAfter=3 * mm,
    )
    body = ParagraphStyle(
        "ReportBody",
        parent=base["BodyText"],
        fontName="ReportRegular",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#3F3F46"),
    )
    small = ParagraphStyle(
        "ReportSmall",
        parent=body,
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#71717A"),
    )
    story = [
        Paragraph("Промпт-радар", title),
        Paragraph(
            "Аналитический отчёт по запросам к корпоративным ИИ-агентам",
            body,
        ),
        Spacer(1, 3 * mm),
        Paragraph(f"Сформирован: {report['generated_at']}", small),
        Paragraph("Ключевые показатели", heading),
    ]

    summary = report["summary"]
    metrics = [
        ["Запросов", "Проанализировано", "Категорий", "Сценариев"],
        [
            summary["total_requests"],
            summary["analyzed_requests"],
            summary["category_count"],
            summary["scenario_count"],
        ],
        ["Проблемные", "Выполнено задач", "Экономия времени", "Ответы агента"],
        [
            f'{summary["query_problem_rate"]}%',
            summary["completed_task_count"],
            f'{summary["estimated_hours_saved"]} ч',
            summary["response_count"],
        ],
    ]
    story.append(_pdf_table(metrics, [42 * mm] * 4, body, header_rows=(0, 2)))
    story.append(Paragraph("Проблемы", heading))
    problem_rows = [["Проблема", "Количество", "Доля"]]
    for item in report["problems"]["items"]:
        problem_rows.append(
            [item["label"], item["count"], f'{item["percentage"]}%']
        )
    story.append(
        _pdf_table(
            problem_rows,
            [112 * mm, 28 * mm, 28 * mm],
            body,
            header_rows=(0,),
        )
    )
    story.append(Paragraph("Категории", heading))
    category_rows = [["Категория", "Запросы", "Доля", "Описание"]]
    for item in report["categories"]:
        category_rows.append(
            [
                CATEGORY_LABELS.get(item["category"], item["category"]),
                item["request_count"],
                f'{item["percentage"]}%',
                item["summary"],
            ]
        )
    story.append(
        _pdf_table(
            category_rows,
            [38 * mm, 20 * mm, 18 * mm, 92 * mm],
            small,
            header_rows=(0,),
        )
    )

    story.extend([PageBreak(), Paragraph("Топ сценариев", heading)])
    scenario_rows = [["Сценарий", "Категория", "Запросы", "Действие"]]
    for item in report["scenarios"]["items"][:15]:
        scenario_rows.append(
            [
                item["name"],
                CATEGORY_LABELS.get(item["category"], item["category"]),
                item["request_count"],
                item["suggested_action"],
            ]
        )
    story.append(
        _pdf_table(
            scenario_rows,
            [60 * mm, 35 * mm, 18 * mm, 55 * mm],
            small,
            header_rows=(0,),
        )
    )

    story.append(Paragraph("Что делать дальше", heading))
    for item in report["decision_support"]["items"][:10]:
        kind = RECOMMENDATION_LABELS.get(item["kind"], item["kind"])
        story.extend(
            [
                Paragraph(f"<b>{kind}: {item['title']}</b>", body),
                Paragraph(item["evidence"], small),
                Paragraph(f"Действие: {item['action']}", small),
                Spacer(1, 2.5 * mm),
            ]
        )
    for limitation in report["decision_support"]["data_limitations"]:
        story.append(Paragraph(f"Ограничение данных: {limitation}", small))

    document.build(
        story,
        onFirstPage=_draw_pdf_footer,
        onLaterPages=_draw_pdf_footer,
    )
    return stream.getvalue()


def _draw_pdf_footer(canvas, document) -> None:
    canvas.saveState()
    canvas.setFont("ReportRegular", 7)
    canvas.setFillColor(colors.HexColor("#71717A"))
    canvas.drawRightString(
        A4[0] - 16 * mm,
        8 * mm,
        f"Страница {document.page}",
    )
    canvas.restoreState()


def _pdf_table(
    rows: list[list[object]],
    widths: list[float],
    paragraph_style: ParagraphStyle,
    *,
    header_rows: tuple[int, ...],
) -> Table:
    formatted = [
        [Paragraph(str(cell), paragraph_style) for cell in row]
        for row in rows
    ]
    table = Table(formatted, colWidths=widths, repeatRows=1)
    commands: list[tuple] = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D4D4D8")),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#FAFAFA")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    for row_index in header_rows:
        commands.extend(
            [
                ("BACKGROUND", (0, row_index), (-1, row_index), colors.HexColor("#EEF2FB")),
                ("TEXTCOLOR", (0, row_index), (-1, row_index), colors.HexColor("#28477F")),
            ]
        )
    table.setStyle(TableStyle(commands))
    return table


def _font_paths() -> tuple[Path, Path]:
    custom = os.getenv("REPORT_FONT_PATH")
    custom_bold = os.getenv("REPORT_FONT_BOLD_PATH")
    candidates = [
        (
            Path(custom) if custom else None,
            Path(custom_bold) if custom_bold else None,
        ),
        (
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ),
        (
            Path("C:/Windows/Fonts/arial.ttf"),
            Path("C:/Windows/Fonts/arialbd.ttf"),
        ),
    ]
    for regular, bold in candidates:
        if regular and bold and regular.is_file() and bold.is_file():
            return regular, bold
    raise RuntimeError(
        "No Unicode PDF font found. Configure REPORT_FONT_PATH and "
        "REPORT_FONT_BOLD_PATH."
    )
