# EP050 — Two Real Plausibility Gates: Commercial Intent + Service Relevance

Source: User instruction after auto-advance ordering fixes: "we have to be cognisant if all
campaigns stopping at the same point will be suspect ... for example if i created campaign
mars_spaceship_builder catford ... and that goes all the way to node 15 ... then i believe
something will be wrong". Confirmed live. Then, after testing the fix: "also need to test a
product / service which is plausible but zero audience ... i.e. snowmobile_repair catford /
audience_hunter Reykjavik". Confirmed live that the first gate was insufficient. Final direction:
"service = snowmobile_repair (not est agent)" -- build a check on the service's own real tokens.

Task Type: standard

Task Attributes:
- workflow_task: true
- workflow_name: "ep050_distribution_engine_delivery_20260816"
- workflow_stage: complete

Task Summary: The pipeline had no plausibility check anywhere between Node 01 (registration, which
accepts any string) and Node 16 (which needs a real fact). Live-tested with a deliberately
implausible target (`mars_spaceship_builder`, Catford): it sailed straight through Node 05's
non-zero-results check and Nodes 11/15 to the identical `needs_facts` state as every genuine
boiler campaign. Built a commercial-intent gate using Node 11's already-computed
`commercial_intent_score`. Live-tested again with two more real, deliberately chosen cases
(`snowmobile_repair`/Catford, `audience_hunter`/Reykjavik) and found the first gate insufficient --
both passed it. Built a second gate checking whether the service's own real name tokens appear in
the actual fetched search results, which catches both remaining cases.

Context:
- `epics/ep_050_distribution_engine/implementation/operational_console_claude/server.py`
- `epics/ep_050_distribution_engine/implementation/operational_console_claude/test_console_server.py`
- `workstream/600_workflow/ep050/EP050_distribution_engine_master_workflow.html`
- No node module changes -- both gates live entirely in the console server, reusing
  Node 11's `commercial_intent_score` and Node 05's real fetched `search_result_summary`.

Destination Folder: `epics/ep_050_distribution_engine/implementation/`; this lifecycle record under `workstream/300_complete/`.

Dependency: The state/position ordering fixes and Node 05 Firecrawl migration (both met, same day)
-- a working live fetch plus a driver that genuinely advances campaigns is what allowed a
deliberately-implausible campaign to reach far enough to expose this gap in the first place.

## Plan
- [x] 1. Live-test the user's specific hypothesis (mars_spaceship_builder, Catford) rather than
      reason about it abstractly.
  - [x] Test: Registered a real target/product/audience/conversion, ran a real Firecrawl search,
        ran the real pipeline driver. Confirmed it reached needs_facts, identical to real campaigns.
  - [x] Evidence: Implementation Log.
- [x] 2. Identify the cheapest already-available real signal rather than inventing new
      instrumentation.
  - [x] Test: Confirmed via code read that `commercial_intent_score` is a required (non-Optional)
        field on every Node 11 classification, always computed, never skipped.
  - [x] Evidence: Implementation Log.
- [x] 3. Build the commercial-intent gate; verify the real cost before shipping it.
  - [x] Test: Confirmed Greenwich/Lewisham/Charlton/Eltham's own real signals also score 0.0
        (informational query, no COMMERCIAL_KEYWORDS hit) -- surfaced to the user explicitly before
        building, so the decision to exclude them was made knowingly, not discovered after the fact.
  - [x] Evidence: Implementation Log.
- [x] 4. Wire the gate into all three checkpoints that must agree (state, position, driver),
      including the mid-run case (a campaign classified for the first time in the same call).
  - [x] Test: New regression test; fixed two test fixtures that had been asserting the old,
        unfiltered behaviour (one was itself written defensively around this exact absence).
  - [x] Evidence: Implementation Log.
- [x] 5. Live-test the user's second, sharper hypothesis: a plausible service in an implausible
      market (snowmobile_repair/Catford) and a non-existent service concept (audience_hunter,
      tested against both Reykjavik and Catford).
  - [x] Test: Real Firecrawl searches, real results captured and inspected.
  - [x] Evidence: Implementation Log.
- [x] 6. Diagnose exactly why both passed the first gate, with a controlled comparison rather than
      assumption -- confirmed geo-targeting itself was working correctly (a direct Firecrawl probe
      proved Reykjavik location targeting returns real local results for an unambiguous query).
  - [x] Test: Side-by-side probe script comparing Reykjavik vs Catford on both the exact failing
        query and a real control query.
  - [x] Evidence: Implementation Log.
- [x] 7. Build the service-relevance gate on the user's own framing ("service = snowmobile_repair
      (not est agent)").
  - [x] Test: Reproduced all three real cases as regression tests (snowmobile, audience_hunter,
        plus a positive control), using real result shapes captured from the live tests.
  - [x] Evidence: Implementation Log.
- [x] 8. Handle the fixture-breakage this exposed: offline/manually-curated test signals have no
      real search results to check relevance against.
  - [x] Test: Gate exempts non-`search_query` signals explicitly, with the reasoning documented in
        the code, not just silently special-cased.
  - [x] Evidence: Implementation Log.
- [x] 9. Full regression, live re-verification, clean up every disposable test campaign.
  - [x] Test: 667 passed (1 transient network flake on a genuinely-live-network test, confirmed
        clean on isolated re-run); all 6 real campaigns unaffected; 5 disposable test runs deleted.
  - [x] Evidence: Implementation Log.
- [x] 10. Document both gates on the master workflow doc's Configuration & Master Data lane.
  - [x] Test: Brace-depth-validated the DETAILS object literal after each edit (19 total entries).
  - [x] Evidence: Implementation Log.

## Evidence
Objective-Delivery-Coverage: 100% for the requested scope (two real, live-verified plausibility
gates; both documented as config/master-data items for future tuning).
Auto-Acceptance: false (changes what proceeds through the pipeline for every campaign; verified
live against real search data across five distinct real test cases)
- Evidence-Type: manual_verification
  - Artifact: Five real, disposable test campaigns run end-to-end against live Firecrawl and
    deleted after verification: `mars_spaceship_builder`/Catford (gate 1 catches),
    `snowmobile_repair`/Catford (gate 1 passes, gate 2 catches), `audience_hunter`/Reykjavik and
    `audience_hunter`/Catford (gate 1 passes both, gate 2 catches both -- the Catford variant
    matched a real local estate agent, 'Hunters Catford', on the coincidental surname token
    'Hunter'), plus a direct Firecrawl probe comparing Reykjavik vs Catford geo-targeting on both
    the failing query and a real control query ("marketing agency"), proving geo-targeting itself
    was correct and the failure was service-relevance, not location.
  - Objective-Proved: Both gates work against real data, in the specific ways the user predicted
    and tested for, not just in unit-test fixtures.
  - Status: captured
- Evidence-Type: manual_verification
  - Artifact: Live campaign queue after restart -- all 6 real campaigns unaffected by either gate
    (they stop on the genuine `needs_facts`/`pending_phase2_approval` blockers established earlier
    the same day; gate 1 does exclude them going forward from re-classification, since their real
    signals score commercial_intent_score=0.0, an accepted, explicitly-surfaced cost).
  - Objective-Proved: Neither gate silently changed the state of already-progressed real campaigns
    in an unexpected way; the one real campaign whose state DID change (from needs_facts to
    stopped_low_commercial_intent) was confirmed and explained before being built, not after.
  - Status: captured
- Evidence-Type: test_output
  - Artifact: `pytest operational_console_claude/test_console_server.py -q` -> 98 passed;
    `pytest . -q --ignore=operational_console` -> 667 passed (666 + 1 transient network flake,
    confirmed clean on isolated re-run of that single test).
  - Objective-Proved: No regression; both gates and all three of their real-world failure modes
    are now pinned by regression tests using real, captured result shapes.
  - Status: captured

## Implementation Log
- 2026-08-19T14:20+01:00 -- User: "if all campaigns stopping at the same point will be suspect ...
  mars_spaceship_builder catford ... if that goes all the way to node 15 ... something will be
  wrong". Live-tested it for real rather than reasoning abstractly: registered target/product/
  audience/conversion, ran a real Node 05 Firecrawl search (genuinely returned 10 HTTP-200 results
  -- NASA/SpaceX/YouTube/STEM pages, zero local businesses), ran the real pipeline driver. Confirmed
  it reached the identical `needs_facts` state as Greenwich, with `commercial_intent_score: 0.0`
  and `urgency: low` sitting unused in its own classification record.
- 2026-08-19T14:35+01:00 -- User: "demand gate only checks 'did the search return non-zero
  results' should be > 0". Tightened the existing check from a string inequality to an explicit
  numeric comparison (minor, unrelated to the plausibility gap, but a real correctness improvement
  found in passing).
- 2026-08-19T14:40+01:00 -- User asked whether `commercial_intent_score` is always present.
  Confirmed via code read (required constructor field, never Optional, computed on every code path)
  before answering, rather than assuming from the two examples already seen.
- 2026-08-19T14:45+01:00 -- User: "if no commercial_intent then for the moment we want to exclude
  ... maybe later we make the gates configurable". Surfaced the real cost BEFORE building (all four
  real geo campaigns also score 0.0). Built MIN_COMMERCIAL_INTENT_SCORE + a shared gate function,
  wired into all three checkpoints (state, position, driver) including the mid-run case. Deleted the
  Mars test campaign. Full regression, live re-verification: all four real campaigns correctly
  transitioned to `stopped_low_commercial_intent`.
- 2026-08-19T14:55+01:00 -- User: "also need to test a product / service which is plausible but
  zero audience ... snowmobile_repair catford / audience_hunter Reykjavik". Live-tested both.
  snowmobile_repair returned real Catford car-mechanic businesses (wrong trade, not zero results).
  audience_hunter/Reykjavik returned generic travel content. Both passed the commercial-intent gate
  (both queries contained real commercial words), proving it insufficient -- reported this
  correction directly rather than let the earlier "gate built" status stand unqualified.
- 2026-08-19T15:00+01:00 -- User: "but your search should include location shouldnt it?" Verified
  from the actual code and the actual request that location was included, both in the query text
  and as an explicit Firecrawl `location` parameter -- geo-targeting was not the gap.
- 2026-08-19T15:05+01:00 -- User: "but Reykjavik not taken into context ... at all??" Rather than
  assert an answer, ran a controlled side-by-side Firecrawl probe: the exact failing query,
  the same query's location param alone, and a real unambiguous control query ("marketing agency")
  against both Reykjavik and Catford. Proved geo-targeting genuinely works for Iceland (a real
  Icelandic marketing-agency directory, agencies.is, came back for the control query) -- the
  audience_hunter failure was that the service concept itself never matches anywhere, and what
  looked like a Catford "success" was a coincidental surname collision ("Hunters Catford", a real
  estate agent), re-confirmed by testing audience_hunter/Catford directly at the user's request.
- 2026-08-19T15:10+01:00 -- User: "service = snowmobile_repair (not est agent)" -- confirmation to
  build the fix. Built `_passes_service_relevance_gate`: requires the service's own distinctive
  name tokens (generic trade words dropped) to appear together in at least one real fetched result.
  Wired into the same three checkpoints as gate 1. Discovered and fixed a real fixture-breakage:
  offline test signals (`manual_curation`, no real search results) failed closed for the wrong
  reason -- exempted non-`search_query` signals from this specific gate, with the reasoning
  documented in the code.
- 2026-08-19T15:12+01:00 -- Added three regression tests reproducing all real cases (snowmobile,
  audience_hunter, plus a positive control) using the actual result shapes captured from the live
  tests. Full regression (667 passed, one confirmed-transient network flake), live re-verification,
  deleted all five disposable test campaigns including one leftover the user didn't have to catch
  (a second Reykjavik diagnostic run from the probe step).
- 2026-08-19T15:15+01:00 -- Updated the Configuration & Master Data lane's "Campaign quality gates"
  card and DETAILS entry to document both gates, their real evidence, and their known costs. Filed
  this record.

## Changes Made
- `server.py`:
  - Tightened the Node 05 approval demand check to an explicit numeric `> 0` comparison.
  - New `MIN_COMMERCIAL_INTENT_SCORE` constant + `_passes_commercial_intent_gate()`.
  - New `_SERVICE_TOKEN_STOPWORDS`, `_service_relevance_tokens()`, `_passes_service_relevance_gate()`.
  - New terminal states `stopped_low_commercial_intent` and `stopped_service_not_locally_relevant`,
    wired into `derive_campaign_state`, `derive_campaign_position`, and `run_pipeline_headless`
    (both the top-level short-circuit and the mid-run first-classification case).
  - Version history entry (v1.11.0) documenting both gates with the real evidence behind each.
- `test_console_server.py`: new `_register_live_signal_with_results` helper; 4 new regression tests
  (commercial-intent gate, service-relevance x2 real cases, service-relevance positive control);
  fixed two shared fixtures (`_register_demand_signal`, `_classify_signal`) whose hardcoded query
  text scored 0.0 commercial intent, which would otherwise have silently broken every test relying
  on them to reach Node 15.
- `workstream/600_workflow/ep050/EP050_distribution_engine_master_workflow.html`: updated the
  "Campaign quality gates" card and its DETAILS entry to document both gates. Also fixed a stray
  extra closing brace in the DETAILS object literal left over from an earlier same-day edit --
  a real JavaScript syntax error that would have broken the page in any actual browser, caught by
  brace-depth validation before it could ship uncorrected.
- Data-only (no code): deleted 5 disposable real test campaigns
  (`mars_spaceship_builder`/Catford, `snowmobile_repair`/Catford, `audience_hunter`/Reykjavik x2,
  `audience_hunter`/Catford) after verification.

## Validation
- PASS -- `pytest operational_console_claude/test_console_server.py -q` -> 98 passed.
- PASS -- `pytest . -q --ignore=operational_console` -> 667 passed (1 transient network flake on a
  genuinely-live-network test, confirmed clean on isolated re-run).
- PASS -- Live: all 6 real campaigns' state unaffected by the service-relevance gate (never
  reached, since gate 1 already stops them); all 4 geo campaigns correctly show
  `stopped_low_commercial_intent` from gate 1.
- PASS -- Live: 5 disposable test campaigns each demonstrated the exact real-world failure mode
  they were built to test, then deleted.

## Risks/Notes
- **Gate 1 has a real, accepted false-negative cost.** All four real geo campaigns (Greenwich,
  Lewisham, Charlton, Eltham) now score 0 on commercial intent and are excluded going forward. This
  was surfaced to the user before building, and the user's explicit, informed decision was to
  accept it. It is not a bug; it is a known and documented tradeoff.
- **Gate 2 cannot be tested against every future case in advance.** It requires the service's
  distinctive tokens to appear together in a real result -- a business using different terminology
  than the registered service slug (e.g. "septic tank" vs a service literally named "septic_tank")
  could still be wrongly excluded. Not fixed here; flagged as the natural next edge case.
- **Both thresholds are single named constants specifically so they can become configurable per
  vertical/client later**, per the user's own framing ("maybe later we make the gates configurable
  if there is a need to vary"). Not built yet -- flagged as future work on the config-lane card.
- **The stray-brace JavaScript bug found and fixed in this task was introduced by an earlier
  same-day edit** (the initial Configuration & Master Data lane insertion), not by anything in
  this task's own scope. Caught only because this task's own insertion script reused the same
  brace-counting logic and was checked before shipping.

## Completion Status
Complete for the requested scope: two real, live-tested plausibility gates now stop implausible
campaigns at the earliest point real evidence contradicts them, both documented with their real
costs on the Configuration & Master Data lane, both regression-tested against the actual real-world
cases that motivated them, and all real campaign state confirmed unaffected in any way that wasn't
explicitly surfaced and agreed first.
