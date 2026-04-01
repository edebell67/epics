from __future__ import annotations

from pathlib import Path
import shutil
import uuid

from fastapi.testclient import TestClient

from workstream.apps.task_review.app import create_app


def _tmp_root() -> Path:
    root = Path(__file__).resolve().parent / "_tmp_task_review" / uuid.uuid4().hex
    root.mkdir(parents=True, exist_ok=True)
    return root


def _write_task(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _task_body(title: str, workstream: str, epic: str, priority: int = 1) -> str:
    return f"""# {title}

**Workstream:** {workstream}
**Epic:** {epic}
**Priority:** {priority}

## Purpose

Purpose text

## Input

Input text

## Output

Output text

## Verification

Verification text
"""


def test_epics_endpoint_lists_available_epics() -> None:
    root = _tmp_root() / "workstream"
    _write_task(
        root / "100_todo" / "20260309_120020_autonomous_trading_signal_platform_workstreamC_create_api_server.md",
        _task_body("TASK C1: Create API Server", "C - API LAYER", "Autonomous Trading Signal Platform", 1),
    )
    try:
        client = TestClient(create_app(root))
        response = client.get("/api/epics")
        assert response.status_code == 200
        payload = response.json()
        assert payload["epics"][0]["slug"] == "autonomous_trading_signal_platform"
        assert payload["epics"][0]["task_count"] == 1
    finally:
        shutil.rmtree(root.parent, ignore_errors=True)


def test_epic_tasks_endpoint_filters_and_extracts_detail_fields() -> None:
    root = _tmp_root() / "workstream"
    _write_task(
        root / "100_todo" / "20260309_120020_autonomous_trading_signal_platform_workstreamC_create_api_server.md",
        _task_body("TASK C1: Create API Server", "C - API LAYER", "Autonomous Trading Signal Platform", 1),
    )
    _write_task(
        root / "200_inprogress" / "claude" / "20260309_120021_autonomous_trading_signal_platform_workstreamD_other.md",
        _task_body("TASK D1: Other", "D - MARKETING", "Autonomous Trading Signal Platform", 2),
    )
    try:
        client = TestClient(create_app(root))
        response = client.get("/api/epics/autonomous_trading_signal_platform/tasks?workstream=C&priority=1")
        assert response.status_code == 200
        tasks = response.json()["tasks"]
        assert len(tasks) == 1
        assert tasks[0]["task_id"] == "C1"
        assert tasks[0]["purpose"] == "Purpose text"
        assert tasks[0]["status_folder"] == "100_todo"
    finally:
        shutil.rmtree(root.parent, ignore_errors=True)


def test_allocate_moves_tasks_into_target_model_folder() -> None:
    root = _tmp_root() / "workstream"
    task_path = root / "100_todo" / "20260309_120020_autonomous_trading_signal_platform_workstreamC_create_api_server.md"
    _write_task(task_path, _task_body("TASK C1: Create API Server", "C - API LAYER", "Autonomous Trading Signal Platform", 1))
    try:
        client = TestClient(create_app(root))
        response = client.post("/api/tasks/allocate", json={"task_paths": [str(task_path)], "target_model": "codex"})
        assert response.status_code == 200
        moved_path = root / "100_todo" / "codex" / task_path.name
        assert moved_path.exists()
        assert response.json()["success"][0]["dest"] == str(moved_path)
    finally:
        shutil.rmtree(root.parent, ignore_errors=True)


def test_reject_moves_task_to_failed_and_appends_reason() -> None:
    root = _tmp_root() / "workstream"
    task_path = root / "200_inprogress" / "claude" / "20260309_120021_autonomous_trading_signal_platform_workstreamD_other.md"
    _write_task(task_path, _task_body("TASK D1: Other", "D - MARKETING", "Autonomous Trading Signal Platform", 2))
    try:
        client = TestClient(create_app(root))
        response = client.post("/api/tasks/reject", json={"task_paths": [str(task_path)], "reason": "Duplicate scope"})
        assert response.status_code == 200
        rejected_path = root / "400_failed" / "claude" / task_path.name
        assert rejected_path.exists()
        assert "Rejection Reason: Duplicate scope" in rejected_path.read_text(encoding="utf-8")
        assert response.json()["success"][0]["dest"] == str(rejected_path)
    finally:
        shutil.rmtree(root.parent, ignore_errors=True)


def test_model_status_counts_only_model_todo_folders() -> None:
    root = _tmp_root() / "workstream"
    _write_task(
        root / "100_todo" / "gemini" / "20260309_120020_autonomous_trading_signal_platform_workstreamC_create_api_server.md",
        _task_body("TASK C1: Create API Server", "C - API LAYER", "Autonomous Trading Signal Platform", 1),
    )
    _write_task(
        root / "100_todo" / "codex" / "20260309_120021_autonomous_trading_signal_platform_workstreamI_dashboard.md",
        _task_body("TASK I1: Dashboard", "I - DASHBOARD", "Autonomous Trading Signal Platform", 1),
    )
    try:
        client = TestClient(create_app(root))
        response = client.get("/api/models/status")
        assert response.status_code == 200
        counts = {item["model"]: item["count"] for item in response.json()["models"]}
        assert counts == {"gemini": 1, "claude": 0, "codex": 1}
    finally:
        shutil.rmtree(root.parent, ignore_errors=True)
