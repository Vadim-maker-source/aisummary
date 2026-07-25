"""Read-only end-to-end quality audit of the current PostgreSQL analysis run."""

from __future__ import annotations

import argparse
import asyncio
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

from dotenv import load_dotenv  # noqa: E402
from sqlalchemy import select  # noqa: E402

load_dotenv(BACKEND / ".env")

from app.core.database import async_session_factory  # noqa: E402
from app.models.entities import (  # noqa: E402
    AgentEvent,
    AnalysisRun,
    EventAnalysis,
    Scenario,
    ScenarioMember,
)


def _pairwise(
    ids: list[str],
    expected: dict[str, str],
    predicted: dict[str, str],
) -> dict[str, float | int]:
    true_positive = false_positive = false_negative = 0
    for left, right in combinations(ids, 2):
        same_expected = expected[left] == expected[right]
        same_predicted = (
            left in predicted
            and right in predicted
            and predicted[left] == predicted[right]
        )
        if same_expected and same_predicted:
            true_positive += 1
        elif same_predicted and not same_expected:
            false_positive += 1
        elif same_expected and not same_predicted:
            false_negative += 1
    precision = (
        true_positive / (true_positive + false_positive)
        if true_positive + false_positive
        else 0.0
    )
    recall = (
        true_positive / (true_positive + false_negative)
        if true_positive + false_negative
        else 0.0
    )
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tp": true_positive,
        "fp": false_positive,
        "fn": false_negative,
    }


async def audit() -> dict[str, Any]:
    labels = json.loads(
        (DATA_DIR / "demo_labels.json").read_text(encoding="utf-8")
    )
    manifest_document = json.loads(
        (DATA_DIR / "generation_manifest.json").read_text(encoding="utf-8")
    )
    manifest = {
        row["external_id"]: row
        for row in manifest_document["records"]
        if row["split"] == "demo"
    }

    async with async_session_factory() as session:
        events = list((await session.scalars(select(AgentEvent))).all())
        analyses = list((await session.scalars(select(EventAnalysis))).all())
        current_run = await session.scalar(
            select(AnalysisRun).where(AnalysisRun.is_current.is_(True))
        )
        if current_run is None:
            raise RuntimeError("PostgreSQL has no current analysis run")
        scenarios = list(
            (
                await session.scalars(
                    select(Scenario).where(
                        Scenario.analysis_run_id == current_run.id
                    )
                )
            ).all()
        )
        scenario_ids = [scenario.id for scenario in scenarios]
        members = list(
            (
                await session.scalars(
                    select(ScenarioMember).where(
                        ScenarioMember.scenario_id.in_(scenario_ids)
                    )
                )
            ).all()
        )

    event_external_id = {event.id: event.external_id for event in events}
    category_prediction = {
        event_external_id[analysis.event_id]: analysis.category
        for analysis in analyses
        if analysis.event_id in event_external_id
    }
    scenario_prediction = {
        event_external_id[member.event_id]: str(member.scenario_id)
        for member in members
    }
    expected_scenario = {
        external_id: row["scenario_label"]
        for external_id, row in labels.items()
        if row["category"] != "other"
    }
    regular_ids = [
        external_id
        for external_id in expected_scenario
        if not manifest[external_id].get("intended_problem_reason")
    ]
    all_scenario_ids = list(expected_scenario)

    category_correct = sum(
        category_prediction.get(external_id) == row["category"]
        for external_id, row in labels.items()
    )
    cluster_truth: dict[str, Counter[str]] = defaultdict(Counter)
    for external_id, scenario_id in scenario_prediction.items():
        if external_id in expected_scenario:
            cluster_truth[scenario_id][expected_scenario[external_id]] += 1
    purities = []
    for scenario in scenarios:
        counts = cluster_truth[str(scenario.id)]
        total = sum(counts.values())
        purities.append(
            counts.most_common(1)[0][1] / total
            if total
            else 0.0
        )

    expected_keys = {
        (event["agent_id"], event["external_id"])
        for event in (
            json.loads(line)
            for line in (DATA_DIR / "demo_events.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        )
    }
    actual_keys = {
        (event.agent_id, event.external_id)
        for event in events
    }

    regular_metrics = _pairwise(
        regular_ids,
        expected_scenario,
        scenario_prediction,
    )
    all_metrics = _pairwise(
        all_scenario_ids,
        expected_scenario,
        scenario_prediction,
    )
    report = {
        "status": "pass",
        "database_integrity": {
            "expected_events": len(expected_keys),
            "stored_events": len(events),
            "missing_events": len(expected_keys - actual_keys),
            "extra_events": len(actual_keys - expected_keys),
            "completed_analyses": sum(
                event.analysis_status == "completed"
                for event in events
            ),
            "analysis_errors": sum(
                bool(event.analysis_error)
                for event in events
            ),
            "analysis_rows": len(analyses),
        },
        "current_run": {
            "id": str(current_run.id),
            "algorithm_version": current_run.algorithm_version,
            "status": current_run.status,
            "scenario_count": len(scenarios),
            "member_count": len(members),
        },
        "classification": {
            "accuracy": category_correct / len(labels),
            "correct": category_correct,
            "total": len(labels),
        },
        "scenario_quality": {
            "regular_queries": regular_metrics,
            "all_non_other_queries": all_metrics,
            "regular_member_coverage": (
                sum(
                    external_id in scenario_prediction
                    for external_id in regular_ids
                )
                / len(regular_ids)
            ),
            "mean_cluster_purity": (
                sum(purities) / len(purities)
                if purities
                else 0.0
            ),
            "pure_cluster_count": sum(purity == 1 for purity in purities),
        },
        "limitations": [
            "Ground truth and events are synthetic.",
            "Business outcome fields validate dashboard mechanics, not real ROI.",
            "Problem-detection precision requires a separately annotated holdout.",
        ],
    }
    gates = {
        "database_exact": (
            not report["database_integrity"]["missing_events"]
            and not report["database_integrity"]["extra_events"]
        ),
        "analysis_complete": (
            report["database_integrity"]["completed_analyses"]
            == report["database_integrity"]["stored_events"]
            == report["database_integrity"]["analysis_rows"]
            and not report["database_integrity"]["analysis_errors"]
        ),
        "scenario_count_reasonable": 25 <= len(scenarios) <= 60,
        "scenario_f1": regular_metrics["f1"] >= 0.65,
        "scenario_purity": (
            report["scenario_quality"]["mean_cluster_purity"] >= 0.80
        ),
    }
    report["gates"] = gates
    report["status"] = "pass" if all(gates.values()) else "fail"
    return report


def _write(report: dict[str, Any]) -> None:
    (DATA_DIR / "database_quality_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    regular = report["scenario_quality"]["regular_queries"]
    integrity = report["database_integrity"]
    run = report["current_run"]
    classification = report["classification"]
    markdown = f"""# End-to-end Database Quality Report

Статус: **{report['status'].upper()}**

## Целостность

- Событий: {integrity['stored_events']} из {integrity['expected_events']}.
- Потеряно: {integrity['missing_events']}.
- Лишних: {integrity['extra_events']}.
- Анализ завершён: {integrity['completed_analyses']}.
- Строк результатов анализа: {integrity['analysis_rows']}.
- Ошибок анализа: {integrity['analysis_errors']}.

## Фактический pipeline PostgreSQL

- Алгоритм: `{run['algorithm_version']}`.
- Сценариев: {run['scenario_count']}.
- Membership: {run['member_count']}.
- Category accuracy: {classification['accuracy']:.4f}.
- Scenario pairwise precision: {regular['precision']:.4f}.
- Scenario pairwise recall: {regular['recall']:.4f}.
- Scenario pairwise F1: {regular['f1']:.4f}.
- Coverage обычных запросов: {report['scenario_quality']['regular_member_coverage']:.4f}.
- Средняя чистота кластеров: {report['scenario_quality']['mean_cluster_purity']:.4f}.

Метрики рассчитаны по текущему `is_current` analysis run в PostgreSQL.
Данные синтетические, поэтому отчёт проверяет качество аналитического pipeline,
но не доказывает реальную экономию времени или ROI.
"""
    (DATA_DIR / "database_quality_report.md").write_text(
        markdown,
        encoding="utf-8",
        newline="\n",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write data/database_quality_report.{json,md}",
    )
    arguments = parser.parse_args()
    report = asyncio.run(audit())
    if arguments.write:
        _write(report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["status"] == "pass" else 1)


if __name__ == "__main__":
    main()
