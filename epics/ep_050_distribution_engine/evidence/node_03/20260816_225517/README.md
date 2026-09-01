# EP050 Node 03 — Evidence Bundle (20260816_225517)

> VERSION HISTORY
> - v1.0.0 · 2026-08-16 · Initial timestamped evidence bundle for Node 03 audience definition.

**Command:**
```
python -m pytest epics/ep_050_distribution_engine/implementation/node_03/test_audience_definition.py -v --basetemp=<scratchpad>/pytest_tmp_node03
```

**Result:** 26 passed, 0 failed, 0 errors, 1.01s. Full output in `pytest_output.txt`.

**Coverage:**
- Positive registration, deterministic `segment_id` derivation, optional-field defaults (3 tests)
- Node01+Node02->03 contract/integration: target missing from Node 01 rejected; target in Node 01 but missing Node 02 record rejected; target present in both real (non-mocked) registries accepted (3 tests)
- Required-field failures for all 6 required fields, plus a geography-subfield case (7 tests)
- Invalid enum/type: urgency enum, wrong-typed/empty `needs`, wrong-typed geography (4 tests)
- **Prohibited-PII rejection**: email address in `needs`, phone number in `pains`, email in `segment_name`, phone in `exclusions` — all rejected fail-closed (4 tests)
- Duplicate idempotency (1 test)
- Conflicting duplicate rejection, fail-closed, original unmodified (1 test)
- Serialization/persistence round trip (1 test)
- No-network assertion (1 test)
- Full-lifecycle regression (1 test)

**External side effects:** none. No network call, no production datastore. The suite constructs real Node 01 (`TargetRegistry`) and Node 02 (`ProductIntelligenceRegistry`) instances to prove both cross-node contracts, rather than mocking either.
