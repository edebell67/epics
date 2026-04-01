from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "solution"))

from dynamic_leverage_band_engine import LeverageBandInputs, calculate_effective_leverage_band


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    spec_path = ROOT / "workstreams" / "C" / "dynamic_leverage_band_engine.md"
    spec_text = spec_path.read_text(encoding="utf-8")

    for required_term in (
        "realized_volatility",
        "vault_imbalance",
        "depth_score",
        "stress_velocity",
        "1x-2x",
        "Recalculation Cadence",
        "Publishing Behavior",
    ):
        assert_true(required_term in spec_text, f"Spec missing required term: {required_term}")

    calm_launch = calculate_effective_leverage_band(
        LeverageBandInputs(
            instrument_id="sfx_ngn_perp",
            timestamp_utc="2026-03-16T21:40:00Z",
            base_leverage=2.0,
            governance_max_leverage=5.0,
            launch_max_leverage=2.0,
            launch_mode=True,
            realized_volatility=0.18,
            vault_imbalance=0.10,
            depth_score=0.92,
            stress_velocity=0.12,
        )
    )
    assert_true(calm_launch.effective_leverage_band == [1.0, 2.0], "Launch posture must remain 1x-2x in calm launch mode")

    thin_liquidity = calculate_effective_leverage_band(
        LeverageBandInputs(
            instrument_id="sfx_ngn_perp",
            timestamp_utc="2026-03-16T21:41:00Z",
            base_leverage=2.0,
            governance_max_leverage=5.0,
            launch_max_leverage=2.0,
            launch_mode=True,
            realized_volatility=0.42,
            vault_imbalance=0.35,
            depth_score=0.25,
            stress_velocity=0.48,
        )
    )
    assert_true(thin_liquidity.effective_leverage_band[1] < 2.0, "Thin liquidity must compress leverage below the launch cap")

    severe_stress = calculate_effective_leverage_band(
        LeverageBandInputs(
            instrument_id="sfx_ngn_perp",
            timestamp_utc="2026-03-16T21:42:00Z",
            base_leverage=2.0,
            governance_max_leverage=5.0,
            launch_max_leverage=2.0,
            launch_mode=True,
            realized_volatility=0.88,
            vault_imbalance=0.82,
            depth_score=0.10,
            stress_velocity=0.91,
        )
    )
    assert_true(severe_stress.effective_leverage_band[1] <= 1.10, "Severe stress must compress leverage toward 1x")

    post_launch = calculate_effective_leverage_band(
        LeverageBandInputs(
            instrument_id="sfx_ngn_perp",
            timestamp_utc="2026-03-16T21:43:00Z",
            base_leverage=2.0,
            governance_max_leverage=5.0,
            launch_max_leverage=2.0,
            launch_mode=False,
            realized_volatility=0.14,
            vault_imbalance=0.08,
            depth_score=0.95,
            stress_velocity=0.10,
        )
    )
    assert_true(post_launch.effective_leverage_band[1] <= 5.0, "Post-launch band must respect the configurable max cap")
    assert_true(post_launch.effective_leverage_band[1] > 2.0, "Healthy post-launch conditions should permit expansion above the launch cap")

    print("verify_dynamic_leverage_band_engine: all assertions passed")
    print(f"calm_launch={calm_launch.as_dict()}")
    print(f"thin_liquidity={thin_liquidity.as_dict()}")
    print(f"severe_stress={severe_stress.as_dict()}")
    print(f"post_launch={post_launch.as_dict()}")


if __name__ == "__main__":
    main()
