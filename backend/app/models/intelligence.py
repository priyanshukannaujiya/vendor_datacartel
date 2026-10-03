"""
BatchIntelligence model storing AI/ML validation outputs, historical metrics,
RandomForest risk predictions, and Kimi K3 technical reasoning synthesis.
"""
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class BatchIntelligence(Base):
    __tablename__ = "batch_intelligence"

    id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    batch_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("batches.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    validation_result = Column(JSON, nullable=True)
    vendor_history = Column(JSON, nullable=True)
    ml_features = Column(JSON, nullable=True)
    ml_prediction = Column(JSON, nullable=True)
    kimi_analysis = Column(JSON, nullable=True)
    kimi_status = Column(String(50), default="PENDING", nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    batch = relationship("Batch", back_populates="intelligence")
