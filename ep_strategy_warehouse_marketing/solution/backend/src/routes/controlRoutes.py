from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..models.database import get_db
from ..schemas.control_schema import (
    EmergencyStopRequest,
    InterventionLogResponse,
    KillSwitchStatusResponse,
    ManualControlResponse,
    PauseRequest,
    QueueActionResponse,
    QueueApprovalRequest,
    QueueItemResponse,
)
from ..services.killSwitchService import KillSwitchService
from ..services.contentQueueService import ContentQueueService


router = APIRouter(
    prefix="/controls",
    tags=["controls"],
    responses={404: {"description": "Not found"}},
)


@router.get("/status", response_model=KillSwitchStatusResponse)
def get_control_status(db: Session = Depends(get_db)):
    service = KillSwitchService(db)
    return service.get_status_snapshot()


@router.get("/queue", response_model=list[QueueItemResponse])
def list_queue_items(status: str | None = None, platform: str | None = None, db: Session = Depends(get_db)):
    service = ContentQueueService(db)
    return service.get_queue_state(status=status, platform=platform)


@router.post("/pause/global", response_model=ManualControlResponse, status_code=status.HTTP_200_OK)
def set_global_pause(payload: PauseRequest, db: Session = Depends(get_db)):     
    service = KillSwitchService(db)
    return service.set_global_pause(payload.paused, payload.actor, payload.reason)


@router.post("/pause/platform/{platform}", response_model=ManualControlResponse, status_code=status.HTTP_200_OK)
def set_platform_pause(platform: str, payload: PauseRequest, db: Session = Depends(get_db)):
    service = KillSwitchService(db)
    return service.set_platform_pause(platform, payload.paused, payload.actor, payload.reason)


@router.post("/emergency-stop", status_code=status.HTTP_200_OK)
def trigger_emergency_stop(payload: EmergencyStopRequest, db: Session = Depends(get_db)):
    service = KillSwitchService(db)
    result = service.trigger_emergency_stop(payload.actor, payload.mode, payload.reason)
    return {
        "scope": "global",
        "status": "emergency_stop_active",
        "mode": result["mode"],
        "affected_items": result["affected_items"],
    }


@router.post("/queue/{queue_id}/approve", response_model=QueueActionResponse, status_code=status.HTTP_200_OK)
def approve_queue_item(queue_id: int, payload: QueueApprovalRequest, db: Session = Depends(get_db)):
    service = KillSwitchService(db)
    try:
        item = service.approve_queue_item(queue_id, payload.actor, payload.reason)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return QueueActionResponse(queue_id=item.id, status=item.status.value, detail="Queue item approved")


@router.post("/queue/{queue_id}/reject", response_model=QueueActionResponse, status_code=status.HTTP_200_OK)
def reject_queue_item(queue_id: int, payload: QueueApprovalRequest, db: Session = Depends(get_db)):
    service = KillSwitchService(db)
    try:
        item = service.reject_queue_item(queue_id, payload.actor, payload.reason)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return QueueActionResponse(queue_id=item.id, status=item.status.value, detail="Queue item rejected")


@router.get("/interventions", response_model=list[InterventionLogResponse])     
def list_interventions(db: Session = Depends(get_db)):
    service = KillSwitchService(db)
    return service.get_intervention_logs()
