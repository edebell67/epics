# Public Transparency Data Contract And Disclosure Pack

## Scope

This pack defines the publishable market-state contract for the sFX transparency layer described in epic section 6. It covers the exact public metrics, their source systems, update cadences, disclosure wording, and the redaction boundary between deterministic formulas and proprietary implementation detail.

## Publication Model

- Publish one `PublicTransparencySnapshot` payload for the venue at a deterministic cadence.
- Emit immediate republish events when `market_status` changes state.
- Keep field names stable across versions and increment `schema_version` on breaking changes.
- Expose per-instrument arrays for instrument-level controls and venue-level objects for shared state.

## Update Cadence

| Public metric | Cadence | Trigger |
| --- | --- | --- |
| `long_short_imbalance` | 30 seconds | Scheduled snapshot or material imbalance refresh |
| `open_interest` | 30 seconds | Scheduled snapshot or material open-interest refresh |
| `market_status` | 60 seconds max | Immediate on halt, degrade, or reopen transition |
| `vault_capital` | 60 seconds | Scheduled snapshot or vault-capital state change |
| `current_leverage_band` | 60 seconds | Scheduled snapshot or leverage recomputation |
| `funding_rate` | 60 seconds | Scheduled snapshot or funding recomputation |
| `volatility_metric` | 60 seconds | Scheduled snapshot or stress recomputation |
| `risk_parameter_band` | 60 seconds | Scheduled snapshot or stress-orchestrator state change |

## Public Metric Definitions

### `vault_capital`

Disclosure wording: Total USDC capital currently available in the DAO vault backstop, including committed and free capacity.

Source system: `C1` vault ledger and exposure engine.

Owner: Vault accounting service.

Formula disclosure:

```text
available_backstop = total - committed_margin
utilization_ratio = committed_margin / total
```

Redaction boundary: wallet topology, signer details, reserve routing, and treasury execution mechanics remain internal.

### `long_short_imbalance`

Disclosure wording: Signed directional imbalance per instrument. Positive values mean longs outweigh shorts; negative values mean shorts outweigh longs.

Source system: `B2` market-state aggregation consumed by the funding engine.

Owner: Market state service.

Formula disclosure:

```text
gross_notional = long_notional + short_notional
imbalance_ratio = (long_notional - short_notional) / gross_notional
net_bias = sign(imbalance_ratio)
```

Redaction boundary: participant-level positions, maker inventories, and internal account groupings remain private.

### `open_interest`

Disclosure wording: Gross open interest per instrument, expressed as both contract count and settlement-currency notional, plus one-hour change.

Source system: `B2` market-state aggregation.

Owner: Market state service.

Formula disclosure:

```text
velocity_1h_pct = ((current_notional - prior_1h_notional) / prior_1h_notional) * 100
```

Redaction boundary: account concentration and order identifiers remain private.

### `current_leverage_band`

Disclosure wording: Live leverage range currently permitted for new or increased positions on each instrument.

Source system: `C2` leverage band engine.

Owner: Risk controls service.

Formula disclosure:

```text
effective_max_leverage =
  clamp(
    governance_max_leverage
    * volatility_scalar
    * imbalance_scalar
    * depth_scalar
    * stress_scalar,
    min_leverage,
    governance_max_leverage
  )
```

Interpretation: the venue publishes the formula shape and the named drivers, while keeping proprietary scalar calibration and anti-gaming buffers internal.

### `funding_rate`

Disclosure wording: Current directional funding transfer used to discourage persistent imbalance and reward the opposing side.

Source system: `B3` funding engine.

Owner: Funding service.

Formula disclosure:

```text
funding_rate =
  imbalance_component
  * volatility_scalar
  * open_interest_velocity_scalar
  * stress_response_multiplier
```

Sign convention:

- Positive rate: longs pay shorts.
- Negative rate: shorts pay longs.

Redaction boundary: exact coefficient calibration, smoothing constants, and market-maker routing logic remain internal.

### `volatility_metric`

Disclosure wording: Public volatility series used to explain leverage compression, funding amplification, and stress-state transitions.

Source system: `A3` index outputs and `D1` stress metrics.

Owner: Index and stress service.

Formula disclosure:

```text
realized_volatility_1h_pct = realized volatility over trailing 1 hour
realized_volatility_24h_pct = realized volatility over trailing 24 hours
volatility_acceleration_pct_per_hour = d(realized_volatility_1h_pct) / dt
```

Redaction boundary: raw source-level ticks, venue-specific weighting, and smoothing coefficients remain internal.

### `risk_parameter_band`

Disclosure wording: Active per-instrument control band after governance limits and stress responses are applied.

Source system: `C1` exposure caps, `C3` spread control, and `D2` stress orchestrator outputs.

Owner: Risk controls service.

Formula disclosure:

```text
risk_parameter_band = {
  effective_min_spread_bps,
  position_cap_notional,
  open_interest_cap_notional,
  funding_multiplier_band,
  stress_level
}
```

Interpretation: this is a publishable control-state snapshot, not a hidden operator override. The venue discloses the active band values and stress level, while keeping private the internal precedence logic weights used to arrive there.

### `market_status`

Disclosure wording: Current venue state and any circuit-breaker stage affecting matching or reopening.

Source system: `D3` circuit-breaker state machine with `D2` response-orchestrator support.

Owner: Market controls service.

Published states:

- `normal`
- `degraded`
- `halted`
- `reopening_stage_1`
- `reopening_stage_2`
- `reopening_stage_3`
- `emergency_read_only`

Publication rule: state changes must be published immediately, even if they occur between scheduled snapshots.

Redaction boundary: internal incident commentary and operator-only coordination notes remain private. No discretionary state may exist outside the published enum set.

## Formula Transparency Principle

The venue publishes:

- The formula shape for each public metric.
- The sign convention and unit of measure.
- The active parameter bands and state enums.
- The upstream owner and refresh cadence.

The venue does not publish:

- Proprietary coefficient tuning and anti-gaming constants.
- Source-weighting internals beyond the public index methodology already disclosed elsewhere.
- Participant identities, wallet routing, or maker-specific quoting logic.

## Publication Rules

- Every published field must map to a named upstream owner.
- Every published field must carry a deterministic maximum staleness window.
- A snapshot is invalid if any required top-level field is missing.
- The public payload is append-only from an audit perspective; corrections require a new `published_at` value and a republished snapshot.
- Governance may adjust bands only within predeclared ranges; the transparency layer publishes the resulting active band, not private deliberation.

## Deliverables

- Contract schema: `solution/transparency/public_transparency_contract.schema.json`
- Example payload: `solution/transparency/public_transparency_snapshot.example.json`
- Publication field catalog: `solution/transparency/public_transparency_field_catalog.csv`
