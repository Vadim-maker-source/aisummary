# Datasets (synthetic)

All data here is **synthetic** and declared as such (`agent_id="synthetic-demo-agent"`).
No real user data and no agent answers are included — the MVP evaluates *queries*,
not answer correctness, so `response` is always `null`.

## Files

| File | Purpose |
|------|---------|
| `demo_events.jsonl` | 511 `EventCreate` objects (contract §5.2), one JSON per line. Import target for the end-to-end demo. |
| `demo_labels.json` | `external_id → {category, scenario_label}` ground truth. **Not** fed to the analyzer — used only by the quality metrics. |
| `demo_truth.json` | Auxiliary per-event truth (query, category, scenario_label, oversized flag). |
| `validation_events.jsonl` | 140 records `{external_id, query, expected_category}` for manual/automatic checking. |
| `validation_labels.json` | `external_id → expected_scenario_label`. Held out from the analyzer for manual grouping checks. |

## Demo dataset properties (role file §10)

- 31 source topics (28 real-category + 3 `other`), ≥ 16 formulations each;
- 511 events (≥ 465), unique `external_id`;
- timestamps spread over 46 days (≥ 30);
- 15 oversized examples (`content > 20000` chars, wrapped in `<context>` + `<user_query>`);
- 48 `other` events (chit-chat / vague / multi-intent), ≥ 20 ambiguous/multi-intent.

## Regenerate

```bash
PYTHONPATH=backend python3 data/generate_datasets.py
```

The generator is deterministic; regenerating reproduces byte-identical files.
