"""
Predictions router returning ML risk predictions, risk distribution, and feature inferences.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, or_
import logging

from app.core.database import get_db
from app.models.intelligence import BatchIntelligence
from app.models.batch import Batch
from app.models.vendor import Vendor
from app.models.raw_material import RawMaterial

router = APIRouter(prefix="/predictions", tags=["Predictions"])
logger = logging.getLogger(__name__)


@router.get("")
def list_predictions(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    # Auto-generate intelligence for any batch lacking ml_prediction
    batches_without_pred = (
        db.query(Batch)
        .options(joinedload(Batch.vendor), joinedload(Batch.raw_material))
        .outerjoin(BatchIntelligence, Batch.id == BatchIntelligence.batch_id)
        .filter(or_(BatchIntelligence.id.is_(None), BatchIntelligence.ml_prediction.is_(None)))
        .order_by(desc(Batch.created_at))
        .limit(5)
        .all()
    )
    if batches_without_pred:
        from app.services.validation_service import BatchValidationService
        from app.services.vendor_history_service import VendorHistoryService
        from app.services.prediction_service import BatchRiskPredictionService
        from app.services.kimi_service import KimiReasoningService
        from app.models.document import Document
        from app.schemas.document import DocumentProcessResult, DocumentType

        val_svc = BatchValidationService()
        hist_svc = VendorHistoryService()
        pred_svc = BatchRiskPredictionService()
        kimi_svc = KimiReasoningService()

        for b in batches_without_pred:
            try:
                material = b.raw_material
                vendor = b.vendor
                docs = db.query(Document).filter(Document.batch_id == b.id).all()
                proc_docs = [
                    DocumentProcessResult(
                        document_id=d.id,
                        filename=d.file_name,
                        document_type=DocumentType(d.document_type) if d.document_type in DocumentType.__members__ else DocumentType.OTHER,
                        status=d.processing_status,
                        extracted_data=d.extracted_data or {},
                    )
                    for d in docs
                ]
                val_res = val_svc.validate_batch(b, material, vendor, proc_docs)
                v_hist = hist_svc.analyze_vendor_history(db, b.vendor_id, b)
                pred_res, feat = pred_svc.predict_risk(b, material, vendor, val_res, v_hist, b.purity_reported)
                kimi_res = kimi_svc.generate_explanation(vendor, material, b, val_res, v_hist, pred_res)

                intel = db.query(BatchIntelligence).filter(BatchIntelligence.batch_id == b.id).first()
                if not intel:
                    intel = BatchIntelligence(batch_id=b.id)
                    db.add(intel)
                intel.validation_result = val_res.model_dump(mode="json")
                intel.vendor_history = v_hist.model_dump(mode="json")
                intel.ml_features = feat
                intel.ml_prediction = pred_res.model_dump(mode="json")
                intel.kimi_analysis = kimi_res.model_dump(mode="json")
                intel.kimi_status = kimi_res.kimi_status.value
                db.commit()
            except Exception as exc:
                logger.warning("Could not auto-generate prediction for batch %s: %s", b.id, exc)

    query = (
        db.query(BatchIntelligence)
        .filter(BatchIntelligence.ml_prediction.isnot(None))
        .order_by(desc(BatchIntelligence.created_at))
    )
    total = query.count()
    records = query.offset((page - 1) * page_size).limit(page_size).all()

    batch_ids = [r.batch_id for r in records if r.batch_id]
    batches_map = {}
    if batch_ids:
        batches_list = (
            db.query(Batch)
            .options(joinedload(Batch.vendor), joinedload(Batch.raw_material))
            .filter(Batch.id.in_(batch_ids))
            .all()
        )
        batches_map = {b.id: b for b in batches_list}

    items = []
    for r in records:
        batch = batches_map.get(r.batch_id)
        pred = r.ml_prediction or {}
        items.append({
            "id": str(r.id),
            "batch_id": str(r.batch_id),
            "batch_number": batch.batch_number if batch else "Unknown",
            "batch_status": batch.status if batch else "UNKNOWN",
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
