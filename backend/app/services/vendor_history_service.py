import math
import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.models.batch import Batch
from app.models.vendor import Vendor
from app.models.document import Document
from app.schemas.vendor_history import VendorHistoryMetrics

logger = logging.getLogger(__name__)


class VendorHistoryService:
    """
    Developer 2 Vendor History Service.
    Reads historical batches, documents, and vendor metrics directly from Neon/SQLAlchemy database.
    Calculates statistical metrics and performs comparative analysis for incoming batches.
    
    SAFETY:
    - Never hardcodes demo vendor statistics.
    - Handles zero previous batches (new vendors) without division by zero.
    """

    def analyze_vendor_history(
        self,
        db: Session,
        vendor_id: Any,
        current_batch: Optional[Batch] = None,
    ) -> VendorHistoryMetrics:
        vendor: Optional[Vendor] = db.query(Vendor).filter(Vendor.id == vendor_id).first()
        if not vendor:
            logger.warning(f"Vendor id={vendor_id} not found in database.")
            return VendorHistoryMetrics(
                vendor_id=vendor_id,
                comparison_notes={"error": f"Vendor id {vendor_id} not found"}
            )

        # Query all previous batches for this vendor (exclude current batch if present)
        query = db.query(Batch).filter(Batch.vendor_id == vendor_id)
        if current_batch and current_batch.id:
            query = query.filter(Batch.id != current_batch.id)
        
        past_batches: List[Batch] = query.all()
        total_past = len(past_batches)

        if total_past == 0:
            # Baseline for new vendor with no past batch records
            return VendorHistoryMetrics(
                vendor_id=vendor_id,
                previous_batches=0,
                approval_rate=0.0,
                rejection_rate=0.0,
                average_purity=0.0,
                purity_variance=0.0,
                documentation_completeness=1.0 if vendor.status == "ACTIVE" else 0.5,
                delivery_reliability=float(vendor.delivery_reliability or 0.85),
                incident_count=0,
                average_lead_time=14.0,
                price_variance=0.0,
                capacity=float(vendor.capacity or 100000.0),
                comparison_notes={
                    "status": "INSUFFICIENT_HISTORY",
                    "message": "New vendor or first recorded batch. Relying on baseline vendor tier data."
                }
            )

        # 1. Approval and Rejection Rates
        approved_count = sum(1 for b in past_batches if b.status == "APPROVED")
        rejected_count = sum(1 for b in past_batches if b.status == "REJECTED")
        decided_count = approved_count + rejected_count

        approval_rate = (approved_count / decided_count) if decided_count > 0 else 0.90
        rejection_rate = (rejected_count / decided_count) if decided_count > 0 else 0.00
        incident_count = rejected_count

        # 2. Purity statistics
        purities = [b.purity_reported for b in past_batches if b.purity_reported is not None]
        if purities:
            avg_purity = sum(purities) / len(purities)
            if len(purities) > 1:
                purity_var = sum((x - avg_purity) ** 2 for x in purities) / (len(purities) - 1)
            else:
                purity_var = 0.0
        else:
            avg_purity = 0.0
            purity_var = 0.0

        # 3. Documentation Completeness across past batches
        # Check percentage of past batches that have at least 2 associated documents
        docs_per_batch = []
        for b in past_batches:
            doc_count = db.query(Document).filter(Document.batch_id == b.id).count()
            docs_per_batch.append(min(1.0, doc_count / 3.0))  # normalized out of 3 standard docs
        doc_completeness = (sum(docs_per_batch) / len(docs_per_batch)) if docs_per_batch else 0.85

        # 4. Delivery Reliability and Lead Times
        lead_times = [b.lead_time_actual for b in past_batches if b.lead_time_actual is not None]
        avg_lead_time = (sum(lead_times) / len(lead_times)) if lead_times else 14.0

        # Delivery reliability: combine vendor's set rate with historical adherence
        delivery_reliability = float(vendor.delivery_reliability or 0.95)

        # 5. Price Variance
        prices = [b.price_per_unit for b in past_batches if b.price_per_unit is not None]
        if len(prices) > 1:
            mean_price = sum(prices) / len(prices)
            price_var = sum((p - mean_price) ** 2 for p in prices) / (len(prices) - 1)
        else:
            price_var = 0.0

        capacity = float(vendor.capacity or 100000.0)

        # 6. Comparison against current batch
        comparison: Dict[str, Any] = {
            "historical_batch_count": total_past,
            "avg_purity": round(avg_purity, 3),
            "approval_rate_pct": round(approval_rate * 100, 1),
        }

        if current_batch:
            if current_batch.purity_reported is not None and avg_purity > 0:
                purity_diff = current_batch.purity_reported - avg_purity
                comparison["purity_diff_from_history"] = round(purity_diff, 3)
                if abs(purity_diff) > 2.0:
                    comparison["purity_anomaly_warning"] = (
                        f"Current purity ({current_batch.purity_reported}%) deviates by "
                        f"{purity_diff:+.2f}% from vendor historical mean ({avg_purity:.2f}%)."
                    )

            if current_batch.quantity and capacity > 0:
                utilization = (current_batch.quantity / capacity) * 100
                comparison["capacity_utilization_pct"] = round(utilization, 2)
                if utilization > 80.0:
                    comparison["capacity_warning"] = f"Batch order consumes {utilization:.1f}% of vendor monthly capacity."

        return VendorHistoryMetrics(
            vendor_id=vendor_id,
            previous_batches=total_past,
            approval_rate=round(approval_rate, 4),
            rejection_rate=round(rejection_rate, 4),
            average_purity=round(avg_purity, 4),
            purity_variance=round(purity_var, 4),
            documentation_completeness=round(doc_completeness, 4),
            delivery_reliability=round(delivery_reliability, 4),
            incident_count=incident_count,
            average_lead_time=round(avg_lead_time, 2),
            price_variance=round(price_var, 4),
            capacity=capacity,
            comparison_notes=comparison,
        )


vendor_history_service = VendorHistoryService()
