"""
Raw Material & Specification Pydantic schemas.
Follows VendorIQ PRD Section 11 & 15.
"""
from typing import Optional, List, Union, Any, Dict
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class SpecificationParameter(BaseModel):
    name: str = Field(..., description="Parameter name, e.g. purity, moisture")
    operator: str = Field(..., description="Comparison operator: >=, <=, ==, >, <, contains")
    value: Union[float, int, str] = Field(..., description="Target or boundary value")
    unit: Optional[str] = Field(None, description="Measurement unit, e.g. %, ppm, mg/kg")
    mandatory: bool = Field(True, description="Whether this check is mandatory for qualification")


class MaterialSpecification(BaseModel):
    parameters: List[SpecificationParameter] = Field(default_factory=list)
    moisture_max: Optional[float] = None
    heavy_metals_max: Optional[float] = None
    storage_requirements: Optional[str] = None
    notes: Optional[str] = None


class RawMaterialBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=100)
    category: Optional[str] = None
    description: Optional[str] = None
    cas_number: Optional[str] = None
    purity_min: Optional[float] = 99.0
    moisture_max: Optional[float] = 1.0
    heavy_metals_max_ppm: Optional[float] = 10.0
    microbial_limit_cfu_g: Optional[float] = 100.0
    storage_conditions: Optional[str] = "Store below 25C in a dry, dark place"
    lead_time_days: Optional[float] = 14.0
    base_price: Optional[float] = 100.0
    specification: Optional[Dict[str, Any]] = None
    required_documents: Optional[List[str]] = Field(default_factory=lambda: ["COA", "SDS", "GMP"])
    active: bool = True


class RawMaterialCreate(RawMaterialBase):
    pass


class RawMaterialUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    cas_number: Optional[str] = None
    purity_min: Optional[float] = None
    moisture_max: Optional[float] = None
    heavy_metals_max_ppm: Optional[float] = None
    microbial_limit_cfu_g: Optional[float] = None
    storage_conditions: Optional[str] = None
    lead_time_days: Optional[float] = None
    base_price: Optional[float] = None
    specification: Optional[Dict[str, Any]] = None
    required_documents: Optional[List[str]] = None
    active: Optional[bool] = None


class RawMaterialResponse(RawMaterialBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    created_at: datetime
    updated_at: datetime


class RawMaterialListResponse(BaseModel):
    items: List[RawMaterialResponse]
    total: int
    page: int
    page_size: int
