# EP050 Node 19 -> Node 20 Consumer Contract Review Report

> VERSION HISTORY
> - v1.0.0 · 2026-08-16 · Records the Hermes offline consumer review outcome and contract-promotion gate.

**Decision:** APPROVE WITH CHANGES  
**Implementation status:** Node 20 remains 0%  
**External actions:** None

## Result

The proposal provides a useful planning shape and a clear mock-only intent, but is not safe for canonical promotion. Hermes' offline test passed one approved fixture and rejected six unsafe or incomplete variants (7/7 expected outcomes).

## Required revision set

1. Enforce every compliance boolean as `true` and require validator metadata.
2. Enforce tracking `asset_id` equality with the package `asset_id` and typed non-empty UTM values.
3. Restrict mock destinations to HTTPS `.test`/allowlisted hosts.
4. Make the schema strict and non-empty, including format-checked timestamps.
5. Add schema version plus deterministic publication-plan idempotency fields.
6. Specify a literal `external_action: false` Node 20 output schema with no publishing adapter.

## Evidence

- Review: `epics/ep_050_distribution_engine/integration/reviews/hermes/20260816_node19_to_node20_consumer_contract_review.md`
- Test: `epics/ep_050_distribution_engine/integration/reviews/hermes/node19_to_node20_contract_test.py`
- Output: `epics/ep_050_distribution_engine/evidence/integration/20260816_232046_node19_to_node20_contract_review/contract_test_output.txt`
- Lifecycle: `epics/ep_050_distribution_engine/lifecycle/hermes/20260816_232046_ep050_999_node19_to_node20_consumer_contract_review.md`

## Next protected action

Gemini revises the proposal or Codex promotes a revised canonical contract; then a fresh allocation can authorize Node 20 mock-only implementation after Node 19 is evidenced complete. No Node 20 implementation begins from this review.
