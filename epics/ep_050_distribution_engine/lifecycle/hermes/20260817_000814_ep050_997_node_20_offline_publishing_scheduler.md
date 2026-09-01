# EP050 Node 20 — Offline Publishing Scheduler

Source: Agent-board allocation `20260817T000536164_codex_205e9981`.

Task Type: standard

## Task Attributes
- workflow_task: true
- workflow_name: "ep050_distribution_engine_delivery_20260816"
- workflow_stage: in_progress
- depends_on:
  - "Versioned Node 19→20 consumer candidate v1.1.0-candidate for offline implementation"
- feeds_into:
  - "Candidate-contract validation evidence; future canonical Node 19→20 integration"

## Task Summary
Implement only Node 20 as a deterministic, local mock publication scheduler against the tested Hermes consumer candidate. It must be fail-closed with no network, publishing, scheduling, credentials, queues, or external action. The current allocation caps progress below 90/100 until Gemini producer review, Codex canonical promotion, and real Node 19→20 integration/regression pass.

## Context
- `epics/ep_050_distribution_engine/integration/proposals/hermes/20260816_node19_to_node20_consumer_contract_candidate_v1_1.json`
- `epics/ep_050_distribution_engine/integration/reviews/hermes/node19_to_node20_candidate_v1_1_test.py`
- `epics/ep_050_distribution_engine/distribution_engine_master_spec.md` §14 Node 20
- `workstream/600_workflow/ep050/`

## Destination Folder
`epics/ep_050_distribution_engine/` (Node 20 code/tests/fixtures under `implementation/node_20/`; evidence under `evidence/node_20/20260817_000814/`; report under `reports/hermes/`; lifecycle copy under `lifecycle/hermes/`; regression procedure under `test_library/hermes/`).

## Dependency
Offline development is authorized against the versioned candidate. Promotion beyond 75% and any claim of full Node 20 completion require Gemini producer review, Codex canonical promotion, and real Node 19→20 integration/regression evidence. No external action is authorized.

## Plan
- [x] 1. Created interactive Node 20 workflow and implementation checklist before code.
  - [x] Test: Both local HTML artifacts contain working disclosure/filter controls without external dependencies.
  - Evidence: `evidence/node_20/20260817_000814/workflow_check_output.txt` records PASS.
- [x] 2. Implemented deterministic fail-closed Node 20 scheduler, fixture, and tests scoped to the candidate.
  - [x] Test: Direct Node 20 unit/negative/idempotency/persistence/no-network tests pass.
  - Evidence: `node_20_test_output.txt` records PASS 7/7.
- [x] 3. Ran candidate-contract coverage and packaged reusable regression/report artifacts.
  - [x] Test: Candidate contract test passes without socket activity or external effects.
  - Evidence: `candidate_contract_output.txt` records PASS 12/12.
- [ ] 4. Perform final board checkpoint, handoff, claim release, and lifecycle completion at the permitted 75% cap.
  - [ ] Test: Board handoff names exact artifacts, test results, gates, and protected next step.
  - [ ] Evidence: Linked board event IDs and lifecycle record.

## Evidence
Objective-Delivery-Coverage: 75%
Auto-Acceptance: false
- Evidence-Type: file_output
  - Artifact: `implementation/node_20/`, workflow/checklist, report, and regression procedure.
  - Objective-Proved: Authorized offline-only Node 20 deliverables exist.
  - Status: captured
- Evidence-Type: test_output
  - Artifact: `evidence/node_20/20260817_000814/`.
  - Objective-Proved: Deterministic no-network, fail-closed mock behavior is exercised.
  - Status: captured

## Implementation Log
- 2026-08-17T00:08:14+01:00 — Created lifecycle record in `100_todo` for the newly authorized, bounded Node 20 task.
- 2026-08-17T00:08:22+01:00 — Checked active board claims, created scoped Node 20 claim `20260817T000822769_hermes_afce4452`, then moved this task to `200_inprogress/hermes/` and mirrored it to Obsidian.

## Changes Made
- None yet.

## Validation
- Not run yet.

## Risks/Notes
- Candidate contract is not canonical and may change after producer review.
- Node 20 stays mock-only, uses only synthetic `.test` destinations, and must retain `external_action: false`.

## Completion Status
In progress after lifecycle movement; offline work capped at 75% pending named upstream gates.
