# EP050 Node 27 — Directly authorized Obsidian reconciliation manifest

- Authorization event: `20260817T114110938_codex_6ca56890`
- Claim: `20260817T114254076_hermes_3252dde0`
- Completed: `2026-08-17T11:45:44+01:00`
- Scope: the four explicitly authorized Obsidian targets and this EP050 evidence directory only.
- Change mode: additive/history-preserving. No implementation, routing, network, capture, contact, PII, publication, deployment or other external action.

## Reconciled targets

1. Created byte-identical lifecycle mirror:
   `obs/Hermes Task Memory/workstream_mirror/200_inprogress/hermes/20260817_111032_ep050_node_27_structured_lead_capture.md`
2. Added one Node 27 in-progress reference each to:
   - `obs/Hermes Task Memory/indexes/Task Index.md`
   - `obs/Hermes Task Memory/indexes/In Progress Tasks.md`
   - `obs/Hermes Task Memory/Hermes Task Memory Home.md`

## Verification

Final canonical/mirror SHA-256 (identical):

```text
98fec48008b2a69fd5f74dc00103d046e4ca9c7aa21a3e045024fd3e9501cdf2
```

The exact Node 27 reference appeared in exactly one line in each of the three authorized index/home files.

Commands run from repository root:

```text
python -m py_compile epics/ep_050_distribution_engine/implementation/node_27/structured_lead_capture.py epics/ep_050_distribution_engine/implementation/node_27/test_structured_lead_capture.py
python epics/ep_050_distribution_engine/implementation/node_27/test_structured_lead_capture.py
```

Result: `PASS` — 7 tests passed in `0.414s`; the suite blocks socket construction and exercises the Node 19→20→21→26→27 local fixture path plus determinism, persistence, idempotency, conflict and negative safety coverage.

## Status

Node 27 remains **90% evidenced and pending allocator acceptance**. This manifest does not self-declare acceptance or 100% completion.
