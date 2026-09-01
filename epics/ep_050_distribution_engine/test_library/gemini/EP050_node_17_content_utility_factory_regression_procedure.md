# EP050 Node 17 Content & Utility Factory Regression Procedure

> VERSION HISTORY
> - v1.0.0 · 2026-08-17 · Initial regression procedure for Node 17 Content & Utility Factory including full multi-node pipeline integration test across Nodes 01-17.

## 1. Purpose & Scope
Deterministic regression validation for EP050 Stage 4 Node 17 (Content & Utility Factory).
Verifies:
- Deterministic template-driven asset synthesis combining Node 16 verified facts, Node 11 intent, Node 14 channel/placement, and Node 04 conversion CTAs
- Mandatory safety disclaimer injection
- Guaranteed `external_action=False` metadata property
- Deterministic asset ID generation:
  $$\text{asset\_id} = \text{"asset\_"} + \text{SHA256}(\text{target\_id}:\text{channel}:\text{format}:\text{template\_version}:\text{fact\_checksum})[:16]$$
- Full upstream factual and targeting lineage preservation (`fact_ids`, `target_id`, `signal_id`, `classification_id`, `opportunity_id`, `path_id`, `selection_id`, `asset_id`)
- Direct integration with Node 14 `ChannelSelectionRecord` and Node 16 `CanonicalFactRecord` in a live multi-node chain (Nodes 01-05 -> 11 -> 12 -> 13 -> 14 -> 16 -> 17)
- Fail-closed validation on missing facts, missing lineage, invalid CTAs, or PII
- Strict offline execution (zero socket or network activity)

## 2. Command Line Execution
Run from repository root `C:\Users\edebe\eds`:
```powershell
pytest -v epics/ep_050_distribution_engine/implementation/node_17/test_content_utility_factory.py
```

## 3. Expected Acceptance Criteria
- Total tests: 7
- Passed: 7
- Failed: 0
- Execution time: < 1.0s
- Confirms positive template synthesis, mandatory safety disclaimers, and offline enclosure.
- Confirms direct consumption of live upstream outputs across Nodes 01 through 16.
