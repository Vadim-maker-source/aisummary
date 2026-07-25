"""Validate project datasets with the real backend analytics implementation."""

from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
DATA_DIR = ROOT / "data"
sys.path.insert(0, str(BACKEND))

from app.analytics import embedding_client, llm_client  # noqa: E402
from app.analytics.public import analyze_event, discover_scenarios  # noqa: E402
from app.analytics.schemas import (  # noqa: E402
    AnalysisInput,
    Category,
    ScenarioInputRecord,
)
from app.schemas.events import EventCreate  # noqa: E402

CATEGORY_ACCURACY_MIN = 0.75
SCENARIO_PAIRWISE_F1_MIN = 0.65
PROBLEM_RECALL_MIN = 0.90


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]


def _analysis_input(event: dict[str, Any]) -> AnalysisInput:
    response = event.get("response") or {}
    usage = response.get("usage") or {}
    return AnalysisInput(
        event_id=event["external_id"],
        messages=event["request"]["messages"],
        model=event["request"].get("model"),
        prompt_tokens=usage.get("prompt_tokens"),
    )


def _pairwise(
    expected: dict[str, str],
    predicted: dict[str, str],
) -> dict[str, float | int]:
    tp = fp = fn = 0
    ids = list(expected)
    for left, right in combinations(ids, 2):
        same_expected = expected[left] == expected[right]
        same_predicted = (
            left in predicted
            and right in predicted
            and predicted[left] == predicted[right]
        )
        if same_expected and same_predicted:
            tp += 1
        elif same_predicted and not same_expected:
            fp += 1
        elif same_expected and not same_predicted:
            fn += 1
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tp": tp,
        "fp": fp,
        "fn": fn,
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def validate() -> dict[str, Any]:
    # The offline baseline must never spend money or depend on network state.
    llm_client.is_configured = lambda: False
    embedding_client.is_configured = lambda: False

    demo = _load_jsonl(DATA_DIR / "demo_events.jsonl")
    validation = _load_jsonl(DATA_DIR / "validation_events.jsonl")
    labels_list = _load_json(DATA_DIR / "validation_labels.json")
    labels = {row["external_id"]: row for row in labels_list}
    manifest_doc = _load_json(DATA_DIR / "generation_manifest.json")
    manifest = {
        row["external_id"]: row
        for row in manifest_doc["records"]
    }
    metadata = _load_json(DATA_DIR / "dataset_metadata.json")

    schema_errors: list[dict[str, str]] = []
    ids: list[str] = []
    for event in demo + validation:
        ids.append(event.get("external_id", ""))
        try:
            EventCreate.model_validate(event)
        except Exception as exc:
            schema_errors.append(
                {
                    "external_id": event.get("external_id", ""),
                    "error": str(exc),
                }
            )

    extraction_mismatches: list[str] = []
    validation_results: dict[str, Any] = {}
    problem_counts: Counter[str] = Counter()
    intended_problem_counts: Counter[str] = Counter()
    intended_problem_detected: Counter[str] = Counter()

    for event in demo + validation:
        result = await analyze_event(_analysis_input(event), [])
        expected_query = manifest[event["external_id"]]["effective_query"]
        if result.effective_query != expected_query:
            extraction_mismatches.append(event["external_id"])
        if event["external_id"] in labels:
            validation_results[event["external_id"]] = result
        reasons = {reason.value for reason in result.query_problem_reasons}
        for reason in reasons:
            problem_counts[reason] += 1
        intended = manifest[event["external_id"]].get("intended_problem_reason")
        if intended:
            intended_problem_counts[intended] += 1
            if intended in reasons:
                intended_problem_detected[intended] += 1

    correct = 0
    confusion: Counter[tuple[str, str]] = Counter()
    for external_id, result in validation_results.items():
        expected = labels[external_id]["expected_category"]
        predicted = result.category.value
        correct += expected == predicted
        confusion[(expected, predicted)] += 1
    category_accuracy = correct / len(validation_results)
    unclassified_rate = sum(
        result.category == Category.other
        for result in validation_results.values()
    ) / len(validation_results)

    records: list[ScenarioInputRecord] = []
    considered: dict[str, str] = {}
    for event in validation:
        external_id = event["external_id"]
        expected_category = labels[external_id]["expected_category"]
        if expected_category == Category.other.value:
            continue
        records.append(
            ScenarioInputRecord(
                event_id=external_id,
                effective_query=validation_results[external_id].effective_query,
                category=Category(expected_category),
            )
        )
        considered[external_id] = labels[external_id][
            "expected_scenario_label"
        ]
    discovery = await discover_scenarios(records)
    predicted_clusters: dict[str, str] = {}
    for index, scenario in enumerate(discovery.scenarios):
        for external_id in scenario.member_event_ids:
            predicted_clusters[external_id] = f"{scenario.category.value}:{index}"
    scenario_metrics = _pairwise(considered, predicted_clusters)

    demo_queries = {
        manifest[event["external_id"]]["effective_query"]
        for event in demo
    }
    validation_queries = {
        manifest[event["external_id"]]["effective_query"]
        for event in validation
    }
    exact_overlap = sorted(demo_queries & validation_queries)

    problem_recall = {
        reason: (
            intended_problem_detected[reason] / count
            if count
            else 1.0
        )
        for reason, count in sorted(intended_problem_counts.items())
    }
    hash_results = {}
    for name, expected in metadata["files"].items():
        path = DATA_DIR / name
        hash_results[name] = {
            "expected": expected["sha256"],
            "actual": _sha256(path),
            "match": expected["sha256"] == _sha256(path),
        }

    response_count = sum(event.get("response") is not None for event in demo)
    completed_count = sum(event.get("task_completed") is True for event in demo)
    saved_minutes = sum(
        int(event.get("estimated_minutes_saved") or 0)
        for event in demo
    )
    dimensions_complete = {
        key: sum(bool(event.get(key)) for event in demo)
        for key in ("user_id", "team", "direction")
    }
    synthetic_count = sum(event.get("is_synthetic") is True for event in demo)

    gates = {
        "schema": not schema_errors,
        "unique_ids": len(ids) == len(set(ids)),
        "extraction": not extraction_mismatches,
        "no_demo_validation_leakage": not exact_overlap,
        "all_categories": len(metadata["categories"]) == len(Category),
        "synthetic_marking": synthetic_count == len(demo),
        "business_dimensions": all(
            count == len(demo)
            for count in dimensions_complete.values()
        ),
        "response_coverage": response_count >= len(demo) // 6,
        "category_accuracy": category_accuracy >= CATEGORY_ACCURACY_MIN,
        "scenario_pairwise_f1": (
            scenario_metrics["f1"] >= SCENARIO_PAIRWISE_F1_MIN
        ),
        "problem_recall": all(
            value >= PROBLEM_RECALL_MIN
            for value in problem_recall.values()
        ),
        "hashes": all(row["match"] for row in hash_results.values()),
    }

    report = {
        "status": "pass" if all(gates.values()) else "fail",
        "gates": gates,
        "schema": {
            "demo_records": len(demo),
            "validation_records": len(validation),
            "schema_error_count": len(schema_errors),
            "schema_error_examples": schema_errors[:5],
            "duplicate_external_id_count": len(ids) - len(set(ids)),
            "extraction_mismatch_count": len(extraction_mismatches),
        },
        "coverage": {
            "categories": metadata["categories"],
            "category_count": len(metadata["categories"]),
            "scenario_count_including_other": metadata[
                "scenario_count_including_other"
            ],
            "timestamp_span_days": metadata["timestamp_span_days"],
            "responses": response_count,
            "completed_tasks": completed_count,
            "estimated_hours_saved": round(saved_minutes / 60, 1),
            "synthetic_marked": synthetic_count,
            "dimensions_complete": dimensions_complete,
        },
        "edge_cases": {
            "intended": dict(sorted(intended_problem_counts.items())),
            "detected": dict(sorted(intended_problem_detected.items())),
            "recall": problem_recall,
            "all_backend_problem_counts": dict(sorted(problem_counts.items())),
        },
        "leakage": {
            "exact_query_overlap_count": len(exact_overlap),
            "exact_query_overlap_examples": exact_overlap[:5],
        },
        "offline_real_backend": {
            "category_accuracy": category_accuracy,
            "unclassified_rate": unclassified_rate,
            "category_correct": correct,
            "category_total": len(validation_results),
            "category_confusion_errors": {
                f"{expected} -> {predicted}": count
                for (expected, predicted), count in sorted(confusion.items())
                if expected != predicted
            },
            "scenario_pairwise_precision": scenario_metrics["precision"],
            "scenario_pairwise_recall": scenario_metrics["recall"],
            "scenario_pairwise_f1": scenario_metrics["f1"],
            "scenario_tp": scenario_metrics["tp"],
            "scenario_fp": scenario_metrics["fp"],
            "scenario_fn": scenario_metrics["fn"],
            "discovered_scenarios": len(discovery.scenarios),
            "unclustered_events": len(discovery.unclustered_event_ids),
        },
        "hashes": hash_results,
        "notes": [
            "Metrics are calculated by backend/app/analytics with the LLM disabled.",
            "Validation labels are never passed to the classifier.",
            "Synthetic outcomes measure dashboard mechanics, not real business ROI.",
        ],
    }
    _write_reports(report, demo, manifest)
    return report


def _write_reports(
    report: dict[str, Any],
    demo: list[dict[str, Any]],
    manifest: dict[str, dict[str, Any]],
) -> None:
    (DATA_DIR / "quality_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    backend = report["offline_real_backend"]
    edge = report["edge_cases"]
    coverage = report["coverage"]
    status = "PASS" if report["status"] == "pass" else "FAIL"
    md = f"""# Dataset Quality Report

Статус: **{status}**

## Структура и покрытие

- Demo: {report['schema']['demo_records']} событий.
- Validation: {report['schema']['validation_records']} событий.
- Категории: {coverage['category_count']} из {len(Category)}.
- Сценарии: {coverage['scenario_count_including_other']}.
- Ответы агента: {coverage['responses']}.
- Подтверждённые выполнения: {coverage['completed_tasks']}.
- Синтетическая оценка экономии: {coverage['estimated_hours_saved']} ч.
- Ошибки схемы: {report['schema']['schema_error_count']}.
- Повторяющиеся ID: {report['schema']['duplicate_external_id_count']}.
- Ошибки effective-query extraction: {report['schema']['extraction_mismatch_count']}.
- Точные пересечения demo/validation: {report['leakage']['exact_query_overlap_count']}.

## Edge cases, проверенные backend

| Причина | Заложено | Обнаружено | Recall |
|---|---:|---:|---:|
"""
    for reason, intended in edge["intended"].items():
        md += (
            f"| `{reason}` | {intended} | "
            f"{edge['detected'].get(reason, 0)} | "
            f"{edge['recall'][reason]:.4f} |\n"
        )
    md += f"""

## Offline baseline настоящего backend

| Метрика | Результат | Минимум |
|---|---:|---:|
| Category accuracy | {backend['category_accuracy']:.4f} | 0.75 |
| Unclassified rate | {backend['unclassified_rate']:.4f} | — |
| Scenario pairwise precision | {backend['scenario_pairwise_precision']:.4f} | — |
| Scenario pairwise recall | {backend['scenario_pairwise_recall']:.4f} | — |
| Scenario pairwise F1 | {backend['scenario_pairwise_f1']:.4f} | 0.65 |

Метрики рассчитаны функциями `backend/app/analytics` с отключённым LLM.
Validation labels не передаются классификатору. Показатели экономии времени
синтетические и проверяют механику дашборда, а не реальную отдачу бизнеса.
"""
    (DATA_DIR / "quality_report.md").write_text(
        md,
        encoding="utf-8",
        newline="\n",
    )

    categories = Counter(
        manifest[event["external_id"]]["expected_category"]
        for event in demo
    )
    scenarios = Counter(
        manifest[event["external_id"]]["expected_scenario_label"]
        for event in demo
    )
    failed = sum(event["execution_status"] == "error" for event in demo)
    completed = sum(event.get("task_completed") is True for event in demo)
    minutes = sum(
        int(event.get("estimated_minutes_saved") or 0)
        for event in demo
    )
    dashboard = f"""# Промпт-радар — преддемонстрационный отчёт

Источник: воспроизводимый синтетический `data/demo_events.jsonl`.
После импорта интерфейс пересчитает те же показатели по PostgreSQL.

## Ключевые показатели

- Запросов: {len(demo)}
- Категорий: {len(categories)}
- Сценариев в эталонной разметке: {len(scenarios)}
- Событий с ответом: {sum(event.get('response') is not None for event in demo)}
- Ошибок выполнения: {failed}
- Подтверждённых выполнений: {completed}
- Синтетическая оценка сэкономленного времени: {minutes / 60:.1f} ч

## Категории

| Категория | Запросы | Доля |
|---|---:|---:|
"""
    for category, count in categories.most_common():
        dashboard += f"| `{category}` | {count} | {count / len(demo):.1%} |\n"
    dashboard += """

## Топ сценариев

| Сценарий | Запросы |
|---|---:|
"""
    for scenario, count in scenarios.most_common(10):
        dashboard += f"| `{scenario}` | {count} |\n"
    dashboard += """

## Ограничение

Данные, ответы и экономия времени синтетические. Для доказательства реальной
эффективности после пилота нужны обезличенные production-логи и подтверждённые
пользователями результаты.
"""
    (DATA_DIR / "prompt-radar-report.md").write_text(
        dashboard,
        encoding="utf-8",
        newline="\n",
    )


def main() -> None:
    report = asyncio.run(validate())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["status"] == "pass" else 1)


if __name__ == "__main__":
    main()
