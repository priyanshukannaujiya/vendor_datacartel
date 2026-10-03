import logging
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session

from app.models.batch import Batch
from app.models.raw_material import RawMaterial
from app.models.vendor import Vendor
from app.schemas.validation import ValidationResult
from app.schemas.vendor_history import VendorHistoryMetrics
from app.schemas.prediction import RiskPredictionResult
from app.ml.feature_builder import FeatureBuilder, FEATURE_NAMES
from app.ml.model import predictor, RiskPredictor

logger = logging.getLogger(__name__)


class BatchRiskPredictionService:
    """
    Developer 2 ML Risk Prediction Service.
    Transforms batch, material, vendor history, and validation outcomes into
    features, executing the trained RandomForestClassifier model.

    CRITICAL RULE:
    The prediction service outputs risk_score (0-100), risk_probability (0.0-1.0),
    risk_level (LOW/MEDIUM/HIGH/CRITICAL), and risk_factors.
    It DOES NOT make the final approval/rejection decision (owned by Developer 3).
    """

    def __init__(self, risk_predictor: Optional[RiskPredictor] = None):
        self.predictor = risk_predictor or predictor

    def predict_risk(
        self,
        batch: Batch,
        material: RawMaterial,
        vendor: Vendor,
        validation_result: Optional[ValidationResult] = None,
        vendor_history: Optional[VendorHistoryMetrics] = None,
        extracted_coa_purity: Optional[float] = None,
    ) -> Tuple[RiskPredictionResult, Dict[str, float]]:
        """
        Calculates deterministic features, generates ML risk prediction,
        and returns both the structured prediction result and the exact feature vector used.
        """
        # 1. Build deterministic feature dictionary and collect rule-based flags
        features, detected_risk_factors = FeatureBuilder.build_features(
            batch=batch,
            material=material,
            vendor=vendor,
            validation_result=validation_result,
            vendor_history=vendor_history,
            extracted_coa_purity=extracted_coa_purity,
        )

        # 2. Convert to ordered numerical vector
        vector = FeatureBuilder.to_vector(features)

        # 3. Model prediction
        prediction_result = self.predictor.predict(
            vector=vector,
            feature_names=FEATURE_NAMES,
            detected_risk_factors=detected_risk_factors,
        )

        logger.info(
            f"Batch {batch.batch_number} ML Risk: Score={prediction_result.risk_score}, "
            f"Level={prediction_result.risk_level}, Factors={len(prediction_result.risk_factors)}"
        )

        return prediction_result, features


prediction_service = BatchRiskPredictionService()
