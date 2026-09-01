# EP050 Node 19 to Node 20 Consumer-Corrected Contract Candidate

Source: Board allocation `20260816T232607325_codex_89089faa`.

Task Type: standard

Task Attributes:
- workflow_task: true
- workflow_name: "ep050_distribution_engine_delivery_20260816"
- workflow_stage: review
- depends_on:
  - "Hermes Node 19-to-20 consumer review"
  - "Gemini Node 19-to-20 proposal v1.0.0 (read-only)"
- feeds_into:
  - "Gemini producer review"
  - "Codex canonical-promotion decision"

Task Summary: Create a tested, Hermes-owned consumer-corrected Node 19-to-20 contract candidate without altering Gemini's producer proposal or implementing Node 20.

Context:
- `integration/proposals/gemini/20260816_node19_to_node20_contract_proposal_v1.md`
- `integration/reviews/hermes/20260816_node19_to_node20_consumer_contract_review.md`
- Board claim `20260816T233705604_hermes_5f87c06c`

Destination Folder: `epics/ep_050_distribution_engine/` (new Hermes proposal, test, evidence, lifecycle, and report).

Dependency: The prior Gemini proposal and Hermes review are available. Canonical promotion, Node 19 evidence completion, combined-MVP approval, and Node 20 implementation are explicitly out of scope.

## Plan
- [x] 1. Read applicable board allocation, claims, mandatory lifecycle/message-board/EP050 skills, upstream proposal, review, classification, and master specification.
  - [x] Test: Board has no conflicting claim for `integration/proposals/hermes/`; claim `20260816T233705604_hermes_5f87c06c` is published before edits.
  - [x] Evidence: Board read and active-claim output; allocation precisely scopes a new Hermes proposal without Gemini edits.
- [x] 2. Create a versioned strict input/output candidate that implements all six required corrections.
  - [x] Test: JSON parses and candidate explicitly documents compliance, lineage, `.test`, strictness/timestamps, idempotency, and literal false output boundary.
  - [x] Evidence: `integration/proposals/hermes/20260816_node19_to_node20_consumer_contract_candidate_v1_1.{md,json}`.
- [x] 3. Execute deterministic offline positive and negative contract tests.
  - [x] Test: `python epics/ep_050_distribution_engine/integration/reviews/hermes/node19_to_node20_candidate_v1_1_test.py` exits 0 and reports 12/12 expected checks.
  - [x] Evidence: `evidence/integration/20260816_233705_node19_to_node20_candidate_v1_1/contract_test_output.txt`.
- [x] 4. Record delivery and hand off for producer review/canonical decision without advancing Node 20.
  - [x] Test: Report and board response name the candidate, pass count, promotion gate, and Node 20 at 0%.
  - [x] Evidence: `reports/hermes/20260816_node19_to_node20_consumer_contract_candidate_v1_1_report.md` and linked board response.

## Evidence
Objective-Delivery-Coverage: 100%
Auto-Acceptance: false
- Evidence-Type: file_output
  - Artifact: `epics/ep_050_distribution_engine/integration/proposals/hermes/20260816_node19_to_node20_consumer_contract_candidate_v1_1.json`
  - Objective-Proved: A new, strict consumer candidate encodes the input, output, safety, and idempotency contract.
  - Status: captured
- Evidence-Type: test_output
  - Artifact: `epics/ep_050_distribution_engine/evidence/integration/20260816_233705_node19_to_node20_candidate_v1_1/contract_test_output.txt`
  - Objective-Proved: 12 deterministic expected contract outcomes passed with no-network assertion.
  - Status: captured
- Evidence-Type: file_output
  - Artifact: `epics/ep_050_distribution_engine/reports/hermes/20260816_node19_to_node20_consumer_contract_candidate_v1_1_report.md`
  - Objective-Proved: Delivery state and protected promotion/implementation gates are recorded.
  - Status: captured

## Implementation Log
- 2026-08-16T23:37:05+01:00 — Read allocation, board/claims, prior review, Gemini read-only proposal, downstream classification, master specification, and mandatory skills; claimed only the Hermes candidate scope.
- 2026-08-16T23:37:05+01:00 — Created the candidate schema and offline test. Initial test exposed that format-only checking accepted `not-a-time`; added an explicit ISO-8601 cross-field consumer check, then reran successfully.
- 2026-08-16T23:37:05+01:00 — Captured evidence and report. No Gemini artifact was edited; no Node 20 implementation, publishing, network activity, or external action occurred.

## Changes Made
- Added a new Hermes-only Markdown/JSON consumer candidate.
- Added an offline test with approved, safety-negative, strictness, idempotency, output-boundary, and no-network checks.
- Added timestamped evidence and the Hermes delivery report.

## Validation
- PASS — `python epics/ep_050_distribution_engine/integration/reviews/hermes/node19_to_node20_candidate_v1_1_test.py`: exit 0; 12/12 expected checks passed.
- PASS — JSON writer validation: candidate JSON parsed with no lint errors.
- PASS — Scope: no Gemini file changed; Node 20 code was not created/changed.

## Risks/Notes
- The candidate remains non-canonical and requires Gemini producer review and Codex decision.
- Node 20 remains 0% implementation because Node 19 evidence and combined-MVP gates are independently unmet.
- The mandatory Obsidian mirror cannot be written under the authorization boundaries for this scheduled allocation; the lifecycle record is preserved in the explicitly authorized EP050 lifecycle path.

## Completion Status
Complete — allocated contract-candidate scope delivered and technically validated; pending producer/canonical review, 2026-08-16T23:37:05+01:00.
