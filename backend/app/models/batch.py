"""
Batch model tracking incoming ingredient batches and status workflow in VendorIQ.
Follows VendorIQ PRD Section 11 & 16, unified with AI/ML intelligence and decisions.
"""
import uuid
from sqlalchemy import (
    Column,
    String,
    Float,
    Date,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class Batch(Base):
    __tablename__ = "batches"

    id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    company_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True,
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
    batch_number = Column(String(100), nullable=False)
    manufacturing_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)
    quantity = Column(Float, default=1000.0, nullable=True)
    unit = Column(String(50), default="kg", nullable=True)
    price = Column(Float, default=100.0, nullable=True)
    expected_delivery_date = Column(Date, nullable=True)
    actual_delivery_date = Column(Date, nullable=True)

    # Status: PENDING, RECEIVED, PROCESSING, VALIDATED, PREDICTED, APPROVED, REJECTED, NEEDS_REVIEW
    status = Column(String(50), default="RECEIVED", nullable=False)
    failure_reason = Column(String(1000), nullable=True)

    # Developer 2 / 3 metrics
    purity_reported = Column(Float, nullable=True)
    lead_time_actual = Column(Float, default=14.0, nullable=True)

    created_by = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    company = relationship("Company", back_populates="batches")
    vendor = relationship("Vendor", back_populates="batches")
    raw_material = relationship("RawMaterial", back_populates="batches")
    creator = relationship("User", foreign_keys=[created_by])
    documents = relationship("Document", back_populates="batch", cascade="all, delete-orphan")
    intelligence = relationship("BatchIntelligence", back_populates="batch", uselist=False, cascade="all, delete-orphan")
    decisions = relationship("BatchDecision", back_populates="batch", cascade="all, delete-orphan")
    email_events = relationship("EmailEvent", back_populates="batch", cascade="all, delete-orphan")

    @property
    def price_per_unit(self) -> float:
        return self.price or 100.0

    @price_per_unit.setter
    def price_per_unit(self, val: float):
        self.price = val

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "vendor_id",
            "batch_number",
            name="uq_batches_company_vendor_batch_number",
        ),
        Index("ix_batches_company_id_status", "company_id", "status"),
    )
