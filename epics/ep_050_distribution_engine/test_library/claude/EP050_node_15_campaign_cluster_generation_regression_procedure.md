# EP050 Node 15 campaign / cluster generation regression procedure

## Use when
Modifying `epics/ep_050_distribution_engine/implementation/node_15/campaign_cluster_generation.py`, or before promoting Node 15 past its current gate, or before any Node 18 work that depends on Node 15's cluster lineage.

## Preconditions
- Changes stay fixture-only: no network call, no live data collection, no production datastore, no real customer identifiers.
- The suite must build every member bundle by calling the REAL Node 11 `classify_demand_signal`, Node 12 `score_demand_opportunity`, Node 13 `discover_demand_path`, and Node 14 `select_channel_placements` functions — do not mock or reimplement any of Gemini's Node 11-14 logic.
- Do not weaken the clustering rule (`primary_intent` + `geography.locality` + `primary_channel`), the lineage-consistency checks across the four sub-records, the `demand_opportunity_score` range check, or the prohibited-PII screen on `campaign_context` to make a test pass.
- Any change to `CLUSTER_RULE_VERSION` or the clustering key requires a version bump and a full regression rerun, since `cluster_id` and every downstream (Node 18) consumer depend on it.

## Steps and pass criteria
1. Run `pytest epics/ep_050_distribution_engine/implementation/node_15/test_campaign_cluster_generation.py -v --basetemp=<a writable scratch dir>`.
2. All tests must pass, covering:
   - One-item and multi-item clustering compatibility.
   - Boundary cases: members differing by locality, by primary_intent, or by primary_channel each form separate clusters.
   - Negative/validation: empty members list, duplicate signal_id within a run, missing lineage bundle key, mismatched lineage IDs across sub-records, out-of-range/non-numeric `demand_opportunity_score`.
   - Prohibited-PII rejection in `campaign_context`.
   - Determinism: identical member sets produce identical `cluster_id`/`cluster_score` across independent registry instances.
   - Duplicate idempotency and conflicting-duplicate rejection (fail-closed, original unmodified).
   - Persistence round trip via a fresh registry instance.
   - No-network assertion via a monkeypatched `socket.socket`.
   - Full-lifecycle regression in one pass.
3. Save the full `pytest -v` output as `pytest_output.txt` under a new timestamped folder in `epics/ep_050_distribution_engine/evidence/node_15/<YYYYMMDD_HHMMSS>/`, plus a short `README.md` manifest.
4. Update the Node 15 lifecycle record's Implementation Log, Evidence, and Validation sections, and re-verify byte-equality between the canonical `workstream/` copy, the `epics/ep_050_distribution_engine/lifecycle/claude/` copy, and the Obsidian mirror.

## Fail conditions
- Any test fails, errors, or is skipped.
- Member bundles are built with mocked or hand-constructed Node11-14 output instead of the real functions.
- The clustering rule accepts members with differing `primary_intent`/`geography.locality`/`primary_channel` into the same cluster, or `demand_opportunity_score` accepts an out-of-range/non-numeric value, or a PII-pattern test is removed/weakened without a documented reason.
- A required-field or lineage-validation case raises anything other than `ValidationError`/`LineageError`/`ConflictError`.
- Any network socket is opened, or any live-data-collection code path is added.
- Evidence, lifecycle, or mirror updates are skipped after a passing run.

## Boundary
A passing regression run proves Node 15's offline campaign-cluster-generation contract only. It does not authorize live data collection, production datastore access, or Node 18 implementation — Node 18 remains explicitly gated until Node 15 is accepted at 100%, finalized, and released, per the allocation's sequencing.
