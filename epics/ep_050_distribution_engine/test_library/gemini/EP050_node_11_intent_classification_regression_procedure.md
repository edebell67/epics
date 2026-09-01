# EP050 Node 11 Intent Classification Regression Procedure

> VERSION HISTORY
> - v1.1.0 · 2026-08-17 · Updated to include full live upstream integration test across Nodes 01, 02, 03, 04, 05 to 11 (23 tests total).
> - v1.0.0 · 2026-08-16 · Initial regression procedure for Node 11 Intent Classification.

## 1. Purpose & Scope
Deterministic regression validation for EP050 Stage 3 Node 11 (Intent Classification).
Verifies:
- Rule-based keyword matching and taxonomy scoring
- Lineage preservation (`target_id`, `signal_id`, `classification_id`)
- Fail-closed validation on missing attributes or invalid enums
- Real upstream end-to-end integration across Nodes 01 -> 02 -> 03 -> 04 -> 05 -> 11
- Strict offline execution (zero socket or network activity)

## 2. Command Line Execution
Run from repository root `C:\Users\edebe\eds`:
```powershell
pytest -v epics/ep_050_distribution_engine/implementation/node_11/test_intent_classification.py
```

## 3. Expected Acceptance Criteria
- Total tests: 23
- Passed: 23
- Failed: 0
- Execution time: < 1.0s
- Confirms positive classification into `IntentCategory.TROUBLESHOOTING` and `UrgencyLevel.HIGH`.
- Confirms direct consumption of live Node 05 `DemandSignalRecord`.
