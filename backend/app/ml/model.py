import os
import joblib
import logging
import numpy as np
from typing import Dict, List, Tuple, Optional
from sklearn.ensemble import RandomForestClassifier

from app.schemas.prediction import RiskLevel, RiskPredictionResult

logger = logging.getLogger(__name__)

ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "artifacts")
MODEL_PATH = os.path.join(ARTIFACTS_DIR, "risk_model.joblib")


def map_score_to_level(risk_score: float) -> RiskLevel:
    """
    Maps continuous 0-100 risk score to standardized categorical risk levels.
    """
    if risk_score < 25.0:
        return RiskLevel.LOW
    elif risk_score < 50.0:
        return RiskLevel.MEDIUM
    elif risk_score < 75.0:
        return RiskLevel.HIGH
    else:
        return RiskLevel.CRITICAL


class RiskPredictor:
    """
    Developer 2 Scikit-Learn RandomForestClassifier Risk Model.
    Predicts probability of batch risk/failure from deterministic feature vectors.
    """

    def __init__(self, model_path: str = MODEL_PATH):
        self.model_path = model_path
        self.model: Optional[RandomForestClassifier] = None
        self._load_or_initialize()

    def _load_or_initialize(self):
        if os.path.exists(self.model_path):
            try:
                self.model = joblib.load(self.model_path)
                logger.info(f"Loaded trained RandomForest model from {self.model_path}")
            except Exception as e:
                logger.warning(f"Failed to load artifact from {self.model_path}: {e}. Initializing fallback model.")
                self.model = self._create_trained_fallback_model()
        else:
            logger.info("No pre-trained model artifact found. Initializing trained fallback model.")
            self.model = self._create_trained_fallback_model()

    def _create_trained_fallback_model(self) -> RandomForestClassifier:
        """
        Creates and trains a baseline RandomForestClassifier on synthetic development data
        to guarantee deterministic, instant readiness upon installation.
        """
        from app.ml.training.train_risk_model import generate_synthetic_development_dataset
        X, y = generate_synthetic_development_dataset(n_samples=600, random_state=42)
        clf = RandomForestClassifier(
            n_estimators=100,
            max_depth=6,
            min_samples_split=5,
            random_state=42,
            class_weight="balanced"
        )
        clf.fit(X, y)
        
        # Save to artifacts directory
        try:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            joblib.dump(clf, self.model_path)
            logger.info(f"Saved initial baseline model to {self.model_path}")
        except Exception as e:
            logger.warning(f"Could not persist fallback model: {e}")

        return clf

    def predict(
        self,
        vector: np.ndarray,
        feature_names: List[str],
        detected_risk_factors: List[str]
    ) -> RiskPredictionResult:
        """
        Executes prediction on a single feature vector.
        Calculates calibrated risk probability, score, level, and feature contributions.
        """
        if self.model is None:
            self._load_or_initialize()

        # Reshape to 2D array for scikit-learn
        X = vector.reshape(1, -1)
        
        # Predict class probabilities: Class 0 = Acceptable/Low risk, Class 1 = High/Critical Risk
        probs = self.model.predict_proba(X)[0]
        # Probability of high risk (index 1 if binary classification)
        if len(probs) > 1:
            risk_prob = float(probs[1])
        else:
            risk_prob = float(probs[0])

        # Risk score scaled 0 - 100
        risk_score = round(risk_prob * 100.0, 1)
        risk_level = map_score_to_level(risk_score)

        # Feature contributions / importances for transparency
        importances = getattr(self.model, "feature_importances_", None)
        contributions: Dict[str, float] = {}
        if importances is not None and len(importances) == len(feature_names):
            for name, imp in zip(feature_names, importances):
                contributions[name] = round(float(imp), 4)

        return RiskPredictionResult(
            risk_score=risk_score,
            risk_probability=round(risk_prob, 4),
            risk_level=risk_level,
            risk_factors=detected_risk_factors,
            feature_contributions=contributions
        )


predictor = RiskPredictor()
