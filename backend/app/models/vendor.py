"""
Vendor model for supplier management in VendorIQ.
Follows VendorIQ PRD Section 11 & 14.
"""
import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Index, func, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class Vendor(Base):
    __tablename__ = "vendors"

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
    vendor_name = Column(String(255), nullable=False)
    company_registration_id = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    contact_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    address = Column(String(500), nullable=True)
    industry = Column(String(100), nullable=True)
    supplier_category = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    company = relationship("Company", back_populates="vendors")
    vendor_materials = relationship("VendorMaterial", back_populates="vendor", cascade="all, delete-orphan")
    batches = relationship("Batch", back_populates="vendor", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_vendors_company_id_is_active", "company_id", "is_active"),
        Index(
            "uq_vendors_company_name_not_deleted",
            "company_id",
            "vendor_name",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )
