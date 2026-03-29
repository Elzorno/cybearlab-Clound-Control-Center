from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from ..deps import get_current_user_id, get_db
from ..models import AdminAction
from ..schemas import AdminActionAccepted, AdminActionRequest, AdminActionResult, UploadRosterResponse
from ..services.audit import write_audit
from ..services.admin_executor import execute_admin_action
from ..services.file_storage import save_roster_upload

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/uploads/roster", response_model=UploadRosterResponse)
def upload_roster(
    roster: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
) -> UploadRosterResponse:
    upload = save_roster_upload(db=db, uploader_id=current_user_id, file=roster)
    write_audit(
        db,
        actor_user_id=current_user_id,
        event_type="admin.upload.roster",
        entity_type="file_upload",
        entity_id=upload.id,
        status="success",
        metadata={"filename": upload.original_name, "size_bytes": upload.size_bytes},
    )
    return UploadRosterResponse(
        file_ref=upload.stored_path,
        original_name=upload.original_name,
        size_bytes=upload.size_bytes,
        sha256=upload.sha256 or "",
        content_type=upload.content_type,
    )


@router.post("/actions", response_model=AdminActionAccepted, status_code=202)
def create_admin_action(
    payload: AdminActionRequest,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
) -> AdminActionAccepted:
    action = AdminAction(action_type=payload.action.value, status="queued", requested_by=current_user_id)
    action.params_json = payload.model_dump(mode="json", exclude_none=True)
    db.add(action)
    db.commit()
    db.refresh(action)

    try:
        action.started_at = datetime.utcnow()
        result = execute_admin_action(payload)
        action.status = result.status
        action.exit_code = result.exit_code
        action.summary = result.summary
        action.output_log = result.output
        action.finished_at = datetime.utcnow()
        db.commit()
        db.refresh(action)
    except ValueError as exc:
        action.status = "failed"
        action.summary = "Validation failed"
        action.output_log = str(exc)
        action.finished_at = datetime.utcnow()
        db.commit()
        write_audit(
            db,
            actor_user_id=current_user_id,
            event_type="admin.action.create",
            entity_type="admin_action",
            entity_id=action.id,
            status="failed",
            metadata={"error": str(exc), "action": payload.action.value},
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    write_audit(
        db,
        actor_user_id=current_user_id,
        event_type="admin.action.create",
        entity_type="admin_action",
        entity_id=action.id,
        status="success" if action.status == "success" else "failed",
        metadata={"action": action.action_type, "result_status": action.status},
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
