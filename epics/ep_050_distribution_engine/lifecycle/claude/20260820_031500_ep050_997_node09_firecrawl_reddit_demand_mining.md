# EP050 — Node 09 Real Reddit Demand Mining via Firecrawl (Replaces Dead OAuth Path)

Source: User walked back through the pipeline node-by-node after objecting to automated batch
progression ("you appeared to have jumped a few steps... walk me through each node from 15"),
corrected the actual objective ("the point of node 01-17 is to know where the demand is, what
content to generate, who to target, and where to place that content... the objective was to
create many campaigns across many trades categories... the distribution channel was going hit
communities like reddit... your demand finding as a being a spectacular failure so far"), then:
"if i remember correctly i was able to use that skill to query communities on reddit... i was able
to find out what was been discussed", then: "you need to tie to a workflow... write and test it..
if it works then need to tie back to a specific node".

Task Type: standard

Task Attributes:
- workflow_task: true
- workflow_name: "ep050_distribution_engine_delivery_20260816"
- workflow_stage: complete

Task Summary: The user correctly identified that all of today's demand-hunting work (Node 05,
Firecrawl generic web search) was solving a narrower problem than the real objective: real
community discussions (Reddit) revealing real language/pain points to inform ad content, not just
confirming a local business exists. Investigated Node 09 (Community Intelligence) -- real code,
100% accepted 17 Aug, 31/31 tests -- and found it has NEVER run for real: its Reddit OAuth
credentials (EP050_REDDIT_CLIENT_ID/SECRET) were never set. Investigated the user's recollection of
a working Reddit query mechanism, found a real public-API skill elsewhere in the workspace
(distribution_TT / skills/distribution_engine), live-tested it, and got a genuine HTTP 403 --
Reddit's own anti-bot policy now blocks that path. Proved Firecrawl (already authenticated) can
directly surface real Reddit discussion via `site:reddit.com` search -- live-tested, real UK
tenant/emergency-repair threads returned. Built this into Node 09 as a new, parallel live-fetch
path (`register_from_firecrawl_search`), tested, and live-verified.

Context:
- `epics/ep_050_distribution_engine/implementation/node_09/community_intelligence.py`
- `epics/ep_050_distribution_engine/implementation/node_09/test_community_intelligence.py`
- Investigated but not modified: `skills/distribution_engine/platforms/reddit/skills/reddit_evidence_mining_public.py`, `distribution_TT/reddit_workflow.py`

Destination Folder: `epics/ep_050_distribution_engine/implementation/`; this lifecycle record under `workstream/300_complete/`.

Dependency: Node 05's Firecrawl migration (met, same day) -- this reuses the same real, already-
authenticated Firecrawl credential and `http_post_json` infrastructure.

## Plan
- [x] 1. Investigate whether Node 09's existing Reddit OAuth path has ever actually run, rather
      than assume from its "100% accepted" status.
  - [x] Test: Checked `.env` for `EP050_REDDIT_CLIENT_ID`/`SECRET` -- neither set, anywhere.
  - [x] Evidence: Implementation Log.
- [x] 2. Investigate the user's recollection of a working Reddit query mechanism before assuming
      it's unavailable.
  - [x] Test: Found `skills/distribution_engine/platforms/reddit/skills/reddit_evidence_mining_public.py`
        (Reddit's public, no-auth JSON API). Live-tested directly -- real HTTP 403 from Reddit
        itself, not a bug in the script.
  - [x] Evidence: Implementation Log.
- [x] 3. Find and prove a working real alternative before proposing to build anything.
  - [x] Test: `firecrawl search "site:reddit.com [problem]"` -- real, rich UK results
        (r/CasualUK, r/LegalAdviceUK, r/AskUK threads), zero new credentials needed.
  - [x] Evidence: Implementation Log.
- [x] 4. Tie the working mechanism to the correct existing node (Node 09), reading its full
      existing contract first so the addition integrates cleanly rather than duplicating it.
  - [x] Test: Read the full `CommunitySignalRegistry`/`register()` contract before writing code.
  - [x] Evidence: Implementation Log.
- [x] 5. Build the real fetch function and registry method, live-verify before writing tests.
  - [x] Test: `fetch_community_signal_via_firecrawl()` called live -- returned a real Reddit
        thread. Found and fixed a geo-ambiguity bug in the same pass (locality alone matched
        r/nyc; region+country needed, same fix already made in Node 05 earlier the same day).
  - [x] Evidence: Implementation Log.
- [x] 6. Write regression tests from the real captured response shape, matching the existing
      OAuth-path test pattern exactly.
  - [x] Test: 6 new tests (disabled-by-default+blocked-socket, missing-credential, mocked-fetch
        produces-valid-record, no-results fail-closed, unsuccessful-response fail-closed,
        full-geography-in-query). Node 09: 46/46. Full suite: 674/674.
  - [x] Evidence: Implementation Log.

## Evidence
Objective-Delivery-Coverage: 100% for the requested scope (a real, working, tested community
demand-mining path, tied to the correct node).
Auto-Acceptance: false (new live-fetch mechanism; verified live against the real Firecrawl API,
not just mocked)
- Evidence-Type: manual_verification
  - Artifact: Live call to `fetch_community_signal_via_firecrawl("boiler broken no heat",
    {"locality": "Greenwich", ...})` returned a real Reddit thread from r/TenantsInTheUK
    ("Unexpected Heating Charges from Landlord – Seeking Advice"), with a real HTTP 200 receipt.
    Prior to the geography fix, the same call with locality-only matched an r/nyc thread --
    caught and fixed before shipping, not left as a known issue.
  - Objective-Proved: The new path genuinely surfaces real, geo-correct Reddit community content,
    not a mocked or assumed response.
  - Status: captured
- Evidence-Type: manual_verification
  - Artifact: Reddit's public no-auth JSON API, tested live via
    `reddit_evidence_mining_public.py`, returned a genuine HTTP 403 for r/DIY -- confirming the
    user's previously-working mechanism is currently blocked Reddit-side, not fixable in this repo.
  - Objective-Proved: The decision to build a new path (rather than fix the old one) is grounded
    in a real, current test result, not assumption.
  - Status: captured
- Evidence-Type: test_output
  - Artifact: `pytest node_09/ -q` -> 46 passed; `pytest . -q --ignore=operational_console` ->
    674 passed.
  - Objective-Proved: No regression; the new path is fully covered including its own fail-closed
    edge cases.
  - Status: captured

## Implementation Log
- 2026-08-19T20:15+01:00 (session-local clock; see note) -- User corrected the actual objective and
  called today's demand-finding work "a spectacular failure" relative to it -- narrow trade/geo
  scope, wrong channel model (Google Maps listing, not social/video), wrong demand source (generic
  web search, not real community discussion). Took this as a real correction, not a mood to manage.
- ~20:20 -- Investigated Node 09 directly: real code, 100% accepted, 31/31 tests -- but confirmed
  via `.env` grep that `EP050_REDDIT_CLIENT_ID`/`SECRET` were never set. It has never run for real.
- ~20:25 -- User: "if i remember correctly i was able to use that skill to query communities on
  reddit". Searched the wider workspace (not just EP050) and found
  `skills/distribution_engine/platforms/reddit/skills/reddit_evidence_mining_public.py`, a
  no-auth public-API Reddit reader. Live-tested it directly -- real HTTP 403, Reddit's own
  anti-bot policy, not a bug.
- ~20:30 -- Proved a working alternative before proposing anything: `firecrawl search
  "site:reddit.com boiler broke no heat what do I do"` returned genuine, rich UK results.
- ~20:35 -- User: "you need to tie to a workflow... write and test it.. if it works then need to
  tie back to a specific node". Read Node 09's full existing contract, then built
  `fetch_community_signal_via_firecrawl()` and `register_from_firecrawl_search()` as a second,
  parallel live path alongside (not replacing) the dormant OAuth one.
- ~20:40 -- Live-verified the new fetch function before writing any test. Found the top result was
  r/nyc on a Greenwich-only query -- the same geo-ambiguity defect already fixed in Node 05 earlier
  the same day. Fixed it here too (full locality+region+country in the query) before proceeding.
- ~20:45 -- Wrote 6 regression tests mirroring the existing OAuth-path test pattern exactly, using
  the real response shape captured live. Full Node 09 suite (46/46) and full EP050 suite
  (674/674) both green.

## Changes Made
- `node_09/community_intelligence.py` (v1.3.0): new `FIRECRAWL_SEARCH_PATH`/`FIRECRAWL_RESULT_LIMIT`
  constants; `_subreddit_from_url()` helper; `fetch_community_signal_via_firecrawl()`;
  `CommunitySignalRegistry.register_from_firecrawl_search()`; new `source_type`
  `"community_search"` added to `ALLOWED_SOURCE_TYPES`.
- `node_09/test_community_intelligence.py`: 6 new tests for the Firecrawl path.

## Validation
- PASS -- `pytest node_09/ -q` -> 46 passed.
- PASS -- `pytest . -q --ignore=operational_console` -> 674 passed.
- PASS -- Live: real Reddit thread returned, geo-correct after the fix.

## Risks/Notes
- **Not yet wired into the operational console.** This is a real, tested, callable node-level
  capability -- nothing in `server.py` exposes it as an API endpoint yet, so it is not reachable
  from the console UI or `pipeline/run_all`. Flagged to the user directly; wiring is a deliberate
  next decision, not an oversight.
- **The dormant OAuth path (`register_from_live_source`, `community_api`) was left in place, not
  removed.** If the user later obtains a real Reddit "script" app and sets
  `EP050_REDDIT_CLIENT_ID`/`SECRET`, that path becomes usable too, independent of this one.
- **Reddit's public no-auth JSON API is confirmed blocked (HTTP 403) as of this session** -- worth
  re-testing periodically in case Reddit's restriction changes, but not something to keep
  re-attempting reflexively.
- **This does not yet address the channel-model correction** (video content -> YouTube/TikTok/
  Instagram, not a Google Maps listing) -- that is a separate, larger piece (Node 14's candidate
  channel list doesn't currently include any social video platform at all) not started here.

## Completion Status
Complete for the requested scope: a real, live-tested, node-tied mechanism for mining actual
community discussion as a demand signal, replacing a Reddit path that has never once worked, built
without any new credentials and verified against genuine live data before a single test was written.
