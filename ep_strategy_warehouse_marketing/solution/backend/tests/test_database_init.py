import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from uuid import uuid4


def _run_init_script(database_path: Path) -> subprocess.CompletedProcess[str]:
    backend_dir = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{database_path.as_posix()}"
    return subprocess.run(
        [sys.executable, "-m", "src.scripts.init_database"],
        cwd=backend_dir,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )


def _workspace_temp_dir() -> Path:
    temp_dir = Path(__file__).resolve().parents[3] / "verification" / f"db-init-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def test_database_initialization_creates_core_tables_and_seed_data():
    database_path = _workspace_temp_dir() / "marketing_engine.db"
    result = _run_init_script(database_path)

    assert "Initialized database at sqlite:///" in result.stdout

    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert {"subscribers", "content_queue", "content_variants", "engagement_metrics", "account_metrics"} <= tables

        views = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='view'"
            )
        }
        assert {"subscriber_growth_snapshot", "content_performance_snapshot"} <= views

        subscriber_count = connection.execute("SELECT COUNT(*) FROM subscribers").fetchone()[0]
        queue_count = connection.execute("SELECT COUNT(*) FROM content_queue").fetchone()[0]
        variant_count = connection.execute("SELECT COUNT(*) FROM content_variants").fetchone()[0]
        metric_count = connection.execute("SELECT COUNT(*) FROM engagement_metrics").fetchone()[0]

        assert subscriber_count >= 3
        assert queue_count >= 2
        assert variant_count >= 2
        assert metric_count >= 2


def test_database_initialization_is_idempotent():
    database_path = _workspace_temp_dir() / "marketing_engine.db"

    _run_init_script(database_path)
    _run_init_script(database_path)

    with sqlite3.connect(database_path) as connection:
        subscriber_count = connection.execute("SELECT COUNT(*) FROM subscribers").fetchone()[0]
        queue_count = connection.execute("SELECT COUNT(*) FROM content_queue").fetchone()[0]
        variant_count = connection.execute("SELECT COUNT(*) FROM content_variants").fetchone()[0]
        account_metric_count = connection.execute("SELECT COUNT(*) FROM account_metrics").fetchone()[0]

        assert subscriber_count == 3
        assert queue_count == 2
        assert variant_count == 2
        assert account_metric_count == 2
