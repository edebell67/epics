from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from ..models.ContentQueue import ContentQueue, QueueStatus
from ..models.ManualControl import InterventionLog, ManualControl


class KillSwitchService:
    GLOBAL_SCOPE = ("global", "all")

    def __init__(self, db: Session):
        self.db = db
        self.logger = logging.getLogger("KillSwitchService")

    def get_or_create_control(self, scope_type: str, scope_key: str) -> ManualControl:
        control = (
            self.db.query(ManualControl)
            .filter(ManualControl.scope_type == scope_type, ManualControl.scope_key == scope_key)
            .first()
        )
        if control:
            return control

        control = ManualControl(scope_type=scope_type, scope_key=scope_key)
        self.db.add(control)
        self.db.commit()
        self.db.refresh(control)
        return control

    def get_status_snapshot(self) -> dict[str, Any]:
        global_control = self.get_or_create_control(*self.GLOBAL_SCOPE)
        platform_controls = (
            self.db.query(ManualControl)
            .filter(ManualControl.scope_type == "platform")
            .order_by(ManualControl.scope_key.asc())
            .all()
        )
        pending_approvals = [
            row[0]
            for row in self.db.query(ContentQueue.id)
            .filter(ContentQueue.status == QueueStatus.APPROVAL_PENDING)
            .order_by(ContentQueue.id.asc())
            .all()
        ]
        return {
            "global_control": global_control,
            "platform_controls": platform_controls,
            "pending_approvals": pending_approvals,
            "emergency_stop_active": bool(global_control.emergency_stop_active),
        }

    def is_dispatch_allowed(self, platform: str) -> tuple[bool, str | None]:
        global_control = self.get_or_create_control(*self.GLOBAL_SCOPE)
        if global_control.emergency_stop_active:
            return False, f"emergency_stop:{global_control.emergency_mode or 'freeze'}"
        if global_control.is_paused:
            return False, "global_pause"

        platform_control = self.get_or_create_control("platform", platform)
        if platform_control.is_paused:
            return False, f"platform_pause:{platform}"

        return True, None

    def set_global_pause(self, paused: bool, actor: str, reason: str | None = None) -> ManualControl:
        control = self.get_or_create_control(*self.GLOBAL_SCOPE)
        control.is_paused = paused
        if not paused:
            control.emergency_stop_active = False
            control.emergency_mode = None
        control.reason = reason
        control.updated_by = actor
        self.db.commit()
        self.db.refresh(control)
        self._log_action("global_pause_set" if paused else "global_pause_cleared", "global", "all", actor, reason)
        return control

    def set_platform_pause(self, platform: str, paused: bool, actor: str, reason: str | None = None) -> ManualControl:
        control = self.get_or_create_control("platform", platform)
        control.is_paused = paused
        control.reason = reason
        control.updated_by = actor
        self.db.commit()
        self.db.refresh(control)
        self._log_action("platform_pause_set" if paused else "platform_pause_cleared", "platform", platform, actor, reason)
        return control

    def trigger_emergency_stop(self, actor: str, mode: str = "freeze", reason: str | None = None) -> dict[str, Any]:
        control = self.get_or_create_control(*self.GLOBAL_SCOPE)
        control.is_paused = True
        control.emergency_stop_active = True
        control.emergency_mode = mode
        control.reason = reason
        control.updated_by = actor

        affected = 0
        items = self.db.query(ContentQueue).filter(
            ContentQueue.status.in_(
                [
                    QueueStatus.PENDING,
                    QueueStatus.FAILED,
                    QueueStatus.IN_PROGRESS,
                    QueueStatus.APPROVAL_PENDING,
                ]
            )
        ).all()

        if mode == "clear":
            for item in items:
                item.status = QueueStatus.CANCELED
                affected += 1
        else:
            affected = len(items)

        self.db.commit()
        self.db.refresh(control)
        self._log_action(
            "emergency_stop_triggered",
            "global",
            "all",
            actor,
            reason,
            {"mode": mode, "affected_items": affected},
        )
        return {"control": control, "affected_items": affected, "mode": mode}

    def approve_queue_item(self, queue_id: int, actor: str, reason: str | None = None) -> ContentQueue:
        item = self._get_queue_item(queue_id)
        if item.status != QueueStatus.APPROVAL_PENDING:
            raise ValueError(f"Queue item {queue_id} is not awaiting approval")

        dispatch_allowed, block_reason = self.is_dispatch_allowed(item.platform)
        item.status = QueueStatus.PAUSED if not dispatch_allowed else QueueStatus.PENDING
        self.db.commit()
        self.db.refresh(item)
        self._log_action(
            "queue_item_approved",
            "queue_item",
            str(queue_id),
            actor,
            reason,
            {"resulting_status": item.status.value, "block_reason": block_reason},
            target_queue_id=queue_id,
        )
        return item

    def reject_queue_item(self, queue_id: int, actor: str, reason: str | None = None) -> ContentQueue:
        item = self._get_queue_item(queue_id)
        item.status = QueueStatus.CANCELED
        self.db.commit()
        self.db.refresh(item)
        self._log_action("queue_item_rejected", "queue_item", str(queue_id), actor, reason, target_queue_id=queue_id)
        return item

    def get_intervention_logs(self) -> list[InterventionLog]:
        return self.db.query(InterventionLog).order_by(InterventionLog.created_at.desc(), InterventionLog.id.desc()).all()

    def _get_queue_item(self, queue_id: int) -> ContentQueue:
        item = self.db.query(ContentQueue).filter(ContentQueue.id == queue_id).first()
        if not item:
            raise ValueError(f"Queue item {queue_id} was not found")
        return item

    def _log_action(
        self,
        action: str,
        scope_type: str,
        scope_key: str,
        actor: str,
        reason: str | None,
        metadata: dict[str, Any] | None = None,
        target_queue_id: int | None = None,
    ) -> None:
        entry = InterventionLog(
            action=action,
            scope_type=scope_type,
            scope_key=scope_key,
            actor=actor,
            reason=reason,
            target_queue_id=target_queue_id,
            metadata_json=json.dumps(metadata) if metadata else None,
        )
        self.db.add(entry)
        self.db.commit()
