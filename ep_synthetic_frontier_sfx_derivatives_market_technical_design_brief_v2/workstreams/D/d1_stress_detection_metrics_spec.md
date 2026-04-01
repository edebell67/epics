# D1 Stress Detection Metrics And Event Thresholds

## Purpose

This specification turns the brief's four stress metrics into deterministic calculations that can be evaluated every 30 seconds and emitted as auditable events for downstream automated response and circuit-breaker workflows.

## Input Contracts

| Upstream | Required fields | Usage |
|----------|-----------------|-------|
| A4 oracle health | `health_score`, `source_quorum`, `divergence_bps`, `instability_state`, `halt_recommendation` | hard-stop overrides and audit context |
| B2 order-book metrics | `best_bid`, `best_ask`, `depth_within_10bps`, `depth_within_25bps`, `mid_price`, `trade_count`, `aggressive_buy_notional`, `aggressive_sell_notional` | volatility, imbalance, and thinning calculations |
| C1 vault model | `net_exposure`, `exposure_cap`, `open_interest`, `vault_utilization` | normalization and severity context |
| C2 leverage engine | `effective_leverage_band`, `stress_velocity`, `realized_volatility` | volatility acceleration anchor and recommended action context |
| C3 spread controls | `effective_min_spread`, `liquidity_thinning`, `order_flow_velocity` | thinning corroboration and response handoff |

## Evaluation Cadence

- Evaluation interval: every 30 seconds per instrument
- All event payloads include the exact window used for each metric
- Metric severities are computed independently, then aggregated into a single `stress_level`

## Metric Definitions

### 1. Volatility Acceleration

Measures how quickly short-horizon realized volatility is rising relative to the instrument's recent baseline.

Formula:

`volatility_acceleration = max(0, (rv_5m - rv_30m) / max(rv_30m, 0.0025))`

Definitions:

- `rv_5m`: annualized realized volatility from 30-second mid-price returns over the last 5 minutes
- `rv_30m`: annualized realized volatility from 30-second mid-price returns over the last 30 minutes
- `0.0025`: floor so low-volatility regimes do not explode on division

Lookback windows:

- short window: 5 minutes
- baseline window: 30 minutes

Thresholds:

| Severity | Condition |
|----------|-----------|
| normal | `< 0.20` |
| warning | `>= 0.20` and `< 0.45` |
| elevated | `>= 0.45` and `< 0.75` |
| emergency | `>= 0.75` |

### 2. Imbalance Slope Change

Measures how fast directional pressure is changing versus the recent baseline, using open-interest imbalance plus aggressive flow confirmation.

Formula:

`imbalance_ratio = (long_open_interest - short_open_interest) / max(open_interest, 1)`

`flow_skew = (aggressive_buy_notional - aggressive_sell_notional) / max(aggressive_buy_notional + aggressive_sell_notional, 1)`

`imbalance_slope_change = abs((slope_2m(imbalance_ratio) - slope_15m(imbalance_ratio)) + 0.35 * slope_2m(flow_skew)) * 10000`

Units:

- basis points of signed imbalance change per minute

Lookback windows:

- short slope window: 2 minutes
- baseline slope window: 15 minutes

Thresholds:

| Severity | Condition |
|----------|-----------|
| normal | `< 12` |
| warning | `>= 12` and `< 25` |
| elevated | `>= 25` and `< 40` |
| emergency | `>= 40` |

### 3. Liquidation Cluster Density

Measures how concentrated forced unwinds are relative to current open interest and whether they are arriving in bursts.

Formula:

`liq_oi_ratio = liquidation_notional_5m / max(open_interest, 1)`

`burst_factor = max(1, peak_liquidation_notional_60s / max(avg_liquidation_notional_60s_5m, 1))`

`liquidation_cluster_density = liq_oi_ratio * burst_factor`

Lookback windows:

- liquidation accumulation: 5 minutes
- burst inspection: rolling 60-second slices inside the 5-minute window

Thresholds:

| Severity | Condition |
|----------|-----------|
| normal | `< 0.015` |
| warning | `>= 0.015` and `< 0.030` |
| elevated | `>= 0.030` and `< 0.050` |
| emergency | `>= 0.050` |

Interpretation:

- `0.015` means liquidations equivalent to 1.5% of current open interest after burst weighting

### 4. Order Book Thinning Rate

Measures how much near-touch liquidity has deteriorated versus the recent baseline.

Formula:

`book_depth_now = avg(depth_within_10bps over last 30s)`

`book_depth_baseline = avg(depth_within_10bps over last 15m)`

`order_book_thinning_rate = max(0, 1 - (book_depth_now / max(book_depth_baseline, 1)))`

Lookback windows:

- current depth window: 30 seconds
- baseline depth window: 15 minutes

Thresholds:

| Severity | Condition |
|----------|-----------|
| normal | `< 0.18` |
| warning | `>= 0.18` and `< 0.35` |
| elevated | `>= 0.35` and `< 0.55` |
| emergency | `>= 0.55` |

Interpretation:

- `0.35` means available depth inside 10 bps has fallen by 35% versus the baseline window

## Aggregate Stress Level

Per-metric severity scores:

- `normal = 0`
- `warning = 1`
- `elevated = 2`
- `emergency = 3`

Aggregation rules:

1. `emergency` if any metric is `emergency`
2. `emergency` if A4 emits `halt_recommendation = true`
3. `emergency` if two or more metrics are `elevated`
4. `elevated` if any metric is `elevated`
5. `elevated` if three or more metrics are `warning`
6. `warning` if any metric is `warning`
7. otherwise `normal`

Cooldown rules:

- Escalation is immediate when a rule fires
- De-escalation requires two consecutive clean evaluation intervals
- Events are re-emitted only when the aggregate level changes or when an `emergency` persists for 5 minutes

## Event Contract

The event payload must be sufficient for D2 automated controls and D3 circuit breakers without requiring a second lookup to reconstruct the trigger.

Required top-level fields:

- `event_id`
- `instrument_id`
- `market_id`
- `event_timestamp`
- `evaluation_window`
- `stress_level`
- `stress_score`
- `metric_values`
- `metric_severities`
- `triggered_thresholds`
- `dependency_snapshot`
- `recommended_actions`
- `oracle_override`
- `audit_context`

Recommended actions by aggregate level:

| Stress level | Recommended actions |
|--------------|---------------------|
| warning | widen spread floor 10%, increase monitoring cadence, freeze leverage increases |
| elevated | compress leverage band 25%, widen spread floor 25%, tighten position caps 15% |
| emergency | compress leverage band 50%, widen spread floor 50%, halt new risk-increasing orders, arm circuit-breaker evaluation |

## Audit And Replay Requirements

- Emit all raw metric values plus the threshold band crossed
- Include upstream snapshot identifiers when available
- Preserve the event sequence as append-only records
- Use UTC ISO-8601 timestamps with millisecond precision

## Worked Severity Example

Example state:

- `volatility_acceleration = 0.51`
- `imbalance_slope_change = 18`
- `liquidation_cluster_density = 0.011`
- `order_book_thinning_rate = 0.39`
- A4 `halt_recommendation = false`

Result:

- metric severities: `elevated`, `warning`, `normal`, `elevated`
- aggregate stress level: `emergency` because two metrics are `elevated`
