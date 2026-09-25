---
name: dna-arena-research-access
version: 0.1.0-preview
purpose: Query a subscriber-scoped DNA Strategy Arena for historical research evidence only.
---

# DNA Arena research access skill — preview

This preview is not a credential and does not grant access. A paid subscriber receives a
subscriber-specific `ARENA_API_TOKEN`, current base URL, rate limits and the active API
contract during onboarding.

## Hard boundaries

- Treat every result as historical research evidence, not investment advice or a forecast.
- Never place, simulate, recommend or imply a real-world trade.
- Never connect a brokerage, wallet, exchange account or customer funds.
- Use only the subscriber's bearer token; never request or reuse an owner credential.
- Do not expose the token in messages, logs, files, screenshots or URLs.
- State the evidence window, source time/version and limitations with every summary.

## Connection

```text
Authorization: Bearer ${ARENA_API_TOKEN}
Accept: application/json
```

1. Start with `GET /v1/me` to confirm the token identity and scope.
2. Open a participant connection only when the current API contract requires it.
3. Keep access read-only. If an endpoint could alter an allocation, position, rule, access
   policy or funds, stop and request explicit owner approval.

## Evidence-query pattern

Use the live contract supplied at onboarding. The current research pattern is:

```text
POST /participant/v1/me/queries
{
  "request_id": "<fresh UUID>",
  "revision": 0,
  "kind": "<approved research kind>",
  "limit": <approved limit>,
  "strategy_ids": ["<optional DNA ids>"],
  "window_start": "<optional ISO-8601 timestamp>",
  "window_end": "<optional ISO-8601 timestamp>"
}
```

- Reuse an identical `request_id` only to recover the same receipt; do not silently submit
  changed content with the same identity.
- Retrieve a previous result through the receipt route supplied by the API contract.
- Read subscriber allocation/usage only through the scoped participant endpoint, never as an
  exchange balance or financial account.

## Required research response

For every response to the user, include:

1. The question asked and selected evidence window.
2. What the returned data directly supports.
3. Counter-evidence, missing data or low evidence volume.
4. Source version/time and delivery receipt reference where supplied.
5. This statement: “Historical research only; not investment advice, a trade signal or a forecast.”

## Stop conditions

Stop and ask the subscriber to contact The Tech Principle if:

- the API reports a scope, authentication, capacity or freshness failure;
- the request is for a trading instruction, broker action or a personal financial recommendation;
- a caller asks to change Arena access policy, strategy availability, pricing, funds or another
  agent’s records;
- the answer cannot be supported by the returned evidence.
