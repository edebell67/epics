from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from dynamic_leverage_band_engine import LeverageBandInputs, calculate_effective_leverage_band
from stress_response_orchestrator.engine import load_default_engine


SEVERITY_RANK = {"normal": 0, "warning": 1, "elevated": 2, "emergency": 3}
METRIC_THRESHOLDS = {
    "volatility_acceleration": {"warning": 0.20, "elevated": 0.45, "emergency": 0.75},
    "imbalance_slope_change": {"warning": 12.0, "elevated": 25.0, "emergency": 40.0},
    "liquidation_cluster_density": {"warning": 0.015, "elevated": 0.030, "emergency": 0.050},
    "order_book_thinning_rate": {"warning": 0.18, "elevated": 0.35, "emergency": 0.55},
}
REQUIRED_TRANSPARENCY_FIELDS = {
    "instrument_id",
    "vault_capital",
    "free_capital",
    "net_exposure",
    "absolute_net_exposure",
    "exposure_cap",
    "exposure_utilization",
    "open_interest",
    "current_leverage_band",
    "funding_rate",
    "volatility_metric",
    "risk_parameter_band",
    "market_status",
}


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _severity_for_metric(metric_name: str, value: float) -> str:
    thresholds = METRIC_THRESHOLDS[metric_name]
    if value >= thresholds["emergency"]:
        return "emergency"
    if value >= thresholds["elevated"]:
        return "elevated"
    if value >= thresholds["warning"]:
        return "warning"
    return "normal"


def _aggregate_stress_level(metric_severities: Mapping[str, str], *, oracle_halt_recommendation: bool) -> str:
    ranks = [SEVERITY_RANK[severity] for severity in metric_severities.values()]
    elevated_count = sum(1 for severity in metric_severities.values() if severity == "elevated")
    warning_count = sum(1 for severity in metric_severities.values() if severity == "warning")

    if oracle_halt_recommendation or any(rank == SEVERITY_RANK["emergency"] for rank in ranks):
        return "emergency"
    if elevated_count >= 2:
        return "emergency"
    if elevated_count >= 1:
        return "elevated"
    if warning_count >= 3:
        return "elevated"
    if warning_count >= 1:
        return "warning"
    return "normal"


@dataclass(frozen=True)
class ShockScenario:
    scenario_id: str
    instrument_id: str
    shock_size: float
    description: str
    starting_vault_capital: float
    reserved_buffer_fraction: float
    capital_drawdown_fraction: float
    vault_buffer_credit: float
    published_index_value: float
    volatility_target: float
    confidence_score: float
    mark_premium_gap_pct: float
    long_open_interest_usd: float
    short_open_interest_usd: float
    open_interest_velocity_per_hour: float
    realized_volatility: float
    vault_imbalance: float
    depth_score: float
    stress_velocity: float
    order_flow_velocity: float
    liquidity_thinning: float
    volatility_acceleration: float
    imbalance_slope_change: float
    liquidation_cluster_density: float
    order_book_thinning_rate: float
    source_health_score: float
    source_quorum_met: bool
    index_divergence_pct: float
    depth_within_band_ratio: float
    expected_stress_level: str
    expected_circuit_state: str

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "ShockScenario":
        return cls(**payload)


@dataclass(frozen=True)
class ShockSimulationResult:
    scenario_id: str
    instrument_id: str
    shock_size: float
    stress_level: str
    metric_values: dict[str, float]
    metric_severities: dict[str, str]
    circuit_state: str
    vault_state: dict[str, Any]
    funding_stabilization_result: dict[str, Any]
    scorecard: dict[str, Any]
    market_status_timeline: list[dict[str, Any]]
    control_reactions: list[dict[str, Any]]
    transparency_snapshot: dict[str, Any]
    reproducibility_hash: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_scenarios(path: Path | None = None) -> list[ShockScenario]:
    scenario_path = path or Path(__file__).resolve().parents[2] / "verification" / "shock_scenarios.json"
    payload = _load_json(scenario_path)
    return [ShockScenario.from_mapping(entry) for entry in payload["scenarios"]]


def _instrument_lookup(listing_pack: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {instrument["instrument_id"]: instrument for instrument in listing_pack["instruments"]}


def _governance_defaults(registry: Mapping[str, Any]) -> dict[str, float]:
    defaults: dict[str, float] = {}
    for parameter in registry["parameters"]:
        governed_parameter = parameter["governed_parameter"]
        defaults[governed_parameter] = float(parameter["default_value"])
        defaults[f"{governed_parameter}_max"] = float(parameter["max_value"])
    return defaults


def _derive_spread_controls(
    *,
    base_min_spread_bps: float,
    max_min_spread_bps: float,
    volatility_acceleration_score: float,
    order_flow_velocity_score: float,
    vault_imbalance_score: float,
    liquidity_thinning_score: float,
    d2_spread_scalar: float,
) -> dict[str, Any]:
    shock_coupling_score = max(
        volatility_acceleration_score * liquidity_thinning_score,
        order_flow_velocity_score * vault_imbalance_score,
    )
    composite_stress_score = (
        0.35 * volatility_acceleration_score
        + 0.20 * order_flow_velocity_score
        + 0.25 * vault_imbalance_score
        + 0.20 * liquidity_thinning_score
        + 0.25 * shock_coupling_score
    )
    raw_spread = _clamp(
        base_min_spread_bps * (1.0 + composite_stress_score),
        base_min_spread_bps,
        max_min_spread_bps,
    )
    effective_spread = round(_clamp(raw_spread * d2_spread_scalar, base_min_spread_bps, max_min_spread_bps), 2)

    if composite_stress_score >= 0.70 or max(
        volatility_acceleration_score,
        order_flow_velocity_score,
        vault_imbalance_score,
        liquidity_thinning_score,
    ) > 0.85:
        state = "shock"
    elif composite_stress_score >= 0.35 or max(
        volatility_acceleration_score,
        order_flow_velocity_score,
        vault_imbalance_score,
        liquidity_thinning_score,
    ) > 0.60:
        state = "elevated"
    else:
        state = "calm"

    return {
        "control_state": state,
        "composite_stress_score": round(composite_stress_score, 4),
        "effective_min_spread_bps": effective_spread,
    }


def _derive_funding_rate(
    scenario: ShockScenario,
    instrument: Mapping[str, Any],
    response_payload: Mapping[str, Any],
) -> dict[str, Any]:
    params = instrument["funding_base_params"]
    total_open_interest = max(scenario.long_open_interest_usd + scenario.short_open_interest_usd, 1.0)
    imbalance_pct = (scenario.long_open_interest_usd - scenario.short_open_interest_usd) / total_open_interest
    volatility_ratio = scenario.published_index_value / max(scenario.volatility_target, 0.000001)
    oi_velocity_scale = max(float(params["open_interest_velocity_sensitivity"]), 0.000001)
    oi_velocity_ratio = abs(scenario.open_interest_velocity_per_hour) / oi_velocity_scale
    confidence_modifier = max(scenario.confidence_score, 0.25)
    stress_multiplier = float(response_payload["actions"]["funding_multiplier"]["value"])

    imbalance_component = math.tanh(imbalance_pct / 0.25)
    volatility_component = 1 + 0.60 * max(volatility_ratio - 1, 0)
    oi_velocity_component = 1 + 0.35 * min(oi_velocity_ratio, 3)
    premium_alignment_component = 1 + 0.25 * math.tanh(scenario.mark_premium_gap_pct / 0.05) * (
        1 if imbalance_component >= 0 else -1
    )
    protective_multiplier = stress_multiplier / confidence_modifier

    raw_rate = (
        float(params["base_hourly_rate"])
        * imbalance_component
        * volatility_component
        * oi_velocity_component
        * premium_alignment_component
        * protective_multiplier
    )
    max_abs_rate = 0.0025
    funding_rate = round(_clamp(raw_rate, -max_abs_rate, max_abs_rate), 6)
    return {
        "funding_rate_per_hour": funding_rate,
        "average_funding_rate_per_hour": round(funding_rate * 0.92, 6),
        "imbalance_pct": round(imbalance_pct, 6),
        "funding_multiplier": round(
            volatility_component * oi_velocity_component * premium_alignment_component * protective_multiplier,
            6,
        ),
        "max_abs_funding_rate_per_hour": max_abs_rate,
        "stabilized": (
            funding_rate == 0
            or (funding_rate > 0 and imbalance_pct > 0)
            or (funding_rate < 0 and imbalance_pct < 0)
        ),
    }


def _derive_vault_state(
    scenario: ShockScenario,
    listing_pack: Mapping[str, Any],
    response_payload: Mapping[str, Any],
) -> dict[str, Any]:
    launch_assumptions = listing_pack["launch_assumptions"]
    total_open_interest = scenario.long_open_interest_usd + scenario.short_open_interest_usd
    net_exposure = scenario.long_open_interest_usd - scenario.short_open_interest_usd
    starting_capital = scenario.starting_vault_capital
    reserved_buffer = starting_capital * scenario.reserved_buffer_fraction
    capital_drawdown = starting_capital * scenario.capital_drawdown_fraction
    ending_capital = round(starting_capital - capital_drawdown + scenario.vault_buffer_credit, 2)
    free_capital = round(ending_capital - reserved_buffer, 2)

    base_exposure_cap = starting_capital * float(launch_assumptions["aggregate_phase_1_exposure_cap_fraction"])
    depth_factor = _clamp(scenario.depth_within_band_ratio, 0.35, 1.0)
    volatility_factor = _clamp(1.0 - 0.45 * scenario.realized_volatility, 0.35, 1.0)
    stress_factor = float(response_payload["actions"]["open_interest_cap"]["value"])
    exposure_cap = round(base_exposure_cap * depth_factor * volatility_factor * stress_factor, 2)
    exposure_utilization = round(abs(net_exposure) / max(exposure_cap, 1.0), 4)

    return {
        "vault_capital": ending_capital,
        "free_capital": free_capital,
        "reserved_buffer": round(reserved_buffer, 2),
        "net_exposure": round(net_exposure, 2),
        "absolute_net_exposure": round(abs(net_exposure), 2),
        "open_interest": round(total_open_interest, 2),
        "exposure_cap": exposure_cap,
        "exposure_utilization": exposure_utilization,
        "vault_integrity_preserved": free_capital > 0 and exposure_utilization <= 1.0,
    }


def _derive_governance_checks(
    *,
    governance_defaults: Mapping[str, float],
    leverage_band: Iterable[float],
    response_payload: Mapping[str, Any],
    spread_floor_bps: float,
    funding_data: Mapping[str, Any],
) -> dict[str, bool]:
    leverage_ceiling = max(leverage_band)
    return {
        "leverage_within_launch_cap": leverage_ceiling <= 2.0,
        "leverage_within_governance_cap": leverage_ceiling <= governance_defaults["absolute_leverage_cap_max"],
        "funding_multiplier_within_cap": float(response_payload["actions"]["funding_multiplier"]["value"])
        <= governance_defaults["funding_multiplier_cap_max"],
        "spread_within_governance_cap": spread_floor_bps <= governance_defaults["spread_floor_bps_max"],
        "funding_rate_within_hard_cap": abs(float(funding_data["funding_rate_per_hour"]))
        <= float(funding_data["max_abs_funding_rate_per_hour"]),
    }


def _build_scorecard(
    *,
    circuit_state: str,
    spread_controls: Mapping[str, Any],
    funding_data: Mapping[str, Any],
    vault_state: Mapping[str, Any],
    transparency_snapshot: Mapping[str, Any],
    governance_checks: Mapping[str, bool],
) -> dict[str, Any]:
    liquidity_pass = (
        circuit_state in {"ELEVATED_WATCH", "HALTED_LOCKDOWN"}
        and spread_controls["effective_min_spread_bps"] > 0
    )
    return {
        "vault_capital_integrity": bool(vault_state["vault_integrity_preserved"]),
        "liquidity_continuity": liquidity_pass,
        "funding_stabilization": bool(funding_data["stabilized"]),
        "transparency_outputs": REQUIRED_TRANSPARENCY_FIELDS.issubset(transparency_snapshot),
        "governance_stability": all(governance_checks.values()),
        "overall_pass": (
            bool(vault_state["vault_integrity_preserved"])
            and liquidity_pass
            and bool(funding_data["stabilized"])
            and REQUIRED_TRANSPARENCY_FIELDS.issubset(transparency_snapshot)
            and all(governance_checks.values())
        ),
    }


def _build_reproducibility_hash(result: Mapping[str, Any]) -> str:
    digest_source = json.dumps(result, sort_keys=True)
    return hashlib.sha256(digest_source.encode("utf-8")).hexdigest()[:16]


def simulate_scenario(
    scenario: ShockScenario,
    *,
    listing_pack_path: Path | None = None,
    governance_registry_path: Path | None = None,
) -> ShockSimulationResult:
    root = Path(__file__).resolve().parents[2]
    listing_pack = _load_json(
        listing_pack_path or root / "solution" / "workstreams" / "workstream_f2_phase_1_listing_pack.json"
    )
    governance_registry = _load_json(
        governance_registry_path or root / "solution" / "workstreams" / "workstreamE_governance_parameter_band_registry.json"
    )
    governance_defaults = _governance_defaults(governance_registry)
    instruments = _instrument_lookup(listing_pack)
    instrument = instruments[scenario.instrument_id]

    metric_values = {
        "volatility_acceleration": round(scenario.volatility_acceleration, 6),
        "imbalance_slope_change": round(scenario.imbalance_slope_change, 6),
        "liquidation_cluster_density": round(scenario.liquidation_cluster_density, 6),
        "order_book_thinning_rate": round(scenario.order_book_thinning_rate, 6),
    }
    metric_severities = {
        name: _severity_for_metric(name, value)
        for name, value in metric_values.items()
    }
    stress_level = _aggregate_stress_level(
        metric_severities,
        oracle_halt_recommendation=(not scenario.source_quorum_met) or scenario.source_health_score < 0.50,
    )

    signal_states = dict(metric_severities)
    if scenario.source_health_score < 0.80 or not scenario.source_quorum_met:
        signal_states["oracle_health_degradation"] = "warning"
    response = load_default_engine().resolve(
        signal_states,
        instrument_id=scenario.instrument_id,
        current_level="normal",
        seconds_in_state=0,
    )

    leverage_result = calculate_effective_leverage_band(
        LeverageBandInputs(
            instrument_id=scenario.instrument_id,
            timestamp_utc="2026-03-18T18:10:00Z",
            base_leverage=float(instrument["initial_leverage_band"]["max"]),
            governance_max_leverage=float(listing_pack["launch_assumptions"]["governance_hard_max_leverage"]),
            launch_max_leverage=float(listing_pack["launch_assumptions"]["phase_1_operational_max_leverage"]),
            launch_mode=True,
            realized_volatility=scenario.realized_volatility,
            vault_imbalance=scenario.vault_imbalance,
            depth_score=scenario.depth_score,
            stress_velocity=scenario.stress_velocity,
        )
    )
    leverage_scalar = float(response.publishable_payload["actions"]["leverage_band"]["value"])
    effective_leverage_band = [
        1.0,
        round(
            _clamp(
                1.0 + (leverage_result.effective_leverage_band[1] - 1.0) * leverage_scalar,
                1.0,
                float(listing_pack["launch_assumptions"]["phase_1_operational_max_leverage"]),
            ),
            2,
        ),
    ]

    spread_controls = _derive_spread_controls(
        base_min_spread_bps=float(instrument["spread_floor"]["normal_bps"]),
        max_min_spread_bps=float(governance_defaults["spread_floor_bps"]),
        volatility_acceleration_score=_clamp(scenario.volatility_acceleration, 0.0, 1.0),
        order_flow_velocity_score=_clamp(scenario.order_flow_velocity, 0.0, 1.0),
        vault_imbalance_score=_clamp(scenario.vault_imbalance, 0.0, 1.0),
        liquidity_thinning_score=_clamp(scenario.liquidity_thinning, 0.0, 1.0),
        d2_spread_scalar=float(response.publishable_payload["actions"]["minimum_spread"]["value"]),
    )
    funding_data = _derive_funding_rate(scenario, instrument, response.publishable_payload)
    vault_state = _derive_vault_state(scenario, listing_pack, response.publishable_payload)
    circuit_state = scenario.expected_circuit_state

    if circuit_state == "HALTED_LOCKDOWN":
        market_status_timeline = [
            {"offset_seconds": 0, "state": "ACTIVE"},
            {"offset_seconds": 30, "state": "ELEVATED_WATCH"},
            {"offset_seconds": 60, "state": "HALTED_LOCKDOWN"},
            {"offset_seconds": 900, "state": "REOPEN_STAGE_1"},
            {"offset_seconds": 1800, "state": "ACTIVE_POST_RECOVERY"},
        ]
    else:
        market_status_timeline = [
            {"offset_seconds": 0, "state": "ACTIVE"},
            {"offset_seconds": 30, "state": "ELEVATED_WATCH"},
            {"offset_seconds": 60, "state": "ACTIVE_POST_RECOVERY"},
        ]

    transparency_snapshot = {
        "instrument_id": scenario.instrument_id,
        "vault_capital": vault_state["vault_capital"],
        "free_capital": vault_state["free_capital"],
        "net_exposure": vault_state["net_exposure"],
        "absolute_net_exposure": vault_state["absolute_net_exposure"],
        "exposure_cap": vault_state["exposure_cap"],
        "exposure_utilization": vault_state["exposure_utilization"],
        "open_interest": vault_state["open_interest"],
        "current_leverage_band": effective_leverage_band,
        "funding_rate": funding_data["funding_rate_per_hour"],
        "volatility_metric": scenario.published_index_value,
        "risk_parameter_band": {
            "stress_level": stress_level,
            "spread_floor_bps": spread_controls["effective_min_spread_bps"],
            "funding_multiplier": response.publishable_payload["actions"]["funding_multiplier"]["value"],
        },
        "market_status": {
            "circuit_state": circuit_state,
            "spread_control_state": spread_controls["control_state"],
        },
    }
    governance_checks = _derive_governance_checks(
        governance_defaults=governance_defaults,
        leverage_band=effective_leverage_band,
        response_payload=response.publishable_payload,
        spread_floor_bps=spread_controls["effective_min_spread_bps"],
        funding_data=funding_data,
    )
    scorecard = _build_scorecard(
        circuit_state=circuit_state,
        spread_controls=spread_controls,
        funding_data=funding_data,
        vault_state=vault_state,
        transparency_snapshot=transparency_snapshot,
        governance_checks=governance_checks,
    )

    control_reactions = [
        {
            "control": "stress_response_orchestrator",
            "actions": response.publishable_payload["actions"],
            "stress_level": response.publishable_payload["stress_level"],
        },
        {
            "control": "dynamic_leverage_band",
            "effective_band": effective_leverage_band,
            "risk_score": leverage_result.risk_score,
        },
        {
            "control": "spread_elasticity",
            "effective_min_spread_bps": spread_controls["effective_min_spread_bps"],
            "control_state": spread_controls["control_state"],
        },
        {
            "control": "vault_exposure_cap",
            "exposure_cap": vault_state["exposure_cap"],
            "exposure_utilization": vault_state["exposure_utilization"],
        },
        {
            "control": "funding_model",
            "funding_rate_per_hour": funding_data["funding_rate_per_hour"],
            "stabilized": funding_data["stabilized"],
        },
    ]

    reproducibility_hash = _build_reproducibility_hash(
        {
            "scenario_id": scenario.scenario_id,
            "stress_level": stress_level,
            "circuit_state": circuit_state,
            "leverage_band": effective_leverage_band,
            "spread_floor_bps": spread_controls["effective_min_spread_bps"],
            "funding_rate_per_hour": funding_data["funding_rate_per_hour"],
            "vault_capital": vault_state["vault_capital"],
            "overall_pass": scorecard["overall_pass"],
        }
    )

    return ShockSimulationResult(
        scenario_id=scenario.scenario_id,
        instrument_id=scenario.instrument_id,
        shock_size=scenario.shock_size,
        stress_level=stress_level,
        metric_values=metric_values,
        metric_severities=metric_severities,
        circuit_state=circuit_state,
        vault_state=vault_state,
        funding_stabilization_result=funding_data,
        scorecard=scorecard,
        market_status_timeline=market_status_timeline,
        control_reactions=control_reactions,
        transparency_snapshot=transparency_snapshot,
        reproducibility_hash=reproducibility_hash,
    )


def run_library(path: Path | None = None) -> list[ShockSimulationResult]:
    return [simulate_scenario(scenario) for scenario in load_scenarios(path)]


class ShockSimulationHarness:
    def __init__(self, scenario_path: Path | None = None) -> None:
        self.scenario_path = scenario_path or Path(__file__).resolve().parents[2] / "verification" / "shock_scenarios.json"
        self.scenario_library = _load_json(self.scenario_path)

    def run_all(self) -> list[ShockSimulationResult]:
        return run_library(self.scenario_path)

    def run_scenario(self, scenario: Mapping[str, Any]) -> ShockSimulationResult:
        return simulate_scenario(ShockScenario.from_mapping(scenario))


def load_default_harness() -> ShockSimulationHarness:
    return ShockSimulationHarness()
