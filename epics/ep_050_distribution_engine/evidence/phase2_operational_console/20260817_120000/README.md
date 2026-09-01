# EP050 Phase 2 Operational Console — Evidence Bundle (20260817_120000)

> VERSION HISTORY
> - v1.0.0 · 2026-08-17 · Evidence for the URGENT ALLOCATION (board event 20260817T122525918_codex_phase2ops): real operational controls for Nodes 04-10, replacing the status-only Phase 2 panel the user's live review rejected.

**Command:**
```
python -m pytest epics/ep_050_distribution_engine/implementation/operational_console_claude/test_console_server.py -v --basetemp=<scratchpad>/pytest_tmp_console_final3
```

**Result:** 43 passed, 0 failed, 0 errors, 8.33s (28 pre-existing + 15 new: 2 tests per Node04-10 [positive + fail-closed-before-prerequisite] plus one full-chain helper test). Full output in `pytest_output.txt`.

**What was built:** each of Node 04 (Conversion Definition), Node 05 (Search Demand Discovery), Node 06 (Question Discovery), Node 07 (Social/Video Discovery), Node 08 (Competitor Intelligence), Node 09 (Community Intelligence), and Node 10 (Trend Detection) now has a real form in the console, posting to a real `server.py` handler that instantiates the actual registry class for that node (not a stub, not a status link), with the same fail-closed upstream-lineage checks each node's own contract already requires. `PHASES` was updated so all seven nodes moved from "accepted, not wired" into `console_controls`.

**Bug found and fixed during first test run:** Node 04's handler didn't default `success_criteria`, so the first `test_node04_register_positive_uses_master_spec_funnel` run failed with a 400 (`ValidationError: success_criteria is required`). Fixed by defaulting it server-side to the master-spec worked example, matching the pattern already used for `stages`/`allowed_transitions`/`success_stage_id`. Re-ran: 43/43 passed clean.

**Real browser E2E — full Node 01-10 chain driven live** (server restarted with the updated code first, confirmed via `/api/status`):
1. New Run → Register Target (Node 01) → Register Product Intelligence (Node 02) → Register Audience Segment (Node 03) → Define Conversion Funnel (Node 04). Confirmed via `GET /api/runs/<id>`: `target`, `product`, `audience`, and `conversion` all populated, 5 lineage events.
2. Switched to the new Phase 2 panel (rail badge: "Operable: Node 05, 06, 07, 08, 09, 10", green). Clicked Record Demand Signal (Node 05) → Record Question (Node 06) → Record Social/Video Signal (Node 07) → Record Competitor Signal (Node 08) → Record Community Signal (Node 09) → Detect Trend (Node 10), in order.
3. Confirmed via `GET /api/runs/<id>`: `demand_signals`, `questions`, `social_video_signals`, `competitor_signals`, `community_signals`, `trends` each populated with 1 real record; 11 total lineage events (created + node01-10). The trend record's computed `direction`/`spike_flag`/`confidence` (`"up"`, `true`, `1.0`) matched hand-calculated expected values.
4. Zero browser console errors throughout.

**Restart/reload persistence check:** stopped the running server process, restarted it fresh, and re-fetched the same run via `GET /api/runs/<id>` — all data (target, demand_signals, trends, 11 lineage events) survived unchanged, confirming the JSON-file-backed storage model persists correctly across a full process restart, not just a page reload.

**Accessibility/contrast spot-check:** no `outline: none` anywhere in `console.css` (native focus rings preserved); every new input uses the existing accessible `<label>`-wrapped `field()` helper (103 total `field()` calls across the file); spot-checked computed contrast on a new Phase 2 submit button (`rgb(20,32,26)` text on `rgb(255,255,255)` background, ~16:1 ratio) to guard against the invisible-text class of bug found elsewhere in the EP050 workflow maps.

**No-network check:** `grep` across `console.html`/`console.js`/`console.css` for `http://`, `https://`, `cdn.` returns zero matches — no external resource is referenced anywhere in the frontend. Combined with the existing pytest no-network assertions (monkeypatched `socket.socket`) on the registration paths.

**External side effects:** none. No network call beyond loopback, no live data, no publishing/routing/deployment/PII, no actual video rendering. Held at evidenced 90%, requesting user acceptance — this pass adds real functionality, it is not self-marked 100%.
