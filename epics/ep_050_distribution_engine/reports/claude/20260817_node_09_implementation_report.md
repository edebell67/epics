# EP050 Node 09 — Community Intelligence Implementation Report

> VERSION HISTORY
> - v1.1.0 · 2026-08-17 · Codex acceptance decision recorded (board event `20260817T062636142_codex_eb573fee`). Node 09 is 100% complete.
> - v1.0.0 · 2026-08-17 · Initial implementation report, held pending required acceptance sign-off.

**Allocation:** `20260817T060634552_codex_dab2cc0c` (activated after Node 08's 100% acceptance).
**Owner:** Claude, Node 09 only.
**Status:** 100% complete. Accepted by Codex: "Timestamped evidence records 31/31 passing with real Nodes01-08 integration, validation/PII/idempotency/conflict/persistence/no-network/full regression coverage and required governed artifacts." (board event `20260817T062636142_codex_eb573fee`).

## What was built

`epics/ep_050_distribution_engine/implementation/node_09/community_intelligence.py` — a deterministic, offline, fail-closed, no-live-community-access community-intelligence registry:

- `CommunitySignalRecord` — `signal_id`, `target_id`, `community_source`, `topic`, `question`, `pain_point`, `intent_cues`, `geography`, `observed_metrics`, `observed_at`, `source_type`, `evidence`, `metadata`, `recorded_at`.
- `CommunitySignalRegistry` — local JSON-file-backed store, keyed by `signal_id`. `register()` validates fully before any write, checks the `target_id` against **eight** real upstream registries — Node 01, Node 02, Node 03, Node 04, Node 05 (demand signal), Node 06 (question), Node 07 (social/video signal), Node 08 (competitor signal, via `list_for_target`) — per the allocation's explicit "consuming validated Nodes01-08 lineage." Any missing raises `UnknownTargetError`. Idempotent on identical re-registration, `ConflictError` on a same-signal conflicting duplicate.
- `source_type` pinned to `{manual_curation, synthetic_fixture}`, consistent with Nodes 05–08.
- `observed_metrics` validated as a non-empty object of non-negative numeric values, reusing the Node 07 pattern.
- **Prohibited-PII fail-closed screen** on `community_source`, `topic`, `question`, and `pain_point`.
- No posting, outreach, or live community-access capability of any kind — intelligence capture only, consistent with the master spec's "not automated spam" framing for this node.

## Tests

`epics/ep_050_distribution_engine/implementation/node_09/test_community_intelligence.py` — 31 tests, all passing on the first run:

| Category | Tests |
|---|---|
| Positive registration + optional-metadata default | 2 |
| Node01-08->09 eight-way contract/integration | 3 |
| Required-field failures (12 fields) | 12 |
| Invalid enum/type (source_type, intent_cues, observed_metrics x3, observed_at, geography) | 7 |
| Prohibited-PII rejection | 2 |
| Duplicate idempotency | 1 |
| Conflicting duplicate rejection | 1 |
| Serialization/persistence | 1 |
| No-network assertion | 1 |
| Full-lifecycle regression | 1 |

Command and result: `pytest epics/ep_050_distribution_engine/implementation/node_09/test_community_intelligence.py -v` → **31 passed, 0 failed, 0 errors** (4.61s). Full output: `epics/ep_050_distribution_engine/evidence/node_09/20260817_061843/pytest_output.txt`.

## Safety confirmation

- No network call, no live community/forum/Reddit access, browsing, scraping, APIs, credentials, or outreach: verified by a monkeypatched-`socket.socket` test.
- No production datastore: only a caller-supplied local JSON file is ever written.
- Prohibited PII actively screened and rejected.
- `observed_metrics` cannot contain negative or non-numeric values, and cannot be empty.
- Only the confirmed synthetic target (`tgt_boiler_repair_blackheath`) and synthetic community-source strings were used in tests.

## Artifact paths

- Implementation: `epics/ep_050_distribution_engine/implementation/node_09/community_intelligence.py`
- Tests: `epics/ep_050_distribution_engine/implementation/node_09/test_community_intelligence.py`
- Evidence: `epics/ep_050_distribution_engine/evidence/node_09/20260817_061843/` (`pytest_output.txt`, `README.md`)
- Implementation checklist: `workstream/600_workflow/ep050/EP050_distribution_engine_node_09_implementation_checklist.html`
- Regression procedure: `workstream/Test Library/ep050/EP050_node_09_community_intelligence_regression_procedure.md`, EP050-root copy at `epics/ep_050_distribution_engine/test_library/claude/`
- Lifecycle: `workstream/200_inprogress/20260817_061843_ep050_997_node_09_implementation.md`, mirrored byte-identical to `epics/ep_050_distribution_engine/lifecycle/claude/` and the Obsidian workstream mirror.

## Acceptance

Per `skills/model-messageboard-interaction/SKILL.md`, 100% requires "user verification or explicit valid auto-acceptance" beyond the technical gates above. Codex issued the explicit lifecycle-compliant auto-acceptance decision at `20260817T062636142_codex_eb573fee`. Node 09 is complete. Node 10 (Trend Detection) was allocated next (`20260817T062636269_codex_ea5e04ff`).
