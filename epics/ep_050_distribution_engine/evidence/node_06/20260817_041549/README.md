# EP050 Node 06 — Evidence Bundle (20260817_041549)

> VERSION HISTORY
> - v1.0.0 · 2026-08-17 · Initial timestamped evidence bundle for Node 06 question discovery.

**Command:**
```
python -m pytest epics/ep_050_distribution_engine/implementation/node_06/test_question_discovery.py -v --basetemp=<scratchpad>/pytest_tmp_node06
```

**Result:** 26 passed, 0 failed, 0 errors, 3.34s. Full output in `pytest_output.txt`.

**Coverage:**
- Positive registration, optional `metadata` default (2 tests)
- Node01-05->06 five-way contract/integration: unregistered target rejected; target missing Node 05 (a demand signal) rejected; target present in all five real (non-mocked) upstream registries accepted (3 tests)
- Required-field failures for all 10 required fields (10 tests)
- Invalid enum/type: `source_type` outside the offline MVP boundary, invalid `observed_at` format, empty `intent_cues`, wrong-typed `geography` (4 tests)
- Prohibited-PII rejection: email address in `question_text`, phone number in `pain_point` (2 tests)
- Duplicate idempotency (1 test)
- Conflicting duplicate rejection, fail-closed, original unmodified (1 test)
- Serialization/persistence round trip (1 test)
- No-network / no-live-source assertion (1 test)
- Full-lifecycle regression (1 test)

**External side effects:** none. No network call, no live sources, no production datastore. The suite constructs real Node 01, Node 02, Node 03, Node 04, and Node 05 registry instances to prove all five cross-node contracts, rather than mocking any of them.
