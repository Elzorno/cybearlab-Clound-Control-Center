from sqlalchemy.orm import Session

from ..models import AuditEvent


def write_audit(
    db: Session,
    *,
    actor_user_id: str | None,
    event_type: str,
    entity_type: str,
    entity_id: str | None,
    status: str,
    metadata: dict | None = None,
) -> AuditEvent:
    event = AuditEvent(
        actor_user_id=actor_user_id,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        status=status,
        metadata_json=metadata or {},
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
