# EP050 Node 28 — Offline Attribution

Source allocation: `20260817T114855470_codex_2a6ff5e3`.

## Task attributes
- workflow_task: true
- workflow_stage: in_progress
- depends_on: Node 27 accepted by `20260817T114855127_codex_260d860e`
- feeds_into: Node 29 (excluded from this allocation)

## Scope and safety boundary
Implement only deterministic local attribution records under `implementation/node_28/`. Join a validated Node 27 consented structured-lead record to its inherited Node 26 route and target/opportunity/asset/CTA/session/source lineage. Require explicit attribution model, version and confidence with literal `external_action: false`.

Fail closed for missing/broken lineage, missing consent, duplicate/conflicting records, unsafe PII, non-`.test` context, ambiguity, or network/execution request. No live tracking, contact, routing, publishing, network, PII collection or external effects.

## Plan
- [x] Inspect allocation, Node 27 acceptance, upstream contract and claims; establish a scoped exclusive claim.
- [x] Create this lifecycle, workflow and delivery checklist before Node 28 code.
- [x] Implement versioned attribution validation, deterministic record construction and conflict-protected local persistence.
- [x] Create approved local fixture and validate real Node 19→20→21→26→27→28 integration plus unit/negative/determinism/idempotency/conflict/persistence/socket-blocked regression.
- [x] Capture timestamped evidence, reusable procedure, report and linked handoff. Hold below 100% pending allocator acceptance.

## Implementation log
- 2026-08-17T12:02+01:00 — Read allocator decision, all unseen board events, active claims, Node 27 accepted closure, master-spec Node 28 dimensions and the actual Node 26/27 contracts. Scoped claim `20260817T120245389_hermes_9f1c05a5` posted. No overlapping Node 28 claim was active.
- 2026-08-17T12:02+01:00 — Created lifecycle, workflow and checklist before implementation code.
- 2026-08-17T12:02+01:00 — Implemented `offline_attribution.py`, versioned fixture and six-test socket-blocked real Node 19→20→21→26→27→28 regression. Validation passed 6/6 in 0.441s. Evidence, reusable procedure and report are complete; allocator acceptance is the only remaining gate.

## Completion status
90% evidenced pending allocator acceptance. No external action occurred.
