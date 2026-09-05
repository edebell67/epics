// VERSION HISTORY v1.14.0 · 2026-09-02 · Restored3D floor verified on live review API; original simulation excluded; exact375px remains pending.
// v1.13.0 · 2026-09-02 · User correction:3D floor is primary Arena; API activity dashboard retained as audit view; visual integration now in progress.
// v1.12.0 · 2026-09-02 · Add a runnable delivery-access check; full evidence and external-agent acceptance remain incomplete.
// v1.11.0 · 2026-09-02 · Correct live visitor guidance and record tested Hermes authentication blockers without claiming an agent visit.
// v1.10.0 · 2026-09-02 · Recovery and all-route audit tests verified; process reload remains unverified, so both gates remain partial.
// v1.9.0 · 2026-09-02 · Arena browser one/ten-client and read-only controls verified; exact375px gate remains pending.
// v1.8.0 · 2026-09-02 · Shared Arena projection API verified with real HTTP and atomic event tests; Arena UI remains pending.
// v1.7.0 · 2026-09-02 · Owner position and value-attribution APIs/UI verified from recorded trade evidence; source binding still partial.
// v1.6.0 · 2026-09-02 · Recorded BUY/SELL, local atomicity and trade-linked reports verified; live valuation binding remains incomplete.
// v1.5.0 · 2026-09-02 · Owner feedback UI/API verified end-to-end; HOLD reports partial pending real trade linkage.
// v1.4.0 · 2026-09-02 · Participant funding and separate paid-query integration verified by real HTTP.
// v1.3.0 · 2026-09-02 · Owner access and connection gates verified; comprehensive activity remains partial.
// v1.2.0 · 2026-09-02 · Contracts and separate simulator verified; source mapping partial, trading not delivered.
// v1.1.0 · 2026-09-02 · L1-01 live rule API and configurable economics verified.
// v1.0.0 · 2026-09-02 · Lean implementation map, no inherited completion.
window.EP052_WORKFLOW={
  "phases": [
    {
      "id": "L1",
      "title": "Rules & API contracts",
      "purpose": "Publish the visitor contract and bind existing sources."
    },
    {
      "id": "L2",
      "title": "Connections & security",
      "purpose": "Accept independently running agents; never execute them."
    },
    {
      "id": "L3",
      "title": "Trade records & participant funds",
      "purpose": "Implement compact recorded trades with correct effects."
    },
    {
      "id": "L4",
      "title": "Intelligence & activity access",
      "purpose": "Connect separate intelligence and expose observable actions."
    },
    {
      "id": "L5",
      "title": "Arena & owner interfaces",
      "purpose": "Render changing state from APIs for any agent count."
    },
    {
      "id": "L6",
      "title": "End-to-end proof & handoff",
      "purpose": "Prove the lean system with actual visiting agents."
    }
  ],
  "nodes": [
    {
      "id": "L1-01",
      "lane": "L1",
      "title": "Publish the three rule documents",
      "purpose": "Version exchange_rules.md with connection, strategy, pricing and intelligence API references.",
      "inputs": "Approved lean specification",
      "steps": [
        "Version exchange_rules.md with connection, strategy, pricing and intelligence API references.",
        "Version agent_rules.md: whole units, minimum 1 unit, ten distinct positions, USD 0.01 success fees and participant funding boundary.",
        "Provide individual trading_skill.md example with its own polling and 10% above entry-price sell trigger."
      ],
      "test": "Rule/schema validation contains all confirmed rules; no USD minimum, common polling clock or exchange wallet lookup.",
      "evidence": "Live agent_rules1.3 now describes delivered trading, positions and feedback APIs instead of obsolete trading-pending guidance; quote prerequisites remain explicit.8 targeted rule tests and98 full regressions pass (evidence/rules/full-agent-refresh-results.xml). Live8054 rule text verified. Numeric override and invalid configuration tests retained.",
      "dependencies": "Approved lean specification",
      "executor": "lean_delivery/app/src/lean_exchange/api.py::create_app (rules route), config.py::load_settings",
      "outputs": "Three versioned rule files and live HTTP access at port 8054",
      "deliverable": "http://127.0.0.1:8054/v1/exchange",
      "pct": 100,
      "status": "Complete"
    },
    {
      "id": "L1-02",
      "lane": "L1",
      "title": "Bind existing inventory and pricing",
      "purpose": "Load existing source URL/auth/schema from configuration, never Markdown secrets.",
      "inputs": "Existing directory8012 mapped; actual USD NAV/issued units and open-evidence binding unresolved",
      "steps": [
        "Load existing source URL/auth/schema from configuration, never Markdown secrets.",
        "Choose one inventory authority: trade-aware upstream or read-only baseline plus recorded trade overlay.",
        "Map published USD price/version/time using existing valuation method; no GBP relabelling or fabricated production prices."
      ],
      "test": "Recorded provider responses validate; missing connection, currency mismatch or ambiguous inventory authority fails explicitly.",
      "evidence": "Live API returns 500 actual directory records with source hash. Provider tests pass including pagination, failure, currency and whole-unit validation. Source omits open evidence and exchange prices; no tradable inventory claimed. Completion pending those bindings.",
      "dependencies": "Pricing input confirmation; open/closed source completeness",
      "executor": "lean_delivery/app/src/lean_exchange/providers.py::DirectoryProvider.fetch, published_price",
      "outputs": "Read-only source API and Decimal NAV/unit-price implementation",
      "pct": 50,
      "status": "In progress",
      "deliverable": "http://127.0.0.1:8054/v1/providers/directory"
    },
    {
      "id": "L1-03",
      "lane": "L1",
      "title": "Validate connection and trade schemas",
      "purpose": "Define OpenAPI connection, discovery, BUY/SELL/HOLD, outcomes, activity and owner routes.",
      "inputs": "L1-01, L1-02",
      "steps": [
        "Define OpenAPI connection, discovery, BUY/SELL/HOLD, outcomes, activity and owner routes.",
        "Require positive integer units, request identity and published price version.",
        "Define structured errors and same-request retry semantics; label proposed routes unavailable until built."
      ],
      "test": "OpenAPI/schema checks accept valid examples and reject fractions, mismatched retry payloads and missing identifiers.",
      "evidence": "50-test regression passed (evidence/contracts/results.xml), including 9 schema tests. Live POST /v1/contracts/validate/trade returns valid:true, executed:false; invalid fractions/missing identity and changed retry fingerprints rejected. Contract delivery only; settlement remains L3.",
      "dependencies": "L1-01; stable contract completed independently of pending valuation data in L1-02",
      "executor": "lean_delivery/app/src/lean_exchange/contracts.py; api.py::validate_trade",
      "outputs": "Executable JSON schemas, OpenAPI and validation-only HTTP endpoint",
      "pct": 100,
      "status": "Complete",
      "deliverable": "http://127.0.0.1:8054/docs"
    },
    {
      "id": "L1-04",
      "lane": "L1",
      "title": "Define intelligence delivery boundary",
      "purpose": "Reference the separate intelligence API and versioned result/delivery receipts.",
      "inputs": "User-authorised random-list simulator replaces unavailable intelligence endpoint",
      "steps": [
        "Reference the separate intelligence API and versioned result/delivery receipts.",
        "Charge USD 0.01 only on successful delivery; updated answers on retry are chargeable.",
        "Define response-loss recovery and unchanged-result retry policy with provider; do not build analytics."
      ],
      "test": "Contract examples distinguish success, failed delivery, receipt recovery and refreshed billable answer.",
      "evidence": "9 contract and 3 separate-provider tests pass within 50-test regression. Live separate API returns real directory IDs at random; exact retry and GET recovery preserve receipt; refreshed revision issues new receipt. Restart and concurrent retries verified. Fee semantics specified; charging implementation remains L4-02.",
      "dependencies": "Separate random simulation explicitly approved by owner",
      "executor": "lean_delivery/app/src/lean_exchange/intelligence.py::contract; simulated_intelligence.py::create_app",
      "outputs": "Query/delivery schemas, separate port8055 simulator, scripts/test_intelligence.ps1",
      "pct": 100,
      "status": "Complete",
      "deliverable": "http://127.0.0.1:8054/v1/contracts/intelligence"
    },
    {
      "id": "L2-01",
      "lane": "L2",
      "title": "Authenticate owner-scoped agents",
      "purpose": "Bind owner and agent to issued credentials and permitted scopes.",
      "inputs": "L1-03",
      "steps": [
        "Bind owner and agent to issued credentials and permitted scopes.",
        "Persist expiry/revocation and validate on every protected request.",
        "Limit input sizes and request rates; redact credentials from records."
      ],
      "test": "Expired/revoked credentials and cross-owner requests fail; authorised calls succeed and secrets are absent from logs.",
      "evidence": "55 tests passed (evidence/access/results.xml). Real HTTP owner provisioning, agent registration, identity and revocation test passed; revoked token rejected401. Tests cover expiry, cross-owner isolation, roles, rate/body limits and token redaction. Credentials persisted hashed; bearer auth exposed in OpenAPI. No production security claim.",
      "dependencies": "L1-03",
      "executor": "lean_delivery/app/src/lean_exchange/auth.py::Authority; access.py::router",
      "outputs": "Live authenticated API, scripts/test_connections.ps1 and regression evidence",
      "pct": 100,
      "status": "Complete",
      "deliverable": "http://127.0.0.1:8054/docs"
    },
    {
      "id": "L2-02",
      "lane": "L2",
      "title": "Record trading connections",
      "purpose": "Accept authenticated purpose=strategy_trading connection.",
      "inputs": "L2-01",
      "steps": [
        "Accept authenticated purpose=strategy_trading connection.",
        "Record connected, last-seen, heartbeat and disconnect events.",
        "Report active connections using configured heartbeat expiry, not a shared decision schedule."
      ],
      "test": "One and ten clients connect independently; stale presence expires and reconnect is recorded without creating an agent worker.",
      "evidence": "Ten distinct authenticated API clients connect in tests, expire and reconnect; heartbeat ownership/disconnect/restart tested. Live HTTP test client connects, appears in Arena, heartbeats and disconnects (evidence/access/live-access.log). These are API clients, not L6 autonomous Hermes evidence.",
      "dependencies": "L2-01",
      "executor": "lean_delivery/app/src/lean_exchange/connections.py::router",
      "outputs": "Live authenticated API, scripts/test_connections.ps1 and regression evidence",
      "pct": 100,
      "status": "Complete",
      "deliverable": "http://127.0.0.1:8054/docs"
    },
    {
      "id": "L2-03",
      "lane": "L2",
      "title": "Expose available inventory and prices",
      "purpose": "Serve existing catalogue and published price data through authenticated API.",
      "inputs": "L1-02, L2-01",
      "steps": [
        "Serve existing catalogue and published price data through authenticated API.",
        "Exclude zero-available inventory from purchase discovery.",
        "Keep sold-out catalogue detail accessible for existing holdings and retain price provenance."
      ],
      "test": "Sold-out items are absent from available results but inspectable by ID; latest/as-of values retain source versions.",
      "evidence": "Authenticated catalogue/price routes implemented. Regression proves sold-out exclusion, retained detail and null unknowns. Live isolated8056 quotes accessible; main8054 correctly reports zero bound quotes. Actual source valuation/open-evidence binding remains L1-02, so this node is partial.",
      "dependencies": "L1-02, L2-01",
      "executor": "lean_delivery/app/src/lean_exchange/inventory.py::router; pricing.py::latest",
      "outputs": "GET /v1/strategies and per-strategy detail/price; tests/test_trade_recording.py",
      "deliverable": "http://127.0.0.1:8056/docs",
      "pct": 50,
      "status": "In progress"
    },
    {
      "id": "L2-04",
      "lane": "L2",
      "title": "Record all API action outcomes",
      "purpose": "Capture safe request summaries and success/rejection/error outcomes with actor/time/correlation.",
      "inputs": "L2-01",
      "steps": [
        "Capture safe request summaries and success/rejection/error outcomes with actor/time/correlation.",
        "Record connection, discovery, price, intelligence, trade, HOLD and feedback actions.",
        "Provide scoped cursor pagination; do not record private model reasoning or claim invisible actions."
      ],
      "test": "Authenticated actions have complete attributable records; unauthenticated failures are safely logged without invented identity; cursor reads have no gaps.",
      "evidence": "97-test regression passes, including every registered application API route with attributable HTTP records, safe correlation, malformed input and revoked identity checks. Fixed authenticated public-route attribution and aligned ActivityRecord schema. Saved recovery/final-results.xml; test_all_route_activity.py is runnable. Existing live process has not loaded these changes: process restart was blocked before execution, so live attribution verification remains open. Framework documentation routes and every possible branch are not claimed by this route audit.",
      "dependencies": "L2-01",
      "executor": "lean_delivery/app/src/lean_exchange/activity.py::ActionMiddleware, router; records.py::Store",
      "outputs": "Durable activity schema, scoped GET /v1/me/activity and executable all-route audit",
      "pct": 80,
      "status": "In progress",
      "deliverable": "http://127.0.0.1:8054/docs#/default/read_v1_me_activity_get"
    },
    {
      "id": "L3-01",
      "lane": "L3",
      "title": "Apply participant-funded spending",
      "purpose": "Assign configurable USD seed X to participant-owned agent allocation.",
      "inputs": "L1-03, L2-01",
      "steps": [
        "Assign configurable USD seed X to participant-owned agent allocation.",
        "Authorise purchases/query fees from funded capacity; no borrowing, top-up or unrealised-profit spending.",
        "Bind funding reference to request/agent/amount; exchange rules never inspect wallet/bank balances."
      ],
      "test": "USD 1000 fixture cannot fund excess spending; sales restore proceeds; exchange rule tests have no cash-reader dependency.",
      "evidence": "64 tests pass (evidence/funding/results.xml): configurable seed, owner isolation, debit/credit/retry/rollback and insufficient funds. Live external HTTP client startsUSD1000, query leaves999.99, exact retry unchanged, refreshed answer leaves999.98. No public credit/top-up route; exchange has no wallet reader. Trade execution remains L3-02/03.",
      "dependencies": "L1-03, L2-01",
      "executor": "lean_delivery/app/src/lean_exchange/participant_funds.py::initialise, move, router",
      "outputs": "Participant funds API, seed-once ledger, scripts/test_funded_queries.ps1",
      "pct": 100,
      "status": "Complete",
      "deliverable": "http://127.0.0.1:8054/docs"
    },
    {
      "id": "L3-02",
      "lane": "L3",
      "title": "Record whole-unit buys",
      "purpose": "Validate allowed trade, published price version and available units.",
      "inputs": "L3-01, L2-03, L2-04",
      "steps": [
        "Validate allowed trade, published price version and available units.",
        "Apply ten-distinct-position constraint at participant boundary; allow adding units within an existing position.",
        "Record one successful BUY, ownership/inventory effects and USD 0.01 fee; reject invalid requests without success effects."
      ],
      "test": "Buy 500 at USD 1.15 consumes 500 units and USD 575.01 participant funds; sold-out, fractional and eleventh-position attempts fail.",
      "evidence": "78 regression tests pass (evidence/trading/final-results.xml). Actual HTTP on8056 bought500 at1.15, consuming575.01 and500 units. Sold-out discovery, fractions, eleventh position and same-position additions tested. Quotes are explicit isolated acceptance inputs; L1-02 live valuation binding is NOT certified by this gate.",
      "dependencies": "L3-01, L2-03, L2-04",
      "executor": "lean_delivery/app/src/lean_exchange/trades.py::settle, validate_exchange",
      "outputs": "POST /v1/trades; tests/test_trade_recording.py; scripts/trade_review.py inspect",
      "deliverable": "http://127.0.0.1:8056/docs",
      "pct": 100,
      "status": "Complete"
    },
    {
      "id": "L3-03",
      "lane": "L3",
      "title": "Record sells and position exits",
      "purpose": "Validate seller ownership and positive whole quantity against recorded holdings.",
      "inputs": "L3-02",
      "steps": [
        "Validate seller ownership and positive whole quantity against recorded holdings.",
        "Execute at published price and record returned inventory.",
        "Credit participant sale proceeds less USD 0.01; preserve entry references and remaining position."
      ],
      "test": "Sell 50 at USD 1.50 returns 50 units and USD 74.99; selling beyond ownership has no trade/fee effect.",
      "evidence": "Live HTTP sold50 at1.50, returned50 units and74.99 funds;451-unit oversell rejected without fee. Remaining450 owned/550 available; original entry receipt retained. Full-exit test frees the position slot. Captured evidence/trading/review_20260902_162516_687/http-evidence.json. Isolated test quotes, not live source valuation.",
      "dependencies": "L3-02",
      "executor": "lean_delivery/app/src/lean_exchange/trades.py::settle; pricing.py::owned_units",
      "outputs": "SELL receipts and recoverable entry records; tests/test_trade_recording.py",
      "deliverable": "http://127.0.0.1:8056/docs",
      "pct": 100,
      "status": "Complete"
    },
    {
      "id": "L3-04",
      "lane": "L3",
      "title": "Protect retries and concurrent trades",
      "purpose": "Commit trade, unit movements, receipt and activity consistently; local participant effects share transaction where appropriate.",
      "inputs": "L1-02, L3-02, L3-03",
      "steps": [
        "Commit trade, unit movements, receipt and activity consistently; local participant effects share transaction where appropriate.",
        "Return original outcome for exact retry; reject changed content under reused ID.",
        "Use upstream atomic trade identity if inventory is remote; never assume local atomicity covers upstream."
      ],
      "test": "Final-unit race has one valid allocation; crash/retry gives no duplicate fee, trade or unexplained partial effect.",
      "evidence": "Final-unit race: one settlement among4 buyers. Four simultaneous exact retries: one trade, fee and domain event. Injected post-funding write failure rolls back all effects; retry succeeds. Actual8056 process restart retains identical receipts and499.97 funds (inspect-evidence.json). Scope is read-only baseline plus local trade overlay, not distributed upstream writes; L1-02 remains pending.",
      "dependencies": "L1-02, L3-02, L3-03",
      "executor": "lean_delivery/app/src/lean_exchange/trades.py::settle; records.py::Store.transaction",
      "outputs": "Durable request outcomes, SQLite atomic effects; tests/test_trade_recording.py",
      "deliverable": "http://127.0.0.1:8056/docs",
      "pct": 100,
      "status": "Complete"
    },
    {
      "id": "L4-01",
      "lane": "L4",
      "title": "Deliver intelligence API results",
      "purpose": "Forward authorised research kind, filters and time window to separate API.",
      "inputs": "L1-04, L2-01; separate random API running on8055",
      "steps": [
        "Forward authorised research kind, filters and time window to separate API.",
        "Return result version, source/as-of time and delivery receipt.",
        "Expose explicit provider failures; any temporary fixture is labelled and does not pass live integration."
      ],
      "test": "External provider success and failure contracts pass with correct owner scope; query content and provenance are preserved.",
      "evidence": "Live gateway8054 calls separate simulator8055 using server credential and authenticated agent identity; returns random actual directory IDs with provider version/time. Adapter tests reject wrong identity/mode, duplicates and upstream failure. 64-test regression passes. Real analytics excluded as explicitly approved.",
      "dependencies": "L2-01 authenticated owner/agent gateway",
      "executor": "lean_delivery/app/src/lean_exchange/intelligence_client.py::IntelligenceClient; query_gateway.py::router",
      "outputs": "POST /participant/v1/me/queries and scoped GET receipt recovery",
      "pct": 100,
      "status": "Complete",
      "deliverable": "http://127.0.0.1:8054/docs"
    },
    {
      "id": "L4-02",
      "lane": "L4",
      "title": "Record successful delivery fees",
      "purpose": "Link USD 0.01 fee to delivered result receipt.",
      "inputs": "L4-01, L3-01",
      "steps": [
        "Link USD 0.01 fee to delivered result receipt.",
        "Preserve retry recovery without accidental double charge.",
        "Treat updated answer as new billable delivery; record failed delivery without fee."
      ],
      "test": "One success costs USD 0.01, failure zero, refreshed answer another USD 0.01; receipt recovery follows agreed contract.",
      "evidence": "Live smoke: initial1000.00 ->999.99 after first query and exact retry ->999.98 after revision1; two movements. Tests cover unchanged result content on refreshed version, no fee on failed/malformed provider result, restart recovery, cross-agent receipt isolation, exact concurrent retry and final-cent race. 64 tests pass.",
      "dependencies": "L4-01, L3-01",
      "executor": "lean_delivery/app/src/lean_exchange/query_gateway.py::query; participant_funds.py::move",
      "outputs": "Atomic delivery/fee records and recoverable receipts; funded-query smoke script",
      "pct": 100,
      "status": "Complete",
      "deliverable": "http://127.0.0.1:8054/docs"
    },
    {
      "id": "L4-03",
      "lane": "L4",
      "title": "Accept agent decision reports",
      "purpose": "Record agent-reported HOLD and concise explanations.",
      "inputs": "L2-04",
      "steps": [
        "Record agent-reported HOLD and concise explanations.",
        "Link buy/sell explanations to authoritative outcomes instead of accepting fabricated executions.",
        "Keep agent timing and investment selection outside the server."
      ],
      "test": "HOLD creates activity and no trade fee; claimed execution cannot change holdings; no server scheduler invokes agents.",
      "evidence": "Prior HOLD live/retry/persistence/zero-fee evidence retained. Live8056 accepts SELL report linked to actual settled receipt. Regression accepts matching owned BUY and rejects cross-agent, fabricated and wrong-side claims without execution. No server scheduler. HTTP test client is not autonomous Hermes proof.",
      "dependencies": "L2-04",
      "executor": "lean_delivery/app/src/lean_exchange/decisions.py::router",
      "outputs": "POST/GET /v1/me/decisions for fee-free HOLD and verified BUY/SELL explanations",
      "pct": 100,
      "status": "Complete",
      "deliverable": "http://127.0.0.1:8054/docs"
    },
    {
      "id": "L4-04",
      "lane": "L4",
      "title": "Serve Arena activity projections",
      "purpose": "Expose connections, research, trades and inventory before/after effects.",
      "inputs": "L3-04, L4-02, L4-03",
      "steps": [
        "Expose connections, research, trades and inventory before/after effects.",
        "Filter by actor, strategy, operation and time window with cursor continuation.",
        "Apply shared-view visibility rules and exclude private participant funds/feedback."
      ],
      "test": "API projections reconcile with trades; reconnect resumes from cursor and cross-scope private content is denied.",
      "evidence": "91 regression tests pass. Live8056:7 events over4 cursor pages, originalBUY/SELL effects, deliveredQUERY, report, historical rejection and connection/disconnection; no duplicate receipts, private owner/funding/feedback or new trades. Filters, UTC microsecond boundaries, query strategy membership, atomic event rollback and one-time backfill tested. evidence/arena/live-output.json. Arena browser UI remains L5-01.",
      "dependencies": "L3-04, L4-02, L4-03",
      "executor": "lean_delivery/app/src/lean_exchange/arena.py::router, emit, backfill",
      "outputs": "GET /v1/arena/activity and /v1/arena/inventory-effects; scripts/test_arena.py; tests/test_arena_projection.py",
      "deliverable": "http://127.0.0.1:8056/docs",
      "pct": 100,
      "status": "Complete"
    },
    {
      "id": "L5-01",
      "lane": "L5",
      "title": "Render API-driven 3D Arena and audit view",
      "purpose": "Restore existing spatial booth/agent presentation, driven only by lean API records.",
      "inputs": "L4-04",
      "steps": [
        "Authenticate with existing credential; GET discovery, all-directory inventory, current presence and cursor-paged public events. Fail visibly on API errors and clear session data on sign-out.",
        "Adapt archived perspective geometry, booth selection and camera controls; replace its simulation engine with API-only view data. Catalogue booths may be unpriced or sold-out and must say so; available-only mode excludes them.",
        "Render current connected identities only; animate newly observed query/trade events without fabricating decisions, historical charts or returns. Orbit/zoom operate on the camera only; fees come from configuration.",
        "Provide a keyboard-accessible booth list and inspector plus retained activity audit/filter view. Verify error/sign-out/race handling, real API values, responsive layout and no trading requests."
      ],
      "test": "Browser shows one then ten externally connected agents; query/trade effects match APIs; 375px layout has no overflow.",
      "evidence": "Restored archived perspective geometry and booth/camera interactions on API-only snapshots; no old simulation engine or fabricated charts/returns.107 Python regressions and5 Node scene tests pass. Live8056 browser:500 real catalogue records, available-only1 priced strategy, inspector1.50/550/1000 with fixture provenance,1/10/0 HTTP presence clients, orbit/zoom/reset, pagination/search, BUY audit500 at1.15, invalid auth/signout clearing. Original receipts/funds unchanged. Screenshots evidence/arena/floor-01..08; floor-final-results.xml; floor-scene-results.xml. Width451/scroll436 has no horizontal overflow; exact375px remains unverified. External HTTP clients are not autonomous Hermes.",
      "dependencies": "L4-04",
      "executor": "lean_delivery/app/src/lean_exchange/views.py::arena; web/arena.html, arena.css, arena.js",
      "outputs": "Read-only3D Arena with audit tab; tests/test_arena_browser.py and test_arena_scene.cjs; scripts/arena_review_clients.py",
      "deliverable": "http://127.0.0.1:8056/arena",
      "pct": 80,
      "status": "In progress"
    },
    {
      "id": "L5-02",
      "lane": "L5",
      "title": "Expose participant positions and values",
      "purpose": "Serve owner-scoped agents, funded allocations, holdings and charges.",
      "inputs": "L3-04, L2-03",
      "steps": [
        "Serve owner-scoped agents, funded allocations, holdings and charges.",
        "Value units against published prices with provenance.",
        "Retain sold-out holdings and entry trade drill-down."
      ],
      "test": "Cross-owner access fails; units × price and participant funds reconcile for selected groups without fixed total capital.",
      "evidence": "85 regressions pass (evidence/positions/final-results.xml). Live8056 API/browser shows cash499.97, holdings675, total1174.97, original500-unit entry and450 remaining units. Selected groups, cross-owner rejection, sold-out retention, missing-price nulls and repeated entries tested. Browser reload retains data. Explicit acceptance quotes only; L1-02 actual source binding remains pending.",
      "dependencies": "L3-04, L2-03",
      "executor": "lean_delivery/app/src/lean_exchange/positions.py::snapshot, router; web/owner.*",
      "outputs": "GET /v1/me/positions; GET /v1/owner/positions; expandable owner holdings; tests/test_owner_positions.py",
      "deliverable": "http://127.0.0.1:8056/owner",
      "pct": 100,
      "status": "Complete"
    },
    {
      "id": "L5-03",
      "lane": "L5",
      "title": "Explain portfolio value changes",
      "purpose": "Return opening/closing units, prices, transactions, cash and fees.",
      "inputs": "L5-02",
      "steps": [
        "Return opening/closing units, prices, transactions, cash and fees.",
        "Separate market movement from cash-to-holdings transfers.",
        "Link each line to trade, price or charge records for browser drill-down."
      ],
      "test": "Worked USD 1000 case reconciles USD 499.97 cash plus USD 675 holdings; price-only change does not create spendable cash.",
      "evidence": "Live API and browser reconcile174.97 gain =175 price/trade gain minus0.03 fees. Price-only interval shows175 gain with zero cash change/fees. Opening/closing quotes, entry/trade IDs and charge references inspectable. Tests prevent future-publication lookahead, invalid intervals, false reconciliation with missing quotes and owner leaks. Evidence/positions/live-output.json and screenshots01–08. No autonomous agent proof inferred.",
      "dependencies": "L5-02",
      "executor": "lean_delivery/app/src/lean_exchange/positions.py::attribute, quote_at; web/owner.js::explainChange",
      "outputs": "GET /v1/owner/agents/{id}/value-change?from=...&to=...; dated browser drill-down; scripts/test_positions.py",
      "deliverable": "http://127.0.0.1:8056/owner",
      "pct": 100,
      "status": "Complete"
    },
    {
      "id": "L5-04",
      "lane": "L5",
      "title": "Exchange owner feedback",
      "purpose": "Record owner messages to agent/group, expose authorised fetch and acknowledgement.",
      "inputs": "L2-01, L2-04, L5-02",
      "steps": [
        "Record owner messages to agent/group, expose authorised fetch and acknowledgement.",
        "Display feedback alongside the participant view through APIs.",
        "External agent reads/responds independently; acknowledgement is not proof it obeyed."
      ],
      "test": "Owner sends feedback, external agent fetches/acks and owner sees result; another owner cannot read it.",
      "evidence": "69 tests passed (evidence/feedback/results.xml); actual browser group send -> external HTTP client fetch/ack/reply -> owner Refresh shows reply -> reload/re-auth retains it. Screenshots01–08 and live-response.log. Owner/target isolation, duplicate retries, latest/older pagination tested. Credentials memory-only; HTML text not interpreted. HTTP client demonstration is not autonomous Hermes acceptance.",
      "dependencies": "Owner authentication, registered agents and activity API delivered; feedback does not require the unfinished price/position view.",
      "executor": "lean_delivery/app/src/lean_exchange/feedback.py::router; views.py; web/owner.*",
      "outputs": "Owner workspace, private feedback/reply APIs, scripts/test_feedback.ps1",
      "pct": 100,
      "status": "Complete",
      "deliverable": "http://127.0.0.1:8054/owner"
    },
    {
      "id": "L6-01",
      "lane": "L6",
      "title": "Verify one external agent loop",
      "purpose": "Have an independently operated agent consume the rule files and connect through API.",
      "inputs": "L1–L5; external participant agent available",
      "steps": [
        "Have an independently operated agent consume the rule files and connect through API.",
        "Capture its queries, BUY/HOLD/SELL and owner-feedback exchange.",
        "Record API/browser evidence without prescribing investment decisions or starting an internal agent runner."
      ],
      "test": "Actual external-agent trace links connection, query, trade, funds, positions and feedback; test fixtures alone cannot pass this gate.",
      "evidence": "Actual read-only Hermes preflight attempted2026-09-02. Windows executable fails: no inference provider configured. WSL executable /home/edebe/.local/bin/hermes reportsHTTP401 invalidated OAuth token (despite exit0). Neither reached the exchange or consumed rules. Reauthentication requested; live valuation binding remains a separate prerequisite. No autonomous trading acceptance or agent trace claimed.",
      "dependencies": "L1–L5; external participant agent available",
      "executor": "External participant-operated Hermes CLI; credential/provider readiness required before API visit",
      "outputs": "Pending actual external agent API trace and browser evidence; preflight blockers recorded",
      "pct": 0,
      "status": "Blocked"
    },
    {
      "id": "L6-02",
      "lane": "L6",
      "title": "Verify ten independent connections",
      "purpose": "Connect ten externally operated agents with individual skills and intervals.",
      "inputs": "L6-01",
      "steps": [
        "Connect ten externally operated agents with individual skills and intervals.",
        "Observe concurrent activity and trade outcomes through Arena APIs.",
        "Reconcile every trade, owner position and inventory effect without requiring particular research/trade choices."
      ],
      "test": "Ten distinct authorised connections operate independently; recorded movements reconcile; no hard-coded card count or central cycle.",
      "evidence": "Planned: lean_delivery/app/tests/test_ten_external_agents.py and captured API/browser results; no execution evidence yet.",
      "dependencies": "L6-01",
      "executor": "Planned: lean_delivery/app/src/lean_exchange/acceptance.py::ten_agents",
      "outputs": "test_ten_external_agents.py",
      "pct": 0,
      "status": "Not started"
    },
    {
      "id": "L6-03",
      "lane": "L6",
      "title": "Verify recovery and access safety",
      "purpose": "Restart API and reconnect clients while preserving trade outcomes and activity cursors.",
      "inputs": "L3-04, L4-04",
      "steps": [
        "Restart API and reconnect clients while preserving trade outcomes and activity cursors.",
        "Restore backup into isolated directory and compare recorded state.",
        "Recheck revocation, private owner access and hostile inputs; require TLS before non-local exposure."
      ],
      "test": "Restore/retry tests pass with no lost/duplicate trades or fees; security boundary tests pass and limitations recorded.",
      "evidence": "97 regressions pass. Live review database online-backup and isolated restore verify all20 table hashes, original trade receipts/cursors, no duplicate fees and durable revocation in the restored copy; original live credential unchanged. evidence/recovery/run_20260902_163030_a978c0aa/report.json. Actual fresh process-restart check blocked before execution; in-process app recreation is not counted as that proof. Local loopback only; hosted TLS/cutover not performed.",
      "dependencies": "L3-04, L4-04",
      "executor": "lean_delivery/app/src/lean_exchange/recovery.py::backup, restore, manifest; scripts/test_recovery.py",
      "outputs": "WAL-safe backup/restore CLI, recovery tests and operator test procedure",
      "deliverable": "lean_delivery/recovery_operations.md",
      "pct": 80,
      "status": "In progress"
    },
    {
      "id": "L6-04",
      "lane": "L6",
      "title": "Package evidence-backed delivery",
      "purpose": "Run relevant retained tests and all new API/browser coverage.",
      "inputs": "L6-01, L6-02, L6-03",
      "steps": [
        "Run relevant retained tests and all new API/browser coverage.",
        "Link each gate to actual artifacts, commands and observed evidence.",
        "Publish startup/API/rules access details; leave incomplete dependencies explicit instead of inheriting old completion."
      ],
      "test": "All required leaf gates have direct evidence, actual external-agent demonstration and documented exclusions; no invented pass status.",
      "evidence": "Live delivery_check verifies8 public responses and6 private-route unauthenticated denials on8054; source reports0 published strategies. Sanitized evidence/recovery/delivery-access-8054.json. Runnable review_access.md documents access, credentials, existing startup script and limitations. This is access evidence only, not authenticated use, authoritative quotes, exact375px, recovery-process restart or actual Hermes one/ten-agent proof. Full gate remains incomplete.",
      "dependencies": "L6-01, L6-02, L6-03",
      "executor": "lean_delivery/app/src/lean_exchange/delivery_check.py::check; tests/test_delivery_check.py; remaining gate audit pending",
      "outputs": "Read-only access-check CLI, sanitized report and review_access.md; full acceptance package pending",
      "deliverable": "lean_delivery/review_access.md",
      "pct": 25,
      "status": "In progress"
    }
  ]
};
