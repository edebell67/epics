# EP050 — Fixed Run Full Pipeline Bypassing the Candidate Approval Gate

Source: Live user session. User loaded a real candidate (Catford, still `pending_phase2_approval`)
into Campaign Overview and clicked "Run Full Pipeline (Phase 2 → 7)" -- it ran Phase 2 through 4
successfully using fabricated demo data before stopping at Phase 5 with a validation error.

Task Type: standard

Task Attributes:
- workflow_task: true
- workflow_name: "ep050_distribution_engine_delivery_20260816"
- workflow_stage: complete
- depends_on:
  - "The Phase 2 candidate approval gate (met, shipped earlier this session)"

Task Summary: Campaign Overview's "Run Full Pipeline (Phase 2 → 7)" button (`runFullPipeline()` in
console.js) drives Phase 2 by clicking through each node's real manual-entry form in DOM order --
it had zero awareness of `candidate_status`, so running it against a candidate still sitting at
`pending_phase2_approval` clicked straight through Phase 2's forms using whatever demo/default
values were pre-filled in them (`sig_demand_01`, `q_demo_01`, `sv_demo_01`, etc.), fabricating a
full real Phase 2-4 chain (video asset, approved package included) under a candidate that was
specifically supposed to earn a real Node 05 signal first. The server-side headless
`pipeline/run_all` already refused this correctly (confirmed by an existing regression test); this
DOM-driven button did not, because it never checks the run's real state before proceeding -- same
fabrication the whole approval-gate design was built to prevent, just reachable through a second,
unguarded path. Fixed by adding a `CANDIDATE_BLOCKING_STATUSES` set (mirroring server.py's
`_BLOCKING_CANDIDATE_STATUSES`) and a guard at the top of `runFullPipeline()` that refuses to
proceed when the loaded run is a blocked candidate. The contaminated Catford run was deleted, not
repaired -- a candidate with fabricated Phase 2 data underneath it can't be made trustworthy by
patching individual fields; a fresh proposal earns real data from scratch.

Context:
- `epics/ep_050_distribution_engine/implementation/operational_console_claude/console.js` (v1.10.2 -> v1.10.3)

Destination Folder: `epics/ep_050_distribution_engine/implementation/operational_console_claude/`; this lifecycle record under `workstream/300_complete/`.

Dependency: The Phase 2 candidate approval gate (met, shipped earlier this session).

## Plan
- [x] 1. Diagnosed the real bug from the user's live screenshot: traced the lineage panel showing
      all 6 Phase 2 nodes fired with demo/placeholder IDs, confirmed `candidate_status` was still
      `pending_phase2_approval` even after the fabricated chain was built.
  - [x] Test: Direct `GET /api/runs/{id}` inspection of the real contaminated Catford run.
  - [x] Evidence: Implementation Log.
- [x] 2. Added the guard to `runFullPipeline()`.
  - [x] Test: Live browser -- loaded the still-contaminated Catford run, clicked Run Full
        Pipeline, confirmed it now refuses with a clear message instead of proceeding.
  - [x] Evidence: Implementation Log.
- [x] 3. Confirmed the guard doesn't over-block: loaded the real non-candidate source run, clicked
      Run Full Pipeline, confirmed it still runs normally (hit the same pre-existing, already-
      documented "already complete" conflict, unrelated to this fix).
  - [x] Test: Live browser.
  - [x] Evidence: Implementation Log.
- [x] 4. Deleted the contaminated Catford run.
  - [x] Test: `GET /api/campaign_queue` confirms 8 campaigns remain, Catford absent, phase_counts
        correct (P1=3, P2=4, P7=1).
  - [x] Evidence: Implementation Log.
- [x] 5. Full regression pass, version bump.
  - [x] Test: `pytest test_console_server.py -q` -- 86/86 (server-side untouched by this fix).
  - [x] Evidence: Implementation Log.

## Evidence
Objective-Delivery-Coverage: 100% for the identified gap.
Auto-Acceptance: false (fabrication-prevention bug found directly by the user during real use;
fix and cleanup both explicitly requested)
- Evidence-Type: manual_verification
  - Artifact: Real contaminated run (`run_20260818_201453_74c7c89a`, Catford) -- `candidate_status`
    confirmed still `pending_phase2_approval` while real fabricated Node05-19 records existed
    underneath it; guard confirmed refusing on this exact run; guard confirmed NOT blocking the
    real source run; run deleted; `GET /api/campaign_queue` confirmed clean state afterward.
  - Objective-Proved: The fix closes the real hole without over-blocking legitimate runs.
  - Status: captured
- Evidence-Type: test_output
  - Artifact: `pytest test_console_server.py -q` -- 86/86.
  - Objective-Proved: No server-side regression (this was a client-side-only fix; the equivalent
    server-side guard on `pipeline/run_all` already existed and is already covered by
    `test_pipeline_run_all_refuses_to_run_a_candidate_pending_approval`).
  - Status: captured

## Implementation Log
- 2026-08-18T22:40+01:00 -- User shared a screenshot showing Catford's Run Full Pipeline stopped
  at Node 20 with a validation error; traced the lineage panel and found all 6 Phase 2 nodes had
  fired with demo/placeholder data.
- 2026-08-18T22:42+01:00 -- Confirmed via direct API call: `candidate_status` still
  `pending_phase2_approval`, yet real (fabricated) `sig_demand_01`/`q_demo_01` records existed.
  Explained the gap to the user and proposed fixing it plus cleaning up Catford.
- 2026-08-18T22:44+01:00 -- User confirmed both. Added `CANDIDATE_BLOCKING_STATUSES` and the guard
  to `runFullPipeline()`.
- 2026-08-18T22:46+01:00 -- Live-verified: reloaded, loaded Catford, clicked Run Full Pipeline,
  confirmed refusal message; loaded the real source run, confirmed it still runs normally.
- 2026-08-18T22:47+01:00 -- Deleted the contaminated Catford run directory; confirmed via
  `GET /api/campaign_queue` that 8 campaigns remain with correct phase_counts.
- 2026-08-18T22:48+01:00 -- Full regression (86/86), version bump (console.js v1.10.3), filed this
  record.

## Changes Made
- Edited `epics/ep_050_distribution_engine/implementation/operational_console_claude/console.js`
  (v1.10.2 -> v1.10.3): `CANDIDATE_BLOCKING_STATUSES`, guard at the top of `runFullPipeline()`.
- Deleted `epics/ep_050_distribution_engine/implementation/operational_console_claude/data/runs/run_20260818_201453_74c7c89a/`
  (the contaminated Catford run).

## Validation
- PASS -- `pytest test_console_server.py -q` -- 86/86.
- PASS -- Live: guard refuses on a real blocked candidate.
- PASS -- Live: guard does not block a real non-candidate run.
- PASS -- Live: Campaign Queue confirms correct state (8 campaigns, no Catford, correct counts)
  after cleanup.

## Risks/Notes
- **Scope is deliberately this one button.** The equivalent server-side guard already existed on
  `pipeline/run_all` (Campaign Queue's headless runner). This fix brings the DOM-driven Campaign
  Overview button up to the same standard, closing the one path that didn't already have it.
- A human can still manually operate a candidate run's individual Phase 1/2 forms one at a time
  (e.g. filling in Node 02 for a service-axis candidate) -- that legitimate path is untouched;
  only the automated "run everything" convenience action is blocked.

## Completion Status
Complete. Real fabrication-prevention bug found live, fixed, verified both directions (refuses
correctly / doesn't over-block), contaminated data cleaned up, full regression clean.
