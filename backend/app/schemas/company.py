"""
Company Pydantic schemas.
"""
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class CompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    industry: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
