# EP050 Node 28 Offline Attribution regression procedure

## Purpose
Verify the Node 28 contract consumes the real offline Node 19→20→21→26→27 fixture chain and produces an inert, consent-preserving attribution record.

## Preconditions
Run from repository root. No service, credentials, network, production data or external adapter is required.

## Command
```bash
python -m py_compile epics/ep_050_distribution_engine/implementation/node_28/offline_attribution.py epics/ep_050_distribution_engine/implementation/node_28/test_offline_attribution.py && python epics/ep_050_distribution_engine/implementation/node_28/test_offline_attribution.py
```

## Expected result
Six tests pass while `socket.socket` construction is replaced with an assertion failure. Coverage proves real upstream integration, complete lead/consent/route/lineage retention, deterministic replay, JSON persistence/idempotency, conflict rejection, and fail-closed rejection of missing consent, broken lineage, PII, non-`.test` destination, execution flag and ambiguous/unallowlisted attribution model.

## Safety assertion
`offline_attribution.py` contains no transport or external adapter. Every output has literal `external_action: false`; the test path blocks socket construction. All persistence is caller-selected local JSON only.
