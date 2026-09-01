# Node 11 Intent Classification Test Evidence Bundle

- Timestamp: `2026-08-16T22:25:00+01:00`
- Target: `tgt_boiler_repair_blackheath` / `sig_20260816_boiler_press_01`
- Test File: `epics/ep_050_distribution_engine/implementation/node_11/test_intent_classification.py`
- Test Results: 22 passed in 0.50s (0 failures, 0 warnings)
- Test Categories:
  - Positive synthetic seed fixture classification
  - JSON Schema contract validation (`jsonschema.validate` against frozen proposal v1.1.0)
  - Bitwise deterministic reproducibility
  - 8 required-field missing fail-closed checks
  - Geography and service_context sub-field checks
  - Invalid enum and malformed date format checks
  - Full origin lineage preservation check
  - JSON serialization roundtrip check
  - Offline no-network assertion check (monkeypatched socket)
