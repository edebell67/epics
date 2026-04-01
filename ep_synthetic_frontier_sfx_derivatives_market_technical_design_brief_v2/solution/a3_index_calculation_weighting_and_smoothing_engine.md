# A3 Index Calculation, Weighting, and Smoothing Engine

## Scope

This document defines the deterministic calculation path that converts normalized source observations into the publishable macro volatility index used by the sFX funding, liquidation, and circuit-breaker layers.

Because A1 and A2 are not yet implemented in the workspace, this document includes the minimum inferred normalized input contract required to make A3 self-contained.

## Inferred Normalized Input Contract

Each calculation cycle operates on a single instrument and a single timestamp bucket.

| Field | Type | Notes |
|---|---|---|
| `instrument_id` | string | Phase-1 examples: `NGNUSD_VOL`, `KESUSD_VOL`, `GHSUSD_VOL`, `ZARUSD_VOL` |
| `calculation_timestamp` | ISO-8601 UTC string | Rounded to the configured calculation interval |
| `source_id` | string | Unique per source feed |
| `source_type` | enum | `official`, `offshore`, `parallel_proxy` |
| `normalized_volatility_value` | decimal(10,6) | Unitless volatility score after A2 normalization |
| `staleness_seconds` | integer | Age of source sample at calculation time |
| `quality_score` | decimal(4,3) | Range `[0.000, 1.000]`, produced by normalization checks |
| `anomaly_flag` | boolean | `true` means keep source in audit trail but exclude from active set |
| `source_priority` | integer | Lower value means preferred source when tie-breaking audit views |

## Configuration

| Parameter | Value | Rationale |
|---|---|---|
| `calculation_interval` | 60 seconds | Fast enough for controls, slow enough for noisy macro data |
| `freshness_soft_limit` | 120 seconds | Data older than this is penalized but may still contribute |
| `freshness_hard_limit` | 300 seconds | Data older than this is excluded |
| `source_type_base_weight.official` | 1.00 | Highest trust |
| `source_type_base_weight.offshore` | 0.85 | Market-observed but can be thinner |
| `source_type_base_weight.parallel_proxy` | 0.65 | Useful fallback, lower directness |
| `smoothing_alpha.normal` | 0.35 | Balanced responsiveness |
| `smoothing_alpha.degraded` | 0.20 | Slower movement when the input set is weak |
| `minimum_publishable_sources` | 2 | Fewer than 2 valid sources enters hold-last-value degraded mode |
| `hold_last_value_ttl` | 900 seconds | Publish stale-with-warning before hard stop |

## Algorithm Summary

1. Collect all normalized observations for `instrument_id` in the active `calculation_timestamp` bucket.
2. Exclude observations where `anomaly_flag = true` or `staleness_seconds > freshness_hard_limit`.
3. Compute each surviving source weight:
   - `freshness_factor = max(0, 1 - (staleness_seconds / freshness_hard_limit))`
   - `raw_weight = source_type_base_weight[source_type] * quality_score * freshness_factor`
4. Discard observations where `raw_weight = 0`.
5. Compute the weighted median of `normalized_volatility_value` using `raw_weight`.
6. Determine regime:
   - `normal` if valid source count >= 3 and at least one `official` or `offshore` source exists
   - `degraded` if valid source count = 2
   - `hold_last_value` if valid source count < 2 and previous published value is still inside `hold_last_value_ttl`
   - `halt` if valid source count < 2 and no eligible last published value exists
7. Smooth the medianized value:
   - `smoothed_index = alpha * current_weighted_median + (1 - alpha) * previous_published_index`
   - use `alpha = smoothing_alpha.normal` in `normal`
   - use `alpha = smoothing_alpha.degraded` in `degraded`
   - in `hold_last_value`, reuse the previous published index unchanged
8. Emit `confidence_score` and a machine-consumable status payload.

## Weighting Function

### Source-Type Hierarchy

Source weighting is trust-biased, not volume-biased:

- Official reference rates anchor the index whenever available.
- Offshore pricing contributes substantial signal without dominating official data.
- Parallel-market proxies are included as resilience inputs and should influence the median only when closer-trust sources are sparse or conflicting.

### Weight Formula

`raw_weight = base_weight(source_type) * quality_score * freshness_factor`

Where:

- `base_weight(official) = 1.00`
- `base_weight(offshore) = 0.85`
- `base_weight(parallel_proxy) = 0.65`
- `freshness_factor = max(0, 1 - staleness_seconds / 300)`

This keeps the engine deterministic, monotonic, and auditable while avoiding hard discontinuities until the hard freshness cutoff is reached.

## Medianization Rule

The engine uses a weighted median rather than a weighted mean.

Reason:

- It limits the influence of one bad but high-confidence source.
- It behaves predictably in source-conflict scenarios.
- It matches the epic requirement for medianisation across sources.

### Weighted Median Procedure

1. Sort active sources by `normalized_volatility_value` ascending.
2. Sum all `raw_weight` values into `total_weight`.
3. Walk the sorted list cumulatively.
4. The first source where `cumulative_weight >= total_weight / 2` defines the `weighted_median_value`.
5. If two adjacent points land exactly on the halfway boundary, choose the lower value.

The lower-value tie break is intentional so every calculation path has a single deterministic output.

## Smoothing Function

The published index is the exponentially weighted moving average of the current weighted median and the previous published index.

### Formula

`published_index_t = alpha * weighted_median_t + (1 - alpha) * published_index_(t-1)`

### Regime-Specific Alpha

| Regime | Alpha | Behavior |
|---|---|---|
| `normal` | 0.35 | Tracks changes with moderate responsiveness |
| `degraded` | 0.20 | Slows moves when the source set is weak |
| `hold_last_value` | 0.00 | Freezes the prior value while surfacing degraded confidence |

The first-ever calculation for an instrument uses `published_index_0 = weighted_median_0`.

## Confidence Score

The confidence score is published on a `0.000` to `1.000` scale.

### Formula

`confidence_score = min(1.0, 0.50 * source_count_factor + 0.30 * weight_quality_factor + 0.20 * source_diversity_factor)`

Where:

- `source_count_factor = min(valid_source_count / 3, 1.0)`
- `weight_quality_factor = sum(raw_weight) / sum(base_weight(source_type) for valid sources)`
- `source_diversity_factor = distinct(source_type among valid sources) / 3`

Interpretation:

- `>= 0.80`: fully publishable normal state
- `0.50 - 0.79`: degraded but still consumable
- `< 0.50`: hold-last-value or pre-halt warning state

## Edge-Case Behavior

### Conflicting Sources

If one source materially diverges but remains non-anomalous, the weighted median suppresses its directional dominance. The divergent source still affects confidence through aggregate weight quality and diversity.

### Two-Source Degraded Mode

With exactly two valid sources:

- calculate weighted median normally
- smooth with degraded `alpha = 0.20`
- mark `calculation_state = degraded`
- reduce confidence score naturally through `source_count_factor`

### One-or-Zero Source Mode

If fewer than two valid sources remain:

- reuse the last published value if it is not older than `hold_last_value_ttl`
- emit `calculation_state = hold_last_value`
- cap `confidence_score` at `0.49`

If the last published value is older than `hold_last_value_ttl`:

- emit `calculation_state = halt`
- do not publish a fresh index value
- downstream controls must transition to safe fallback behavior

## Pseudocode

```text
function calculate_index(instrument_id, timestamp_bucket, observations, previous_publish):
    active = []

    for obs in observations:
        if obs.anomaly_flag:
            continue
        if obs.staleness_seconds > 300:
            continue

        freshness_factor = max(0, 1 - obs.staleness_seconds / 300)
        raw_weight = base_weight(obs.source_type) * obs.quality_score * freshness_factor

        if raw_weight > 0:
            active.append({
                value: obs.normalized_volatility_value,
                weight: raw_weight,
                source_type: obs.source_type
            })

    if len(active) < 2:
        if previous_publish.exists and previous_publish.age_seconds <= 900:
            return held_output(previous_publish.value, active)
        return halt_output()

    weighted_median = compute_weighted_median(active)
    state = "normal" if len(active) >= 3 and has_high_trust_source(active) else "degraded"
    alpha = 0.35 if state == "normal" else 0.20

    if previous_publish.exists:
        published_index = alpha * weighted_median + (1 - alpha) * previous_publish.value
    else:
        published_index = weighted_median

    confidence_score = compute_confidence(active, state)

    return {
        instrument_id: instrument_id,
        calculation_timestamp: timestamp_bucket,
        weighted_median_value: weighted_median,
        published_index_value: published_index,
        confidence_score: confidence_score,
        calculation_state: state
    }
```

## Downstream Consumption Contract

### Funding Consumption

- Consume `published_index_value` as the canonical macro volatility anchor.
- Consume `confidence_score` to scale protective funding multipliers in later workstreams.
- Treat `hold_last_value` as a warning state and `halt` as a no-settlement escalation input.

### Liquidation Consumption

- Consume `published_index_value` as the liquidation reference family input, not as the market execution price.
- If `calculation_state = hold_last_value`, reduce leverage bands or require conservative liquidation buffers in downstream risk logic.
- If `calculation_state = halt`, stop opening new risk until the index recovers.

### Circuit Breaker Consumption

- Compare market price divergence against `published_index_value`.
- Use `confidence_score` and `calculation_state` to distinguish data weakness from true market dislocation.
- Treat `halt` as an immediate circuit-breaker trigger candidate.

## Reference Test Vector Summary

| Scenario | Expected State | Expected Behavior |
|---|---|---|
| `normal` | `normal` | Three valid sources, weighted median published with normal smoothing |
| `source_conflict` | `normal` | Divergent proxy source does not dominate due to weighted median |
| `degraded_data` | `hold_last_value` | Sparse/stale inputs freeze the last good index and depress confidence |

## Deliverable Notes

- This document is designed to be directly implementable in code.
- The companion verification artifact stores explicit scenario inputs and expected outputs for deterministic testing.
