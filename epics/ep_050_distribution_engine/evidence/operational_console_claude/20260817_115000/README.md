# EP050 Operational Console v2 — Evidence Bundle (20260817_115000)

> VERSION HISTORY
> - v1.0.0 · 2026-08-17 · CHANGE REQUIRED fix evidence: five-state phase reconciliation, per board event 20260817T113648989_codex_781e7f99.

**Command:**
```
python -m pytest epics/ep_050_distribution_engine/implementation/operational_console_claude/test_console_server.py -v --basetemp=<scratchpad>/pytest_tmp_console_final2
```

**Result:** 28 passed, 0 failed, 0 errors, 5.60s (26 pre-existing + 2 net new after replacing 1 stale assertion test with 3 new ones). Full output in `pytest_output.txt`.

**What was wrong:** `server.py`'s `PHASES` constant used a binary `implemented_nodes`/`locked_nodes` model. Any accepted-but-unwired node (Nodes 05-10 in Phase 2, Node 04 in Phase 1, Node 19 in Phase 4, Nodes 20/21/26 in Phase 5) was rendered as "Not Implemented / Locked" — false, since all of these are accepted EP050 implementations at 100%, just without a dedicated console control.

**Fix:** Replaced the binary with five explicit, mutually exclusive states per node, reconciled against direct board/workstream evidence inspection at fix time:
- `accepted_nodes` — EP050-accepted at 100% (board evidence)
- `console_controls` — subset of `accepted_nodes` wired as an executable control in this console
- `pending_acceptance_nodes` — evidenced but not yet accepted (Node 27, blocked on an Obsidian-mirror authorization gate at the time of writing)
- `mvp_deferred_nodes` — explicitly deferred under the approved MVP classification (Nodes 22-25), never implemented, never claimed complete
- `not_started_nodes` — no allocation or work begun (Nodes 28-37)

**New/changed test coverage (3 tests replacing 1 stale one):**
- `test_phases_endpoint_reports_node15_18_as_console_controls` — Phase 3/4 accepted_nodes vs console_controls now correctly distinguished (Node 19 accepted but not a console control).
- `test_phases_endpoint_does_not_falsely_report_accepted_nodes_as_not_implemented` — the direct regression proof for this fix: Phase 2 accepted_nodes = Nodes 05-10, console_controls = []; Phase 5 shows the mixed accepted/pending/deferred state accurately.
- `test_phases_endpoint_every_node_in_range_is_classified_exactly_once` — structural invariant: every node 01-37 appears in exactly one of the five state lists per phase, and `console_controls` is always a subset of `accepted_nodes`.

**Real browser E2E:** stopped the previous live server, restarted with the reconciled code, and visually confirmed:
1. Phase rail subtitle text now reads e.g. "Operable: Node 01, 02, 03 · Accepted, not wired: Node 04" (Phase 1) and "Accepted, not wired: Node 05, 06, 07, 08, 09, 10" (Phase 2, blue, not red/locked).
2. Phase 2's generic panel body lists Nodes 05-10 under "Accepted EP050 implementation, not yet wired as a console control:" instead of "Not Implemented / Locked".
3. Phase 5's generic panel body correctly separates its three sub-states: accepted-unwired (20/21/26), pending acceptance (27), and MVP-deferred (22-25).
4. Phase 1's Node 04 block renders with the new `.node-block--accepted-unwired` style (blue), text: "Accepted (EP050 100%) — not yet wired as a console control."
5. No regression: registered a Node 01 target through the live UI post-change and confirmed the real `tgt_boiler_repair_blackheath` record still returns correctly.
6. Zero browser console errors throughout.

**External side effects:** none. No network call, no live data, no publishing/routing/rendering/deployment/PII, no actual video rendering. Held at evidenced 90%, pending live user review, as before — this pass corrects accuracy, it does not claim new completion.
