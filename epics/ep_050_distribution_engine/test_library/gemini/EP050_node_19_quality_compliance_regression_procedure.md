# EP050 Node 19 Quality & Compliance Regression Procedure

> VERSION HISTORY
> - v1.0.0 · 2026-08-17 · Initial regression procedure for Node 19 Quality & Compliance including full multi-node pipeline integration test across Nodes 01-19 and Canonical Contract v1.1.0 validation.

## 1. Purpose & Scope
Deterministic regression validation for EP050 Stage 4 Node 19 (Quality & Compliance Review).
Verifies:
- Deterministic compliance stop-gate validation over Node 17 `AssetPayload` and Node 16 `CanonicalFactRecord`
- Mandatory safety disclaimer and Gas Safe compliance checks
- Guaranteed `external_action=False` metadata property and PII screening
- Output package byte-for-byte validation against Canonical Contract v1.1.0 (`approved_asset_package_schema`)
- Deterministic check ID generation:
  $$\text{check\_id} = \text{"chk\_"} + \text{SHA256}(\text{asset\_id}:\text{target\_id}:\text{opportunity\_id}:\text{validator\_version})[:16]$$
- Full upstream lineage preservation (`target_id`, `signal_id`, `classification_id`, `opportunity_id`, `path_id`, `selection_id`, `asset_id`, `check_id`)
- Fail-closed evaluation returning explicit reasons upon failure
- Strict offline execution (zero socket or network activity)

## 2. Command Line Execution
Run from repository root `C:\Users\edebe\eds`:
```powershell
pytest -v epics/ep_050_distribution_engine/implementation/node_19/test_quality_compliance.py
```

## 3. Expected Acceptance Criteria
- Total tests: 7
- Passed: 7
- Failed: 0
- Execution time: < 1.0s
- Confirms positive compliance approval, rejection of negative test matrix cases, and full schema validation against Canonical Contract v1.1.0.
