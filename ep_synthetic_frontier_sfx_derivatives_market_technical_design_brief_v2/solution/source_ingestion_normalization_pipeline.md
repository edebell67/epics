# Source Ingestion and Normalization Pipeline

## Purpose

This pipeline converts official reference rates, offshore spot quotes, and proxy market inputs into a deterministic canonical stream that later workstreams can medianize, smooth, and monitor for health divergence.

## Canonical Source Envelope

All adapters must emit the canonical fields defined in `solution/json/macro_volatility_source_contract.json`:

| Field | Meaning |
| --- | --- |
| `source_id` | Stable adapter/source key used for routing and observability |
| `source_type` | Category: official, offshore, proxy, or derived proxy |
| `poll_interval` | Adapter poll cadence in seconds |
| `normalization_rule` | Named deterministic transformation recipe |
| `staleness_threshold` | Freshness budget in seconds |
| `fallback_priority` | Lower number means higher preference |
| `anomaly_flag` | Highest severity issue attached to the quote |

## Source Categories

| Source Type | Role in Index Layer | Typical Cadence | Primary Failure Mode | Fallback Intent |
| --- | --- | --- | --- | --- |
| `official_reference_rate` | Anchor slow-moving daily fixes and governance-visible reference points | 1h to daily | Late publication or missing fix | Fall back to offshore spot while flagging late official publication |
| `offshore_spot` | Provide the fastest executable market reference for current conditions | 30s to 60s | Transport drops, crossed quotes, stale book | Fall back to proxy sources only after offshore freshness breach |
| `parallel_market_proxy` | Capture observable informal or OTC stress regimes | 5m | Sparse prints, manual desk lag | Use only when official/offshore are stale or divergence confirms regime shift |
| `derived_proxy` | Maintain continuity from regional baskets or correlated instruments | 5m | Model drift or stale dependent legs | Last-resort continuity source with explicit `gap_fill` style flagging |

## Ingestion Stages

### 1. Acquire

- Each adapter polls or receives upstream payloads according to its `poll_interval`.
- Payloads are stamped with `received_at_utc` at ingress.
- Adapter-specific transport errors emit a synthetic record to observability with `anomaly_flag=transport_error`; those records never enter the index-ready stream.

### 2. Parse and Standardize

- Convert vendor field names into canonical names.
- Normalize timestamps to UTC ISO-8601.
- Preserve upstream raw values for audit, but do not publish them downstream as index inputs.
- Reject schema-invalid payloads with `anomaly_flag=schema_error`.

### 3. Normalize Value Orientation

- Convert all quotes to a consistent `BASE/QUOTE` orientation before any comparison.
- Collapse bid/ask into a deterministic midpoint when the source provides both sides.
- Apply source-specific unit normalization:
  - `daily_fix_to_mid_quote_6dp`
  - `bid_ask_mid_to_usd_base_6dp`
  - `proxy_spread_adjusted_mid_6dp`
  - `basket_implied_fx_mid_6dp`
- Round normalized values to 6 decimal places before storage to eliminate adapter-specific floating point drift.

### 4. Quality Gates

- Freshness gate: mark `stale` when `received_at_utc - observed_at_utc > staleness_threshold`.
- Publish-lag gate: mark `late_publish` when an official source misses its expected publication window.
- Outlier gate: mark `outlier` when the normalized value breaches the configured deviation band against the rolling median of live sources.
- Gap-fill gate: mark `gap_fill` when the selected quote is imputed from the last accepted quote or a derived proxy.
- Manual override gate: `manual_hold` blocks the source from all downstream publication paths.

### 5. Rank and Select

- Eligible quotes must not carry blocking anomalies: `schema_error`, `transport_error`, or `manual_hold`.
- Ranking order:
  1. Freshness within threshold
  2. Lower `fallback_priority`
  3. Lower anomaly severity
  4. More recent `observed_at_utc`
- Medianization input set:
  - Require at least two fresh, non-blocked sources for direct medianization.
  - If only one fresh quote remains, publish it only with a degraded-health marker for downstream health monitoring.
  - If no fresh primary sources remain, use the highest-ranked proxy or derived proxy and attach the strongest applicable anomaly flag.

### 6. Persist and Publish

- Store every accepted canonical quote in an append-only normalized source table or log.
- Publish a current source-state snapshot per instrument that includes:
  - active source IDs
  - blocked source IDs
  - selected quote
  - anomaly summary
  - freshness age
- Do not collapse anomaly history; downstream health logic needs full per-source visibility.

## Normalization Rules

| Rule | Applies To | Deterministic Behavior |
| --- | --- | --- |
| `daily_fix_to_mid_quote_6dp` | Official daily or hourly reference publications | Convert the reference fix into canonical pair orientation, emit a single normalized midpoint, round to 6dp |
| `bid_ask_mid_to_usd_base_6dp` | Offshore broker or venue quotes with executable bid/ask | Compute midpoint, invert pair if required, round to 6dp |
| `proxy_spread_adjusted_mid_6dp` | Parallel or OTC desk proxy feeds | Apply desk spread haircut, convert to canonical orientation, round to 6dp |
| `basket_implied_fx_mid_6dp` | Derived proxies from regional baskets or correlated instruments | Compute implied pair from dependency basket, apply configured coefficient, round to 6dp |

## Freshness and Error Policy

| Source Type | Poll Interval | Staleness Threshold | Error Budget Policy |
| --- | --- | --- | --- |
| `official_reference_rate` | 3600s | 14400s | Missing publication degrades health but does not trigger transport paging unless repeated across two expected windows |
| `offshore_spot` | 60s | 300s | Two consecutive transport failures trigger paging and immediate candidate demotion |
| `parallel_market_proxy` | 300s | 1800s | Sparse updates are tolerated if explicitly marked and lower-priority sources are unavailable |
| `derived_proxy` | 300s | 1800s | Only valid as continuity support; never primary when fresher direct sources exist |

## Fallback Behavior

1. Use fresh official and offshore sources together when available.
2. Prefer offshore spot as the live execution anchor once official data becomes stale.
3. Promote proxy sources only after official and offshore inputs fail freshness or are blocked.
4. Promote derived proxies only when no direct source remains publishable.
5. If every candidate is blocked, freeze the last accepted quote, mark `gap_fill`, and raise a degraded-oracle event for downstream circuit-breaker logic.

## Anomaly Flag Semantics

| `anomaly_flag` | Meaning | Downstream Effect |
| --- | --- | --- |
| `none` | Quote is usable and healthy | Eligible for normal medianization |
| `stale` | Observation exceeded freshness threshold | Lower ranking and degraded health |
| `late_publish` | Scheduled official publication missed expected window | Degraded health and governance visibility |
| `outlier` | Value materially diverges from peer sources | Excluded from medianization until reconfirmed |
| `gap_fill` | Continuity value used because live sources were unavailable | Publishable only in degraded mode |
| `schema_error` | Payload failed canonical parse | Block from publication |
| `transport_error` | Adapter could not fetch or receive payload | Block from publication |
| `manual_hold` | Operator or governance system suspended the source | Block from publication |

## Quality Gates

- Every accepted record must contain `source_id`, `source_type`, `poll_interval`, `normalization_rule`, `staleness_threshold`, `fallback_priority`, and `anomaly_flag`.
- Adapter implementations must be deterministic: identical raw input must emit identical normalized output.
- All ranking and exclusion decisions must be reproducible from the stored canonical record plus policy tables.
- Medianization and smoothing tasks must consume only canonical records, never raw adapter payloads.

## Handoff to Downstream Workstreams

- A3 can consume the canonical stream without adapter-specific logic.
- A4 can compute source health, divergence, and degraded-publication conditions directly from the anomaly and freshness metadata.
- Workstream D circuit-breaker logic can rely on the degraded-source states defined here without redefining quote eligibility.
