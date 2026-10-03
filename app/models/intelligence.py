import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.models.base import Base


class BatchIntelligence(Base):
    """
    Developer 2 isolated persistence table for AI/ML and validation outputs.
    Stores validation results, computed vendor history metrics,
    deterministic ML risk predictions, and Kimi reasoning layers.
    """
    __tablename__ = "batch_intelligence"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("batches.id"), unique=True, nullable=False)

    # Developer 2 Module Outputs
    validation_result = Column(JSON, nullable=True)
    vendor_history = Column(JSON, nullable=True)
    ml_features = Column(JSON, nullable=True)
    ml_prediction = Column(JSON, nullable=True)
    kimi_analysis = Column(JSON, nullable=True)

    # Status tracking
    kimi_status = Column(String(50), default="PENDING")  # SUCCESS, FAILED, SKIPPED

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationship back to Batch
    batch = relationship("Batch", back_populates="intelligence")
