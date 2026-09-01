# EP050 — Full De-Hardcoding Sweep, Fabrication Purge, State/Position-Ordering Fixes, Config/Master-Data Lane

Source: User instruction "NO HARD CODING please" / "no hard code content!!!!! that means NO FUCKING
HARD CODING!!!! hope this clearer", then "i wish YOU WOULD STOP FABRICATING" and "remove all
fabrications", then "we CANNOT mix real with fake data", clarified 2026-08-19 that registering a
real target via Node 01 is not fabrication as long as it runs the real process from there — only
invented RESULTS presented as real outcomes are. Followed by "were there any other campaigns that
ran?" and "if node 15 is furthest... then image is incorrect", both of which surfaced two further
real bugs. Also "will need to create a configuration space in the workflow document that captures
configuration or master data ... i.e. postcode list ... for the scalable version". Finally: "if a
status is complete then must move to next ... if unable to move from an incomplete status then we
need to investigate to get it moving" and "unless failure at a gate due to criteria, or a problem,
or external wait, a campaign should continue to proceed until it becomes a valid lead" -- applying
this to Lewisham/Charlton/Eltham (each holding a real, complete Phase 2 signal but never driven
further) surfaced two more real ordering/crash bugs in the same class as the position-reporting fix.

Task Type: standard

Task Attributes:
- workflow_task: true
- workflow_name: "ep050_distribution_engine_delivery_20260816"
- workflow_stage: complete

Task Summary: Node 17's hardcoded "Blackheath"/"SE3" ad copy (fixed earlier the same day) turned
out to be one instance of a pattern repeated across Nodes 13, 14, 19, 24, 26, 35, 37. Separately,
the headless pipeline driver was fabricating leads, attribution, qualification, routing, performance,
winners, lifecycle transitions and outcome feedback (including an invented GBP 240 invoice and a
5-star customer rating) for any campaign it drove past Node 26. Both classes of defect are now
removed with regression coverage. Also fixed: a Node 26 routing allowlist that literally rejected
every real campaign except Blackheath boiler_repair, and a campaign-position ordering bug that
misreported a campaign's real pipeline stage. Closed with a new Configuration & Master Data lane on
the master workflow doc, capturing what real owned data (postcode lists, adjacency, cost rates,
verified fact sources) is needed before this can scale, versus what currently exists as an
inline-code guess.

Context:
- `epics/ep_050_distribution_engine/implementation/node_13/demand_path_discovery.py`
- `epics/ep_050_distribution_engine/implementation/node_14/channel_placement_selection.py`
- `epics/ep_050_distribution_engine/implementation/node_17/content_utility_factory.py` (earlier same-day fix, referenced)
- `epics/ep_050_distribution_engine/implementation/node_19/quality_compliance.py`
- `epics/ep_050_distribution_engine/implementation/node_24/community_participation.py`
- `epics/ep_050_distribution_engine/implementation/node_26/smart_destination_router.py`
- `epics/ep_050_distribution_engine/implementation/node_35/winner_amplification.py`
- `epics/ep_050_distribution_engine/implementation/node_37/distribution_knowledge_base.py`
- `epics/ep_050_distribution_engine/implementation/operational_console_claude/server.py`
- Corresponding test files for every node above
- `workstream/600_workflow/ep050/EP050_distribution_engine_master_workflow.html`
- `epics/ep_050_distribution_engine/implementation/operational_console_claude/data/runs/*/run.json` (data purge, not code)

Destination Folder: `epics/ep_050_distribution_engine/implementation/`; this lifecycle record under `workstream/300_complete/`.

Dependency: Node 05 Firecrawl migration + Node 17 fix (both met, same day) — the first working live
fetch is what allowed real campaigns to reach every one of these previously-unexercised code paths.

## Plan
- [x] 1. Audit every node module for hardcoded content, not just Node 17.
  - [x] Test: grep sweep across `implementation/` for domain/place terms; 7 modules beyond Node 17 hit.
  - [x] Evidence: Implementation Log.
- [x] 2. Fix Node 13's default demand-path stages (hardcoded "Blackheath"/boiler-specific text for
      every campaign) to derive service/geography from the real opportunity record.
  - [x] Test: node_13 tests pass; live re-derivation for Greenwich reads "boiler repair in
        Greenwich, London" throughout.
  - [x] Evidence: Implementation Log.
- [x] 3. Fix Node 14's default channel rationale (hardcoded "Blackheath") to derive from real geography.
  - [x] Test: node_14 tests pass.
  - [x] Evidence: Implementation Log.
- [x] 4. Fix Node 19's hardcoded destination URL, fallback copy, and gas-specific compliance check.
  - [x] Test: node_19 tests pass.
  - [x] Evidence: Implementation Log.
- [x] 5. Fix Node 26's routing rule allowlist, which literally rejected every campaign except
      geography="blackheath"/service="boiler_repair" -- a functional block, not cosmetic.
  - [x] Test: new test proves a different real town/vertical routes successfully; existing
        "unknown rule" test rewritten since it was asserting the bug.
  - [x] Evidence: Implementation Log.
- [x] 6. Fix Node 35's hardcoded adjacent-geo default list (a fixed 4-town suggestion for any winner).
  - [x] Test: default now omits the geographic_expansion variant rather than inventing one;
        new test confirms real geos still work when supplied.
  - [x] Evidence: Implementation Log.
- [x] 7. Fix Node 37's default learning_summary -- a SPECIFIC FABRICATED PERFORMANCE CLAIM
      ("yield 12.5x ROAS in South London") that would have been silently written into permanent
      "knowledge" by any unattributed caller.
  - [x] Test: all three learning-record fields now required, no default; 3 new fail-closed tests.
  - [x] Evidence: Implementation Log.
- [x] 8. Fix Node 24's hardcoded Reddit thread URL default.
  - [x] Test: node_24 tests pass with explicit target_thread_url.
  - [x] Evidence: Implementation Log.
- [x] 9. Stop the headless pipeline driver from fabricating Nodes 27-34 outcomes.
  - [x] Test: new test asserts none of node_27/28/29/30/32/34 ever appear in `steps`, and none of
        leads/attributions/qualifications/routings/performance_records/winners are ever populated.
  - [x] Evidence: Implementation Log.
- [x] 10. Purge fabricated records already on disk across all 6 real runs.
  - [x] Test: manual audit script found and removed leads/attributions/performance_records/winners/
        lifecycles/outcome_feedback, an orphaned Node 19 compliance check, a stale
        last_proposed_winner_id, and (separately) the fixture-sourced Node 16 fact and everything
        derived from it, and the Blackheath source run's never-real demo demand signal.
  - [x] Evidence: Implementation Log.
- [x] 11. Fix the campaign-position ordering bug found live via user review.
  - [x] Test: new tests pin both the previously-misreported case (signal only -> Node 11, not
        Node 16) and the genuine case (classified+clustered, no fact -> Node 16).
  - [x] Evidence: Implementation Log.
- [x] 12. Add the Configuration & Master Data lane to the master workflow doc.
  - [x] Test: brace-depth-validated the DETAILS object literal (18 total entries, 6 new); loaded
        the file in-browser and confirmed no console errors.
  - [x] Evidence: Implementation Log.
- [x] 14. Fix `derive_campaign_state`'s same ordering defect (facts checked before
      classifications/clusters), which caused `run_pipeline_headless` to short-circuit before
      Node 11 ever ran for a signal-only campaign.
  - [x] Test: new test asserts a signal-only campaign advances through node_11+node_15 and stops
        honestly at needs_facts, not steps=[].
  - [x] Evidence: Implementation Log.
- [x] 15. Fix the crash the above fix exposed: the driver's Node 18 step unconditionally read
      `meta["facts"]`, previously unreachable without facts present.
  - [x] Test: covered by the same new test (no KeyError, honest stop with real steps recorded).
  - [x] Evidence: Implementation Log.
- [x] 13. Full regression across every change.
  - [x] Test: 663 passed (twice -- once after the audit/purge, again after the state-ordering fixes).
  - [x] Evidence: Implementation Log.

## Evidence
Objective-Delivery-Coverage: 100% for the requested scope (remove hardcoded content and fabricated
results across the pipeline; document required config/master data).
Auto-Acceptance: false (touches rendered output, routing eligibility, and permanent knowledge-base
records across 8 node modules; verified live and via full regression)
- Evidence-Type: manual_verification
  - Artifact: Live campaign queue after restart -- Lewisham/Charlton/Eltham correctly report
    "Phase 3 · Node 11" (previously misreported as "Phase 4 · Node 16" with zero classifications/
    clusters on record). Greenwich, which genuinely completed classification+clustering, correctly
    still reports Node 16.
  - Objective-Proved: The position-reporting fix is real and live, not just unit-tested.
  - Status: captured
- Evidence-Type: manual_verification
  - Artifact: Blackheath source run's fabricated lifecycle transition and outcome_feedback record
    (including a GBP 240 invoice and 5-star customer rating referencing a lead that never existed)
    located and removed after the earlier fabrication purge missed them; found via a complete
    per-run field sweep rather than assuming the first purge was exhaustive.
  - Objective-Proved: No fabricated result-shaped record remains in any of the 6 real run files.
  - Status: captured
- Evidence-Type: test_output
  - Artifact: `pytest . -q --ignore=operational_console` from
    `epics/ep_050_distribution_engine/implementation` -> 663 passed.
  - Objective-Proved: No regression across the full node suite from any of the above changes.
  - Status: captured

## Implementation Log
- 2026-08-19T12:55+01:00 -- User ran the Greenwich pipeline and immediately reported the wrong-town
  bug (documented in the earlier same-day Node 17 record). Broadened the audit to every node module
  after "NO HARD CODING" -- grep swept `implementation/` for domain/place terms, found 7 more hits.
- 2026-08-19T13:05+01:00 -- Fixed Node 13 (demand path stages) and Node 14 (channel rationale),
  both of which fed Node 17's already-fixed copy from upstream, so the Node 17 fix alone had been
  incomplete.
- 2026-08-19T13:15+01:00 -- User: "i wish YOU WOULD STOP FABRICATING". Investigated the headless
  driver directly rather than defending the earlier work; found it drove Nodes 27-34 from generated
  input, including calling Node 27 with consent_granted=True -- a fabricated compliance artifact,
  not just fake data. Cut the driver off at Node 26 (hard stop), added the fail-closed test, purged
  the first round of fabricated records from disk.
- 2026-08-19T13:25+01:00 -- User: "we CANNOT mix real with fake data" after I reported a fabricated
  performance record as if it were status. Full-field audit (not just leads/winners) found the
  Node 16 fact was fixture-sourced across every run, and the Blackheath SOURCE run's demand signal
  was itself a hand-entered demo (sig_console_demo_01), never real -- meaning everything descended
  from it, including the winner that had triggered all four candidates' creation, was unreal.
  Purged the fact layer and the demo-signal layer, plus an orphaned Node 19 compliance check found
  in the same pass.
- 2026-08-19T13:35+01:00 -- User clarified the fabrication boundary: registering a real target
  through Node 01 is legitimate configuration, not fabrication, as long as it runs the real process
  from there; only invented results pretending to be real outcomes are the problem. Confirmed this
  matched what had already been done and continued under that explicit rule.
- 2026-08-19T13:40+01:00 -- Full node-by-node hardcoding audit (Node 19, 24, 26, 35, 37) at the
  user's insistence ("NO FUCKING HARD CODING"). Node 26 turned out to be a FUNCTIONAL block, not
  cosmetic: its routing rule required an exact match on geography="blackheath"/service="boiler_repair",
  so every other real campaign would have been rejected outright with "no approved routing rule
  matches". Node 37 turned out to hold a specific fabricated performance claim ("yield 12.5x ROAS in
  South London") as its default -- the same defect class as the fake leads, just not yet reached by
  any campaign. Fixed all five modules, updated/added tests, ran full regression (662 passed at
  this point).
- 2026-08-19T13:52+01:00 -- User: "were there any other campaigns that ran?" Full per-run field
  sweep (not assuming the earlier purge was complete) found `lifecycles` and `outcome_feedback` --
  including a fabricated GBP 240 invoice and 5-star rating -- still present on the Blackheath source
  run, missed by the first purge because Nodes 31/33 weren't in its node-set. Also found a stale
  `last_proposed_winner_id` pointer. Purged all three, extended the permanent regression test to
  cover Nodes 31/33 and these two fields explicitly.
- 2026-08-19T13:58+01:00 -- User: "if node 15 is furthest... then image is incorrect" (screenshot
  showing the console reporting Greenwich at "Node 16", seemingly contradicting "furthest real node
  = Node 15"). Explained the framing was consistent (Node 15 = last completed, Node 16 = next/
  blocked) but cross-checked the OTHER campaigns visible in the same screenshot and found a real bug:
  Lewisham/Charlton/Eltham, each holding zero classifications and zero clusters, were all reported
  at "Phase 4 · Node 16". Root cause: derive_campaign_position checked `facts` before checking
  `classifications`/`clusters`, so any campaign with only a signal short-circuited past Phase 3
  entirely. Fixed the check order, rewrote the test that had asserted the bug, added a second test
  pinning the genuine Node 16 case.
- 2026-08-19T14:00+01:00 -- Built the Configuration & Master Data lane on the master workflow doc:
  6 cards (geo adjacency, service adjacency, postcode master list, live-fetch credentials, cost
  rates, verified fact sources), each stating what's real today vs. what's an inline-code guess vs.
  what's missing entirely. Validated the DETAILS object literal by brace-depth parsing (JS doesn't
  execute for a local file outside the project root in this browser preview) and confirmed no
  console errors on load.
- 2026-08-19T14:05+01:00 -- Full regression: 663 passed.
- 2026-08-19T14:08+01:00 -- User: "if a status is complete then must move to next ... unless
  failure at a gate due to criteria, or a problem, or external wait, a campaign should continue to
  proceed until it becomes a valid lead". Applied directly: Lewisham/Charlton/Eltham each held a
  complete, real Phase 2 signal but had never been driven further. Ran pipeline/run_all on all
  three and got state="needs_facts", steps=[] -- no progress at all, despite nothing genuinely
  blocking Node 11/15. Root cause: `derive_campaign_state` had the identical ordering defect just
  fixed in `derive_campaign_position` (facts checked before classifications/clusters), and
  `run_pipeline_headless` short-circuits entirely on state=="needs_facts" before attempting
  anything. Fixed the ordering; re-ran the three campaigns; the fix immediately exposed a second,
  previously-unreachable bug -- the driver's Node 18 step unconditionally read `meta["facts"]` and
  crashed with KeyError the instant Node 11/15 were allowed to run without facts existing yet.
  Added an explicit honest-stop return there instead of a crash. Updated the two tests that had
  asserted the buggy steps=[] behaviour (one of them a soft "if it ran" conditional, itself written
  defensively around this exact bug -- made it a hard assertion now that Node 11 genuinely always
  runs). Re-ran full regression (663 passed) and re-drove all three real campaigns live: each now
  correctly advances through node_11+node_15 and stops at the same genuine boundary as Greenwich --
  Phase 4, Node 16, no canonical facts registered. All four real geo campaigns now sit at their
  true furthest reachable state with nothing fabricated and nothing stuck on a bug.

## Changes Made
- `node_13/demand_path_discovery.py`: `_get_default_stages_for_intent` now derives service/geography
  text from the real opportunity record; new `_service_phrase`/`_place_phrase` helpers;
  `DemandPathRecord` gained `geography`/`service_context` fields to carry that context to Node 14.
- `node_14/channel_placement_selection.py`: `_get_default_candidate_channels` now takes `geography`
  and derives its local-search rationale from it instead of a literal.
- `node_19/quality_compliance.py`: default destination URL, fallback summary/steps/headline/CTA/
  utm_campaign all de-hardcoded; the "GAS SAFE" alternative in the disclaimer check removed
  (never load-bearing, purely domain-specific).
- `node_24/community_participation.py`: `target_thread_url` has no default, now required.
- `node_26/smart_destination_router.py`: `_RULES` no longer matches on `geography`/`service`
  (real per-campaign data, not a rule-matching literal) -- only `intent`/`channel`/
  `destination_path`/`cta_type` remain policy-matched fields.
- `node_35/winner_amplification.py`: `adjacent_geos` has no fabricated default; the
  `geographic_expansion` variant is simply omitted when none is supplied.
- `node_37/distribution_knowledge_base.py`: `learning_summary`/`key_success_factors`/
  `recommended_rules` are all required, no default (previous default was a specific fabricated
  ROAS claim).
- `operational_console_claude/server.py`:
  - `run_pipeline_headless` hard-stops before Node 27; returns `distribution_ready_awaiting_real_events`.
  - `derive_campaign_state` gained the same new state.
  - `derive_campaign_position` check order fixed (classifications/clusters before facts).
  - `handle_node26_generate`'s routing-context defaults now derive from the real target/signal.
  - `handle_node37_generate` now requires `learning_summary`/`key_success_factors`/`recommended_rules`
    in the request body.
  - `derive_campaign_state`: same ordering fix as `derive_campaign_position` -- classifications/
    clusters checked before facts, so `needs_facts` only fires once Phase 3 has genuinely run.
  - `run_pipeline_headless`: explicit honest-stop before the Node 18 step when facts are absent,
    replacing an unconditional `meta["facts"]` read that would otherwise crash with KeyError.
- Tests: new/updated coverage across `node_13`, `node_14`, `node_17` (earlier same day), `node_19`,
  `node_24`, `node_26`, `node_35`, `node_37`, and `operational_console_claude/test_console_server.py`.
- `workstream/600_workflow/ep050/EP050_distribution_engine_master_workflow.html`: new
  "Configuration & Master Data" lane, toolbar filter, 6 node cards, 6 DETAILS entries.
- Data-only (no code): purged fabricated leads/attributions/qualifications/routings/
  performance_records/winners/lifecycles/outcome_feedback, the fixture-sourced fact and everything
  derived from it, the Blackheath source run's demo demand signal and everything derived from it,
  one orphaned Node 19 compliance check, and one stale `last_proposed_winner_id` pointer, across all
  6 real run files under `operational_console_claude/data/runs/`.

## Validation
- PASS -- `pytest . -q --ignore=operational_console` -> 663 passed.
- PASS -- Live: campaign queue correctly reports Lewisham/Charlton/Eltham at Node 11, Greenwich at
  Node 16, after restart.
- PASS -- Config lane HTML loads with no console errors; DETAILS object literal brace-validated.

## Risks/Notes
- **The hardcoding audit was targeted, not exhaustive.** It grepped for terms already known to be
  suspect (boiler, Blackheath, SE3, 24/7, etc.) across `implementation/`. It cannot prove zero
  hardcoding exists under different vocabulary in modules not yet exercised by a real campaign --
  the same way every defect fixed today was invisible until a real campaign first reached that code
  path. Flagged directly to the user rather than claimed as complete.
- **The pre-existing pytest collection clash** between `operational_console/` and
  `operational_console_claude/` (duplicate `test_console_server.py` basename) still requires
  `--ignore=operational_console` on full-suite runs. Not introduced or fixed here.
- **All 6 real campaigns now sit at their genuine furthest reachable position**: the four geo
  candidates (Blackheath source, Greenwich, Lewisham, Charlton, Eltham -- note two runs are named
  Blackheath, source and the boiler_service candidate) all correctly reach Phase 4 · Node 16,
  blocked on a real fact, with nothing fabricated anywhere in their stored state. Progressing any
  of them past Node 16 needs a real, non-fixture fact source -- exactly the gap CONFIG_FACT_SOURCES
  on the new lane documents as the highest-priority item.
- Node 26's routing-rule fix and Node 35/37's default-removal fixes were found DURING this task,
  not requested up front -- each surfaced from methodically working through the audit list rather
  than stopping once the town-name literals were gone.

## Completion Status
Complete for the requested scope: no hardcoded content found in this audit remains, no
fabricated-result record exists in any real run, the driver cannot regenerate either class of
defect (regression-tested), a genuine display bug found via user review is fixed, and the
configuration/master-data gap for scaling is now documented with a specific, real example
(postcodes) plus five more real gaps found while building the lane.
