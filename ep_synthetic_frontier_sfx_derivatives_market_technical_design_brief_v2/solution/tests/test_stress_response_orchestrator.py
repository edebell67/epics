from __future__ import annotations

import sys
from pathlib import Path


SOLUTION_ROOT = Path(__file__).resolve().parents[1]
if str(SOLUTION_ROOT) not in sys.path:
    sys.path.insert(0, str(SOLUTION_ROOT))

from stress_response_orchestrator.engine import load_default_engine


def test_matrix_maps_each_epic_response_to_triggered_actions() -> None:
    engine = load_default_engine()

    for level_name in ("warning", "elevated", "emergency"):
        level = engine.levels[level_name]
        assert level["trigger_condition"]
        assert level["cooldown_seconds"] > 0
        assert set(level["actions"]) == {
            "leverage_band",
            "funding_multiplier",
            "minimum_spread",
            "position_size_cap",
            "open_interest_cap",
        }


def test_multiple_signals_resolve_with_deterministic_precedence() -> None:
    engine = load_default_engine()

    response = engine.resolve(
        {
            "imbalance_slope_change": "elevated",
            "order_book_thinning_rate": "emergency",
            "volatility_acceleration": "warning",
        },
        instrument_id="NGN-PERP",
        current_level="normal",
        seconds_in_state=0,
    )

    assert response.target_level == "emergency"
    assert response.effective_level == "emergency"
    assert [action["action"] for action in response.ordered_actions] == [
        "leverage_band",
        "funding_multiplier",
        "minimum_spread",
        "position_size_cap",
        "open_interest_cap",
    ]
    actions = {action["action"]: action["value"] for action in response.ordered_actions}
    assert actions == {
        "leverage_band": 0.4,
        "funding_multiplier": 2.5,
        "minimum_spread": 2.25,
        "position_size_cap": 0.5,
        "open_interest_cap": 0.65,
    }
    assert response.publishable_payload["trigger_summary"][0] == {
        "signal": "order_book_thinning_rate",
        "severity": "emergency",
    }


def test_deescalation_waits_for_cooldown_and_keeps_publishable_audit_payload() -> None:
    engine = load_default_engine()

    response = engine.resolve(
        {"volatility_acceleration": "warning"},
        instrument_id="KES-PERP",
        current_level="emergency",
        seconds_in_state=600,
    )

    assert response.target_level == "warning"
    assert response.effective_level == "emergency"
    assert response.cooldown_seconds == 1800
    assert response.publishable_payload["instrument_id"] == "KES-PERP"
    assert response.publishable_payload["stress_level"] == "emergency"
    assert response.publishable_payload["target_stress_level"] == "warning"
    assert response.publishable_payload["transparency_fields"] == [
        "stress_level",
        "target_stress_level",
        "trigger_summary",
        "cooldown_seconds",
        "actions",
    ]
