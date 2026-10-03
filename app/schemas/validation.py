from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, Field


class CheckStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    MISSING = "MISSING"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class OverallValidationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class ValidationCheckItem(BaseModel):
    name: str
    status: CheckStatus
    expected: str
    actual: Any
    reason: str


class ValidationResult(BaseModel):
    overall_status: OverallValidationStatus
    checks: List[ValidationCheckItem] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
