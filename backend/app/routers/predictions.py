"""
Predictions router returning ML risk predictions, risk distribution, and feature inferences.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.models.intelligence import BatchIntelligence
from app.models.batch import Batch
from app.models.vendor import Vendor
from app.models.raw_material import RawMaterial

router = APIRouter(prefix="/predictions", tags=["Predictions"])


@router.get("")
def list_predictions(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = (
        db.query(BatchIntelligence)
        .filter(BatchIntelligence.ml_prediction.isnot(None))
        .order_by(desc(BatchIntelligence.created_at))
    )
    total = query.count()
    records = query.offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for r in records:
        batch = db.query(Batch).filter(Batch.id == r.batch_id).first()
        pred = r.ml_prediction or {}
        items.append({
            "id": str(r.id),
            "batch_id": str(r.batch_id),
            "batch_number": batch.batch_number if batch else "Unknown",
            "vendor_name": batch.vendor.vendor_name if (batch and batch.vendor) else "Unknown",
            "raw_material_name": batch.raw_material.name if (batch and batch.raw_material) else "Unknown",
            "risk_score": pred.get("risk_score", 0.0),
            "risk_probability": pred.get("risk_probability", 0.0),
            "risk_level": pred.get("risk_level", "LOW"),
            "risk_factors": pred.get("risk_factors", []),
            "features_used": r.ml_features or {},
            "kimi_status": r.kimi_status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
