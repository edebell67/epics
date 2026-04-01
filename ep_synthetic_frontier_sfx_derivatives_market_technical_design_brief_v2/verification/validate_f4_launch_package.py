from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "deploy"

RUNBOOK_PATH = DEPLOY / "f4_mvp_launch_runbook.md"
CHECKLIST_PATH = DEPLOY / "f4_mvp_readiness_checklist.json"
DEPENDENCY_PATH = DEPLOY / "f4_dependency_register.csv"
DECISION_MEMO_PATH = DEPLOY / "f4_go_no_go_decision_memo.md"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _load_text(path: Path) -> str:
    _assert(path.exists(), f"missing_file:{path}")
    return path.read_text(encoding="utf-8")


def validate_runbook() -> None:
    text = _load_text(RUNBOOK_PATH)
    required_sections = [
        "## Startup Procedure",
        "## Runtime Monitoring Procedure",
        "## Halt Procedure",
        "## Reopen Procedure",
        "## Incident Escalation Procedure",
    ]
    for section in required_sections:
        _assert(section in text, f"missing_runbook_section:{section}")


def validate_checklist() -> int:
    data = json.loads(_load_text(CHECKLIST_PATH))
    _assert(data["decision_status"] in {"go", "conditional_go", "no_go"}, "invalid_decision_status")
    required_fields = {
        "prelaunch_check",
        "runtime_monitor",
        "halt_procedure",
        "reopen_procedure",
        "owner",
        "evidence_link",
    }
    checklist = data["checklist"]
    _assert(len(checklist) >= 6, "insufficient_checklist_items")
    for item in checklist:
        _assert(required_fields.issubset(item), f"missing_checklist_fields:{item.get('check_id', 'unknown')}")
        evidence_path = Path(item["evidence_link"])
        _assert(evidence_path.exists(), f"missing_evidence_link:{evidence_path}")
    return len(checklist)


def validate_dependency_register() -> int:
    with DEPENDENCY_PATH.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    expected = {"E1", "E2", "E3", "F1", "F2", "F3"}
    actual = {row["dependency_id"] for row in rows}
    _assert(actual == expected, f"dependency_mismatch:{sorted(actual)}")
    for row in rows:
        evidence_path = Path(row["evidence_link"])
        _assert(evidence_path.exists(), f"missing_dependency_evidence:{evidence_path}")
    return len(rows)


def validate_decision_memo() -> str:
    text = _load_text(DECISION_MEMO_PATH)
    _assert("Decision: `no_go`" in text or "Decision: `go`" in text or "Decision: `conditional_go`" in text, "missing_decision")
    required_markers = [
        "Configuration evidence link:",
        "Governance evidence link:",
        "Transparency evidence link:",
        "Shock-test evidence link:",
        "## Blocking Findings",
        "## Required Exit Criteria To Move To Go",
    ]
    for marker in required_markers:
        _assert(marker in text, f"missing_decision_marker:{marker}")
    if "Decision: `no_go`" in text:
        return "no_go"
    if "Decision: `conditional_go`" in text:
        return "conditional_go"
    return "go"


def main() -> None:
    validate_runbook()
    checklist_items = validate_checklist()
    dependency_rows = validate_dependency_register()
    decision = validate_decision_memo()
    print(
        f"f4_launch_package_ok decision={decision} "
        f"checklist_items={checklist_items} dependencies={dependency_rows}"
    )


if __name__ == "__main__":
    main()
