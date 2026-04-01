# Liquidation Workflow and Vault Backstop Specification

## 1. Objective

This document defines a non-discretionary liquidation workflow for sFX perpetual instruments. It specifies how maintenance margin failures are detected, how partial and full liquidations are sequenced, when the DAO vault becomes the residual counterparty, how penalties are allocated, and how residual losses are absorbed during stress.

The design implements the epic constraint that the index is never used to set executable trade price. The order book remains the only executable price source. The index is used only as a liquidation reference, a funding anchor, and a circuit-breaker anchor.

## 2. Deterministic Inputs

Each instrument must expose the following fields:

| Field | Meaning | Deterministic rule |
| --- | --- | --- |
| `maintenance_margin` | Minimum required equity ratio after mark-to-market and accrued funding | Fixed by instrument risk config and recomputed every risk tick |
| `liquidation_reference_price` | Index-derived fair reference used only to evaluate liquidation eligibility | Derived from the instrument index, not the order book |
| `partial_liquidation_step` | Fraction of position size reduced per liquidation tranche | Configured per instrument, default 25% of current position notional |
| `penalty_rate` | Liquidation fee charged on notional closed through forced reduction | Split deterministically between vault reserve and insurance buffer |
| `vault_takeover_condition` | Rule for transferring residual risk to the vault | Triggered automatically when forced order flow cannot restore maintenance margin within allowed tranches |
| `residual_loss_handling` | Loss waterfall after account equity is exhausted | Account equity, liquidation penalty reserve, insurance buffer, vault capital, then socialized loss if governance enables it |

## 3. Liquidation Trigger Logic

### 3.1 Reference values

- `account_equity = collateral + realized_pnl + unrealized_pnl - accrued_fees - accrued_funding`
- `maintenance_requirement = abs(position_notional) * maintenance_margin`
- `liquidation_buffer = account_equity - maintenance_requirement`
- `liquidation_reference_price` is sourced from the instrument index with smoothing rules inherited from the macro volatility index stack.

### 3.2 Trigger condition

A position enters liquidation monitoring when both conditions hold:

1. `account_equity <= maintenance_requirement`
2. The breach persists for `risk_confirmation_ticks` consecutive risk cycles to avoid one-tick noise

The trigger uses the index-derived `liquidation_reference_price` to determine whether the account is below maintenance. The order book is then used to execute the response. This preserves the epic rule that the index is a liquidation reference only.

### 3.3 Side-specific breach evaluation

- Long positions breach when the liquidation reference implies mark-to-market loss large enough to push equity below maintenance.
- Short positions breach when the liquidation reference implies adverse upward movement large enough to push equity below maintenance.

## 4. Liquidation State Machine

| State | Entry condition | Exit condition | Deterministic action |
| --- | --- | --- | --- |
| `healthy` | Equity above maintenance | Breach detected | No forced action |
| `warning` | First confirmed maintenance breach | Equity restored or breach escalates | Freeze new risk-increasing orders; allow reduce-only actions |
| `partial_liquidation` | Warning persists and position size exceeds minimum forced-reduction size | Margin restored or tranches exhausted | Submit reduce-only forced orders in configured tranches |
| `vault_takeover_pending` | Forced reduction cannot restore maintenance or order book liquidity falls below execution floor | Transfer completed or market halted | Move remaining risk to vault under bounded takeover price logic |
| `full_liquidation` | Position is fully closed through market or vault transfer | Position size is zero | Close account exposure and settle penalties |
| `residual_loss_resolution` | Account equity remains negative after closeout | Loss waterfall completed | Apply deterministic residual-loss waterfall |
| `closed` | All accounting finished | None | Terminal state |

## 5. Forced Execution Sequence

### 5.1 Immediate controls

When a position enters `warning`:

- Reject all new orders that increase exposure.
- Cancel resting orders on the same side that would expand risk.
- Keep reduce-only orders live.
- Snapshot account equity, maintenance requirement, liquidation reference price, best bid, best ask, vault headroom, and stress state for audit.

### 5.2 Partial liquidation algorithm

Forced reduction runs in bounded tranches:

1. Compute `target_reduction = max(partial_liquidation_step * current_notional, minimum_forced_reduction_notional)`.
2. Submit an IOC reduce-only order against the order book using a bounded aggressiveness schedule.
3. Recompute account equity and maintenance requirement after each fill.
4. Stop forced selling or buying as soon as `account_equity > maintenance_requirement + recovery_buffer`.
5. If the tranche is unfilled or only partially filled, continue until `max_partial_liquidation_rounds` is reached.

Default bounded execution controls:

- `partial_liquidation_step`: 25% of current notional
- `max_partial_liquidation_rounds`: 3
- `recovery_buffer`: 10% of maintenance requirement
- `forced_order_price_band`: no wider than the active stress-adjusted spread protection band

This sequence avoids immediate all-or-nothing closeout when a smaller deterministic reduction can restore maintenance.

### 5.3 Escalation to full liquidation

Escalate from partial liquidation to full liquidation when any of the following is true:

- Remaining position notional falls below the instrument minimum tradable size while still under maintenance.
- `max_partial_liquidation_rounds` is exhausted without restoring maintenance.
- Order book depth inside the allowable forced-execution band cannot absorb the next tranche.
- Stress controls have placed the instrument into a state that forbids continued open-market liquidation and requires vault transfer.

## 6. Vault Backstop Intervention

### 6.1 Vault role

The vault acts as residual counterparty, not as a price-setting discretionary trader. Vault takeover is triggered automatically when the rules below are satisfied.

### 6.2 Vault takeover condition

Vault takeover is triggered automatically when all of the following hold:

1. The position is already in forced liquidation.
2. Open-market execution within the forced-order price band cannot restore maintenance.
3. The instrument-level vault exposure cap and market-wide vault concentration cap both have remaining headroom.
4. The market is not in a hard-stop circuit-breaker state that forbids new risk transfer.

If any required condition fails, the system skips vault takeover and proceeds directly to residual loss resolution after available market closeout.

### 6.3 Transfer mechanics

When takeover occurs:

- The remaining position is transferred to the vault at a deterministic `vault_transfer_price`.
- `vault_transfer_price` is the worse of:
  - the last executable forced-liquidation price inside the allowed band
  - the current liquidation reference price plus or minus the configured adverse-transfer buffer for the relevant side
- The transferred exposure is tagged with:
  - source account identifier
  - instrument identifier
  - takeover timestamp
  - inherited entry basis
  - stress regime label
- The vault must immediately subject inherited exposure to the same leverage, spread, and open-interest controls as external participants.

The vault never overrides pricing manually and cannot absorb exposure beyond configured caps.

## 7. Penalty Model and Post-Liquidation Accounting

### 7.1 Penalty assessment

Each forced-close tranche pays:

`liquidation_penalty = executed_notional * penalty_rate`

Default routing:

- 50% to the vault reserve as compensation for backstop service
- 50% to the insurance buffer for future bad-debt absorption

Penalty routing is deterministic and instrument-agnostic unless an instrument config explicitly overrides the split.

### 7.2 Account settlement order

After closeout:

1. Realize all remaining PnL from the forced execution or vault transfer.
2. Deduct liquidation penalties.
3. Release excess initial margin if any remains after maintenance and penalties.
4. Set remaining account collateral to zero if losses exceed available equity.

## 8. Residual Loss Handling

Residual loss exists when the account remains negative after all forced execution, vault transfer, and penalty application are complete.

The loss waterfall is:

1. Defaulting account collateral
2. Accrued liquidation penalties not yet routed
3. Insurance buffer allocated to the instrument
4. General vault capital within market-wide loss limits
5. Socialized loss across profitable open-interest cohorts only if governance pre-enables this path

Each stage is exhausted in order before the next stage is touched. No operator can skip stages or reorder the waterfall.

If governance does not enable socialized loss, the final stage becomes a market halt and recapitalization requirement.

## 9. Clustered Liquidation Safeguards

### Clustered Liquidation Safeguards

The design includes the following protections for correlated stress events:

- Liquidation queue ordering by breach severity and time priority to prevent arbitrary sequencing.
- Per-instrument `max_concurrent_liquidations` so the engine does not consume all visible depth in one burst.
- Dynamic reduction of `partial_liquidation_step` during high cluster density to reduce slippage spirals.
- Automatic spread-band tightening for forced execution when index divergence exceeds the circuit-breaker warning band.
- Immediate suspension of new leverage increases whenever clustered liquidation density crosses the stress threshold.
- Vault takeover throttling by remaining cap headroom so backstop capital cannot be exhausted by a single instrument.
- Escalation to circuit-breaker logic if liquidation queue growth, depth collapse, and index divergence all breach their stress bands together.

## 10. Deterministic Governance Boundaries

Governance may tune parameter bands only for future use. Governance may not:

- choose which account liquidates first outside the queue rules
- manually decide whether the vault absorbs a specific position
- manually waive or alter a liquidation penalty for a specific account
- bypass the residual-loss waterfall during an active event

Emergency powers may pause the market only through predefined circuit-breaker controls already disclosed to participants.

## 11. Required Audit Outputs

Every liquidation event must emit:

- account identifier
- instrument identifier
- state transition timestamps
- liquidation reference price at trigger
- forced execution prices and fills
- vault takeover decision and reason code
- penalty charged and routing split
- residual loss amount and waterfall stage consumption
- stress metrics active at the time of liquidation

## 12. Acceptance Mapping

| Task verification item | Specification coverage |
| --- | --- |
| Index used only as liquidation reference | Sections 1, 3, and 5 explicitly separate reference pricing from executable order-book pricing |
| Vault intervention and penalty handling deterministic | Sections 6 through 8 define rule-based takeover, transfer pricing, penalty routing, and residual-loss ordering |
| Safeguards for clustered liquidations | Section 9 defines queueing, throttles, tranche reduction, vault throttling, and escalation logic |
