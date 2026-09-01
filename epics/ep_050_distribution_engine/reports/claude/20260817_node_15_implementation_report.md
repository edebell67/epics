# EP050 Node 15 — Campaign / Cluster Generation Implementation Report

> VERSION HISTORY
> - v1.1.0 · 2026-08-17 · Codex acceptance decision recorded (board event `20260817T100656848_codex_5adc8829`). Node 15 is 100% complete.
> - v1.0.0 · 2026-08-17 · Initial implementation report, held pending required acceptance sign-off.

**Allocation:** `20260817T094732186_codex_b3bc09ef`, activated per user-authorized scope expansion `20260817T094731870_codex_9273b8d6` (reassigning Nodes 15 and 18 from inactive Gemini to Claude).
**Owner:** Claude, Node 15 only. Node 18 is queued (`20260817T094732322_codex_877fdf88`) and will not be touched until Node 15 is accepted at 100%, finalized, and released.
**Status:** 100% complete. Accepted by Codex: "Timestamped evidence exists and records 19/19 passing after a documented idempotency defect was fixed in v1.0.1. Coverage includes real Nodes11-14 integration, exact lineage, one/multi-item clusters, clustering boundaries, deterministic IDs/scores, validation/PII/idempotency/conflict/no-network/regression and mandatory workflow/checklist/lifecycle/Obsidian/report/procedure artifacts." (board event `20260817T100656848_codex_5adc8829`).

## What was built

`epics/ep_050_distribution_engine/implementation/node_15/campaign_cluster_generation.py` — a deterministic, offline, fail-closed campaign/cluster generation engine:

- `CampaignClusterRegistry.generate_and_register(members, campaign_context=None)` — consumes a flat list of member bundles, each carrying the real (non-mocked) Node 11 (`classification`), Node 12 (`opportunity`), Node 13 (`path`), and Node 14 (`selection`) output records for one opportunity.
- **Exact lineage verification**: for each member, `target_id`, `signal_id`, and `classification_id` must match identically across all four sub-records; `opportunity_id` must match across opportunity/path/selection; `path_id` must match across path/selection. Any mismatch raises `LineageError`. A missing sub-record key also raises `LineageError`.
- **Explicit, versioned clustering rule** (`CLUSTER_RULE_VERSION = "cluster_rule_v1.0"`): members are grouped by `(primary_intent, geography.locality, primary_channel)`. One-item clusters are fully supported; members differing in any one of the three dimensions land in separate clusters — proven independently for each dimension.
- `demand_opportunity_score` validated numeric in `[0.0, 100.0]`.
- **Duplicate membership**: the same `signal_id` appearing twice within a single `generate_and_register()` call is rejected fail-closed.
- **Deterministic `cluster_id`**: SHA-256 hash of the sorted member `selection_id`s plus the rule version — reproducible across independent registry instances, not caller-suppliable.
- `cluster_score` (average `demand_opportunity_score` across members) and a human-readable `score_explanation` are computed, not caller-supplied.
- **Prohibited-PII fail-closed screen** on the optional caller-supplied `campaign_context` string.
- Idempotent on an identical re-clustering rerun; `ConflictError` on a persisted record with the same `cluster_id` but different content (e.g. a concurrent external edit).

## Tests

`epics/ep_050_distribution_engine/implementation/node_15/test_campaign_cluster_generation.py` — 19 tests, all real (non-mocked) Node 11-14 integration, 17/19 passing on the first run, 19/19 after one fix:

| Category | Tests |
|---|---|
| One-item / multi-item clustering | 2 |
| Boundary (locality, intent, channel dimensions) | 3 |
| Negative/validation (empty list, duplicate membership, missing/mismatched lineage, invalid score) | 6 |
| Prohibited-PII rejection | 2 |
| Determinism | 1 |
| Duplicate idempotency | 1 |
| Conflicting duplicate rejection | 1 |
| Serialization/persistence | 1 |
| No-network assertion | 1 |
| Full-lifecycle regression | 1 |

Command and result: `pytest epics/ep_050_distribution_engine/implementation/node_15/test_campaign_cluster_generation.py -v` → **19 passed, 0 failed, 0 errors** (0.53s, after the fix below). Full output: `epics/ep_050_distribution_engine/evidence/node_15/20260817_095758/pytest_output.txt`.

## Bug found and fixed

The first run failed 2 of 19 tests: `test_identical_rerun_is_idempotent_and_does_not_duplicate` and `test_full_lifecycle_regression`. Root cause: the idempotency comparison excluded only `recorded_at` from the equality check, but `CampaignClusterRecord.created_at` is also assigned fresh on every build (`datetime.now(timezone.utc)`), so an identical re-clustering rerun was misclassified as a conflicting duplicate and raised `ConflictError` instead of returning the existing record. Fixed (v1.0.1) by excluding both `created_at` and `recorded_at` from the comparability check, since neither is part of cluster identity. Re-ran the full suite clean: 19/19 passed.

## Safety confirmation

- No network call, no live data collection: verified by a monkeypatched-`socket.socket` test.
- No production datastore: only a caller-supplied local JSON file is ever written.
- Prohibited PII actively screened and rejected on the one caller-supplied free-text field.
- `cluster_id`, `cluster_score`, `score_explanation`, `shared_traits` are all computed by the registry, never caller-suppliable.
- Only the confirmed synthetic targets (`tgt_boiler_repair_blackheath` and one synthetic sibling target) were used in tests.
- No touch to Node 18, other nodes, or the UI, per the allocation's exclusive scope.

## Artifact paths

- Implementation: `epics/ep_050_distribution_engine/implementation/node_15/campaign_cluster_generation.py`
- Tests: `epics/ep_050_distribution_engine/implementation/node_15/test_campaign_cluster_generation.py`
- Evidence: `epics/ep_050_distribution_engine/evidence/node_15/20260817_095758/` (`pytest_output.txt`, `README.md`)
- Implementation checklist: `workstream/600_workflow/ep050/EP050_distribution_engine_node_15_implementation_checklist.html`
- Regression procedure: `workstream/Test Library/ep050/EP050_node_15_campaign_cluster_generation_regression_procedure.md`, EP050-root copy at `epics/ep_050_distribution_engine/test_library/claude/`
- Lifecycle: `workstream/200_inprogress/20260817_095758_ep050_997_node_15_implementation.md`, mirrored byte-identical to `epics/ep_050_distribution_engine/lifecycle/claude/` and the Obsidian workstream mirror.

## Acceptance

Per `skills/model-messageboard-interaction/SKILL.md`, 100% requires "user verification or explicit valid auto-acceptance" beyond the technical gates above. Codex issued the explicit lifecycle-compliant auto-acceptance decision at `20260817T100656848_codex_5adc8829`, additionally directing: "acknowledge and claim queued Node18 allocation 20260817T094732322_codex_877fdf88. Continue Node18 to fully tested handoff before touching the queued UI update." Node 15 is complete. Node 18 (Video Asset Factory) is next.
