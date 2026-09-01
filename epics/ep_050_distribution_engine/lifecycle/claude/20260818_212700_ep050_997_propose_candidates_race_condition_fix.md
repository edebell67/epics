# EP050 — Fixed Race Condition in propose_candidates

Source: Live production use immediately after the winner-replication build shipped. Real user
click of "Propose one-hop candidate campaigns" against the live run produced 16 candidates instead
of 8, plus one orphaned run. User asked to clean up, then explicitly asked to fix the underlying
race condition ("yes, fix the race condition now").

Task Type: standard

Task Attributes:
- workflow_task: true
- workflow_name: "ep050_distribution_engine_delivery_20260816"
- workflow_stage: complete
- depends_on:
  - "20260818_200000_ep050_997_winner_replication_and_scale_out.md (the feature this bug was found in)"

Task Summary: `handle_node01_propose_candidates` did load_run_meta -> check
`last_proposed_winner_id` -> create candidates -> save_run_meta as four separate steps against a
plain JSON file, with no locking. Two near-simultaneous real requests for the same run both read
"not yet proposed" before either had saved, so both proceeded -- producing double the candidates
plus an orphaned run whose Node 01 registration didn't finish before a racing request interleaved.
Fixed with a single global `threading.Lock` around the whole function. Verified the fix is real by
temporarily removing the lock and confirming the new regression test reliably fails (reproduced
both the 16-candidate duplication and a Windows file-write collision) before confirming 5/5 clean
passes with the lock restored.

Context:
- `epics/ep_050_distribution_engine/implementation/operational_console_claude/server.py` (v1.9.0 -> v1.9.1)
- `epics/ep_050_distribution_engine/implementation/operational_console_claude/test_console_server.py`

Destination Folder: `epics/ep_050_distribution_engine/implementation/operational_console_claude/`; this lifecycle record under `workstream/300_complete/`.

Dependency: The winner-replication build (met, shipped earlier this session).

## Plan
- [x] 1. Diagnosed the real bug from live output: traced the "8 candidates" the user saw against
      Campaign Queue's actual state (only 1 campaign), found the timestamp match to my own earlier
      cleanup, then had the user re-trigger it for real and observed 16 candidates + 1 orphan.
  - [x] Test: Direct inspection of `data/runs/` on disk and `GET /api/campaign_queue`.
  - [x] Evidence: Implementation Log.
- [x] 2. Cleaned up the 7 duplicate runs and 1 orphaned run, leaving the correct 8.
  - [x] Test: `GET /api/campaign_queue` shows exactly 9 campaigns (1 source + 8 candidates), no orphan.
  - [x] Evidence: Implementation Log.
- [x] 3. Fixed the race with `_PROPOSE_CANDIDATES_LOCK` (global `threading.Lock`).
  - [x] Test: New `test_node01_propose_candidates_concurrent_calls_never_duplicate` (5 concurrent
        real HTTP requests, asserts exactly 8 created total, no orphaned targets).
  - [x] Evidence: Implementation Log; verified the test fails reliably without the lock (3/3 runs)
        before confirming it passes reliably with the lock (5/5 runs).
- [x] 4. Full regression pass.
  - [x] Test: `pytest test_console_server.py -q` -- 81/81.
  - [x] Evidence: Implementation Log.

## Evidence
Objective-Delivery-Coverage: 100% for the identified race condition.
Auto-Acceptance: false (data-integrity bug fix on a just-shipped feature; user directly involved
in discovery and requested the fix)
- Evidence-Type: manual_verification
  - Artifact: Real live click produced 16 candidates + 1 orphan on `run_20260818_102850_a3e4d29f`;
    cleaned up to the correct 8; re-verified via `GET /api/campaign_queue`.
  - Objective-Proved: The bug was real, not hypothetical, and the cleanup restored correct state.
  - Status: captured
- Evidence-Type: test_output
  - Artifact: New concurrency test fails 3/3 without the lock (16 or 40 duplicates, or a Windows
    file-write collision depending on thread interleaving) and passes 5/5 with it. Full suite
    81/81 passing after the fix.
  - Objective-Proved: The lock actually closes the race, not just theoretically.
  - Status: captured

## Implementation Log
- 2026-08-18T20:34+01:00 (UTC 18:34, per the run lineage) -- My own earlier live-verification
  click of propose_candidates against the real run, later cleaned up.
- 2026-08-18T21:12+01:00 -- User shared a screenshot; I misread the historical lineage entry from
  the event above as a new real action -- corrected once I checked disk state directly.
- 2026-08-18T21:14+01:00 -- User asked for the real 8 candidates; re-triggered the action for
  real via the console -- produced 16 candidates + 1 orphan due to a genuine race (my click and
  the user's near-simultaneous interaction both hit the server within the same second).
- 2026-08-18T21:16+01:00 -- Diagnosed and reported the race to the user; user confirmed cleanup.
- 2026-08-18T21:17+01:00 -- Cleaned up 7 duplicates + 1 orphan, verified exactly 9 campaigns remain.
- 2026-08-18T21:20+01:00 -- User asked to fix the race condition. Added `threading` import and
  `_PROPOSE_CANDIDATES_LOCK`, wrapped the function body.
- 2026-08-18T21:24+01:00 -- Added the concurrency regression test; verified it fails reliably
  without the lock (temporarily neutered it, ran 3x, all failed) before confirming 5/5 clean
  passes with the real lock restored.
- 2026-08-18T21:27+01:00 -- Full regression (81/81), version bump (server.py v1.9.1), restarted
  the dev server clean, filed this record.

## Changes Made
- Edited `epics/ep_050_distribution_engine/implementation/operational_console_claude/server.py`
  (v1.9.0 -> v1.9.1): added `import threading`, `_PROPOSE_CANDIDATES_LOCK`, wrapped
  `handle_node01_propose_candidates`'s body in `with _PROPOSE_CANDIDATES_LOCK:`.
- Edited `epics/ep_050_distribution_engine/implementation/operational_console_claude/test_console_server.py`:
  added `test_node01_propose_candidates_concurrent_calls_never_duplicate`.
- Deleted 8 real duplicate/orphaned run directories from
  `epics/ep_050_distribution_engine/implementation/operational_console_claude/data/runs/`
  (produced by the bug, not test fixtures).

## Validation
- PASS -- `pytest test_console_server.py -q` -- 81/81.
- PASS -- New test confirmed meaningful: fails 3/3 without the fix, passes 5/5 with it.
- PASS -- Live console state verified correct (9 campaigns, no orphan) after cleanup.

## Risks/Notes
- **Scope of the fix is deliberately narrow.** Every other handler in this file does the same
  load-mutate-save pattern without locking, so the same class of race technically exists anywhere
  two concurrent requests could touch the same run's `run.json`. This fix addresses the one
  identified and reproduced instance (`propose_candidates`, the only action that both mints new
  runs AND has an idempotency check to race around) rather than locking every handler pre-emptively
  -- that would be a much larger, untested change beyond what was found or asked for.
- A single global lock (not a per-run lock) was a deliberate choice for this local,
  single-operator console -- correct here, would need revisiting if this code were ever adapted
  for genuine multi-operator concurrent use.

## Completion Status
Complete. Real bug found live, fixed, verified both ways (fails without the fix, passes with it),
full regression clean, live console state restored to correct.
