"""Quality-metric gate (role file section 11).

Runs the offline analytics pipeline over the independent validation dataset
and asserts the target quality bars. Skips gracefully if the datasets have not
been generated.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import metrics as metrics_module

pytestmark = pytest.mark.asyncio

DATA_DIR = Path(__file__).resolve().parents[3] / "data"


@pytest.mark.skipif(
    not (DATA_DIR / "validation_events.jsonl").exists(),
    reason="demo dataset not generated (run data/generate_datasets.py)",
)
async def test_quality_targets_met():
    results = await metrics_module.compute_all()
    assert results["category_accuracy"] >= 0.75, results
    assert results["scenario_pairwise_f1"] >= 0.65, results
    # sanity: unclassified rate stays reasonable
    assert 0.0 <= results["unclassified_rate"] <= 0.5, results
