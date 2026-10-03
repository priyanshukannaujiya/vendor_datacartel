import pytest
import numpy as np

from app.ml.feature_builder import FeatureBuilder, FEATURE_NAMES
from app.ml.model import RiskPredictor, map_score_to_level
from app.services.prediction_service import BatchRiskPredictionService
from app.schemas.prediction import RiskLevel
from app.schemas.validation import ValidationResult, OverallValidationStatus, CheckStatus, ValidationCheckItem
from app.schemas.vendor_history import VendorHistoryMetrics
from app.models.batch import Batch
from app.models.raw_material import RawMaterial
from app.models.vendor import Vendor


def test_feature_builder_feature_vector_dimensions():
    # Verify exact 12 features matching FEATURE_NAMES
    vendor = Vendor(id=1, certification_status="GMP_CERTIFIED", delivery_reliability=0.95, capacity=100000.0)
    material = RawMaterial(id=1, purity_min=99.0, lead_time_days=14.0)
    batch = Batch(id=1, batch_number="B-1", purity_reported=99.3, lead_time_actual=14.0)

    val_res = ValidationResult(
        overall_status=OverallValidationStatus.PASS,
        checks=[ValidationCheckItem(name="purity", status=CheckStatus.PASS, expected=">=99", actual=99.3, reason="OK")]
    )
    hist = VendorHistoryMetrics(
        vendor_id=1,
        previous_batches=10,
        approval_rate=0.9,
        rejection_rate=0.1,
        average_purity=99.2,
        purity_variance=0.04,
        documentation_completeness=0.95,
        delivery_reliability=0.95,
        incident_count=1,
        average_lead_time=14.0,
        price_variance=0.5,
        capacity=100000.0,
    )

    features, risk_factors = FeatureBuilder.build_features(
        batch=batch,
        material=material,
        vendor=vendor,
        validation_result=val_res,
        vendor_history=hist,
        extracted_coa_purity=99.3
    )

    assert len(features) == len(FEATURE_NAMES)
    for name in FEATURE_NAMES:
        assert name in features
        assert isinstance(features[name], (int, float))

    vec = FeatureBuilder.to_vector(features)
    assert isinstance(vec, np.ndarray)
    assert vec.shape == (12,)


def test_risk_level_mapping():
    assert map_score_to_level(12.5) == RiskLevel.LOW
    assert map_score_to_level(24.9) == RiskLevel.LOW
    assert map_score_to_level(25.0) == RiskLevel.MEDIUM
    assert map_score_to_level(49.9) == RiskLevel.MEDIUM
    assert map_score_to_level(50.0) == RiskLevel.HIGH
    assert map_score_to_level(74.9) == RiskLevel.HIGH
    assert map_score_to_level(75.0) == RiskLevel.CRITICAL
    assert map_score_to_level(95.0) == RiskLevel.CRITICAL


def test_ml_prediction_low_risk_batch():
    predictor = RiskPredictor()
    pred_service = BatchRiskPredictionService(predictor)

    vendor = Vendor(id=1, certification_status="GMP_CERTIFIED", delivery_reliability=0.99, capacity=200000.0)
    material = RawMaterial(id=1, purity_min=99.0, lead_time_days=14.0)
    batch = Batch(id=1, batch_number="B-PRISTINE", purity_reported=99.8, lead_time_actual=12.0)

    val_res = ValidationResult(
        overall_status=OverallValidationStatus.PASS,
        checks=[
            ValidationCheckItem(name="purity", status=CheckStatus.PASS, expected=">=99", actual=99.8, reason="Met"),
            ValidationCheckItem(name="gmp", status=CheckStatus.PASS, expected="Valid", actual="Valid", reason="Met")
        ]
    )
    hist = VendorHistoryMetrics(
        vendor_id=1,
        previous_batches=25,
        approval_rate=0.98,
        rejection_rate=0.02,
        average_purity=99.6,
        purity_variance=0.01,
        documentation_completeness=1.0,
        delivery_reliability=0.99,
        incident_count=0,
        average_lead_time=13.0,
        price_variance=0.01,
        capacity=200000.0
    )

    pred, feat_used = pred_service.predict_risk(batch, material, vendor, val_res, hist)

    assert 0.0 <= pred.risk_score <= 100.0
    assert 0.0 <= pred.risk_probability <= 1.0
    assert pred.risk_level in (RiskLevel.LOW, RiskLevel.MEDIUM)
    assert pred.feature_contributions is not None


def test_ml_prediction_high_risk_batch():
    predictor = RiskPredictor()
    pred_service = BatchRiskPredictionService(predictor)

    # Vendor with expired cert, low reliability, high rejection rate, failing purity
    vendor = Vendor(id=2, certification_status="EXPIRED", delivery_reliability=0.60, capacity=20000.0)
    material = RawMaterial(id=2, purity_min=99.0, lead_time_days=14.0)
    batch = Batch(id=2, batch_number="B-BAD", purity_reported=94.5, lead_time_actual=45.0)

    val_res = ValidationResult(
        overall_status=OverallValidationStatus.FAIL,
        checks=[
            ValidationCheckItem(name="purity", status=CheckStatus.FAIL, expected=">=99", actual=94.5, reason="Substandard"),
            ValidationCheckItem(name="gmp", status=CheckStatus.FAIL, expected="Valid", actual="Expired", reason="Expired")
        ]
    )
    hist = VendorHistoryMetrics(
        vendor_id=2,
        previous_batches=10,
        approval_rate=0.50,
        rejection_rate=0.50,
        average_purity=95.0,
        purity_variance=1.8,
        documentation_completeness=0.40,
        delivery_reliability=0.60,
        incident_count=5,
        average_lead_time=35.0,
        price_variance=12.0,
        capacity=20000.0
    )

    pred, feat_used = pred_service.predict_risk(batch, material, vendor, val_res, hist)

    assert pred.risk_score >= 50.0  # Should be HIGH or CRITICAL
    assert pred.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
    assert len(pred.risk_factors) >= 3
