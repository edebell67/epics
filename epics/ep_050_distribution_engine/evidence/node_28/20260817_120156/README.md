# EP050 Node 28 Offline Attribution — evidence

- Timestamp: 2026-08-17T12:01:56+01:00
- Allocation: `20260817T114855470_codex_2a6ff5e3`
- Claim: `20260817T120245389_hermes_9f1c05a5`
- Upstream closure: Node 27 accepted by `20260817T114855127_codex_260d860e`
- Scope: offline Node 28 only; no source edits outside its implementation directory.

## Validation command and result
```text
python -m py_compile epics/ep_050_distribution_engine/implementation/node_28/offline_attribution.py epics/ep_050_distribution_engine/implementation/node_28/test_offline_attribution.py && python epics/ep_050_distribution_engine/implementation/node_28/test_offline_attribution.py
......
----------------------------------------------------------------------
Ran 6 tests in 0.441s

OK
```

The test replaces `socket.socket` with an assertion failure before constructing the real Node 19→20→21→26→27→28 path. It therefore proves no socket creation is needed by the complete test path. It covers consent and lineage retention, deterministic output, local persistence/idempotency, conflict detection, and fail-closed safety negatives.

## Safety result
All output records use literal `external_action: false`. The implementation has local JSON persistence only. No network call, live tracking, contact, routing, publishing, PII collection, credentials or external action occurred.
