# EP050 Node 08 competitor intelligence regression procedure

## Use when
Modifying `epics/ep_050_distribution_engine/implementation/node_08/competitor_intelligence.py`, or before promoting Node 08 past its current gate, or before any Node 09+ work that depends on Node 08's competitor-intelligence contract.

## Preconditions
- Changes stay fixture-only: no network call, no live competitor research/browsing/scraping/APIs/credentials, no production datastore, no real customer identifiers.
- The suite must construct real `TargetRegistry` (Node 01), `ProductIntelligenceRegistry` (Node 02), `AudienceSegmentRegistry` (Node 03), `ConversionDefinitionRegistry` (Node 04), `DemandSignalRegistry` (Node 05), `QuestionRegistry` (Node 06), and `SocialVideoSignalRegistry` (Node 07) instances and populate the synthetic target through all seven — do not mock any of the seven upstream dependency checks away.
- Do not weaken the `source_type` enum, `relevance_score` range check, `competition_indicator` enum, or the prohibited-PII screen to make a test pass.

## Steps and pass criteria
1. Run `pytest epics/ep_050_distribution_engine/implementation/node_08/test_competitor_intelligence.py -v --basetemp=<a writable scratch dir>`.
2. All tests must pass, covering:
   - Positive registration and optional-`metadata` default.
   - Node01-07->08 contract/integration: a target missing from any one of the seven real upstream registries (including Node 07's own social/video signal) must be rejected; a target present in all seven must be accepted.
   - Required-field failures for all 13 required fields.
   - Invalid enum/type: `source_type` outside the offline MVP boundary, invalid `competition_indicator`, out-of-range/non-numeric `relevance_score`, invalid `observed_at` format, wrong-typed `geography`.
   - Prohibited-PII rejection: email and phone patterns in `competitor_name` and `query` at minimum.
   - Duplicate idempotency and conflicting-duplicate rejection (fail-closed, original unmodified).
   - Persistence round trip via a fresh registry instance.
   - No-network assertion via a monkeypatched `socket.socket`.
   - Full-lifecycle regression in one pass.
3. Save the full `pytest -v` output as `pytest_output.txt` under a new timestamped folder in `epics/ep_050_distribution_engine/evidence/node_08/<YYYYMMDD_HHMMSS>/`, plus a short `README.md` manifest.
4. Update the Node 08 lifecycle record's Implementation Log, Evidence, and Validation sections, and re-verify byte-equality between the canonical `workstream/` copy, the `epics/ep_050_distribution_engine/lifecycle/claude/` copy, and the Obsidian mirror.

## Fail conditions
- Any test fails, errors, or is skipped.
- Any of the seven Node01-07->08 dependency checks are mocked/bypassed instead of using real registries.
- `source_type` accepts a live-collection value, `relevance_score` accepts an out-of-range/non-numeric value, `competition_indicator` accepts an unrecognized value, or a PII-pattern test is removed/weakened without a documented reason.
- A required-field or type-validation case raises anything other than `ValidationError`/`UnknownTargetError`/`ConflictError`.
- Any network socket is opened, or any live-research/browsing code path is added.
- Evidence, lifecycle, or mirror updates are skipped after a passing run.

## Boundary
A passing regression run proves Node 08's offline competitor-intelligence contract only. It does not authorize live competitor research, browsing, scraping, API access, production datastore access, or Node 09+ implementation — those remain separately gated per the EP050 master specification and the current combined-MVP approval state.
