"""
RawMaterial model for ingredient and spec management in VendorIQ.
Follows VendorIQ PRD Section 11 & 15, enriched with analytical parameters for validation.
"""
import uuid
from sqlalchemy import Column, String, Boolean, Float, DateTime, ForeignKey, UniqueConstraint, JSON, func
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
    cas_number = Column(String(50), nullable=True)

    # Configurable material analytical specifications
    purity_min = Column(Float, default=99.0, nullable=False)
    moisture_max = Column(Float, default=1.0, nullable=False)
    heavy_metals_max_ppm = Column(Float, default=10.0, nullable=False)
    microbial_limit_cfu_g = Column(Float, default=100.0, nullable=False)
    storage_conditions = Column(String(255), default="Store below 25C in a dry, dark place", nullable=False)
    lead_time_days = Column(Float, default=14.0, nullable=False)
    base_price = Column(Float, default=100.0, nullable=False)

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
