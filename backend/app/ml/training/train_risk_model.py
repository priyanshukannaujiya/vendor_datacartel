"""
SYNTHETIC DEVELOPMENT DATASET GENERATOR & TRAINING SCRIPT
==========================================================
DISCLAIMER: This script generates SYNTHETIC DEVELOPMENT DATA ONLY for training
the baseline RandomForestClassifier risk model. It is intended strictly for
development, local testing, and offline benchmarking.
NEVER REPRESENT THIS SYNTHETIC DATA AS REAL PRODUCTION DATA.
"""

import os
import joblib
import numpy as np
from typing import Tuple
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import train_test_split


ARTIFACTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "artifacts")
MODEL_OUTPUT_PATH = os.path.join(ARTIFACTS_DIR, "risk_model.joblib")


def generate_synthetic_development_dataset(n_samples: int = 1200, random_state: int = 42) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generates synthetic batches for development training.
    Features:
    0: quality_score (0-100)
    1: purity (90-100%)
    2: purity_variance (0.0-2.0)
    3: document_completeness (0.0-1.0)
    4: certification_status (0.0-1.0)
    5: delivery_reliability (0.0-1.0)
    6: rejection_rate (0.0-0.5)
    7: incident_count (0-10)
    8: lead_time (5-60 days)
    9: capacity (1000-500000 units)
    10: price_variance (0.0-50.0)
    11: historical_approval_rate (0.5-1.0)
    """
    rng = np.random.RandomState(random_state)

    quality_score = rng.normal(85.0, 15.0, n_samples).clip(10.0, 100.0)
    purity = rng.normal(99.1, 1.2, n_samples).clip(92.0, 100.0)
    purity_variance = rng.exponential(0.1, n_samples).clip(0.001, 2.5)
    document_completeness = rng.beta(8, 2, n_samples).clip(0.2, 1.0)
    certification_status = rng.choice([1.0, 0.8, 0.4, 0.0], size=n_samples, p=[0.70, 0.15, 0.10, 0.05])
    delivery_reliability = rng.beta(9, 1.5, n_samples).clip(0.4, 1.0)
    rejection_rate = rng.exponential(0.04, n_samples).clip(0.0, 0.6)
    incident_count = rng.poisson(0.5, n_samples).clip(0, 12)
    lead_time = rng.normal(14.0, 5.0, n_samples).clip(3.0, 60.0)
    capacity = rng.uniform(20000.0, 300000.0, n_samples)
    price_variance = rng.exponential(1.5, n_samples).clip(0.0, 40.0)
    historical_approval_rate = (1.0 - rejection_rate).clip(0.3, 1.0)

    X = np.column_stack([
        quality_score,
        purity,
        purity_variance,
        document_completeness,
        certification_status,
        delivery_reliability,
        rejection_rate,
        incident_count,
        lead_time,
        capacity,
        price_variance,
        historical_approval_rate,
    ])

    # True risk logic formulation for synthetic ground-truth
    # High risk if purity < 98.5, quality_score < 70, cert == 0, rejection_rate > 0.15, or incidents >= 3
    risk_signal = (
        (100.0 - quality_score) * 0.35 +
        (99.0 - purity).clip(min=0.0) * 12.0 +
        purity_variance * 10.0 +
        (1.0 - document_completeness) * 20.0 +
        (1.0 - certification_status) * 25.0 +
        (1.0 - delivery_reliability) * 15.0 +
        rejection_rate * 35.0 +
        incident_count * 5.0
    )

    # Normalize to probability through sigmoid
    prob = 1.0 / (1.0 + np.exp(-(risk_signal - 26.0) / 7.0))
    y = (prob > 0.5).astype(int)

    return X, y


def train_and_save_model():
    print("Generating synthetic DEVELOPMENT dataset...")
    X, y = generate_synthetic_development_dataset(n_samples=1500, random_state=42)
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    print(f"Training RandomForestClassifier on {len(X_train)} samples...")
    model = RandomForestClassifier(
        n_estimators=150,
        max_depth=7,
        min_samples_leaf=4,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    print("\n--- Test Set Evaluation ---")
    print(classification_report(y_test, y_pred))
    auc = roc_auc_score(y_test, y_prob)
    print(f"ROC-AUC Score: {auc:.4f}")

    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    joblib.dump(model, MODEL_OUTPUT_PATH)
    print(f"\nModel artifact successfully saved to: {MODEL_OUTPUT_PATH}")


if __name__ == "__main__":
    train_and_save_model()
