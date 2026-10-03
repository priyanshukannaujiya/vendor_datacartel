"""
Email events tracking and retry router for VendorIQ.
Follows Developer 3 specifications, unified with Neon PostgreSQL UUID schema.
"""
from typing import Optional, List, Any
from uuid import UUID
from datetime import datetime, timezone
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.models.decision import EmailEvent
from app.services.email_service import EmailDeliveryError, send_email
from app.services.audit_service import record_audit_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/email-events", tags=["Email Events"])


class EmailRetryResponse(BaseModel):
    id: str
    status: str
    error_message: Optional[str] = None


@router.get("")
def list_email_events(
    batch_id: Optional[UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(EmailEvent)
    if batch_id:
        query = query.filter(EmailEvent.batch_id == batch_id)
    if status_filter:
        query = query.filter(EmailEvent.status == status_filter.upper())

    total = query.count()
    events = (
        query.order_by(desc(EmailEvent.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = []
    for e in events:
        items.append({
            "id": str(e.id),
            "batch_id": str(e.batch_id),
            "vendor_id": str(e.vendor_id),
            "decision_id": str(e.decision_id) if e.decision_id else None,
            "recipient_email": e.recipient_email,
            "subject": e.subject,
            "email_type": e.email_type,
            "status": e.status,
            "provider": e.provider,
            "sent_at": e.sent_at.isoformat() if e.sent_at else None,
            "error_message": e.error_message,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/{event_id}/retry", response_model=EmailRetryResponse)
def retry_email_event(
    event_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Retries delivery of a FAILED email event using Google SMTP.
    """
    event = db.query(EmailEvent).filter(EmailEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Email event not found.")

    if event.status not in ["FAILED", "PENDING"]:
        raise HTTPException(
            status_code=409,
            detail=f"Only FAILED or PENDING email events can be retried; current status is {event.status}."
        )

    try:
        send_email(
            recipient=event.recipient_email,
            subject=event.subject,
            html_content=event.html_content,
            text_content=event.text_content,
        )
        event.status = "SENT"
        event.sent_at = datetime.now(timezone.utc)
        event.error_message = None
        record_audit_event(
            db,
            "Email Sent",
            company_id=event.company_id,
            vendor_id=event.vendor_id,
            batch_id=event.batch_id,
            details={"email_event_id": str(event.id), "email_type": event.email_type, "retried": True},
        )
    except EmailDeliveryError as exc:
        event.status = "FAILED"
        event.error_message = str(exc)
        logger.error(f"Retry failed for email event {event.id}: {exc}")

    db.commit()
    db.refresh(event)

    return EmailRetryResponse(
        id=str(event.id),
        status=event.status,
        error_message=event.error_message,
    )
