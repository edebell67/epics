from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


@dataclass(frozen=True)
class LeverageBandInputs:
    instrument_id: str
    timestamp_utc: str
    base_leverage: float
    governance_max_leverage: float
    launch_max_leverage: float
    launch_mode: bool
    realized_volatility: float
    vault_imbalance: float
    depth_score: float
    stress_velocity: float


@dataclass(frozen=True)
class LeverageBandOutput:
    instrument_id: str
    timestamp_utc: str
    base_leverage: float
    permitted_cap: float
    realized_volatility: float
    vault_imbalance: float
    depth_score: float
    stress_velocity: float
    risk_score: float
    healthy_score: float
    effective_leverage_band: List[float]

    def as_dict(self) -> Dict[str, object]:
        return asdict(self)


def calculate_effective_leverage_band(inputs: LeverageBandInputs) -> LeverageBandOutput:
    realized_volatility = _clamp(inputs.realized_volatility, 0.0, 1.0)
    vault_imbalance = _clamp(inputs.vault_imbalance, 0.0, 1.0)
    depth_score = _clamp(inputs.depth_score, 0.0, 1.0)
    stress_velocity = _clamp(inputs.stress_velocity, 0.0, 1.0)

    base_leverage = max(1.0, inputs.base_leverage)
    governance_max_leverage = max(1.0, inputs.governance_max_leverage)
    launch_max_leverage = _clamp(inputs.launch_max_leverage, 1.0, 2.0)
    permitted_cap = (
        min(governance_max_leverage, launch_max_leverage)
        if inputs.launch_mode
        else governance_max_leverage
    )
    base_leverage = min(base_leverage, permitted_cap)

    depth_penalty = 1.0 - depth_score
    risk_score = (
        0.35 * realized_volatility
        + 0.25 * vault_imbalance
        + 0.20 * depth_penalty
        + 0.20 * stress_velocity
    )
    healthy_score = (
        0.30 * (1.0 - realized_volatility)
        + 0.20 * (1.0 - vault_imbalance)
        + 0.35 * depth_score
        + 0.15 * (1.0 - stress_velocity)
    )

    if inputs.launch_mode:
        target_leverage = base_leverage
    else:
        expansion = _clamp((healthy_score - 0.60) / 0.40, 0.0, 1.0)
        target_leverage = base_leverage + (permitted_cap - base_leverage) * expansion

    compression = _clamp((risk_score - 0.15) / 0.75, 0.0, 1.0)
    effective_max = max(1.0, target_leverage - (target_leverage - 1.0) * compression)
    effective_max = min(effective_max, permitted_cap)

    return LeverageBandOutput(
        instrument_id=inputs.instrument_id,
        timestamp_utc=inputs.timestamp_utc,
        base_leverage=base_leverage,
        permitted_cap=permitted_cap,
        realized_volatility=realized_volatility,
        vault_imbalance=vault_imbalance,
        depth_score=depth_score,
        stress_velocity=stress_velocity,
        risk_score=round(risk_score, 4),
        healthy_score=round(healthy_score, 4),
        effective_leverage_band=[1.0, round(effective_max, 2)],
    )


if __name__ == "__main__":
    sample = LeverageBandInputs(
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
    print(calculate_effective_leverage_band(sample).as_dict())
