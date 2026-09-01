# EP050 Nodes 20–37 MVP Classification

> VERSION HISTORY
> - v1.0.0 · 2026-08-16 · Initial offline, planning-only classification for the Hermes-owned downstream nodes.

**Scope:** Nodes 20–37 only.  
**Source:** `distribution_engine_master_spec.md` §§14–26, 36, 39–42; board decision `20260816T195607599_codex_42e0dcfb` and planning clarification `20260816T200206133_codex_b62f69a3`.  
**Decision boundary:** This is a classification proposal, not MVP approval and not implementation authorization. All `implementation/node_NN/` folders remain untouched. All proposed validation is deterministic, local, and mock/fixture based; it must not schedule, publish, contact, route real leads, spend money, consume credits, or mutate production systems.

## Classification Legend

- **A — Required for First Live Loop:** cannot acquire and learn from a lead without the capability.
- **B — Manual Initially:** conceptually needed, but safely human-operated for the first loop.
- **C — Automate Next:** valuable automation after the loop is proven.
- **D — Scale Capability:** needed as services, geographies, clients, or volume increase.
- **E — Advanced Intelligence:** requires accumulated outcome data and optimization maturity.

## Node-by-Node Classification

| Node | Classification | Rationale and dependency | Safe manual substitute | Local completion test | Candidate 24–48h MVP participation |
|---|---|---|---|---|---|
| 20 Publishing Scheduler | **B** | A placement decision is necessary, but automated timing/channel scheduling is not. Depends on approved asset/channel inputs from Nodes 11–19. | Human selects one approved asset, owned test destination, time, audience, and CTA; records a mock publication plan. | Given an approved fixture asset, validate a complete plan containing asset, destination, audience, timing, CTA, approval state, and `external_action=false`. | **Yes, manual only** |
| 21 Search Distribution | **B** | Search placement can supply the first path, but SEO automation/indexing is unnecessary. Depends on Node 20 plan and a safe owned/mock destination. | Human prepares one landing-page/FAQ placement and records its canonical URL/CTA in a fixture; no indexing submission. | Validate placement metadata and attribution tags against a fixture URL without a network call. | **Yes, manual only** |
| 22 Video Distribution | **C** | Video can extend reach but is not required for one complete loop; it depends on video assets and approved distribution plans. | Defer or manually retain an approved video distribution checklist. | Mock validates channel-specific metadata and a blocked/no-publish adapter response. | No |
| 23 Social Distribution | **B** | A social path can be used manually, but platform-specific automation is not required. Depends on Node 20 and approved assets. | Human drafts and, only under a later authorization, posts one channel-specific item; current MVP uses a non-publishing fixture record. | Mock validates channel-specific copy/CTA fields and fail-closed adapter behavior. | **Optional manual path** |
| 24 Community Participation | **B** | Helpful human participation may identify/capture demand but must never be automated as spam. Depends on an approved opportunity and compliance review. | Human reviews conversation context and drafts a helpful response; no live community activity in this scope. | Fixture test rejects unapproved links, missing context, and any `auto_post=true`. | No; planning guardrail only |
| 25 Syndication / Partnership Distribution | **B** | Partnerships can be effective but require human permission and relationship handling; they are not needed for the first loop. | Human maintains an approved-partner/outreach checklist; no outreach or syndication occurs. | Fixture test accepts only approved owned/partner route records and blocks outbound execution. | No |
| 26 Smart Destination Router | **A** | The loop needs a deterministic destination for captured intent. Depends on the Node 20–25 channel/asset context and upstream intent data. | A human can choose a destination only as a documented fallback; routing rules should exist from the start. | Fixture matrix routes topic/intent/geography/service/channel/asset to an approved mock destination; unrecognized or unapproved cases fail closed. | **Yes** |
| 27 Conversion / Lead Capture | **A** | A structured lead with acquisition context is essential to prove the loop. Depends on Node 26 and upstream identity/consent contract. | A structured offline intake fixture may be entered by a human. | Fixture capture creates a pseudonymous `lead_id`, preserves required acquisition fields, and rejects missing consent/lineage. | **Yes** |
| 28 Attribution | **A** | The MVP must answer origin, asset, CTA, destination, and outcome lineage. Depends on Node 27 and the upstream identifier contract. | Human may complete missing non-sensitive fields only with an audit record; no fabricated lineage. | Contract fixture preserves `lead_id` and required origin-to-destination attributes; missing mandatory lineage fails validation. | **Yes** |
| 29 Lead Qualification | **B** | Qualification is required conceptually, but first-loop scoring/rules may be performed by an accountable human. Depends on Node 27 and Node 28. | Human applies an explicit checklist for service, geography, intent, duplicate/spam, and contactability. | Fixture checklist produces qualified/rejected/needs-review plus reason codes; no external enrichment. | **Yes, manual only** |
| 30 Lead Routing | **B** | The first loop must record where a qualified lead would go, but automated/client routing is unsafe and premature. Depends on Node 29 and approved destinations. | Human selects an approved mock/test queue or records `withheld_pending_approval`; never sends a real lead. | Fixture routes only to allowlisted mock destinations; all real/outbound destinations fail closed. | **Yes, manual/mock only** |
| 31 Lifecycle / Outcome Tracking | **A** | Learning requires a traceable recorded outcome, including no-sale/loss states. Depends on Nodes 27–30. | Human records a fixture outcome and reason using the lifecycle state model. | State-machine tests allow valid ordered transitions and reject skipped/illegal transitions; fixture outcome links to `lead_id`. | **Yes** |
| 32 Performance Warehouse | **C** | A durable warehouse is valuable after first-loop records exist; an MVP can use a bounded local event projection. Depends on attribution and outcomes. | Human reviews one local aggregate/export. | Fixture projection aggregates acquisition/outcome events and reconciles counts with source fixtures. | No |
| 33 Outcome Feedback | **B** | Outcomes must re-enter learning, but a person can record the first verified outcome. Depends on Node 31. | Human submits a validated local feedback record with provenance. | Fixture feedback records outcome/reason/source and rejects an unlinked or unsigned/unknown source. | **Yes, manual only** |
| 34 Winner Detection | **C** | Requires more than one comparable outcome and enough data to avoid false winners. Depends on Nodes 32–33. | Human reviews a small outcome table; no winner declaration without threshold evidence. | Synthetic cohort test applies declared sample-size, value, and confidence thresholds; insufficient data yields `no_decision`. | No |
| 35 Amplification Engine | **C** | Amplification follows validated winners and should not create/publish assets automatically. Depends on Node 34 and approval. | Human writes a proposed next experiment after review. | Fixture converts a qualified winner into an approval-required, non-executing recommendation. | No |
| 36 Distribution Investment | **E** | Portfolio resource allocation needs repeated outcome/cost data and governance. Depends on Nodes 32–35. | Human performs a documented periodic prioritization outside the MVP. | Synthetic inputs produce ranked recommendations with uncertainty; no spend/action command is emitted. | No |
| 37 Distribution Knowledge Base | **D** | Structured learning is important for multi-loop reuse and scale, but first-loop observations can be held in a reviewed local record. Depends on provenance from Nodes 28, 31, and 33. | Human maintains a versioned, non-sensitive learning log. | Fixture ingestion stores only provenance-linked, versioned observations and rejects unsupported claims. | No |

## Candidate Combined MVP Contribution

The Hermes-owned contribution to a smallest complete learning loop is:

1. **Manual, fail-closed placement:** Node 20 and one selected manual path from Node 21 or 23.
2. **Deterministic intent-to-destination and lead record:** Nodes 26–28.
3. **Human-controlled quality and destination decision:** Nodes 29–30, using only local mock/test queues.
4. **Recorded outcome and feedback:** Node 31 plus manual Node 33.

This candidate subset depends on the upstream cross-owner chain providing a known service/location, opportunity, approved asset, intent context, and compatible identity/consent contract. It does **not** authorize a real lead loop: the master-spec wording “live” remains subject to explicit user authorization for external activity, privacy review, and orchestrator approval of the combined MVP set.

## Cross-Owner/Approval Gates

- **Upstream:** Nodes 1–19 must publish reviewed, versioned contract proposals before any downstream implementation; Node 19 at evidenced 100% remains the hard gate for Node 20 implementation.
- **MVP approval:** Codex/orchestrator must approve the combined cross-owner subset before any implementation scaffolding.
- **Canonical contracts:** Any cross-owner schema belongs first in `integration/proposals/<owner>/`, followed by producer review and orchestrator approval before promotion.
- **Safety:** No adapter may perform an external action by default. Approval, consent, audit lineage, allowlisted mock destinations, and explicit `external_action=false` are required for all planning tests.

## Recommendation

Approve this report as the Hermes planning input only. Select the combined MVP after receiving the Node 1–19 classifications and contract proposals; then authorize a bounded implementation task only for approved nodes whose upstream gates are evidenced.