from __future__ import annotations

import json
import sys
from pathlib import Path


EPIC_ROOT = Path(__file__).resolve().parents[1]
SOLUTION_ROOT = EPIC_ROOT / "solution"
if str(SOLUTION_ROOT) not in sys.path:
    sys.path.insert(0, str(SOLUTION_ROOT))

from shock_simulation_harness.engine import load_default_harness


OUTPUT_PATH = EPIC_ROOT / "verification" / "workstream_f3_shock_validation_results.json"


def main() -> None:
    harness = load_default_harness()
    results = [result.as_dict() for result in harness.run_all()]

    OUTPUT_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")

    scenario_ids = [result["scenario_id"] for result in results]
    assert any(result["shock_size"] == 0.3 for result in results)
    assert any(result["shock_size"] == 0.5 for result in results)

    for result in results:
        scorecard = result["scorecard"]
        assert scorecard["vault_capital_integrity"] is True
        assert scorecard["liquidity_continuity"] is True
        assert scorecard["funding_stabilization"] is True
        assert scorecard["transparency_outputs"] is True
        assert scorecard["governance_stability"] is True
        assert scorecard["overall_pass"] is True
        controls = {item["control"]: item for item in result["control_reactions"]}
        assert controls["stress_response_orchestrator"]["actions"]
        assert result["market_status_timeline"]

    print(
        "shock_validation_passed "
        f"scenarios={len(results)} "
        f"scenario_ids={','.join(scenario_ids)} "
        "checks=vault_capital_integrity,liquidity_continuity,funding_stabilization,transparency_outputs,governance_stability "
        f"artifact={OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
