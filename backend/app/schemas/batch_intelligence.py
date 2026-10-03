from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.schemas.validation import ValidationResult
from app.schemas.vendor_history import VendorHistoryMetrics
from app.schemas.document import DocumentProcessResult
from app.schemas.prediction import RiskPredictionResult
from app.schemas.kimi import KimiAnalysisResult


class BatchProcessResponse(BaseModel):
    batch_id: Any
    batch_number: str
    validation_result: ValidationResult
    vendor_history: VendorHistoryMetrics
    extracted_documents: List[DocumentProcessResult] = Field(default_factory=list)
    message: str = "Batch processed and validated successfully."


class BatchPredictRiskResponse(BaseModel):
    batch_id: Any
    batch_number: str
    risk_prediction: RiskPredictionResult
    kimi_analysis: KimiAnalysisResult
    features_used: Dict[str, float] = Field(default_factory=dict)
    message: str = "Risk prediction and AI reasoning generated successfully."
