"""
VendorMaterial Pydantic schemas.
Follows VendorIQ PRD Section 11 & 16.
"""
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class VendorMaterialCreate(BaseModel):
    vendor_id: UUID
    raw_material_id: UUID
    is_approved: bool = False
    notes: Optional[str] = None


class VendorMaterialUpdate(BaseModel):
    is_approved: Optional[bool] = None
    notes: Optional[str] = None


class VendorMaterialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    vendor_id: UUID
    raw_material_id: UUID
    is_approved: bool
    approved_at: Optional[datetime] = None
    approved_by: Optional[UUID] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class VendorMaterialListResponse(BaseModel):
    items: List[VendorMaterialResponse]
    total: int
    page: int
    page_size: int
