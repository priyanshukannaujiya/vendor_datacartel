"""
RawMaterial model for ingredient and spec management in VendorIQ.
Follows VendorIQ PRD Section 11 & 15.
"""
import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, UniqueConstraint, JSON, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class RawMaterial(Base):
    __tablename__ = "raw_materials"

    id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    company_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    code = Column(String(100), nullable=False)
    category = Column(String(100), nullable=True)
    description = Column(String(1000), nullable=True)
    specification = Column(JSON, nullable=True, default=dict)
    required_documents = Column(JSON, nullable=True, default=list)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    company = relationship("Company", back_populates="raw_materials")
    vendor_materials = relationship("VendorMaterial", back_populates="raw_material", cascade="all, delete-orphan")
    batches = relationship("Batch", back_populates="raw_material", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_raw_materials_company_code"),
    )
