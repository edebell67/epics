# EP050 Node 19 -> Node 20 Consumer Contract Review

> VERSION HISTORY
> - v1.0.0 · 2026-08-16 · Initial Hermes consumer review of proposal v1.0.0 using offline fail-closed checks.

**Allocation:** `20260816T231616437_codex_63402803`  
**Proposal reviewed:** `integration/proposals/gemini/20260816_node19_to_node20_contract_proposal_v1.md`  
**Consumer:** Node 20 Publishing Scheduler (mock-only)  
**Decision:** **APPROVE WITH CHANGES** — safe as a planning proposal, not ready for canonical promotion or Node 20 implementation.

## Positive findings

- Required top-level identity and lineage fields include `asset_id`, `target_id`, and `opportunity_id`.
- The proposal requires a compliance stamp and states that Node 20 rejects `approved != true`.
- The declared target channels and CTA provide the core `what -> where -> CTA` scheduling inputs.
- Rule 3 explicitly limits output to a mock record with `external_action=false`, consistent with EP050 safety boundaries.

## Required changes before canonical promotion

1. **Fail-closed compliance:** require and consumer-enforce `approved`, `disclaimer_verified`, and `facts_verified` all equal to `true`; require non-empty `checked_at` and `validator_version`.
2. **Lineage integrity:** enforce `cta_definition.tracking_params.asset_id == asset_id`; type and require each UTM field as a non-empty string.
3. **Destination safety:** constrain Node 20 fixtures to an HTTPS synthetic/allowlisted destination (for current offline MVP, a `.test` hostname). Node 20 must not schedule arbitrary URLs.
4. **Schema strictness:** add `additionalProperties: false`, `minLength: 1` to identity/text fields, `minItems: 1` to `steps` and `target_channels`, and a format checker for both timestamps.
5. **Idempotency:** add required `publication_plan_id` (deterministically derived from asset, channel, destination, audience, and scheduled time) plus `schema_version`. Node 20 must produce one stable mock plan for the same key and reject a conflicting replay.
6. **Explicit consumer output boundary:** define a Node 20 mock-plan schema containing `publication_plan_id`, input lineage, channel, audience, scheduled time, CTA, `approval_state`, and literal `external_action: false`. No publishing adapter may be included.

## Executed offline validation

`python epics/ep_050_distribution_engine/integration/reviews/hermes/node19_to_node20_contract_test.py`

The positive fixture passed. Six negative cases were rejected: unapproved stamp, unverified disclaimer, unverified facts, unsafe destination, tracking lineage mismatch, and empty channels. This test defines the consumer's required fail-closed behavior; it also demonstrates requirements not fully constrained by proposal v1.0.0.

## Gate and next protected action

Node 20 remains **0% implementation**. The Node 19 evidence/implementation gate remains independently unmet. Gemini should revise the proposal or Codex should issue an approved canonical contract incorporating the six changes; only then may a separately allocated Node 20 implementation claim be considered. No external action was performed.
