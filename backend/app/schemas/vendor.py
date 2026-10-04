"""
Vendor Pydantic schemas.
Follows VendorIQ PRD Section 14, enriched with risk, performance metrics, and detail views.
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class VendorBase(BaseModel):
    vendor_name: str = Field(..., min_length=1, max_length=255)
    company_registration_id: Optional[str] = None
    country: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    industry: Optional[str] = None
    supplier_category: Optional[str] = None
    tier: Optional[str] = "TIER_2"
    status: Optional[str] = "ACTIVE"
    certification_status: Optional[str] = "GMP_CERTIFIED"
    delivery_reliability: Optional[float] = 0.95
    capacity: Optional[float] = 100000.0
    risk_score: Optional[float] = 15.0
    approval_rate: Optional[float] = 0.95
    quality_score: Optional[float] = 98.0
    is_active: bool = True
    invitation_status: Optional[str] = "NOT_INVITED"
    invitation_sent_at: Optional[datetime] = None


class VendorCreate(VendorBase):
    pass


class VendorInviteRequest(BaseModel):
    vendor_name: str = Field(..., min_length=1, max_length=255)
    email: str = Field(..., min_length=3, max_length=255)
    contact_name: Optional[str] = None
    country: Optional[str] = None
    supplier_category: Optional[str] = "Active Raw Material"
    notes: Optional[str] = None


class VendorUpdate(BaseModel):
    vendor_name: Optional[str] = None
    company_registration_id: Optional[str] = None
    country: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    industry: Optional[str] = None
    supplier_category: Optional[str] = None
    tier: Optional[str] = None
    status: Optional[str] = None
    certification_status: Optional[str] = None
    delivery_reliability: Optional[float] = None
    capacity: Optional[float] = None
    risk_score: Optional[float] = None
    approval_rate: Optional[float] = None
    quality_score: Optional[float] = None
    is_active: Optional[bool] = None


class VendorResponse(VendorBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    name: Optional[str] = None
    code: Optional[str] = None
    invitation_token: Optional[str] = None
    total_batches: Optional[int] = 0
    created_at: datetime
    updated_at: datetime


class VendorDetailResponse(VendorResponse):
    health: Dict[str, Any] = Field(default_factory=dict)
    quality_consistency: float = 98.0
    documentation_completeness: float = 0.95
    historical_batches: List[Dict[str, Any]] = Field(default_factory=list)
    documents: List[Dict[str, Any]] = Field(default_factory=list)
    certifications: List[Dict[str, Any]] = Field(default_factory=list)
    risk_trend: List[Dict[str, Any]] = Field(default_factory=list)
    kimi_assessment: Optional[Dict[str, Any]] = None
    recommended_actions: List[str] = Field(default_factory=list)


class VendorListResponse(BaseModel):
    items: List[VendorResponse]
    total: int
    page: int
    page_size: int
