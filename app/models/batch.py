import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base


class Batch(Base):
    """Batch entity owned by Developer 1."""
    __tablename__ = "batches"

    id = Column(Integer, primary_key=True, index=True)
    batch_number = Column(String(100), unique=True, index=True, nullable=False)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    raw_material_id = Column(Integer, ForeignKey("raw_materials.id"), nullable=False)

    quantity = Column(Float, nullable=False, default=1000.0)
    unit = Column(String(20), default="kg")
    price_per_unit = Column(Float, nullable=True, default=100.0)
    lead_time_actual = Column(Float, nullable=True, default=14.0)

    manufacturing_date = Column(DateTime, nullable=True)
    expiry_date = Column(DateTime, nullable=True)

    # Status managed by pipeline (Dev 1, Dev 2, Dev 3)
    # PENDING, PROCESSING, VALIDATED, PREDICTED, APPROVED, REJECTED, NEEDS_REVIEW
    status = Column(String(50), default="PENDING")
    purity_reported = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    vendor = relationship("Vendor", back_populates="batches")
    raw_material = relationship("RawMaterial", back_populates="batches")
    documents = relationship("Document", back_populates="batch", cascade="all, delete-orphan")
    intelligence = relationship("BatchIntelligence", back_populates="batch", uselist=False, cascade="all, delete-orphan")
