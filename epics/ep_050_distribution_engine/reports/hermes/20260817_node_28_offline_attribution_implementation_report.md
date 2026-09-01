# EP050 Node 28 — Offline Attribution implementation report

## Outcome
Implemented `implementation/node_28/offline_attribution.py`, a deterministic local-only attribution contract. It consumes an actual validated Node 27 structured-lead record, preserves its `lead_id`, explicit consent, session/source and full inherited route context, and emits a stable pseudonymous `atr_` record containing target, opportunity, asset, publication-plan and search-distribution lineage. The allowlisted model is explicit: `deterministic_last_verified_touch` v`1.0.0`, with explicit bounded confidence.

## Safety controls
- Requires Node 27 schema/capture version, stable `slc_` lead identifier, explicit granted consent and literal `external_action: false`.
- Requires the complete inherited Node 26 route, CTA, source/channel and upstream lineage, with a credential-free HTTPS `.test` destination.
- Recursively rejects PII, missing/broken or ambiguous lineage, non-test destinations, execution requests, unknown model/version, malformed confidence and unknown model fields.
- `LocalAttributionRepository` is caller-selected local JSON persistence only; it supports byte-identical idempotency and rejects same-ID conflicts. No network, tracking client, contact or execution capability exists.

## Validation
`python -m py_compile ... && python epics/ep_050_distribution_engine/implementation/node_28/test_offline_attribution.py` — PASS, 6/6 in 0.441s with socket construction blocked. The real Node 19→20→21→26→27→28 fixture path, lineage/consent preservation, deterministic output, JSON persistence/idempotency, conflict, and safety-negative behavior are exercised.

## Evidence and status
Workflow/checklist: `workstream/600_workflow/ep050/EP050_node_28_offline_attribution_{workflow,implementation_checklist}.html`; fixture/tests: `implementation/node_28/`; procedure: `test_library/hermes/EP050_node_28_offline_attribution_regression_procedure.md`; timestamped evidence: `evidence/node_28/20260817_120156/`.

Node 28 is **90% evidenced pending allocator acceptance**. It makes no claim of live tracking or external behavior. No network, contact, routing, publishing, PII collection, credential use or external action occurred.
