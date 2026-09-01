# EP050 Node 07 social/video discovery regression procedure

## Use when
Modifying `epics/ep_050_distribution_engine/implementation/node_07/social_video_discovery.py`, or before promoting Node 07 past its current gate, or before any Node 08+ work that depends on Node 07's social/video theme contract.

## Preconditions
- Changes stay fixture-only: no network call, no live browsing/scraping/APIs/credentials, no production datastore, no real customer identifiers.
- The suite must construct real `TargetRegistry` (Node 01), `ProductIntelligenceRegistry` (Node 02), `AudienceSegmentRegistry` (Node 03), `ConversionDefinitionRegistry` (Node 04), `DemandSignalRegistry` (Node 05), and `QuestionRegistry` (Node 06) instances and populate the synthetic target through all six — do not mock any of the six upstream dependency checks away.
- Do not weaken the `source_type` enum, the `observed_metrics` numeric/non-negative check, or the prohibited-PII screen to make a test pass.

## Steps and pass criteria
1. Run `pytest epics/ep_050_distribution_engine/implementation/node_07/test_social_video_discovery.py -v --basetemp=<a writable scratch dir>`.
2. All tests must pass, covering:
   - Positive registration and optional-`metadata` default.
   - Node01-06->07 contract/integration: a target missing from any one of the six real upstream registries (including Node 06's own question) must be rejected; a target present in all six must be accepted.
   - Required-field failures for all 12 required fields.
   - Invalid enum/type: `source_type` outside the offline MVP boundary, invalid `observed_at` format, empty/non-numeric/negative `observed_metrics`, wrong-typed `geography`.
   - Prohibited-PII rejection: email and phone patterns in `theme` and `topic` at minimum.
   - Duplicate idempotency and conflicting-duplicate rejection (fail-closed, original unmodified).
   - Persistence round trip via a fresh registry instance.
   - No-network assertion via a monkeypatched `socket.socket`.
   - Full-lifecycle regression in one pass.
3. Save the full `pytest -v` output as `pytest_output.txt` under a new timestamped folder in `epics/ep_050_distribution_engine/evidence/node_07/<YYYYMMDD_HHMMSS>/`, plus a short `README.md` manifest.
4. Update the Node 07 lifecycle record's Implementation Log, Evidence, and Validation sections, and re-verify byte-equality between the canonical `workstream/` copy, the `epics/ep_050_distribution_engine/lifecycle/claude/` copy, and the Obsidian mirror.

## Fail conditions
- Any test fails, errors, or is skipped.
- Any of the six Node01-06->07 dependency checks are mocked/bypassed instead of using real registries.
- `source_type` accepts a live-collection value, `observed_metrics` accepts a non-numeric/negative/empty value, or a PII-pattern test is removed/weakened without a documented reason.
- A required-field or type-validation case raises anything other than `ValidationError`/`UnknownTargetError`/`ConflictError`.
- Any network socket is opened, or any live-browsing/scraping code path is added.
- Evidence, lifecycle, or mirror updates are skipped after a passing run.

## Boundary
A passing regression run proves Node 07's offline social/video theme contract only. It does not authorize live platform browsing, scraping, API access, production datastore access, or Node 08+ implementation — those remain separately gated per the EP050 master specification and the current combined-MVP approval state.
