# EP050 Node 26 Smart Destination Router — regression procedure

## Scope and safety
Run only local fixture tests. The router recommends an inert HTTPS `.test` URL and must never execute it. No network, publication, routing, lead capture, CMS, credentials, or external action is permitted.

## Preconditions
- Node 19 approved synthetic asset fixture is available at `implementation/node_21/fixtures/approved_search_asset_fixture.json`.
- Node 20 and Node 21 modules are locally importable.
- Node 21 has been explicitly accepted by the allocator.

## Procedure
1. Run:
   ```bash
   python -m py_compile epics/ep_050_distribution_engine/implementation/node_26/smart_destination_router.py epics/ep_050_distribution_engine/implementation/node_26/test_smart_destination_router.py
   python epics/ep_050_distribution_engine/implementation/node_26/test_smart_destination_router.py
   ```
2. Confirm all nine tests pass with socket construction blocked.
3. Confirm the positive route has stable `sdr_` ID, exact Node 20/21 lineage, HTTPS `.test` destination, approval/compliance fields, and literal `external_action: false`.
4. Confirm negative coverage rejects altered Node 21 output, unknown rule, non-`.test` destination, PII, external execution request, invalid deferred-state claim, and broken lineage.
5. Confirm persisted duplicate input is idempotent and altered duplicate is a conflict.

## Expected result
PASS: 9/9 tests. Any validation failure or an attempt to perform external activity is a stop condition. Preserve all evidence; do not deploy or route anyone.
