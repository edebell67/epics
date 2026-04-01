# D2 Automated Response Orchestrator

## Scope

This artifact turns epic section 5.2 into an executable response matrix for warning, elevated, and emergency stress states.

## Deterministic Rules

- The target stress level is the highest active severity emitted by D1 metrics.
- Escalation is immediate.
- De-escalation is delayed by the cooldown of the current level.
- Conflicting controls are merged by restrictiveness:
  - `leverage_band`, `position_size_cap`, `open_interest_cap`: choose the lowest scalar.
  - `funding_multiplier`, `minimum_spread`: choose the highest scalar.

## Publishable Outputs

The orchestrator emits a public-safe payload containing:

- `stress_level`
- `target_stress_level`
- ordered trigger summary
- cooldown seconds
- effective action scalars for leverage, funding, spread, position cap, and open-interest cap

## Implementation References

- `solution/json/stress_response_orchestrator_matrix.json`
- `solution/stress_response_orchestrator/engine.py`
- `solution/tests/test_stress_response_orchestrator.py`
