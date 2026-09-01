# epics/ep_050_distribution_engine/implementation/node_35/test_winner_amplification.py
# EP050 Node 35 — Winner Amplification Test Suite.

from __future__ import annotations

import pytest
from winner_amplification import (
    WinnerAmplificationValidationError,
    generate_amplification_plan,
    derive_amplification_id,
)

SAMPLE_WINNER = {
    "schema_version": "1.0.0",
    "winner_id": "wnr_98a7b6c5d4e3",
    "opportunity_id": "opp_diagnostic_quote_001",
    "channel": "search_landing",
    "is_winner": True,
}


def test_generate_amplification_plan_success():
    """No adjacent_geos supplied -> only the domain-neutral format_diversification variant is
    produced. Until 2026-08-19 an unsupplied adjacent_geos fabricated a fixed town list
    ("Greenwich"/"Lewisham"/"Bromley"/"Dulwich") regardless of what market the winner was in."""
    res = generate_amplification_plan(SAMPLE_WINNER)
    assert res["schema_version"] == "1.0.0"
    assert res["amplification_id"].startswith("amp_")
    assert len(res["expansion_variants"]) == 1
    assert res["expansion_variants"][0]["dimension"] == "format_diversification"
    assert "guardrails" in res
    assert res["status"] == "ready_for_effort_allocation"


def test_generate_amplification_plan_includes_geo_variant_when_real_geos_supplied():
    res = generate_amplification_plan(SAMPLE_WINNER, adjacent_geos=["Lewisham", "Charlton"])
    dimensions = [v["dimension"] for v in res["expansion_variants"]]
    assert "geographic_expansion" in dimensions
    geo_variant = next(v for v in res["expansion_variants"] if v["dimension"] == "geographic_expansion")
    assert geo_variant["target_markets"] == ["Lewisham", "Charlton"]


def test_non_winner_rejected():
    non_winner = dict(SAMPLE_WINNER, is_winner=False)
    with pytest.raises(WinnerAmplificationValidationError, match="Cannot amplify a non-winning strategy"):
        generate_amplification_plan(non_winner)
