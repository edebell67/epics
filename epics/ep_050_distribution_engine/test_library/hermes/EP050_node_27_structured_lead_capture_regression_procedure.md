# EP050 Node 27 — Structured Lead Capture regression procedure

## Boundary
Run locally only. The suite deliberately replaces `socket.socket` with an exception and uses only `https://*.test` identifiers. Do not add transport, external capture, contact, routing execution, publication, credentials, or PII.

## Command
```bash
python -m py_compile epics/ep_050_distribution_engine/implementation/node_27/structured_lead_capture.py epics/ep_050_distribution_engine/implementation/node_27/test_structured_lead_capture.py
python epics/ep_050_distribution_engine/implementation/node_27/test_structured_lead_capture.py
```

## Expected result
Seven tests pass: real Node 19→20→21→26→27 lineage, deterministic identifier/record construction, local persistence/idempotency, same-ID conflict rejection, invalid consent rejection, PII/unknown-schema/source mismatch rejection, and non-`.test` or execution-request rejection. Any socket construction fails the test.
