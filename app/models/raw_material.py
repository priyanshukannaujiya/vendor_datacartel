import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.orm import relationship
from app.models.base import Base


class RawMaterial(Base):
    """Raw material specification entity owned by Developer 1."""
    __tablename__ = "raw_materials"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    code = Column(String(50), unique=True, index=True, nullable=False)
    cas_number = Column(String(50), nullable=True)

    # Configurable company / material specifications
    purity_min = Column(Float, default=99.0)  # e.g., 99.0%
    moisture_max = Column(Float, default=1.0)  # e.g., 1.0%
    heavy_metals_max_ppm = Column(Float, default=10.0)  # e.g., 10.0 ppm
    microbial_limit_cfu_g = Column(Float, default=100.0)  # e.g., 100 CFU/g
    storage_conditions = Column(String(255), default="Store below 25C in a dry, dark place")
    lead_time_days = Column(Float, default=14.0)
    base_price = Column(Float, default=100.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    batches = relationship("Batch", back_populates="raw_material")
