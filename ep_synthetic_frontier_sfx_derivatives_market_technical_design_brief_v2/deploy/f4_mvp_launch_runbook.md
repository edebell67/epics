# F4 MVP Launch Runbook

## Purpose

Operate the phase-1 sFX MVP launch in a conservative mode that keeps each instrument isolated, publishes the required public state, and escalates immediately into deterministic protective controls if health degrades.

## Launch Scope

- Phase-1 instruments: `NGN_VOL`, `KES_VOL`, `GHS_VOL`, `ZAR_VOL`
- Operating posture: conservative MVP with per-instrument vault isolation, no cross-margin, aggregate exposure cap fraction `0.55`, reserve buffer fraction `0.45`
- Default decision status for this package on 2026-03-19: `no_go` for public external launch until the transparency surface is backed by live rather than deterministic mock data

## Roles

| Role | Owner | Responsibility |
|---|---|---|
| Launch Commander | Operations lead | Owns the go/no-go call, prelaunch checklist sign-off, and incident command |
| Risk Duty Officer | Risk controls service owner | Monitors leverage, spread, funding, exposure utilization, and control-state drift |
| Market Controls Engineer | D2/D3 controls owner | Confirms halt-state transitions and staged reopen eligibility |
| Transparency Operator | Transparency service owner | Confirms snapshot publication freshness and public-state completeness |
| Governance Liaison | DAO operations delegate | Coordinates any restrictive emergency override and ratification trail |

## Startup Procedure

1. Confirm the approved listing pack is the active phase-1 configuration:
   - `workstream_f2_phase_1_listing_pack.json`
   - All four instruments present and marked `launch_ready`
   - Operational leverage does not exceed `2.0x`
2. Confirm governance registry is loaded and restrictive-only emergency policy is intact:
   - `workstreamE_governance_parameter_band_registry.json`
   - `emergency_policy.restrictive_only = true`
   - At least the 13 declared bounded parameters are present
3. Confirm isolation model remains unchanged:
   - `f1_isolated_margin_and_per_instrument_containment_model.md`
   - No cross-instrument margining or inter-vault borrowing
4. Confirm transparency contract validation passes:
   - `validate_public_transparency_contract.py`
   - Snapshot payload fields present with 60-second maximum staleness for required top-level values
5. Confirm shock validation remains green:
   - `validate_shock_scenarios.py`
   - All scenarios pass scorecard checks for vault integrity, liquidity continuity, funding stabilization, transparency outputs, and governance stability
6. Confirm operator visibility surface is reachable:
   - `verification/20260316_sfx_dashboard_smoke.txt`
   - Document whether the surface is live-backed or mock-backed before any launch decision

Release gate:
- Public MVP launch requires all checks above plus a live-backed transparency surface.
- If the transparency surface remains mock-backed, limit activity to shadow rehearsal, dry run, or internal operational drills only.

## Runtime Monitoring Procedure

Monitor every 60 seconds or faster during the first trading hour:

| Signal | Source | Threshold or expectation | Owner |
|---|---|---|---|
| `market_status` | Transparency snapshot plus D3 status | Immediate publish on any state change | Transparency Operator |
| `current_leverage_band` | C2 output via transparency snapshot | Never above instrument launch cap; investigate any unexplained compression | Risk Duty Officer |
| `funding_rate` | B3 funding output | Must remain inside model cap and show stabilizing sign | Risk Duty Officer |
| `exposure_utilization` | F3 results pattern and vault controls | Escalate if utilization approaches emergency tightening zone | Risk Duty Officer |
| `spread_floor_bps` | C3/D2 active risk band | Must widen under stress, never narrow via emergency path | Risk Duty Officer |
| `halt_state` and `reopen_stage` | D3 operator model | No manual reopen allowed; only deterministic staged progression | Market Controls Engineer |
| Transparency freshness | E1 contract | Required fields must remain within staleness budget | Transparency Operator |

Escalation triggers:
- Any missing required transparency field
- Any `market_status` transition without corresponding operator alert
- Emergency-level stress with no leverage compression, spread widening, or cap tightening
- Any evidence of cross-instrument loss transfer
- Any emergency request that would widen risk instead of tighten it

## Halt Procedure

Use this procedure for any instrument entering `HALTED` or `HALTED_LOCKDOWN`:

1. Freeze the affected instrument to the published D3 state only. Do not manually reprice or selectively intervene in accounts.
2. Confirm the trigger family:
   - `index_divergence_breach`
   - `oracle_quorum_failure`
   - `depth_collapse_event`
   - `liquidation_cluster_emergency`
   - `control_integrity_failure`
3. Validate the matching protective actions are present:
   - leverage compressed toward floor
   - funding multiplier increased
   - spread widened to stressed or emergency floor
   - position-size and open-interest caps tightened
4. Publish or verify immediate public state update:
   - `market_status`
   - `risk_parameter_band`
   - incident timestamp
5. If automation failed or controls are inconsistent, Governance Liaison may invoke only a restrictive emergency override from the registry:
   - `force_reduce_only`
   - `tighten_leverage_to_floor`
   - `tighten_spread_to_emergency_floor`
   - `tighten_position_and_oi_caps`
   - `freeze_oracle_weights_to_fallback`
   - `revert_parameter_to_last_good`
6. Record incident id, trigger metrics, signers, and expiry immediately.

## Reopen Procedure

Reopen only through the D3 staged flow:

1. Confirm cooldown elapsed for `HALTED` or `HALTED_LOCKDOWN`.
2. Confirm all recovery requirements are true for the full stability window:
   - depth recovery
   - source stability
   - divergence recovery
3. Permit `REOPEN_STAGE_1` only:
   - cancel and passive-only quoting
   - no market orders
   - no leverage increases
4. Advance to `REOPEN_STAGE_2` only after the dwell window passes with no trigger relapse.
5. Advance to `ACTIVE_POST_RECOVERY` only if limited matching remains stable and D2 response lock is cooling down normally.
6. Return to `ACTIVE` only after the full observation window completes without renewed trigger activation.
7. If any original trigger reappears during any reopen stage, force `HALTED_LOCKDOWN`.

## Incident Escalation Procedure

1. Launch Commander opens incident command and names the affected instrument scope.
2. Risk Duty Officer captures the active control state and confirms whether the issue is contained locally or systemic.
3. Market Controls Engineer verifies D3 transition validity and next eligible transition time.
4. Transparency Operator confirms public disclosure completeness and freshness.
5. Governance Liaison is engaged only if the registry allows a restrictive emergency action and automation has failed or needs hardening.
6. Publish a post-incident report within 24 hours and ratify or roll back any emergency action within 7 days.

## Launch-Day Stop Conditions

- Transparency surface still uses deterministic mock data instead of live publication inputs
- Governance registry missing, altered outside bounds, or not restrictive-only
- Any upstream validator fails
- Any instrument exceeds the approved launch leverage or cap posture
- Inability to prove per-instrument isolation and local loss containment

## Evidence References

- F1 isolation model: `C:\Users\edebe\eds\ep_synthetic_frontier_sfx_derivatives_market_technical_design_brief_v2\workstreams\F\f1_isolated_margin_and_per_instrument_containment_model.md`
- F2 listing pack: `C:\Users\edebe\eds\ep_synthetic_frontier_sfx_derivatives_market_technical_design_brief_v2\solution\workstreams\workstream_f2_phase_1_listing_pack.json`
- E1 transparency pack: `C:\Users\edebe\eds\ep_synthetic_frontier_sfx_derivatives_market_technical_design_brief_v2\solution\transparency\public_transparency_disclosure_pack.md`
- E2 governance framework: `C:\Users\edebe\eds\ep_synthetic_frontier_sfx_derivatives_market_technical_design_brief_v2\solution\workstreams\workstreamE_governance_parameter_band_and_emergency_override_framework.md`
- F3 shock results: `C:\Users\edebe\eds\ep_synthetic_frontier_sfx_derivatives_market_technical_design_brief_v2\verification\workstream_f3_shock_validation_results.json`
- Dashboard smoke evidence: `C:\Users\edebe\eds\ep_synthetic_frontier_sfx_derivatives_market_technical_design_brief_v2\verification\20260316_sfx_dashboard_smoke.txt`
- Dashboard snapshot evidence: `C:\Users\edebe\eds\ep_synthetic_frontier_sfx_derivatives_market_technical_design_brief_v2\verification\20260316_sfx_market_state_snapshot.html`
