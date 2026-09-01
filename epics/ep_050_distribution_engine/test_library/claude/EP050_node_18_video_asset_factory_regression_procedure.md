# EP050 Node 18 video asset factory regression procedure

## Use when
Modifying `epics/ep_050_distribution_engine/implementation/node_18/video_asset_factory.py`, or before promoting Node 18 past its current gate, or before the queued Operational UI update that depends on Node 18's video-asset lineage.

## Preconditions
- Changes stay fixture-only: no network call, no actual video rendering, no paid media/LLM APIs, no uploads, publishing, or credentials, no production datastore, no real customer identifiers.
- The suite must build every fixture by calling the REAL Node 11 `classify_demand_signal`, Node 12 `score_demand_opportunity`, Node 13 `discover_demand_path`, Node 14 `select_channel_placements`, Node 15 `CampaignClusterRegistry.generate_and_register`, Node 16 `CanonicalKnowledgeStore.register_fact`, and Node 17 `generate_asset_payload` — do not mock or reimplement any of them.
- Do not weaken the exact-lineage checks (classification/selection/asset ID consistency, fact-id subset verification, cluster-membership verification), the `external_action` literal-`False` check, the mandatory disclaimer/CTA presence checks, the scene timing bounds (`MIN_TOTAL_DURATION_SECONDS`/`MAX_TOTAL_DURATION_SECONDS`), or the prohibited-PII screen on scene text to make a test pass.
- `safety_disclaimer` and `call_to_action` must always be inherited verbatim from the Node 17 asset — never allow them to become caller-overridable free text.

## Steps and pass criteria
1. Run `pytest epics/ep_050_distribution_engine/implementation/node_18/test_video_asset_factory.py -v --basetemp=<a writable scratch dir>`.
2. All tests must pass, covering:
   - Positive registration with the real full upstream chain; default shot-list length matches storyboard.
   - Lineage/negative: mismatched classification_id/selection_id, a fact not in the asset's approved fact_ids, an asset with empty fact_ids, an asset that is not a cluster member, external_action not literal False, missing safety_disclaimer/call_to_action.
   - Scene/storyboard validation: empty custom scenes, missing field, wrong scene-index order, non-positive duration, an unapproved fact_id reference, email/phone PII in scene text, total duration too short/too long.
   - Determinism: identical inputs produce an identical video_asset_id across independent registry instances.
   - Duplicate idempotency and conflicting-duplicate rejection (fail-closed, original unmodified).
   - Persistence round trip via a fresh registry instance.
   - No-network assertion via a monkeypatched `socket.socket`.
   - Full-lifecycle regression in one pass.
3. Save the full `pytest -v` output as `pytest_output.txt` under a new timestamped folder in `epics/ep_050_distribution_engine/evidence/node_18/<YYYYMMDD_HHMMSS>/`, plus a short `README.md` manifest.
4. Update the Node 18 lifecycle record's Implementation Log, Evidence, and Validation sections, and re-verify byte-equality between the canonical `workstream/` copy, the `epics/ep_050_distribution_engine/lifecycle/claude/` copy, and the Obsidian mirror.

## Fail conditions
- Any test fails, errors, or is skipped.
- Any upstream fixture is built with mocked or hand-constructed Node11/14/15/16/17 output instead of the real functions/classes.
- A scene references a fact_id absent from the asset's approved fact_ids, `external_action` accepts a non-`False` value, a disclaimer/CTA becomes empty or caller-overridable, total duration falls outside `[10.0, 180.0]` seconds, or a PII-pattern test is removed/weakened without a documented reason.
- A required-field or lineage-validation case raises anything other than `ValidationError`/`LineageError`/`ConflictError`.
- Any network socket is opened, or any live-rendering/upload/publishing code path is added.
- Evidence, lifecycle, or mirror updates are skipped after a passing run.

## Boundary
A passing regression run proves Node 18's offline video-asset-factory contract only. It does not authorize actual video rendering, paid media/LLM API access, uploads, publishing, or the queued Operational UI update — that update remains explicitly gated until both Node 15 and Node 18 are accepted at 100%, finalized, and released.
