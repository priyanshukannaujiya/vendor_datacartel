"""
Alerts router for critical quality deviations, high risk batches, and certification expirations.
"""
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.models.batch import Batch
from app.models.vendor import Vendor
from app.models.intelligence import BatchIntelligence

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("")
def list_alerts(db: Session = Depends(get_db)):
    """
    Returns active alerts for quality leads and plant managers.
    """
    alerts = []

    # High risk vendors
    high_risk_vendors = (
        db.query(Vendor)
        .filter(Vendor.risk_score >= 50.0, Vendor.deleted_at.is_(None))
        .all()
    )
    for v in high_risk_vendors:
        alerts.append({
            "id": f"alert-v-{v.id}",
            "severity": "CRITICAL" if (v.risk_score or 0) >= 75 else "WARNING",
            "title": f"Elevated Supplier Risk: {v.vendor_name}",
            "description": f"Vendor risk score increased to {v.risk_score}/100 based on historical batch performance.",
            "source_type": "VENDOR",
            "source_id": str(v.id),
            "created_at": v.updated_at.isoformat() if v.updated_at else None,
        })

    # Rejected or needs review batches
    flagged_batches = (
        db.query(Batch)
        .filter(Batch.status.in_(["REJECTED", "NEEDS_REVIEW"]))
        .order_by(desc(Batch.created_at))
        .limit(10)
        .all()
    )
    for b in flagged_batches:
        vendor_name = b.vendor.vendor_name if b.vendor else "Unknown Vendor"
        alerts.append({
            "id": f"alert-b-{b.id}",
            "severity": "CRITICAL" if b.status == "REJECTED" else "INFO",
            "title": f"Batch {b.batch_number} {b.status}",
            "description": f"Batch from {vendor_name} flagged as {b.status}. Immediate inspection required.",
            "source_type": "BATCH",
            "source_id": str(b.id),
            "created_at": b.created_at.isoformat() if b.created_at else None,
        })

    return {"items": alerts, "total": len(alerts)}
