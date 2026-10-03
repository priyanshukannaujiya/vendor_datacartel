from enum import Enum
from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskPredictionResult(BaseModel):
    risk_score: float = Field(..., description="Overall risk score from 0 (safest) to 100 (highest risk)")
    risk_probability: float = Field(..., description="Calibrated risk probability between 0.0 and 1.0")
    risk_level: RiskLevel = Field(..., description="Categorical risk rating: LOW, MEDIUM, HIGH, CRITICAL")
    risk_factors: List[str] = Field(default_factory=list, description="Top detected risk factors contributing to prediction")
    feature_contributions: Optional[Dict[str, float]] = Field(default=None, description="Feature attribution scores")
