from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.decision import AuditEvent


def record_audit_event(
    db: Session,
    event_type: str,
    *,
    company_id: Optional[str] = None,
    vendor_id: Optional[int] = None,
    batch_id: Optional[int] = None,
    details: Optional[dict[str, Any]] = None,
    commit: bool = True,
) -> AuditEvent:
    event = AuditEvent(
        event_type=event_type,
        company_id=company_id,
        vendor_id=vendor_id,
        batch_id=batch_id,
        details=details or {},
    )
    db.add(event)
    if commit:
        db.commit()
        db.refresh(event)
    return event
