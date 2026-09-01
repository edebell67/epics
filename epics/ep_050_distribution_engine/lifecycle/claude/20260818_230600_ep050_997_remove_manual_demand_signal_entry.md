# EP050 — Removed Manual Entry from Nodes 05-10 (Demand Intelligence)

Source: Direct user instruction, following the Catford fabrication-hole discussion: "i think the
manual version is unworkable... good for testing... but not for real use!!!!" / "well... we wont
use them for real analysis!!!!" / "it has to be automated and work via searching + automated
process only."

Task Type: standard

Task Attributes:
- workflow_task: true
- workflow_name: "ep050_distribution_engine_delivery_20260816"
- workflow_stage: complete
- depends_on:
  - "20260818_224800_ep050_997_run_full_pipeline_candidate_gate_bypass_fix.md (the fabrication hole that prompted this)"

Task Summary: Each of the six Phase 2 node blocks (Node 05 Search Demand, Node 06 Question
Discovery, Node 07 Social/Video Discovery, Node 08 Competitor Intelligence, Node 09 Community
Intelligence, Node 10 Trend Detection) had a manual "Record X" submit button, pre-filled with
demo/fixture values (`sig_demand_01`, `q_demo_01`, `sv_demo_01`, `cp_demo_01`, `cm_demo_01`,
`trend_demo_01`), sitting immediately next to its real "Live fetch" button -- visually
indistinguishable at a glance, and exactly the mechanism that fabricated Catford's Phase 2 data
earlier this session. The user's underlying point: a demand signal is defined as *observed* real
demand (the live-fetch path calls the real provider API and either gets a real result or fails);
a manually-typed value can never be verified as genuine research versus something typed in to
unblock a run, so it has no place in real operational use, however useful it remains for building
test fixtures. Removed the manual submit button and all manual-only fields from all six blocks,
keeping only the fields each block's own Live fetch call actually uses (e.g. Node 08 keeps
competitor_url/channel/query; Node 06/07 need no node-specific fields at all beyond the shared
topic/geography). Also removed the now-fully-dead shared "source type" field (no live-fetch
payload ever referenced it) and the "Run all Phase 2" button (nothing left in that phase for it to
click, since none of the six blocks have a manual button anymore).

Context:
- `epics/ep_050_distribution_engine/implementation/operational_console_claude/console.js` (v1.10.3 -> v1.10.4)

Destination Folder: `epics/ep_050_distribution_engine/implementation/operational_console_claude/`; this lifecycle record under `workstream/300_complete/`.

Dependency: The Run Full Pipeline candidate-gate bypass fix (met, same session, same root cause family).

## Plan
- [x] 1. Read all six node blocks in full to map exactly which fields each Live fetch call
      actually uses, before removing anything, so nothing needed by a real live-fetch call got
      dropped by mistake.
  - [x] Test: Cross-checked each block's `liveButton()` payload against its field-grid.
  - [x] Evidence: Implementation Log.
- [x] 2. Removed the manual submit button + manual-only fields from all six blocks; trimmed the
      shared Common block (removed the now-dead "source type" field); removed the "Run all Phase
      2" button.
  - [x] Test: Live browser -- confirmed zero "Record" buttons and zero "Run all Phase 2" button
        anywhere in the Phase 2 panel.
  - [x] Evidence: Implementation Log.
- [x] 3. Verified real live-fetch still works end to end after the removal.
  - [x] Test: Live browser -- clicked Node 06's real Live fetch button on the real source run;
        question count went 1->2 with a genuine new Stack Exchange question (real fetch_receipt,
        HTTP 200, real diy.stackexchange.com URL).
  - [x] Evidence: Implementation Log.
- [x] 4. Confirmed no regression to server-side test fixtures, which build via direct HTTP calls
      to the still-present manual API endpoints, never through this UI.
  - [x] Test: `pytest test_console_server.py -q` -- 86/86 (server-side untouched).
  - [x] Evidence: Implementation Log.
- [x] 5. Version bump, this record.

## Evidence
Objective-Delivery-Coverage: 100% for the requested scope (Nodes 05-10 manual entry removed from
the console UI).
Auto-Acceptance: false (removes a user-facing capability across six nodes; verified live as built,
per explicit user direction)
- Evidence-Type: manual_verification
  - Artifact: Live browser session -- Phase 2 panel confirmed to have zero manual "Record" buttons
    and zero "Run all Phase 2" button; Node 06's real Live fetch button clicked for real, producing
    a genuine new Stack Exchange record with a real fetch_receipt and source URL.
  - Objective-Proved: Manual entry is gone; the real automated path is unaffected and still works.
  - Status: captured
- Evidence-Type: test_output
  - Artifact: `pytest test_console_server.py -q` -- 86/86.
  - Objective-Proved: No server-side regression -- this was a console.js-only UI change; test
    fixtures use the server's manual endpoints directly via HTTP, independent of this UI.
  - Status: captured

## Implementation Log
- 2026-08-18T22:55+01:00 -- User stated the manual demand-signal path is "unworkable... not for
  real use", reinforced with "we wont use them for real analysis" and "it has to be automated and
  work via searching + automated process only." Confirmed this generalizes to all six Phase 2
  nodes, not just Node 05, and read all six blocks in full before editing.
- 2026-08-18T22:58+01:00 -- Trimmed the shared Common block (removed dead "source type" field).
- 2026-08-18T23:00+01:00 -- Rewrote all six node blocks (05-10), removing manual submit buttons
  and manual-only fields, keeping only what each Live fetch call needs.
- 2026-08-18T23:02+01:00 -- Removed the now-dead `sourceTypeSelect()` helper; fixed the Phase 2
  panel's own description text (stale "source type" reference); removed the "Run all Phase 2"
  button (nothing left for it to click).
- 2026-08-18T23:04+01:00 -- Live-verified: reloaded, confirmed zero manual buttons in Phase 2;
  clicked Node 06's real Live fetch on the source run, confirmed a genuine new Stack Exchange
  question was recorded (question count 1->2, real fetch_receipt/HTTP 200/real source URL).
- 2026-08-18T23:05+01:00 -- Full regression (86/86, server-side untouched), version bump
  (console.js v1.10.4), filed this record.

## Changes Made
- Edited `epics/ep_050_distribution_engine/implementation/operational_console_claude/console.js`
  (v1.10.3 -> v1.10.4): `buildDemandIntelligenceCommonBlock()`, `buildNode05Block()` through
  `buildNode10Block()`, removed `sourceTypeSelect()`, removed the Phase 2 "Run all Phase 2" button
  call and fixed the panel's description text.

## Validation
- PASS -- `pytest test_console_server.py -q` -- 86/86.
- PASS -- Live: zero manual buttons anywhere in Phase 2.
- PASS -- Live: real Live fetch still works end to end (Node 06, genuine Stack Exchange result).
- PASS -- No console errors after the change.

## Risks/Notes
- **Node 11 (Intent Classification) still has its own independent manual form** with hardcoded
  demo values (`sig_console_demo_01`), separate from Nodes 05-10 and not touched by this task --
  it's a downstream classification step, not a demand-signal source, and wasn't part of what the
  user raised. Flagged to the user as a related, not-yet-addressed follow-on; out of scope here
  unless they ask for it.
- Real campaigns now depend entirely on live-fetch succeeding for Phase 2 to produce any data at
  all -- for nodes without working credentials/access (Node 05's documented Search 403, Node 09's
  parked Reddit credential setup), this means those specific nodes simply cannot produce real data
  right now, by design (fail-closed), not a bug to work around with a fallback.

## Completion Status
Complete for the requested scope (Nodes 05-10). Live-verified both that fabrication is closed and
that the real automated path remains fully functional.
