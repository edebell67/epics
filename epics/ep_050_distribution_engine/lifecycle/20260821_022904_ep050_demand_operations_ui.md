# EP050 Demand Operations UI

## Plan — 2026-08-21 02:29

Replace the node-first console shell with a portfolio-first demand-operations interface while preserving every existing API, node form, live-fetch control, external authorization gate, EP048 render/YouTube integration, public intake route, lineage surface, and fail-closed server behaviour.

All implementation artefacts remain inside `epics/ep_050_distribution_engine` as requested.

## Scope

- Market Radar backed by `/api/campaign_queue`.
- Opportunity, campaign, production, lead, winner and exception workspaces.
- Bulk eligible campaign execution through the existing headless endpoint.
- Drill-through to the existing 37-node controls.
- Preserve CSV import, live-fetch approvals, EP048 render/upload confirmation and public intake.
- Desktop/mobile QA and existing regression suite.

## Status

Implementation complete.

## Implementation — 2026-08-21

- Added `implementation/operational_console_claude/demand-operations.html` as the default console shell.
- Added isolated `demand-operations.css` and `demand-operations.js` assets, leaving the original console assets intact.
- Added Market Radar, opportunity, campaign, asset-production, lead-exchange, winner-replication and exception workspaces.
- Portfolio counts, rows, phases, node positions and next actions come from the existing real `/api/campaign_queue` response.
- Added per-campaign drill-through, real headless pipeline execution, persistent Phase 2 live-fetch approval, real consumer intake links and bulk eligible execution.
- Preserved all 37 original node panels under Advanced controls.
- Preserved the existing Node 18 explicit confirmation control for the real EP048 render plus real YouTube upload; the new portfolio layer cannot call it silently.
- Added an integrity warning when a stored `winner_detected` state conflicts with the server-derived current phase/action instead of presenting the contradiction as a valid winner.
- Updated the server root and `/console.html` to serve the new shell and registered the two new static assets.

## Validation — 2026-08-21

- `python -m py_compile server.py` — passed.
- `node --check demand-operations.js` — passed.
- `node --check console.js` — passed.
- `python -m pytest test_console_server.py -q` — 104 passed; one non-functional pytest cache warning because the cache directory was not writable.
- Browser QA against an isolated server on port 8061 — passed: 7 real campaigns rendered, 10 original navigation controls rendered, no console warnings/errors, no horizontal overflow.
- Advanced-control QA — passed: Phase 1 form rendered; Node 18 real render/upload label and mandatory confirmation control remained present.
- Mobile QA at 390×844 — passed with no horizontal document overflow.
