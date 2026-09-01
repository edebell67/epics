# EP050 Node 04 — Conversion Definition Implementation Report

> VERSION HISTORY
> - v1.1.0 · 2026-08-17 · Codex acceptance decision recorded (board event `20260817T044641358_codex_6034e811`). Node 04 is 100% complete.
> - v1.0.0 · 2026-08-17 · Initial implementation report, held pending required acceptance sign-off.

**Allocation:** `20260817T000604746_codex_02584543` (activated after Node 03's 100% acceptance; deferred once for Operational UI v2 priority; reactivated `20260817T010116815_codex_32dba309`, urgently `20260817T043143354_codex_f3aa6368`).
**Owner:** Claude, Node 04 only.
**Status:** 100% complete. Accepted by Codex: "Evidence reconciled: required implementation, workflow/checklist, report, lifecycle/mirrors and reusable regression procedure exist; timestamped pytest evidence records 24/24 passing, including real Nodes01-03 integration, validation, transition, idempotency/conflict, persistence, no-network and lifecycle regression coverage." (board event `20260817T044641358_codex_6034e811`).

## What was built

`epics/ep_050_distribution_engine/implementation/node_04/conversion_definition.py` — a deterministic, offline, fail-closed conversion/funnel-definition registry:

- `MASTER_SPEC_STAGES` — the master specification's own worked funnel (§9 Node 04): Visit → Engage → Tool use → Enquiry → Lead → Qualified lead → Booking → Sale → Revenue, used as the confirmed default fixture (9 stages, matching the spec verbatim).
- `ConversionDefinitionRecord` — immutable record with `target_id`, `stages` (each with `stage_id`/`label`/`order`), `allowed_transitions` (ordered `[from, to]` pairs), `success_stage_id`, `success_criteria`, `recorded_at`.
- `ConversionDefinitionRegistry` — local JSON-file-backed store, one record per `target_id`. `register()` validates fully before any write: stage `order` values must be exactly `1..N` with no gaps or duplicates; every transition must reference declared stages and move strictly forward in order (no backward or self transitions, no duplicate pairs); `success_stage_id` must be one of the declared stages. It then checks the referenced `target_id` against **three** real upstream registries — Node 01 (`TargetRegistry`), Node 02 (`ProductIntelligenceRegistry`), Node 03 (`AudienceSegmentRegistry`, via `list_for_target`) — any missing raises `UnknownTargetError`. It is idempotent on identical re-registration and raises `ConflictError` on a same-target conflicting duplicate.

## Tests

`epics/ep_050_distribution_engine/implementation/node_04/test_conversion_definition.py` — 24 tests, all passing on the first run:

| Category | Tests |
|---|---|
| Positive registration (master-spec funnel) | 1 |
| Node01+Node02+Node03->04 contract/integration (all three real registries) | 4 |
| Required-field failures (5 fields) | 5 |
| Invalid stages (duplicate id/order, order gap, non-positive order) | 4 |
| Invalid transitions (unknown ref, backward, self, duplicate, bad success_stage_id) | 5 |
| Duplicate idempotency | 1 |
| Conflicting duplicate rejection | 1 |
| Serialization/persistence | 1 |
| No-network assertion | 1 |
| Full-lifecycle regression | 1 |

Command and result: `pytest epics/ep_050_distribution_engine/implementation/node_04/test_conversion_definition.py -v` → **24 passed, 0 failed, 0 errors** (1.32s). Full output: `epics/ep_050_distribution_engine/evidence/node_04/20260817_033930/pytest_output.txt`.

## Safety confirmation

- No network call: verified by a monkeypatched-`socket.socket` test.
- No production datastore: only a caller-supplied local JSON file is ever written.
- Only the confirmed synthetic target (`tgt_boiler_repair_blackheath`) was used in tests.
- No live scraping, publishing, outreach, routing, payment, or deployment code exists in this node.

## Artifact paths

- Implementation: `epics/ep_050_distribution_engine/implementation/node_04/conversion_definition.py`
- Tests: `epics/ep_050_distribution_engine/implementation/node_04/test_conversion_definition.py`
- Evidence: `epics/ep_050_distribution_engine/evidence/node_04/20260817_033930/` (`pytest_output.txt`, `README.md`)
- Implementation checklist: `workstream/600_workflow/ep050/EP050_distribution_engine_node_04_implementation_checklist.html`
- Regression procedure: `workstream/Test Library/ep050/EP050_node_04_conversion_definition_regression_procedure.md`, EP050-root copy at `epics/ep_050_distribution_engine/test_library/claude/`
- Lifecycle: `workstream/200_inprogress/20260817_033930_ep050_997_node_04_implementation.md`, mirrored byte-identical to `epics/ep_050_distribution_engine/lifecycle/claude/` and the Obsidian workstream mirror.

## Acceptance

Per `skills/model-messageboard-interaction/SKILL.md`, 100% requires "user verification or explicit valid auto-acceptance" beyond the technical gates above. Codex issued the explicit lifecycle-compliant auto-acceptance decision at `20260817T044641358_codex_6034e811`. Node 04 is complete — this closes Phase 1 (Target & Conversion Definition, Nodes 01–04) of the seven-phase master workflow. Node 05 (Search Demand Discovery) was allocated next (`20260817T044641486_codex_15a3c325`).
