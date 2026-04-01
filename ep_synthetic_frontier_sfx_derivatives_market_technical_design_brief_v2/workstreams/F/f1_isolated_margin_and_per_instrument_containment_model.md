# F1 Isolated Margin And Per-Instrument Containment Model

## Objective
Define the launch-time containment rules that keep each synthetic macro perpetual in its own collateral, vault, and failure domain while documenting the shared services that remain systemic dependencies.

## Scope
- Phase-1 instruments: `NGN_VOL`, `KES_VOL`, `GHS_VOL`, `ZAR_VOL`
- Margin asset: `USDC`
- Market structure: order-book perpetuals with no redeemable spot balances
- Launch posture: low leverage, conservative exposure caps, isolated vault participation

## Core Containment Principles
1. Every open position is margined against a single `instrument_id`; collateral posted for one market is never available to satisfy maintenance or initial margin on another market.
2. Every listed instrument has a dedicated vault ledger and exposure cap, so vault PnL, fee accrual, liquidation losses, and funding participation are booked per instrument.
3. Losses stop at the instrument boundary before they reach unrelated markets; the system prefers halting or shrinking a single market over socializing losses across the venue.
4. Shared infrastructure may interrupt multiple markets operationally, but it must not merge their economic state.

## Isolation Domain Table
| instrument_id | margin_scope | vault_scope | loss_containment_boundary | shared_dependency_exception |
|---|---|---|---|---|
| `NGN_VOL` | Trader sub-ledger tagged `instrument_id=NGN_VOL`; collateral locked to the NGN market only | Dedicated `vault_ngn_vol` ledger with its own capital, exposure cap, fee accrual, funding PnL, and liquidation PnL | NGN liquidations, vault drawdowns, and cap breaches can only deplete `vault_ngn_vol` and NGN trader balances; the response is leverage compression, tighter caps, or halt on NGN only | Oracle/index publication, sequencer/matching engine availability, governance pause authority, and USDC settlement rail remain shared |
| `KES_VOL` | Trader sub-ledger tagged `instrument_id=KES_VOL`; no collateral reuse into NGN, GHS, or ZAR | Dedicated `vault_kes_vol` ledger with isolated capital accounting and backstop limits | KES losses are absorbed by KES positions and `vault_kes_vol`; deficits trigger KES-only restriction states before any venue-wide emergency action | Oracle/index publication, sequencer/matching engine availability, governance pause authority, and USDC settlement rail remain shared |
| `GHS_VOL` | Trader sub-ledger tagged `instrument_id=GHS_VOL`; margin transfers require closing or reducing GHS risk first | Dedicated `vault_ghs_vol` ledger with isolated fee, funding, and liquidation accounting | GHS stress events can shut GHS quoting, liquidations, and new order entry without touching unrelated vault balances | Oracle/index publication, sequencer/matching engine availability, governance pause authority, and USDC settlement rail remain shared |
| `ZAR_VOL` | Trader sub-ledger tagged `instrument_id=ZAR_VOL`; no portfolio cross-netting at launch | Dedicated `vault_zar_vol` ledger with independent exposure cap and capital utilization tracking | ZAR mark loss, liquidation deficit, or imbalance expansion remains inside the ZAR ledger and invokes ZAR-local controls first | Oracle/index publication, sequencer/matching engine availability, governance pause authority, and USDC settlement rail remain shared |

## Economic State Model

### Margin Scope
- `margin_scope` is defined as the tuple `(account_id, instrument_id, collateral_asset=USDC)`.
- Initial margin, maintenance margin, unrealized PnL, and liquidation checks are computed only against positions with the same `instrument_id`.
- A trader may hold multiple instrument positions, but each position behaves like a separate account silo.
- Cross-instrument PnL offsets are disabled at launch; profits on one market cannot cure margin deficiency on another until realized and explicitly withdrawn or reallocated through a new deposit flow.

### Vault Scope
- Each market uses one vault identifier and one capital pool per instrument.
- Vault accounting is isolated across:
  - fee accrual
  - funding participation
  - liquidation inventory
  - realized backstop gains/losses
  - exposure cap consumption
- Exposure caps are enforced per vault, not globally, so a stressed market cannot silently consume idle capital from another market's reserve.

### Loss Containment Boundary
- The containment boundary sits at the instrument ledger pair:
  - trader margin sub-ledgers for `instrument_id`
  - dedicated backstop vault ledger for `instrument_id`
- If mark losses exceed trader margin and liquidation recovery:
  - the deficit is absorbed only by the matching instrument vault up to its configured cap
  - the market then escalates through local protections: leverage compression, wider spreads, position-cap tightening, open-interest clamp, and finally trading halt
- No insurance sweep, auto-borrow, or socialized loss transfer from other instrument vaults is allowed in phase 1.

## Shared Services Outside The Containment Boundary
These components can create correlated downtime or governance impact, but they must not move economic losses between markets.

| shared_service | why_shared | containment requirement |
|---|---|---|
| Index/oracle publication stack | Market controls and liquidation references depend on common data pipelines | A bad feed can halt multiple markets, but each market still settles against its own margin and vault ledgers only |
| Sequencer, matching engine, and API gateway | Operational simplicity at launch | Outages may pause order flow venue-wide, but balances and exposure caps remain segregated by `instrument_id` |
| Governance controls | Parameter updates and emergency pauses are centrally authorized | Governance may pause or de-list a market, but it cannot reassign one vault's capital to another outside a predeclared migration process |
| USDC custody/settlement rail | All markets settle in the same stablecoin | Custody failure is systemic operational risk; internal accounting must still preserve per-instrument claim boundaries for recovery |
| Transparency publication layer | Public reporting aggregates venue state | Published venue summaries must be derived from instrument-level ledgers, never from pooled hidden accounting |

## Failure Containment Scenarios

### Scenario 1: Single-Market Liquidation Cascade
- Trigger: `NGN_VOL` gaps 35% and clustered liquidations exhaust several trader margin accounts.
- Expected containment:
  - Only `NGN_VOL` traders are liquidated against the NGN liquidation reference.
  - Residual loss is booked to `vault_ngn_vol` only.
  - `KES_VOL`, `GHS_VOL`, and `ZAR_VOL` vault balances, margin ratios, and open positions remain unchanged.
  - The response stack escalates on `NGN_VOL` only unless a shared dependency also fails.

### Scenario 2: Vault Deficit Reaches Exposure Cap
- Trigger: `GHS_VOL` imbalance forces the GHS vault to absorb inventory until `exposure_cap` is reached.
- Expected containment:
  - New GHS position growth is blocked or sharply reduced.
  - GHS leverage band compresses and spread floor widens.
  - No capital is drawn from `vault_ngn_vol`, `vault_kes_vol`, or `vault_zar_vol`.
  - Venue stays live for unaffected markets unless governance invokes a broader emergency state for operational reasons.

### Scenario 3: Shared Oracle Instability
- Trigger: offshore and proxy inputs degrade across multiple markets.
- Expected containment:
  - One or more markets may halt because liquidation references are unreliable.
  - Economic isolation still holds because no vault merging or cross-margin netting is introduced during the halt.
  - Restart decisions are made per instrument once source stability and depth criteria recover.

## Launch-Time Control Rules
- No portfolio margin.
- No cross-collateralization.
- No inter-vault borrowing.
- No socialized loss waterfall across instruments.
- No hidden venue-level reserve that can backfill a market without explicit governance disclosure.
- Any future move toward shared insurance or portfolio margin requires a separate governance artifact and migration plan because it changes the containment model materially.

## Transparency Outputs Required
- `instrument_id`
- `margin_scope`
- `vault_scope`
- `loss_containment_boundary`
- `shared_dependency_exception`
- `exposure_cap_state`
- `market_status`

These fields allow the transparency layer and launch pack to prove that isolation is an explicit operating rule rather than an informal assumption.

## Acceptance Summary
- Cross-instrument margining is disallowed by construction at launch.
- Vault accounting, exposure caps, funding PnL, and liquidation PnL are instrument-local.
- Loss escalation ends in instrument-local restrictions or halt before any cross-market capital transfer.
- Shared services that still create systemic risk are listed explicitly so downstream launch and simulation tasks can test them.
