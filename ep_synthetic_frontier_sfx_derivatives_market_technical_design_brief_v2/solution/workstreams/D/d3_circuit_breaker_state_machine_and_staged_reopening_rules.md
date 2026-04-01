# D3 Circuit Breaker State Machine And Staged Reopening Rules

## Purpose

Define the deterministic per-instrument halt lifecycle used when index anchoring, source health, or executable liquidity deteriorate beyond safe operating limits.

## Design Principles

- Circuit logic is per instrument. A halt in one market does not freeze unrelated instruments.
- Trigger classes are objective and machine-evaluated. No operator may halt or reopen a market outside the predefined emergency path.
- Reopening is staged. Each stage restores a limited subset of functionality only after explicit recovery checks pass.
- A market must fail closed. Missing health inputs, ambiguous state, or stale recovery data keep the instrument halted.
- All state changes are emitted to the transparency layer and operator console with trigger reason, timestamp, and next eligible transition time.

## Integration Contract

This design consumes the following upstream signals:

- `index_divergence_bps`: absolute divergence between executable mid price and the approved macro-volatility index anchor.
- `source_health_score`: normalized oracle stability score from A4.
- `source_quorum_met`: boolean indicating the minimum number of healthy sources are contributing.
- `depth_within_band_ratio`: ratio of live executable depth within the allowed spread band versus configured minimum depth.
- `order_book_thinning_rate`: velocity of depth deterioration from B2 and D1.
- `stress_level`: `normal`, `warning`, `elevated`, or `emergency` from D1.
- `response_lock_active`: indicates D2 has an active stress-response package still inside cooldown.

If any required signal is unavailable for longer than the data grace window, the circuit breaker treats that condition as `source_instability`.

## Halt Trigger Model

An instrument enters a halt path when any of the following trigger families is satisfied:

| Trigger family | Required condition | Notes |
|---|---|---|
| Index divergence breach | `index_divergence_bps >= halt_trigger.index_divergence_bps` for `N` consecutive evaluation windows | Prevents trading when market price loses credible anchor reference |
| Source instability | `source_quorum_met = false` or `source_health_score < halt_trigger.source_health_floor` or source stale age exceeds grace window | Covers oracle outages, conflicting feeds, and stale index computation |
| Depth collapse | `depth_within_band_ratio < halt_trigger.depth_floor_ratio` and `order_book_thinning_rate >= halt_trigger.depth_collapse_velocity` | Prevents trading into a non-executable book |
| Compound emergency | `stress_level = emergency` and at least one trigger family above is already degraded | Escalates aggressively during cascading market stress |

### Trigger Severity

- `warning`: below halt threshold, no state transition; emit status only.
- `elevated`: pre-halt watch state; tighten D2 controls and start cooldown timers.
- `halt`: hard transition into `HALTED`.
- `lockdown`: hard transition into `HALTED_LOCKDOWN`, requiring longer cooldown and stricter reopening checks.

`HALTED_LOCKDOWN` is used when either:

- two trigger families breach halt conditions simultaneously, or
- a single trigger family remains in breach for longer than the maximum tolerated breach duration, or
- a market re-halts during staged reopening.

## State Machine

### States

| State | Trading status | Meaning |
|---|---|---|
| `ACTIVE` | Full trading allowed | Normal operation |
| `ELEVATED_WATCH` | Trading allowed with D2 stress controls | Degradation detected but halt conditions not yet met |
| `HALTED` | Matching disabled, cancels allowed | Standard protection halt |
| `HALTED_LOCKDOWN` | Matching disabled, cancels allowed, stricter reopen gate | Severe or repeated halt |
| `REOPEN_STAGE_1` | Cancel/replace and passive quoting only | Book rebuild without aggressive taker flow |
| `REOPEN_STAGE_2` | Limited matching, reduced leverage and size caps | Controlled liquidity restoration |
| `ACTIVE_POST_RECOVERY` | Full trading restored with temporary post-recovery guardrails | Recovery observation window before returning to `ACTIVE` |

### Allowed Transitions

| From | To | Condition |
|---|---|---|
| `ACTIVE` | `ELEVATED_WATCH` | Any trigger family reaches elevated severity |
| `ELEVATED_WATCH` | `ACTIVE` | All trigger families return to normal for watch reset window |
| `ELEVATED_WATCH` | `HALTED` | Any halt trigger breach persists through debounce window |
| `ACTIVE` | `HALTED` | Immediate hard halt for source quorum loss or extreme divergence |
| `HALTED` | `HALTED_LOCKDOWN` | Breach persists beyond halt cooldown or additional trigger family fires |
| `HALTED` | `REOPEN_STAGE_1` | Cooldown window elapsed and all stage-1 recovery checks pass |
| `HALTED_LOCKDOWN` | `REOPEN_STAGE_1` | Extended cooldown window elapsed and lockdown recovery checks pass |
| `REOPEN_STAGE_1` | `REOPEN_STAGE_2` | Stage-1 minimum duration elapsed and stage-2 recovery checks pass |
| `REOPEN_STAGE_1` | `HALTED_LOCKDOWN` | Any original halt trigger reappears |
| `REOPEN_STAGE_2` | `ACTIVE_POST_RECOVERY` | Stage-2 duration elapsed and post-recovery checks pass |
| `REOPEN_STAGE_2` | `HALTED_LOCKDOWN` | Any original halt trigger reappears or response lock reactivates |
| `ACTIVE_POST_RECOVERY` | `ACTIVE` | Observation window completes with stable metrics |
| `ACTIVE_POST_RECOVERY` | `HALTED_LOCKDOWN` | Any halt trigger reappears during observation |

No other transitions are valid. Manual jumps between states are rejected.

## Cooldown Windows

| State entered | Cooldown window |
|---|---|
| `HALTED` | Minimum fixed cooldown before any reopen attempt |
| `HALTED_LOCKDOWN` | Extended cooldown, at least 2x standard halt cooldown |
| `REOPEN_STAGE_1` | Minimum dwell time before stage-2 evaluation |
| `REOPEN_STAGE_2` | Minimum dwell time before active-post-recovery evaluation |
| `ACTIVE_POST_RECOVERY` | Observation window with temporary conservative controls |

Cooldown timers reset whenever a new halt trigger fires.

## Recovery Requirements

Reopening is blocked until all relevant recovery conditions evaluate true.

### depth_recovery_requirement

- Aggregate executable depth inside the configured spread band must recover above `reopen_stage.depth_min_ratio`.
- Depth must remain above threshold for the full recovery stability window, not just a single sample.
- Depth recovery must be distributed across both sides of the book; one-sided depth does not qualify.
- `order_book_thinning_rate` must return below the degradation floor before stage advancement.

### source_stability_requirement

- `source_quorum_met = true` for the full recovery stability window.
- `source_health_score` must recover above the reopen floor with no stale source events.
- Index publications must resume at expected cadence with monotonic timestamps.
- Cross-source dispersion must return inside the permitted reconciliation band.

### divergence_recovery_requirement

- `index_divergence_bps` must remain below the reopen threshold for the entire recovery stability window.
- The reopen threshold is stricter than the halt threshold to avoid immediate oscillation.

## Staged Reopening Rules

### REOPEN_STAGE_1

Purpose: rebuild displayed depth and confirm source stability before meaningful matching resumes.

Allowed actions:

- Cancel resting orders
- Replace existing quotes inside the permitted spread band
- Submit new passive-only orders

Blocked actions:

- Market orders
- Aggressive IOC/FOK orders
- Liquidation auctions except predefined safety liquidations
- Leverage increases

Controls:

- Reduced maximum order size
- Tight per-account message rate cap to prevent quote stuffing
- Mandatory passive price protection collar

Advance to `REOPEN_STAGE_2` only if depth and source stability requirements remain satisfied throughout the stage dwell window.

### REOPEN_STAGE_2

Purpose: restore limited matching while keeping exposures compressed.

Allowed actions:

- Passive and capped-aggression limit orders
- Matching inside reduced size caps
- Controlled liquidations through predefined safety flow

Blocked or constrained actions:

- No maximum leverage restoration yet
- No uncapped taker flow
- No governance-initiated parameter loosening outside the published recovery matrix

Controls:

- Lower leverage band than pre-halt state
- Reduced position size caps
- Spread floor remains widened
- Funding multipliers stay on stressed settings until active recovery completes

Advance to `ACTIVE_POST_RECOVERY` only if no trigger family reactivates and observation metrics remain stable for the full stage window.

### ACTIVE_POST_RECOVERY

Purpose: restore normal trading while keeping a short memory of the incident.

Controls still active:

- Conservative leverage cap
- Wider spread floor than baseline
- Lower open-interest cap if D2 response lock remains cooling down

Exit to `ACTIVE` only after the post-recovery observation window completes with:

- no divergence breach,
- no source instability event,
- no depth collapse relapse,
- and no renewed emergency stress classification.

## Operator-Visible Status Model

Every instrument publishes the following status object:

| Field | Description |
|---|---|
| `halt_state` | Current circuit breaker state |
| `halt_trigger` | Primary trigger family that caused the current or most recent halt |
| `halt_trigger_set` | All trigger families active at transition time |
| `cooldown_window` | Remaining time until the next transition may be evaluated |
| `reopen_stage` | `none`, `stage_1`, `stage_2`, or `post_recovery` |
| `depth_recovery_requirement` | Pass/fail plus current depth ratio versus threshold |
| `source_stability_requirement` | Pass/fail plus quorum and health details |
| `divergence_recovery_requirement` | Pass/fail plus current divergence versus threshold |
| `next_eligible_transition` | Earliest timestamp for reevaluation |
| `manual_override_status` | `not_available`, `emergency_only_pending`, or `emergency_only_executed` |
| `incident_id` | Correlates the halt cycle with D1/D2 audit and transparency records |

## Emergency Logic And Manual Intervention Constraint

Discretionary manual intervention is prohibited for normal halt and reopen flow.

The only manual path is a predefined emergency override with all of the following constraints:

- It may move a market only from `HALTED` to `HALTED_LOCKDOWN`, never directly to a reopening or active state.
- It requires a declared emergency reason code.
- It emits an immutable audit event with actor, timestamp, affected instrument, and reason.
- It cannot relax any threshold, cooldown, or recovery requirement during the incident.
- A manual override cannot reopen a market; reopening always returns to automated staged rules.

This preserves operator ability to harden protections without enabling discretionary market restarts.

## Failure Handling

- If status evaluation fails, the instrument remains in its current halted state or escalates to `HALTED_LOCKDOWN`.
- If recovery inputs conflict, the stricter result wins.
- If the market re-halts twice within the incident observation horizon, force `HALTED_LOCKDOWN` and require the extended cooldown path.

## Verification Mapping

- Index divergence, source instability, and order-book depth collapse are explicit trigger families in the halt model.
- Reopening uses fixed stages with cooldowns, dwell windows, and explicit recovery requirements.
- Manual intervention is limited to emergency lockdown escalation and cannot bypass automated reopening rules.
