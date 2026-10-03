"""
VendorMaterial model linking approved suppliers to ingredients in VendorIQ.
Follows VendorIQ PRD Section 11 & 16.
"""
import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class VendorMaterial(Base):
    __tablename__ = "vendor_materials"

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
    vendor_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    raw_material_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("raw_materials.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_approved = Column(Boolean, default=False, nullable=False)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    notes = Column(String(1000), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    company = relationship("Company")
    vendor = relationship("Vendor", back_populates="vendor_materials")
    raw_material = relationship("RawMaterial", back_populates="vendor_materials")
    approver = relationship("User", foreign_keys=[approved_by])

    __table_args__ = (
        UniqueConstraint("vendor_id", "raw_material_id", name="uq_vendor_materials_vendor_raw_material"),
    )
