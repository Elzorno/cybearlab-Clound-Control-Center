from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..deps import get_current_user_id, get_db
from ..models import AuditEvent
from ..schemas import AuditEventResponse, AuditListResponse

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("/events", response_model=AuditListResponse)
def list_audit_events(
    actionType: str | None = None,
    actor: str | None = None,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
) -> AuditListResponse:
    query = db.query(AuditEvent)
    if actionType:
        query = query.filter(AuditEvent.event_type == actionType)
    if actor:
        query = query.filter(AuditEvent.actor_user_id == actor)

    events = query.order_by(AuditEvent.created_at.desc()).limit(500).all()
    items = [
        AuditEventResponse(
            id=e.id,
            actor=e.actor_user_id or "system",
            action_type=e.event_type,
            entity_id=e.entity_id,
            status=e.status,
            created_at=e.created_at,
        )
        for e in events
    ]

    return AuditListResponse(items=items)
