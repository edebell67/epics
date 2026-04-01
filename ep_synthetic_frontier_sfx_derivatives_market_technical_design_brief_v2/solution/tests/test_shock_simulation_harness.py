from __future__ import annotations

import sys
from pathlib import Path


SOLUTION_ROOT = Path(__file__).resolve().parents[1]
if str(SOLUTION_ROOT) not in sys.path:
    sys.path.insert(0, str(SOLUTION_ROOT))

from shock_simulation_harness.engine import load_default_harness


def test_scenario_library_covers_required_shock_band() -> None:
    harness = load_default_harness()
    results = harness.run_all()

    shock_sizes = {result.shock_size for result in results}

    assert 0.30 in shock_sizes
    assert 0.50 in shock_sizes
    assert len(results) >= 2


def test_results_are_reproducible_and_attributable_to_control_reactions() -> None:
    harness = load_default_harness()

    first_pass = [result.as_dict() for result in harness.run_all()]
    second_pass = [result.as_dict() for result in harness.run_all()]

    assert first_pass == second_pass
    for result in first_pass:
        controls = {item["control"]: item for item in result["control_reactions"]}
        assert controls["stress_response_orchestrator"]["actions"]
        assert controls["dynamic_leverage_band"]["effective_band"][1] <= 2.0
        assert result["reproducibility_hash"]


def test_scorecard_covers_required_survivability_dimensions() -> None:
    harness = load_default_harness()

    for result in harness.run_all():
        scorecard = result.scorecard
        assert set(scorecard) == {
            "vault_capital_integrity",
            "liquidity_continuity",
            "funding_stabilization",
            "transparency_outputs",
            "governance_stability",
            "overall_pass",
        }
        assert scorecard["vault_capital_integrity"] is True
        assert scorecard["liquidity_continuity"] is True
        assert scorecard["funding_stabilization"] is True
        assert scorecard["transparency_outputs"] is True
        assert scorecard["governance_stability"] is True
        assert scorecard["overall_pass"] is True


def test_severe_scenarios_use_staged_recovery_and_preserve_vault_capital() -> None:
    harness = load_default_harness()
    severe_results = [result for result in harness.run_all() if result.shock_size >= 0.50]

    assert severe_results
    for result in severe_results:
        states = [item["state"] for item in result.market_status_timeline]
        assert "HALTED_LOCKDOWN" in states
        assert states[-1] == "ACTIVE_POST_RECOVERY"
        assert result.vault_state["free_capital"] > 0
