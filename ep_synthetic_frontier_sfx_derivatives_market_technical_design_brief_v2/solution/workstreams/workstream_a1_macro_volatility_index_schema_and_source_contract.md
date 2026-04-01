# Workstream A1: Macro Volatility Index Schema and Source Contract

## 1. Purpose

This document defines the canonical source contract for phase-1 macro volatility indices covering `NGN`, `KES`, `GHS`, and `ZAR`.

The contract standardizes:

- index input observations collected from official, offshore, and proxy venues
- normalized source records used by the weighting and smoothing engine
- published index outputs consumed by funding, liquidation, and circuit-breaker controls

The design target is deterministic downstream behavior even when some source classes are missing, stale, or degraded.

## 2. Publication Semantics

- Publication cadence: every 60 seconds on a fixed UTC minute boundary
- Observation timestamp: RFC 3339 / ISO-8601 UTC timestamp for the source observation time
- Publication timestamp: RFC 3339 / ISO-8601 UTC timestamp for the index record release time
- Deterministic ordering: all source records are sorted by `instrument_id`, `source_type`, `source_id`, then `observation_timestamp`
- Quorum rule: publish only when at least two source classes are usable or one source class is usable with a previous valid smoothed state inside the replay window
- Replay window: 30 minutes of prior normalized observations may be used for smoothing continuity, but never to satisfy freshness
- Freshness gating:
  - official reference inputs: stale after 24 hours
  - offshore price inputs: stale after 10 minutes
  - parallel market proxy inputs: stale after 15 minutes
- Nullable semantics:
  - raw source fields may be null when the source class does not exist for an instrument
  - published index output fields may not be null except `degraded_reason`
- Units:
  - prices and index values are stored as quote-currency units per 1 USD
  - weights are decimal fractions in `[0,1]`
  - smoothing windows are integer seconds

## 3. Canonical Records

### 3.1 Input Observation Record

Each upstream adapter must emit a normalized source observation with the following fields.

| Field | Type | Precision / Format | Nullable | Description |
|---|---|---|---|---|
| `schema_version` | string | `a1.v1` | No | Contract version for backward compatibility |
| `instrument_id` | string | enum: `NGN_VOL`, `KES_VOL`, `GHS_VOL`, `ZAR_VOL` | No | Phase-1 instrument identifier |
| `source_id` | string | slug | No | Stable identifier for the exact upstream feed |
| `source_type` | string | enum | No | `official_reference_rate`, `offshore_price`, `parallel_market_proxy` |
| `source_class_rank` | integer | 1-3 | No | Predefined quality class order, lower is better |
| `observation_timestamp` | string | RFC 3339 UTC | No | Time the source value was observed or published |
| `ingestion_timestamp` | string | RFC 3339 UTC | No | Time the platform ingested the record |
| `quote_value` | number | decimal(18,8) | No | Raw quote in local-currency units per USD |
| `quote_currency` | string | ISO-like code | No | `NGN`, `KES`, `GHS`, or `ZAR` |
| `usd_notional_basis` | number | decimal(18,2) | Yes | Approximate transaction size represented by the quote if available |
| `source_weight` | number | decimal(8,6) | No | Pre-normalized source weight after source-quality policy |
| `freshness_seconds` | integer | whole seconds | No | Age of the observation at computation time |
| `source_quality_flag` | string | enum | No | `ok`, `degraded`, `stale`, `manual_holdout`, `rejected` |
| `collection_method` | string | enum | No | `api`, `file_drop`, `manual_capture`, `derived_proxy` |
| `quality_notes` | string | text | Yes | Optional annotation for audit and health monitoring |

### 3.2 Published Index Output Record

Each minute, the index publisher emits one output record per instrument.

| Field | Type | Precision / Format | Nullable | Description |
|---|---|---|---|---|
| `schema_version` | string | `a1.v1` | No | Contract version |
| `instrument_id` | string | enum | No | Instrument identifier |
| `publication_timestamp` | string | RFC 3339 UTC | No | Time the index record is published |
| `effective_observation_timestamp` | string | RFC 3339 UTC | No | Latest common usable source timestamp included in the calculation |
| `official_reference_rate` | number | decimal(18,8) | Yes | Official rate used for this publication if fresh enough |
| `offshore_price` | number | decimal(18,8) | Yes | Offshore rate used for this publication if available |
| `parallel_market_proxy` | number | decimal(18,8) | Yes | Parallel or derived proxy rate used for this publication if available |
| `smoothing_window` | integer | whole seconds | No | Effective smoothing window applied to the minute output |
| `weighted_median_input_value` | number | decimal(18,8) | No | Weighted and medianized pre-smoothed rate |
| `medianized_index_value` | number | decimal(18,8) | No | Final published rate after smoothing |
| `index_return_1h` | number | decimal(10,6) | No | One-hour absolute return metric used by funding logic |
| `index_return_24h` | number | decimal(10,6) | No | One-day absolute return metric used by circuit-breaker context |
| `usable_source_count` | integer | whole number | No | Count of sources that passed quality gating |
| `source_weight_sum` | number | decimal(8,6) | No | Sum of accepted source weights |
| `market_state_flag` | string | enum | No | `normal`, `degraded`, `protected`, `halted` |
| `source_quality_flag` | string | enum | No | Aggregate source-quality state for this publication |
| `degraded_reason` | string | text | Yes | Required when `market_state_flag != normal` |

## 4. Source Taxonomy and Rules

| Source Type | Definition | Required Fields | Freshness Threshold | Typical Use |
|---|---|---|---|---|
| `official_reference_rate` | Published official or administrator fixing for the local currency | `quote_value`, `observation_timestamp`, `source_id` | 24h | Baseline anchor for liquidation and public disclosure |
| `offshore_price` | Observable executable offshore quote, NDF-implied rate, or institutional reference market price | `quote_value`, `usd_notional_basis`, `observation_timestamp` | 10m | Primary near-real-time market input for funding and stress sensing |
| `parallel_market_proxy` | Derived proxy from regulated cross markets, dealer surveys, or validated OTC indications | `quote_value`, `observation_timestamp`, `quality_notes` | 15m | Secondary resiliency input and circuit-breaker divergence checks |

Source-quality handling:

- `ok`: accepted directly into weighting
- `degraded`: accepted with capped weight reduction of at least 50%
- `stale`: excluded from the current publication
- `manual_holdout`: excluded because governance or operator policy intentionally suppresses the source
- `rejected`: excluded because parsing, range, or anomaly rules failed

## 5. Phase-1 Instrument Matrix

| Instrument | Official Reference | Offshore Price | Parallel Market Proxy | Default Smoothing Window | Minimum Usable Sources |
|---|---|---|---|---|---|
| `NGN_VOL` | Required daily anchor | Strongly expected | Required fallback class | 900 | 2 |
| `KES_VOL` | Required daily anchor | Optional but preferred | Required fallback class | 600 | 2 |
| `GHS_VOL` | Required daily anchor | Optional but preferred | Required fallback class | 900 | 2 |
| `ZAR_VOL` | Required daily anchor | Required | Optional fallback class | 300 | 2 |

Instrument-specific rules:

- `NGN_VOL`
  - highest expected use of `parallel_market_proxy` during official/offshore dislocations
  - `parallel_market_proxy` may contribute up to 0.45 of weight in degraded states
- `KES_VOL`
  - offshore input may be absent for long periods; this does not block publication if official plus proxy remain fresh
- `GHS_VOL`
  - daily official prints can lag; smoothing must preserve continuity while refusing stale official rates after 24 hours
- `ZAR_VOL`
  - deeper offshore observability allows shorter smoothing and tighter circuit-breaker anchoring

## 6. Per-Instrument Field Dictionary

### 6.1 Shared Output Obligations

All instruments must emit:

- `medianized_index_value` for funding reference and public transparency
- `official_reference_rate` when fresh for liquidation anchor explainability
- `market_state_flag` and `source_quality_flag` for circuit-breaker and health-monitoring consumers

### 6.2 Instrument Overrides

| Instrument | `official_reference_rate` | `offshore_price` | `parallel_market_proxy` | Notes |
|---|---|---|---|---|
| `NGN_VOL` | nullable only when stale or unavailable | nullable | non-null when used to satisfy quorum | Designed for fragmented markets |
| `KES_VOL` | nullable only when stale or unavailable | nullable | normally non-null | Proxy-supported continuity |
| `GHS_VOL` | nullable only when stale or unavailable | nullable | normally non-null | High smoothing bias |
| `ZAR_VOL` | nullable only when stale or unavailable | normally non-null | nullable | Offshore-led near-real-time anchor |

## 7. Funding, Liquidation, and Circuit-Breaker Support

- Funding support:
  - `medianized_index_value`, `index_return_1h`, and `usable_source_count` provide deterministic funding inputs
- Liquidation support:
  - `official_reference_rate`, `weighted_median_input_value`, and `effective_observation_timestamp` provide a defensible liquidation anchor and audit trail
- Circuit-breaker support:
  - `market_state_flag`, `source_quality_flag`, `index_return_24h`, and divergence across source classes support automated protection and halts

## 8. Worked Example: `NGN_VOL`

### 8.1 Raw Inputs

| source_id | source_type | observation_timestamp | quote_value | source_weight | source_quality_flag |
|---|---|---|---|---|---|
| `ngn_official_fix` | `official_reference_rate` | `2026-03-13T12:00:00Z` | `1585.25000000` | `0.400000` | `ok` |
| `ngn_offshore_ref` | `offshore_price` | `2026-03-13T12:00:20Z` | `1598.10000000` | `0.350000` | `ok` |
| `ngn_proxy_otc` | `parallel_market_proxy` | `2026-03-13T12:00:35Z` | `1606.40000000` | `0.250000` | `degraded` |

### 8.2 Normalized Calculation

- accepted sources: 3
- normalized weight sum: `1.000000`
- weighted median input value: `1598.10000000`
- smoothing window: `900`
- prior smoothed state: `1592.80000000`
- final `medianized_index_value`: `1594.56666667`

### 8.3 Published Record

```json
{
  "schema_version": "a1.v1",
  "instrument_id": "NGN_VOL",
  "publication_timestamp": "2026-03-13T12:01:00Z",
  "effective_observation_timestamp": "2026-03-13T12:00:20Z",
  "official_reference_rate": 1585.25,
  "offshore_price": 1598.1,
  "parallel_market_proxy": 1606.4,
  "smoothing_window": 900,
  "weighted_median_input_value": 1598.1,
  "medianized_index_value": 1594.56666667,
  "index_return_1h": 0.0184,
  "index_return_24h": 0.0642,
  "usable_source_count": 3,
  "source_weight_sum": 1.0,
  "market_state_flag": "normal",
  "source_quality_flag": "degraded",
  "degraded_reason": "parallel_market_proxy accepted with reduced confidence weight"
}
```

## 9. Versioning

- Contract owner: Workstream A index data layer
- Initial version: `a1.v1`
- Backward-incompatible changes require a new version string and explicit downstream migration notes
- New source classes may be added only if they remain ignorable by older consumers
