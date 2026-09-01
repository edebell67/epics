# EP050 Node 27 — Structured Lead Capture evidence

- Captured: 2026-08-17 11:14:11 +01:00
- Boundary: deterministic local fixtures only; socket construction is blocked by the regression test.
- Command: `python -m py_compile epics/ep_050_distribution_engine/implementation/node_27/structured_lead_capture.py epics/ep_050_distribution_engine/implementation/node_27/test_structured_lead_capture.py && python epics/ep_050_distribution_engine/implementation/node_27/test_structured_lead_capture.py`
- Result: **PASS — 7/7**.
- Coverage: real Node 19→20→21→26→27 lineage; consent enforcement; approved PII-free schema; source/route/destination safety; deterministic `slc_` identifiers; local persistence/idempotency; conflict detection; no-network guard.
- No network, live capture, contact, routing execution, publication, PII collection, credentials, or external action occurred.
