# EP050 Node 13 Demand Path Discovery Regression Procedure

> VERSION HISTORY
> - v1.0.0 · 2026-08-17 · Initial regression procedure for Node 13 Demand Path Discovery including 7-node upstream integration test.

## 1. Purpose & Scope
Deterministic regression validation for EP050 Stage 3 Node 13 (Demand Path Discovery).
Verifies:
- Deterministic multi-stage customer demand path construction
- Commercial intent emergence detection
- Deterministic path ID generation:
  $$\text{path\_id} = \text{"path\_"} + \text{SHA256}(\text{target\_id}:\text{signal\_id}:\text{classification\_id}:\text{opportunity\_id}:\text{path\_name})[:16]$$
- Full upstream lineage preservation (`target_id`, `signal_id`, `classification_id`, `opportunity_id`, `path_id`)
- Direct integration with Node 12 `DemandOpportunityRecord` and full live multi-node chain (Nodes 01-05 -> 11 -> 12 -> 13)
- Fail-closed validation on missing lineage or disordered stages
- Strict offline execution (zero socket or network activity)

## 2. Command Line Execution
Run from repository root `C:\Users\edebe\eds`:
```powershell
pytest -v epics/ep_050_distribution_engine/implementation/node_13/test_demand_path_discovery.py
```

## 3. Expected Acceptance Criteria
- Total tests: 7
- Passed: 7
- Failed: 0
- Execution time: < 1.0s
- Confirms positive path creation and emergence detection.
- Confirms direct consumption of live Node 12 `DemandOpportunityRecord`.
