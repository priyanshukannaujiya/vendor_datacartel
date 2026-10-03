"""
Authentication Pydantic schemas.
Follows VendorIQ PRD Section 13.
"""
from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.schemas.company import CompanyResponse


class RegisterRequest(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=255)
    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters")


class LoginRequest(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    password: str

    @property
    def login_email(self) -> str:
        return (self.email or self.username or "").strip().lower()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class MeResponse(BaseModel):
    user: UserResponse
    company: CompanyResponse
