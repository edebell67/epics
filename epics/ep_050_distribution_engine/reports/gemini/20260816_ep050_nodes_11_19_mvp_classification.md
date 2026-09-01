# EP050 Nodes 11–19 MVP Classification

> VERSION HISTORY
> - v1.0.0 · 2026-08-16 · Initial offline, planning-only classification for Gemini-owned Strategy and Asset/Content Creation nodes.

**Scope:** Nodes 11–19 only (Strategy & Planning: Nodes 11–15; Asset & Content Creation: Nodes 16–19).  
**Source:** `distribution_engine_master_spec.md` §§11–13, 36, 39–42; board decisions `20260816T194428761_codex_b733d113`, `20260816T194649992_codex_659cc2e1`, and planning clarifications `20260816T200204509_codex_f1c37d75` & `20260816T202149109_codex_99cab443`.  
**Decision boundary:** This is a classification proposal and contract baseline, not MVP approval and not implementation authorization. All `implementation/node_NN/` folders remain untouched. All proposed validation is deterministic, local, and mock/fixture based; it must not call external LLMs or media APIs, spend compute/rendering credits, make network requests, or mutate production systems.

Per confirmed orchestrator guidance:
1. Target context aligns with Claude's confirmed synthetic target: `service=boiler_repair`, `market=domestic plumbing`, `geography=Blackheath, London, UK`, `target_type=service_market`.
2. Nodes 17 & 18 execute 100% offline, deterministic, mock-driven tests without live API calls or external credit consumption.
3. Upstream input: Consumes Stage 2 output (Node 05/Node 10 raw demand signal fixture).
4. Downstream handoff: Produces Stage 4 approved asset output (Node 19 quality/compliance gate) feeding Hermes Stage 5 (Node 20 Publishing Scheduler).

---

## Classification Legend

- **A — Required for First Live Loop:** cannot acquire and learn from a lead without the capability.
- **B — Manual Initially:** conceptually needed, but safely human-operated for the first loop.
- **C — Automate Next:** valuable automation after the loop is proven.
- **D — Scale Capability:** needed as services, geographies, clients, or volume increase.
- **E — Advanced Intelligence:** requires accumulated outcome data and optimization maturity.

---

## Node-by-Node Classification

| Node | Classification | Rationale and dependency | Safe manual substitute | Local completion test | Candidate 24–48h MVP participation |
|---|---|---|---|---|---|
| 11 Intent Classification | **A** | Determines whether an incoming demand signal is troubleshooting, commercial, informational, urgent, or educational. Directly determines asset type and CTA structure. Depends on Stage 2 raw/curated demand signal (Node 05/10). | Rule-based keyword matching or pre-classified synthetic fixture for the seed boiler repair issue (e.g. low pressure $\to$ troubleshooting + urgent). | Fixture test passes normalized signal record; maps keywords to taxonomy enums; validates confidence score $>0.0$ and rejects unclassified/invalid enum states. | **Yes** |
| 12 Opportunity Scoring | **A** | Applies deterministic formula: `(Demand_Vol * 0.25) + (Commercial_Intent * 0.30) + (Urgency * 0.20) + (Ease_of_Capture * 0.15) + (Relevance * 0.10)` to rank opportunities and select the single seed path. Depends on Node 11. | Static weights and bounded scores (0–100) computed deterministically; no dynamic ML model needed. | Unit test executes exact mathematical formula on fixture inputs; verifies weighted sum, range clamping (0–100), and priority tier thresholding. | **Yes** |
| 13 Demand Path Discovery | **B** | Maps the buyer journey stages (Trigger $\to$ Symptom $\to$ Diagnostic $\to$ Provider Search $\to$ Conversion). Crucial conceptually, but for a single synthetic MVP opportunity, the path can be manually specified. Depends on Nodes 11–12. | Human authors a structured 5-stage buyer journey fixture for the synthetic boiler repair opportunity. | Schema validation test confirms journey stages are sequentially ordered, have explicit transition criteria, and match the target's conversion definition (Node 04). | **Yes, manually pinned** |
| 14 Channel Selection | **A** | Determines the best delivery mechanism (Search/Landing Page vs Social vs Video) for the scored opportunity. For boiler repair troubleshooting, maps intent to Search/Direct response. Depends on Nodes 11–13. | Deterministic channel-suitability matrix (e.g., Troubleshooting + Urgent $\to$ Search / Landing Page). | Fixture test evaluates opportunity attributes against channel rules; asserts Search/Landing Page selected with score $\ge 80$; rejects empty/ambiguous channel output. | **Yes** |
| 15 Campaign Clustering | **C** | Groups multiple related opportunities into unified campaign themes. Only relevant when dozens of signals exist across multiple sub-topics. Depends on Nodes 11–14. | Defer for single-seed MVP; pass single opportunity directly as a 1-item "cluster". | Mock adapter wraps single opportunity in cluster container schema without multi-item clustering algorithms. | No |
| 16 Canonical Knowledge Store | **A** | Single source of truth for verified facts, problem diagnosis, safety warnings, pricing baselines, and brand copy. Prevents generative hallucinations. Depends on Node 02 (Product Intelligence). | Human curates a verified JSON knowledge pack for the synthetic boiler repair target (e.g., normal pressure 1.0–1.5 bar, repressurising loop instructions, emergency safety warning). | Schema validation test asserts knowledge items have required keys (`fact_id`, `topic`, `claim`, `verification_source`, `safety_critical`); rejects unverified claims. | **Yes, curated fixture** |
| 17 Content & Utility Factory | **A** | Generates the core deliverable asset (e.g., "Boiler Pressure Dropped: Step-by-Step Fix & Local Engineer Checklist" FAQ/Guide with emergency quote CTA). Depends on Nodes 11, 14, 16. | Template-based deterministic generator combining Canonical Knowledge (Node 16) with Conversion CTA (Node 04); no live paid LLM API calls during automated tests. | Unit test verifies generated asset matches `AssetPayload` schema, includes mandatory disclaimer & CTA link, incorporates exact facts from Node 16, and passes length/structure rules. | **Yes, template/mock driven** |
| 18 Video Asset Factory | **C** | Generates video scripts, shot lists, and rendered clips. High value for multi-channel distribution, but text/search landing asset (Node 17) is sufficient for the first learning loop. Depends on Nodes 11, 14, 16. | Defer full video render pipeline. Produce offline synthetic script/storyboard artifact only; zero video render API/credit calls. | Mock test asserts script generator emits timed scene beats and CTA voiceover transcript against template; validates 100% offline fail-closed media adapter. | No (Optional script artifact only) |
| 19 Quality & Compliance Review | **A** | Mandatory hard stop-gate validating truthfulness, factual accuracy against Node 16, brand safety, legal disclaimers, and technical format readiness before Stage 5 publishing. Depends on Nodes 16–18. | Automated deterministic ruleset checking forbidden words, mandatory disclaimers, claim verification against Knowledge Store, and required CTA parameters. | Unit test matrix verifies that: (1) compliant asset passes with `approved=true`; (2) asset with unverified claims fails; (3) asset missing safety disclaimer fails; (4) asset with invalid CTA schema fails. | **Yes** |

---

## Candidate Combined MVP Contribution

The Gemini-owned contribution to the smallest complete learning loop is:

1. **Deterministic Intent & Opportunity Scoring:** Nodes 11 & 12 (classifying intent and ranking the opportunity using the master spec formula).
2. **Pinned Journey & Channel Mapping:** Node 13 (manually-pinned 5-stage journey fixture) and Node 14 (rule-based channel selection targeting Search/Web).
3. **Verified Knowledge Pack:** Node 16 (curated factual repository for domestic boiler pressure troubleshooting).
4. **Structured Asset Production:** Node 17 (template-based offline generation of troubleshooting guide + CTA).
5. **Quality & Compliance Hard Gate:** Node 19 (automated compliance validator ensuring 100% truthfulness and safety before publishing handoff).
6. **Deferred for Scale (C/D):** Node 15 (Campaign Clustering) and Node 18 (Video Rendering Pipeline) are deferred to keep the initial loop lightweight and credit-free.

---

## Cross-Owner Interfaces & Contract Deliverables

1. **Stage 2 $\to$ Stage 3 Contract (Node 10 / Node 05 $\to$ Node 11):**
   - Proposal staged at: `epics/ep_050_distribution_engine/integration/proposals/gemini/20260816_node10_to_node11_contract_proposal_v1.md`
   - Ingests `RawDemandSignal` from Claude (Node 05/10) with required fields: `signal_id`, `target_id`, `raw_query`, `topic`, `source`, `observed_at`, and context payload.

2. **Stage 4 $\to$ Stage 5 Contract (Node 19 $\to$ Node 20):**
   - Proposal staged at: `epics/ep_050_distribution_engine/integration/proposals/gemini/20260816_node19_to_node20_contract_proposal_v1.md`
   - Emits `ApprovedAssetPackage` to Hermes (Node 20) with required fields: `asset_id`, `target_id`, `opportunity_id`, `asset_type`, `headline`, `content_body`, `cta_definition`, `compliance_stamp`, and `approved_channels`.

---

## Recommendation

Approve this report as Gemini's planning contribution. Reconcile across Claude (Nodes 01–10), Gemini (Nodes 11–19), and Hermes (Nodes 20–37) to formalize the master MVP pipeline. Implementation remains at 0% pending orchestrator authorization.
