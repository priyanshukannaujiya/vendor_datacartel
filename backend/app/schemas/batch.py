"""
Batch Pydantic schemas.
Follows VendorIQ PRD Section 11 & 16, unified with Developer 2 & Developer 3 workflows.
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field


class BatchCreate(BaseModel):
    vendor_id: UUID
    raw_material_id: UUID
    batch_number: str = Field(..., min_length=1, max_length=100)
    manufacturing_date: Optional[date] = None
    expiry_date: Optional[date] = None
    quantity: Optional[float] = 1000.0
    unit: Optional[str] = Field("kg", max_length=50)
    price: Optional[float] = 100.0
    expected_delivery_date: Optional[date] = None
    actual_delivery_date: Optional[date] = None
    purity_reported: Optional[float] = None


class BatchUpdate(BaseModel):
    batch_number: Optional[str] = None
    manufacturing_date: Optional[date] = None
    expiry_date: Optional[date] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    price: Optional[float] = None
    status: Optional[str] = None
    purity_reported: Optional[float] = None


class BatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    vendor_id: UUID
    raw_material_id: UUID
    batch_number: str
    manufacturing_date: Optional[date] = None
    expiry_date: Optional[date] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    price: Optional[float] = None
    expected_delivery_date: Optional[date] = None
    actual_delivery_date: Optional[date] = None
    status: str
    failure_reason: Optional[str] = None
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    warning: Optional[str] = None

    # Unified pipeline fields
    vendor_name: Optional[str] = None
    raw_material_name: Optional[str] = None
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    processed: Optional[bool] = False
    email_status: Optional[str] = None
    purity_reported: Optional[float] = None


class BatchDetailResponse(BatchResponse):
    quality_checks: Dict[str, Any] = Field(default_factory=dict)
    historical_comparison: Dict[str, Any] = Field(default_factory=dict)
    risk_prediction: Optional[Dict[str, Any]] = None
    kimi_analysis: Optional[Dict[str, Any]] = None
    final_decision: Optional[Dict[str, Any]] = None
    email_event: Optional[Dict[str, Any]] = None
    audit_timeline: List[Dict[str, Any]] = Field(default_factory=list)
    documents: List[Dict[str, Any]] = Field(default_factory=list)


class BatchListResponse(BaseModel):
    items: List[BatchResponse]
    total: int
    page: int
    page_size: int


class BatchDecisionRequest(BaseModel):
    company_id: Optional[str] = None
    company_thresholds: Dict[str, Any] = Field(default_factory=dict)


class BatchDecisionResponse(BaseModel):
    decision: str
    risk_score: float
    reason: str
    recommended_actions: List[str]
    reference_id: Any
    email_status: str
