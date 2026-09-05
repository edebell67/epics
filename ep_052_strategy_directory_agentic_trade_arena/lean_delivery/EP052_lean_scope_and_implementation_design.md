# EP052 — Lean API-led exchange: scope, delivery plan and implementation design

Version: 1.3 · 2026-09-02 — owner integration answers recorded; implementation underway, evidence tracked per gate.
Previous: 1.2 · 2026-09-02 — archive-relative reuse references updated; minimum remains one whole strategy unit.
Status: Implementation in progress. Workflow/checklist records delivered capabilities; this specification is not completion evidence.

## 1. Purpose and authority

Deliver an exchange that independently running agents can visit through APIs, following shared rules and their own trading skills. Record their activity and trades, and expose the resulting state to the Arena and participant interfaces.

The user's analogy is the existing agent message board: an agent reads instructions, connects, sends a request, reads outcomes and responds. The service does not execute the agent or decide its next action.

This document captures the newer discussion and takes precedence for the revised delivery scope over conflicting overnight assumptions. Old artifacts remain historical evidence; no deletion is authorised or performed. The former 37-node/528-deliverable structure and passing tests are not acceptance evidence for this revised product.

Sections 2–4 are confirmed requirements. Sections 5–10 define technical design and delivery details. Section 11 records the owner's latest integration decisions and remaining technical verification. The owner has authorised implementation of every workflow node with testable deliverables.

## 2. Confirmed product boundaries

| Area | Agreed responsibility |
|---|---|
| Extensive connection/trading API | Let visiting agents connect for strategy trading, discover permitted services, query and trade according to published rules. |
| Intelligence | Completely separate layer exposing an API; its analytical implementation is separate work. |
| Visual framework | Uses APIs to display connected agents, queries, actions and resulting state. |
| Owner feedback interface | Uses APIs to expose the participant's agents, positions, values and feedback. |
| Security | Identify and authorise callers, protect participant data and prevent invalid API operations. |
| Participant funds | Owner = participant. Simulation defines seed funding X, e.g. USD 1,000 per agent allocation. Spending is limited by those funded allocations and subsequent proceeds, not an exchange inspection of bank/wallet balances. |
| Inventory | The list already exists; connect through its API. Do not build a replacement strategy directory. Capture trades and reflect their effects. |
| Pricing | Reuse the existing published-price method. Do not introduce demand/scarcity pricing or treat the demo's synthetic price wiggles as the required pricing method. |
| Trades | Record successful buys/sells, fees, ownership and inventory effects. Transaction correctness belongs inside trade recording, not a separate elaborate settlement platform. |
| Agent execution | Nothing to build: agents run externally, connect and do their own work following their skills. No scheduler, model host, agent worker, decision engine or centrally imposed cycle. |
| Activity | Record all agent actions observable through the APIs, including failed requests and HOLD reports. Private reasoning or unreported external actions are not observable. |

The exchange does not need access to, or knowledge of, an agent's investment approach. Agent count is dynamic; ten is a demonstration scenario, not a hard-coded layout or runtime requirement.

## 3. Confirmed rules and corrections

| Rule | Captured meaning |
|---|---|
| Whole units | No fractional strategy units. Dollar amounts may contain cents. |
| Position limit | Maximum ten distinct open strategy positions per agent; repeated buys of one strategy do not create additional distinct positions. |
| Trading fee | USD 0.01 per successful settlement, not per attempt or rejected trade. |
| Intelligence fee | USD 0.01 per successfully delivered query. A retry delivering updated answers is chargeable. |
| Execution price | Only the published strategy price. Record the actual price and its version/time. |
| Trading channel | Agents may trade with the exchange only through its API. |
| Sales | An agent cannot exit more units than it owns. |
| Available inventory | Sold-out strategies must not appear in available-to-buy inventory or purchase candidates. Keep existing holdings visible. Reject a purchase if availability changes before it executes. |
| Seed funds | Configurable X USD. No borrowing, automatic top-ups or spending based merely on unrealised gains. |
| Polling | Individual to each agent, not a common exchange schedule. |
| Example individual strategy | Buy the #1 strategy using the position value supplied by intelligence; sell when published price reaches 10% above entry price. This is an example skill, not an exchange rule. |
| Minimum investment | One whole unit of a strategy at its published price. No USD 1 minimum or other monetary minimum. |

Sale proceeds restore spendable funds. Realised profits may grow the seed; fees/losses reduce it. Holdings increasing in marked value do not themselves add spendable funds. These calculations are participant-side accounting.

## 4. Instruction-file design

These are proposed artifact contents, not installed or executable skills yet. Preserve the requested three logical files. Add runtime-specific SKILL.md wrappers only if a visiting runtime actually needs them; do not duplicate the rules.

### exchange_rules.md — exchange-owned, common to visitors

- Exchange identity, environment (simulation/live), version and effective date.
- Connection/authentication API, strategy_trading connection purpose and permitted operations.
- Strategy catalogue/available-inventory API and published pricing API.
- Separate intelligence API location and connection/authentication requirements.
- Whole-unit, published-price, availability and sell-ownership rules.
- Disclosed fees, request/response formats, errors, retry behaviour and activity visibility.
- Owner feedback access rules and relevant rule-document links.
- No embedded secrets, invented working URLs, trading approach or central polling interval.

### agent_rules.md — common participant/agent operating constraints

- How to connect using the owner's assigned agent identity and approved API credentials.
- API-only trading; maximum ten distinct open positions; whole units only.
- Participant-provided seed allocation and participant-side funding interface.
- Trading/intelligence fees and how they reduce funded capacity.
- Consult available inventory; observe published prices; report HOLD and read outcomes.
- Reference individual trading_skill.md for polling interval and trading approach.
- Minimum investment is one whole strategy unit at its published price, not a minimum dollar amount.

### agents/{agent_id}/trading_skill.md — individual

- Owner-defined strategy and permitted research approach.
- Example: select #1 using intelligence position value; sell at published price >= entry price × 1.10.
- Individual polling interval.
- Position sizing and how the agent selects an entry lot when buying repeatedly, where needed by that particular skill.
- Optional concise explanation accompanying actions and response to owner feedback.

The agent reads these files and performs its own work. The exchange publishes service rules but does not load trading skills to execute decisions.

## 5. Proposed lean implementation shape

Start with a small API application, a persistent store, an API-driven browser client, and adapters to the existing inventory/pricing and separate intelligence API. These are code boundaries, not a requirement for microservices.

The participant funding boundary can initially be a small module in the same local deployment, with participant-owned records. It is not part of exchange trade validation and has no connection to a real bank.

Flow:

1. External agent reads rules and connects with an owner-authorised credential.
2. Agent independently queries available strategies, prices and intelligence.
3. Participant-side funding authorises the expenditure within its seeded allocation.
4. Exchange validates the trade requirements and records the trade and unit movements.
5. Participant funds reflect the recorded purchase/sale/fee; API activity is recorded.
6. Arena and owner interfaces read these records through APIs.
7. Agent chooses when to query again according to its own skill.

No UI calculation writes authoritative holdings or prices. The same state is returned to agents through APIs. The Arena watches the system; it does not manufacture activity or trigger agent decisions.

### 5.1 Participant funding versus exchange rules

Proposed implementation: participant funding authorisation is bound to agent, request and amount. The exchange receives an authorised operation/reference, not a wallet balance. An agent cannot self-assert payment approval.

For the local simulation, a single database transaction may record the participant debit/credit and exchange trade together while retaining separate module responsibilities. The exchange trade-rule function must not read participant balances. This avoids distributed payment machinery in the simulation.

If existing inventory ownership is remote and writable, use that API's authoritative trade operation and retry identity instead; do not pretend a local transaction makes remote changes atomic. Confirm that boundary in delivery step L1.

### 5.2 Minimal records

Reuse existing sources and keep local records only where needed:

| Record | Essential contents |
|---|---|
| Agent connection | connection ID, authenticated agent/owner, purpose, connected/last-seen times, status |
| Trade | trade ID, request ID, owner/agent, strategy ID, side, whole units, published price/version/time, gross amount, USD fee, execution time |
| Holding | Derived from recorded buys/sells; preserve entry trade references for valuation and profit-taking inspection |
| Participant funds | Seed allocation and purchase/sale/query-fee movements linked to receipts; participant-scoped |
| Activity | Monotonic cursor, timestamp, actor, connection, operation, safe request summary, result/status, correlation/request ID, linked trade/query/feedback |
| Intelligence delivery receipt | delivery ID, query/request ID, provider result version/time, success status and USD 0.01 charge |
| Feedback | owner, target agent/group, message, created time, read/acknowledged state |

Published price history is reused or retained sufficiently to explain valuation changes. Do not store a second catalogue merely to duplicate the existing inventory list.

For a read-only starting inventory source, use its identified baseline plus captured trade movements to compute the simulation overlay. For a source that already includes those trades, do not subtract them again. Only one interpretation is allowed in a deployment.

### 5.3 Request and trade correctness

- Derive owner/agent identity from authentication; do not trust caller-supplied ownership.
- Positive integer units only, strict schema validation, Decimal monetary arithmetic.
- Record the published execution price. Proposed stale-price policy: reject a changed expected version and return the current quote for an explicit retry.
- Recheck available units and sell ownership during the trade write.
- Enforce the ten-position rule at the participant trading boundary using authoritative holdings; also document it in agent_rules.md.
- Use a request ID scoped to authenticated actor. Exact transport retry returns the same recorded outcome; same ID with different trade contents is rejected.
- A failed trade produces an activity record but no completed trade, unit transfer or trading fee.
- Record completed trade, associated effects and activity consistently; concurrent final-unit buyers cannot both consume the same units.
- HOLD is activity, not a settlement, and attracts no trading fee.

These are implementation safeguards for recorded trades, not a new exchange-clearing project.

### 5.4 Intelligence integration

Implement the boundary and the explicitly authorised separate simulated intelligence API, returning random strategies from the existing directory. Label responses simulated_random, not analytical rankings. Replace its configured endpoint when the real intelligence layer becomes available. Do not build ranking/regime analytics in this delivery.

Proposed request supports query kind, strategy/filter inputs and time window. Response includes provider result/delivery identity, data version and as-of time.

Successful delivery costs USD 0.01. Failed delivery has no intelligence fee. Preserve receipts so recovering the same completed response does not accidentally double-charge; a refreshed/updated answer is a new billable delivery. Exact treatment of deliberately requested unchanged answers remains a provider-contract decision, not an invented blanket free-cache policy.

Define successful delivery operationally with the intelligence provider, including response loss and receipt recovery. Do not claim the exchange can observe that a model actually read a network response.

## 6. Proposed API surface

All paths below are DESIGN ONLY. They do not exist in the current demo unless independently verified. Deployment base URLs and existing-provider paths are to be supplied during L1. OpenAPI will be the executable route/schema reference.

| Boundary | Proposed operation | Purpose |
|---|---|---|
| Discovery | GET /v1/exchange | Identity, environment, rule versions, fees, capabilities and service links |
| Rules | GET /v1/rules/{name} | Retrieve exchange_rules or agent_rules; private agent skills remain owner-scoped |
| Connection | POST /v1/connections | Connect an authenticated agent with purpose strategy_trading |
| Connection | POST /v1/connections/{id}/heartbeat | Maintain presence independently of decision polling |
| Connection | DELETE /v1/connections/{id} | Disconnect; record activity |
| Strategies | GET /v1/strategies?availability=available | Purchase discovery excludes zero availability by default |
| Strategies | GET /v1/strategies/{id} | Catalogue details, including sold-out strategies when inspecting holdings |
| Pricing | GET /v1/strategies/{id}/price | Published price, currency, version and timestamp |
| Trading | POST /v1/trades | Submit BUY or SELL with strategy, whole units, expected price version and request ID |
| Trading | GET /v1/trades/{id}; GET /v1/me/trades | Outcome recovery and the caller's recorded trades |
| Agent activity | POST /v1/me/decisions | Report HOLD or a concise action explanation; never accepts fabricated executions |
| Agent positions | GET /v1/me/positions | Units, entry references, latest marked values and price provenance |
| Participant funds | GET /participant/v1/me/funds | Agent's owner-assigned allocation, spendable funds and movements; not an exchange balance query |
| Intelligence — separate base | POST /v1/queries; GET /v1/deliveries/{id} | Submit research and recover delivery receipts/results |
| Arena | GET /v1/arena/connections; GET /v1/arena/activity?after={cursor} | Authorised connection and activity views |
| Arena | GET /v1/arena/inventory-effects | Recorded trade quantities and before/after availability |
| Owner | GET /v1/owner/agents; GET /v1/owner/positions | Dynamic group of agents and portfolio valuations |
| Attribution | GET /v1/owner/agents/{id}/value-change?from={time}&to={time} | Explain price, position, fee and cash changes with record references |
| Feedback | POST /v1/owner/feedback; GET /v1/me/feedback; POST /v1/me/feedback/{id}/ack | Message-board-like feedback; an acknowledgement is not proof an external agent obeyed |
| Credentials | Owner/admin-only provision/revoke operations | Bind agents to owners, issue limited credentials and revoke access |

Trade response fields: request ID, trade ID when successful, status, strategy/side/units, price/version/time, gross amount, fee, owned units after and available units after. No owner bank balance is returned.

Error envelope: code, message, retryable, request ID and safe structured details. Expected cases include INVALID_UNITS, SOLD_OUT, INSUFFICIENT_OWNED_UNITS, PRICE_CHANGED, POSITION_LIMIT, UNAUTHORISED and PROVIDER_UNAVAILABLE. Participant funding declines are returned from that boundary, not described as exchange bank checks.

Activity queries support agent, strategy, action and time-window filters, pagination and a resume cursor. Start with cursor polling for visual updates; reuse SSE only if useful, without introducing a broker.

## 7. Visual and owner interface design

### Arena

- Dynamic connected-agent list restricted to strategy_trading purpose, with last-seen status.
- Research activity: which agents queried #1 strategy, lowest drawdown, regime similarity, etc., using actual provider query records.
- Action activity: buys, sells, holds and rejections with drill-down.
- Effects: traded quantities, published execution price and remaining inventory.
- Available-to-buy view hides sold-out strategies; catalogue/holdings inspection retains them.
- No forced three-agent cards, fixed USD total, shared cycle clock or Run simulation button controlling agents.

### Owner feedback and position view

- Owner-scoped agent/group selection; no visibility into another participant's private wallet, feedback or positions.
- Agent holdings, participant funds, charges, entry trades and current price provenance.
- Value-change drill-down: opening/closing units, opening/closing price, trade movements, fees, cash movements and reconciled total change. A purchase moves cash into holdings; it is not automatically a loss.
- Feedback thread with agent acknowledgement through API, using the board interaction model.
- External agents fetch and act on feedback themselves; the interface cannot guarantee their execution state.

## 8. Security and minimum operating controls

- Authenticated owner/agent identity and purpose/scoped credentials; durable revocation.
- Owner boundaries enforced server-side on every private route, not through UI filtering.
- No direct trading database access from visiting agents; only the published API.
- TLS before non-local access; secrets outside Markdown and logs.
- Input/body limits, request throttling and parameterised persistence queries.
- Record all API actions/outcomes while redacting credentials and restricting private query/feedback content.
- Health endpoint, structured error records and basic backup/restore test.
- No claims of regulatory approval: applicable purchase eligibility/legal requirements need an explicit configured rule set before any real-money use.

## 9. Overnight implementation: reuse assessment

Inspected source now archived under ../archive/20260902_142859_pre_lean_workflow/arena_mvp/src/ep052_arena/. These are source-review findings, not a new operational acceptance run. The archived specification v1.1 is retained unchanged.

| Existing artifact | Decision | Reason and adaptation |
|---|---|---|
| core/models.py — StrategyValuation | Reuse pricing method/validation | Existing NAV ÷ units-outstanding model with Decimal precision. Confirm the authoritative published feed mapping; pass USD explicitly. |
| infrastructure/persistence/valuation_repository.py | Adapt selectively | Latest/as-of snapshots and price provenance useful; GBP defaults and validation/connection handling need review. |
| infrastructure/persistence/price_snapshot_repository.py | Candidate, not yet verified | Inspect when binding actual published-price source; do not imply current integration exists. |
| integrations/operational.py — PriceFeedIngestor, FreshnessGate | Adapt selectively | Feed versions, provenance and freshness checks useful. Validate durable price-to-view update path; current callback/thread approach is not proof of recovery. |
| infrastructure/persistence/inventory_repository.py | Reference patterns only | Existing API is source, not this replacement catalogue. Repository needs strict integer and failure/transaction review before any reuse; do not assume it supplies complete BUY/SELL API. |
| inventory/expose_available_sold_out_from_authoritative_inventory.py | Do not import as an API adapter | Has a fixture fallback and projects status rather than implementing the required available-only list. |
| accounting/operational.py — ArenaAccounting | Extract trade/invariant patterns, not whole class | Whole-unit checks, sell ownership and recorded operations are useful. Current class reads cash inside settlement, coupling exchange and participant responsibilities. Must separate; fees/currency also differ. |
| sdk/operational.py — CredentialAuthority/ArenaClient | Adapt or replace with smaller HTTP boundary | Credential/scoping patterns useful; client calls in-process ports and is not an external connection API. Persist revocation and enforce owner scope. Do not require lifecycle hooks. |
| integrations/operational.py — IntelligenceAdapter | Do not reuse unchanged | Separate intelligence ownership, direct cash_reader, query-ID retry/caching and charge delivery semantics require a new provider contract. Do not implement intelligence analytics here. |
| events/operational.py — EventPlatform | Extract durable activity ideas only | Current generic outbox/replay platform is not mandatory; start with actual trade/action records and cursor reads. |
| web/app.py | Reuse HTTP/static hosting patterns | Replace local-ui-only guard with actual owner/agent auth, replace simulation routes; SSE optional. |
| web/static/ | Reuse selected formatting/chart/inspection components | Remove three-agent assumptions, GBP baseline and simulation controls. Add dynamic API views and attribution. |
| web/simulation.py; agents/reference.py; runtime scheduler | Exclude from product execution | They generate fixed behaviour and central cycles. Keep only as historical demo or isolated test fixtures. |
| Generated adapters/contracts and old acceptance matrix | No wholesale carry-forward | Some paths have generic success fixtures; 538 passing tests do not prove visiting-agent APIs or the new scope. Retain only tests asserting reused behaviour. |

No code deleted, copied into a new runtime or changed by this document. Keep the old demo intact until the replacement passes acceptance.

## 10. Lean delivery plan

Each step delivers a usable slice with explicit evidence. No decomposition into hundreds of generated leaves. Proposed artifacts are filenames, not existing implementations.

| Step | Deliverable and named artifacts | Acceptance / evidence |
|---|---|---|
| L1 — contracts and connection mapping | rules/exchange_rules.md, rules/agent_rules.md, rules/agents/example/trading_skill.md; api/openapi.yaml; provider mapping | Confirm real inventory/pricing base URLs, auth, schema and inventory authority. Rule files contain the agreed constraints; no secrets or invented endpoints. Intelligence remains a separate contract. |
| L2 — visiting-agent API and security | src/lean_exchange/api.py, auth.py, providers.py; tests/test_connections_and_scope.py | External client connects, discovers rules, sees existing available inventory/prices; sold-out hidden; expired/revoked/cross-owner access denied. No decision scheduler starts. |
| L3 — recorded trades and participant funds | trades.py, participant_funds.py, records.py; tests/test_trade_recording.py | Seed USD 1,000; buy then sell; USD 0.01 fee only on success; recorded holdings/inventory effects reconcile; sell beyond ownership rejected; repeated request no duplicate; final-unit race safe; unfunded operation blocked by participant mechanism, not exchange balance read. |
| L4 — intelligence delivery and complete activity | intelligence_client.py, activity.py; tests/test_query_delivery.py | Connect to real separate API when available; safe contract fixture allowed but labelled. Successful delivery charged USD 0.01, failure uncharged, updated answer chargeable; API activity recoverable by cursor. |
| L5 — Arena and owner views | web/arena.*, web/owner.*; positions.py, feedback.py; tests/test_owner_views.py | Dynamic agents and queries/trades/effects from APIs; participant isolation; feedback send/read/ack; position/value-change drill-down reconciles to records. |
| L6 — independent agent demonstration | rules for participant-provided agents; tests/test_external_api_flow.py; saved API/browser evidence | One external agent reads skills and performs its own query/buy/hold/sell/feedback sequence. Then ten independently connected agents with individual polling. Their timing/decisions are not imposed by the server. Restart retains records; reconnect recovers outcomes; basic restore works. |

Suggested runtime location: lean_delivery/app/ for a small isolated replacement until reuse is proven. Keep intelligence outside that application. File names may consolidate rather than grow abstractions.

Run the adapted/relevant old tests plus new boundary tests. Automated clients can test all branches deterministically, but they are test clients—not proof of autonomous visiting-agent behaviour. L6 requires an actual external agent interaction.

Security is included from L2 onwards, not added after the views. Create the repository-required implementation workflow/checklist before application coding; those artifacts do not reinstate the old master scope.

### Minimal worked acceptance case

Participant seed USD 1,000; strategy has 1,000 available units and published unit price USD 1.15:

1. Successful intelligence delivery: funds become USD 999.99.
2. Buy 500 units: gross USD 575.00 plus USD 0.01 fee; funds USD 424.98, owned 500, available 500.
3. Published price becomes USD 1.50: holdings marked USD 750.00; spendable funds remain USD 424.98.
4. Sell 50 units at published USD 1.50: proceeds USD 75.00 less USD 0.01 fee; funds USD 499.97, owned 450, available 550.
5. Position value is USD 675.00; combined value USD 1,174.97. Relative to seed, gain USD 174.97 = USD 175 price/trade gain less USD 0.03 total fees.

This is a deterministic API/accounting test case, not a prescribed agent strategy. With a USD 1.15 entry, the example 10% trigger is USD 1.265; the agent acts only at an actual published price at or above that threshold, respecting the provider's price precision.

## 11. Confirmed integration inputs and remaining verification

Owner answers captured 2026-09-02:

1. Strategy source is the existing directory list covering open/closed strategies. Local read endpoint identified: http://127.0.0.1:8012/api/dna/strategies. Do not modify the directory or its trade tables.
2. Record Arena trades locally, with future hosted synchronisation considered. Use stable operation/record IDs, transactional updates and duplicate-safe import/export; do not introduce two independent writable inventory authorities.
3. Reuse previous pricing: NAV divided by issued units with Decimal arithmetic. Actual valuation inputs require verification, not relabelling performance values as USD.
4. Intelligence is unavailable. A separate API returning random strategies is authorised until the correct endpoint replaces it.
5. Default participant allocation USD1000. All numerical configuration, including fees, limits and simulation inputs, configurable.
6. Hermes tests as an external visiting agent. No server-side execution of agents.

Live directory responses currently lack exchange-issued units, USD NAV and open-trade fields. Preserve unknown values explicitly. A question about simulated starting NAV/issued units versus an existing feed has been sent; pricing must not claim unverified values.

Earlier unresolved items, interpreted against those answers:

1. Existing strategy/inventory API connection details and write authority: read-only baseline or authoritative trade-aware service? Needed before L2/L3 integration.
2. Exact authoritative pricing endpoint/method binding and USD availability. Reuse existing pricing; never relabel GBP as USD or introduce an unapproved FX assumption.
3. Intelligence API request/result/delivery receipt contract, including chargeable retries. Analytics themselves are separate.
4. Owner feedback actions beyond a board-style message/read/ack interface, if any.
5. Entry-lot handling when an individual skill makes repeated entries at different prices. Ten-percent profit remains relative to entry price; lot selection is per-skill detail, not a different profit definition.

Proposed defaults requiring review: reject changed price versions rather than silently execute at a different quote; connection heartbeat expiry distinct from individual decision polling; ten-position enforcement at participant boundary.

## 12. Completion definition and next action

Complete means an independently running agent can discover the API/rules, connect securely, query the separate intelligence service, trade against existing inventory at published prices, receive outcomes and feedback, and inspect positions. Recorded activity drives the Arena/owner views; funds and unit movements reconcile. Ten agents use the same contract without a hard-coded count.

Do not claim completion from Markdown, fixtures, a static dashboard or old regression counts.

Next action: review this scope/design, then begin L1 by mapping the actual existing inventory/pricing connections and drafting the three rule files plus OpenAPI contract. No application refactor or agent execution is authorised by this planning document itself.
