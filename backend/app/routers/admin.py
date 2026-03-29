from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_current_user_id, get_db
from ..models import AdminAction
from ..schemas import AdminActionAccepted, AdminActionRequest, AdminActionResult
from ..services.audit import write_audit

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/actions", response_model=AdminActionAccepted, status_code=202)
def create_admin_action(
    payload: AdminActionRequest,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
) -> AdminActionAccepted:
    action = AdminAction(
        action_type=payload.action.value,
        status="queued",
        requested_by=current_user_id,
        params_json=payload.model_dump(mode="json", exclude_none=True),
        summary="Accepted for execution",
        started_at=datetime.utcnow(),
    )
    db.add(action)
    db.commit()
    db.refresh(action)

    write_audit(
        db,
        actor_user_id=current_user_id,
        event_type="admin.action.create",
        entity_type="admin_action",
        entity_id=action.id,
        status="success",
        metadata={"action": action.action_type},
    )

    return AdminActionAccepted(action_id=action.id, status=action.status)


@router.get("/actions/{action_id}", response_model=AdminActionResult)
def get_admin_action(
    action_id: str,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
) -> AdminActionResult:
    action = db.query(AdminAction).filter(AdminAction.id == action_id).first()
    if not action:
        write_audit(
            db,
            actor_user_id=current_user_id,
            event_type="admin.action.read",
            entity_type="admin_action",
            entity_id=action_id,
            status="failed",
        )
        raise HTTPException(status_code=404, detail="Action not found")

    write_audit(
        db,
        actor_user_id=current_user_id,
        event_type="admin.action.read",
        entity_type="admin_action",
        entity_id=action.id,
        status="success",
    )
    return AdminActionResult(
        action_id=action.id,
        action=action.action_type,
        status=action.status,
        started_at=action.started_at,
        finished_at=action.finished_at,
        exit_code=action.exit_code,
        summary=action.summary,
        output=action.output_log,
    )
