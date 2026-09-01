# EP050 .env Loader — Add Repo-Root Search Path

Source: Direct user chat instruction (2026-08-18): "i am using .env file in
'C:\Users\edebe\eds\.env' instead" -- in response to the console live-fetch error, revealing the
user's real credential file is the repo-root `.env` (which already holds ELEVENLABS_API_KEY,
PEXELS_API_KEY, HERMES_GOOGLE_USER/PWD for other epics), not the EP050-specific file created
earlier this session.

Task Type: standard

Task Attributes:
- workflow_task: true
- workflow_name: "ep050_distribution_engine_delivery_20260816"
- workflow_stage: complete
- depends_on:
  - "shared/live_fetch.py's .env loader (met, v1.1.0, this session's own prior fix)"

Task Summary: `shared/live_fetch.py`'s `_load_dotenv_if_present()` (added earlier this session)
only ever read `epics/ep_050_distribution_engine/.env` -- it had no way to see the repo-root
`.env` the user is actually using. Extended it to check an ordered list of candidate paths
(`_dotenv_search_paths()`): repo-root `.env` first, then the EP050-specific one as a fallback,
first path wins per-key. Verified live by temporarily appending
`EP050_LIVE_FETCH_ENABLED=1` to the real root `.env`, confirming `/api/live_fetch_status`
reported `true`, then removing it again.

Context:
- `epics/ep_050_distribution_engine/implementation/shared/live_fetch.py` -- new
  `_dotenv_search_paths()`, `_load_dotenv_if_present()` now iterates it.
- `epics/ep_050_distribution_engine/implementation/shared/test_live_fetch.py` -- 1 new test.
- `C:\Users\edebe\eds\.env` -- confirmed to already hold real credentials for other epics
  (ElevenLabs, Pexels, Hermes' Google account), none of EP050's `EP050_*` vars yet.

Destination Folder: `epics/ep_050_distribution_engine/implementation/shared/`; this lifecycle
record under `workstream/300_complete/`.

Dependency: None beyond the already-completed v1.1.0 loader.

## Plan
- [x] 1. Confirmed the repo-root `.env` exists and is real (not empty/placeholder): 4 real
      credential keys, none EP050-specific yet.
  - [x] Test: Direct file read (keys only, values redacted in the log, not the file).
  - [x] Evidence: This Implementation Log.
- [x] 2. Extended `_load_dotenv_if_present()` with `_dotenv_search_paths()`: repo-root `.env`
      first, EP050-specific `.env` second, first-path-wins per key (matches the existing
      never-override-a-real-env-var rule).
  - [x] Test: `pytest shared -v` -- 23/23 passing, including the new
        `test_dotenv_search_paths_checks_repo_root_before_ep050_specific_file`.
  - [x] Evidence: `shared/live_fetch.py`, `shared/test_live_fetch.py`.
- [x] 3. Verified live against the real files, not just unit tests: appended
      `EP050_LIVE_FETCH_ENABLED=1` to the actual root `.env`, restarted the real running console
      server, confirmed `GET /api/live_fetch_status` reported `true`. Removed the line, restarted
      again to confirm it reverted to the safe default.
  - [x] Test: Direct HTTP response inspection via the Browser pane, both states.
  - [x] Evidence: This Implementation Log.
- [x] 4. Ran the fuller regression to confirm zero breakage.
  - [x] Test: `pytest shared node_01..node_10 operational_console_claude -q` -- 380 passed, 1
        transient Windows file-lock error on an unrelated test (same class of flakiness
        documented repeatedly this session, not caused by this change).
  - [x] Evidence: This Implementation Log.

## Evidence
Objective-Delivery-Coverage: 100% for the scope (extend the search path; both files now work)
Auto-Acceptance: false (live-fetch infrastructure change; verification requested in chat)
- Evidence-Type: test_output
  - Artifact: `pytest shared -v` -- 23/23; `pytest shared node_01..node_10
    operational_console_claude -q` -- 380/381 (1 transient, unrelated).
  - Objective-Proved: The extended search order works correctly and introduces zero regressions.
  - Status: captured
- Evidence-Type: manual_verification
  - Artifact: Live browser session against the real running console -- flipped the flag in the
    real repo-root `.env`, confirmed the real server picked it up via `/api/live_fetch_status`,
    then reverted.
  - Objective-Proved: The fix works against the user's actual credential file, not just a
    simulated one.
  - Status: captured

## Implementation Log
- 2026-08-18T12:30+01:00 -- User: "i am using .env file in 'C:\Users\edebe\eds\.env' instead".
  Checked the file directly: real, holds ELEVENLABS_API_KEY/PEXELS_API_KEY/HERMES_GOOGLE_USER/
  HERMES_GOOGLE_PWD, no EP050_* keys yet. Confirmed `shared/live_fetch.py`'s existing loader
  never looked at this path.
- 2026-08-18T12:33+01:00 -- Added `_dotenv_search_paths()` (repo-root first, EP050-specific
  second), updated `_load_dotenv_if_present()` to iterate it. Verified path resolution directly
  (`parents[4]` -> repo root, `parents[2]` -> `epics/ep_050_distribution_engine`).
- 2026-08-18T12:35+01:00 -- Added a test for the new search-path function. Full `shared` suite:
  23/23 passing.
- 2026-08-18T12:38+01:00 -- Verified live against the real root `.env`: appended the flag,
  restarted the real console server, confirmed `/api/live_fetch_status` reported `true`, removed
  the line, restarted again, confirmed it reverted.
- 2026-08-18T12:42+01:00 -- Ran the fuller regression: 380 passed, 1 transient unrelated error.
- 2026-08-18T12:45+01:00 -- Filed this lifecycle record.

## Changes Made
- Edited `epics/ep_050_distribution_engine/implementation/shared/live_fetch.py` (v1.1.0 ->
  v1.2.0): `_dotenv_search_paths()`, `_load_dotenv_if_present()` updated to iterate it.
- Edited `epics/ep_050_distribution_engine/implementation/shared/test_live_fetch.py` (v1.0.0 ->
  v1.1.0): 1 new test.
- `C:\Users\edebe\eds\.env` -- temporarily modified for live verification, then restored to its
  exact prior state (the four pre-existing credential lines, unchanged).

## Validation
- PASS -- `pytest shared -v` -- 23/23.
- PASS -- `pytest shared node_01..node_10 operational_console_claude -q` -- 380/381 (1 transient,
  independently known flaky, unrelated to this change).
- PASS -- Live round-trip against the real root `.env`: flag set -> server picked it up -> flag
  removed -> server reverted to disabled.

## Risks/Notes
- **Both .env files are now live search targets.** If the same key is ever set differently in
  both files, the repo-root one silently wins (first-path-wins) with no warning. Not expected to
  matter in practice since the EP050-specific file's EP050_LIVE_FETCH_ENABLED is still `0` and
  its credential fields are still blank, but worth knowing if both ever get filled in
  independently.
- **The user still needs to add the actual EP050_* keys to the root `.env`** for anything to
  change functionally -- this task only fixed where the loader looks, not what's in the file yet.

## Completion Status
Complete. Verification requested in chat immediately after this task's summary.
