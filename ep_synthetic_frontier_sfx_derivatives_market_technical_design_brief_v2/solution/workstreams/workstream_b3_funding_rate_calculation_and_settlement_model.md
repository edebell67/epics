# B3 Funding Rate Calculation And Settlement Model

## Scope

This document defines the deterministic funding-rate model for the synthetic frontier sFX perpetual venue, including the minimum inferred market-state contract, the public formula surface, settlement cadence, and worked examples suitable for transparency disclosures.

The epic requires funding to scale continuously with imbalance, volatility, and open-interest velocity, with no cliff thresholds. Because B1 and B2 are not yet implemented in the workspace, this document defines the minimum contract those workstreams must emit for B3 to be implementable.

## Upstream Contracts

### A3 Reference Inputs

Funding consumes the A3 index output as the macro-volatility anchor:

| Field | Type | Notes |
|---|---|---|
| `instrument_id` | string | Example: `NGNUSD_VOL` |
| `published_index_value` | decimal(12,6) | Canonical macro-volatility index |
| `confidence_score` | decimal(4,3) | Range `[0.000, 1.000]` |
| `calculation_state` | enum | `normal`, `degraded`, `hold_last_value`, `halt` |
| `calculation_timestamp` | ISO-8601 UTC string | Timestamp of the active index bucket |

### Inferred B1 Instrument Configuration Contract

| Field | Type | Notes |
|---|---|---|
| `contract_size` | decimal(18,8) | Notional units per contract |
| `base_funding_rate_per_hour` | decimal(10,8) | Launch default before multipliers |
| `max_abs_funding_rate_per_hour` | decimal(10,8) | Hard governance-approved cap |
| `funding_settlement_interval_minutes` | integer | Launch default `60` |
| `funding_snapshot_interval_seconds` | integer | Launch default `300` |
| `volatility_target` | decimal(10,6) | Reference macro-volatility level for normal state |
| `imbalance_scale_pct` | decimal(8,4) | Soft scale for continuous imbalance response |
| `oi_velocity_scale_per_hour` | decimal(10,6) | Soft scale for open-interest acceleration |
| `vault_spread_retention_pct` | decimal(8,4) | Share of net funding retained by vault when one side is underrepresented |

### Inferred B2 Market-State Contract

| Field | Type | Notes |
|---|---|---|
| `mark_price` | decimal(18,8) | Order-book derived trading mark |
| `best_bid` | decimal(18,8) | Top of book bid |
| `best_ask` | decimal(18,8) | Top of book ask |
| `long_open_interest_usdc` | decimal(18,2) | Gross long exposure |
| `short_open_interest_usdc` | decimal(18,2) | Gross short exposure |
| `net_open_interest_usdc` | decimal(18,2) | `long - short` |
| `open_interest_velocity_per_hour` | decimal(12,6) | First derivative of total OI |
| `stress_multiplier` | decimal(10,6) | Comes from D-series controls later; defaults to `1.0` until available |
| `market_state_timestamp` | ISO-8601 UTC string | Timestamp aligned to the funding snapshot |

## Derived Inputs

The funding engine derives the following publishable control variables every funding snapshot:

| Field | Formula | Range |
|---|---|---|
| `imbalance_pct` | `(long_open_interest_usdc - short_open_interest_usdc) / max(long_open_interest_usdc + short_open_interest_usdc, 1)` | `[-1.000000, 1.000000]` |
| `premium_gap_pct` | `(mark_price - published_index_value) / max(published_index_value, 0.000001)` | unbounded, later clamped |
| `volatility_ratio` | `published_index_value / volatility_target` | `>= 0` |
| `oi_velocity_ratio` | `abs(open_interest_velocity_per_hour) / oi_velocity_scale_per_hour` | `>= 0` |
| `confidence_modifier` | `max(confidence_score, 0.25)` | `[0.25, 1.00]` |

The `confidence_modifier` slows funding when the index is weak. This preserves determinism without creating a hard threshold.

## Funding Design Principles

- Funding exists to pay the crowded side to transfer carry toward the underrepresented side and the vault.
- Funding must react continuously. No branch in the formula is allowed to jump only after a threshold is crossed.
- Funding must remain explainable with a public formula and public parameter bands even if the implementation code remains private.
- Funding should amplify when imbalance, macro volatility, and open-interest acceleration rise together.
- Funding cannot rely on premium-to-index spread alone because the epic explicitly centers imbalance, volatility, and open-interest velocity.

## Funding Formula

### Continuous Scaling Components

The model uses smooth bounded transforms instead of cliff thresholds:

`imbalance_component = tanh(imbalance_pct / imbalance_scale_pct)`

`volatility_component = 1 + 0.60 * max(volatility_ratio - 1, 0)`

`oi_velocity_component = 1 + 0.35 * min(oi_velocity_ratio, 3)`

`premium_alignment_component = 1 + 0.25 * tanh(premium_gap_pct / 0.05) * sign(imbalance_component)`

`protective_multiplier = stress_multiplier / confidence_modifier`

### Raw Funding Rate

`raw_funding_rate_per_hour = base_funding_rate_per_hour * imbalance_component * volatility_component * oi_velocity_component * premium_alignment_component * protective_multiplier`

### Published Funding Rate

`funding_rate_per_hour = clamp(raw_funding_rate_per_hour, -max_abs_funding_rate_per_hour, max_abs_funding_rate_per_hour)`

This satisfies the epic requirement for continuous scaling:

- `tanh` provides a smooth response around zero and approaches the cap gradually.
- Volatility and OI velocity increase amplitude smoothly rather than switching modes.
- The hard clamp is a governance safety cap, not a behavioral threshold, and is disclosed publicly.

## Sign Convention

### Position-Side Rule

- Positive `funding_rate_per_hour` means longs pay shorts.
- Negative `funding_rate_per_hour` means shorts pay longs.
- A rate of `0` means neither side pays funding for that interval.

### Economic Interpretation

- If longs dominate open interest, `imbalance_component` becomes positive and the model tends to make longs pay.
- If shorts dominate open interest, `imbalance_component` becomes negative and the model tends to make shorts pay.
- If market price is moving in the same direction as crowding, `premium_alignment_component` strengthens the transfer.
- If market price moves against the crowded side, the premium-alignment term softens funding but does not reverse it unless the broader crowding state truly flips.

## Funding Snapshot And Settlement Cadence

## Snapshot Cadence

- Funding inputs are sampled every `funding_snapshot_interval_seconds`, default `300` seconds.
- Each snapshot computes a provisional `funding_rate_per_hour`.
- The publishable interval rate is the time-weighted average of all snapshots in the settlement window.

## Settlement Cadence

- Settlement occurs every `funding_settlement_interval_minutes`, default `60`.
- Funding is accrued continuously between settlements using the latest provisional rate for each snapshot bucket.
- The settlement engine emits:
  - `funding_interval_start`
  - `funding_interval_end`
  - `average_funding_rate_per_hour`
  - `settlement_fraction = settlement_interval_minutes / 60`
  - per-account `settlement_amount_usdc`

## Account-Level Settlement Formula

For a position with signed notional `position_notional_usdc`:

`position_funding_amount_usdc = position_notional_usdc * average_funding_rate_per_hour * settlement_fraction`

Settlement sign is applied from the position direction:

- Long account cashflow = `-position_notional_usdc * average_funding_rate_per_hour * settlement_fraction`
- Short account cashflow = `+position_notional_usdc * average_funding_rate_per_hour * settlement_fraction`

If the published rate is negative, the economic payer/receiver relationship reverses automatically.

## Vault Settlement Path

The vault participates when matched payer and receiver notionals are not equal in the settlement window.

### Rules

1. Calculate gross payer obligations from the paying side.
2. Calculate gross receiver entitlements on the receiving side.
3. If payer notional equals receiver notional, funding transfers peer to peer and the vault only retains any predeclared spread.
4. If one side is structurally smaller, the vault absorbs the residual:
   - receives residual funding when the crowded side payer base is larger than the receiver base
   - pays residual funding when the venue intentionally subsidizes the minority side and governance permits it
5. Residual vault participation must respect per-instrument exposure caps defined in C1.

### Default MVP Rule

For launch, use a conservative residual rule:

- The minority side receives funding only up to its live open-interest base.
- Any remainder is retained by the vault as `funding_spread_income`.
- The vault does not pay out beyond collected funding in the same interval.

This keeps the model anti-fragile during one-sided markets and aligns with the epic's vault-backstop design.

## Index Degradation Handling

Funding uses A3 index-state outputs directly:

| A3 State | Funding Behavior |
|---|---|
| `normal` | Standard funding calculation |
| `degraded` | Apply full formula but publish the lower `confidence_score` alongside the rate |
| `hold_last_value` | Continue funding with `confidence_modifier`, which increases protection and reduces responsiveness |
| `halt` | Freeze new funding rate publication at `0` and escalate to D-series control logic |

This keeps funding deterministic while preventing weak index states from causing aggressive oscillation.

## Public Transparency Contract

The following outputs are safe to publish without exposing proprietary implementation internals:

| Field | Description |
|---|---|
| `instrument_id` | Instrument being funded |
| `funding_rate_per_hour` | Published signed funding rate |
| `average_funding_rate_per_hour` | Settlement-window average of provisional rates |
| `settlement_interval_minutes` | Current cadence |
| `imbalance_pct` | Signed long-short imbalance |
| `volatility_metric` | Current A3 `published_index_value` |
| `open_interest_velocity_per_hour` | Current OI acceleration signal |
| `funding_multiplier` | Product of `volatility_component * oi_velocity_component * premium_alignment_component * protective_multiplier` |
| `calculation_state` | Current A3 state used by funding |
| `confidence_score` | A3 confidence published alongside funding |
| `max_abs_funding_rate_per_hour` | Governance-approved cap |

The public can reconstruct funding behavior from the disclosed fields and formulas without requiring the private matching-engine code.

## Governance Parameter Bands

Suggested MVP launch defaults:

| Parameter | Launch Default | Governance Band |
|---|---|---|
| `base_funding_rate_per_hour` | `0.000100` | `0.000050` to `0.000300` |
| `max_abs_funding_rate_per_hour` | `0.002500` | `0.001500` to `0.005000` |
| `funding_settlement_interval_minutes` | `60` | `30` to `240` |
| `funding_snapshot_interval_seconds` | `300` | `60` to `900` |
| `imbalance_scale_pct` | `0.250000` | `0.100000` to `0.500000` |
| `oi_velocity_scale_per_hour` | `0.400000` | `0.100000` to `1.000000` |
| `vault_spread_retention_pct` | `0.100000` | `0.000000` to `0.250000` |

These are soft calibration values. The public formula remains unchanged if governance adjusts them inside approved bands.

## Worked Example 1: Normal Balanced Market

Inputs:

- `published_index_value = 0.080000`
- `mark_price = 0.081200`
- `long_open_interest_usdc = 5,300,000`
- `short_open_interest_usdc = 4,900,000`
- `open_interest_velocity_per_hour = 0.120000`
- `confidence_score = 0.920`
- `stress_multiplier = 1.000000`

Result summary:

- Modest positive imbalance produces a small positive funding rate.
- Volatility is near target, so amplification remains low.
- Longs pay shorts at a controlled rate that nudges the book back toward balance.

## Worked Example 2: Stress Long Crowding

Inputs:

- `published_index_value = 0.132000`
- `mark_price = 0.145000`
- `long_open_interest_usdc = 8,400,000`
- `short_open_interest_usdc = 2,100,000`
- `open_interest_velocity_per_hour = 0.680000`
- `confidence_score = 0.880`
- `stress_multiplier = 1.350000`

Result summary:

- Severe long crowding, high volatility, and fast OI expansion multiply together.
- Funding remains continuous but rises sharply toward the governance cap.
- The crowded long side pays; the minority short side receives up to its live notional base, with residual collected by the vault.

## Worked Example 3: Reversal Short Crowding

Inputs:

- `published_index_value = 0.071000`
- `mark_price = 0.068000`
- `long_open_interest_usdc = 3,000,000`
- `short_open_interest_usdc = 5,900,000`
- `open_interest_velocity_per_hour = 0.280000`
- `confidence_score = 0.830`
- `stress_multiplier = 1.100000`

Result summary:

- Negative imbalance produces a negative funding rate.
- Shorts pay longs because the short side is crowded.
- The model stays symmetric without introducing separate logic branches for long-heavy and short-heavy markets.

## Verification Expectations

- Funding design uses continuous scaling with no cliff thresholds.
- Worked examples show amplification under imbalance and stressed-volatility conditions.
- Published outputs are sufficient for the transparency layer without revealing private implementation code.

## Deliverable Notes

- This document is implementation-ready for a matching-engine or risk-service team.
- The companion JSON artifact stores deterministic scenarios with expected intermediate and final outputs for future automated tests.
