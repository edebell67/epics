# B1 Perpetual Instrument and Market Configuration Model

## Objective
Define a complete per-market configuration contract for the MVP synthetic frontier perpetual venue. The model supports listing, execution, margining, liquidation reference selection, vault containment, funding linkage, and public transparency without introducing cross-margin or redeemable token balances.

## Design Principles
- Stablecoin margined and settled. All markets use USDC collateral for the MVP.
- Positions only. Users hold positions, not synthetic currency balances.
- Order-flow priced. The trade price comes from the CLOB, not a hard peg.
- Index referenced. The index anchors funding, liquidation, and circuit-breaker logic.
- Instrument isolation first. Margin, vault exposure, and failure containment are per instrument.
- Launch conservatively. Phase 1 listings default to low leverage and explicit position caps.

## Canonical Market Configuration
Each perpetual market is represented as one configuration object with the following top-level groups.

### 1. Instrument Identity
| Field | Type | Required | Description |
|---|---|---:|---|
| `instrument_id` | string | yes | Canonical venue identifier such as `SFX_NGN_PERP`. |
| `display_name` | string | yes | User-facing name. |
| `underlier_code` | string | yes | Macro underlier code such as `NGN`, `KES`, `GHS`, `ZAR`. |
| `contract_type` | enum | yes | Always `perpetual` for MVP. |
| `status` | enum | yes | `draft`, `prelaunch`, `active`, `reduce_only`, `halted`, `retired`. |
| `launch_phase` | enum | yes | `phase_1` or later. |

### 2. Collateral and Margin
| Field | Type | Required | Description |
|---|---|---:|---|
| `quote_collateral` | string | yes | Stablecoin settlement asset, `USDC` for MVP. |
| `settlement_currency` | string | yes | Currency used for PnL realization and fee settlement. |
| `isolated_margin` | boolean | yes | Must be `true` for MVP. |
| `cross_margin_enabled` | boolean | yes | Must be `false` for MVP. |
| `initial_leverage_min` | number | yes | Minimum listed leverage band, typically `1.0`. |
| `initial_leverage_max` | number | yes | Initial launch cap, typically `2.0`. |
| `governance_leverage_ceiling` | number | yes | Hard upper band governance may not exceed without a new listing action. |
| `maintenance_margin_ratio` | number | yes | Base maintenance requirement used by liquidation logic. |
| `margin_call_buffer_ratio` | number | yes | Early warning distance above maintenance. |

### 3. Pricing and Reference Inputs
| Field | Type | Required | Description |
|---|---|---:|---|
| `index_reference.index_id` | string | yes | Canonical macro-volatility index identifier. |
| `index_reference.publication_interval_seconds` | integer | yes | Expected cadence of fresh index values. |
| `index_reference.max_staleness_seconds` | integer | yes | Maximum allowed staleness before degraded mode or halt logic. |
| `index_reference.confidence_floor` | number | yes | Minimum health/confidence score accepted for normal operations. |
| `pricing_rules.trade_price_source` | enum | yes | Must be `order_book`. |
| `pricing_rules.mark_price_source` | enum | yes | `order_book_mid_with_guardrails` for MVP. |
| `pricing_rules.liquidation_reference_source` | enum | yes | Must be `index_reference`. |
| `pricing_rules.circuit_breaker_anchor` | enum | yes | Must be `index_reference`. |

### 4. Execution and Book Controls
| Field | Type | Required | Description |
|---|---|---:|---|
| `tick_size` | number | yes | Minimum price increment. |
| `lot_size` | number | yes | Minimum trade size increment. |
| `min_order_notional_usdc` | number | yes | Smallest accepted order notional. |
| `max_order_notional_usdc` | number | yes | Largest single order notional. |
| `position_size_cap` | number | yes | Per-account position cap in contract units. |
| `open_interest_cap_usdc` | number | yes | Instrument-level notional cap for launch containment. |
| `reduce_only_on_halt` | boolean | yes | Allows exits while preventing new exposure in halted states. |

### 5. Vault and Isolation Controls
| Field | Type | Required | Description |
|---|---|---:|---|
| `vault_id` | string | yes | Dedicated vault for the instrument. |
| `vault.exposure_cap_usdc` | number | yes | Maximum net exposure the vault may absorb. |
| `vault.fee_share_ratio` | number | yes | Portion of trading/funding fees allocated to the vault. |
| `vault.loss_containment_boundary` | string | yes | Human-readable isolation boundary, usually `instrument_only`. |
| `shared_dependencies` | array[string] | yes | Shared services still outside the isolated vault boundary. |

### 6. Funding Interface
| Field | Type | Required | Description |
|---|---|---:|---|
| `funding.enabled` | boolean | yes | Funding active for the instrument. |
| `funding.settlement_interval_seconds` | integer | yes | Settlement cadence consumed by B3. |
| `funding.base_multiplier` | number | yes | Per-market base sensitivity. |
| `funding.max_abs_rate_per_interval` | number | yes | Launch cap on funding transfer magnitude. |
| `funding.inputs` | array[string] | yes | Declares the market-state inputs B3 will consume. |

### 7. Transparency and Governance Outputs
| Field | Type | Required | Description |
|---|---|---:|---|
| `transparency_fields` | array[string] | yes | Public fields emitted for market status, caps, leverage band, funding, and vault state. |
| `governance_parameters` | array[string] | yes | Parameters governance may tune within approved bands. |
| `operator_notes` | string | no | Launch assumptions or temporary caveats. |

## Required Consumer Field Coverage

### Trading Engine
- `instrument_id`
- `status`
- `tick_size`
- `lot_size`
- `min_order_notional_usdc`
- `max_order_notional_usdc`
- `pricing_rules.trade_price_source`
- `reduce_only_on_halt`

### Risk Engine
- `isolated_margin`
- `cross_margin_enabled`
- `maintenance_margin_ratio`
- `margin_call_buffer_ratio`
- `initial_leverage_min`
- `initial_leverage_max`
- `governance_leverage_ceiling`
- `position_size_cap`
- `open_interest_cap_usdc`
- `vault_id`
- `vault.exposure_cap_usdc`
- `pricing_rules.liquidation_reference_source`
- `index_reference.max_staleness_seconds`

### Funding Engine
- `funding.enabled`
- `funding.settlement_interval_seconds`
- `funding.base_multiplier`
- `funding.max_abs_rate_per_interval`
- `funding.inputs`
- `pricing_rules.mark_price_source`
- `index_reference.index_id`

### Transparency Layer
- `instrument_id`
- `display_name`
- `status`
- `quote_collateral`
- `initial_leverage_min`
- `initial_leverage_max`
- `position_size_cap`
- `open_interest_cap_usdc`
- `vault_id`
- `transparency_fields`
- `governance_parameters`

## Operator Listing Rules
- Every listed market must be `perpetual`, `isolated_margin=true`, and `cross_margin_enabled=false`.
- Every listed market must bind exactly one dedicated `vault_id`.
- `trade_price_source` must remain `order_book`; the index cannot directly set trade price.
- `liquidation_reference_source` and `circuit_breaker_anchor` must both reference the index.
- Phase 1 leverage must remain within the epic's conservative launch posture, with launch defaults at `1.0x` to `2.0x`.
- Every instrument must expose transparency fields sufficient for public publication of leverage, funding, open interest, and market status.

## Phase 1 Listing Template Guidance
Use one listing object per market. The phase 1 pack should instantiate:
- `SFX_NGN_PERP`
- `SFX_KES_PERP`
- `SFX_GHS_PERP`
- `SFX_ZAR_PERP`

Shared launch defaults:
- `quote_collateral=USDC`
- `settlement_currency=USDC`
- `isolated_margin=true`
- `cross_margin_enabled=false`
- `contract_type=perpetual`
- `pricing_rules.trade_price_source=order_book`
- `pricing_rules.liquidation_reference_source=index_reference`
- `pricing_rules.circuit_breaker_anchor=index_reference`
- `funding.settlement_interval_seconds=28800`

## Example Market Object
```json
{
  "instrument_id": "SFX_NGN_PERP",
  "display_name": "Synthetic NGN Macro Volatility Perpetual",
  "underlier_code": "NGN",
  "contract_type": "perpetual",
  "status": "prelaunch",
  "launch_phase": "phase_1",
  "quote_collateral": "USDC",
  "settlement_currency": "USDC",
  "isolated_margin": true,
  "cross_margin_enabled": false,
  "initial_leverage_min": 1.0,
  "initial_leverage_max": 2.0,
  "governance_leverage_ceiling": 5.0,
  "maintenance_margin_ratio": 0.08,
  "margin_call_buffer_ratio": 0.03,
  "index_reference": {
    "index_id": "MVI_NGN",
    "publication_interval_seconds": 60,
    "max_staleness_seconds": 180,
    "confidence_floor": 0.75
  },
  "pricing_rules": {
    "trade_price_source": "order_book",
    "mark_price_source": "order_book_mid_with_guardrails",
    "liquidation_reference_source": "index_reference",
    "circuit_breaker_anchor": "index_reference"
  },
  "tick_size": 0.0001,
  "lot_size": 1,
  "min_order_notional_usdc": 25,
  "max_order_notional_usdc": 25000,
  "position_size_cap": 100000,
  "open_interest_cap_usdc": 250000,
  "reduce_only_on_halt": true,
  "vault_id": "VAULT_NGN_ISO",
  "vault": {
    "exposure_cap_usdc": 150000,
    "fee_share_ratio": 0.6,
    "loss_containment_boundary": "instrument_only"
  },
  "shared_dependencies": [
    "oracle_publication_service",
    "matching_engine_cluster",
    "transparency_feed"
  ],
  "funding": {
    "enabled": true,
    "settlement_interval_seconds": 28800,
    "base_multiplier": 1.0,
    "max_abs_rate_per_interval": 0.0075,
    "inputs": [
      "imbalance_pct",
      "volatility_metric",
      "open_interest_velocity"
    ]
  },
  "transparency_fields": [
    "market_status",
    "vault_capital",
    "long_short_imbalance",
    "open_interest",
    "current_leverage_band",
    "funding_rate",
    "volatility_metric",
    "risk_parameter_band"
  ],
  "governance_parameters": [
    "initial_leverage_max",
    "open_interest_cap_usdc",
    "vault.exposure_cap_usdc",
    "funding.base_multiplier"
  ],
  "operator_notes": "Phase 1 launch settings assume conservative exposure and low leverage."
}
```

## Assumptions and Follow-up Hooks
- `index_reference` field names are provisional until A1 and A3 publish their finalized schema and confidence outputs.
- `mark_price_source` is intentionally specified here so B3 can reuse a stable instrument-level field instead of inventing a new contract.
- `shared_dependencies` makes systemic exceptions explicit, which supports the later F1 containment model.
