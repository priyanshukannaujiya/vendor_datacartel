import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.orm import relationship
from app.models.base import Base


class Vendor(Base):
    """Vendor entity owned by Developer 1."""
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    code = Column(String(50), unique=True, index=True, nullable=False)
    contact_email = Column(String(255), nullable=True)
    tier = Column(String(50), default="TIER_2")  # TIER_1, TIER_2, TIER_3
    status = Column(String(50), default="ACTIVE")  # ACTIVE, SUSPENDED, ON_PROBATION
    certification_status = Column(String(50), default="GMP_CERTIFIED")  # GMP_CERTIFIED, ISO_CERTIFIED, EXPIRED, NONE
    delivery_reliability = Column(Float, default=0.95)  # 0.0 to 1.0 (95%)
    capacity = Column(Float, default=100000.0)  # production capacity
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    batches = relationship("Batch", back_populates="vendor")
    documents = relationship("Document", back_populates="vendor")
