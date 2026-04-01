import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
import yaml


os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.services.healthMonitorService import HealthMonitorService


class StubConnector:
    def __init__(self, healthy: bool):
        self.healthy = healthy

    def verify_auth(self) -> bool:
        return self.healthy


class CapturingChannel:
    name = "capture"

    def __init__(self):
        self.alerts = []

    def send(self, alert) -> None:
        self.alerts.append(alert)


@pytest.fixture
def custom_config_path() -> Path:
    config = {
        "monitoring": {
            "scheduler": {
                "heartbeat_interval_seconds": 10,
                "max_missed_heartbeats": 3,
            },
            "connectors": {
                "enabled": True,
                "check_interval_seconds": 0,
                "platforms": ["twitter"],
            },
            "queue": {
                "enabled": True,
                "max_depth_warning": 5,
                "max_depth_critical": 10,
                "tracked_statuses": ["pending", "failed"],
            },
        },
        "alerting": {
            "dedupe_cooldown_seconds": 600,
            "channels": {
                "logging": {"enabled": False},
                "email": {"enabled": False, "recipients": []},
                "webhook": {"enabled": False, "url": ""},
            },
        },
    }
    config_dir = Path(__file__).parent / "_generated"
    config_dir.mkdir(exist_ok=True)
    config_path = config_dir / f"alerting_{uuid4().hex}.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    try:
        yield config_path
    finally:
        if config_path.exists():
            config_path.unlink()


def test_scheduler_heartbeat_alert_triggers_when_heartbeat_stops(custom_config_path: Path):
    channel = CapturingChannel()
    service = HealthMonitorService(
        config_path=str(custom_config_path),
        notification_channels=[channel],
    )
    now = datetime(2026, 3, 21, 12, 0, tzinfo=UTC)
    service.record_scheduler_heartbeat(now - timedelta(seconds=45))

    alerts = service.run_checks(now=now)

    assert len(alerts) == 1
    assert alerts[0].rule_name == "scheduler_down"
    assert alerts[0].severity == "critical"
    assert channel.alerts[0].details["heartbeat_age_seconds"] == 45


def test_connector_failure_and_backlog_thresholds_are_detected(custom_config_path: Path):
    channel = CapturingChannel()
    service = HealthMonitorService(
        config_path=str(custom_config_path),
        connectors={"twitter": StubConnector(healthy=False)},
        queue_depth_provider=lambda: 7,
        notification_channels=[channel],
    )
    now = datetime(2026, 3, 21, 12, 0, tzinfo=UTC)
    service.record_scheduler_heartbeat(now)

    alerts = service.run_checks(now=now)
    alert_rules = {(alert.rule_name, alert.severity) for alert in alerts}

    assert ("connector_auth_failure", "high") in alert_rules
    assert ("queue_backlog", "warning") in alert_rules
    assert len(channel.alerts) == 2


def test_normal_operation_does_not_emit_repeated_false_positives(custom_config_path: Path):
    channel = CapturingChannel()
    service = HealthMonitorService(
        config_path=str(custom_config_path),
        connectors={"twitter": StubConnector(healthy=True)},
        queue_depth_provider=lambda: 1,
        notification_channels=[channel],
    )
    now = datetime(2026, 3, 21, 12, 0, tzinfo=UTC)
    service.record_scheduler_heartbeat(now)

    first_alerts = service.run_checks(now=now)
    second_alerts = service.run_checks(now=now + timedelta(seconds=30))

    assert first_alerts == []
    assert second_alerts == []
    assert channel.alerts == []
    assert service.alert_history == []


def test_configuration_supports_thresholds_and_channel_toggles(custom_config_path: Path):
    service = HealthMonitorService(config_path=str(custom_config_path))

    assert service.config["monitoring"]["queue"]["max_depth_warning"] == 5
    assert service.config["monitoring"]["queue"]["max_depth_critical"] == 10
    assert service.config["monitoring"]["scheduler"]["heartbeat_interval_seconds"] == 10
    assert service.channel_names == []
