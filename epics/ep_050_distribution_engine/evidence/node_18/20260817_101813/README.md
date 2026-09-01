# EP050 Node 18 — Evidence Bundle (20260817_101813)

> VERSION HISTORY
> - v1.0.0 · 2026-08-17 · Initial timestamped evidence bundle for Node 18 video asset factory.

**Command:**
```
python -m pytest epics/ep_050_distribution_engine/implementation/node_18/test_video_asset_factory.py -v --basetemp=<scratchpad>/pytest_tmp_node18
```

**Result:** 25 passed, 0 failed, 0 errors, 0.51s. Full output in `pytest_output.txt`.

**Coverage:**
- Positive registration with the real full upstream chain; default shot-list length matches storyboard (2 tests)
- Lineage/negative: mismatched `classification_id`/`selection_id`, a fact not present in the asset's approved `fact_ids`, an asset with empty `fact_ids`, an asset that is not a member of the supplied Node 15 cluster, `external_action` not literal `False`, missing `safety_disclaimer`/`call_to_action` (8 tests)
- Scene/storyboard validation: empty custom scenes, missing field, wrong scene-index order, non-positive duration, an unapproved `fact_id` reference, email/phone PII in scene text, total duration too short/too long (9 tests)
- Determinism: identical inputs produce an identical `video_asset_id` across independent registry instances (1 test)
- Duplicate idempotency (1 test)
- Conflicting duplicate rejection: a tampered stored record with the same `video_asset_id` but different content is rejected fail-closed (1 test)
- Serialization/persistence round trip (1 test)
- No-network / no-rendering assertion (1 test)
- Full-lifecycle regression (1 test)

**Real (non-mocked) upstream integration:** every fixture is built by calling the actual Node 11 `classify_demand_signal`, Node 12 `score_demand_opportunity`, Node 13 `discover_demand_path`, Node 14 `select_channel_placements`, Node 15 `CampaignClusterRegistry.generate_and_register`, Node 16 `CanonicalKnowledgeStore.register_fact`, and Node 17 `generate_asset_payload` functions/classes directly — none of Gemini's or this session's own Node 11-17 logic is mocked or reimplemented.

**External side effects:** none. No network call, no actual video rendering, no paid media/LLM APIs, no uploads, publishing, or credentials — `external_action` is a literal `False` guarantee on every record, and `render_manifest`/`licensing_metadata` describe intent only, never real media. `video_asset_id` is a deterministic SHA-256-derived hash of `(cluster_id, asset_id, template_version)`, not caller-suppliable.
