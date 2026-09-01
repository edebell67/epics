# EP050 — Real Consumer Intake Form (Node 27 Public Entry Point)

Source: Direct user chat instruction (2026-08-18): "if there is a gap FIX IT" -- in response to
Node 27 being described as producing a real lead record but only via console-driven fixture
submissions, not a real consumer.

Task Type: standard

Task Attributes:
- workflow_task: true
- workflow_name: "ep050_distribution_engine_delivery_20260816"
- workflow_stage: complete
- depends_on:
  - "Node 26 route recommendation (met, run_20260818_102850_a3e4d29f has a real route)"

Task Summary: Built and verified a real, working consumer-facing intake form. `GET
/intake?run=<id>` serves a real HTML page personalized to the run's registered target
(service/locality); its form submits via a real browser interaction to `POST
/api/runs/{id}/node27/public_intake`, which splits the submission -- raw PII (name/email/phone)
and job-request content stored separately in `data/runs/{id}/public_intake_pii.json`, never
merged into Node 27's contract -- and calls the real `build_structured_lead_record()` against the
run's most recent Node 26 route. Verified with an actual browser form fill-and-submit (typed
fields, real click), not a simulated API call: produced real lead `slc_d97e2c83a151f7b2...`,
confirmed server-side to contain zero PII while the PII file holds the real submitted values.

Context:
- `epics/ep_050_distribution_engine/implementation/operational_console_claude/server.py` --
  `render_intake_form()`, `handle_node27_public_intake()`, `public_pii_path()`, `_send_html()`,
  new `GET /intake` and `POST .../node27/public_intake` routes.

Destination Folder: `epics/ep_050_distribution_engine/implementation/operational_console_claude/`;
this lifecycle record under `workstream/300_complete/`.

Dependency: A Node 26 route must already exist for the target run (met for the live run).

## Plan
- [x] 1. Design the PII split before writing any code: Node 27's real contract
      (`_ALLOWED = {session_id, source, consent}`, active PII rejection) means raw consumer data
      can never reach it -- it needs a separate, real store next to but never merged into the
      lead record.
  - [x] Test: N/A (design).
  - [x] Evidence: This Implementation Log.
- [x] 2. Implemented the real HTML form + backend handler + separate PII storage.
  - [x] Test: `python -c "import server"` -- clean import.
  - [x] Evidence: `server.py`.
- [x] 3. Verified with a genuine browser interaction, not a simulated fetch call: typed real
      values into each field, clicked the real submit button, confirmed the real success message
      with a real lead_id rendered on the page.
  - [x] Test: Live browser fill-and-submit against the real running server.
  - [x] Evidence: This Implementation Log.
- [x] 4. Verified server-side storage directly: the stored lead record contains zero PII; the
      separate PII file contains the real submitted name/email/phone/details.
  - [x] Test: Direct file read of both `run.json`'s `leads` array and `public_intake_pii.json`.
  - [x] Evidence: This Implementation Log.
- [x] 5. Ran the full regression.
  - [x] Test: `pytest operational_console_claude/test_console_server.py node_27 -q` -- 65/65.
  - [x] Evidence: This Implementation Log.

## Evidence
Objective-Delivery-Coverage: 100% for the intake-side gap (a real consumer can now submit a real
form and produce a real Node 27 lead). Publishing this page to a real public domain/hosting is a
separate, larger infrastructure step, not done here -- it currently only exists at
`http://127.0.0.1:8060/intake`, local-only.
Auto-Acceptance: false (new public-facing entry point; verification requested in chat)
- Evidence-Type: manual_verification
  - Artifact: Real browser form submission producing `lead_id: slc_d97e2c83a151f7b2...`; direct
    file inspection confirming the lead record is PII-free and the separate PII file holds the
    real submitted data.
  - Objective-Proved: The form works end-to-end through genuine browser interaction, and the
    PII/lead separation holds under a real submission, not just in test fixtures.
  - Status: captured
- Evidence-Type: test_output
  - Artifact: `pytest operational_console_claude/test_console_server.py node_27 -q` -- 65/65.
  - Objective-Proved: Zero regressions from the new routes.
  - Status: captured

## Implementation Log
- 2026-08-18T13:55+01:00 -- Ran Phase 5 against the live run to get a real Node 26 route to build
  against (`sdr_cef6ec6d...`).
- 2026-08-18T14:00+01:00 -- Implemented `render_intake_form()`, `handle_node27_public_intake()`,
  `public_pii_path()`, `_send_html()`, wired `GET /intake` and `POST
  /api/runs/{id}/node27/public_intake`.
- 2026-08-18T14:05+01:00 -- Restarted the server, loaded `/intake?run=run_20260818_102850_a3e4d29f`
  in the browser, filled every field with realistic values, clicked the real submit button.
- 2026-08-18T14:09+01:00 -- Page showed a real success message with `lead_id:
  slc_d97e2c83a151f7b2cf4c8c0c3079188457ae8a6a442f592ae56a4f5b24e116e7`. Verified server-side:
  the lead record in `run.json` has zero PII fields; `public_intake_pii.json` holds the real
  name/email/phone/details, session_id matching between the two.
- 2026-08-18T14:12+01:00 -- Ran full regression: 65/65 passing.
- 2026-08-18T14:14+01:00 -- Filed this lifecycle record.

## Changes Made
- Edited `epics/ep_050_distribution_engine/implementation/operational_console_claude/server.py`
  (v1.7.0 -> v1.8.0): `render_intake_form()`, `handle_node27_public_intake()`,
  `public_pii_path()`, `_send_html()`, `GET /intake`, `POST .../node27/public_intake`.

## Validation
- PASS -- Real browser submission produced a real, correct lead record.
- PASS -- PII/lead separation holds: zero PII in the lead record, real PII in the separate file.
- PASS -- `pytest operational_console_claude/test_console_server.py node_27 -q` -- 65/65.

## Risks/Notes
- **Local only.** This closes the "no real backend" half of the gap -- a real form now produces
  a real lead. It does not put this page on the public internet; it's reachable only at
  `http://127.0.0.1:8060/intake?run=<id>` on this machine. Real public hosting/domain is a
  separate decision with its own real-world consequences, not taken here.
- **Ties to the most recent route in the run**, not a specific one selected by the visitor --
  fine for a single-target run like this one; would need real routing logic if a run ever has
  multiple concurrent routes.

## Completion Status
Complete for the intake-backend gap. Verification requested in chat immediately after this task's
summary.
