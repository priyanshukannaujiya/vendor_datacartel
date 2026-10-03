"""
Vendor Pydantic schemas.
Follows VendorIQ PRD Section 14.
"""
from typing import Optional, List
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
    is_active: bool = True


class VendorCreate(VendorBase):
    pass


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
    is_active: Optional[bool] = None


class VendorResponse(VendorBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    created_at: datetime
    updated_at: datetime


class VendorListResponse(BaseModel):
    items: List[VendorResponse]
    total: int
    page: int
    page_size: int
