"""
Company model for multi-tenant isolation in VendorIQ.
Follows VendorIQ PRD Section 11.
"""
import uuid
from sqlalchemy import Column, String, DateTime, JSON, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name = Column(String(255), unique=True, nullable=False, index=True)
    industry = Column(String(255), nullable=True)
    settings = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    users = relationship("User", back_populates="company", cascade="all, delete-orphan")
    vendors = relationship("Vendor", back_populates="company", cascade="all, delete-orphan")
    raw_materials = relationship("RawMaterial", back_populates="company", cascade="all, delete-orphan")
    batches = relationship("Batch", back_populates="company", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="company", cascade="all, delete-orphan")

