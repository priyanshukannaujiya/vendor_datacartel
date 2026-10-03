"""
Batch service functions and shared status update helper.
Follows VendorIQ PRD Section 16 & 36.
"""
from typing import Optional, Union
from uuid import UUID
from sqlalchemy.orm import Session
from app.models.batch import Batch
from app.core.errors import NotFoundError, BadRequestError

ALLOWED_STATUSES = {
    "RECEIVED",
    "PROCESSING",
    "VALIDATED",
    "PREDICTED",
    "APPROVED",
    "REJECTED",
    "NEEDS_REVIEW",
    "FAILED",
}


def update_batch_status(
    db: Session,
    batch_id: Union[str, UUID],
    status: str,
    reason: Optional[str] = None,
) -> Batch:
    """
    Shared helper to transition batch status across lifecycle stages.
    Used by Dev 1 (CRUD), Dev 2 (Analysis pipeline), and Dev 3 (Decision engine).
    """
    if status not in ALLOWED_STATUSES:
        raise BadRequestError(f"Invalid status '{status}'. Must be one of: {sorted(list(ALLOWED_STATUSES))}")

    import uuid
    if isinstance(batch_id, str):
        try:
            batch_uuid = uuid.UUID(batch_id)
        except Exception:
            batch_uuid = batch_id
    else:
        batch_uuid = batch_id

    batch = db.query(Batch).filter(Batch.id == batch_uuid).first()
    if not batch:
        raise NotFoundError(f"Batch with ID '{batch_id}' not found")

    batch.status = status
    if status == "FAILED" and reason:
        batch.failure_reason = reason
    elif reason:
        batch.failure_reason = reason

    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch
