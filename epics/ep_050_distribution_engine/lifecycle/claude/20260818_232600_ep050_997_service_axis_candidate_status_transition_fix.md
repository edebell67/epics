# EP050 — Fixed Service-Axis Candidate Stuck at pending_product_definition Forever

Source: Found live while actually completing the `boiler_service` candidate's Node 02/03/04 setup
at the user's request ("i need to set up boiler_service").

Task Type: standard

Task Attributes:
- workflow_task: true
- workflow_name: "ep050_distribution_engine_delivery_20260816"
- workflow_stage: complete
- depends_on:
  - "Winner-triggered candidate clustering (met, shipped earlier this session)"

Task Summary: A service-axis candidate is created with `candidate_status: pending_product_definition`
(plan §4: never auto-copy a differently-scoped product description). `derive_campaign_state()` and
`derive_campaign_position()` both check this static field first, before any real artifact check.
Nothing ever cleared or re-evaluated it once the actual blocking condition (missing Node 02) was
resolved -- so after registering real Node 02/03/04 content for `boiler_service` (per the user's
explicit request and confirmed draft content), the candidate still showed `pending_product_definition`
in Campaign Queue, as if nothing had happened. Fixed by having `handle_node04_register` advance
`candidate_status` from `pending_product_definition` to `pending_phase2_approval` when Node 04
completes -- the same real point a geo-axis candidate already starts at, just earned by hand
instead of copied, since completing Node 04 is what genuinely means "Phase 1 is done" for either
kind of candidate.

Context:
- `epics/ep_050_distribution_engine/implementation/operational_console_claude/server.py` (v1.9.2 -> v1.9.3)
- `epics/ep_050_distribution_engine/implementation/operational_console_claude/test_console_server.py`

Destination Folder: `epics/ep_050_distribution_engine/implementation/operational_console_claude/`; this lifecycle record under `workstream/300_complete/`.

Dependency: Winner-triggered candidate clustering (met, shipped earlier this session).

## Plan
- [x] 1. Registered real Node 02/03/04 content for the live `boiler_service` candidate (per the
      user's confirmed draft), then discovered `candidate_status` hadn't moved.
  - [x] Test: Direct `GET /api/campaign_queue` inspection of the real run.
  - [x] Evidence: Implementation Log.
- [x] 2. Traced the root cause: `derive_campaign_state`/`derive_campaign_position` both trust the
      static `candidate_status` field unconditionally, and nothing ever clears it.
  - [x] Test: Code inspection.
  - [x] Evidence: Implementation Log.
- [x] 3. Fixed `handle_node04_register` to advance the status on completion.
  - [x] Test: New pytest case -- builds a real winner, proposes candidates, fills in a service-axis
        candidate's Node 02/03/04 for real, asserts `candidate_status` becomes
        `pending_phase2_approval` and Campaign Queue reflects it.
  - [x] Evidence: Implementation Log.
- [x] 4. Live-verified against the real `boiler_service` run by re-submitting Node 04 (idempotent)
      after restarting the server with the fix.
  - [x] Test: `GET /api/campaign_queue` confirmed `state: pending_phase2_approval`, `node: Node 05`.
  - [x] Evidence: Implementation Log.
- [x] 5. Full regression pass, version bump.
  - [x] Test: `pytest test_console_server.py -q` -- 87/87.
  - [x] Evidence: Implementation Log.

## Evidence
Objective-Delivery-Coverage: 100% for the identified bug.
Auto-Acceptance: false (found and fixed while directly acting on the user's own real candidate
at their explicit request)
- Evidence-Type: manual_verification
  - Artifact: Real `run_20260818_201454_4c18c60e` (`boiler_service`) -- confirmed stuck at
    `pending_product_definition` with real Node 02/03/04 data already present; confirmed
    transitioned to `pending_phase2_approval` / Phase 2 / Node 05 after the fix, via a real
    idempotent Node 04 re-submission (no data changed, only the status logic).
  - Objective-Proved: The fix corrects real, already-existing broken state, not just new cases.
  - Status: captured
- Evidence-Type: test_output
  - Artifact: `pytest test_console_server.py -q` -- 87/87 (1 new case).
  - Objective-Proved: No regression; the transition is directly covered going forward.
  - Status: captured

## Implementation Log
- 2026-08-18T23:10+01:00 -- User asked to set up `boiler_service`; drafted Node 02 content,
  confirmed by the user, registered Node 02/03/04 for the real candidate.
- 2026-08-18T23:12+01:00 -- Checked Campaign Queue: `boiler_service` still showed
  `pending_product_definition` despite Node 02/03/04 all being genuinely complete. Traced root
  cause in `derive_campaign_state`/`derive_campaign_position`.
- 2026-08-18T23:13+01:00 -- Added the transition to `handle_node04_register`.
- 2026-08-18T23:14+01:00 -- Added and ran the new regression test; full suite 87/87.
- 2026-08-18T23:16+01:00 -- Restarted the dev server, re-submitted Node 04 for the real
  `boiler_service` run (idempotent), confirmed it correctly advanced to
  `pending_phase2_approval` / Phase 2 / Node 05 in Campaign Queue.
- 2026-08-18T23:20+01:00 -- Version bump (server.py v1.9.3), filed this record (after a real-time
  detour answering the user's follow-up questions about Node 02/03/04 semantics and how audience
  needs shape the real search query).

## Changes Made
- Edited `epics/ep_050_distribution_engine/implementation/operational_console_claude/server.py`
  (v1.9.2 -> v1.9.3): `handle_node04_register` now advances `candidate_status` from
  `pending_product_definition` to `pending_phase2_approval` on completion.
- Edited `epics/ep_050_distribution_engine/implementation/operational_console_claude/test_console_server.py`:
  `test_service_axis_candidate_advances_to_pending_phase2_approval_once_product_is_filled_in`.

## Validation
- PASS -- `pytest test_console_server.py -q` -- 87/87.
- PASS -- Live: the real `boiler_service` candidate correctly transitioned after the fix.

## Risks/Notes
- None new. This is a status-tracking correction, not a change to any real data or validation
  rule -- the real Node 02/03/04 content registered for `boiler_service` was already correct and
  unaffected by this fix.

## Completion Status
Complete. Real bug found and fixed while genuinely using the feature as intended, live-verified
against the actual affected run, full regression clean.
