"""
Decision, EmailEvent, and AuditEvent models for VendorIQ.
Follows Developer 3 specifications, unified with Neon PostgreSQL UUID schema.
"""
import uuid
from sqlalchemy import Column, String, Float, Text, DateTime, ForeignKey, JSON, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class BatchDecision(Base):
    __tablename__ = "batch_decisions"

    id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    batch_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    decision = Column(String(32), nullable=False)
    risk_score = Column(Float, nullable=False)
    risk_level = Column(String(32), nullable=False)
    reason = Column(Text, nullable=False)
    recommended_actions = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    batch = relationship("Batch", back_populates="decisions")
    email_events = relationship("EmailEvent", back_populates="decision")


class EmailEvent(Base):
    __tablename__ = "email_events"

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
    batch_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("batches.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    decision_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("batch_decisions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    recipient_email = Column(String(320), nullable=False)
    subject = Column(String(998), nullable=False)
    email_type = Column(String(32), nullable=False)
    status = Column(String(16), nullable=False, default="PENDING")
    provider = Column(String(32), nullable=False, default="GOOGLE_SMTP")
    sent_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    html_content = Column(Text, nullable=False)
    text_content = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    batch = relationship("Batch", back_populates="email_events")
    decision = relationship("BatchDecision", back_populates="email_events")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    event_type = Column(String(64), nullable=False, index=True)
    company_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    vendor_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    batch_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("batches.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    details = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
