import datetime
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text

from app.models.base import Base


class BatchDecision(Base):
    __tablename__ = "batch_decisions"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=False, index=True)
    company_id = Column(String(255), nullable=True, index=True)
    decision = Column(String(32), nullable=False)
    risk_score = Column(Float, nullable=False)
    risk_level = Column(String(32), nullable=False)
    reason = Column(Text, nullable=False)
    recommended_actions = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)


class EmailEvent(Base):
    __tablename__ = "email_events"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(String(255), nullable=True, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False, index=True)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=False, index=True)
    decision_id = Column(Integer, ForeignKey("batch_decisions.id"), nullable=True)
    recipient_email = Column(String(320), nullable=False)
    subject = Column(String(998), nullable=False)
    email_type = Column(String(32), nullable=False)
    status = Column(String(16), nullable=False, default="PENDING")
    provider = Column(String(32), nullable=False, default="GOOGLE_SMTP")
    sent_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    html_content = Column(Text, nullable=False)
    text_content = Column(Text, nullable=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    company_id = Column(String(255), nullable=True, index=True)
    vendor_id = Column(Integer, nullable=True, index=True)
    batch_id = Column(Integer, nullable=True, index=True)
    details = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
