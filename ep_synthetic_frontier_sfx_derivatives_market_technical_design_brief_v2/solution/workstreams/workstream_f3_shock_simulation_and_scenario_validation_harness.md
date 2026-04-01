# Workstream F3 Shock Simulation And Scenario Validation Harness

## Purpose

This artifact defines the deterministic validation harness used to test the phase-1 sFX venue against `30%` to `50%` macro-shock scenarios while preserving isolated vault capital, functioning liquidity, and attributable automated control reactions.

## Implemented Artifacts

- `solution/json/shock_validation_scenarios.json`
- `solution/shock_simulation_harness/engine.py`
- `solution/tests/test_shock_simulation_harness.py`
- `verification/validate_shock_scenarios.py`
- `verification/workstream_f3_shock_scorecard_template.csv`

## Harness Inputs

The harness composes the existing workstream outputs instead of inventing a separate control model:

- B2 order-book depth, thinning, and imbalance-derived stress inputs
- B3 funding sign, multiplier, and vault-spread retention behavior
- C1 isolated vault capital and open-interest cap constraints
- C2 executable leverage compression via `dynamic_leverage_band_engine.py`
- C3 spread widening and executable liquidity scoring
- D1 metric thresholds and aggregate stress-level rules
- D2 deterministic response matrix from `stress_response_orchestrator_matrix.json`
- D3 halt and staged-reopening semantics
- F2 phase-1 instrument caps and launch leverage limits

## Scorecard Dimensions

The scorecard emits deterministic pass/fail results for:

- vault capital integrity
- liquidity continuity
- funding stabilization
- transparency outputs
- governance stability

`overall_pass` is `true` only when all five dimensions pass.

## Reproducibility

The harness is deterministic:

- no random sampling
- no clock-dependent branching beyond scenario timestamps
- result hash derived from scenario id plus key output states
- pytest validates that repeated execution yields identical structured results
