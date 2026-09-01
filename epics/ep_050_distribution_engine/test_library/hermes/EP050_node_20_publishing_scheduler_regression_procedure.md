# EP050 Node 20 Publishing Scheduler Regression Procedure

> VERSION HISTORY
> - v1.1.0 · 2026-08-17 · Replaces stale function-discovery guidance with the consolidated current-code unittest procedure.
> - v1.0.0 · 2026-08-17 · Initial reusable local-only Node 20 regression procedure.

## Preconditions
Run from the repository root with Python and `jsonschema` installed. Do not configure adapters, credentials, queues, destinations outside `.test`, or network access.

## Steps
1. Run `python -m py_compile epics/ep_050_distribution_engine/implementation/node_20/publishing_scheduler.py epics/ep_050_distribution_engine/implementation/node_20/test_publishing_scheduler.py`.
2. Run `python epics/ep_050_distribution_engine/implementation/node_20/test_publishing_scheduler.py`.
3. Run `python epics/ep_050_distribution_engine/integration/reviews/hermes/node19_to_node20_candidate_v1_1_test.py`.
4. Stop on any failure. Preserve prior evidence; create a new timestamped `evidence/node_20/<timestamp>/` record for each rerun.

## Expected Results
- Compile succeeds.
- Current Node 20 suite passes 10/10 with actual Node 19 `evaluate_asset_compliance` output, idempotency/persistence, negative validation, conflict, and socket-prohibition coverage.
- Candidate contract procedure passes 12/12.
- Aggregate is 22/22 behavioral checks plus compile.
- Every plan remains local/in-memory with `external_action: false`; no network, queue, timer, scheduler, adapter, credential, or publishing action is allowed.
