# EP050 Node 06 question discovery regression procedure

## Use when
Modifying `epics/ep_050_distribution_engine/implementation/node_06/question_discovery.py`, or before promoting Node 06 past its current gate, or before any Node 07+ work that depends on Node 06's explicit-question contract.

## Preconditions
- Changes stay fixture-only: no network call, no live sources, no production datastore, no real customer identifiers.
- The suite must construct real `TargetRegistry` (Node 01), `ProductIntelligenceRegistry` (Node 02), `AudienceSegmentRegistry` (Node 03), `ConversionDefinitionRegistry` (Node 04), and `DemandSignalRegistry` (Node 05) instances and populate the synthetic target through all five — do not mock any of the five upstream dependency checks away.
- Do not weaken the `source_type` enum or the prohibited-PII screen to make a test pass.

## Steps and pass criteria
1. Run `pytest epics/ep_050_distribution_engine/implementation/node_06/test_question_discovery.py -v --basetemp=<a writable scratch dir>`.
2. All tests must pass, covering:
   - Positive registration and optional-`metadata` default.
   - Node01-05->06 contract/integration: a target missing from any one of the five real upstream registries (including Node 05's own demand signal) must be rejected; a target present in all five must be accepted.
   - Required-field failures for all 10 required fields.
   - Invalid enum/type: `source_type` outside the offline MVP boundary, invalid `observed_at` format, empty `intent_cues`, wrong-typed `geography`.
   - Prohibited-PII rejection: email and phone patterns in `question_text` and `pain_point` at minimum.
   - Duplicate idempotency and conflicting-duplicate rejection (fail-closed, original unmodified).
   - Persistence round trip via a fresh registry instance.
   - No-network assertion via a monkeypatched `socket.socket`.
   - Full-lifecycle regression in one pass.
3. Save the full `pytest -v` output as `pytest_output.txt` under a new timestamped folder in `epics/ep_050_distribution_engine/evidence/node_06/<YYYYMMDD_HHMMSS>/`, plus a short `README.md` manifest.
4. Update the Node 06 lifecycle record's Implementation Log, Evidence, and Validation sections, and re-verify byte-equality between the canonical `workstream/` copy, the `epics/ep_050_distribution_engine/lifecycle/claude/` copy, and the Obsidian mirror.

## Fail conditions
- Any test fails, errors, or is skipped.
- Any of the five Node01-05->06 dependency checks are mocked/bypassed instead of using real registries.
- `source_type` accepts a live-collection value, or a PII-pattern test is removed/weakened without a documented reason.
- A required-field or type-validation case raises anything other than `ValidationError`/`UnknownTargetError`/`ConflictError`.
- Any network socket is opened, or any live-source code path is added.
- Evidence, lifecycle, or mirror updates are skipped after a passing run.

## Boundary
A passing regression run proves Node 06's offline explicit-question contract only. It does not authorize live forum/community collection, production datastore access, or Node 07+ implementation — those remain separately gated per the EP050 master specification and the current combined-MVP approval state.
