# Workstream E Governance Parameter Band and Emergency Override Framework

## Objective
Define exactly what governance may change in production, the immutable bounds that keep the market inside the epic's safety envelope, and the small closed set of emergency actions that may be invoked without introducing discretionary market intervention.

## Design Principles
1. Governance can tune only predeclared parameters.
2. Every governed parameter has an immutable minimum, maximum, and named authority.
3. Routine changes are timelocked and publicly auditable before activation.
4. Emergency actions may only apply enumerated overrides tied to objective trigger conditions.
5. Emergency overrides are temporary, automatically expiring, and require retrospective ratification or rollback.
6. No override may create fiat exposure, cross-margin, unbounded leverage, or hidden pricing discretion.

## Immutable Safety Invariants
- Collateral and settlement remain stablecoin-denominated only.
- Instruments remain isolated; no cross-margin is introduced through governance.
- Trading price remains order-flow determined; the index remains a reference input for funding, liquidation, and circuit-breakers only.
- Effective leverage can never exceed `5.0x`.
- Governance cannot disable audit logging, timelock publication, or public transparency outputs.
- Emergency logic can restrict trading conditions, but cannot force-fill, reprice user orders, or selectively intervene in individual accounts.

## Governance Control Matrix
| governed_parameter | min_value | max_value | change_authority | timelock_rule | emergency_override_condition | audit_requirement |
|---|---:|---:|---|---|---|---|
| `launch_base_leverage_min` | `1.0x` | `2.0x` | DAO risk vote | 48h public timelock | May only revert to last-good value if stress automation or circuit-breaker integrity fails | Proposal, vote hash, old/new values, activation time |
| `absolute_leverage_cap` | `2.0x` | `5.0x` | DAO supermajority | 72h public timelock | May only be reduced immediately during emergency; never increased via override | Proposal, quorum proof, old/new values, rationale |
| `funding_multiplier_cap` | `1.0` | `4.0` | DAO risk vote | 48h public timelock | Can be reset to last-good value if runaway amplification is caused by a verified model fault | Parameter diff, incident reference, activation expiry |
| `spread_floor_bps` | `5` | `250` | DAO risk vote | 24h public timelock | Can be raised immediately during objective liquidity collapse; cannot be lowered via override | Parameter diff, trigger metrics, expiry |
| `position_size_cap_pct_of_oi` | `1%` | `15%` | DAO risk vote | 24h public timelock | Can be tightened immediately under liquidation clustering or vault stress | Parameter diff, trigger metrics, expiry |
| `open_interest_cap_pct_of_vault` | `10%` | `80%` | DAO risk vote | 48h public timelock | Can be tightened immediately when vault utilization breaches emergency threshold | Parameter diff, trigger metrics, expiry |
| `vault_allocation_cap_pct` | `5%` | `40%` | DAO treasury vote | 72h public timelock | Can be reduced immediately to contain a stressed instrument; cannot be increased via override | Vote record, treasury impact, activation time |
| `oracle_source_weight_per_source` | `0%` | `60%` | DAO oracle committee ratified by DAO | 48h public timelock | Weights may be frozen to the prepublished fallback set when source instability or quorum loss is detected | Weight vector before/after, trigger event, expiry |
| `oracle_quorum_min_sources` | `2` | `5` | DAO oracle committee ratified by DAO | 48h public timelock | May switch to a stricter fallback quorum schedule already published in the registry | Trigger event, fallback schedule id, expiry |
| `index_divergence_halt_band_pct` | `2%` | `12%` | DAO risk vote | 48h public timelock | Can only tighten immediately if divergence control is failing; cannot widen via override | Parameter diff, divergence readings, expiry |
| `depth_collapse_threshold_pct` | `20%` | `80%` | DAO risk vote | 24h public timelock | Can only tighten immediately when order-book thinning rate exceeds emergency threshold | Parameter diff, depth metrics, expiry |
| `reopen_stage_duration_minutes` | `5` | `120` | DAO operations policy vote | 24h public timelock | May extend the current stage once when recovery conditions fail, capped at registry max | Incident log, stage id, extension duration |
| `new_instrument_listing_status` | `0` | `1` | DAO listing vote | 72h public timelock before enablement | Emergency authority may pause pending listings; cannot activate a new listing | Listing proposal id, status change, reason |

## Routine Governance vs Emergency Actions
| Dimension | Routine governance | Emergency action |
|---|---|---|
| Purpose | Tune predeclared parameters or approve listings within bounded ranges | Temporarily constrain the system to preserve solvency, auditability, and orderly reopening |
| Who may act | DAO or named governance subcommittee with DAO-backed scope | Emergency multisig operating under predeclared trigger conditions |
| Allowed direction | Increase or decrease within parameter band, subject to authority scope | Restrictive only: pause, tighten, freeze to fallback, or revert to last-good value |
| Activation timing | After public timelock expires | Immediate once objective condition evaluates `true` |
| Duration | Persistent until superseded by another valid governance action | Temporary with auto-expiry and forced post-incident review |
| Transparency | Proposal and activation disclosed ahead of time | Trigger metrics, override action, expiry, and incident reference published immediately |

## Emergency Override Framework
### Authorized Emergency Authority
- `Emergency Council`: a 2-of-3 multisig with scope limited to the override actions enumerated below.
- The council cannot introduce new parameters, widen risk limits, list new instruments, or bypass audit publication.

### Objective Trigger Conditions
Emergency overrides are valid only when one or more of the following machine-observable conditions occur:
1. `oracle_quorum_failure`: active source count falls below the published quorum minimum.
2. `index_divergence_breach`: market/index divergence exceeds the configured halt band for the configured dwell time.
3. `depth_collapse_event`: visible top-of-book depth falls below the configured collapse threshold.
4. `liquidation_cluster_emergency`: liquidation cluster density and vault utilization both exceed their emergency thresholds.
5. `control_integrity_failure`: the automated response or circuit-breaker subsystem fails checksum or state-transition validation.

### Allowed Emergency Actions
| override_action | Allowed effect | Bound | Auto-expiry |
|---|---|---|---|
| `force_reduce_only` | Prevents net-new exposure while allowing position reduction | Global or instrument scoped only | 6 hours |
| `tighten_leverage_to_floor` | Sets effective leverage to the lowest predeclared band for the affected scope | Never below `1.0x`, never above current cap | 6 hours |
| `tighten_spread_to_emergency_floor` | Raises minimum spread to the predeclared emergency level | Cannot exceed `250 bps` | 6 hours |
| `tighten_position_and_oi_caps` | Applies the lower of current values and emergency fallback caps | Restrictive only | 6 hours |
| `freeze_oracle_weights_to_fallback` | Replaces dynamic weights with the prepublished fallback vector | Must use registry fallback only | 6 hours |
| `pause_new_listings` | Blocks activation of pending listings | Cannot affect already active contracts except by separate circuit-breaker logic | 24 hours |
| `extend_reopen_stage_once` | Adds one bounded extension to the current reopen stage when recovery fails | Maximum total stage duration `120 minutes` | Expires at stage completion |
| `revert_parameter_to_last_good` | Restores the most recent ratified value for a parameter affected by control-integrity failure | Only for parameters in this registry | 24 hours |

### Explicitly Forbidden Emergency Actions
- Manual repricing of trades or index values.
- Selective intervention on individual accounts or positions outside the published liquidation workflow.
- Increasing leverage caps, widening divergence bands, or increasing vault allocation caps through emergency powers.
- Listing or enabling a new instrument via emergency authority.
- Disabling public disclosure, audit logging, or timelock visibility.

## Audit and Disclosure Requirements
- Every routine governance change publishes: proposal id, authority, prior value, new value, activation timestamp, and affected instruments.
- Every emergency action publishes immediately: trigger condition id, observed metrics, action taken, scope, signer set, start timestamp, and expiry timestamp.
- A post-incident report is required within 24 hours for any emergency override.
- DAO ratification or rollback is required within 7 days for every emergency action that materially changed market controls.

## Registry Implementation Notes
- The JSON registry is the canonical machine-readable source for downstream services.
- Services consuming the registry should reject any parameter update that exceeds the declared `min_value` and `max_value`.
- Emergency action handlers should enforce `restrictive_only = true` and validate that any fallback target exists in the published registry.

## Outcome
This framework gives governance bounded control over market configuration while preserving the epic's core constraint: the venue remains deterministic, transparent, and resistant to discretionary intervention even during severe stress.
