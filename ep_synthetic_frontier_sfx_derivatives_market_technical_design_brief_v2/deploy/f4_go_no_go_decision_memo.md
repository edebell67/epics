# F4 Go/No-Go Decision Memo

Decision Date: 2026-03-19
Decision: `no_go`
Release Scope Evaluated: public phase-1 MVP launch for `NGN_VOL`, `KES_VOL`, `GHS_VOL`, and `ZAR_VOL`

## Executive Summary

The workspace contains sufficient design-time evidence to support a controlled internal rehearsal of the phase-1 sFX launch package. The public external MVP launch should not proceed on 2026-03-19 because the only operator-surface evidence available in the workspace is a dashboard smoke test and snapshot that explicitly rely on deterministic mock transparency data rather than proven live publication inputs.

## Positive Readiness Signals

- Configuration posture is conservative and validated through the F2 pack.
- Emergency governance remains bounded and restrictive-only.
- Deterministic macro-shock scenarios from `30%` to `50%` all pass scorecard checks.
- Per-instrument containment and local loss boundaries are documented.
- Transparency contract fields, cadences, and redaction boundaries are defined and validated.

## Blocking Findings

1. `E3` remains a launch blocker for a public release.
   - Evidence link: `C:\Users\edebe\eds\ep_synthetic_frontier_sfx_derivatives_market_technical_design_brief_v2\verification\20260316_sfx_dashboard_smoke.txt`
   - Evidence link: `C:\Users\edebe\eds\ep_synthetic_frontier_sfx_derivatives_market_technical_design_brief_v2\verification\20260316_sfx_market_state_snapshot.html`
   - Rationale: the snapshot states the dashboard is using deterministic mock transparency data, so the package does not yet prove a live production publication path.
2. The current package proves deterministic validation, not live operating rehearsal.
   - Evidence link: `C:\Users\edebe\eds\ep_synthetic_frontier_sfx_derivatives_market_technical_design_brief_v2\verification\workstream_f3_shock_validation_results.json`
   - Rationale: the shock results are strong, but they validate control contracts and expected reactions rather than a live connected venue.

## Supporting Evidence

- Configuration evidence link: `C:\Users\edebe\eds\ep_synthetic_frontier_sfx_derivatives_market_technical_design_brief_v2\solution\workstreams\workstream_f2_phase_1_listing_pack.json`
- Governance evidence link: `C:\Users\edebe\eds\ep_synthetic_frontier_sfx_derivatives_market_technical_design_brief_v2\solution\workstreams\workstreamE_governance_parameter_band_registry.json`
- Transparency evidence link: `C:\Users\edebe\eds\ep_synthetic_frontier_sfx_derivatives_market_technical_design_brief_v2\solution\transparency\public_transparency_disclosure_pack.md`
- Isolation evidence link: `C:\Users\edebe\eds\ep_synthetic_frontier_sfx_derivatives_market_technical_design_brief_v2\workstreams\F\f1_isolated_margin_and_per_instrument_containment_model.md`
- Shock-test evidence link: `C:\Users\edebe\eds\ep_synthetic_frontier_sfx_derivatives_market_technical_design_brief_v2\verification\workstream_f3_shock_validation_results.json`

## Required Exit Criteria To Move To Go

1. Replace the mock-backed transparency surface with a live-backed publication flow.
2. Capture a fresh dashboard smoke test and snapshot proving live publication inputs.
3. Re-run F2, E1, F3, and F4 validations against the live-backed operator surface.
4. Execute at least one internal shadow launch rehearsal with incident, halt, and reopen drills.

## Owner And Follow-Up

- Blocking owner: Transparency Operator
- Decision owner: Launch Commander
- Next review trigger: completion of live-backed dashboard validation artifacts
