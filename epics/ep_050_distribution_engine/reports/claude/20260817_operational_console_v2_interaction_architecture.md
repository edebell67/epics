# EP050 Operational Console v2 — Interaction Architecture

> VERSION HISTORY
> - v1.3.0 · 2026-08-17 · URGENT ALLOCATION addendum (see bottom section): real operational controls for Node 04-10, replacing the status-only Phase 2 the user's live review rejected.
> - v1.2.0 · 2026-08-17 · CHANGE REQUIRED fix addendum (see bottom section): five-state phase reconciliation, replacing a misleading locked-vs-operable binary.
> - v1.1.0 · 2026-08-17 · Reactivation addendum: Node 15/16/18 wiring (see bottom section). Checklist/workflow docs updated before code, per the process-deviation lesson from the initial pass.
> - v1.0.0 · 2026-08-17 · Initial architecture document.

**Process note (honest ordering):** the allocation (`20260817T001150693_codex_cd0dd339`) asks for this document and the dedicated pre-code interactive workflow HTML before code. In practice, the first implementation pass (`server.py`, `console.html/css/js`) was written first, in order to discover Gemini's real Node 11 API surface (`classify_demand_signal`) by reading its source rather than guessing a contract. This document and the accompanying workflow HTML are being delivered now, before requesting the 90% live-review gate, and describe the architecture as actually built and verified — not backdated to claim a chronology that didn't happen.

## Source basis

- Topology: `workstream/600_workflow/ep050/EP050_distribution_engine_master_workflow.html` — seven phases, Nodes 01–37.
- Functional requirements: `epics/ep_050_distribution_engine/distribution_engine_master_spec.md`.
- Implemented node contracts (read directly, not guessed): `implementation/node_01/registration.py`, `node_02/product_intelligence.py`, `node_03/audience_definition.py`, `node_11/intent_classification.py`.

## Shell

- **Top bar**: brand mark, run indicator (`No active run` / `Run: <run_id>`), "New Run" action, a permanently visible "External actions: DISABLED" badge (not conditional — there is no code path that could enable it).
- **Phase rail** (left): one entry per master-workflow phase (1–7) plus a secondary "Delivery Status (historical)" entry. Each entry's operable/locked state is derived from `/api/phases`, which lists `implemented_nodes` per phase — never hardcoded per-phase text that could drift from reality.
- **Stage** (center): one panel per phase, toggled by CSS class, never by re-fetching/re-rendering DOM per navigation (cheap, avoids flicker, but means all seven panels exist in the DOM at once — a plain 7-phase build, not a virtualized router, since the node count here is small).
- **Lineage** (right, sticky): renders the active run's `lineage` array verbatim from the server, newest first. This is the audit trail requirement — local-only, no external system involved.

## Run model

A **run** is one operator session working the pipeline for one target. `POST /api/runs` creates `data/runs/<run_id>/` containing `run.json` (metadata + lineage) plus one JSON-file-backed registry per implemented node, each instantiated from the *real* Node 01/02/03 registry classes pointed at that run's own directory — not a reimplementation of their storage logic.

Each node-adapter route (`/api/runs/<id>/node01`, `node02`, `node03`, `node11/classify`) is fail-closed in the same way its underlying node already is: Node 02 refuses without a Node 01 target in the run, Node 03 refuses without both, Node 11 refuses without a target_id (either the run's own or an explicit one in the request body). Every successful call appends one lineage entry; nothing is written on failure.

## Phase panels

- **Phase 1 (Ingestion)**: bespoke panel, three live node blocks (01/02/03) each with a form pre-filled with the confirmed synthetic fixture values, a submit button, and a result box that renders the raw JSON response (success in green, error in red) — so the operator sees exactly what the node returned, not a paraphrase. Node 04 renders as an explicit locked block with a truthful reason string.
- **Phase 3 (Strategy)**: bespoke panel, one live node block (11) with a demand-signal fixture form; Nodes 12–15 render as locked blocks.
- **Phases 2, 4, 5, 6, 7**: fully generic locked-phase rendering, driven entirely by `/api/phases` data (`locked_nodes` list) — adding a new implemented node to any phase only requires updating the phase's `implemented_nodes`/`locked_nodes` arrays and, if it needs a form, one new panel-building function; the generic locked-phase path needs no code change.
- **Delivery Status (secondary)**: a short static note pointing at the existing checklist/report trail and at Gemini's frozen prior console, explicitly kept secondary per the allocation ("preserve a separate Delivery Status view only as secondary information").

## Safety boundary

No code path in `server.py` makes an outbound network call, imports a requests/http-client library for external use, or references a production connection string. `ThreadingHTTPServer` binds `127.0.0.1` only (asserted in the test suite). External-action affordances (publish/route/pay/deploy) are not present as functional controls anywhere in the UI — the top-bar badge communicates this as a standing property of the build, not a per-action toggle a future change could silently flip.

## Known gap at time of writing

The Browser automation tool's simulated mouse click was unreliable against two dynamically-scrolled buttons during verification (documented in `evidence/operational_console_claude/20260816_233849/README.md`). The application code itself was confirmed correct via direct DOM dispatch. This is being retested with careful real-mouse interaction in this same session before the live-review gate is requested.

## Reactivation addendum (2026-08-17T10:34-10:44+01:00) — Node 15/16/18

Per allocation `20260817T095239426_codex_f21198e1`, activated only after Node 15 and Node 18 both reached accepted 100%. Scope: expose the two newly-accepted nodes in the console without touching anything else.

- **Node 12/13/14 are exercised for real but have no dedicated form.** `_pipeline_from_classification()` in `server.py` calls the real `score_demand_opportunity` → `discover_demand_path` → `select_channel_placements` chain using each module's own deterministic default weights/candidates. This is safe to recompute on demand (rather than persisting separate pipeline state) because the same classification always produces the same `opportunity_id`/`path_id`/`selection_id` and content — these IDs are pure hash functions of upstream lineage, not randomized.
- **Phase 3** gained one new node block: **Node 15** ("Generate Campaign Cluster(s)"), which runs the pipeline above over every classification in the run and clusters the results.
- **Phase 4**, previously fully locked, gained two new node blocks: **Node 16** ("Register Canonical Fact", a plain form) and **Node 18** ("Generate Video Asset"), which internally calls Node 17 (`generate_asset_payload`) to build the underlying asset before Node 18 assembles the script/storyboard/shot-list/caption/branding/CTA/render-manifest package. Node 19 remains an explicit locked block.
- The Node 18 form's cluster dropdown and fact multi-select are populated live from the run's actual state (`refreshNode18Selectors()`, called after every `refreshRun()`), not a static list — confirmed in browser E2E to update immediately after registering a fact or generating a cluster.
- `/api/phases` completion was recalculated from real child evidence, not adjusted by hand: Phase 3 `implemented_nodes=[11,12,13,14,15]`/`locked_nodes=[]`; Phase 4 `implemented_nodes=[16,17,18]`/`locked_nodes=[19]`.
- A stale server process from an earlier session was found still listening on :8060, running pre-reactivation code. It was stopped and a fresh instance started before any browser verification in this pass, so no verification was accidentally run against stale code.
- Backend suite extended to 26/26 passing (18 pre-existing + 8 new). Full extended chain re-verified live: New Run → Node 01 → Node 11 → Node 15 → Node 16 → Node 18, 6 real lineage events, no console errors, locked-node inertness (Node 04/19) re-confirmed programmatically, mobile-width (375px) responsive check performed.
- Held at evidenced 90%, pending live user-review acceptance, per Codex's explicit instruction — the same gate this task has always required.

## CHANGE REQUIRED fix addendum (2026-08-17T11:44-11:55+01:00) — five-state phase reconciliation

Board event `20260817T113648989_codex_781e7f99` found that Phase 2 (`console.js`'s generic locked-phase path) rendered Nodes 05-10 as "Not Implemented / Locked" when they are accepted EP050 implementation at 100% — simply not wired as console controls. The same false-negative risk existed for Phase 1's Node 04, Phase 4's Node 19, and Phase 5's Nodes 20/21/26 (accepted) vs 27 (pending) vs 22-25 (MVP-deferred).

**Root cause:** `PHASES` used a binary `implemented_nodes`/`locked_nodes` model that conflated "not accepted" with "accepted but no console control exists" — two entirely different facts.

**Fix:** Verified accepted-node status directly against board/workstream evidence for all 37 nodes before touching code, then replaced the binary with five explicit, mutually exclusive states per node: `accepted_nodes`, `console_controls` (⊆ `accepted_nodes`), `pending_acceptance_nodes`, `mvp_deferred_nodes`, `not_started_nodes`. `console.js`'s generic phase-body renderer now walks all five lists and labels each honestly (never "locked" for an accepted node), with distinct colors (green=operable, blue=accepted-unwired, amber=pending, grey-dashed=deferred/not-started).

**Verification:** extended the backend suite from 26 to 28 tests, including a structural invariant test asserting every node 01-37 is classified in exactly one state per phase and that `console_controls` is always a subset of `accepted_nodes`. Re-verified live in the browser after restarting the server with the fixed code; confirmed Phase 2 and Phase 5 render correctly, confirmed no regression to the existing Node 01 registration flow.

This is an accuracy fix, not new functional scope — held at the same evidenced 90%, still pending live user-review acceptance.

## URGENT ALLOCATION addendum (2026-08-17T12:32-12:50+01:00) — real Node 04-10 controls

The user's own live review of the console rejected Phase 2: accurate labeling ("accepted, not wired") is not the same as usable functionality, and a status-only page does not let an operator actually run Node 05-10. Board event `20260817T122525918_codex_phase2ops`.

**What was built:** one real form per node for Node 04 (Conversion Definition) through Node 10 (Trend Detection), each posting to a new `server.py` handler that instantiates the actual registry class for that node — `ConversionDefinitionRegistry`, `DemandSignalRegistry`, `QuestionRegistry`, `SocialVideoSignalRegistry`, `CompetitorSignalRegistry`, `CommunitySignalRegistry`, `TrendSignalRegistry` — per-run, with the exact same fail-closed upstream-lineage checks each node's own contract already requires (Node 05 requires Node 04; Node 06 requires Node 05; and so on through the nine-way lineage Node 10 already enforces). Node 10's form explicitly tells the operator that `velocity`/`direction`/`spike_flag`/`confidence` are computed by the server, not editable inputs — consistent with Node 10's own design.

**A hard dependency, not scope creep:** Node 04 (`ConversionDefinitionRegistry`) is a mandatory constructor argument of Node 05's real registry — there is no way to wire Node 05 without a real Node 04 instance. So Node 04 necessarily gained a form too, even though the allocation named "Nodes 05-10." Its form was kept deliberately minimal (one optional text field for `success_criteria`) since the master spec's own 9-stage funnel and its transitions are not something an operator should be free-typing per run — they default server-side to the same canonical funnel every other node in this session has used.

**Verification, in order:**
1. Real HTTP test coverage: 15 new tests (positive + fail-closed-before-prerequisite for each of Node 04-10, plus a full-chain helper), extending the suite from 28 to 43, all passing.
2. A real bug found on the first run: Node 04's handler didn't default `success_criteria`, so the positive test failed with a 400. Fixed by defaulting it, matching the pattern already used for the funnel's other fields.
3. Live browser E2E of the complete chain (server restarted with the fixed code first): New Run → Node 01-04 (Phase 1) → Node 05-10 (Phase 2, now a genuine operational panel, not the generic locked-phase body). Verified via the API that all six new record types were created and 11 real lineage events were recorded, with Node 10's computed trend fields matching hand-calculated values.
4. Restart/reload persistence: stopped and restarted the server process entirely, re-fetched the same run, confirmed all data survived — this is a stronger check than a page reload, since it proves the JSON-file-backed storage model itself, not just client-side caching.
5. Accessibility/contrast spot-check on the new forms, and a no-network check (zero external URL references in the frontend files).

Held at evidenced 90%, requesting user acceptance — never self-marked 100%, per Codex's explicit instruction.
