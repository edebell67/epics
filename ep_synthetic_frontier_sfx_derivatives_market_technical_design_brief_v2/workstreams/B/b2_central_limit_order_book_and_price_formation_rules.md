# B2 Central Limit Order Book and Price Formation Rules

## 1. Purpose

This specification defines the MVP central limit order book (CLOB) for
synthetic frontier perpetual markets. It standardizes order acceptance,
matching, trade-price formation, market-state publication, and derived
depth metrics consumed by funding, risk, stress, and transparency
modules.

The venue is explicitly order-flow priced. The reference index anchors
funding, liquidation, and circuit-breaker logic, but it does not
mechanically set the executable trading price.

## 2. Dependency Contract

This specification depends on the B1 market configuration model exposing
at least the following per-instrument fields:

- `instrument_id`
- `quote_collateral`
- `index_reference`
- `tick_size`
- `lot_size`
- `max_leverage_band`
- `position_size_cap`
- `vault_id`
- `status`

Until B1 is published, these fields are treated as the minimum
configuration contract required for book operation.

## 3. Market Model

### 3.1 Instrument Scope

- One isolated CLOB per `instrument_id`
- Stablecoin-quoted, stablecoin-margined perpetual contracts only
- No cross-margin and no shared order book across instruments
- `status` gates whether a market accepts new orders, cancel-only
  requests, or no order activity

### 3.2 Supported Order Types

Phase-1 launch supports only the following order types:

| order_type | Description | MVP support |
| --- | --- | --- |
| `limit_gtc` | Resting or aggressive limit order with good-till-cancel behavior | Required |
| `limit_ioc` | Immediate-or-cancel limit order; any unfilled size is cancelled | Required |
| `market_ioc` | Marketable order executed against visible book depth up to risk and protection bounds; residual size is cancelled | Required |
| `cancel` | Removes an open resting order | Required |

The engine should reject hidden, iceberg, post-only, pegged, stop, and
auction order variants in phase 1 to keep matching deterministic and
operationally conservative.

## 4. Order Lifecycle

### 4.1 Validation and Admission

An incoming order is accepted only if all checks pass:

1. Market `status` permits the requested action.
2. Price is aligned to `tick_size` when a limit price is supplied.
3. Quantity is aligned to `lot_size`.
4. Quantity does not breach `position_size_cap` after considering the
   participant's existing exposure and outstanding orders.
5. The resulting position respects the current leverage band and any
   spread, circuit-breaker, or stress controls applied by downstream
   modules.
6. Margin is available in the isolated instrument account.

Rejected orders produce a deterministic reject reason and do not mutate
book state.

### 4.2 Matching Sequence

1. Validate and normalize the order.
2. Determine whether the order crosses the best contra quote.
3. Execute matches using price priority first, then time priority within
   each price level.
4. For each fill, decrement resting and aggressing remaining quantity.
5. Remove any resting order whose remaining quantity reaches zero.
6. If residual quantity remains:
   - `limit_gtc`: rest the order at its limit price with a new time
     priority timestamp.
   - `limit_ioc`: cancel the remainder.
   - `market_ioc`: cancel the remainder.
7. Publish the updated market-state snapshot and trade events.

### 4.3 Priority Rules

- Better price always wins over earlier time.
- Within the same price level, earlier accepted order timestamp wins.
- Ties must be broken by a deterministic monotonic sequence id assigned
  by the matching engine.
- Partial fills preserve the resting order's original time priority for
  the unfilled remainder.
- Cancels remove queue priority completely. A replacement order is a new
  order with new time priority.

## 5. Trade Price Formation

### 5.1 Executable Price Rule

- The trade price for each fill is the price of the resting order being
  matched.
- Market orders consume visible opposite-side depth level by level.
- Limit orders execute immediately only against resting quotes priced at
  or better than the incoming limit.

### 5.2 Index Relationship

- The executable trading price is determined by order flow in the CLOB.
- The reference index is not a peg and does not force trade execution at
  any fixed spread or parity.
- The index is used only for:
  - funding rate inputs
  - liquidation reference checks
  - divergence monitoring
  - circuit-breaker anchoring

This separation must remain explicit in all downstream implementations.

### 5.3 Price Protection Rules

Because phase 1 launches with low leverage and thin initial depth, the
matching engine should apply simple deterministic protections:

- Market orders may execute only while visible depth remains inside the
  active circuit-breaker and spread-protection envelope.
- If the next executable level would violate a protection bound, the
  residual quantity is cancelled and the event is logged as a protected
  partial fill.
- No discretionary manual repricing is allowed.

## 6. Market-State Outputs

The matching engine must emit the following normalized outputs per
instrument after every accepted state mutation:

| Output | Description | Consumer |
| --- | --- | --- |
| `trade_price` | Last fill price for the most recent execution | Transparency, charting |
| `last_trade_qty` | Quantity of most recent fill | Transparency, analytics |
| `best_bid` | Highest active bid price | Trading UI, risk |
| `best_bid_size` | Aggregate resting quantity at best bid | Risk, stress |
| `best_ask` | Lowest active ask price | Trading UI, risk |
| `best_ask_size` | Aggregate resting quantity at best ask | Risk, stress |
| `mid_price` | `(best_bid + best_ask) / 2` when both sides exist | Funding, analytics |
| `spread_absolute` | `best_ask - best_bid` | Risk controls |
| `spread_bps` | Spread relative to `mid_price` | Risk controls |
| `depth_snapshot` | Price-level ladder for visible top-of-book depth | UI, stress |
| `depth_snapshot_timestamp` | Event timestamp for the published depth | Audit |
| `executed_volume_1m` | Rolling one-minute traded volume | Analytics, stress |
| `order_count_bid` | Active resting bid order count | Stress |
| `order_count_ask` | Active resting ask order count | Stress |
| `book_imbalance` | Visible top-depth bid vs ask imbalance ratio | Funding, risk |
| `book_thinning_metric` | Rate of loss of visible depth over time | Stress |
| `market_state_version` | Monotonic sequence for replay and reconciliation | Audit, downstream sync |

## 7. Depth Visibility

### 7.1 Publication Requirements

- The book is fully transparent at the published depth horizon.
- Phase 1 must publish at least the top 10 price levels per side and the
  aggregate quantity at each level.
- The venue may internally track deeper levels, but public and risk
  consumers must receive at least the same top-10 ladder.
- No hidden liquidity is included in MVP calculations because hidden
  orders are not supported.

### 7.2 Snapshot Shape

Each `depth_snapshot` should expose, per visible level:

- `side`
- `price`
- `aggregate_qty`
- `order_count`
- `level_rank`
- `snapshot_timestamp`

Snapshots may be generated event-by-event or as incremental updates with
periodic full refreshes, but replay must reconstruct the same visible
book deterministically.

## 8. Derived Metrics

### 8.1 Book Imbalance

For a configurable top-of-book horizon `N`:

`book_imbalance = (sum_bid_qty_N - sum_ask_qty_N) / (sum_bid_qty_N + sum_ask_qty_N)`

Requirements:

- Default phase-1 horizon: top 5 levels per side
- Emit `0` when both sums are zero
- Positive values indicate bid-heavy support; negative values indicate
  ask-heavy pressure

### 8.2 Book Thinning Metric

`book_thinning_metric` measures how quickly visible depth disappears from
the top `N` levels over a rolling interval.

Recommended phase-1 calculation:

`book_thinning_metric = max(0, visible_depth_t_minus_30s - visible_depth_t) / max(visible_depth_t_minus_30s, epsilon)`

Where:

- `visible_depth` is the sum of bid and ask quantity across the top 10
  levels
- default lookback is 30 seconds
- `epsilon` prevents division by zero

Interpretation:

- `0` means depth is stable or improving
- Higher values indicate rapid liquidity withdrawal and should feed
  stress logic

### 8.3 Additional State Inputs for Downstream Modules

The matching engine should also emit:

- `trade_count_1m`
- `cancel_rate_1m`
- `new_order_rate_1m`
- `aggressive_buy_volume_1m`
- `aggressive_sell_volume_1m`
- `price_return_1m`
- `depth_change_1m`

These support future leverage compression, spread elasticity, and stress
classification without changing the core execution semantics.

## 9. Phase-1 Consistency Rules

To remain consistent with the low-leverage MVP launch:

- Matching remains strict price-time priority with no discretionary
  intervention.
- Order types are intentionally narrow.
- Depth visibility is explicit and transparent.
- The order book may trade away from the index when order flow demands
  it; risk controls react through funding and guardrails rather than
  forced pegging.
- Any halt or cancel-only state must come from predefined circuit
  breaker or market-status logic, not manual quote management.

## 10. Open Interfaces

This specification provides the B2 outputs consumed by later tasks:

- B3 funding model consumes `mid_price`, `book_imbalance`,
  `executed_volume_1m`, and trade flow velocity fields.
- C1 vault controls consume `best_bid`, `best_ask`, `depth_snapshot`,
  `book_imbalance`, and `book_thinning_metric`.
- D1 stress metrics consume `book_thinning_metric`, cancel/new-order
  rates, and short-horizon depth changes.

## 11. Acceptance Mapping

The specification satisfies the task verification targets as follows:

1. Trading price is defined as order-flow determined in Sections 1, 5.1,
   5.2, and 9.
2. Depth, imbalance, and thinning outputs are enumerated in Sections 6,
   7, and 8.
3. Matching and market-state rules are internally consistent for a
   phase-1 low-leverage launch in Sections 3, 4, 5.3, and 9.
