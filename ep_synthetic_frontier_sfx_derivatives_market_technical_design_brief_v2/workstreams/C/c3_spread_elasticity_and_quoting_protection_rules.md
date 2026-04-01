# C3 Spread Elasticity and Quoting Protection Rules

## Objective

Define a deterministic minimum spread floor that widens when market stress increases so the venue can keep quoting, slow toxic flow, and protect isolated vault capital during frontier macro shocks.

## Dependency Contract

This specification consumes the dependency interfaces declared by B2 and C1.

### B2 market-state inputs

- `volatility_acceleration`: normalized `dVol/dt` score from recent realized volatility changes.
- `order_flow_velocity`: normalized score for aggressive order-flow burst intensity versus rolling baseline.
- `liquidity_thinning`: normalized score for loss of visible top-of-book depth versus rolling baseline.
- `book_thinning_rate`: raw change in near-touch depth used for trigger conditions.
- `best_bid`, `best_ask`, `mid_price`: reference values for spread publication.
- `market_state_timestamp`: source timestamp for recomputation and publication.

### C1 vault-state inputs

- `vault_imbalance`: `abs(net_exposure_usd) / exposure_cap_usd`, clipped to `0.0-1.0`.
- `vault_capital`, `exposure_cap_usd`, `remaining_headroom_usd`: used for quote-size clamps.
- `instrument_id`: keeps spread control isolated per instrument vault.

## Normalization Rules

All four drivers are consumed as normalized scores in the closed interval `0.0-1.0`.

- `volatility_acceleration_score = clamp(volatility_acceleration, 0.0, 1.0)`
- `order_flow_velocity_score = clamp(order_flow_velocity, 0.0, 1.0)`
- `vault_imbalance_score = clamp(vault_imbalance, 0.0, 1.0)`
- `liquidity_thinning_score = clamp(liquidity_thinning, 0.0, 1.0)`

The B2 and C1 owners may refine raw metric construction, but C3 expects the normalized interface above to remain stable.

## Spread Elasticity Formula

### Governance parameters

- `base_min_spread_bps`: launch default spread floor for a calm market.
- `max_min_spread_bps`: hard ceiling for emergency spread widening.
- `stress_weight_vol = 0.35`
- `stress_weight_flow = 0.20`
- `stress_weight_vault = 0.25`
- `stress_weight_liquidity = 0.20`
- `shock_coupling_weight = 0.25`

### Coupling term

Two combinations matter most during toxic conditions: volatility plus thin depth, and fast aggressive flow plus vault imbalance.

```text
shock_coupling_score =
  max(
    volatility_acceleration_score * liquidity_thinning_score,
    order_flow_velocity_score * vault_imbalance_score
  )
```

### Composite stress score

```text
composite_stress_score =
  0.35 * volatility_acceleration_score +
  0.20 * order_flow_velocity_score +
  0.25 * vault_imbalance_score +
  0.20 * liquidity_thinning_score +
  0.25 * shock_coupling_score
```

### Effective spread floor

```text
effective_min_spread_bps =
  clamp(
    base_min_spread_bps * (1.0 + composite_stress_score),
    base_min_spread_bps,
    max_min_spread_bps
  )
```

The formula explicitly uses the four epic drivers:

- `volatility_acceleration`
- `order_flow_velocity`
- `vault_imbalance`
- `liquidity_thinning`

## Control States

Spread control publishes one of three deterministic states per instrument.

| State | Entry rule | Exit rule | Intent |
| --- | --- | --- | --- |
| `calm` | `composite_stress_score < 0.35` and no driver above `0.60` | Leaves when elevated rule is met for one recompute cycle | Preserve tight quoting and normal size |
| `elevated` | `0.35 <= composite_stress_score < 0.70` or any driver above `0.60` | Returns to calm after 3 consecutive calm recomputes | Widen spread and reduce size before the book destabilizes |
| `shock` | `composite_stress_score >= 0.70` or any driver above `0.85` | Returns to elevated after 5 consecutive non-shock recomputes | Defend the vault and avoid adverse selection during violent moves |

Hysteresis is intentional so the quoting mode does not flap when the market oscillates near a threshold.

## Quoting Protection Rules

The market-making layer must consume the control output directly. Public transparency feeds receive the same state and floor values, excluding proprietary per-maker quote inventory.

| Control output | Calm | Elevated | Shock |
| --- | --- | --- | --- |
| `effective_min_spread_bps` | formula result, typically near base | formula result with visible widening | formula result, usually near cap |
| `quote_size_multiplier` | `1.00` | `0.70` | `0.35` |
| `quote_refresh_interval_ms` | `1500` | `750` | `250` |
| `max_passive_quote_notional_usd` | `remaining_headroom_usd * 0.20` | `remaining_headroom_usd * 0.12` | `remaining_headroom_usd * 0.05` |
| `join_top_of_book_allowed` | `true` | `true`, but not inside `25%` of floor | `false` |
| `cross_spread_for_inventory_rebalance` | `false` | `false` | `false` |
| `cancel_stale_quotes_after_ms` | `3000` | `1500` | `500` |

### Mandatory protections

- Quotes may never be tighter than `effective_min_spread_bps`.
- Quote size must scale by `quote_size_multiplier` before posting.
- Shock mode disables price-improving joins inside the current best spread and forces passive-only quoting.
- If `liquidity_thinning_score >= 0.90` and `volatility_acceleration_score >= 0.80`, cancel all resting maker quotes older than `500 ms` before re-posting.
- If `vault_imbalance_score >= 0.90`, clamp new passive notional to `5%` of remaining headroom even if other drivers have improved.

## Recalculation Cadence and Triggers

### Base cadence

- Recompute once per second for every listed instrument.
- Stamp every control packet with the latest `market_state_timestamp`.
- Publish unchanged values only when the state changes or the spread floor moves by at least `0.5 bps`.

### Immediate recomputation triggers

Recompute without waiting for the next one-second cycle when any of the following occurs:

- `book_thinning_rate` shows a top-five-depth drop greater than `20%` within `3s`.
- `vault_imbalance` changes by at least `0.10` within `5s`.
- `volatility_acceleration_score` crosses `0.70`.
- A liquidation cluster or other stress event from the risk engine is emitted.

## Published Outputs

### Internal trading safeguard payload

- `instrument_id`
- `control_state`
- `effective_min_spread_bps`
- `composite_stress_score`
- `quote_size_multiplier`
- `quote_refresh_interval_ms`
- `max_passive_quote_notional_usd`
- `join_top_of_book_allowed`
- `cancel_stale_quotes_after_ms`
- `market_state_timestamp`

### Public transparency feed payload

- `instrument_id`
- `control_state`
- `effective_min_spread_bps`
- `composite_stress_score`
- `volatility_acceleration`
- `order_flow_velocity`
- `vault_imbalance`
- `liquidity_thinning`
- `market_state_timestamp`

This satisfies the requirement that the outputs can be consumed by both trading safeguards and public transparency feeds.

## Scenario Coverage

| Scenario | Driver profile | Expected result |
| --- | --- | --- |
| `calm` | low volatility acceleration, normal order flow, balanced vault, healthy depth | Spread stays close to base, normal quote size, normal refresh cadence |
| `elevated` | volatility and flow rising, vault leaning, depth softening | Spread widens materially, quote size reduces, stale quotes recycle faster |
| `shock` | violent acceleration, toxic flow, large vault imbalance, severe thinning | Spread approaches cap, quote size drops hard, join-to-best disabled, shock protections activate |

Reference vectors for these scenarios are stored in `verification/c3_spread_elasticity_scenarios.json`.

## Phase-1 Launch Guidance

- Start with a conservative `base_min_spread_bps` that assumes shallow frontier-market depth.
- Keep `max_min_spread_bps` sufficiently high to absorb a first `30-50%` macro shock without exhausting vault headroom.
- Review the driver normalization thresholds after the first month of live observation, but do not change the public output schema without governance notice.
