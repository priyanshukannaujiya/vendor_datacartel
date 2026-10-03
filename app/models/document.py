import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.models.base import Base


class Document(Base):
    """Document metadata entity owned by Developer 1, processed by Developer 2."""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=True)

    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    # COA, SDS, GMP, SPECIFICATION, TEST_REPORT, COMPLIANCE, OTHER
    document_type = Column(String(50), nullable=False, default="OTHER")
    # UPLOADED, PROCESSED, NEEDS_REVIEW, FAILED
    status = Column(String(50), default="UPLOADED")

    extracted_data = Column(JSON, nullable=True)
    extraction_error = Column(Text, nullable=True)
    upload_date = Column(DateTime, default=datetime.datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)

    # Relationships
    batch = relationship("Batch", back_populates="documents")
    vendor = relationship("Vendor", back_populates="documents")
