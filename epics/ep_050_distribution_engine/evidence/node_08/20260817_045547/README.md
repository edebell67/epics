# EP050 Node 08 — Evidence Bundle (20260817_045547)

> VERSION HISTORY
> - v1.0.0 · 2026-08-17 · Initial timestamped evidence bundle for Node 08 competitor intelligence.

**Command:**
```
python -m pytest epics/ep_050_distribution_engine/implementation/node_08/test_competitor_intelligence.py -v --basetemp=<scratchpad>/pytest_tmp_node08
```

**Result:** 31 passed, 0 failed, 0 errors, 3.75s. Full output in `pytest_output.txt`.

**Coverage:**
- Positive registration, optional `metadata` default (2 tests)
- Node01-07->08 seven-way contract/integration: unregistered target rejected; target missing Node 07 (a social/video signal) rejected; target present in all seven real (non-mocked) upstream registries accepted (3 tests)
- Required-field failures for all 13 required fields (13 tests)
- Invalid enum/type: `source_type` outside the offline MVP boundary, invalid `competition_indicator` enum, `relevance_score` out-of-range and non-numeric, invalid `observed_at` format, wrong-typed `geography` (6 tests)
- Prohibited-PII rejection: email address in `competitor_name`, phone number in `query` (2 tests)
- Duplicate idempotency (1 test)
- Conflicting duplicate rejection, fail-closed, original unmodified (1 test)
- Serialization/persistence round trip (1 test)
- No-network / no-live-research assertion (1 test)
- Full-lifecycle regression (1 test)

**External side effects:** none. No network call, no live competitor research/browsing/scraping/APIs, no production datastore. The suite constructs real Node 01 through Node 07 registry instances to prove all seven cross-node contracts, rather than mocking any of them.
