# EP050 Node 16 Canonical Knowledge Store Regression Procedure

> VERSION HISTORY
> - v1.0.0 · 2026-08-17 · Initial regression procedure for Node 16 Canonical Knowledge Store including Node 01 -> Node 02 -> Node 16 upstream integration test.

## 1. Purpose & Scope
Deterministic regression validation for EP050 Stage 4 Node 16 (Canonical Knowledge Store).
Verifies:
- Deterministic canonical fact registration and query
- Mandatory safety guidance enforcement on safety-critical claims
- Deterministic fact ID generation:
  $$\text{fact\_id} = \text{"fact\_"} + \text{SHA256}(\text{target\_id}:\text{topic}:\text{claim}:\text{verification\_source})[:16]$$
- Prohibited PII screening (rejects email and phone patterns)
- Direct integration with Node 01 `TargetRegistry` and Node 02 `ProductIntelligenceRegistry`
- File persistence save and reload integrity
- Strict offline execution (zero socket or network activity)

## 2. Command Line Execution
Run from repository root `C:\Users\edebe\eds`:
```powershell
pytest -v epics/ep_050_distribution_engine/implementation/node_16/test_canonical_knowledge_store.py
```

## 3. Expected Acceptance Criteria
- Total tests: 6
- Passed: 6
- Failed: 0
- Execution time: < 1.0s
- Confirms positive fact registration, safety guidance enforcement, and PII protection.
- Confirms direct consumption of live Node 01 and Node 02 registries.
