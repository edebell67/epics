# EP050 — Global Phase/Node Summary Matrix

Source: Direct user request with an ASCII mockup: a global page/summary showing P1-P7 (with node
ranges) and a count of campaigns per phase, drilling down to campaign name / current node / real
action ("stopped, community discussion, video generation, or whatever relevant reason").

Task Type: standard

Task Attributes:
- workflow_task: true
- workflow_name: "ep050_distribution_engine_delivery_20260816"
- workflow_stage: complete
- depends_on:
  - "Campaign Queue (met, shipped earlier this session)"

Task Summary: Added `derive_campaign_position(meta)` to server.py, which walks the exact same real
artifact checks `run_pipeline_headless()` already uses to decide what to run next -- read-only, so
it reports where a campaign genuinely stands without ever executing anything -- returning
`{phase, node, action}` for every real state a campaign can be in. Critically, the `action` for a
parked candidate is the real stored `candidate_park_reason` (e.g. Node 05's actual HTTP 403 text),
not a canned label, directly answering the user's earlier "parked where??" question inline in the
UI instead of requiring a raw API call. `campaign_queue_snapshot()` now returns `phase`/`node`/
`action` per campaign plus a `phase_counts` summary (1-7). console.js's Campaign Queue panel gained
a 7-cell clickable matrix (live counts, click to filter the list to just that phase) and each row
now shows its real phase/node/action instead of the old coarse state label.

Context:
- `epics/ep_050_distribution_engine/implementation/operational_console_claude/server.py` (v1.9.1 -> v1.9.2)
- `epics/ep_050_distribution_engine/implementation/operational_console_claude/console.js` (v1.10.1 -> v1.10.2)
- `epics/ep_050_distribution_engine/implementation/operational_console_claude/test_console_server.py`

Destination Folder: `epics/ep_050_distribution_engine/implementation/operational_console_claude/`; this lifecycle record under `workstream/300_complete/`.

Dependency: Campaign Queue (met, shipped earlier this session).

## Plan
- [x] 1. Confirmed understanding of the requested format with the user before building (phase
      summary strip with counts, drill-down to campaign/node/action) since there was real
      ambiguity in how to bucket a campaign's "current phase."
  - [x] Test: N/A (design confirmation in chat).
  - [x] Evidence: Implementation Log.
- [x] 2. Implemented `derive_campaign_position()`, mirroring `run_pipeline_headless()`'s exact
      real-artifact walk order so "current node" can never drift from what the automation would
      actually do next.
  - [x] Test: 5 new pytest cases covering a fresh run, a needs-facts position, winner-detected,
        and -- critically -- that a parked candidate's action is the REAL park reason, not a label.
  - [x] Evidence: Implementation Log.
- [x] 3. Enriched `campaign_queue_snapshot()` with phase/node/action + phase_counts.
  - [x] Test: `test_campaign_queue_phase_counts_sum_to_total_campaigns`.
  - [x] Evidence: Implementation Log.
- [x] 4. Built the console.js matrix UI (7 clickable cells) and enriched per-row display.
  - [x] Test: Live browser -- verified real counts (P1=3, P2=5, P7=1 matching the actual 9
        campaigns), click-to-filter works, status line reflects the active filter.
  - [x] Evidence: Implementation Log.
- [x] 5. Full regression pass, version bumps.
  - [x] Test: `pytest test_console_server.py -q` -- 86/86.
  - [x] Evidence: Implementation Log.

## Evidence
Objective-Delivery-Coverage: 100% for the requested format.
Auto-Acceptance: false (new user-facing dashboard surface; verified live against real campaign
state as it was built)
- Evidence-Type: manual_verification
  - Artifact: Live browser session against the real 9 campaigns -- matrix showed P1=3 (the 3
    pending_product_definition candidates), P2=5 (Greenwich parked + 4 pending approval), P7=1
    (the winner-detected source run); clicking P1 filtered the list to exactly those 3; Greenwich's
    row showed the real HTTP 403 text inline.
  - Objective-Proved: The matrix and drill-down both reflect genuinely real state, not mocked data.
  - Status: captured
- Evidence-Type: test_output
  - Artifact: `pytest test_console_server.py -q` -- 86/86 (5 new cases for this feature).
  - Objective-Proved: No regression; the position-derivation logic is directly tested.
  - Status: captured

## Implementation Log
- 2026-08-18T22:15+01:00 -- User shared an ASCII mockup requesting a global P1-P7 summary with
  drill-down to campaign/status/action; confirmed understanding before building.
- 2026-08-18T22:18+01:00 -- Implemented `derive_campaign_position()` mirroring
  `run_pipeline_headless()`'s exact check order; enriched `campaign_queue_snapshot()`.
- 2026-08-18T22:24+01:00 -- Added 5 pytest cases; all passing.
- 2026-08-18T22:28+01:00 -- Built the console.js matrix (PHASE_ORDER, renderMatrix/renderList
  split, click-to-filter) and enriched row display.
- 2026-08-18T22:33+01:00 -- Restarted dev server, live-verified real counts and the real Node 05
  403 text now showing inline for Greenwich; fixed a small status-line inconsistency (filter
  wasn't reflected in the status text) found during verification.
- 2026-08-18T22:36+01:00 -- Full regression (86/86), version bumps (server.py v1.9.2, console.js
  v1.10.2), filed this record.

## Changes Made
- Edited `epics/ep_050_distribution_engine/implementation/operational_console_claude/server.py`
  (v1.9.1 -> v1.9.2): `derive_campaign_position()`, enriched `campaign_queue_snapshot()`.
- Edited `epics/ep_050_distribution_engine/implementation/operational_console_claude/console.js`
  (v1.10.1 -> v1.10.2): `PHASE_ORDER`, `buildCampaignQueuePanel()`'s `renderMatrix()`/`renderList()`
  split, `updateStatus()`.
- Edited `epics/ep_050_distribution_engine/implementation/operational_console_claude/test_console_server.py`:
  5 new test cases.

## Validation
- PASS -- `pytest test_console_server.py -q` -- 86/86.
- PASS -- Live: matrix counts match real campaign state exactly.
- PASS -- Live: click-to-filter and status line both work correctly.
- PASS -- Live: Greenwich's real park reason (actual HTTP 403 URL/message) shows inline, not a
  canned label -- directly closing the "parked where??" gap from earlier in the session.

## Risks/Notes
- None new. Read-only reporting layer over existing real state; no new write paths introduced.

## Completion Status
Complete. Built to the user's requested format, confirmed understanding first, live-verified
against real campaign state, full regression clean.
