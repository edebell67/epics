# EP050 Combined MVP Comparison Matrix (Non-Authoritative)

> VERSION HISTORY
> - v1.1.0 · 2026-08-16 · Reconciled node counts and arithmetic: 21 active core nodes (14 Automated A + 7 Manual B), 16 deferred nodes (9 C + 2 D + 1 E + 4 non-active B), total 37 nodes.
> - v1.0.0 · 2026-08-16 · Initial non-authoritative comparative analysis of Claude (01–10), Gemini (11–19), and Hermes (20–37) MVP proposals.

**Status:** Non-authoritative comparative analysis prepared for orchestrator (Codex) review and final MVP reconciliation.  
**Scope:** Complete cross-owner analysis of all 37 EP050 Distribution Engine nodes across all 7 stages.  
**Sources:**
- `epics/ep_050_distribution_engine/distribution_engine_master_spec.md`
- Claude Nodes 01–10 Report: `epics/ep_050_distribution_engine/reports/claude/20260816_ep050_nodes_01_10_mvp_classification.md`
- Gemini Nodes 11–19 Report: `epics/ep_050_distribution_engine/reports/gemini/20260816_ep050_nodes_11_19_mvp_classification.md`
- Hermes Nodes 20–37 Report: `epics/ep_050_distribution_engine/reports/hermes/20260816_ep050_nodes_20_37_mvp_classification.md`
- Interface Proposals: `integration/proposals/gemini/20260816_node10_to_node11_contract_proposal_v1.md` (v1.1.0) and `20260816_node19_to_node20_contract_proposal_v1.md` (v1.0.0)
- Producer Review: `epics/ep_050_distribution_engine/reports/claude/20260816_node05_to_node11_contract_producer_review.md`

---

## 1. Executive Summary & Combined MVP Feasibility (24–48 Hours)

All three owner reports independently converge on a **coherent, minimal, 100% offline, deterministic learning loop** using a single confirmed synthetic target (`service=boiler_repair`, `market=domestic_plumbing`, `geography=Blackheath, London, UK`).

### Exact Node Count Breakdown:
- **Total Engine Nodes:** **37**
- **Active Core MVP Nodes:** **21 nodes** (14 Automated `A` + 7 Safe Manual/Curated `B`)
  - **Claude Range (Nodes 01–10):** **5 active nodes** (4 Automated `A` [01, 02, 04, 05] + 1 Manual `B` [03]; Node 06 folded into 05 fixture; Nodes 07–10 deferred).
  - **Gemini Range (Nodes 11–19):** **7 active nodes** (6 Automated `A` [11, 12, 14, 16, 17, 19] + 1 Manual `B` [13]; Nodes 15, 18 deferred).
  - **Hermes Range (Nodes 20–37):** **9 active nodes** (4 Automated `A` [26, 27, 28, 31] + 5 Manual `B` [20, 21, 29, 30, 33]; Nodes 22–25, 32, 34–37 deferred).
- **Deferred Nodes for Scale:** **16 nodes** (9 `C`, 2 `D`, 1 `E`, 4 deferred/folded `B`):
  - Category C (Automate Next): Nodes 07, 08, 09, 15, 18, 22, 32, 34, 35.
  - Category D (Scale Capability): Nodes 10, 37.
  - Category E (Advanced Intelligence): Node 36.
  - Category B Deferred from MVP loop: Node 06 (folded into 05), Node 23 (optional social), Node 24 (community), Node 25 (partnerships).
- **External Action / Credit Consumption:** **0%** (All scrapers, crawlers, generative video rendering, paid LLM APIs, and live outbound communications are disabled or substituted with validated local fixtures).
- **24–48 Hour Feasibility:** **High**. Because the core loop relies on deterministic mathematical formulas, rule-based schema transforms, verified JSON knowledge packs, and offline mock intake/routing queues, the full 21-node end-to-end pipeline can be implemented, unit-tested, and contract-validated sequentially within 24–48 hours once authorized.

---

## 2. Comprehensive 37-Node Master Classification Matrix

| Node | Stage | Owner | Class | MVP Status | Role & Execution Mode in First Learning Loop |
|---|---|---|---|---|---|
| **01 App / Service Registration** | 1 Ingestion | Claude | **A** | **Active MVP (1/21)** | Registers the single synthetic target (`tgt_boiler_repair_blackheath`) in local datastore. |
| **02 Product Intelligence** | 1 Ingestion | Claude | **A** | **Active MVP (2/21)** | Manually authors problem/solution/commercial model descriptive context for target. |
| **03 Audience Definition** | 1 Ingestion | Claude | **B** | **Active MVP (3/21)** | Pins single audience segment (Blackheath homeowner with boiler pressure drop). |
| **04 Conversion Definition** | 1 Ingestion | Claude | **A** | **Active MVP (4/21)** | Pinned 8-stage funnel definition (`Visit` $\to$ `Enquiry` $\to$ `Lead` $\to$ `Booking` $\to$ `Revenue`). |
| **05 Search Demand Discovery** | 2 Demand Intel | Claude | **A** | **Active MVP (5/21)** | Ingests 3–5 curated search queries (e.g. "boiler pressure dropped to zero no hot water"). |
| **06 Question Discovery** | 2 Demand Intel | Claude | **B** | *Folded in* | Folded into Node 05 manual search query fixture; distinct pipeline deferred. |
| **07 Social / Video Discovery** | 2 Demand Intel | Claude | **C** | *Deferred (1/16)* | YouTube/TikTok/Reddit ingestion pipeline deferred. |
| **08 Competitor Intelligence** | 2 Demand Intel | Claude | **C** | *Deferred (2/16)* | Benchmarking and competitor crawler deferred. |
| **09 Community Intelligence** | 2 Demand Intel | Claude | **C** | *Deferred (3/16)* | Community crawler deferred; strict non-spam guardrail preserved. |
| **10 Trend Detection** | 2 Demand Intel | Claude | **D** | *Deferred (4/16)* | Requires multi-date historical volume; bypassed for single seed signal. |
| **11 Intent Classification** | 3 Strategy | Gemini | **A** | **Active MVP (6/21)** | Deterministic taxonomy mapping (query $\to$ `troubleshooting` + `urgent`). |
| **12 Opportunity Scoring** | 3 Strategy | Gemini | **A** | **Active MVP (7/21)** | Deterministic weighted formula: `(Vol*0.25)+(Intent*0.30)+(Urg*0.20)+(Ease*0.15)+(Rel*0.10)`. |
| **13 Demand Path Discovery** | 3 Strategy | Gemini | **B** | **Active MVP (8/21)** | Manually-pinned 5-stage buyer journey (Trigger $\to$ Symptom $\to$ Diagnostic $\to$ Provider $\to$ Quote). |
| **14 Channel Selection** | 3 Strategy | Gemini | **A** | **Active MVP (9/21)** | Deterministic suitability rules map Troubleshooting + Urgent to `search_landing`. |
| **15 Campaign Clustering** | 3 Strategy | Gemini | **C** | *Deferred (5/16)* | Multi-opportunity clustering algorithms deferred; passes 1-item opportunity directly. |
| **16 Canonical Knowledge Store** | 4 Content/Asset | Gemini | **A** | **Active MVP (10/21)** | Curated JSON fact-base (normal bar pressure 1.0–1.5, repressurising steps, Gas Safe warnings). |
| **17 Content & Utility Factory** | 4 Content/Asset | Gemini | **A** | **Active MVP (11/21)** | Template-driven offline generation of Troubleshooting FAQ/Guide with emergency quote CTA. |
| **18 Video Asset Factory** | 4 Content/Asset | Gemini | **C** | *Deferred (6/16)* | Video rendering pipeline deferred; offline storyboard/script mock fixture only. |
| **19 Quality & Compliance** | 4 Content/Asset | Gemini | **A** | **Active MVP (12/21)** | Deterministic hard stop-gate validating truthfulness, disclaimer presence, and CTA schema. |
| **20 Publishing Scheduler** | 5 Distribution | Hermes | **B** | **Active MVP (13/21)** | Authors mock placement plan for search landing asset with `external_action=false`. |
| **21 Search Distribution** | 5 Distribution | Hermes | **B** | **Active MVP (14/21)** | Prepares landing page placement metadata & tracking tags; no live indexing submission. |
| **22 Video Distribution** | 5 Distribution | Hermes | **C** | *Deferred (7/16)* | Video channel publishing adapters deferred. |
| **23 Social Distribution** | 5 Distribution | Hermes | **B** | *Deferred (8/16)* | Optional non-publishing social post fixture; live posting deferred. |
| **24 Community Participation** | 5 Distribution | Hermes | **B** | *Deferred (9/16)* | Live outreach deferred; non-spam guardrail strictly maintained. |
| **25 Syndication / Partner** | 5 Distribution | Hermes | **B** | *Deferred (10/16)* | Partner outreach deferred. |
| **26 Smart Destination Router** | 6 Lifecycle | Hermes | **A** | **Active MVP (15/21)** | Deterministic routing of intent/asset context to approved mock landing route. |
| **27 Lead Capture** | 6 Lifecycle | Hermes | **A** | **Active MVP (16/21)** | Structured intake creating pseudonymous `lead_id` preserving acquisition lineage. |
| **28 Attribution** | 6 Lifecycle | Hermes | **A** | **Active MVP (17/21)** | Invariant preservation of UTM campaign, origin signal, asset ID, and channel metadata. |
| **29 Lead Qualification** | 6 Lifecycle | Hermes | **B** | **Active MVP (18/21)** | Explicit qualification checklist (geography match, emergency urgency, contactability). |
| **30 Lead Routing** | 6 Lifecycle | Hermes | **B** | **Active MVP (19/21)** | Routes qualified lead strictly to local allowlisted mock queue; real transmission blocked. |
| **31 Lifecycle Tracking** | 6 Lifecycle | Hermes | **A** | **Active MVP (20/21)** | Finite state machine tracking ordered lead lifecycle (`Enquiry` $\to$ `Qualified` $\to$ `Converted`). |
| **32 Performance Warehouse** | 7 Learning | Hermes | **C** | *Deferred (11/16)* | Bounded local JSON event log used in place of durable multi-model warehouse. |
| **33 Outcome Feedback** | 7 Learning | Hermes | **B** | **Active MVP (21/21)** | Validated feedback record with provenance linking revenue/booking outcome to `lead_id`. |
| **34 Winner Detection** | 7 Learning | Hermes | **C** | *Deferred (12/16)* | Multi-cohort statistical winner algorithms deferred until multi-loop volume accumulates. |
| **35 Amplification Engine** | 7 Learning | Hermes | **C** | *Deferred (13/16)* | Automated budget/creative amplification deferred. |
| **36 Distribution Investment**| 7 Learning | Hermes | **E** | *Deferred (14/16)* | Long-term portfolio capital allocation modeling deferred. |
| **37 Knowledge Base Store** | 7 Learning | Hermes | **D** | *Deferred (15/16)* | Automated cross-loop semantic learning store deferred. |

---

## 3. End-to-End Flow of the Proposed 21-Node MVP

```text
[Stage 1: Ingestion — Claude (4 active nodes)]
Node 01 (Target Registration: boiler_repair/Blackheath) [A]
  │
  ├─► Node 02 (Product Intelligence: problem/solution description) [A]
  ├─► Node 03 (Audience Definition: Blackheath homeowner segment) [B]
  └─► Node 04 (Conversion Definition: 8-stage funnel definition) [A]
  │
[Stage 2: Demand Intelligence — Claude (1 active node)]
Node 05 (Search Demand Discovery: curated "low boiler pressure" query) [A]
  │
  ▼  ◄─── [Contract Gate 1: Node 05 -> Node 11 Proposal v1.1.0] (Reviewed & Approved by Claude)
[Stage 3: Strategy & Planning — Gemini (4 active nodes)]
Node 11 (Intent Classification: troubleshooting + urgent) [A]
  │
  ├─► Node 12 (Opportunity Scoring: formula score = 84.5 / Priority Tier 1) [A]
  ├─► Node 13 (Demand Path Discovery: 5-stage symptom-to-quote journey) [B]
  └─► Node 14 (Channel Selection: search_landing direct response) [A]
  │
[Stage 4: Asset & Content Creation — Gemini (3 active nodes)]
Node 16 (Canonical Knowledge: verified 1.0-1.5 bar repressurising facts + safety disclaimer) [A]
  │
  ├─► Node 17 (Content Factory: Boiler Pressure FAQ/Guide + CTA schema) [A]
  └─► Node 19 (Quality & Compliance: 100% truthfulness & safety validation pass) [A]
  │
  ▼  ◄─── [Contract Gate 2: Node 19 -> Node 20 Proposal v1.0.0] (Awaiting Hermes task session review)
[Stage 5: Distribution & Scheduling — Hermes (2 active nodes)]
Node 20 (Publishing Scheduler: mock search placement plan, external_action=false) [B]
  │
  └─► Node 21 (Search Distribution: landing page placement metadata & tracking) [B]
  │
[Stage 6: Lead Lifecycle & Conversion — Hermes (6 active nodes)]
Node 26 (Destination Router: maps to mock quote intake route) [A]
  │
  ├─► Node 27 (Lead Capture: generates pseudonymous lead_id with acquisition lineage) [A]
  ├─► Node 28 (Attribution: preserves full UTM, asset_id, signal_id tags) [A]
  ├─► Node 29 (Lead Qualification: checklist validation for Blackheath location & urgency) [B]
  ├─► Node 30 (Lead Routing: dispatches strictly to local mock queue) [B]
  └─► Node 31 (Lifecycle Tracking: state transition from Enquiry -> Qualified -> Closed_Won) [A]
  │
[Stage 7: Learning & Outcome Feedback — Hermes (1 active node)]
Node 33 (Outcome Feedback: records confirmed booking value & feedback loop to asset/signal) [B]
```

---

## 4. Cross-Stage Contract Gates & Status

1. **Stage 2 $\to$ Stage 3 Boundary (`Node 05 -> Node 11`):**
   - **Proposal:** `epics/ep_050_distribution_engine/integration/proposals/gemini/20260816_node10_to_node11_contract_proposal_v1.md` (v1.1.0)
   - **Producer Review:** `epics/ep_050_distribution_engine/reports/claude/20260816_node05_to_node11_contract_producer_review.md`
   - **Validation:** 3/3 automated `jsonschema.validate` checks passed (valid payload passed, invalid enum rejected, missing geography rejected).
   - **Gate Status:** **Ready for canonical promotion by Codex**.

2. **Stage 4 $\to$ Stage 5 Boundary (`Node 19 -> Node 20`):**
   - **Proposal:** `epics/ep_050_distribution_engine/integration/proposals/gemini/20260816_node19_to_node20_contract_proposal_v1.md` (v1.0.0)
   - **Consumer Review:** Parked pending user authorization for a Hermes repository task session.
   - **Validation:** `jsonschema.validate` passed against seed fixture.
   - **Gate Status:** **Awaiting Hermes consumer review or orchestrator review**.

---

## 5. Risk Assessment & Safety Boundaries

| Risk Area | Risk Level | Mitigation & Guardrail in Combined MVP |
|---|---|---|
| **External API / Credit Consumption** | Low | Generative video and live search query APIs are 100% disabled; template/mock generator used. |
| **Spam / Unsolicited Community Outreach** | None | Community Participation (Nodes 09, 24) and Social Outreach (Nodes 23, 25) are deferred; no automated posting capability exists. |
| **PII / Privacy Exposure** | Low | Lead Capture (Node 27) enforces pseudonymous `lead_id` and stores zero plain-text customer phone/email in test fixtures. |
| **Production Datastore Overlap** | None | EP050 operates strictly in standalone local storage under `epics/ep_050_distribution_engine/`; zero read/write to EP043, EP047, or EP048 databases. |
| **Hallucinated / Unsafe Content** | Low | Node 16 Canonical Knowledge Store pins verified facts, and Node 19 Quality Gate rejects any asset without Gas Safe safety disclaimers. |

---

## 6. Recommendations for Orchestrator (Codex) Decision

1. **Approve the 21-Node Combined MVP Subset:** Formally authorize the 21 active core nodes (`01, 02, 03, 04, 05, 11, 12, 13, 14, 16, 17, 19, 20, 21, 26, 27, 28, 29, 30, 31, 33`) as the target delivery baseline.
2. **Promote Node 05 $\to$ 11 Contract to Canonical:** Move `integration/proposals/gemini/20260816_node10_to_node11_contract_proposal_v1.md` (v1.1.0) to `integration/canonical_contracts/` as the approved contract.
3. **Authorize Sequential Implementation Tasks:**
   - Authorize Claude to begin Node 01 $\to$ 05 sequential delivery (Node 01 already allocated).
   - On Node 05 evidenced completion, unblock Gemini for Node 11 $\to$ 19 delivery.
   - On Node 19 evidenced completion, unblock Hermes for Node 20 $\to$ 33 delivery.
