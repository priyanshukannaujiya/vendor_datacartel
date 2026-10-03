from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class KimiStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class KimiAnalysisResult(BaseModel):
    summary: str
    key_findings: List[str] = Field(default_factory=list)
    risk_factors: List[str] = Field(default_factory=list)
    business_impact: List[str] = Field(default_factory=list)
    recommended_actions: List[str] = Field(default_factory=list)
    decision_explanation: str
    kimi_status: KimiStatus = Field(default=KimiStatus.SUCCESS)
    error_message: Optional[str] = None
