# EP050 Node 05 — Evidence Bundle (20260817_035602)

> VERSION HISTORY
> - v1.0.0 · 2026-08-17 · Initial timestamped evidence bundle for Node 05 search demand discovery.

**Command:**
```
python -m pytest epics/ep_050_distribution_engine/implementation/node_05/test_search_demand_discovery.py -v --basetemp=<scratchpad>/pytest_tmp_node05
```

**Result:** 25 passed, 0 failed, 0 errors, 1.95s. Full output in `pytest_output.txt`.

**Coverage:**
- Positive registration, optional `metadata` default (2 tests)
- Node01+02+03+04->05 contract/integration: unregistered target rejected; target missing Node 04 rejected; target present in all four real (non-mocked) upstream registries accepted (3 tests)
- **Cross-owner contract compatibility (real, not assumed)**: a signal produced by Node 05 is fed directly into Gemini's actual, unmodified `intent_classification.classify_demand_signal()` and succeeds -- proving Node 05's output genuinely conforms to the frozen Node05->11 contract, not merely believed to (1 test)
- Required-field failures for all 8 required fields (8 tests)
- Invalid enum/type: `source_type` outside the offline MVP boundary (rejects `search_query`), invalid `observed_at` format, wrong-typed `geography`, incomplete `service_context` (4 tests)
- **Prohibited-PII rejection**: email address in `raw_query`, phone number in `topic` (2 tests)
- Duplicate idempotency (1 test)
- Conflicting duplicate rejection, fail-closed, original unmodified (1 test)
- Serialization/persistence round trip (1 test)
- No-network / no-live-scraping assertion (1 test)
- Full-lifecycle regression, including a second real Node 11 compatibility check (1 test)

**External side effects:** none. No network call, no live scraping, no production datastore. The suite constructs real Node 01, Node 02, Node 03, and Node 04 registry instances to prove all four cross-node contracts, and imports Gemini's real Node 11 module (read-only) to prove downstream compatibility -- nothing is mocked or assumed.
