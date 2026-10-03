from enum import Enum
from typing import Optional, Any, Dict, List
from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    COA = "COA"
    SDS = "SDS"
    GMP = "GMP"
    SPECIFICATION = "SPECIFICATION"
    TEST_REPORT = "TEST_REPORT"
    COMPLIANCE = "COMPLIANCE"
    OTHER = "OTHER"


class DocumentExtractionStatus(str, Enum):
    PROCESSED = "PROCESSED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    FAILED = "FAILED"
    MISSING = "MISSING"


class COAExtractionData(BaseModel):
    batch_number: Optional[str] = None
    material: Optional[str] = None
    purity: Optional[float] = None
    moisture: Optional[float] = None
    heavy_metals: Optional[float] = None
    microbial_parameters: Optional[Dict[str, Any]] = None
    test_date: Optional[str] = None
    manufacturing_date: Optional[str] = None
    expiry_date: Optional[str] = None
    laboratory: Optional[str] = None
    extraction_notes: List[str] = Field(default_factory=list)


class SDSExtractionData(BaseModel):
    product_name: Optional[str] = None
    cas_number: Optional[str] = None
    hazard_statements: List[str] = Field(default_factory=list)
    storage_requirements: Optional[str] = None
    revision_date: Optional[str] = None
    extraction_notes: List[str] = Field(default_factory=list)


class GMPExtractionData(BaseModel):
    certificate_number: Optional[str] = None
    issuing_body: Optional[str] = None
    valid_until: Optional[str] = None
    is_valid: Optional[bool] = None
    scope: Optional[str] = None
    extraction_notes: List[str] = Field(default_factory=list)


class GenericExtractionData(BaseModel):
    title: Optional[str] = None
    date: Optional[str] = None
    summary: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    extraction_notes: List[str] = Field(default_factory=list)


class DocumentProcessResult(BaseModel):
    document_id: Optional[int] = None
    filename: str
    document_type: DocumentType
    status: DocumentExtractionStatus
    extracted_data: Dict[str, Any] = Field(default_factory=dict)
    missing_fields: List[str] = Field(default_factory=list)
    error: Optional[str] = None
