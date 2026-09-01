# EP050 Node 19 to 20 Candidate v1.1 Producer Review Regression Procedure

> VERSION HISTORY
> - v1.0.0 · 2026-08-17 · Initial version: reusable deterministic regression procedure for Node 19->20 candidate v1.1 producer review.

## 1. Purpose & Scope
Validates the producer-side compliance, lineage, URL security, deterministic ID hashing, and safety boundary constraints of the Hermes Node 19 to 20 Consumer Contract Candidate v1.1.

## 2. Command Line Execution
Run from repository root `C:\Users\edebe\eds`:
```powershell
pytest -v epics/ep_050_distribution_engine/integration/reviews/gemini/test_node19_to_node20_producer_review.py
```

## 3. Expected Acceptance Criteria
- Total tests: 8
- Passed: 8
- Failed: 0
- Positive asset package conforms to `approved_asset_package_schema`.
- Rejects non-true compliance booleans (`disclaimer_verified=false`, `facts_verified=false`).
- Rejects URLs outside `.test` domain.
- Rejects empty strings.
- Rejects non-deterministic or malformed `publication_plan_id`.
- Rejects `external_action=true`.
