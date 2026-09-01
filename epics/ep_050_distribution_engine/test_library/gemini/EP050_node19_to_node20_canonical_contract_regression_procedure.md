# EP050 Node 19 to 20 Canonical Contract Regression Procedure

> VERSION HISTORY
> - v1.0.0 · 2026-08-17 · Initial version: reusable deterministic regression procedure for Node 19->20 canonical contract v1.1.

## 1. Purpose & Scope
Validates the canonical status, metadata provenance, SHA-256 candidate hash integrity, and schema compliance for the Stage 4 (Node 19) to Stage 5 (Node 20) interface contract.

## 2. Command Line Execution
Run from repository root `C:\Users\edebe\eds`:
```powershell
pytest -v epics/ep_050_distribution_engine/integration/canonical_contracts/test_node19_to_node20_canonical_contract.py
```

## 3. Expected Acceptance Criteria
- Total tests: 4
- Passed: 4
- Failed: 0
- Confirms `contract_node19_to_node20_v1_1` is `PROMOTED_CANONICAL`.
- Confirms SHA-256 matches Hermes candidate `e6739e5c411480724c4fbc590c24b1c537a5bb4020325aa98ff59e3f1c66f19a`.
- Confirms positive validation for producer asset package and consumer mock plan.
- Confirms `external_action=false` and `network=prohibited`.
