import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from app.models.batch import Batch
from app.models.raw_material import RawMaterial
from app.models.vendor import Vendor
from app.schemas.validation import ValidationResult, OverallValidationStatus, CheckStatus
from app.schemas.vendor_history import VendorHistoryMetrics


FEATURE_NAMES = [
    "quality_score",
    "purity",
    "purity_variance",
    "document_completeness",
    "certification_status",
    "delivery_reliability",
    "rejection_rate",
    "incident_count",
    "lead_time",
    "capacity",
    "price_variance",
    "historical_approval_rate",
]

CERTIFICATION_ENCODING = {
    "GMP_CERTIFIED": 1.0,
    "ISO_CERTIFIED": 0.8,
    "PENDING": 0.4,
    "EXPIRED": 0.0,
    "NONE": 0.0,
}


class FeatureBuilder:
    """
    Developer 2 Deterministic Feature Builder.
    Converts domain entities, validation results, and historical statistics
    into a fixed, reproducible numerical vector for the ML Risk Model.
    """

    @classmethod
    def build_features(
        cls,
        batch: Optional[Batch],
        material: Optional[RawMaterial],
        vendor: Optional[Vendor],
        validation_result: Optional[ValidationResult] = None,
        vendor_history: Optional[VendorHistoryMetrics] = None,
        extracted_coa_purity: Optional[float] = None,
    ) -> Tuple[Dict[str, float], List[str]]:
        """
        Builds feature map and detects rule-based preliminary risk indicators.
        Returns:
            features: Dict mapping exact feature name to float
            risk_factors: List of human-readable risk factors identified
        """
        risk_factors: List[str] = []

        # 1. Purity
        # Preference: direct COA extracted purity -> batch.purity_reported -> material min -> default
        if extracted_coa_purity is not None:
            purity = float(extracted_coa_purity)
        elif batch and batch.purity_reported is not None:
            purity = float(batch.purity_reported)
        elif material and material.purity_min is not None:
            purity = float(material.purity_min)
        else:
            purity = 98.0
            risk_factors.append("Batch purity unavailable; defaulted to baseline.")

        expected_purity = material.purity_min if material and material.purity_min else 99.0
        if purity < expected_purity:
            risk_factors.append(f"Purity ({purity:.2f}%) below minimum specification threshold ({expected_purity:.2f}%).")

        # 2. Quality Score (Derived composite score 0-100 based on validation & purity)
        if validation_result:
            pass_count = sum(1 for c in validation_result.checks if c.status == CheckStatus.PASS)
            total_checks = max(len(validation_result.checks), 1)
            validation_pct = (pass_count / total_checks) * 100.0

            if validation_result.overall_status == OverallValidationStatus.FAIL:
                quality_score = min(validation_pct, 45.0)
                risk_factors.append("Validation failed on one or more mandatory parameter checks.")
            elif validation_result.overall_status == OverallValidationStatus.NEEDS_REVIEW:
                quality_score = min(validation_pct, 70.0)
                risk_factors.append("Validation requires manual QA review due to missing or unverified parameters.")
            else:
                quality_score = validation_pct
        else:
            quality_score = 75.0

        # 3. Purity Variance & Historical Stats
        if vendor_history:
            purity_variance = float(vendor_history.purity_variance)
            document_completeness = float(vendor_history.documentation_completeness)
            delivery_reliability = float(vendor_history.delivery_reliability)
            rejection_rate = float(vendor_history.rejection_rate)
            incident_count = int(vendor_history.incident_count)
            price_variance = float(vendor_history.price_variance)
            historical_approval_rate = float(vendor_history.approval_rate)
            capacity = float(vendor_history.capacity)

            if vendor_history.previous_batches == 0:
                risk_factors.append("Vendor has no prior recorded batch history (new supplier risk).")
            if rejection_rate > 0.15:
                risk_factors.append(f"Elevated supplier rejection rate ({rejection_rate * 100:.1f}%).")
            if incident_count > 2:
                risk_factors.append(f"Multiple recorded quality/operational incidents ({incident_count}).")
            if purity_variance > 1.0:
                risk_factors.append(f"High historical batch purity variance ({purity_variance:.2f}).")
        else:
            purity_variance = 0.05
            document_completeness = 0.90
            delivery_reliability = float(vendor.delivery_reliability if vendor and vendor.delivery_reliability else 0.95)
            rejection_rate = 0.05
            incident_count = 0
            price_variance = 0.0
            historical_approval_rate = 0.95
            capacity = float(vendor.capacity if vendor and vendor.capacity else 100000.0)

        # 4. Certification Status
        cert_raw = vendor.certification_status if vendor and vendor.certification_status else "GMP_CERTIFIED"
        cert_score = CERTIFICATION_ENCODING.get(cert_raw.upper(), 0.5)
        if cert_score == 0.0:
            risk_factors.append(f"Supplier certification status is invalid or expired ({cert_raw}).")

        # 5. Delivery Reliability
        if delivery_reliability < 0.85:
            risk_factors.append(f"Supplier delivery reliability is low ({delivery_reliability * 100:.1f}%).")

        # 6. Lead Time
        if batch and batch.lead_time_actual is not None:
            lead_time = float(batch.lead_time_actual)
        elif material and material.lead_time_days is not None:
            lead_time = float(material.lead_time_days)
        else:
            lead_time = 14.0

        if material and material.lead_time_days and lead_time > material.lead_time_days * 1.5:
            risk_factors.append(f"Batch lead time ({lead_time:.0f} days) severely delayed vs baseline ({material.lead_time_days:.0f} days).")

        # Compile feature dict
        features: Dict[str, float] = {
            "quality_score": round(quality_score, 4),
            "purity": round(purity, 4),
            "purity_variance": round(purity_variance, 4),
            "document_completeness": round(document_completeness, 4),
            "certification_status": round(cert_score, 4),
            "delivery_reliability": round(delivery_reliability, 4),
            "rejection_rate": round(rejection_rate, 4),
            "incident_count": float(incident_count),
            "lead_time": round(lead_time, 2),
            "capacity": round(capacity, 2),
            "price_variance": round(price_variance, 4),
            "historical_approval_rate": round(historical_approval_rate, 4),
        }

        return features, risk_factors

    @classmethod
    def to_vector(cls, features: Dict[str, float]) -> np.ndarray:
        """Converts feature dictionary into standard 1D numpy vector ordered by FEATURE_NAMES."""
        return np.array([features[name] for name in FEATURE_NAMES], dtype=np.float32)
