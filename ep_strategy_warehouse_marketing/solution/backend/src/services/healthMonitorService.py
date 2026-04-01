"""
Health monitoring and alerting service for the autonomous marketing scheduler.
"""
from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Callable, Optional
from urllib import error, request

import yaml

from src.models.ContentQueue import QueueStatus


def get_utc_now() -> datetime:
    return datetime.now(UTC)


def _normalize_dt(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


@dataclass(frozen=True)
class AlertEvent:
    key: str
    rule_name: str
    severity: str
    message: str
    created_at: datetime
    details: dict[str, Any] = field(default_factory=dict)


class NotificationChannel:
    name = "base"

    def send(self, alert: AlertEvent) -> None:
        raise NotImplementedError


class LoggingNotificationChannel(NotificationChannel):
    name = "logging"

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def send(self, alert: AlertEvent) -> None:
        self.logger.warning(
            "Health alert [%s] %s: %s | details=%s",
            alert.severity.upper(),
            alert.rule_name,
            alert.message,
            alert.details,
        )


class EmailNotificationChannel(NotificationChannel):
    name = "email"

    def __init__(self, config: dict[str, Any], logger: logging.Logger):
        self.config = config
        self.logger = logger

    def send(self, alert: AlertEvent) -> None:
        recipients = self.config.get("recipients", [])
        if not recipients:
            self.logger.warning("Email alert channel enabled without recipients; skipping alert.")
            return

        message = EmailMessage()
        message["Subject"] = f"[{alert.severity.upper()}] {alert.rule_name}"
        message["From"] = self.config.get("sender", "marketing-engine@example.local")
        message["To"] = ", ".join(recipients)
        message.set_content(f"{alert.message}\n\nDetails: {alert.details}")

        host = self.config.get("host", "localhost")
        port = int(self.config.get("port", 25))
        timeout = int(self.config.get("timeout_seconds", 10))

        with smtplib.SMTP(host=host, port=port, timeout=timeout) as client:
            if self.config.get("starttls", False):
                client.starttls()
            username = self.config.get("username")
            password = self.config.get("password")
            if username and password:
                client.login(username, password)
            client.send_message(message)


class WebhookNotificationChannel(NotificationChannel):
    name = "webhook"

    def __init__(self, config: dict[str, Any], logger: logging.Logger):
        self.config = config
        self.logger = logger

    def send(self, alert: AlertEvent) -> None:
        webhook_url = self.config.get("url", "").strip()
        if not webhook_url:
            self.logger.warning("Webhook channel enabled without URL; skipping alert.")
            return

        payload = yaml.safe_dump(
            {
                "rule": alert.rule_name,
                "severity": alert.severity,
                "message": alert.message,
                "details": alert.details,
                "created_at": alert.created_at.isoformat(),
            }
        ).encode("utf-8")
        req = request.Request(
            webhook_url,
            data=payload,
            headers={"Content-Type": "application/x-yaml"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=int(self.config.get("timeout_seconds", 10))):
                return
        except error.URLError as exc:
            self.logger.error("Webhook notification failed for %s: %s", alert.rule_name, exc)


class HealthMonitorService:
    def __init__(
        self,
        config_path: str = "src/config/alerting_config.yaml",
        queue_service: Any | None = None,
        connectors: Optional[dict[str, Any]] = None,
        logger: Optional[logging.Logger] = None,
        notification_channels: Optional[list[NotificationChannel]] = None,
        queue_depth_provider: Optional[Callable[[], int]] = None,
    ):
        self.config_path = config_path
        self.queue_service = queue_service
        self.queue_depth_provider = queue_depth_provider
        self.connectors = connectors or {}
        self.logger = logger or logging.getLogger("HealthMonitorService")
        self.config = self._load_config()
        self.scheduler_last_heartbeat: Optional[datetime] = None
        self.last_connector_check: Optional[datetime] = None
        self.active_alerts: dict[str, datetime] = {}
        self.alert_history: list[AlertEvent] = []
        self._channels = notification_channels if notification_channels is not None else self._build_notification_channels()

    def _load_config(self) -> dict[str, Any]:
        default_config = {
            "monitoring": {
                "scheduler": {
                    "heartbeat_interval_seconds": 60,
                    "max_missed_heartbeats": 3,
                },
                "connectors": {
                    "enabled": True,
                    "check_interval_seconds": 300,
                    "platforms": [],
                },
                "queue": {
                    "enabled": True,
                    "max_depth_warning": 100,
                    "max_depth_critical": 500,
                    "tracked_statuses": [
                        QueueStatus.PENDING.value,
                        QueueStatus.APPROVAL_PENDING.value,
                        QueueStatus.IN_PROGRESS.value,
                        QueueStatus.FAILED.value,
                    ],
                },
            },
            "alerting": {
                "dedupe_cooldown_seconds": 1800,
                "channels": {
                    "logging": {"enabled": True},
                    "email": {"enabled": False, "recipients": []},
                    "webhook": {"enabled": False, "url": ""},
                },
            },
        }

        config_file = Path(self.config_path)
        if not config_file.exists():
            return default_config

        with config_file.open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle) or {}

        return _deep_merge(default_config, loaded)

    def _build_notification_channels(self) -> list[NotificationChannel]:
        channels: list[NotificationChannel] = []
        channel_config = self.config.get("alerting", {}).get("channels", {})

        if channel_config.get("logging", {}).get("enabled", True):
            channels.append(LoggingNotificationChannel(self.logger))
        if channel_config.get("email", {}).get("enabled", False):
            channels.append(EmailNotificationChannel(channel_config["email"], self.logger))
        if channel_config.get("webhook", {}).get("enabled", False):
            channels.append(WebhookNotificationChannel(channel_config["webhook"], self.logger))

        return channels

    @property
    def channel_names(self) -> list[str]:
        return [channel.name for channel in self._channels]

    def record_scheduler_heartbeat(self, heartbeat_time: Optional[datetime] = None) -> None:
        self.scheduler_last_heartbeat = _normalize_dt(heartbeat_time or get_utc_now())

    def run_checks(self, now: Optional[datetime] = None) -> list[AlertEvent]:
        current_time = _normalize_dt(now or get_utc_now()) or get_utc_now()
        alerts: list[AlertEvent] = []

        alerts.extend(self._check_scheduler_heartbeat(current_time))
        alerts.extend(self._check_connectors(current_time))
        alerts.extend(self._check_queue_depth(current_time))

        return alerts

    def _check_scheduler_heartbeat(self, now: datetime) -> list[AlertEvent]:
        if self.scheduler_last_heartbeat is None:
            alert = self._activate_alert(
                key="scheduler_down",
                rule_name="scheduler_down",
                severity="critical",
                message="Scheduler heartbeat has never been recorded.",
                now=now,
                details={"last_heartbeat": None},
            )
            return [alert] if alert else []

        scheduler_config = self.config["monitoring"]["scheduler"]
        max_gap_seconds = scheduler_config["heartbeat_interval_seconds"] * scheduler_config["max_missed_heartbeats"]
        heartbeat_age = (now - self.scheduler_last_heartbeat).total_seconds()
        if heartbeat_age > max_gap_seconds:
            alert = self._activate_alert(
                key="scheduler_down",
                rule_name="scheduler_down",
                severity="critical",
                message="Scheduler heartbeat exceeded the missed-heartbeat threshold.",
                now=now,
                details={
                    "last_heartbeat": self.scheduler_last_heartbeat.isoformat(),
                    "heartbeat_age_seconds": int(heartbeat_age),
                    "max_gap_seconds": max_gap_seconds,
                },
            )
            return [alert] if alert else []

        self.active_alerts.pop("scheduler_down", None)
        return []

    def _check_connectors(self, now: datetime) -> list[AlertEvent]:
        connector_config = self.config["monitoring"]["connectors"]
        if not connector_config.get("enabled", True):
            return []

        interval_seconds = int(connector_config.get("check_interval_seconds", 300))
        if self.last_connector_check and (now - self.last_connector_check).total_seconds() < interval_seconds:
            return []

        self.last_connector_check = now
        alerts: list[AlertEvent] = []
        configured_platforms = connector_config.get("platforms", [])
        platforms = configured_platforms or list(self.connectors.keys())

        active_connector_keys: set[str] = set()
        for platform in platforms:
            connector = self.connectors.get(platform)
            if connector is None:
                continue

            verify_auth = getattr(connector, "verify_auth", None)
            if not callable(verify_auth):
                continue

            alert_key = f"connector_auth_failure:{platform}"
            active_connector_keys.add(alert_key)

            try:
                is_healthy = bool(verify_auth())
            except Exception as exc:
                self.logger.error("Connector auth check failed for %s: %s", platform, exc)
                is_healthy = False

            if is_healthy:
                self.active_alerts.pop(alert_key, None)
                continue

            alert = self._activate_alert(
                key=alert_key,
                rule_name="connector_auth_failure",
                severity="high",
                message=f"Connector authentication failed for {platform}.",
                now=now,
                details={"platform": platform},
            )
            if alert:
                alerts.append(alert)

        stale_keys = [
            key
            for key in self.active_alerts
            if key.startswith("connector_auth_failure:") and key not in active_connector_keys
        ]
        for key in stale_keys:
            self.active_alerts.pop(key, None)

        return alerts

    def _check_queue_depth(self, now: datetime) -> list[AlertEvent]:
        queue_config = self.config["monitoring"]["queue"]
        if not queue_config.get("enabled", True):
            return []

        queue_depth = self._get_queue_depth()
        warning_threshold = int(queue_config.get("max_depth_warning", 100))
        critical_threshold = int(queue_config.get("max_depth_critical", 500))

        if queue_depth >= critical_threshold:
            self.active_alerts.pop("queue_backlog_warning", None)
            alert = self._activate_alert(
                key="queue_backlog_critical",
                rule_name="queue_backlog",
                severity="critical",
                message=f"Content queue backlog reached critical depth ({queue_depth} items).",
                now=now,
                details={"queue_depth": queue_depth, "threshold": critical_threshold},
            )
            return [alert] if alert else []

        self.active_alerts.pop("queue_backlog_critical", None)
        if queue_depth >= warning_threshold:
            alert = self._activate_alert(
                key="queue_backlog_warning",
                rule_name="queue_backlog",
                severity="warning",
                message=f"Content queue backlog reached warning depth ({queue_depth} items).",
                now=now,
                details={"queue_depth": queue_depth, "threshold": warning_threshold},
            )
            return [alert] if alert else []

        self.active_alerts.pop("queue_backlog_warning", None)
        return []

    def _get_queue_depth(self) -> int:
        if self.queue_depth_provider is not None:
            return int(self.queue_depth_provider())

        if self.queue_service is None:
            return 0

        if hasattr(self.queue_service, "get_backlog_depth"):
            return int(self.queue_service.get_backlog_depth())

        tracked_statuses = self.config["monitoring"]["queue"].get("tracked_statuses", [])
        queue_depth = 0
        for status in tracked_statuses:
            queue_depth += len(self.queue_service.get_queue_state(status=status))
        return queue_depth

    def _activate_alert(
        self,
        key: str,
        rule_name: str,
        severity: str,
        message: str,
        now: datetime,
        details: Optional[dict[str, Any]] = None,
    ) -> Optional[AlertEvent]:
        cooldown_seconds = int(self.config.get("alerting", {}).get("dedupe_cooldown_seconds", 1800))
        last_sent_at = self.active_alerts.get(key)
        if last_sent_at and (now - last_sent_at).total_seconds() < cooldown_seconds:
            return None

        alert = AlertEvent(
            key=key,
            rule_name=rule_name,
            severity=severity,
            message=message,
            created_at=now,
            details=details or {},
        )
        self.active_alerts[key] = now
        self.alert_history.append(alert)
        self._dispatch(alert)
        return alert

    def _dispatch(self, alert: AlertEvent) -> None:
        for channel in self._channels:
            try:
                channel.send(alert)
            except Exception as exc:
                self.logger.error(
                    "Alert dispatch failed on channel %s for %s: %s",
                    channel.name,
                    alert.rule_name,
                    exc,
                )


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
