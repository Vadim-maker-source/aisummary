from __future__ import annotations

import json
from pathlib import Path

from app.analytics.classifier import rule_based_classify
from app.analytics.clustering import cluster_category
from app.analytics.schemas import Category, ScenarioInputRecord

DATA_DIR = Path(__file__).resolve().parents[3] / "data"


def _load_holdout() -> tuple[list[dict], dict[str, dict]]:
    with (DATA_DIR / "holdout_events.jsonl").open(encoding="utf-8") as source:
        events = [json.loads(line) for line in source if line.strip()]
    labels = json.loads(
        (DATA_DIR / "holdout_labels.json").read_text(encoding="utf-8")
    )
    return events, labels


def test_handwritten_holdout_category_accuracy_is_at_least_80_percent():
    events, labels = _load_holdout()
    correct = 0
    for event in events:
        predicted, _ = rule_based_classify(event["query"])
        if predicted.value == labels[event["external_id"]]["category"]:
            correct += 1

    assert correct / len(events) >= 0.80


def test_handwritten_holdout_scenarios_have_pairwise_f1_at_least_65_percent():
    events, labels = _load_holdout()
    predicted_cluster: dict[str, str | None] = {
        event["external_id"]: None for event in events
    }
    by_category: dict[Category, list[ScenarioInputRecord]] = {}
    for event in events:
        category = Category(labels[event["external_id"]]["category"])
        by_category.setdefault(category, []).append(
            ScenarioInputRecord(
                event_id=event["external_id"],
                effective_query=event["query"],
                category=category,
            )
        )

    for category, records in by_category.items():
        clusters, _ = cluster_category(records)
        for index, cluster in enumerate(clusters):
            for event_id in cluster.member_event_ids:
                predicted_cluster[event_id] = f"{category.value}-{index}"

    true_positive = false_positive = false_negative = 0
    ids = [event["external_id"] for event in events]
    for left_index, left in enumerate(ids):
        for right in ids[left_index + 1 :]:
            same_truth = (
                labels[left]["scenario_label"]
                == labels[right]["scenario_label"]
            )
            same_prediction = (
                predicted_cluster[left] is not None
                and predicted_cluster[left] == predicted_cluster[right]
            )
            if same_truth and same_prediction:
                true_positive += 1
            elif not same_truth and same_prediction:
                false_positive += 1
            elif same_truth and not same_prediction:
                false_negative += 1

    precision = true_positive / (true_positive + false_positive)
    recall = true_positive / (true_positive + false_negative)
    f1 = 2 * precision * recall / (precision + recall)
    assert f1 >= 0.65
