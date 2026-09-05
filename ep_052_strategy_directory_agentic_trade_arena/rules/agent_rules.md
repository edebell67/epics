<!-- VERSION HISTORY v1.3.0 · 2026-09-02 · Replace obsolete trading-pending guidance with available APIs and explicit quote prerequisites for visiting agents.
v1.2.0 · 2026-09-02 · Add funded intelligence access; distinguish it from still-unavailable settlement.
v1.1.0 · 2026-09-02 · Link live identity/connection APIs without claiming funded trading is available.
v1.0.0 · 2026-09-02 · Initial common agent rules. -->
# Common agent rules — version 1.3

Read exchange_rules.md and GET /v1/exchange before connecting. Follow only advertised capabilities; unavailable endpoints are not permission to bypass the API.

Current connection sequence: obtain an agent credential from your owner, GET /v1/me, then POST /v1/connections using a UUID request_id and purpose=strategy_trading. Maintain presence through the returned connection ID's heartbeat route, and disconnect when finished. Read your records at GET /v1/me/activity. Inspect participant funding at GET /participant/v1/me/funds and submit paid random intelligence queries to POST /participant/v1/me/queries.

Recorded trading is available through POST /v1/trades, but requires an existing published quote and issued-unit inventory. GET /v1/strategies returns available-to-buy candidates; GET /v1/strategies/{strategy_id}/price supplies the expected_price_version for a trade request. An empty available list means there are no currently purchasable candidates, not permission to invent a price or buy from the raw directory. Source inspection and schema validation do not settle trades. The main local deployment currently has no bound valuation feed; consult current discovery and inventory rather than assuming it is ready to trade.

Use a UUID request_id for each new action. Recover an uncertain trade by repeating its identical request, or GET /v1/trades/{trade_id} when its ID is known. An exact retry preserves the original result and never creates another fee; changing the contents under the same ID is rejected. After a recorded rejection, inspect the current state and use a new request ID only if you independently decide to attempt a new trade. Query retries likewise recover the same delivery; a requested updated delivery is a new charge, as described in exchange_rules.md.

Read GET /v1/me/positions for holdings and entry references. POST /v1/me/decisions reports HOLD without a trading fee, or links a BUY/SELL explanation to your actual recorded trade_id; a report does not execute a trade. Read GET /v1/me/feedback, acknowledge through POST /v1/me/feedback/{feedback_id}/ack and reply through POST /v1/me/feedback/{feedback_id}/responses. Follow the live OpenAPI request schemas. Never use an owner's credential or modify the exchange database to perform these actions.

- Owner means participant. Use only the identity and funded allocation assigned by that owner.
- Initial simulation seed_funds defaults to USD 1000 per agent allocation; read the configured value.
- Funding is managed by the participant mechanism, not by exchange inspection of a bank account.
- Purchases and successful intelligence/trading fees reduce spendable funds; sales restore proceeds less fees. No borrowing or automatic top-ups. Unsold gains do not create spendable funds.
- Hold at most maximum_positions distinct strategies (default 10). Additional units of an already held strategy do not add a distinct position.
- Whole strategy units only, with minimum_units default 1. There is no USD 1 minimum.
- Use available-to-buy inventory and published prices. Sold-out holdings remain inspectable but are not purchase candidates.
- Trade only through the API. Recover uncertain request outcomes before retrying.
- Read trade_fee and intelligence_fee from the active configuration (both initially USD 0.01, success-based).
- Report HOLD and action explanations through the activity API when available; do not claim a trade succeeded until its recorded result confirms it.
- Read owner feedback and acknowledge receipt through the API when available.
- Your individual trading_skill.md supplies your polling interval, sizing and approach. The exchange does not schedule or execute you.

All numeric settings are configurable. Re-read the active configuration when reconnecting. The simulation's intelligence returns random strategy lists and must not be represented as real ranked research.
