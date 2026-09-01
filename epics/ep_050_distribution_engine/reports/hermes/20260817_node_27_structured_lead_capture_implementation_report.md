# EP050 Node 27 — Structured Lead Capture implementation report

## Outcome
Implemented `implementation/node_27/structured_lead_capture.py`, a deterministic local-only capture-record builder consuming a validated Node 26 route and bounded consented intake. It emits a stable pseudonymous `slc_` `lead_id`, consent evidence, session/source context, route/destination/CTA/channel lineage, target/opportunity/asset/publication/search identifiers, and literal `external_action: false`.

## Safety controls
- Requires a valid, non-executing Node 26 `sdr_` route and credential-free HTTPS `.test` destination.
- Intake schema is allowlisted to a pseudonymous session ID, inherited source and explicit consent evidence; all other fields fail closed.
- Rejects PII patterns, missing/invalid consent, invalid timestamp, source mismatch, route lineage failures, non-test destination and execution requests.
- `LocalLeadCaptureRepository` is local JSON-only; it supports idempotent replay and detects same-ID record conflicts. There is no transport, contact or execution code.

## Validation
`python -m py_compile ... && python epics/ep_050_distribution_engine/implementation/node_27/test_structured_lead_capture.py` — PASS, 7/7 with socket construction blocked. The suite exercises the real Node 19→20→21→26→27 fixture path plus deterministic, persistence/idempotency, conflict and negative safety coverage.

## Evidence and status
Workflow/checklist: `workstream/600_workflow/ep050/EP050_node_27_structured_lead_capture_{workflow,implementation_checklist}.html`; fixture: `implementation/node_27/fixtures/approved_structured_lead_capture_fixture.json`; procedure: `test_library/hermes/EP050_node_27_structured_lead_capture_regression_procedure.md`; initial timestamped evidence: `evidence/node_27/20260817_111411/`; amendment assessment and rerun: `evidence/node_27/20260817_112815_obsidian_reconciliation/`; directly authorized mirror/index completion evidence: `evidence/node_27/20260817_1142_direct_authorized_obsidian_reconciliation/`.

Node 27 is **100% accepted** by allocator event `20260817T114855127_codex_260d860e`. The directly authorized, history-preserving Obsidian lifecycle mirror and three index references are complete and byte-identity verified; the post-reconciliation socket-blocked regression passed 7/7 in 0.437s. No network, live capture, contact, routing execution, publication, PII collection, credentials or external action occurred.
