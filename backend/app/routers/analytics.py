"""
Analytics and Dashboard router for VendorIQ.
Aggregates database statistics for KPI cards, risk distribution, trends, and risk tables with caching.
"""
import time
from typing import Optional, Dict, Any
from collections import defaultdict
from datetime import date, datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func

from app.core.database import get_db
from app.core.security import get_optional_current_user
from app.models.user import User
from app.models.vendor import Vendor
from app.models.batch import Batch
from app.models.intelligence import BatchIntelligence
from app.models.decision import EmailEvent

router = APIRouter(prefix="/analytics", tags=["Analytics"])

# High-performance per-company in-memory cache (45-second TTL with active invalidation)
_ANALYTICS_CACHE: Dict[str, Dict[str, Any]] = {}
_CACHE_TTL_SECONDS = 45.0


def invalidate_analytics_cache(company_id: Optional[Any] = None):
    """Call when new batch or prediction is persisted to bust analytics cache."""
    if company_id:
        _ANALYTICS_CACHE.pop(str(company_id), None)
    else:
        _ANALYTICS_CACHE.clear()


@router.get("")
def get_dashboard_analytics(
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns full analytics payload for the Vendor Intelligence Dashboard:
    KPI cards, 4 charts (Risk Distribution, Risk Trend, Batch Approval Trend, Quality Trend),
    and tables for High Risk Vendors and Recent Batch Assessments.
    Strictly scoped to current_user.company_id for multi-tenant isolation.
    """
    company_id_str = str(current_user.company_id) if current_user and current_user.company_id else "global"
    now = time.monotonic()
    cached = _ANALYTICS_CACHE.get(company_id_str)
    if cached and (now - cached["timestamp"] < _CACHE_TTL_SECONDS):
        return cached["data"]

    # 1. KPI Counts via fast SQL aggregations scoped to company
    vendor_count_q = db.query(func.count(Vendor.id)).filter(Vendor.deleted_at.is_(None))
    batch_count_q = db.query(Batch.status, func.count(Batch.id))

    if current_user and current_user.company_id:
        vendor_count_q = vendor_count_q.filter(Vendor.company_id == current_user.company_id)
        batch_count_q = batch_count_q.filter(Batch.company_id == current_user.company_id)

    total_vendors = vendor_count_q.scalar() or 0
    batch_counts = dict(batch_count_q.group_by(Batch.status).all())

    approved_batches = batch_counts.get("APPROVED", 0)
    rejected_batches = batch_counts.get("REJECTED", 0)
    pending_reviews = sum(
        batch_counts.get(s, 0)
        for s in ["NEEDS_REVIEW", "RECEIVED", "PENDING", "PROCESSING"]
    )
    batches_processed = sum(
        batch_counts.get(s, 0)
        for s in ["APPROVED", "REJECTED", "NEEDS_REVIEW", "PROCESSING", "VALIDATED", "PREDICTED", "EVALUATED"]
    )

    vendor_list_q = db.query(Vendor).filter(Vendor.deleted_at.is_(None))
    scored_vendor_q = (
        db.query(Batch.vendor_id, BatchIntelligence.ml_prediction)
        .join(BatchIntelligence, BatchIntelligence.batch_id == Batch.id)
        .filter(BatchIntelligence.ml_prediction.isnot(None))
    )

    if current_user and current_user.company_id:
        vendor_list_q = vendor_list_q.filter(Vendor.company_id == current_user.company_id)
        scored_vendor_q = scored_vendor_q.filter(Batch.company_id == current_user.company_id)

    vendors = vendor_list_q.all()
    scored_vendor_rows = scored_vendor_q.order_by(desc(BatchIntelligence.created_at)).all()
    vendor_risk_scores = {}
    for vendor_id, prediction in scored_vendor_rows:
        if vendor_id not in vendor_risk_scores and prediction and prediction.get("risk_score") is not None:
            vendor_risk_scores[vendor_id] = float(prediction["risk_score"])
    high_risk_vendors = sum(1 for score in vendor_risk_scores.values() if score >= 50.0)

    # 2. Vendor Risk Distribution
    scores = list(vendor_risk_scores.values())
    risk_low = sum(1 for score in scores if score < 25.0)
    risk_medium = sum(1 for score in scores if 25.0 <= score < 50.0)
    risk_high = sum(1 for score in scores if 50.0 <= score < 75.0)
    risk_critical = sum(1 for score in scores if score >= 75.0)

    risk_distribution = [
        {"name": "Low Risk (<25)", "value": risk_low, "color": "#10b981"},
        {"name": "Medium Risk (25-50)", "value": risk_medium, "color": "#3b82f6"},
        {"name": "High Risk (50-75)", "value": risk_high, "color": "#f59e0b"},
        {"name": "Critical Risk (>75)", "value": risk_critical, "color": "#ef4444"},
    ]

    # Trends: dynamically computed over the last 6 months
    today = date.today()
    months = []
    year, month = today.year, today.month
    for _ in range(5):
        month -= 1
        if month == 0:
            year -= 1
            month = 12
    for _ in range(6):
        months.append((year, month))
        month += 1
        if month == 13:
            year += 1
            month = 1

    start_yr, start_mo = months[0]
    trend_start_dt = datetime(start_yr, start_mo, 1, tzinfo=timezone.utc)

    # Only load batches created in the trend window with selective column projection
    trend_batches_q = (
        db.query(Batch.id, Batch.status, Batch.created_at, Batch.purity_reported)
        .filter(Batch.created_at >= trend_start_dt)
    )
    if current_user and current_user.company_id:
        trend_batches_q = trend_batches_q.filter(Batch.company_id == current_user.company_id)
    trend_batches = trend_batches_q.all()

    batch_by_month = defaultdict(list)
    for batch in trend_batches:
        if batch.created_at:
            batch_by_month[(batch.created_at.year, batch.created_at.month)].append(batch)

    # Fetch recent batches table (10 latest batches)
    recent_batches_q = (
        db.query(Batch)
        .options(joinedload(Batch.vendor), joinedload(Batch.raw_material))
        .order_by(desc(Batch.created_at))
    )
    if current_user and current_user.company_id:
        recent_batches_q = recent_batches_q.filter(Batch.company_id == current_user.company_id)
    recent_batches = recent_batches_q.limit(10).all()

    batch_ids_for_intel = list({b.id for b in trend_batches} | {b.id for b in recent_batches if b.id})
    intelligence_by_batch = {}
    if batch_ids_for_intel:
        intels = (
            db.query(
                BatchIntelligence.batch_id,
                BatchIntelligence.ml_prediction,
                BatchIntelligence.validation_result,
            )
            .filter(BatchIntelligence.batch_id.in_(batch_ids_for_intel))
            .all()
        )
        intelligence_by_batch = {row.batch_id: row for row in intels}

    risk_trend = []
    batch_approval_trend = []
    quality_trend = []
    for month_key in months:
        month_batches = batch_by_month[month_key]
        month_scores = []
        month_purities = []
        month_compliance = []
        for batch in month_batches:
            intelligence = intelligence_by_batch.get(batch.id)
            prediction = intelligence.ml_prediction if intelligence and intelligence.ml_prediction else {}
            if prediction.get("risk_score") is not None:
                month_scores.append(float(prediction["risk_score"]))
            if batch.purity_reported is not None:
                month_purities.append(float(batch.purity_reported))
            validation = intelligence.validation_result if intelligence and intelligence.validation_result else {}
            overall_status = validation.get("overall_status")
            if overall_status in {"PASS", "FAIL", "NEEDS_REVIEW"}:
                month_compliance.append(overall_status == "PASS")

        label = date(month_key[0], month_key[1], 1).strftime("%b %Y")
        risk_trend.append({
            "period": label,
            "average_risk": round(sum(month_scores) / len(month_scores), 2) if month_scores else None,
            "high_risk_count": sum(1 for score in month_scores if score >= 50),
        })
        batch_approval_trend.append({
            "period": label,
            "approved": sum(1 for batch in month_batches if batch.status == "APPROVED"),
            "rejected": sum(1 for batch in month_batches if batch.status == "REJECTED"),
            "needs_review": sum(1 for batch in month_batches if batch.status == "NEEDS_REVIEW"),
        })
        quality_trend.append({
            "period": label,
            "average_purity": round(sum(month_purities) / len(month_purities), 3) if month_purities else None,
            "compliance_rate": round(sum(month_compliance) / len(month_compliance) * 100, 2) if month_compliance else None,
        })

    # High Risk Vendors Table
    high_risk_vendors_table = []
    for v in sorted(vendors, key=lambda x: vendor_risk_scores.get(x.id, -1), reverse=True):
        risk_score = vendor_risk_scores.get(v.id)
        if risk_score is not None and risk_score >= 30.0:
            high_risk_vendors_table.append({
                "id": str(v.id),
                "vendor_name": v.vendor_name,
                "industry": v.industry,
                "risk_score": risk_score,
                "approval_rate": round(v.approval_rate * 100, 1) if v.approval_rate is not None else None,
                "quality_score": v.quality_score,
                "delivery_reliability": round(v.delivery_reliability * 100, 1) if v.delivery_reliability is not None else None,
                "status": v.status,
            })

    recent_batch_ids = [b.id for b in recent_batches if b.id]
    recent_emails = {}
    if recent_batch_ids:
        emails = (
            db.query(EmailEvent.batch_id, EmailEvent.status)
            .filter(EmailEvent.batch_id.in_(recent_batch_ids))
            .order_by(desc(EmailEvent.created_at))
            .all()
        )
        for em in emails:
            if em.batch_id not in recent_emails:
                recent_emails[em.batch_id] = em

    recent_batches_table = []
    for b in recent_batches:
        intel = intelligence_by_batch.get(b.id)
        pred = intel.ml_prediction if (intel and intel.ml_prediction) else {}
        email = recent_emails.get(b.id)

        risk_sc = pred.get("risk_score")
        risk_lv = pred.get("risk_level")
        if not risk_lv and risk_sc is not None:
            risk_lv = "LOW" if risk_sc < 25 else ("MEDIUM" if risk_sc < 50 else ("HIGH" if risk_sc < 75 else "CRITICAL"))

        recent_batches_table.append({
            "id": str(b.id),
            "batch_number": b.batch_number,
            "vendor_name": b.vendor.vendor_name if b.vendor else "Unknown Vendor",
            "raw_material_name": b.raw_material.name if b.raw_material else "Unknown Material",
            "quantity": b.quantity,
            "unit": b.unit,
            "status": b.status,
            "risk_score": risk_sc,
            "risk_level": risk_lv,
            "email_status": email.status if email else None,
            "created_at": b.created_at.isoformat() if b.created_at else None,
        })

    payload = {
        "kpis": {
            "total_vendors": total_vendors,
            "batches_processed": batches_processed,
            "approved_batches": approved_batches,
            "rejected_batches": rejected_batches,
            "high_risk_vendors": high_risk_vendors,
            "pending_reviews": pending_reviews,
        },
        "charts": {
            "vendor_risk_distribution": risk_distribution,
            "risk_trend": risk_trend,
            "batch_approval_trend": batch_approval_trend,
            "quality_trend": quality_trend,
        },
        "tables": {
            "high_risk_vendors": high_risk_vendors_table[:10],
            "recent_batch_assessments": recent_batches_table,
        }
    }

    _ANALYTICS_CACHE[company_id_str] = {
        "data": payload,
        "timestamp": time.monotonic(),
    }
    return payload

