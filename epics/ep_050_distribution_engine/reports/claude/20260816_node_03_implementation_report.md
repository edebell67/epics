# EP050 Node 03 — Audience Definition Implementation Report

> VERSION HISTORY
> - v1.1.0 · 2026-08-17 · Codex acceptance decision recorded (board event `20260817T000604616_codex_a4c9dde4`). Node 03 is 100% complete.
> - v1.0.0 · 2026-08-16 · Initial implementation report, held pending required acceptance sign-off.

**Allocation:** `20260816T234617397_codex_0c8c6179` (Node 03, activated immediately after Node 02's 100% acceptance).
**Owner:** Claude, Node 03 only.
**Status:** 100% complete. Accepted by Codex: "Node 03 approved at 100%. Evidence supports 26/26 passing with real Node01+Node02->03 integration, fail-closed upstream checks, privacy/PII rejection, deterministic identity, validation, idempotency/conflict, persistence, no-network and regression coverage; required workflow/checklist, Test Library plus EP050 copy, lifecycle/report/Obsidian mirrors are reported with no blocker or external effect." (board event `20260817T000604616_codex_a4c9dde4`).

## What was built

`epics/ep_050_distribution_engine/implementation/node_03/audience_definition.py` — a deterministic, offline, fail-closed, privacy-safe audience-segment registry:

- `AudienceSegmentRecord` — immutable record with `segment_id`, `target_id`, `segment_name`, `needs`, `pains`, `urgency` (enum), `eligibility_geography`, optional `exclusions`/`evidence_sources`, `recorded_at`.
- `AudienceSegmentRegistry` — local JSON-file-backed store, keyed by a deterministic `segment_id` (`<target_id>__seg_<segment_name>`). `register()` validates fully before any write, checks the referenced `target_id` against **both** a real Node 01 `TargetRegistry` and a real Node 02 `ProductIntelligenceRegistry` (the Node01+Node02→03 contract dependency — either missing raises `UnknownTargetError`), is idempotent on identical re-registration, and raises `ConflictError` on a same-segment conflicting duplicate.
- **Prohibited-PII fail-closed screen**: every free-text field (`segment_name`, `needs`, `pains`, `exclusions`) is checked against email and phone-number patterns; a match raises `ValidationError` before anything is written. This directly satisfies the allocation's "fail closed on ... prohibited PII" requirement.

## Tests

`epics/ep_050_distribution_engine/implementation/node_03/test_audience_definition.py` — 26 tests, all passing on the first run:

| Category | Tests |
|---|---|
| Positive registration, deterministic ID, optional defaults | 3 |
| Node01+Node02->03 contract/integration (both real registries) | 3 |
| Required-field failures (6 fields + geography subfield) | 7 |
| Invalid enum/type | 4 |
| Prohibited-PII rejection (email + phone across 4 fields) | 4 |
| Duplicate idempotency | 1 |
| Conflicting duplicate rejection | 1 |
| Serialization/persistence | 1 |
| No-network assertion | 1 |
| Full-lifecycle regression | 1 |

Command and result: `pytest epics/ep_050_distribution_engine/implementation/node_03/test_audience_definition.py -v` → **26 passed, 0 failed, 0 errors** (1.01s). Full output: `epics/ep_050_distribution_engine/evidence/node_03/20260816_225517/pytest_output.txt`.

## Safety confirmation

- No network call: verified by a monkeypatched-`socket.socket` test.
- No production datastore: only a caller-supplied local JSON file is ever written.
- Prohibited PII (email addresses, phone numbers) is actively screened and rejected across every free-text input, not merely assumed absent.
- Only the confirmed synthetic target (`tgt_boiler_repair_blackheath`) was used in tests.
- No live scraping, publishing, outreach, routing, payment, or deployment code exists in this node.

## Artifact paths

- Implementation: `epics/ep_050_distribution_engine/implementation/node_03/audience_definition.py`
- Tests: `epics/ep_050_distribution_engine/implementation/node_03/test_audience_definition.py`
- Evidence: `epics/ep_050_distribution_engine/evidence/node_03/20260816_225517/` (`pytest_output.txt`, `README.md`)
- Implementation checklist: `workstream/600_workflow/ep050/EP050_distribution_engine_node_03_implementation_checklist.html`
- Regression procedure: `workstream/Test Library/ep050/EP050_node_03_audience_definition_regression_procedure.md`, EP050-root copy at `epics/ep_050_distribution_engine/test_library/claude/`
- Lifecycle: `workstream/200_inprogress/20260816_225517_ep050_997_node_03_implementation.md`, mirrored byte-identical to `epics/ep_050_distribution_engine/lifecycle/claude/` and the Obsidian workstream mirror.

## Acceptance

Per `skills/model-messageboard-interaction/SKILL.md`, 100% requires "user verification or explicit valid auto-acceptance" beyond the technical gates above. Codex issued the explicit lifecycle-compliant auto-acceptance decision at `20260817T000604616_codex_a4c9dde4`. Node 03 is complete. Node 04 (Conversion Definition) was allocated (`20260817T000604746_codex_02584543`) but is **deferred before activation** per `20260817T001150407_codex_53c90aac`: the user reallocated priority to Operational UI v2 after rejecting the prior Operational Console attempt. Node 04 ownership remains reserved to Claude and resumes after the UI review cycle.
