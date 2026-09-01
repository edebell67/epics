# EP050 — Winner Replication & Scale-Out Build

Source: Direct user chat instruction sequence (2026-08-18) — multi-turn design review culminating
in "yes, write it up" (design doc approval), "add that section... go ahead and build it and update
percent complete as each is completed" (build approval). Design captured in
`plans/20260818_1645_ep050_winner_replication_and_scale_out.md`.

Task Type: standard

Task Attributes:
- workflow_task: true
- workflow_name: "ep050_distribution_engine_delivery_20260816"
- workflow_stage: complete
- depends_on:
  - "A detected winner (Node 34 is_winner=True) to trigger replication from (met, run_20260818_102850_a3e4d29f)"

Task Summary: Built the full 8-item plan for closing the winner-detection loop: (1) curated
real geo-adjacency + service-taxonomy reference data, (2) winner-triggered one-hop candidate
clustering at Node 01, (3) a human-approval gate before any candidate's real Node 05 live-fetch
fires (with two distinct fail-closed stop states: parked vs. stopped-no-demand — never a fixture
fallback), (4) an opt-in cost ledger schema, (5) a Campaign Queue view + genuinely concurrent
headless pipeline driver, (6) CSV bulk import feeding the same queue, (7) auto-propose-on-winner
wired into `runFullPipeline()` (and fixed a real pre-existing gap: that function had been fully
built earlier this session but never attached to any button), (8) this regression pass and record.

Context:
- `epics/ep_050_distribution_engine/implementation/shared/candidate_expansion.py` (new)
- `epics/ep_050_distribution_engine/implementation/shared/test_candidate_expansion.py` (new)
- `epics/ep_050_distribution_engine/implementation/operational_console_claude/server.py` (v1.8.0 -> v1.9.0)
- `epics/ep_050_distribution_engine/implementation/operational_console_claude/console.js` (v1.9.0 -> v1.10.0)
- `epics/ep_050_distribution_engine/implementation/operational_console_claude/test_console_server.py`
- `workstream/600_workflow/ep050/EP050_distribution_engine_master_workflow.html` (Planned lane + impacted-node tags)
- `plans/20260818_1645_ep050_winner_replication_and_scale_out.md`

Destination Folder: `epics/ep_050_distribution_engine/implementation/`; this lifecycle record under `workstream/300_complete/`.

Dependency: A real detected winner in at least one run (met).

## Plan
- [x] 1. Curated geo-adjacency + service-taxonomy reference files.
  - [x] Test: `pytest shared/test_candidate_expansion.py -q` — 11/11.
  - [x] Evidence: Implementation Log.
- [x] 2. Node 01 candidate auto-registration from a winner (one-hop, both axes; geo-axis copies
      real Node 02/03/04/16; service-axis stops at `pending_product_definition` rather than
      fabricate a product description).
  - [x] Test: `pytest test_console_server.py -k propose_candidates -q`.
  - [x] Evidence: Implementation Log; live-verified against the real run (8 real candidates created).
- [x] 3. Phase 2 candidate approval branch (pending/parked/stopped states); never a fixture signal.
  - [x] Test: `pytest test_console_server.py -k approve_phase2 -q`.
  - [x] Evidence: Implementation Log; live-verified — hit the real, already-documented Node 05
        Search 403 constraint and correctly parked instead of fabricating a signal.
- [x] 4. Cost ledger field (`append_lineage(cost_gbp=...)`, opt-in, never estimated) + Campaign
      Overview spend rollup (renders nothing while zero, not a misleading £0.00).
  - [x] Test: `pytest test_console_server.py -k cost_gbp -q`, incl. a baseline-lock test asserting
        today's real chain carries zero cost_gbp entries.
  - [x] Evidence: Implementation Log.
- [x] 5. Campaign Queue (multi-run view, real per-campaign state) + genuinely concurrent headless
      pipeline driver (`run_pipeline_headless`, in-process calls to the real handlers, not DOM
      clicks).
  - [x] Test: `pytest test_console_server.py -k "pipeline_run_all or campaign_queue" -q` — 5/5.
  - [x] Evidence: Implementation Log; live-verified (zero-runnable case fires no stray requests).
- [x] 6. Bulk spreadsheet (CSV) import feeding the same queue, same real Node 01-04 validation as
      manual entry, one bad row reported and skipped without blocking the rest.
  - [x] Test: `pytest test_console_server.py -k bulk_import -q` — 4/4.
  - [x] Evidence: Implementation Log.
- [x] 7. Extended `runFullPipeline()` to auto-propose candidates on a detected winner; added an
      idempotency guard (`last_proposed_winner_id`) so repeat runs never mint duplicates; found
      and fixed a real pre-existing gap (the function existed but was never wired to any button).
  - [x] Test: `pytest test_console_server.py -k propose_candidates -q` (idempotency case).
  - [x] Evidence: Implementation Log; live-verified — button now wired, correctly fails closed
        on a real conflict when re-run against an already-completed run.
- [x] 8. Full regression pass, version bumps, this record.
  - [x] Test: `pytest operational_console_claude/test_console_server.py -q` — 78/78;
        `pytest shared/test_candidate_expansion.py -q` — 11/11.
  - [x] Evidence: Implementation Log.

## Evidence
Objective-Delivery-Coverage: 100% for all 8 plan items as scoped and agreed. Not in scope (by
design, per plan §10 non-goals): real external dispatch (Node 22/23), and wiring an actual
cost_gbp into any node (nothing has a confirmed real, currently-billed rate yet).
Auto-Acceptance: false (new automation surface with a real approval gate; verification requested
in chat as work progressed, "update percent complete as each is completed")
- Evidence-Type: test_output
  - Artifact: `pytest operational_console_claude/test_console_server.py -q` — 78/78 (up from 65 at
    session start); `pytest shared/test_candidate_expansion.py -q` — 11/11.
  - Objective-Proved: Zero regressions; every new code path has dedicated coverage.
  - Status: captured
- Evidence-Type: manual_verification
  - Artifact: Live browser session against `run_20260818_102850_a3e4d29f` — "Propose one-hop
    candidate campaigns" created 8 real candidates (5 geo: Lewisham/Greenwich/Catford/Charlton/
    Eltham; 3 service: boiler_service/boiler_installation/central_heating_repair); approving a
    geo candidate's Phase 2 hit the real Node 05 Search 403 and parked correctly; Campaign Queue
    and bulk-import UI rendered and ran with no console errors; "Run Full Pipeline" button (newly
    wired) correctly failed closed on a real conflict when re-run against the completed live run.
  - Objective-Proved: The whole chain works against real state, not just fixtures, and fails
    safely rather than fabricating data when it hits a genuine real-world constraint.
  - Status: captured
- Evidence-Type: doc_sync
  - Artifact: `workstream/600_workflow/ep050/EP050_distribution_engine_master_workflow.html` —
    Planned lane (5 cards) + impacted-node tags on Phase 1/4/7, percent-complete reduced then
    incrementally restored as each item completed, evidence fields updated per item.
  - Objective-Proved: The tracked workflow artifact reflects real, current build status, not
    aspirational or stale claims.
  - Status: captured

## Implementation Log
- 2026-08-18T16:45+01:00 — Wrote and got sign-off on the design doc (`plans/20260818_1645_...md`),
  through a multi-turn review covering format-diversification replication, one-hop geo/service
  clustering with curated real adjacency sources, the Phase 2 approval gate with its two distinct
  fail-closed states, the parallel Campaign Queue, bulk CSV import, and the cost ledger.
- 2026-08-18T16:50+01:00 — Added the "Planned — pending sign-off" lane + impacted-node tags to the
  master workflow HTML per explicit instruction, before any code changes.
- 2026-08-18T18:00+01:00 — Build approved ("go ahead and build it"). Reduced percent-complete on
  Phase 1/4/7 to reflect in-progress work, per explicit instruction.
- 2026-08-18T18:05+01:00 — Item 1: `shared/candidate_expansion.py` + tests, 11/11 passing.
- 2026-08-18T18:15+01:00 — Items 2/3: `handle_node01_propose_candidates` /
  `handle_node01_approve_phase2`, product/audience/facts copy for geo-axis, 7/7 new tests passing.
  Live-verified against the real run: 8 real candidates created; approving Lewisham's Phase 2 hit
  the real Google Search 403 and parked correctly, with `demand_signals` confirmed absent (no
  fixture fallback). Cleaned up the 8 verification-only candidate runs afterward.
- 2026-08-18T18:35+01:00 — Item 4: cost ledger schema + Campaign Overview rollup, 3/3 new tests.
- 2026-08-18T18:50+01:00 — Item 5: `run_pipeline_headless`/`derive_campaign_state`/Campaign Queue
  endpoints + panel, 5/5 new tests, live-verified.
- 2026-08-18T19:10+01:00 — Item 6: `handle_bulk_import` + CSV upload widget, 4/4 new tests.
- 2026-08-18T19:20+01:00 — Item 7: found `runFullPipeline()` was fully built but never wired to a
  button (dead code from earlier this session); wired it, extended it with auto-propose-on-winner,
  added the `last_proposed_winner_id` idempotency guard after observing live duplication.
  Live-verified: correctly fails closed on re-run against the completed run.
- 2026-08-18T19:40+01:00 — Item 8: full regression (78/78 + 11/11), version history bumps for
  `server.py` (v1.9.0, also documenting the previously-unversioned Phase 6/7 handler wiring) and
  `console.js` (v1.10.0, also documenting the previously-unversioned Phase 6/7 UI), updated the
  master workflow doc's evidence fields for every Planned card and restored Phase 1/4/7 badges to
  reflect real completion. Filed this record.

## Changes Made
- Added `epics/ep_050_distribution_engine/implementation/shared/candidate_expansion.py`.
- Added `epics/ep_050_distribution_engine/implementation/shared/test_candidate_expansion.py`.
- Edited `epics/ep_050_distribution_engine/implementation/operational_console_claude/server.py`
  (v1.8.0 -> v1.9.0): `append_lineage(cost_gbp=...)`, `_register_candidate_run`,
  `handle_node01_propose_candidates`, `handle_node01_approve_phase2`, `_park_candidate`,
  `handle_node18_replicate_winner`, `derive_campaign_state`, `run_pipeline_headless`,
  `handle_pipeline_run_all`, `campaign_queue_snapshot`, `handle_bulk_import`, plus new routes
  (`node01/propose_candidates`, `node01/approve_phase2`, `node18/replicate_winner`,
  `pipeline/run_all`, `GET /api/campaign_queue`, `POST /api/bulk_import`).
- Edited `epics/ep_050_distribution_engine/implementation/operational_console_claude/console.js`
  (v1.9.0 -> v1.10.0): `buildWhatWorkedSection`, `buildSpendRollup`, `buildCandidateApprovalRow`,
  `buildCampaignQueuePanel`, `runFullPipeline` (extended + wired to a button for the first time),
  `buildCampaignOverviewPanel` (new Run Full Pipeline button).
- Edited `epics/ep_050_distribution_engine/implementation/operational_console_claude/test_console_server.py`:
  13 new test cases (propose_candidates, approve_phase2, cost ledger, headless pipeline,
  campaign queue, bulk import).
- Edited `workstream/600_workflow/ep050/EP050_distribution_engine_master_workflow.html`: Planned
  lane, impacted-node tags, percent-complete reduced then restored with real evidence per item.

## Validation
- PASS — `pytest operational_console_claude/test_console_server.py -q` — 78/78.
- PASS — `pytest shared/test_candidate_expansion.py -q` — 11/11.
- PASS — `python -c "import server"` — clean import throughout.
- PASS — Live browser verification against the real run for every UI surface added (Campaign
  Overview winner card buttons, Campaign Queue panel, bulk import widget, Run Full Pipeline
  button), zero new console errors.
- PASS — Real-world fail-closed behavior confirmed twice: Node 05's real Search 403 correctly
  parked a candidate rather than fabricating a signal; re-running the DOM pipeline on a completed
  run correctly stopped at a real conflict rather than corrupting state.

## Risks/Notes
- **`runAllInPanel`/`runFullPipeline` (the DOM-click mechanism) is not idempotent on an
  already-advanced run** — it has no "skip if already done" guards, unlike the newer headless
  `pipeline/run_all`. This is pre-existing behavior from earlier this session, not introduced or
  changed here; documented for whoever next touches that function.
- **Service-axis candidates need a human (or a future bulk-import row) to describe their real
  product** before they can request Phase 2 approval — deliberate, not a missing feature: an
  auto-copied "boiler_repair" product description would misrepresent a "boiler_service" offering.
- **Gate 2 (pre-distribution/cost approval) has no live path to exercise yet** — nothing in this
  pipeline performs a real external or paid action today, so it's dormant by design, ready for
  whenever Node 22/23 real dispatch or a paid render/ad step gets wired in.
- **Node 05 (Google Custom Search) remains genuinely blocked** by the previously-documented 403
  constraint — this build makes that failure mode safe and visible (parked, not fabricated) rather
  than resolving the underlying Google-side restriction, which stays out of scope.

## Completion Status
Complete for all 8 items as designed and approved. Regression clean, docs synced, live-verified
against real state including two genuine real-world failure paths handled correctly.
