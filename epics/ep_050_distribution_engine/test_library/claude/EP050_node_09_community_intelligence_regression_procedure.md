# EP050 Node 09 community intelligence regression procedure

## Use when
Modifying `epics/ep_050_distribution_engine/implementation/node_09/community_intelligence.py`, or before promoting Node 09 past its current gate, or before any Node 10+ work that depends on Node 09's community-intelligence contract.

## Preconditions
- Changes stay fixture-only: no network call, no live community/forum/Reddit access, browsing, scraping, APIs, credentials, or outreach; no production datastore; no real customer identifiers.
- The suite must construct real `TargetRegistry` (Node 01), `ProductIntelligenceRegistry` (Node 02), `AudienceSegmentRegistry` (Node 03), `ConversionDefinitionRegistry` (Node 04), `DemandSignalRegistry` (Node 05), `QuestionRegistry` (Node 06), `SocialVideoSignalRegistry` (Node 07), and `CompetitorSignalRegistry` (Node 08) instances and populate the synthetic target through all eight — do not mock any of the eight upstream dependency checks away.
- Do not weaken the `source_type` enum, the `observed_metrics` non-negative-numeric check, or the prohibited-PII screen to make a test pass.

## Steps and pass criteria
1. Run `pytest epics/ep_050_distribution_engine/implementation/node_09/test_community_intelligence.py -v --basetemp=<a writable scratch dir>`.
2. All tests must pass, covering:
   - Positive registration and optional-`metadata` default.
   - Node01-08->09 contract/integration: a target missing from any one of the eight real upstream registries (including Node 08's own competitor signal) must be rejected; a target present in all eight must be accepted.
   - Required-field failures for all 12 required fields.
   - Invalid enum/type: `source_type` outside the offline MVP boundary, wrong-typed `intent_cues`, negative/non-numeric/empty `observed_metrics`, invalid `observed_at` format, wrong-typed `geography`.
   - Prohibited-PII rejection: email and phone patterns in `question` and `pain_point` at minimum.
   - Duplicate idempotency and conflicting-duplicate rejection (fail-closed, original unmodified).
   - Persistence round trip via a fresh registry instance.
   - No-network assertion via a monkeypatched `socket.socket`.
   - Full-lifecycle regression in one pass.
3. Save the full `pytest -v` output as `pytest_output.txt` under a new timestamped folder in `epics/ep_050_distribution_engine/evidence/node_09/<YYYYMMDD_HHMMSS>/`, plus a short `README.md` manifest.
4. Update the Node 09 lifecycle record's Implementation Log, Evidence, and Validation sections, and re-verify byte-equality between the canonical `workstream/` copy, the `epics/ep_050_distribution_engine/lifecycle/claude/` copy, and the Obsidian mirror.

## Fail conditions
- Any test fails, errors, or is skipped.
- Any of the eight Node01-08->09 dependency checks are mocked/bypassed instead of using real registries.
- `source_type` accepts a live-collection value, `observed_metrics` accepts a negative/non-numeric/empty value, or a PII-pattern test is removed/weakened without a documented reason.
- A required-field or type-validation case raises anything other than `ValidationError`/`UnknownTargetError`/`ConflictError`.
- Any network socket is opened, or any live-community-access/browsing code path is added.
- Evidence, lifecycle, or mirror updates are skipped after a passing run.

## Boundary
A passing regression run proves Node 09's offline community-intelligence contract only. It does not authorize live community/forum access, posting, outreach, production datastore access, or Node 10+ implementation — those remain separately gated per the EP050 master specification and the current combined-MVP approval state.
