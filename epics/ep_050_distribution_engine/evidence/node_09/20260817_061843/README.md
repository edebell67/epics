# EP050 Node 09 — Evidence Bundle (20260817_061843)

> VERSION HISTORY
> - v1.0.0 · 2026-08-17 · Initial timestamped evidence bundle for Node 09 community intelligence.

**Command:**
```
python -m pytest epics/ep_050_distribution_engine/implementation/node_09/test_community_intelligence.py -v --basetemp=<scratchpad>/pytest_tmp_node09
```

**Result:** 31 passed, 0 failed, 0 errors, 4.61s. Full output in `pytest_output.txt`.

**Coverage:**
- Positive registration, optional `metadata` default (2 tests)
- Node01-08->09 eight-way contract/integration: unregistered target rejected; target missing Node 08 (a competitor signal) rejected; target present in all eight real (non-mocked) upstream registries accepted (3 tests)
- Required-field failures for all 12 required fields (12 tests)
- Invalid enum/type: `source_type` outside the offline MVP boundary, wrong-typed `intent_cues`, negative and non-numeric `observed_metrics` values, empty `observed_metrics`, invalid `observed_at` format, wrong-typed `geography` (7 tests)
- Prohibited-PII rejection: email address in `question`, phone number in `pain_point` (2 tests)
- Duplicate idempotency (1 test)
- Conflicting duplicate rejection, fail-closed, original unmodified (1 test)
- Serialization/persistence round trip (1 test)
- No-network / no-live-community-access assertion (1 test)
- Full-lifecycle regression (1 test)

**External side effects:** none. No network call, no live community/forum/Reddit access, browsing, scraping, APIs, credentials, or outreach; no production datastore. The suite constructs real Node 01 through Node 08 registry instances to prove all eight cross-node contracts, rather than mocking any of them.
