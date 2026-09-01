# EP050 Node 15 — Evidence Bundle (20260817_095758)

> VERSION HISTORY
> - v1.0.0 · 2026-08-17 · Initial timestamped evidence bundle for Node 15 campaign/cluster generation.

**Command:**
```
python -m pytest epics/ep_050_distribution_engine/implementation/node_15/test_campaign_cluster_generation.py -v --basetemp=<scratchpad>/pytest_tmp_node15
```

**Result:** 19 passed, 0 failed, 0 errors, 0.53s. Full output in `pytest_output.txt`.

**Coverage:**
- One-item and multi-item clustering: a single member forms a valid one-item cluster; two members sharing all three trait dimensions merge into one cluster (2 tests)
- Boundary: members differing by locality, by primary_intent, or by primary_channel each form separate clusters, proving the clustering rule respects all three dimensions independently (3 tests)
- Negative/validation: empty members list, duplicate signal_id within a single run, missing lineage bundle key, mismatched lineage IDs across Node11-14 sub-records, out-of-range/non-numeric `demand_opportunity_score` (6 tests)
- Prohibited-PII rejection on caller-supplied `campaign_context`: email address, phone number (2 tests)
- Determinism: identical member sets produce identical `cluster_id`/`cluster_score` across independent registry instances (1 test)
- Duplicate idempotency: an identical rerun does not duplicate stored clusters (1 test)
- Conflicting duplicate rejection: a tampered stored record with the same `cluster_id` but different content is rejected fail-closed (1 test)
- Serialization/persistence round trip (1 test)
- No-network / no-live-data assertion (1 test)
- Full-lifecycle regression (1 test)

**Real (non-mocked) upstream integration:** every member bundle is built by calling the actual Node 11 `classify_demand_signal`, Node 12 `score_demand_opportunity`, Node 13 `discover_demand_path`, and Node 14 `select_channel_placements` functions directly — none of Gemini's Node 11-14 logic is mocked or reimplemented.

**Bug found and fixed during first test run:** the initial idempotency comparison excluded only `recorded_at` from the equality check, but each `CampaignClusterRecord.created_at` is also a fresh wall-clock timestamp assigned per build, causing an identical re-clustering rerun to be misclassified as a conflicting duplicate. Fixed by excluding both `created_at` and `recorded_at` from the comparability check, since neither is part of cluster identity. Documented in the implementation's version history.

**External side effects:** none. No network call, no live data collection, no production datastore. `cluster_id` is a deterministic SHA-256-derived hash of the sorted member `selection_id`s and the versioned clustering rule, not caller-suppliable.
