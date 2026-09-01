# EP050 Node 05 — Search Demand Discovery Implementation Report

> VERSION HISTORY
> - v1.1.0 · 2026-08-17 · Codex acceptance decision recorded (board event `20260817T050624417_codex_590ac6c0`), citing independent Hermes re-verification. Node 05 is 100% complete.
> - v1.0.0 · 2026-08-17 · Initial implementation report, held pending required acceptance sign-off.

**Allocation:** `20260817T044641486_codex_15a3c325` (activated after Node 04's 100% acceptance, closing Phase 1).
**Owner:** Claude, Node 05 only.
**Status:** 100% complete. Accepted by Codex: "Accepted at 100%. Evidence includes owner 25/25 pass and independent Hermes 25/25 rerun, real Nodes01-04 integration, unmodified Gemini Node11 compatibility, validation/PII/idempotency/conflict/persistence/no-network/regression coverage, and required lifecycle/workflow/checklist/report/procedure artifacts." (board event `20260817T050624417_codex_590ac6c0`). Independently corroborated by Hermes: a fresh WSL run of the full suite reproduced 25/25 passing, including the real Node01-04 lineage checks and the unmodified Node 11 compatibility test (`epics/ep_050_distribution_engine/lifecycle/hermes/20260817_050123_ep050_node_05_acceptance_assessment.md`).

## What was built

`epics/ep_050_distribution_engine/implementation/node_05/search_demand_discovery.py` — a deterministic, offline, fail-closed, no-live-scraping demand-signal registry, deliberately producing records in **exactly** the shape the already-implemented Node 11 (Gemini-owned) expects:

- `DemandSignalRecord` — `signal_id`, `target_id`, `raw_query`, `topic`, `source_type`, `observed_at`, `geography`, `service_context`, `metadata`, `recorded_at` — matching the frozen Node05→11 contract v1.1.0 field-for-field, plus a local `recorded_at` timestamp. `to_contract_payload()` strips the Node-05-local field to produce the exact contract shape.
- `DemandSignalRegistry` — local JSON-file-backed store, keyed by `signal_id`. `register()` validates fully before any write, checks the `target_id` against **four** real upstream registries — Node 01, Node 02, Node 03 (via `list_for_target`), Node 04 — any missing raises `UnknownTargetError`. Idempotent on identical re-registration, `ConflictError` on a same-signal conflicting duplicate.
- `source_type` pinned to `{manual_curation, synthetic_fixture}` — the same offline-only boundary already enforced by Node 11 and by the contract itself; `search_query`/`forum_question` are explicitly rejected as reserved for a future, separately-authorized live phase.
- **Prohibited-PII fail-closed screen** on `raw_query` and `topic` (email/phone patterns), reusing the same approach proven in Node 03.

## Real cross-owner verification, not assumed compatibility

The test suite imports Gemini's actual `intent_classification.py` (read-only) and feeds a signal produced by Node 05's own registry directly into `classify_demand_signal()`. It succeeds without any adaptation — proving Node 05's output is genuinely usable by the already-built Node 11, not merely believed to match on paper.

## Tests

`epics/ep_050_distribution_engine/implementation/node_05/test_search_demand_discovery.py` — 25 tests, all passing on the first run:

| Category | Tests |
|---|---|
| Positive registration + optional-metadata default | 2 |
| Node01+02+03+04->05 contract/integration (all four real registries) | 3 |
| **Cross-owner contract compatibility (real Node 11 import)** | 1 |
| Required-field failures (8 fields) | 8 |
| Invalid enum/type | 4 |
| Prohibited-PII rejection | 2 |
| Duplicate idempotency | 1 |
| Conflicting duplicate rejection | 1 |
| Serialization/persistence | 1 |
| No-network assertion | 1 |
| Full-lifecycle regression (incl. second Node 11 check) | 1 |

Command and result: `pytest epics/ep_050_distribution_engine/implementation/node_05/test_search_demand_discovery.py -v` → **25 passed, 0 failed, 0 errors** (1.95s). Full output: `epics/ep_050_distribution_engine/evidence/node_05/20260817_035602/pytest_output.txt`.

## Safety confirmation

- No network call, no live scraping: verified by a monkeypatched-`socket.socket` test.
- No production datastore: only a caller-supplied local JSON file is ever written.
- Prohibited PII actively screened and rejected, not assumed absent.
- `source_type` cannot be set to a live-collection value.
- Only the confirmed synthetic target (`tgt_boiler_repair_blackheath`) was used in tests.

## Artifact paths

- Implementation: `epics/ep_050_distribution_engine/implementation/node_05/search_demand_discovery.py`
- Tests: `epics/ep_050_distribution_engine/implementation/node_05/test_search_demand_discovery.py`
- Evidence: `epics/ep_050_distribution_engine/evidence/node_05/20260817_035602/` (`pytest_output.txt`, `README.md`)
- Implementation checklist: `workstream/600_workflow/ep050/EP050_distribution_engine_node_05_implementation_checklist.html`
- Regression procedure: `workstream/Test Library/ep050/EP050_node_05_search_demand_discovery_regression_procedure.md`, EP050-root copy at `epics/ep_050_distribution_engine/test_library/claude/`
- Lifecycle: `workstream/200_inprogress/20260817_035602_ep050_997_node_05_implementation.md`, mirrored byte-identical to `epics/ep_050_distribution_engine/lifecycle/claude/` and the Obsidian workstream mirror.

## Acceptance

Per `skills/model-messageboard-interaction/SKILL.md`, 100% requires "user verification or explicit valid auto-acceptance" beyond the technical gates above. Codex issued the explicit lifecycle-compliant auto-acceptance decision at `20260817T050624417_codex_590ac6c0`, itself grounded in Hermes's independent re-verification. Node 05 is complete. Node 06 (Question Discovery) was allocated next (`20260817T050624536_codex_8955f58f`).
