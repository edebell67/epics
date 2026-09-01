# EP050 Node 05 search demand discovery regression procedure

## Use when
Modifying `epics/ep_050_distribution_engine/implementation/node_05/search_demand_discovery.py`, or before promoting Node 05 past its current gate, or before any Node 06+ work that depends on Node 05's demand-signal contract, or if Gemini's Node 11 module changes.

## Preconditions
- Changes stay fixture-only: no network call, no live scraping, no production datastore, no real customer identifiers.
- The suite must construct real `TargetRegistry` (Node 01), `ProductIntelligenceRegistry` (Node 02), `AudienceSegmentRegistry` (Node 03), and `ConversionDefinitionRegistry` (Node 04) instances and populate the synthetic target through all four — do not mock any of the four upstream dependency checks away.
- The suite must import Gemini's real `intent_classification.py` (Node 11) read-only and feed a real produced signal into it — do not mock this cross-owner compatibility check away; if it starts failing, that is a genuine contract-drift signal requiring board coordination with Gemini, not a test change.
- Do not weaken the `source_type` enum (`manual_curation`/`synthetic_fixture` only) or the prohibited-PII screen to make a test pass.

## Steps and pass criteria
1. Run `pytest epics/ep_050_distribution_engine/implementation/node_05/test_search_demand_discovery.py -v --basetemp=<a writable scratch dir>`.
2. All tests must pass, covering:
   - Positive registration and optional-`metadata` default.
   - Node01+02+03+04->05 contract/integration: a target missing from any one of the four real upstream registries must be rejected; a target present in all four must be accepted.
   - **Cross-owner contract compatibility**: a Node-05-produced signal, converted via `to_contract_payload()`, must be accepted by Gemini's real `classify_demand_signal()` without modification.
   - Required-field failures for all 8 required fields.
   - Invalid enum/type: `source_type` outside the offline MVP boundary, invalid `observed_at` format, wrong-typed `geography`, incomplete `service_context`.
   - Prohibited-PII rejection: email and phone patterns in both `raw_query` and `topic`.
   - Duplicate idempotency and conflicting-duplicate rejection (fail-closed, original unmodified).
   - Persistence round trip via a fresh registry instance.
   - No-network assertion via a monkeypatched `socket.socket`.
   - Full-lifecycle regression, including a second real Node 11 compatibility check.
3. Save the full `pytest -v` output as `pytest_output.txt` under a new timestamped folder in `epics/ep_050_distribution_engine/evidence/node_05/<YYYYMMDD_HHMMSS>/`, plus a short `README.md` manifest.
4. Update the Node 05 lifecycle record's Implementation Log, Evidence, and Validation sections, and re-verify byte-equality between the canonical `workstream/` copy, the `epics/ep_050_distribution_engine/lifecycle/claude/` copy, and the Obsidian mirror.

## Fail conditions
- Any test fails, errors, or is skipped.
- Any of the four Node01/02/03/04->05 dependency checks are mocked/bypassed instead of using real registries.
- The Node 11 cross-owner compatibility test is mocked instead of importing Gemini's real module.
- `source_type` accepts a live-collection value, or a PII-pattern test is removed/weakened without a documented reason.
- A required-field or type-validation case raises anything other than `ValidationError`/`UnknownTargetError`/`ConflictError`.
- Any network socket is opened, or any live scraping code path is added.
- Evidence, lifecycle, or mirror updates are skipped after a passing run.

## Boundary
A passing regression run proves Node 05's offline demand-signal contract only. It does not authorize live search-API access, scraping, production datastore access, or Node 06+ implementation — those remain separately gated per the EP050 master specification and the current combined-MVP approval state.
