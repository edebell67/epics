# EP050 Node 12 Opportunity Scoring Regression Procedure

> VERSION HISTORY
> - v1.1.0 · 2026-08-17 · Updated to include full live upstream pipeline integration test across Nodes 01 -> 02 -> 03 -> 04 -> 05 -> 11 -> 12 (9 tests total).
> - v1.0.0 · 2026-08-17 · Initial regression procedure for Node 12 Opportunity Scoring.

## 1. Purpose & Scope
Deterministic regression validation for EP050 Stage 3 Node 12 (Opportunity Scoring / DOS v1.0).
Verifies:
- Deterministic weighted Demand Opportunity Score calculation:
  $$\text{DOS} = (\text{Urgency} \times 35.0) + (\text{IntentViability} \times 30.0) + (\text{ServiceAlignment} \times 20.0) + (\text{GeographicAlignment} \times 15.0)$$
- Priority tier classification (`TIER_1_IMMEDIATE` $\ge 80.0$, `TIER_2_HIGH` $65.0-79.9$, `TIER_3_MODERATE` $45.0-64.9$, `TIER_4_LOW` $< 45.0$)
- Full upstream lineage preservation (`target_id`, `signal_id`, `classification_id`, `opportunity_id`)
- Direct integration with Node 11 `IntentClassificationResult` and full live multi-node chain (Nodes 01-05 -> 11 -> 12)
- Fail-closed validation on missing attributes or invalid weights
- Strict offline execution (zero socket or network activity)

## 2. Command Line Execution
Run from repository root `C:\Users\edebe\eds`:
```powershell
pytest -v epics/ep_050_distribution_engine/implementation/node_12/test_opportunity_scoring.py
```

## 3. Expected Acceptance Criteria
- Total tests: 9
- Passed: 9
- Failed: 0
- Execution time: < 1.0s
- Confirms positive scoring and tiering into `TIER_1_IMMEDIATE`.
- Confirms direct consumption of live Node 11 `IntentClassificationResult` and Node 05 `DemandSignalRecord`.
