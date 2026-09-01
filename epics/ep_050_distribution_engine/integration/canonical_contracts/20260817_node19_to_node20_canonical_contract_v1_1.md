# EP050 Stage 4 to Stage 5 Canonical Interface Contract (v1.1.0)

> VERSION HISTORY
> - v1.1.0 · 2026-08-17 · Promoted to CANONICAL CONTRACT by Codex decision `20260817T002606239_codex_e2cb088c` following Hermes consumer verification (12/12) and Gemini producer review approval (8/8).
> - v1.0.0 · 2026-08-16 · Initial candidate proposal.

**Contract ID:** `contract_node19_to_node20_v1_1`  
**Version:** `1.1.0`  
**Status:** **PROMOTED_CANONICAL**  
**Producer:** Stage 4 / Gemini (`Node 19: Quality & Compliance Review`)  
**Consumer:** Stage 5 / Hermes (`Node 20: Publishing Scheduler`)  

---

## 1. Provenance & Verification Trace

- **Orchestrator Decision:** `20260817T002606239_codex_e2cb088c`
- **Consumer Candidate Proposal:** [`epics/ep_050_distribution_engine/integration/proposals/hermes/20260816_node19_to_node20_consumer_contract_candidate_v1_1.json`](file:///C:/Users/edebe/eds/epics/ep_050_distribution_engine/integration/proposals/hermes/20260816_node19_to_node20_consumer_contract_candidate_v1_1.json)
  - Candidate SHA-256: `e6739e5c411480724c4fbc590c24b1c537a5bb4020325aa98ff59e3f1c66f19a`
  - Candidate Tests: 12/12 passed (Hermes consumer verification)
- **Producer Review Report:** [`epics/ep_050_distribution_engine/integration/reviews/gemini/20260817_node19_to_node20_producer_review_v1.md`](file:///C:/Users/edebe/eds/epics/ep_050_distribution_engine/integration/reviews/gemini/20260817_node19_to_node20_producer_review_v1.md)
  - Producer Decision: **APPROVED**
  - Producer Tests: 8/8 passed (Gemini schema/fixture suite)

---

## 2. Six Canonical Safety & Quality Invariants

1. **Explicit Compliance Stop-Gate:**
   Every approved asset package must contain a `compliance_stamp` with `approved=true`, `disclaimer_verified=true`, and `facts_verified=true`.
2. **End-to-End Lineage Preservation:**
   `target_id`, `opportunity_id`, and `tracking_params.asset_id` must match upstream lineage exactly.
3. **Safe Offline Destination URLs:**
   All destination URLs must match `^https://[A-Za-z0-9.-]+\\.test(?:/|$)`.
4. **Strict Non-Empty Attributes:**
   All required text fields enforce `minLength: 1` and RFC 3339 / ISO 8601 UTC date-times.
5. **Deterministic SHA-256 Plan ID:**
   `publication_plan_id` must be formatted as `^mpp_[a-f0-9]{64}$` computed from sorted canonical JSON keys.
6. **Zero External Action Boundary:**
   `external_action=false` is enforced at schema and execution level. Zero outbound HTTP requests or live publishing adapters.

---

## 3. Canonical JSON Schema Reference

The machine-readable canonical schema is located at:
[`epics/ep_050_distribution_engine/integration/canonical_contracts/20260817_node19_to_node20_canonical_contract_v1_1.json`](file:///C:/Users/edebe/eds/epics/ep_050_distribution_engine/integration/canonical_contracts/20260817_node19_to_node20_canonical_contract_v1_1.json)
