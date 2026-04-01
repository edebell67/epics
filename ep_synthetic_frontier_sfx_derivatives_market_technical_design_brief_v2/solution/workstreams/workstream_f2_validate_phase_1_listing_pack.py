from __future__ import annotations

import json
from pathlib import Path


PACK_PATH = Path(
    r"C:\Users\edebe\eds\ep_synthetic_frontier_sfx_derivatives_market_technical_design_brief_v2\solution\workstreams\workstream_f2_phase_1_listing_pack.json"
)

EXPECTED_INSTRUMENTS = {"NGN_VOL", "KES_VOL", "GHS_VOL", "ZAR_VOL"}
EXPECTED_SMOOTHING_WINDOWS = {
    "NGN_VOL": 900,
    "KES_VOL": 600,
    "GHS_VOL": 900,
    "ZAR_VOL": 300,
}
REQUIRED_INSTRUMENT_FIELDS = {
    "instrument_id",
    "launch_enabled",
    "initial_leverage_band",
    "exposure_cap",
    "funding_base_params",
    "spread_floor",
    "status",
}


def load_pack(path: Path = PACK_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_pack(data: dict) -> tuple[int, float]:
    assert data["pack_id"] == "f2.phase_1.v1"
    assert data["launch_assumptions"]["cross_margin_enabled"] is False
    assert data["launch_assumptions"]["per_instrument_vault_isolation"] is True
    assert data["launch_assumptions"]["phase_1_operational_max_leverage"] <= 2.0
    assert data["launch_assumptions"]["governance_hard_max_leverage"] == 5.0

    references = data["upstream_references"]
    assert len(references) >= 5
    for reference in references:
        assert Path(reference["artifact_path"]).exists(), reference["artifact_path"]

    instruments = data["instruments"]
    instrument_ids = {item["instrument_id"] for item in instruments}
    assert instrument_ids == EXPECTED_INSTRUMENTS

    total_vault_fraction = 0.0
    max_operational_leverage = 0.0

    for item in instruments:
        assert REQUIRED_INSTRUMENT_FIELDS.issubset(item)
        assert item["launch_enabled"] is True
        assert item["status"] == "launch_ready"
        leverage_band = item["initial_leverage_band"]
        cap = item["exposure_cap"]
        spread_floor = item["spread_floor"]
        index_requirements = item["index_requirements"]

        assert leverage_band["min"] == 1.0
        assert leverage_band["max"] <= data["launch_assumptions"]["phase_1_operational_max_leverage"]
        assert cap["vault_fraction"] <= 0.18
        assert cap["tighten_on_stress_to_vault_fraction"] < cap["vault_fraction"]
        assert spread_floor["normal_bps"] >= 35
        assert spread_floor["stress_bps"] > spread_floor["normal_bps"]
        assert index_requirements["min_usable_sources"] >= 2
        assert (
            index_requirements["default_smoothing_window_seconds"]
            == EXPECTED_SMOOTHING_WINDOWS[item["instrument_id"]]
        )

        total_vault_fraction += cap["vault_fraction"]
        max_operational_leverage = max(max_operational_leverage, leverage_band["max"])

    assert round(total_vault_fraction, 8) <= data["launch_assumptions"]["aggregate_phase_1_exposure_cap_fraction"]

    return len(instruments), round(total_vault_fraction, 2), max_operational_leverage


def main() -> None:
    instrument_count, total_cap, max_operational_leverage = validate_pack(load_pack())
    print(
        "phase_1_pack_ok "
        f"instruments={instrument_count} "
        f"total_vault_cap={total_cap:.2f} "
        f"max_operational_leverage={max_operational_leverage:.2f}"
    )


if __name__ == "__main__":
    main()
