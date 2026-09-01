# EP050 Node 03 audience definition regression procedure

## Use when
Modifying `epics/ep_050_distribution_engine/implementation/node_03/audience_definition.py`, or before promoting Node 03 past its current gate, or before any Node 04+ work that depends on Node 03's audience-segment contract.

## Preconditions
- Changes stay fixture-only: no network call, no production datastore, no real customer identifiers.
- The suite must construct real `TargetRegistry` (Node 01) and `ProductIntelligenceRegistry` (Node 02) instances and register/describe the synthetic target through them — do not mock either upstream dependency check away.
- Do not weaken the fail-closed PII screen (`EMAIL_PATTERN`, `PHONE_PATTERN`) to make a test pass; if a false-positive is found on legitimate fixture text, adjust the fixture text, not the pattern strictness, unless the pattern is genuinely wrong.

## Steps and pass criteria
1. Run `pytest epics/ep_050_distribution_engine/implementation/node_03/test_audience_definition.py -v --basetemp=<a writable scratch dir>`.
2. All tests must pass, covering:
   - Positive registration, deterministic `segment_id` derivation, optional-field defaults.
   - Node01+Node02->03 contract/integration: a target unknown to Node 01 is rejected; a target known to Node 01 but without a Node 02 record is rejected; a target present in both real registries is accepted.
   - Required-field failures for all 6 required fields, plus a geography-subfield case.
   - Invalid enum/type: urgency enum, wrong-typed/empty `needs`/`pains`, wrong-typed geography.
   - **Prohibited-PII rejection**: an email address and a phone-number-like sequence must each be rejected in every free-text field exercised (`needs`, `pains`, `segment_name`, `exclusions` at minimum).
   - Duplicate idempotency and conflicting-duplicate rejection (fail-closed, original unmodified).
   - Persistence round trip via a fresh registry instance.
   - No-network assertion via a monkeypatched `socket.socket`.
   - Full-lifecycle regression in one pass.
3. Save the full `pytest -v` output as `pytest_output.txt` under a new timestamped folder in `epics/ep_050_distribution_engine/evidence/node_03/<YYYYMMDD_HHMMSS>/`, plus a short `README.md` manifest.
4. Update the Node 03 lifecycle record's Implementation Log, Evidence, and Validation sections, and re-verify byte-equality between the canonical `workstream/` copy, the `epics/ep_050_distribution_engine/lifecycle/claude/` copy, and the Obsidian mirror.

## Fail conditions
- Any test fails, errors, or is skipped.
- The Node01+Node02->03 dependency checks are mocked/bypassed instead of using real registries.
- Any PII-pattern test is removed or its pattern is weakened without a documented reason.
- A required-field or type-validation case raises anything other than `ValidationError`/`UnknownTargetError`/`ConflictError`.
- Any network socket is opened during registration.
- Evidence, lifecycle, or mirror updates are skipped after a passing run.

## Boundary
A passing regression run proves Node 03's offline audience-definition contract only. It does not authorize live network collection, production datastore access, real customer PII handling, or Node 04+ implementation — those remain separately gated per the EP050 master specification and the current combined-MVP approval state.
