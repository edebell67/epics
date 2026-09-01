# EP050 Node 14 Channel / Placement Selection Regression Procedure

> VERSION HISTORY
> - v1.0.0 · 2026-08-17 · Initial regression procedure for Node 14 Channel/Placement Selection including 8-node upstream integration test.

## 1. Purpose & Scope
Deterministic regression validation for EP050 Stage 3 Node 14 (Channel / Placement Selection).
Verifies:
- Deterministic 4-factor channel fit scoring:
  $$\text{ChannelFitScore} = (\text{AudienceMatch} \times 30.0) + (\text{IntentRelevance} \times 30.0) + (\text{FormatViability} \times 20.0) + (\text{CostEfficiency} \times 20.0)$$
- Strict descending rank ordering across candidate placements
- Deterministic selection ID generation:
  $$\text{selection\_id} = \text{"sel\_"} + \text{SHA256}(\text{target\_id}:\text{signal\_id}:\text{classification\_id}:\text{opportunity\_id}:\text{path\_id}:\text{strategy\_name})[:16]$$
- Full upstream lineage preservation (`target_id`, `signal_id`, `classification_id`, `opportunity_id`, `path_id`, `selection_id`)
- Direct integration with Node 13 `DemandPathRecord` and full live multi-node chain (Nodes 01-05 -> 11 -> 12 -> 13 -> 14)
- Fail-closed validation on missing lineage or out-of-bounds weights/scores
- Strict offline execution (zero socket or network activity)

## 2. Command Line Execution
Run from repository root `C:\Users\edebe\eds`:
```powershell
pytest -v epics/ep_050_distribution_engine/implementation/node_14/test_channel_placement_selection.py
```

## 3. Expected Acceptance Criteria
- Total tests: 8
- Passed: 8
- Failed: 0
- Execution time: < 1.0s
- Confirms positive channel fit scoring and placement ranking.
- Confirms direct consumption of live Node 13 `DemandPathRecord`.
