# EP050 Node 20 — Current-Code Regression Reconciliation

Source: Codex change-required decision `20260817T062636421_codex_81e01461`.

Task Type: standard

## Task Attributes
- workflow_task: true
- workflow_name: `ep050_distribution_engine_delivery_20260816`
- workflow_stage: review
- depends_on:
  - Canonical Node 19→20 contract v1.1.0
  - Node 19 accepted producer output
- feeds_into:
  - Codex acceptance decision for Node 20

## Task Summary
Consolidate current recreated Node 20 code coverage, retain evidence of the absent legacy source-directory anomaly, and reconcile evidence/status at 90% without external effects.

## Destination Folder
`epics/ep_050_distribution_engine/` — code in `implementation/node_20/`, evidence in `evidence/node_20/20260817_063639/`, report in `reports/hermes/`, and regression procedure in `test_library/hermes/`.

## Dependency
Canonical Node 19→20 contract v1.1.0 and accepted Node 19 producer are available. 100% requires Codex acceptance.

## Plan
- [x] 1. Check board claims and re-claim exact reconciliation scope.
  - [x] Test: Active claims contain no overlapping Node 20 owner; claim `20260817T063526589_hermes_a47842ca` is recorded.
  - Evidence: Board claim event.
- [x] 2. Reconcile current Node 20 source with legacy evidence without deleting or rewriting history.
  - [x] Test: Existing legacy evidence and lifecycle paths remain referenced; new evidence directory is additive.
  - Evidence: `evidence/node_20/20260817_063639/README.md`.
- [x] 3. Execute consolidated current-code regression.
  - [x] Test: Compile succeeds and aggregate behavioral coverage is 22/22.
  - Evidence: `evidence/node_20/20260817_063639/consolidated_current_code_regression_output.txt`.
- [x] 4. Update report, reusable procedure, and reviewable workflow/checklist to 90% pending acceptance.
  - [x] Test: Artifact statuses name exact test result and acceptance gate.
  - Evidence: report/procedure/workflow/checklist paths recorded below.
- [x] 5. Request Codex acceptance, release claim, and close only after acceptance.
  - [x] Test: Linked board acceptance event records 100% or a specific remaining blocker.
  - Evidence: Codex acceptance `20260817T064638149_codex_1e6c89bd` records 100%.

## Evidence
Objective-Delivery-Coverage: 100%
Auto-Acceptance: false
- Evidence-Type: test_output
  - Artifact: `epics/ep_050_distribution_engine/evidence/node_20/20260817_063639/consolidated_current_code_regression_output.txt`
  - Objective-Proved: Current code is compiled and the required direct, negative, idempotency/persistence, conflict, no-network, and real Node 19 integration coverage passes.
  - Status: captured
- Evidence-Type: file_output
  - Artifact: `epics/ep_050_distribution_engine/reports/hermes/20260817_node_20_real_node_19_integration_report.md`
  - Objective-Proved: Historical anomaly and protected acceptance gate are explicitly reconciled.
  - Status: captured

## Implementation Log
- 2026-08-17T06:35:26+01:00 — Re-claimed exact Node 20 reconciliation scope after board/claim review.
- 2026-08-17T06:36:39+01:00 — Added current-code negative/conflict coverage and ran the consolidated suite.
- 2026-08-17T06:36:39+01:00 — Captured additive evidence; retained all legacy artifacts unchanged.
- 2026-08-17T06:46:38+01:00 — Codex accepted Node 20 at 100%; claim had already been released and Node 21 allocation activated.

## Changes Made
- `implementation/node_20/publishing_scheduler.py`: added mandatory in-file version history only; no runtime behavior change.
- `implementation/node_20/test_publishing_scheduler.py`: added six fail-closed current-code tests and in-file version history.
- Updated Node 20 report and reusable regression procedure; created this reconciliation lifecycle record and timestamped evidence.

## Validation
- `python -m py_compile ...publishing_scheduler.py ...test_publishing_scheduler.py` — PASS.
- `python .../node_20/test_publishing_scheduler.py` — PASS 10/10, socket prohibited.
- `python .../node19_to_node20_candidate_v1_1_test.py` — PASS 12/12, socket prohibited.
- Aggregate — PASS 22/22 behavioral checks plus compile.

## Risks/Notes
- The old workstream lifecycle record is intentionally not edited: the scheduled EP050 authorization permits edits within the EP050 epic root and EP050 workflow root only.
- Node 20 remains an offline mock plan producer with `external_action: false`; Codex accepted the evidence at 100%.

## Completion Status
Complete at 100% as of 2026-08-17T06:46:38+01:00; accepted by Codex event `20260817T064638149_codex_1e6c89bd`.
