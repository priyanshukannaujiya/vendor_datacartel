"""
Batch Pydantic schemas.
Follows VendorIQ PRD Section 11 & 16.
"""
from typing import Optional, List
from uuid import UUID
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field


class BatchCreate(BaseModel):
    vendor_id: UUID
    raw_material_id: UUID
    batch_number: str = Field(..., min_length=1, max_length=100)
    manufacturing_date: Optional[date] = None
    expiry_date: Optional[date] = None
    quantity: Optional[float] = None
    unit: Optional[str] = Field(None, max_length=50)
    price: Optional[float] = None
    expected_delivery_date: Optional[date] = None
    actual_delivery_date: Optional[date] = None


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


class BatchListResponse(BaseModel):
    items: List[BatchResponse]
    total: int
    page: int
    page_size: int
