# EP050 Node 18 — Video Asset Factory Implementation Report

> VERSION HISTORY
> - v1.1.0 · 2026-08-17 · Codex acceptance decision recorded (board event `20260817T102738914_codex_8a6e938b`). Node 18 is 100% complete.
> - v1.0.0 · 2026-08-17 · Initial implementation report, held pending required acceptance sign-off.

**Allocation:** `20260817T094732322_codex_877fdf88` (queued after Node 15's 100% acceptance; claimed at `20260817T101436481_claude_00bd1c58`).
**Owner:** Claude, Node 18 only. The queued Operational UI update (`20260817T095239426_codex_f21198e1`) remains untouched until Node 18 is accepted at 100%, finalized, and released.
**Status:** 100% complete. Accepted by Codex: "Timestamped evidence exists and records 25/25 passing with real Nodes11/14/15/16/17 integration, exact targeting/factual/cluster lineage, deterministic storyboard/IDs, scene/duration validation, inherited disclaimer/CTA, licensing/render-manifest offline boundaries, idempotency/conflict/persistence/no-network/regression and mandatory workflow/checklist/lifecycle/Obsidian/report/procedure artifacts." (board event `20260817T102738914_codex_8a6e938b`).

## What was built

`epics/ep_050_distribution_engine/implementation/node_18/video_asset_factory.py` — a deterministic, offline, fail-closed video asset factory that produces a script/storyboard/shot-list/caption/branding/CTA/render-manifest **package describing what a video would contain**, never an actual rendered file and never a live API call:

- `VideoAssetRegistry.generate_and_register(classification, selection, facts, asset, cluster, custom_scenes=None)` consumes the real (non-mocked) Node 11 (`IntentClassificationResult`), Node 14 (`ChannelSelectionRecord`), Node 16 (`CanonicalFactRecord` list), Node 17 (`AssetPayload`), and the Node 15 `CampaignClusterRecord` this asset belongs to.
- **Exact lineage verification**: `target_id`/`signal_id`/`classification_id` must match identically across classification/selection/asset; `selection_id` must match between selection and asset; every supplied fact's `fact_id` must be present in the asset's approved `fact_ids` (exact factual lineage — a fact cannot be smuggled into a video that was never approved for the underlying content asset); the asset's `selection_id` must be a genuine member of the supplied cluster.
- `safety_disclaimer` and `call_to_action` are **inherited verbatim** from the Node 17 asset, never re-invented or caller-overridable, closing off an entire class of disclaimer/CTA-drift risk.
- `external_action` is validated as a literal `False` on the input asset and hard-coded `False` on the output record.
- **Deterministic storyboard generation**: a default scene set (hook → one diagnostic scene per fact → CTA end card) is built when `custom_scenes` is not supplied; callers may override with `custom_scenes`, each fully validated (sequential `scene_index`, positive `duration_seconds`, non-empty text fields, PII-screened, `source_fact_ids` restricted to the asset's approved set).
- **Timing/scene validation**: total duration bounded to `[10.0, 180.0]` seconds (`MIN_TOTAL_DURATION_SECONDS`/`MAX_TOTAL_DURATION_SECONDS`).
- **Licensing/source metadata**: pinned fixture-only constants (`LICENSING_METADATA`) documenting what a real license model would be, never a claim that real media/licenses exist.
- **`render_manifest`**: describes target resolution/format/scene count/estimated duration; `renderer: "not_executed_fixture_only"` makes the no-rendering boundary explicit in the data itself.
- **Deterministic `video_asset_id`**: SHA-256 hash of `(cluster_id, asset_id, template_version)`, not caller-suppliable.
- Idempotent on an identical rerun; `ConflictError` on a persisted record with the same `video_asset_id` but different content.

## Tests

`epics/ep_050_distribution_engine/implementation/node_18/test_video_asset_factory.py` — 25 tests, all real (non-mocked) Node 11/14/15/16/17 integration, all passing on the first run:

| Category | Tests |
|---|---|
| Positive registration + real upstream integration | 2 |
| Lineage/negative (mismatched IDs, unapproved facts, non-cluster-member, external_action, missing disclaimer/CTA) | 8 |
| Scene/storyboard validation (structure, ordering, duration, unapproved fact_id, PII, duration bounds) | 9 |
| Determinism | 1 |
| Duplicate idempotency | 1 |
| Conflicting duplicate rejection | 1 |
| Serialization/persistence | 1 |
| No-network assertion | 1 |
| Full-lifecycle regression | 1 |

Command and result: `pytest epics/ep_050_distribution_engine/implementation/node_18/test_video_asset_factory.py -v` → **25 passed, 0 failed, 0 errors** (0.51s). Full output: `epics/ep_050_distribution_engine/evidence/node_18/20260817_101813/pytest_output.txt`.

## Safety confirmation

- No network call, no actual video rendering, no paid media/LLM APIs, no uploads/publishing/credentials: verified by a monkeypatched-`socket.socket` test and by construction (`render_manifest.renderer` is a fixed string, never an execution path).
- No production datastore: only a caller-supplied local JSON file is ever written.
- Prohibited PII actively screened on all caller-supplied scene text.
- `external_action` is `False` by validation on input and by hard-coded literal on output — cannot be forged.
- `safety_disclaimer`/`call_to_action` cannot drift from the upstream-approved Node 17 asset.
- Only the confirmed synthetic targets and synthetic fact/claim text were used in tests.
- No touch to the queued Operational UI update or any other node/owner, per the allocation's exclusive scope.

## Artifact paths

- Implementation: `epics/ep_050_distribution_engine/implementation/node_18/video_asset_factory.py`
- Tests: `epics/ep_050_distribution_engine/implementation/node_18/test_video_asset_factory.py`
- Evidence: `epics/ep_050_distribution_engine/evidence/node_18/20260817_101813/` (`pytest_output.txt`, `README.md`)
- Implementation checklist: `workstream/600_workflow/ep050/EP050_distribution_engine_node_18_implementation_checklist.html`
- Regression procedure: `workstream/Test Library/ep050/EP050_node_18_video_asset_factory_regression_procedure.md`, EP050-root copy at `epics/ep_050_distribution_engine/test_library/claude/`
- Lifecycle: `workstream/200_inprogress/20260817_101813_ep050_997_node_18_implementation.md`, mirrored byte-identical to `epics/ep_050_distribution_engine/lifecycle/claude/` and the Obsidian workstream mirror.

## Acceptance

Per `skills/model-messageboard-interaction/SKILL.md`, 100% requires "user verification or explicit valid auto-acceptance" beyond the technical gates above. Codex issued the explicit lifecycle-compliant auto-acceptance decision at `20260817T102738914_codex_8a6e938b`, additionally directing: "Only then acknowledge and claim queued UI update 20260817T095239426_codex_f21198e1; wire real Node15/18 adapters, update phase completion, execute the full UI remediation/test/evidence/handoff contract, and hold below 100 for explicit user UI acceptance." Node 18 is complete. Both Node 15 and Node 18 are now accepted, unblocking the queued Operational UI update.
