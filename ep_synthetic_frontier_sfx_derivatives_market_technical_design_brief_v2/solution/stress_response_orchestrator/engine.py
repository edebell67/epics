from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Mapping


SEVERITY_RANK = {"normal": 0, "warning": 1, "elevated": 2, "emergency": 3}


@dataclass(frozen=True)
class ResolvedStressResponse:
    instrument_id: str
    current_level: str
    target_level: str
    effective_level: str
    active_signals: Dict[str, str]
    cooldown_seconds: int
    ordered_actions: list[dict[str, object]]
    publishable_payload: dict[str, object]


class StressResponseEngine:
    def __init__(self, spec: Mapping[str, object]) -> None:
        self.spec = spec
        self.levels = spec["levels"]
        self.action_order = list(spec["action_order"])
        self.signal_priority = list(spec["signal_priority"])

    @classmethod
    def from_path(cls, spec_path: Path) -> "StressResponseEngine":
        return cls(json.loads(spec_path.read_text(encoding="utf-8")))

    def resolve(
        self,
        signal_states: Mapping[str, str],
        *,
        instrument_id: str,
        current_level: str = "normal",
        seconds_in_state: int | None = None,
    ) -> ResolvedStressResponse:
        active_signals = self._normalize_signals(signal_states)
        target_level = self._highest_active_level(active_signals.values())
        effective_level = self._apply_cooldown(
            current_level=current_level,
            target_level=target_level,
            seconds_in_state=seconds_in_state,
        )

        merged_actions = self._merge_actions(active_signals, effective_level)
        ordered_actions = [
            {
                "action": action_name,
                "mode": merged_actions[action_name]["mode"],
                "value": merged_actions[action_name]["value"],
                "source_levels": merged_actions[action_name]["source_levels"],
            }
            for action_name in self.action_order
        ]
        publishable_payload = {
            "instrument_id": instrument_id,
            "stress_level": effective_level,
            "target_stress_level": target_level,
            "trigger_summary": self._build_trigger_summary(active_signals),
            "cooldown_seconds": self.levels[effective_level]["cooldown_seconds"],
            "actions": {
                action_name: {
                    "value": merged_actions[action_name]["value"],
                    "mode": merged_actions[action_name]["mode"],
                }
                for action_name in self.action_order
            },
            "transparency_fields": [
                "stress_level",
                "target_stress_level",
                "trigger_summary",
                "cooldown_seconds",
                "actions",
            ],
        }
        return ResolvedStressResponse(
            instrument_id=instrument_id,
            current_level=current_level,
            target_level=target_level,
            effective_level=effective_level,
            active_signals=active_signals,
            cooldown_seconds=self.levels[effective_level]["cooldown_seconds"],
            ordered_actions=ordered_actions,
            publishable_payload=publishable_payload,
        )

    def _normalize_signals(self, signal_states: Mapping[str, str]) -> Dict[str, str]:
        normalized = {
            signal: severity
            for signal, severity in signal_states.items()
            if severity in SEVERITY_RANK and severity != "normal"
        }
        return dict(
            sorted(
                normalized.items(),
                key=lambda item: (
                    -SEVERITY_RANK[item[1]],
                    self.signal_priority.index(item[0]) if item[0] in self.signal_priority else len(self.signal_priority),
                    item[0],
                ),
            )
        )

    def _highest_active_level(self, severities: Iterable[str]) -> str:
        highest_rank = 0
        highest_level = "normal"
        for severity in severities:
            rank = SEVERITY_RANK[severity]
            if rank > highest_rank:
                highest_rank = rank
                highest_level = severity
        return highest_level

    def _apply_cooldown(
        self,
        *,
        current_level: str,
        target_level: str,
        seconds_in_state: int | None,
    ) -> str:
        if SEVERITY_RANK[target_level] >= SEVERITY_RANK[current_level]:
            return target_level
        if seconds_in_state is None:
            return current_level
        required = int(self.levels[current_level]["cooldown_seconds"])
        if seconds_in_state >= required:
            return target_level
        return current_level

    def _merge_actions(
        self,
        active_signals: Mapping[str, str],
        effective_level: str,
    ) -> dict[str, dict[str, object]]:
        contributing_levels = list(active_signals.values()) or [effective_level]
        levels = sorted(set(contributing_levels + [effective_level]), key=lambda level: SEVERITY_RANK[level])
        merged: dict[str, dict[str, object]] = {}
        for action_name in self.action_order:
            candidates = [self.levels[level]["actions"][action_name] for level in levels]
            if action_name in {"leverage_band", "position_size_cap", "open_interest_cap"}:
                value = min(candidate["value"] for candidate in candidates)
            else:
                value = max(candidate["value"] for candidate in candidates)
            merged[action_name] = {
                "mode": candidates[0]["mode"],
                "value": value,
                "source_levels": levels,
            }
        return merged

    def _build_trigger_summary(self, active_signals: Mapping[str, str]) -> list[dict[str, str]]:
        return [
            {"signal": signal, "severity": severity}
            for signal, severity in active_signals.items()
        ]


def load_default_engine() -> StressResponseEngine:
    root = Path(__file__).resolve().parents[1]
    return StressResponseEngine.from_path(root / "json" / "stress_response_orchestrator_matrix.json")
