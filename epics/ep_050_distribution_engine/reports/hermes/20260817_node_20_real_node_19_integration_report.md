# EP050 Node 20 Publishing Scheduler — Reconciliation Report

> VERSION HISTORY
> - v2.1.0 · 2026-08-17 · Adds the requested current-code consolidated regression and preserves the missing-directory history anomaly.
> - v2.0.0 · 2026-08-17 · Recreated missing Node 20 source and completed canonical real Node 19-to-20 local integration evidence.

## Outcome
Node 20 is evidenced at **90%, pending Codex acceptance**, as an offline mock consumer. `implementation/node_20/publishing_scheduler.py` accepts the actual `ApprovedAssetPackage` emitted by Node 19 `evaluate_asset_compliance`, validates the promoted canonical v1.1.0 contract, enforces timestamp/lineage gates, derives the contract-defined SHA-256 `mpp_` ID, and stores only idempotent in-memory mock plans.

## Preservation / Reconciliation Note
Legacy 75% records remain intact under `workstream/200_inprogress/hermes/20260817_000814_ep050_997_node_20_offline_publishing_scheduler.md` and `evidence/node_20/20260817_000814/`. At the 06:20 canonical-integration allocation, `implementation/node_20/` was absent, so the current consumer was recreated rather than modifying a legacy implementation. No historic file was deleted, moved, reset, archived, or rewritten. This report and `evidence/node_20/20260817_063639/` are additive reconciliation artifacts. The legacy workstream lifecycle is outside the EP050 authorization edit boundary and is therefore referenced, not altered.

## Consolidated Current-Code Validation
Command set recorded in `evidence/node_20/20260817_063639/consolidated_current_code_regression_output.txt`:

- **PASS — py_compile** for the current Node 20 module and its current regression suite.
- **PASS — 10/10 Node 20 current-code tests**, with `socket.socket` blocked in every test: real Node 19 producer integration, idempotency/persistence, tracking lineage rejection, non-`.test` rejection, unapproved-compliance rejection, timestamp rejection, channel rejection, additional-property rejection, repository-conflict rejection, and malformed-input rejection.
- **PASS — 12/12 retained candidate-contract checks**, including canonical plan projection, nine negative gates, `external_action` rejection, and a socket-prohibited assertion.
- **Aggregate: PASS 22/22 behavioral checks plus py_compile.**

## Safety Boundary
This is not a live scheduler or publisher. It contains no adapter, request, queue, credential, timer, durable store, external action, or network capability. Every emitted plan contains literal `external_action: false` and a schema-constrained `.test` destination.

## Requested Next Action
Codex acceptance is required before 100%. Until then, Node 20 remains 90% and this scope remains offline-only.
