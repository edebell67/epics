# Vault Accounting and Exposure Cap Model

## 1. Scope

This document defines the vault accounting model for the Synthetic Frontier sFX derivatives venue. It specifies:

- per-instrument vault isolation,
- canonical vault state and ledger events,
- exposure-cap formulas and enforcement thresholds,
- fee, funding, and liquidation accounting treatment,
- transparency outputs required for public publication.

This is the canonical Workstream C1 artifact for the MVP technical design.

## 2. Dependency Assumptions

The source task depends on `B1` instrument configuration and `B2` market-state outputs. Those artifacts were not available at execution time, so the following interfaces are assumed from the epic:

- each listed instrument has its own isolated vault and margin pool,
- market state provides open interest, long-short imbalance, volatility state, depth state, and stress state,
- funding is computed separately and posted into vault accounting as periodic settlements,
- liquidation logic can route residual exposure to the vault when no market counterparty is available.

These assumptions must be reconciled against finalized B1/B2 outputs once they exist.

## 3. Instrument Isolation Rules

### 3.1 Core Rule

Each instrument has a dedicated vault. Vault assets, liabilities, fees, funding transfers, and liquidation outcomes are never netted across instruments.

### 3.2 Instrument Isolation Guarantees

- losses on `vault_id = NGN_VOL_PERP` cannot consume capital assigned to `KES_VOL_PERP`,
- each instrument has its own exposure cap and stress thresholds,
- governance may rebalance capital between vaults only through an explicit deposit or withdrawal event,
- no trader receives cross-margin credit across instruments in MVP.

### 3.3 Consequence

Instrument isolation is the primary anti-contagion control. A single macro shock can force one market into protective mode without mechanically impairing every other market.

## 4. Canonical Vault State

The vault state is maintained per `(vault_id, instrument_id)` pair.

| Field | Type | Description |
|---|---|---|
| `vault_id` | string | Unique identifier for the isolated instrument vault |
| `instrument_id` | string | Perpetual instrument key |
| `vault_capital` | decimal | Current net capital available to absorb imbalance and liquidation residuals |
| `reserved_buffer` | decimal | Capital ring-fenced for worst-case liquidation slippage and fees payable |
| `free_capital` | decimal | `vault_capital - reserved_buffer` |
| `gross_long_notional` | decimal | Aggregate long open interest notional |
| `gross_short_notional` | decimal | Aggregate short open interest notional |
| `net_exposure` | decimal | `gross_long_notional - gross_short_notional` from the vault perspective |
| `absolute_net_exposure` | decimal | `abs(net_exposure)` |
| `exposure_cap` | decimal | Maximum permitted absolute vault exposure |
| `exposure_utilization` | decimal | `absolute_net_exposure / exposure_cap` |
| `fee_accrual` | decimal | Unsettled trading and penalty fees accrued to the vault |
| `funding_pnl` | decimal | Net funding received minus paid by the vault |
| `liquidation_pnl` | decimal | Net PnL impact of liquidation backstop activity |
| `stress_state` | enum | `normal`, `tightened`, `restricted`, `backstop_only`, `halted` |
| `publication_timestamp` | timestamp | Last published transparency snapshot time |

## 5. Vault Ledger Event Model

The vault is event-sourced. Each state change appends a ledger event and updates the aggregate vault state.

### 5.1 Ledger Event Types

| Event Type | Effect on Vault |
|---|---|
| `capital_deposit` | increases `vault_capital` |
| `capital_withdrawal` | decreases `vault_capital` |
| `trade_fee_credit` | increases `fee_accrual` and `vault_capital` when settled |
| `funding_receive` | increases `funding_pnl` and `vault_capital` |
| `funding_pay` | decreases `funding_pnl` and `vault_capital` |
| `liquidation_penalty_credit` | increases `fee_accrual` and `vault_capital` |
| `liquidation_loss` | decreases `liquidation_pnl` and `vault_capital` |
| `liquidation_gain` | increases `liquidation_pnl` and `vault_capital` |
| `inventory_transfer_to_vault` | increases `net_exposure` magnitude when the vault absorbs residual exposure |
| `inventory_transfer_from_vault` | decreases `net_exposure` magnitude when the vault unwinds exposure |
| `buffer_reserve_update` | adjusts `reserved_buffer` without changing gross capital |

### 5.2 Minimal Ledger Record

Each ledger row should carry:

- `event_id`
- `vault_id`
- `instrument_id`
- `event_type`
- `event_timestamp`
- `quantity`
- `notional`
- `cash_delta`
- `exposure_delta`
- `reference_price`
- `source_reference`
- `post_event_vault_capital`
- `post_event_net_exposure`
- `post_event_exposure_utilization`

## 6. Accounting Treatment

### 6.1 Vault Capital Equation

At any time:

`vault_capital = initial_capital + realized_fee_income + realized_funding_pnl + realized_liquidation_pnl + governance_capital_flows`

Where:

- `realized_fee_income` includes trading fees and liquidation penalties that are explicitly assigned to the vault,
- `realized_funding_pnl` reflects the vault's net role in periodic funding settlement,
- `realized_liquidation_pnl` captures gains or losses from backstop intervention and unwind execution.

### 6.2 Free Capital

`free_capital = vault_capital - reserved_buffer`

`reserved_buffer` must cover:

- projected close-out slippage on current vault inventory,
- pending funding payable,
- queued liquidation obligations,
- a governance-defined safety margin.

### 6.3 Net Exposure Sign Convention

- positive `net_exposure` means the vault is net long the instrument,
- negative `net_exposure` means the vault is net short the instrument,
- `absolute_net_exposure` is used for cap enforcement.

## 7. Exposure Cap Framework

### 7.1 Objective

The exposure cap limits how much directional inventory the vault may warehouse while acting as imbalance absorber or liquidation counterparty.

### 7.2 Base Exposure Cap

For instrument `i`:

`base_exposure_cap_i = vault_capital_i * max_inventory_multiple_i`

Where `max_inventory_multiple_i` is governance-set and conservative for MVP. A phase-1 default should favor low leverage and low inventory warehousing.

### 7.3 Stress-Adjusted Exposure Cap

The live cap is reduced as stress rises:

`exposure_cap_i = base_exposure_cap_i * depth_factor_i * volatility_factor_i * stress_factor_i`

With bounded factors:

- `depth_factor_i` in `(0, 1]`, lower when order-book depth thins,
- `volatility_factor_i` in `(0, 1]`, lower when realized or implied volatility rises,
- `stress_factor_i` in `(0, 1]`, lower during rapid imbalance acceleration or liquidation clustering.

This means cap never widens during stress. It either stays constant or tightens.

### 7.4 Utilization Bands

`exposure_utilization = absolute_net_exposure / exposure_cap`

| Utilization Band | State | Required Action |
|---|---|---|
| `< 0.50` | normal | no vault restriction |
| `0.50 - 0.75` | tightened | funding multiplier bias and leverage caution |
| `0.75 - 0.90` | restricted | tighter leverage, wider spreads, position-cap tightening |
| `0.90 - 1.00` | backstop_only | vault may unwind or absorb liquidations only; discretionary imbalance warehousing disabled |
| `> 1.00` | halted | new exposure-increasing flow blocked until utilization falls below threshold |

## 8. Cap Enforcement Logic

### 8.1 New Trade Admission

Any new action that would increase `absolute_net_exposure` must be rejected or repriced when projected post-trade utilization breaches the active threshold.

### 8.2 Liquidation Exception

If the vault must absorb exposure during liquidation to avoid disorderly failure, it may temporarily exceed `exposure_cap`, but:

- the event is flagged as `forced_backstop`,
- the market moves immediately to `halted` or `backstop_only`,
- unwind priority becomes the top control objective,
- transparency output must disclose breach state and recovery progress.

### 8.3 Governance Buffer

A secondary capital-protection guardrail prevents withdrawals or cap expansions that would reduce:

`free_capital / absolute_net_exposure`

below a governance minimum. This avoids cosmetic cap settings on thin actual capital.

## 9. Fee, Funding, and Liquidation Participation

### 9.1 Trading Fees

The vault may receive a predefined share of trading fees as compensation for providing systemic backstop capacity.

### 9.2 Funding Participation

The vault participates in funding only when it holds residual inventory. Funding cashflows must map to actual directional exposure:

- net-long vault inventory receives funding when longs are entitled to receive,
- net-short vault inventory pays or receives according to the opposite side of the funding rule.

Funding should never be booked to the vault when inventory is flat.

### 9.3 Liquidation Counterparty Behavior

The vault acts as buyer or seller of last resort only when:

- no market participant fills the liquidation order in time,
- price impact would exceed allowed slippage bands,
- the liquidation engine explicitly routes residual inventory to the vault.

All such events are recorded with:

- pre-event exposure,
- post-event exposure,
- close-out reference price,
- realized slippage,
- resulting stress-state transition.

## 10. Control State Outputs

The vault model feeds downstream controls:

| Output | Consumer |
|---|---|
| `exposure_utilization` | leverage engine |
| `stress_state` | spread elasticity logic |
| `free_capital` | governance and withdrawal controls |
| `absolute_net_exposure` | liquidation and risk dashboards |
| `forced_backstop_flag` | market halt and disclosure logic |

## 11. Transparency Output Contract

The transparency output is published per instrument snapshot.

### 11.1 Required Transparency Output

| Field | Description |
|---|---|
| `instrument_id` | instrument being reported |
| `vault_capital` | current vault capital |
| `free_capital` | capital remaining after reserves |
| `net_exposure` | signed inventory exposure |
| `absolute_net_exposure` | absolute inventory exposure |
| `exposure_cap` | current live exposure cap |
| `exposure_utilization` | cap utilization ratio |
| `gross_long_notional` | total long open interest |
| `gross_short_notional` | total short open interest |
| `fee_accrual` | cumulative fee accrual |
| `funding_pnl` | cumulative funding PnL |
| `liquidation_pnl` | cumulative liquidation PnL |
| `stress_state` | current risk-control state |
| `last_material_event` | most recent cap or backstop event |
| `publication_timestamp` | snapshot timestamp |

### 11.2 Transparency Output Example

```json
{
  "instrument_id": "NGN_VOL_PERP",
  "vault_capital": 1200000.0,
  "free_capital": 1035000.0,
  "net_exposure": -285000.0,
  "absolute_net_exposure": 285000.0,
  "exposure_cap": 400000.0,
  "exposure_utilization": 0.7125,
  "gross_long_notional": 2410000.0,
  "gross_short_notional": 2695000.0,
  "fee_accrual": 18400.0,
  "funding_pnl": 9200.0,
  "liquidation_pnl": -12750.0,
  "stress_state": "tightened",
  "last_material_event": "inventory_transfer_to_vault",
  "publication_timestamp": "2026-03-16T22:45:00Z"
}
```

## 12. Worked Stress Scenarios

### 12.1 Imbalance Absorption Stress Scenario

- long-side order flow dominates and market makers fade,
- vault absorbs short inventory to keep liquidation flow orderly,
- `absolute_net_exposure` rises from 42% to 78% utilization,
- system moves from `normal` to `restricted`,
- leverage tightens and spreads widen automatically.

### 12.2 Liquidation Cascade Stress Scenario

- clustered forced liquidations hit during macro shock,
- public liquidity is insufficient at permitted slippage,
- vault takes residual inventory and temporarily breaches cap,
- market enters `halted`,
- unwind logic prioritizes reducing vault inventory before reopening.

### 12.3 Capital Preservation Stress Scenario

- liquidation losses and funding outflows reduce `vault_capital`,
- `exposure_cap` shrinks mechanically because it is capital-linked,
- new exposure-increasing flow is blocked earlier,
- transparency output shows falling capital and rising utilization in real time.

## 13. Acceptance Mapping

This design satisfies the task objectives as follows:

- instrument isolation is explicit and prevents cross-margin contagion by design,
- exposure cap logic covers imbalance absorption, liquidation counterparty behavior, and backstop breach handling,
- transparency output defines the public publication layer for vault capital and exposure state.

## 14. Follow-On Interfaces

Downstream tasks should consume this artifact as input for:

- dynamic leverage band design,
- spread elasticity rules,
- liquidation workflow and vault intervention,
- public transparency data contracts,
- phase-1 instrument cap configuration.
