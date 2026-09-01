# EP050 Node 06 — Question Discovery Implementation Report

> VERSION HISTORY
> - v1.1.0 · 2026-08-17 · Codex acceptance decision recorded (board event `20260817T052644252_codex_b758a636`). Node 06 is 100% complete.
> - v1.0.0 · 2026-08-17 · Initial implementation report, held pending required acceptance sign-off.

**Allocation:** `20260817T050624536_codex_8955f58f` (activated after Node 05's 100% acceptance).
**Owner:** Claude, Node 06 only.
**Status:** 100% complete. Accepted by Codex: "Evidence paths exist and timestamped pytest output records 26/26 passing with real Nodes01-05 integration, validation/PII/idempotency/conflict/persistence/no-network/regression coverage and required lifecycle/workflow/checklist/report/procedure artifacts." (board event `20260817T052644252_codex_b758a636`).

## What was built

`epics/ep_050_distribution_engine/implementation/node_06/question_discovery.py` — a deterministic, offline, fail-closed, no-live-source explicit-question registry:

- `QuestionRecord` — `question_id`, `target_id`, `question_text`, `topic`, `pain_point`, `geography`, `intent_cues`, `source_type`, `observed_at`, `evidence`, `metadata`, `recorded_at`.
- `QuestionRegistry` — local JSON-file-backed store, keyed by `question_id`. `register()` validates fully before any write, checks the `target_id` against **five** real upstream registries — Node 01, Node 02, Node 03, Node 04, and Node 05 (via `list_for_target`, requiring at least one demand signal) — per the allocation's explicit "consuming validated Nodes01-05 with exact lineage." Any missing raises `UnknownTargetError`. Idempotent on identical re-registration, `ConflictError` on a same-question conflicting duplicate.
- `source_type` pinned to `{manual_curation, synthetic_fixture}`, consistent with Node 05's boundary.
- **Prohibited-PII fail-closed screen** on `question_text`, `topic`, and `pain_point`.

## Tests

`epics/ep_050_distribution_engine/implementation/node_06/test_question_discovery.py` — 26 tests, all passing on the first run:

| Category | Tests |
|---|---|
| Positive registration + optional-metadata default | 2 |
| Node01-05->06 five-way contract/integration | 3 |
| Required-field failures (10 fields) | 10 |
| Invalid enum/type | 4 |
| Prohibited-PII rejection | 2 |
| Duplicate idempotency | 1 |
| Conflicting duplicate rejection | 1 |
| Serialization/persistence | 1 |
| No-network assertion | 1 |
| Full-lifecycle regression | 1 |

Command and result: `pytest epics/ep_050_distribution_engine/implementation/node_06/test_question_discovery.py -v` → **26 passed, 0 failed, 0 errors** (3.34s). Full output: `epics/ep_050_distribution_engine/evidence/node_06/20260817_041549/pytest_output.txt`.

## Safety confirmation

- No network call, no live sources: verified by a monkeypatched-`socket.socket` test.
- No production datastore: only a caller-supplied local JSON file is ever written.
- Prohibited PII actively screened and rejected.
- Only the confirmed synthetic target (`tgt_boiler_repair_blackheath`) was used in tests.

## Artifact paths

- Implementation: `epics/ep_050_distribution_engine/implementation/node_06/question_discovery.py`
- Tests: `epics/ep_050_distribution_engine/implementation/node_06/test_question_discovery.py`
- Evidence: `epics/ep_050_distribution_engine/evidence/node_06/20260817_041549/` (`pytest_output.txt`, `README.md`)
- Implementation checklist: `workstream/600_workflow/ep050/EP050_distribution_engine_node_06_implementation_checklist.html`
- Regression procedure: `workstream/Test Library/ep050/EP050_node_06_question_discovery_regression_procedure.md`, EP050-root copy at `epics/ep_050_distribution_engine/test_library/claude/`
- Lifecycle: `workstream/200_inprogress/20260817_041549_ep050_997_node_06_implementation.md`, mirrored byte-identical to `epics/ep_050_distribution_engine/lifecycle/claude/` and the Obsidian workstream mirror.

## Acceptance

Per `skills/model-messageboard-interaction/SKILL.md`, 100% requires "user verification or explicit valid auto-acceptance" beyond the technical gates above. Codex issued the explicit lifecycle-compliant auto-acceptance decision at `20260817T052644252_codex_b758a636`. Node 06 is complete. Node 07 (Social/Video Discovery) was allocated next (`20260817T052644427_codex_7bef37f7`).
