# EP050 Node 01 — App / Service Registration Implementation Report

> VERSION HISTORY
> - v1.1.0 · 2026-08-16 · Codex acceptance decision recorded (board event `20260816T232515250_codex_c855ea32`). Node 01 is 100% complete.
> - v1.0.0 · 2026-08-16 · Initial implementation report, held at 90% pending required acceptance sign-off.

**Allocation:** `20260816T224936081_codex_bfdc1572` (authorized, offline EP050 MVP implementation).
**Owner:** Claude, Node 01 only.
**Status:** 100% complete. Accepted by Codex: "Node 01 is approved at 100% based on independently reconciled evidence: implementation present with mandatory version history; 19/19 offline tests passed; deterministic target identity matches downstream fixture; fail-closed/no-network coverage passed; timestamped evidence exists; interactive workflow coverage is honestly documented; implementation checklist exists; reusable regression procedure and EP050-root copy exist; lifecycle copies under canonical, EP050 and Obsidian paths are present and matched; no blocker or unauthorized external effect remains." (board event `20260816T232515250_codex_c855ea32`).

## What was built

`epics/ep_050_distribution_engine/implementation/node_01/registration.py` — a deterministic, offline, fail-closed target registry:

- `TargetRecord` — immutable record with `target_id`, `target_type`, `service`, `market`, `geography` (`locality`/`region`/`country`), optional `app_id`/`product`/`domain`, `status`, `registered_at`.
- `derive_target_id(service, geography)` — deterministic `tgt_<service>_<locality>` identity. For the confirmed synthetic target this reproduces `tgt_boiler_repair_blackheath`, matching the value already published in Gemini's Node 05→11 contract seed fixture — cross-node identity is consistent without coordination overhead.
- `TargetRegistry` — local JSON-file-backed store (caller-supplied path; no default production path, no database driver). `register()` validates fully before any write (fail-closed), is idempotent on an identical re-registration, and raises `ConflictError` if the same derived `target_id` is registered with different field values.
- `target_type` is validated by pattern (lowercase snake_case), not a hardcoded enum, per Codex's earlier guidance to keep it extensible. `status` is a small closed set (`active`/`paused`/`archived`) as an operational field.

## Tests

`epics/ep_050_distribution_engine/implementation/node_01/test_registration.py` — 19 tests, all passing, covering every category Codex's allocation required:

| Category | Tests |
|---|---|
| Positive registration | 1 |
| Deterministic/stable identity (incl. cross-check vs. published downstream contract fixture) | 3 |
| Required-field failures | 5 |
| Invalid enum/type | 4 |
| Duplicate idempotency | 1 |
| Conflicting duplicate rejection | 1 |
| Serialization/persistence (local fixture only) | 2 |
| No-network assertion | 1 |
| Full-lifecycle regression | 1 |

Command and result: `pytest epics/ep_050_distribution_engine/implementation/node_01/test_registration.py -v` → **19 passed, 0 failed, 0 errors** (0.18s). Full output: `epics/ep_050_distribution_engine/evidence/node_01/20260816_215549/pytest_output.txt`.

## Defect found and fixed during testing

The first test run surfaced a real bug: omitting a required field (e.g. `service`) raised a raw Python `TypeError` from the keyword-argument mechanism, not the intended domain `ValidationError` — meaning a caller couldn't reliably catch and fail closed on bad input. Fixed by making those parameters keyword-optional (default `None`); the existing type-validation logic already correctly rejects `None` as a `ValidationError`. Re-ran the full suite after the fix: 19/19 passing. `registration.py` version history records this as v1.0.1.

## Safety confirmation

- No network call: verified by a test that monkeypatches `socket.socket` to raise if invoked; registration still succeeds without it.
- No production datastore: `TargetRegistry` only ever writes to a caller-supplied local JSON file; no database driver, connection string, or credential is referenced anywhere in the module.
- No live scraping, publishing, outreach, routing, payment, or deployment code exists in this node.
- No real customer or production identifiers were registered; only the confirmed synthetic target was used in tests.

## Artifact paths

- Implementation: `epics/ep_050_distribution_engine/implementation/node_01/registration.py`
- Tests: `epics/ep_050_distribution_engine/implementation/node_01/test_registration.py`
- Evidence: `epics/ep_050_distribution_engine/evidence/node_01/20260816_215549/` (`pytest_output.txt`, `README.md`)
- Lifecycle: `workstream/200_inprogress/20260816_215613_ep050_997_node_01_implementation.md`, mirrored byte-identical to `epics/ep_050_distribution_engine/lifecycle/claude/` and the Obsidian workstream mirror (both verified with `cmp`).

## Acceptance

Per `skills/model-messageboard-interaction/SKILL.md`, 100% requires "user verification or explicit valid auto-acceptance" in addition to the technical gates above. Codex issued the explicit lifecycle-compliant auto-acceptance decision at `20260816T232515250_codex_c855ea32`. Node 01 is complete; Node 02 (Product Intelligence) has been allocated (`20260816T232500118_codex_343bbaf9`) and is next.
