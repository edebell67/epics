# EP050 — Node 05 Search Provider Migration (Google Custom Search → Firecrawl) + Demand Gate Fix

Source: User reported "there was a google problem with node 5 yesterday. can you retest today?",
then after root-cause confirmation: "lets move quickly to the suggested solution".

Task Type: standard

Task Attributes:
- workflow_task: true
- workflow_name: "ep050_distribution_engine_delivery_20260816"
- workflow_stage: complete
- depends_on:
  - "Node 05 Search Demand Discovery (met, pre-existing) — provider swapped, contract unchanged"

Task Summary: Node 05's live search provider was permanently broken. Google **closed the Custom
Search JSON API to new customers** (their own docs: *"The Custom Search JSON API is closed to new
customers"*, discontinuation 2027-01-01), so every call returned HTTP 403 "This project does not
have the access to Custom Search JSON API" — unfixable by any configuration. Migrated Node 05 to
Firecrawl. In doing so, the first-ever successful live fetch in this node's history immediately
exposed a **latent demand-gate bug** that would have silently discarded every good candidate.

Context:
- `epics/ep_050_distribution_engine/implementation/node_05/search_demand_discovery.py` (v1.3.0 → v2.0.0)
- `epics/ep_050_distribution_engine/implementation/node_05/test_search_demand_discovery.py`
- `epics/ep_050_distribution_engine/implementation/shared/live_fetch.py` (v1.2.0 → v1.3.0)
- `epics/ep_050_distribution_engine/implementation/operational_console_claude/server.py` (v1.9.4 → v1.10.0)
- `epics/ep_050_distribution_engine/implementation/operational_console_claude/test_console_server.py`

Destination Folder: `epics/ep_050_distribution_engine/implementation/`; this lifecycle record under `workstream/300_complete/`.

Dependency: Node 05 (met, pre-existing). No upstream/downstream contract change.

## Plan
- [x] 1. Prove the 403 was not transient, not config, not the key — before proposing any rewrite.
  - [x] Test: Isolation matrix — bogus key → different error (key is valid); CSE key on YouTube API
        → correctly blocked (restriction works); YouTube key on YouTube API → HTTP 200 (network and
        code path fine); alternate host and `/siterestrict` → identical 403; retest at +25min
        (not propagation); disable/re-enable → produced a *different* error (`SERVICE_DISABLED`),
        proving enablement worked and the refusal sat a layer above it.
  - [x] Evidence: Implementation Log, board post 20260819T110728303.
- [x] 2. Decisive test: brand-new, normally-created GCP project, API enabled, fresh unrestricted key.
  - [x] Test: Identical 403 → disproved the "auto-created project" hypothesis; refusal is not project-scoped.
  - [x] Evidence: Implementation Log.
- [x] 3. Confirm root cause against Google's own documentation rather than inference.
  - [x] Test: developers.google.com/custom-search/v1/overview states verbatim that the API is closed
        to new customers, with discontinuation 2027-01-01.
  - [x] Evidence: board post 20260819T114924665.
- [x] 4. Verify the replacement provider before building against it (the exact due-diligence step
      whose omission caused this incident).
  - [x] Test: Firecrawl CLI authenticated, 928/1000 credits; live search returned real results;
        probed the real POST /v2/search response shape rather than assuming it.
  - [x] Evidence: Implementation Log.
- [x] 5. Migrate `fetch_search_demand()` to Firecrawl; leave register()/validation/lineage/PII/
      idempotency completely untouched.
  - [x] Test: Live call returns 10 real UK results with a genuine HTTP 200 receipt.
  - [x] Evidence: Implementation Log.
- [x] 6. Fix geography ambiguity found during verification.
  - [x] Test: `build_search_query` unit tests incl. missing/empty/duplicate geography fields.
  - [x] Evidence: Implementation Log.
- [x] 7. Fix the latent demand-gate bug exposed by the first working fetch.
  - [x] Test: New regression test pinning the gate to the real record shape, both directions
        (10 real results → demand; genuinely empty → no demand).
  - [x] Evidence: Implementation Log.
- [x] 8. Make parking non-terminal so the four real parked candidates could be revived.
  - [x] Test: New test — park, retry while still blocked, assert retry is admitted (not 409),
        parks honestly again, records lineage, and never fabricates a signal.
  - [x] Evidence: Implementation Log.
- [x] 9. Full regression + live end-to-end on the four real candidates.
  - [x] Test: 650 passed; all four candidates proceed on real UK demand data.
  - [x] Evidence: Implementation Log.

## Evidence
Objective-Delivery-Coverage: 100% for the requested scope (Node 05 restored to working live search).
Auto-Acceptance: false (provider migration + a gate fix affecting candidate selection; verified live)
- Evidence-Type: manual_verification
  - Artifact: All four real candidates parked since 2026-08-18 (Greenwich, Lewisham, Charlton,
    Eltham) retried live and now proceed, each on 10 genuine UK results — e.g. Greenwich →
    `boilerrepairgreenwich.co.uk`, Charlton → `boiler-repairs-charlton.co.uk`, Eltham →
    `elthamplumber.co.uk`. Real HTTP 200 fetch receipts, real `.co.uk` SE-London engineers.
  - Objective-Proved: The provider migration works end to end against real live data, and the
    previously-stuck candidates are genuinely unblocked.
  - Status: captured
- Evidence-Type: test_output
  - Artifact: `pytest node_05/ -q` → 37/37; `pytest . -q --ignore=operational_console` → 650 passed.
  - Objective-Proved: No regression; new coverage for the gate bug, retry path, readiness, query
    construction, and fail-closed provider-error handling.
  - Status: captured

## Implementation Log
- 2026-08-19T10:25+01:00 — Retested yesterday's 403; still failing. Captured the response body the
  existing code discards: "This project does not have the access to Custom Search JSON API."
- 2026-08-19T10:44+01:00 — User confirmed the previously-flagged "open-web toggle" constraint was a
  red herring (Google deprecated that control). Retracted it on the board.
- 2026-08-19T10:49+01:00 — Declined gemini's dual-provider recommendation as premised on that
  retracted finding. **This was the wrong call** — see 11:49.
- 2026-08-19T11:07+01:00 — Ran the full isolation matrix; every layer under our control verified
  correct. Walked the user through disable/re-enable; the differential error proved enablement
  worked and the refusal was above it.
- 2026-08-19T11:35+01:00 — Decisive test: brand-new GCP project + fresh key → identical 403.
- 2026-08-19T11:49+01:00 — Confirmed via Google's own docs that the API is closed to new customers.
  Retracted my decline: gemini's conclusion (swap provider) was right, its premise wrong. Also
  established that its specific proposal (Bing) is itself dead — Microsoft retired the Bing Search
  API on 2025-08-11 — so building it as written would have been a second dead end.
- 2026-08-19T11:55+01:00 — Verified Firecrawl BEFORE building: CLI authenticated, credits available,
  live search real, and probed the actual API response shape.
- 2026-08-19T12:00+01:00 — Found during verification that `--country`/`--location` geo flags do NOT
  disambiguate an ambiguous place name: "restore hot water quickly Greenwich" returned Greenwich,
  CONNECTICUT despite UK targeting. Added `build_search_query()` carrying locality+region+country.
- 2026-08-19T12:05+01:00 — Migrated the provider; 37/37 node_05, 650 total.
- 2026-08-19T12:10+01:00 — First live run of the four real candidates returned `stopped_no_demand`
  for all four, contradicting a direct call that had just returned 10 results. Investigated rather
  than accepted it: the demand gate read a top-level `total_results` that has never existed on a
  DemandSignalRecord. Fixed, pinned with a regression test, reset the four wrongly-stopped runs
  (recording the correction in each run's own lineage), retried — all four now proceed.

## Changes Made
- `search_demand_discovery.py` v2.0.0: `fetch_search_demand()` now calls Firecrawl POST /v2/search;
  new `build_search_query()`; fail-closed handling of unsuccessful/malformed provider responses;
  `total_results` semantics changed (documented) with new `total_results_basis` field.
- `live_fetch.py` v1.3.0: new `http_post_json()` (also surfaces the error body that the existing
  helpers discard — recovering it during this outage required a throwaway script) and
  `resolve_firecrawl_credentials()` (env var first, Firecrawl CLI store as fallback).
- `server.py` v1.10.0: demand-gate fix; parked candidates retryable; Node 05 readiness resolves the
  real Firecrawl credential instead of checking dead Google env vars.
- Tests: Google fixture replaced with a verified Firecrawl-shaped one; +9 tests across the suites.

## Validation
- PASS — `pytest node_05/ -q` → 37/37.
- PASS — `pytest operational_console_claude/test_console_server.py -q` → 91.
- PASS — `pytest . -q --ignore=operational_console` → 650 passed.
- PASS — Live: four real candidates unparked and proceeding on genuine UK demand data.

## Risks/Notes
- **Credit ceiling.** Firecrawl is at 1,000 credits/cycle and each search costs ~2. Fine for
  development and modest live use, but it will NOT sustain the stated ambition of thousands of
  continuous campaigns — that needs a paid tier. Flagged to the user, not solved here.
- **`total_results` changed meaning.** Google reported an estimated corpus-wide match count;
  Firecrawl returns ranked results with no such estimate. It is now an honest count of results
  returned, with `total_results_basis` recording which meaning applies. Hence the major version bump.
- **Nodes 06-10 still use their original providers** and were not touched. It is NOT established
  that Firecrawl covers their sources (YouTube, Reddit, competitor pages, trends). Node 07 uses the
  YouTube Data API, which was verified working during this investigation (HTTP 200).
- **Root cause of the whole incident** was selecting a provider without checking it was open to new
  customers — the notice was on the same page as the API documentation. The verification step at
  Plan item 4 exists specifically so this is not repeated.
- The four candidates now proceed but have **not** been run through the rest of the pipeline; that
  is the natural next step and was not in scope here.

## Completion Status
Complete for the requested scope: Node 05 restored to genuine live search on a verified working
provider, the four real candidates unparked and proceeding on real data, and two latent bugs (demand
gate, terminal parking) found and fixed with regression coverage.
