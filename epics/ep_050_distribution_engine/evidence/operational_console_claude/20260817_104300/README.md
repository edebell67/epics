# EP050 Operational Console v2 — Evidence Bundle (20260817_104300)

> VERSION HISTORY
> - v1.0.0 · 2026-08-17 · Reactivation-pass evidence: Node 15/16/18 wiring, per allocation 20260817T095239426_codex_f21198e1.

**Command:**
```
python -m pytest epics/ep_050_distribution_engine/implementation/operational_console_claude/test_console_server.py -v --basetemp=<scratchpad>/pytest_tmp_console_final
```

**Result:** 26 passed, 0 failed, 0 errors, 4.59s (18 pre-existing + 8 new). Full output in `pytest_output.txt`.

**New backend coverage (8 tests):**
- `test_phases_endpoint_reports_node15_18_as_implemented` — Phase 3 implemented_nodes = `["11","12","13","14","15"]`, locked_nodes = `[]`; Phase 4 implemented_nodes = `["16","17","18"]`, locked_nodes = `["19"]`.
- Node 15: rejection without any classification (`no_classifications`), positive cluster generation from a real classified signal.
- Node 16: rejection without a target (`no_target`), positive fact registration.
- Node 18: rejection with an unknown cluster (`cluster_not_found`), rejection with an unknown fact (`fact_not_found`), positive video-asset generation.
- `test_full_lifecycle_regression` extended to run the complete Node 01→11→15→16→18 chain and assert 8 lineage events.

**Real (non-mocked) browser E2E** — driven live against a fresh server instance (old stale process on :8060 stopped and restarted with the updated code first):
1. New Run → Register Target (Node 01) → real `tgt_boiler_repair_blackheath`.
2. Phase 3: Classify Signal (Node 11) → real classification, `primary_intent: troubleshooting`, `urgency_level: high`.
3. Phase 3: Generate Campaign Cluster(s) (Node 15, running real Node 12→13→14 internally) → real `cluster_21f2d753af1b4e42`, 1 member.
4. Phase 4: Register Canonical Fact (Node 16) → real `fact_c6f11d4da64ef17e`.
5. Phase 4: cluster dropdown and fact multi-select auto-populated live from the run state (confirms `refreshNode18Selectors()` wiring) → selected the fact, clicked Generate Video Asset (Node 18, running real Node 17 internally) → real `vid_168841f6aa43052a` with full lineage back to the target, script/storyboard/shot-list/caption/branding/CTA/render-manifest all populated, `external_action: false`.
6. Captured full run state via `GET /api/runs/<run_id>`: `browser_e2e_run_state.json` — 6 lineage events (created, node_01, node_11, node_15, node_16, node_18), 1 cluster, 1 fact, 1 asset, 1 video_asset.
7. No browser console errors.
8. Locked-node inertness re-verified programmatically: Node 04 and Node 19 both render `.node-block--locked`; the locked-phase "Execute Phase (Locked)" button is `disabled === true`.
9. Responsive check at mobile width (375px): phase rail stacks cleanly, Phase 3/4 badges ("Operable: Node 11, 12, 13, 14, 15" / "Operable: Node 16, 17, 18") remain legible.

**External side effects:** none. No network call beyond loopback, no actual video rendering, no paid media/LLM APIs, no publishing/routing/payment/deployment. `external_action: false` on every generated record, confirmed in the live-captured `vid_` record.
