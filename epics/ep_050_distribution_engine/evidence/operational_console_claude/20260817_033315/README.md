# EP050 Operational Console v2 — Evidence Bundle (20260817_033315)

> VERSION HISTORY
> - v1.0.0 · 2026-08-17 · Closes the three gaps left open in the 20260816_233849 bundle: launcher, button-click retest, locked-control inertness.

## Launcher: verified working

`open_console.bat` was tested by killing any process on port 8060, then launching the batch file the way a real user launch would happen (`Start-Process` on the `.bat` file, not a nested shell invocation). Result: the server came up and `GET /api/status` returned 200 within seconds — the persistent-window + readiness-poll pattern works correctly.

**Process note:** two earlier attempts to invoke the launcher via a bash-wrapped `cmd.exe /c open_console.bat` returned instantly with no server running and no readiness output. Isolated the cause: it was an artifact of nested shell quoting/execution context in that specific test harness, not a defect in the launcher — confirmed by (a) testing `open_console.ps1` directly against a dead port, which correctly reported "did not become ready" and exited 1, proving the readiness-poll logic itself is correct, and (b) launching the exact same `start "..." cmd /k python server.py PORT` pattern directly, which kept the server alive. The final `Start-Process`-based test, which is the closest available approximation to a real double-click, passed cleanly.

## Button-click retest: both flaky buttons now confirmed working

Re-ran the full flow with a fresh run (`run_20260817_033136_bc08fbba`) using only real simulated mouse clicks (no JS-dispatched `.click()` this time), adding a short `wait` after each scroll before clicking. Both "Register Product Intelligence" and "Register Audience Segment" fired correctly on the first click attempt this time. Root cause of the earlier flakiness: clicking immediately after a scroll action, before layout/paint settled — a timing race in the test interaction, not an application defect. Confirmed via `read_network_requests`: real `POST .../node02` and `POST .../node03` calls were sent and returned 200. Full resulting run state: `browser_e2e_retest_run_state.json` — 4 lineage events (created, node_01, node_02, node_03).

## Locked-phase control confirmed inert

Programmatically inspected the Phase 2 "Execute Phase (Locked)" control: `disabled === true` and no click handler is attached (`onclick === null`). A disabled native `<button>` cannot dispatch a click event in any browser, and even if it could, there is no handler to call. This is structural inertness, not merely a visual/CSS disabled state.

## Updated status

All items from the prior evidence bundle's "Not yet covered" list are now closed except the systematic accessibility/responsive audit (spot-checked: semantic `<label>`/`<button>`/`<input>` throughout, no `outline:none`, native focus order — not exhaustively audited with a dedicated tool) and the live user review itself, which is the final required gate per the hard user-acceptance decision on this allocation.
