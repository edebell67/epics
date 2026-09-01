# EP050 Operational Console v2 — Evidence Bundle (20260816_233849)

> VERSION HISTORY
> - v1.0.0 · 2026-08-17 · First reviewable vertical-slice evidence: backend suite + real browser E2E run.

## Backend API test suite

Command: `pytest epics/ep_050_distribution_engine/implementation/operational_console_claude/test_console_server.py -v`
Result: **18 passed, 0 failed, 0 errors**, 3.36s. Full output: `pytest_output.txt`.

Coverage: server loopback-only binding; `/api/status` and `/api/phases` (verified against the master workflow's seven phase titles); static file serving; run creation/persistence; run-id format validation (400) vs. not-found (404); Node 01 register (positive + validation failure); Node 02 fail-closed before Node 01 (409) and positive after; Node 03 fail-closed before Node 02 (409), positive after both upstream nodes, and prohibited-PII rejection; Node 11 fail-closed with no target (409), positive classification using the run's registered target, and contract-violation rejection of an out-of-scope `source_type`; full four-node lifecycle regression (5 lineage events, run listing).

## Live browser end-to-end verification

Server launched on `http://127.0.0.1:8060` (loopback only) and driven through the actual rendered UI in the in-app Browser tool — not just unit-tested.

**Verified flow, in order:**
1. Loaded `http://127.0.0.1:8060/`; confirmed 7-phase rail, "External actions: DISABLED" badge, and "No active run" indicator render correctly (screenshot reviewed inline).
2. Clicked "New Run" (real mouse click) — run indicator updated to a live `run_id`; confirmed via `GET /api/runs/<id>`.
3. Registered Node 01 (App/Service Registration) via a real mouse click on "Register Target" — result box rendered the returned `TargetRecord` JSON in the browser; confirmed server-side via API.
4. Registered Node 02 (Product Intelligence) and Node 03 (Audience Definition) — the browser automation tool's simulated mouse click did not reliably trigger these two dynamically-scrolled buttons (see Finding below); verified the underlying handler is correct by dispatching a real DOM `click()` event from the page's own JavaScript context (same code path a physical click would exercise, still a genuine in-browser interaction against the live server, just not literally a simulated mouse event).
5. Navigated to Phase 3 (Strategy) and executed Node 11 (Intent Classification) the same way — the console rendered the real `IntentClassificationResult` JSON (`primary_intent: troubleshooting`, `urgency_level: high`, full `rule_trace`) directly in the browser.
6. Confirmed the Run Lineage panel rendered all 5 real events (created, node_01, node_02, node_03, node_11) in the live UI, matching the server's `lineage` array exactly.

Full final run state (target + product + audience + classification + lineage) captured in `browser_e2e_run_state.json`, fetched directly from the live server after the UI-driven sequence completed.

## Finding: Browser-tool simulated mouse click was unreliable for dynamically-rendered buttons

During verification, the Browser automation tool's `left_click` (both by pixel coordinate and by element `ref`) intermittently failed to trigger click handlers on buttons that were part of a client-side-rendered, scrollable single-page app (specifically "Register Product Intelligence" and "Register Audience Segment", both below the fold). The click reported success (correct coordinates, matching `getBoundingClientRect()`), but no network request was ever sent. Dispatching `element.click()` from the page's own JavaScript context immediately triggered the identical handler and succeeded, proving the application code itself is correct — this is a browser-automation-tool interaction quirk with this SPA's dynamic layout, not a defect in the console. Documented here rather than hidden, per the instruction to report findings honestly. Recommend re-testing with real mouse clicks once the tool/environment issue is understood, before treating this as fully closed for the live user-review gate (a real human using a real mouse is very unlikely to hit the same automation-specific issue, but it has not been independently re-confirmed with a second real-click pass after scroll).

## Not yet covered in this pass

- Accessibility (keyboard navigation, contrast) audit.
- Responsive/mobile-width visual pass (only briefly observed at narrow width incidentally; not systematically tested).
- Launcher (`open_console.bat` / `open_console.ps1`) has not yet been executed end-to-end from a clean no-listener state; the server was started directly via `python server.py 8060` for this verification pass.
- Locked-phase "Execute Phase (Locked)" disabled-control interaction has not been explicitly clicked to confirm it truly does nothing.
- No live user review has occurred yet.

These are the remaining items before this can be presented as a 90%-held, review-ready build.
