# EP050 — Node 17 De-Hardcoding: Ad Copy Follows the Campaign's Real Town and Service

Source: User ran the first replicated candidate through the full pipeline ("run for one candidate
(1st one)"), which surfaced ad copy advertising the wrong town. User instruction: "NO HARD CODING
please" + "yes!!" to fixing Node 17's geography derivation.

Task Type: standard

Task Attributes:
- workflow_task: true
- workflow_name: "ep050_distribution_engine_delivery_20260816"
- workflow_stage: complete
- depends_on:
  - "Node 05 provider migration to Firecrawl (met, same day) — a working live fetch is what allowed a replicated candidate to reach Node 17 for the first time"

Task Summary: `node_17/content_utility_factory.py` wrote the literal strings **"Blackheath"** and
**"SE3"** into every asset title, body and call-to-action, alongside boiler/gas-specific wording.
Correct for exactly one campaign. Since the engine's entire scaling model is **geographic
replication**, every replicated candidate rendered adverts naming the **wrong town**. Replaced all
hardcoded geography and service wording with derivation from real upstream records, and removed
fabricated business claims baked into the templates.

Context:
- `epics/ep_050_distribution_engine/implementation/node_17/content_utility_factory.py` (v1.0.0 → v1.1.0)
- `epics/ep_050_distribution_engine/implementation/node_17/test_content_utility_factory.py`
- `epics/ep_050_distribution_engine/implementation/operational_console_claude/server.py` (provenance fix)

Destination Folder: `epics/ep_050_distribution_engine/implementation/`; this lifecycle record under `workstream/300_complete/`.

Dependency: Node 05 Firecrawl migration (met, same day).

## Plan
- [x] 1. Confirm the wrong-town output on real data rather than reasoning about it.
  - [x] Test: Live Greenwich run rendered "Emergency Boiler Repair Blackheath … rapid arrival across
        SE3" while target/audience/cluster/shared_traits all carried Greenwich.
  - [x] Evidence: Implementation Log.
- [x] 2. Confirm it is hardcoding, not bad derivation.
  - [x] Test: grep found the literals at content_utility_factory.py:214/223/225/227/230/236.
  - [x] Evidence: Implementation Log.
- [x] 3. Establish what real context is already available before adding plumbing.
  - [x] Test: Node 11 classification carries both `geography` and `service_context`, and is already
        passed to `generate_asset_payload` as `intent_input`. No new plumbing needed.
  - [x] Evidence: Implementation Log.
- [x] 4. Derive locality/region/service; fail closed rather than default.
  - [x] Test: New `resolve_campaign_context()`; ValidationError when no service resolvable; place
        omitted entirely when geography unknown.
  - [x] Evidence: Implementation Log.
- [x] 5. Remove unevidenced business claims and the domain-specific safety fallback.
  - [x] Test: New test asserting the default CTA contains no "vetted"/"fixed-fee"/"same-day"/"24/7".
  - [x] Evidence: Implementation Log.
- [x] 6. Prove multi-vertical safety, not just multi-town.
  - [x] Test: New test — `option_trading_stocks` in Manchester renders with zero boiler/gas leakage.
  - [x] Evidence: Implementation Log.
- [x] 7. Fix the provenance mislabel found while preparing the run.
  - [x] Test: New test asserting the classification carries the signal's real `source_type`.
  - [x] Evidence: Implementation Log.
- [x] 8. Full regression + live re-verification on the real Greenwich run.
  - [x] Test: 656 passed; regenerated asset reads Greenwich throughout.
  - [x] Evidence: Implementation Log.

## Evidence
Objective-Delivery-Coverage: 100% for the requested scope (Node 17 geography/service derivation).
Auto-Acceptance: false (changes rendered output of every asset; verified live)
- Evidence-Type: manual_verification
  - Artifact: Real Greenwich candidate `run_20260818_201453_09dd8f99` regenerated after the fix —
    title `Boiler Repair | Greenwich, London`; body `Local boiler repair support in Greenwich,
    London.` followed by the real Node 16 fact; CTA `Enquire about Boiler Repair in Greenwich,
    London.` The non-video sibling factory picked up the corrected content
    (`verified_local_listing_with_emergency_hours`, headline `Boiler Repair | Greenwich, London`).
  - Objective-Proved: A replicated candidate now advertises its own town, on real pipeline data.
  - Status: captured
- Evidence-Type: test_output
  - Artifact: `pytest node_17/ node_18/ node_19/ -q` → 73 passed;
    `pytest . -q --ignore=operational_console` → 656 passed.
  - Objective-Proved: No regression; the wrong-town and cross-vertical cases are now pinned.
  - Status: captured

## Implementation Log
- 2026-08-19T12:30+01:00 — Ran the first replicated candidate (Greenwich) through the full pipeline
  at the user's request. 13 nodes completed. Inspected the output rather than reporting the
  `winner_detected` state at face value, and found the asset advertising Blackheath/SE3.
- 2026-08-19T12:33+01:00 — Confirmed via grep that these were string literals, not derivation.
  Confirmed the scope was wider than geography: service wording was hardcoded too.
- 2026-08-19T12:38+01:00 — Established the classification already carries geography and
  service_context, so no new plumbing was required.
- 2026-08-19T12:42+01:00 — Implemented `resolve_campaign_context()` and rewrote all three template
  branches, the default CTA and the safety-disclaimer fallback.
- 2026-08-19T12:45+01:00 — Three pre-existing tests failed because they called the factory with no
  context at all. That is the fail-closed guard behaving correctly, so updated them to pass a real
  classification (new `valid_classification` fixture) rather than weakening the guard.
- 2026-08-19T12:47+01:00 — One of my own new tests failed on "boiler" leaking into the trading
  vertical. That was my test's artefact — I had passed a boiler *fact* to a trading campaign — not
  a template leak. Fixed the test to supply a vertical-appropriate fact.
- 2026-08-19T12:49+01:00 — 656 passed; posted handoff-quality progress to the message board at the
  user's request so other models can pick this up.
- 2026-08-19T12:52+01:00 — Restarted the console, regenerated the Greenwich asset live, confirmed
  correct town and service throughout.

## Changes Made
- `content_utility_factory.py` v1.1.0: new `resolve_campaign_context()`, `_humanise_token()`,
  `_as_mapping()`; `generate_asset_payload()` accepts `geography`/`service_context` overrides; all
  three template branches, the default CTA and the safety fallback now derive from real data;
  `template_version` 1.0.0 → 1.1.0.
- `test_content_utility_factory.py`: +6 tests (wrong-town regression, cross-vertical leakage,
  fail-closed on unresolvable service, unknown-geography omission, unevidenced-claims check, plus
  the shared fixture); 3 existing tests updated to pass a real classification.
- `server.py`: `run_pipeline_headless` now carries the signal's real `source_type` into Node 11
  instead of hardcoding `synthetic_fixture`.

## Validation
- PASS — `pytest node_17/ node_18/ node_19/ -q` → 73 passed.
- PASS — `pytest . -q --ignore=operational_console` → 656 passed.
- PASS — Live: real Greenwich candidate renders Greenwich in title, body and CTA.

## Risks/Notes
- **Postcodes were removed, not corrected.** The old copy claimed "SE3"; Greenwich is SE10. No node
  registers real postcode data anywhere, so deriving it would require either a lookup source or an
  invented mapping — the latter being exactly the hardcoding this task removed. Copy now carries no
  postcode. If postcode-level targeting is wanted, it needs a real data source first.
- **Rendered output changed for every asset**, including the original Blackheath campaign, whose
  copy is now derived (and shorter/plainer). This is why `template_version` was bumped.
- **The removed claims were fabrications, not styling.** "vetted", "fixed-fee", "same-day", "24/7"
  and "Fixed diagnostic pricing" were asserted for every business the engine ran campaigns for,
  with nothing registering them as true. Restoring them requires registering them as real facts.
- **Copy is now plainer and less persuasive.** That is the honest floor given what the pipeline can
  currently evidence. Richer copy needs more registered real facts (Node 16) or a per-client
  claims source, not more template literals.
- **`winner_detected` on this run is not a business result.** The performance metrics behind it are
  each node's illustrative defaults; no ads ran and no spend occurred. Flagged to the user directly.
- The pre-existing pytest collection clash between `operational_console/` and
  `operational_console_claude/` (identical `test_console_server.py` basenames) still requires
  `--ignore=operational_console` on full-suite runs. Not introduced here, not fixed here.

## Completion Status
Complete for the requested scope: Node 17 contains no hardcoded locality, postcode or service, ad
copy follows the campaign's real town and vertical, fabricated business claims removed, and the fix
verified live on the real Greenwich candidate that exposed the bug.
