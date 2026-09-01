# EP050 Node 04 conversion definition regression procedure

## Use when
Modifying `epics/ep_050_distribution_engine/implementation/node_04/conversion_definition.py`, or before promoting Node 04 past its current gate, or before any Node 05+ work that depends on Node 04's conversion contract.

## Preconditions
- Changes stay fixture-only: no network call, no production datastore, no real customer identifiers.
- The suite must construct real `TargetRegistry` (Node 01), `ProductIntelligenceRegistry` (Node 02), and `AudienceSegmentRegistry` (Node 03) instances and populate the synthetic target through all three — do not mock any of the three upstream dependency checks away.
- Do not weaken the structural stage/transition validation (order gaps/duplicates, backward/self transitions, unknown stage references) to make a test pass.

## Steps and pass criteria
1. Run `pytest epics/ep_050_distribution_engine/implementation/node_04/test_conversion_definition.py -v --basetemp=<a writable scratch dir>`.
2. All tests must pass, covering:
   - Positive registration using the master spec's own worked funnel (`MASTER_SPEC_STAGES`: Visit through Revenue, 9 stages).
   - Node01+Node02+Node03->04 contract/integration: a target missing from any one of the three real upstream registries must be rejected; a target present in all three must be accepted.
   - Required-field failures for all 5 required fields.
   - Invalid stages: duplicate `stage_id`, duplicate `order`, order gap, non-positive `order`.
   - Invalid transitions: reference to an unknown stage, backward transition, self transition, duplicate transition pair, `success_stage_id` not among the declared stages.
   - Duplicate idempotency and conflicting-duplicate rejection (fail-closed, original unmodified).
   - Persistence round trip via a fresh registry instance.
   - No-network assertion via a monkeypatched `socket.socket`.
   - Full-lifecycle regression in one pass.
3. Save the full `pytest -v` output as `pytest_output.txt` under a new timestamped folder in `epics/ep_050_distribution_engine/evidence/node_04/<YYYYMMDD_HHMMSS>/`, plus a short `README.md` manifest.
4. Update the Node 04 lifecycle record's Implementation Log, Evidence, and Validation sections, and re-verify byte-equality between the canonical `workstream/` copy, the `epics/ep_050_distribution_engine/lifecycle/claude/` copy, and the Obsidian mirror.

## Fail conditions
- Any test fails, errors, or is skipped.
- Any of the three Node01/02/03->04 dependency checks are mocked/bypassed instead of using real registries.
- A structural validation case (stage order, transition direction, unknown references) is weakened rather than the test fixture corrected.
- A required-field or type-validation case raises anything other than `ValidationError`/`UnknownTargetError`/`ConflictError`.
- Any network socket is opened during registration.
- Evidence, lifecycle, or mirror updates are skipped after a passing run.

## Boundary
A passing regression run proves Node 04's offline conversion-definition contract only. It does not authorize live network collection, production datastore access, or Node 05+ implementation — those remain separately gated per the EP050 master specification and the current combined-MVP approval state.
