# EP050 Node 08 — Competitor Intelligence Implementation Report

> VERSION HISTORY
> - v1.1.0 · 2026-08-17 · Codex acceptance decision recorded (board event `20260817T060634418_codex_761a5084`). Node 08 is 100% complete.
> - v1.0.0 · 2026-08-17 · Initial implementation report, held pending required acceptance sign-off.

**Allocation:** `20260817T054639708_codex_732b65de` (activated after Node 07's 100% acceptance).
**Owner:** Claude, Node 08 only.
**Status:** 100% complete. Accepted by Codex: "Timestamped evidence records 31/31 passing with real Nodes01-07 integration, validation/PII/idempotency/conflict/persistence/no-network/regression coverage and governed artifacts." (board event `20260817T060634418_codex_761a5084`).

## What was built

`epics/ep_050_distribution_engine/implementation/node_08/competitor_intelligence.py` — a deterministic, offline, fail-closed, no-live-research competitor-intelligence registry:

- `CompetitorSignalRecord` — `signal_id`, `target_id`, `competitor_name`, `channel`, `topic`, `query`, `attention_source`, `relevance_score` (0.0–1.0), `competition_indicator` (low/medium/high), `geography`, `observed_at`, `source_type`, `evidence`, `metadata`, `recorded_at`.
- `CompetitorSignalRegistry` — local JSON-file-backed store, keyed by `signal_id`. `register()` validates fully before any write, checks the `target_id` against **seven** real upstream registries — Node 01, Node 02, Node 03, Node 04, Node 05 (demand signal), Node 06 (question), Node 07 (social/video signal, via `list_for_target`) — per the allocation's explicit "consuming validated Nodes01-07 lineage." Any missing raises `UnknownTargetError`. Idempotent on identical re-registration, `ConflictError` on a same-signal conflicting duplicate.
- `source_type` pinned to `{manual_curation, synthetic_fixture}`, consistent with Nodes 05–07.
- **Prohibited-PII fail-closed screen** on `competitor_name`, `topic`, and `query`.

## Tests

`epics/ep_050_distribution_engine/implementation/node_08/test_competitor_intelligence.py` — 31 tests, all passing on the first run:

| Category | Tests |
|---|---|
| Positive registration + optional-metadata default | 2 |
| Node01-07->08 seven-way contract/integration | 3 |
| Required-field failures (13 fields) | 13 |
| Invalid enum/type (source_type, competition_indicator, relevance_score, observed_at, geography) | 6 |
| Prohibited-PII rejection | 2 |
| Duplicate idempotency | 1 |
| Conflicting duplicate rejection | 1 |
| Serialization/persistence | 1 |
| No-network assertion | 1 |
| Full-lifecycle regression | 1 |

Command and result: `pytest epics/ep_050_distribution_engine/implementation/node_08/test_competitor_intelligence.py -v` → **31 passed, 0 failed, 0 errors** (3.75s). Full output: `epics/ep_050_distribution_engine/evidence/node_08/20260817_045547/pytest_output.txt`.

## Safety confirmation

- No network call, no live competitor research/browsing/scraping/APIs/credentials: verified by a monkeypatched-`socket.socket` test.
- No production datastore: only a caller-supplied local JSON file is ever written.
- Prohibited PII actively screened and rejected.
- `relevance_score` cannot exceed [0.0, 1.0]; `competition_indicator` cannot be an unrecognized value.
- Only the confirmed synthetic target (`tgt_boiler_repair_blackheath`) and a synthetic competitor name were used in tests.

## Artifact paths

- Implementation: `epics/ep_050_distribution_engine/implementation/node_08/competitor_intelligence.py`
- Tests: `epics/ep_050_distribution_engine/implementation/node_08/test_competitor_intelligence.py`
- Evidence: `epics/ep_050_distribution_engine/evidence/node_08/20260817_045547/` (`pytest_output.txt`, `README.md`)
- Implementation checklist: `workstream/600_workflow/ep050/EP050_distribution_engine_node_08_implementation_checklist.html`
- Regression procedure: `workstream/Test Library/ep050/EP050_node_08_competitor_intelligence_regression_procedure.md`, EP050-root copy at `epics/ep_050_distribution_engine/test_library/claude/`
- Lifecycle: `workstream/200_inprogress/20260817_045547_ep050_997_node_08_implementation.md`, mirrored byte-identical to `epics/ep_050_distribution_engine/lifecycle/claude/` and the Obsidian workstream mirror.

## Acceptance

Per `skills/model-messageboard-interaction/SKILL.md`, 100% requires "user verification or explicit valid auto-acceptance" beyond the technical gates above. Codex issued the explicit lifecycle-compliant auto-acceptance decision at `20260817T060634418_codex_761a5084`. Node 08 is complete. Node 09 (Community Intelligence) was allocated next (`20260817T060634552_codex_dab2cc0c`).
