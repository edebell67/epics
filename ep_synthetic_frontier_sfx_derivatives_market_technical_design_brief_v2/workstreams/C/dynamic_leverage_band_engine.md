# Dynamic Leverage Band Engine

## Purpose

This engine determines the effective leverage band published for each instrument. It keeps the launch posture at 1x-2x, compresses leverage under deteriorating conditions, and only permits expansion toward governance-approved caps after launch mode is disabled.

## Inputs

| Field | Type | Range | Meaning |
| --- | --- | --- | --- |
| `base_leverage` | float | `1.0` to `governance_max_leverage` | Neutral operating leverage before expansion or compression. |
| `governance_max_leverage` | float | `1.0` to `10.0` | Hard governance cap for the instrument. |
| `launch_max_leverage` | float | `1.0` to `2.0` | Launch-phase hard cap; default `2.0`. |
| `launch_mode` | bool | n/a | When `true`, the engine cannot publish above `launch_max_leverage`. |
| `realized_volatility` | float | `0.0` to `1.0` | Smoothed realized volatility percentile or normalized score from A3. |
| `vault_imbalance` | float | `0.0` to `1.0` | Absolute normalized long-short imbalance pressure from C1. |
| `depth_score` | float | `0.0` to `1.0` | Normalized order-book depth quality from B2; `1.0` is deepest. |
| `stress_velocity` | float | `0.0` to `1.0` | Composite stress acceleration from A3 and B2. |
| `timestamp_utc` | ISO-8601 string | n/a | Snapshot timestamp used for publication and audit. |

## Derived Terms

- `depth_penalty = 1.0 - depth_score`
- `risk_score = 0.35 * realized_volatility + 0.25 * vault_imbalance + 0.20 * depth_penalty + 0.20 * stress_velocity`
- `healthy_score = 0.30 * (1.0 - realized_volatility) + 0.20 * (1.0 - vault_imbalance) + 0.35 * depth_score + 0.15 * (1.0 - stress_velocity)`
- `permitted_cap = min(governance_max_leverage, launch_max_leverage)` when `launch_mode = true`; otherwise `permitted_cap = governance_max_leverage`

Weights sum to `1.0` and include all four epic factors: realized volatility, vault imbalance, order-book depth, and stress velocity.

## Adjustment Function

1. Clamp each normalized input into the `0.0` to `1.0` range.
2. Compute `risk_score` and `healthy_score`.
3. Set `target_leverage`:
   - If `launch_mode = true`, `target_leverage = min(base_leverage, permitted_cap)`.
   - If `launch_mode = false`, `target_leverage = base_leverage + (permitted_cap - base_leverage) * max((healthy_score - 0.60) / 0.40, 0.0)`.
4. Compute compression:
   - `compression = min(1.0, max(0.0, (risk_score - 0.15) / 0.75))`
5. Publish:
   - `effective_max_leverage = max(1.0, target_leverage - (target_leverage - 1.0) * compression)`
   - `effective_min_leverage = 1.0`
   - `effective_leverage_band = [effective_min_leverage, effective_max_leverage]`

## Hard Bounds

- The engine must never publish below `1.0x`.
- The engine must never publish above `permitted_cap`.
- During launch mode the published band is always within `1.0x-2.0x`.
- If `risk_score >= 0.90`, the engine should be treated as severe stress and operational policy may pair this with tighter position-size caps and spread widening.

## Recalculation Cadence

Recalculate on the first matching event:

1. Every 5 seconds on the instrument risk loop.
2. Immediately when any normalized input changes by `>= 0.05`.
3. Immediately when `risk_score` crosses one of `0.30`, `0.55`, or `0.75`.
4. Immediately when `launch_mode`, `governance_max_leverage`, or `base_leverage` changes.

## Publishing Behavior

Publish one immutable snapshot per recomputation:

```json
{
  "instrument_id": "sfx_ngn_perp",
  "timestamp_utc": "2026-03-16T21:40:00Z",
  "base_leverage": 2.0,
  "permitted_cap": 2.0,
  "realized_volatility": 0.18,
  "vault_imbalance": 0.10,
  "depth_score": 0.92,
  "stress_velocity": 0.12,
  "risk_score": 0.128,
  "healthy_score": 0.88,
  "effective_leverage_band": [1.0, 2.0]
}
```

The publication stream should feed the transparency layer so the market can see the current leverage band, the governing cap in force, and the normalized state metrics behind the band.

## Worked Examples

| Scenario | Inputs | Published Band | Interpretation |
| --- | --- | --- | --- |
| Calm launch | `rv=0.18`, `imb=0.10`, `depth=0.92`, `stress=0.12`, `launch_mode=true` | `1.00x-2.00x` | Launch posture remains intact under healthy conditions. |
| Thin liquidity | `rv=0.42`, `imb=0.35`, `depth=0.25`, `stress=0.48`, `launch_mode=true` | `1.00x-1.56x` | Shallow depth and rising stress compress leverage without discretionary action. |
| Severe stress | `rv=0.88`, `imb=0.82`, `depth=0.10`, `stress=0.91`, `launch_mode=true` | `1.00x-1.03x` | The band approaches 1x when all risk inputs deteriorate together. |
| Post-launch healthy market | `rv=0.14`, `imb=0.08`, `depth=0.95`, `stress=0.10`, `launch_mode=false`, `governance_max=5.0` | `1.00x-4.32x` | Expansion is only available after launch mode is disabled and health is strong. |

## Assumptions

- A3 and B2 provide normalized metrics per instrument, not raw rates.
- C1 supplies absolute vault imbalance pressure rather than directional imbalance.
- The engine is deterministic and does not include manual overrides outside governance parameter changes.
