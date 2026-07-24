"""Quality metrics for the analytics MVP (role file section 11).

Computes, fully offline (rule-based fallback path):
  - category_accuracy
  - unclassified_rate
  - scenario_pairwise_precision / recall / f1

Pairwise definition: a pair of queries is *positive* if they share the same
expected scenario label; *predicted positive* if they land in the same
discovered scenario. Only non-``other`` events participate in the pairwise
metric (discovery excludes ``other``). Grouping for discovery uses the expected
category so the pairwise metric measures clustering quality, not classification.
"""

from __future__ import annotations

import json
from itertools import combinations
from pathlib import Path
from typing import Dict, List, Tuple

from app.analytics.public import analyze_event, discover_scenarios
from app.analytics.schemas import AnalysisInput, Category, ScenarioInputRecord

DATA_DIR = Path(__file__).resolve().parents[3] / "data"


def load_demo() -> Tuple[List[dict], Dict[str, dict]]:
    events = [
        json.loads(line)
        for line in (DATA_DIR / "demo_events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    labels = json.loads((DATA_DIR / "demo_labels.json").read_text(encoding="utf-8"))
    return events, labels


def _analysis_input(event: dict) -> AnalysisInput:
    request = event.get("request", {})
    return AnalysisInput(
        event_id=event["external_id"],
        messages=request.get("messages", []),
        model=request.get("model"),
        prompt_tokens=None,
    )


async def analyze_all(events: List[dict]) -> Dict[str, "AnalyzeRow"]:
    rows: Dict[str, AnalyzeRow] = {}
    for event in events:
        result = await analyze_event(_analysis_input(event), [])
        rows[event["external_id"]] = AnalyzeRow(
            predicted_category=result.category.value,
            effective_query=result.effective_query,
        )
    return rows


class AnalyzeRow:
    __slots__ = ("predicted_category", "effective_query")

    def __init__(self, predicted_category: str, effective_query: str):
        self.predicted_category = predicted_category
        self.effective_query = effective_query


def category_metrics(rows: Dict[str, "AnalyzeRow"], labels: Dict[str, dict]) -> Dict[str, float]:
    total = 0
    correct = 0
    unclassified = 0
    for ext, row in rows.items():
        expected = labels[ext]["category"]
        total += 1
        if row.predicted_category == expected:
            correct += 1
        if row.predicted_category == Category.other.value:
            unclassified += 1
    return {
        "category_accuracy": correct / total if total else 0.0,
        "unclassified_rate": unclassified / total if total else 0.0,
        "count": total,
    }


async def pairwise_metrics(rows: Dict[str, "AnalyzeRow"], labels: Dict[str, dict]) -> Dict[str, float]:
    # Build discovery input for non-other events, grouped by EXPECTED category.
    records: List[ScenarioInputRecord] = []
    considered: List[str] = []
    for ext, row in rows.items():
        expected_category = labels[ext]["category"]
        if expected_category == Category.other.value:
            continue
        records.append(
            ScenarioInputRecord(
                event_id=ext,
                effective_query=row.effective_query,
                category=expected_category,
            )
        )
        considered.append(ext)

    result = await discover_scenarios(records)

    # Map each event id -> discovered scenario index.
    event_to_scenario: Dict[str, int] = {}
    for scenario_idx, scenario in enumerate(result.scenarios):
        for ext in scenario.member_event_ids:
            event_to_scenario[ext] = scenario_idx

    expected_label = {ext: labels[ext]["scenario_label"] for ext in considered}

    tp = fp = fn = 0
    for a, b in combinations(considered, 2):
        same_expected = expected_label[a] == expected_label[b]
        pred_a = event_to_scenario.get(a)
        pred_b = event_to_scenario.get(b)
        same_predicted = pred_a is not None and pred_a == pred_b
        if same_expected and same_predicted:
            tp += 1
        elif same_predicted and not same_expected:
            fp += 1
        elif same_expected and not same_predicted:
            fn += 1

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {
        "scenario_pairwise_precision": precision,
        "scenario_pairwise_recall": recall,
        "scenario_pairwise_f1": f1,
        "discovered_scenarios": len(result.scenarios),
        "unclustered": len(result.unclustered_event_ids),
    }


async def compute_all() -> Dict[str, object]:
    events, labels = load_demo()
    rows = await analyze_all(events)
    out: Dict[str, object] = {}
    out.update(category_metrics(rows, labels))
    out.update(await pairwise_metrics(rows, labels))
    return out


if __name__ == "__main__":
    import asyncio

    metrics = asyncio.run(compute_all())
    print("=== Analytics quality metrics (demo, offline) ===")
    for key, value in metrics.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")
    print()
    print("Targets: category_accuracy >= 0.75, scenario_pairwise_f1 >= 0.65")
