# EP050 — Campaign Queue Persistent Approve-Phase-2 Button

Source: Direct user question ("are they in the automation process?") about the 8 candidate
campaigns just created. Answering it honestly surfaced a real UX gap.

Task Type: standard

Task Attributes:
- workflow_task: true
- workflow_name: "ep050_distribution_engine_delivery_20260816"
- workflow_stage: complete
- depends_on:
  - "20260818_212700_ep050_997_propose_candidates_race_condition_fix.md (candidates this gap was found on)"

Task Summary: The "Approve real Phase 2 live-fetch" button only ever rendered inside the
transient list built right after the original "Propose one-hop candidate campaigns" click
(`buildCandidateApprovalRow`, called only from that one handler). Once `propose_candidates` became
idempotent (server.py v1.9.0's race-condition-adjacent fix), a repeat click returns `created: []`
and never regenerates that list -- so after any page reload, a candidate sitting in
`pending_phase2_approval` had no way to be approved at all through the UI. Fixed by rendering the
same approve button in Campaign Queue's per-row output whenever a row's state is
`pending_phase2_approval`, which persists across reloads since it's built from the live
`/api/campaign_queue` snapshot every refresh. Live-verified by approving a real candidate
(Greenwich) from the queue and confirming it correctly transitioned to `parked` and the button
disappeared once no longer applicable.

Context:
- `epics/ep_050_distribution_engine/implementation/operational_console_claude/console.js` (v1.10.0 -> v1.10.1)

Destination Folder: `epics/ep_050_distribution_engine/implementation/operational_console_claude/`; this lifecycle record under `workstream/300_complete/`.

Dependency: The 8 real candidate campaigns created earlier this session (met).

## Plan
- [x] 1. Diagnosed the gap: traced `buildCandidateApprovalRow`'s only call site, confirmed it's
      only reachable from the one-shot propose click, and that idempotency (a prior fix) means
      that list never regenerates on a repeat click or page reload.
  - [x] Test: Code inspection (`grep buildCandidateApprovalRow`) confirmed a single call site.
  - [x] Evidence: Implementation Log.
- [x] 2. Added the same approve action to Campaign Queue's per-row rendering, gated on
      `c.state === "pending_phase2_approval"`.
  - [x] Test: Live browser -- fresh page load, navigated to Campaign Queue, confirmed the button
        renders for all 5 geo-axis candidates still pending.
  - [x] Evidence: Implementation Log.
- [x] 3. Live-verified the button actually works, not just renders.
  - [x] Test: Clicked "Approve real Phase 2 live-fetch" for the real Greenwich candidate; polled
        `/api/campaign_queue`, confirmed state changed to `parked`; confirmed the button no longer
        renders for that row.
  - [x] Evidence: Implementation Log.
- [x] 4. Full regression pass.
  - [x] Test: `pytest test_console_server.py -q` -- 81/81 (UI-only change, no server logic touched).
  - [x] Evidence: Implementation Log.

## Evidence
Objective-Delivery-Coverage: 100% for the identified gap.
Auto-Acceptance: false (user directly asked the question that surfaced this and asked for the fix)
- Evidence-Type: manual_verification
  - Artifact: Live browser session -- approved the real `run_20260818_201453_09dd8f99` (Greenwich)
    candidate from Campaign Queue; server state confirmed transitioned `pending_phase2_approval`
    -> `parked` (real Node 05 Search 403); UI confirmed the approve button correctly disappeared.
  - Objective-Proved: The fix works end-to-end against real state, not just renders.
  - Status: captured
- Evidence-Type: test_output
  - Artifact: `pytest test_console_server.py -q` -- 81/81.
  - Objective-Proved: No regression from the UI change (server-side logic untouched).
  - Status: captured

## Implementation Log
- 2026-08-18T21:52+01:00 -- User asked "are they in the automation process?"; answering honestly
  required tracing `buildCandidateApprovalRow`'s call sites, which surfaced the gap.
- 2026-08-18T21:55+01:00 -- Reported the gap to the user; user asked for the fix.
- 2026-08-18T21:58+01:00 -- Added the approve button to Campaign Queue's `refreshQueue()` row
  rendering, gated on `pending_phase2_approval`.
- 2026-08-18T22:00+01:00 -- Live-verified: fresh page load, Campaign Queue showed the button for
  all 5 geo candidates; clicked it for Greenwich; confirmed real state transition to `parked` and
  the button's correct disappearance afterward.
- 2026-08-18T22:07+01:00 -- Full regression (81/81), version bump (console.js v1.10.1), filed this
  record.

## Changes Made
- Edited `epics/ep_050_distribution_engine/implementation/operational_console_claude/console.js`
  (v1.10.0 -> v1.10.1): `refreshQueue()` now renders "Approve real Phase 2 live-fetch" per row
  when `c.state === "pending_phase2_approval"`.

## Validation
- PASS -- `pytest test_console_server.py -q` -- 81/81.
- PASS -- Live: button renders persistently after a fresh page load.
- PASS -- Live: clicking it produces a real, correct state transition (verified against the
  actual live candidate, not a test fixture).

## Risks/Notes
- None new. This closes a real usability gap in a feature shipped earlier the same session; no
  new architectural surface introduced.

## Completion Status
Complete. Gap found via direct user question, fixed, live-verified against real candidate state,
full regression clean.
