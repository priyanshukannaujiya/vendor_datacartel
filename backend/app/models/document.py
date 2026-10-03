"""
Document model for storing document metadata and tracking extraction status in VendorIQ.
Follows VendorIQ PRD Section 11 & 17.
"""
import uuid
from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    ForeignKey,
    JSON,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class Document(Base):
    __tablename__ = "documents"

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
    batch_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("batches.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    vendor_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    document_type = Column(String(50), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)
    uploaded_by = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    processing_status = Column(String(50), default="PENDING", nullable=False)
    extracted_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    company = relationship("Company", back_populates="documents")
    batch = relationship("Batch", back_populates="documents")
    vendor = relationship("Vendor", back_populates="documents")
    uploader = relationship("User", foreign_keys=[uploaded_by])

    __table_args__ = (
        Index("ix_documents_company_batch", "company_id", "batch_id"),
        Index("ix_documents_company_type", "company_id", "document_type"),
        Index("ix_documents_processing_status", "company_id", "processing_status"),
    )
