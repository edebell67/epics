# EP050 Node 19 -> Node 20 Consumer-Corrected Contract Candidate

> VERSION HISTORY
> - v1.1.0-candidate · 2026-08-16 · Hermes consumer-corrected candidate; does not replace the Gemini producer proposal.

**Allocation:** `20260816T232607325_codex_89089faa`  
**Status:** Consumer candidate — pending Gemini producer review and Codex canonical decision.  
**Scope:** Fixture-only contract and offline validation. **Node 20 implementation: 0%.**

## Provenance and non-replacement

This is a new Hermes-owned candidate derived from Gemini's read-only proposal `integration/proposals/gemini/20260816_node19_to_node20_contract_proposal_v1.md` and the six findings in Hermes' review `integration/reviews/hermes/20260816_node19_to_node20_consumer_contract_review.md`. It neither edits nor supersedes the producer proposal and is not a canonical contract.

The machine-readable candidate is `20260816_node19_to_node20_consumer_contract_candidate_v1_1.json`.

## Corrected contract

1. **Complete fail-closed compliance.** `approved`, `disclaimer_verified`, and `facts_verified` each have the literal value `true`; `checked_at` is a non-empty ISO-8601 timestamp and `validator_version` is non-empty.
2. **Strict input and lineage.** Every object rejects additional properties. Required textual identity/content fields use `minLength: 1`; `steps` and `target_channels` use `minItems: 1`; timestamps are schema-format and consumer ISO-8601 checked. Each non-empty UTM field is typed, and `tracking_params.asset_id` must equal package `asset_id`.
3. **Safe fixture destination.** `destination_url` is an HTTPS `.test` hostname only. A consumer must reject arbitrary, non-HTTPS, or real destinations.
4. **Scheduling facts.** `schedule_request` explicitly supplies the selected channel, non-empty audience, and scheduled time. The channel must be declared in `target_channels`; this supplies Node 20's required what → where → when → audience → CTA planning data.
5. **Idempotency.** `publication_plan_id` is `mpp_` plus SHA-256 of canonical sorted UTF-8 JSON comprising `asset_id`, selected `channel`, destination URL, audience, and scheduled time. Same key returns the same mock plan; a replay with the same id but any different output field is a conflict and must be rejected.
6. **Output boundary.** The mock publication-plan schema requires lineage (`asset_id`, `target_id`, `opportunity_id`), selected channel/audience/time, CTA, `approval_state: "approved"`, and literal `external_action: false`. It declares no adapter, credential, queue, request, or publishing behavior.

## Offline validation

`python epics/ep_050_distribution_engine/integration/reviews/hermes/node19_to_node20_candidate_v1_1_test.py`

Result: **12/12 passed**: accepted approved fixture/stable output; rejected three compliance failures, unsafe destination, lineage mismatch, empty text, invalid timestamp, undeclared schedule channel, extra input property, and external-action output; confirmed no socket use.

## Promotion and implementation gate

Gemini must review this consumer candidate for producer compatibility, then Codex must issue a canonical-promotion decision. Separately, Node 19 must be evidenced at 100% and the combined MVP gate must be approved before a new Node 20 mock-only implementation allocation. Until then this candidate creates no Node 20 implementation, plan record, publishing activity, or external action.
