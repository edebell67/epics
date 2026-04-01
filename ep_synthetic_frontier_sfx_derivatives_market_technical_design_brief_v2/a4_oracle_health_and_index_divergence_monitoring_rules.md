# A4 Oracle Health and Index Divergence Monitoring Rules

## Purpose

Define deterministic monitoring rules that detect source instability and index-versus-market divergence before those conditions can propagate into funding, liquidation, leverage, or circuit-breaker decisions.

This specification produces explicit outputs for downstream stress and circuit-breaker workflows:

- `health_score`
- `source_quorum`
- `divergence_band`
- `instability_event`
- `halt_recommendation`

## Scope and Assumptions

- Applies per instrument (`NGN`, `KES`, `GHS`, `ZAR`, or other approved phase-1 markets).
- Consumes normalized source observations from the A2 ingestion pipeline.
- Consumes the medianized and smoothed index from the A3 calculation engine.
- Compares the published index against the executable market mid-price from the trading core.
- Uses deterministic thresholds with no discretionary operator override inside the normal monitoring path.

## Monitored Inputs

For each instrument and calculation interval:

- `official_reference_rate`
- `offshore_price`
- `parallel_market_proxy`
- `source_weight`
- `source_quality_flag`
- `source_timestamp`
- `source_latency_ms`
- `medianized_index_value`
- `confidence_score`
- `market_mid_price`
- `best_bid`
- `best_ask`
- `order_book_depth_score`

## Health Score Model

Each source receives a rolling `health_score` in the range `0..100`.

Per-source sub-scores:

- `freshness_score`
  - `100` when age <= poll interval
  - `60` when age is between `1x` and `2x` the staleness threshold
  - `20` when age is between `2x` and `3x` the staleness threshold
  - `0` when age exceeds `3x` the staleness threshold
- `quality_score`
  - `100` when `source_quality_flag=normal`
  - `60` when `source_quality_flag=warning`
  - `20` when `source_quality_flag=degraded`
  - `0` when `source_quality_flag=invalid`
- `latency_score`
  - `100` when latency <= configured p95 target
  - `50` when latency is between `1x` and `2x` target
  - `0` when latency exceeds `2x` target
- `consistency_score`
  - `100` when source deviation from the weighted peer median <= `0.50%`
  - `70` when deviation is `0.50%..1.50%`
  - `30` when deviation is `1.50%..3.00%`
  - `0` when deviation > `3.00%`

Weighted source health formula:

```text
health_score_source =
    0.35 * freshness_score +
    0.25 * quality_score +
    0.15 * latency_score +
    0.25 * consistency_score
```

Instrument-level health formula:

```text
health_score_instrument =
    weighted_average(health_score_source, source_weight)
```

Smoothing rule:

- Apply an EMA with `alpha = 0.20` to reduce flip-flopping caused by single-tick noise.
- A hard invalidation event still bypasses smoothing and sets the affected source contribution to `0` immediately.

Health state bands:

- `healthy`: `health_score_instrument >= 85`
- `watch`: `70..84.99`
- `degraded`: `50..69.99`
- `hard_stop_candidate`: `< 50`

## Source Quorum Rules

The published index is valid only when quorum requirements are satisfied.

Minimum source-category expectations:

- At least `1` official or reference-rate source, when such a source exists for the instrument
- At least `1` market-traded source (`offshore_price` or equivalent)
- At least `3` total active sources across all categories
- At least `60%` of configured source weight must remain active after exclusions

Quorum status definitions:

- `full_quorum`
  - `>= 3` active sources
  - both reference and traded categories represented
  - active weight >= `80%`
- `reduced_quorum`
  - `>= 2` active sources
  - at least one traded category represented
  - active weight between `60%` and `79.99%`
- `quorum_failed`
  - fewer than `2` active sources
  - no traded category represented
  - or active weight < `60%`

Operational effect:

- `full_quorum`: normal publication and downstream control usage allowed
- `reduced_quorum`: publication allowed with `degraded` status, tighter downstream thresholds, and raised monitoring severity
- `quorum_failed`: index may be computed internally for diagnostics but must not be considered authoritative for automated trading-risk actions

## Instability Heuristics

An `instability_event` must be emitted when any of the following conditions are met:

- `source_stale_burst`
  - `>= 2` active sources become stale within `3` consecutive calculation intervals
- `source_flip_flop`
  - a source transitions between valid and invalid states `>= 3` times in `10` intervals
- `peer_dispersion_spike`
  - weighted cross-source dispersion exceeds `2.50%` for `2` consecutive intervals
- `confidence_drop`
  - calculation-engine `confidence_score < 0.60`
- `quorum_degradation`
  - quorum moves from `full_quorum` to `reduced_quorum`
- `quorum_failure`
  - quorum status becomes `quorum_failed`

Severity mapping:

- `warning`: isolated single-source issues without quorum loss
- `elevated`: repeated source instability or reduced quorum
- `emergency`: quorum failure, confidence collapse, or multi-source dispersion spike

## Divergence Measurement and Bands

Divergence is measured against the executable market mid-price.

```text
index_market_divergence_pct =
    abs(medianized_index_value - market_mid_price) / medianized_index_value * 100
```

Supporting conditions:

- If spread is unusually wide, compare against both `market_mid_price` and the closer of `best_bid` or `best_ask`.
- If order book depth is below the minimum executable threshold, divergence severity is increased by one level because observed price becomes less reliable.

Divergence bands:

- `normal`
  - divergence < `1.00%`
- `watch`
  - divergence >= `1.00%` and < `2.50%`
- `degraded`
  - divergence >= `2.50%` and < `4.00%`
- `hard_stop`
  - divergence >= `4.00%`

Persistence rule:

- A band only escalates when the threshold is breached for `2` consecutive intervals.
- A band only de-escalates after `3` consecutive intervals below the lower threshold.

Circuit-breaker trigger alignment from the epic:

- `Index divergence exceeds predefined band`
- `Data source instability detected`
- `Order book depth collapses beyond threshold`

## Event Contract

Each monitoring cycle emits one instrument-scoped event object when any monitored state changes or a threshold persists.

```json
{
  "event_type": "oracle_monitor_state_change",
  "instrument_id": "NGN-PERP",
  "timestamp": "2026-03-16T21:35:36Z",
  "health_score": 78.4,
  "health_state": "watch",
  "source_quorum": "reduced_quorum",
  "divergence_pct": 2.9,
  "divergence_band": "degraded",
  "instability_event": "peer_dispersion_spike",
  "severity": "elevated",
  "order_book_depth_score": 0.41,
  "halt_recommendation": "tighten_controls",
  "reasons": [
    "cross-source dispersion > 2.50% for 2 intervals",
    "index-market divergence >= 2.50% for 2 intervals"
  ]
}
```

Required fields:

- `event_type`
- `instrument_id`
- `timestamp`
- `health_score`
- `health_state`
- `source_quorum`
- `divergence_pct`
- `divergence_band`
- `instability_event`
- `severity`
- `halt_recommendation`
- `reasons`

Allowed `halt_recommendation` values:

- `none`
- `tighten_controls`
- `degraded_mode`
- `pause_new_risk`
- `halt_market`

## Automated Responses and Halt Recommendation

The monitor does not execute trading controls directly. It emits a deterministic recommendation for the stress and circuit-breaker layers.

Recommendation matrix:

- `none`
  - `health_state=healthy`
  - `source_quorum=full_quorum`
  - `divergence_band=normal`
- `tighten_controls`
  - `health_state=watch` or `divergence_band=watch`
  - downstream systems should compress leverage bands and widen minimum spread moderately
- `degraded_mode`
  - `health_state=degraded`
  - or `source_quorum=reduced_quorum`
  - or `divergence_band=degraded`
  - downstream systems should reduce position caps, increase funding multipliers, and block aggressive auto-expansion logic
- `pause_new_risk`
  - `health_score_instrument < 50`
  - or `confidence_score < 0.60`
  - or order-book depth collapse occurs alongside `degraded` divergence
  - downstream systems should reject new risk-increasing orders while still permitting risk reduction and position exits
- `halt_market`
  - `source_quorum=quorum_failed`
  - or `divergence_band=hard_stop`
  - or `peer_dispersion_spike` persists for `3` consecutive intervals with depth collapse
  - or `Data source instability detected` while order-book depth is below the configured emergency threshold

Degraded mode versus hard-stop distinction:

- `degraded_mode`
  - monitoring still permits index publication with explicit warnings
  - automated controls remain active but tighten risk aggressively
  - liquidation references may continue if quorum remains above failure minimum
- `hard_stop`
  - index publication is not authoritative for automated expansion of risk
  - matching may be halted by the circuit-breaker state machine
  - only predefined recovery checks may return the instrument to trading

## Downstream Consumption Rules

Stress-management and circuit-breaker workflows must consume the monitor output as follows:

- D1 stress detection uses:
  - `health_score`
  - `source_quorum`
  - `divergence_band`
  - `severity`
- D2 automated responses use:
  - `halt_recommendation`
  - `reasons`
  - `order_book_depth_score`
- D3 circuit breakers use:
  - `halt_recommendation`
  - `source_quorum`
  - `divergence_band`
  - `instability_event`

## Recovery Rules

An instrument may exit emergency status only when all of the following are true:

- `source_quorum` is at least `reduced_quorum` for `5` consecutive intervals
- `health_score_instrument >= 70` for `5` consecutive intervals
- `divergence_band` is below `degraded` for `5` consecutive intervals
- no `peer_dispersion_spike` or `quorum_failure` event is active
- order-book depth has recovered above the minimum reopening threshold

These rules support the epic requirement that reopening is gradual and rule-based.

## Worked Severity Examples

### Example 1: Reduced-quorum degraded mode

- One reference source goes stale and one offshore source flips invalid twice.
- Active weight drops to `68%`.
- Divergence rises to `2.8%` for two intervals.

Expected output:

- `health_state=degraded`
- `source_quorum=reduced_quorum`
- `divergence_band=degraded`
- `instability_event=quorum_degradation`
- `halt_recommendation=degraded_mode`

### Example 2: Hard-stop candidate due to divergence and depth collapse

- Index remains stable, but executable market mid-price diverges by `4.6%`.
- Order-book depth collapses below the emergency threshold.

Expected output:

- `divergence_band=hard_stop`
- `severity=emergency`
- `halt_recommendation=halt_market`

### Example 3: Hard-stop candidate due to source instability

- Two sources become stale in rapid succession.
- Cross-source dispersion remains above `2.50%` for three intervals.
- Quorum falls below `60%` active weight.

Expected output:

- `source_quorum=quorum_failed`
- `instability_event=quorum_failure`
- `health_state=hard_stop_candidate`
- `halt_recommendation=halt_market`
