# EP050 Node 10 trend detection regression procedure

## Use when
Modifying `epics/ep_050_distribution_engine/implementation/node_10/trend_detection.py`, or before promoting Node 10 past its current gate, or before any Node 11+ work that depends on Node 10's trend-detection contract.

## Preconditions
- Changes stay fixture-only: no network call, no live monitoring/browsing/scraping/APIs/credentials, no production datastore, no real customer identifiers.
- The suite must construct real `TargetRegistry` (Node 01), `ProductIntelligenceRegistry` (Node 02), `AudienceSegmentRegistry` (Node 03), `ConversionDefinitionRegistry` (Node 04), `DemandSignalRegistry` (Node 05), `QuestionRegistry` (Node 06), `SocialVideoSignalRegistry` (Node 07), `CompetitorSignalRegistry` (Node 08), and `CommunitySignalRegistry` (Node 09) instances and populate the synthetic target through all nine — do not mock any of the nine upstream dependency checks away.
- Do not weaken the `source_type` enum, the `window` monotonicity check, the minimum sample-count gate, or the prohibited-PII screen to make a test pass.
- `velocity`/`direction`/`spike_flag`/`confidence` are derived deterministically by the module from `baseline_value`/`current_value`/`baseline_sample_count`/`current_sample_count` — never accept them as caller-supplied input, and never change the classification thresholds (`FLAT_VELOCITY_DEADBAND`, `SPIKE_VELOCITY_THRESHOLD`, `MIN_SAMPLE_COUNT`, `CONFIDENT_SAMPLE_COUNT`) without a version-history entry and a full test rerun.

## Steps and pass criteria
1. Run `pytest epics/ep_050_distribution_engine/implementation/node_10/test_trend_detection.py -v --basetemp=<a writable scratch dir>`.
2. All tests must pass, covering:
   - Positive registration and optional-`metadata` default.
   - Derived trend computation: an upward spike, a downward trend, a flat trend within the deadband, confidence scaling with the minimum of the two sample counts, and rejection of a zero baseline value.
   - Node01-09->10 contract/integration: a target missing from any one of the nine real upstream registries (including Node 09's own community signal) must be rejected; a target present in all nine must be accepted.
   - Required-field failures for all 12 required fields.
   - Invalid enum/type: `source_type` outside the offline MVP boundary, wrong-typed `geography`, non-monotonic window, overlapping baseline/current window, a window missing a key, negative `baseline_value`, non-numeric `current_value`, a sample count below the statistical minimum, a non-integer sample count.
   - Prohibited-PII rejection: email and phone patterns in `topic` and `metric_name` at minimum.
   - Duplicate idempotency and conflicting-duplicate rejection (fail-closed, original unmodified).
   - Persistence round trip via a fresh registry instance.
   - No-network assertion via a monkeypatched `socket.socket`.
   - Full-lifecycle regression in one pass.
3. Save the full `pytest -v` output as `pytest_output.txt` under a new timestamped folder in `epics/ep_050_distribution_engine/evidence/node_10/<YYYYMMDD_HHMMSS>/`, plus a short `README.md` manifest.
4. Update the Node 10 lifecycle record's Implementation Log, Evidence, and Validation sections, and re-verify byte-equality between the canonical `workstream/` copy, the `epics/ep_050_distribution_engine/lifecycle/claude/` copy, and the Obsidian mirror.

## Fail conditions
- Any test fails, errors, or is skipped.
- Any of the nine Node01-09->10 dependency checks are mocked/bypassed instead of using real registries.
- `source_type` accepts a live-collection value, `window` accepts a non-monotonic or overlapping period, a sample count below `MIN_SAMPLE_COUNT` is accepted, or a PII-pattern test is removed/weakened without a documented reason.
- `velocity`/`direction`/`spike_flag`/`confidence` become caller-suppliable inputs instead of derived outputs, or their thresholds change without a version-history entry.
- A required-field or type-validation case raises anything other than `ValidationError`/`UnknownTargetError`/`ConflictError`.
- Any network socket is opened, or any live-monitoring/browsing code path is added.
- Evidence, lifecycle, or mirror updates are skipped after a passing run.

## Boundary
A passing regression run proves Node 10's offline trend-detection contract only. It does not authorize live monitoring, browsing, scraping, API access, production datastore access, or Node 11+ implementation — those remain separately gated per the EP050 master specification and the current combined-MVP approval state.
