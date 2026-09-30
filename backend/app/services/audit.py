from sqlalchemy.orm import Session

from app.models import AuditEvent


def record_audit_event(
    session: Session,
    *,
    event_type: str,
    summary: str,
    entity_type: str = "",
    entity_id: str = "",
    details: dict | None = None,
) -> AuditEvent:
    event = AuditEvent(
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        summary=summary,
        details=details or {},
    )
    session.add(event)
    return event

