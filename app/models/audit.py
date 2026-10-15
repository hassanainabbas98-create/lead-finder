"""Website Audit model."""

from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    Boolean,
)
from sqlalchemy.orm import relationship
from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class WebsiteAudit(Base):
    """Digital presence inspection records for a business website."""

    __tablename__ = "website_audits"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=True, index=True)
    url_checked = Column(String(500), nullable=False)
    http_status = Column(Integer, nullable=True)
    status = Column(String(50), nullable=False)  # 'Success', 'Inaccessible', 'Failed', 'Timeout', 'Invalid URL'

    # Observable feature detections ('Detected', 'Not Detected', 'Unknown')
    has_online_booking = Column(String(50), default="Unknown", nullable=False)
    has_chatbot = Column(String(50), default="Unknown", nullable=False)
    has_online_ordering = Column(String(50), default="Unknown", nullable=False)
    has_customer_portal = Column(String(50), default="Unknown", nullable=False)
    is_mobile_friendly = Column(String(50), default="Unknown", nullable=False)
    has_https = Column(Boolean, default=False)

    # Page metadata
    title = Column(String(500), nullable=True)
    meta_description = Column(Text, nullable=True)

    # Extracted contact details from HTML (JSON strings)
    extracted_emails = Column(Text, nullable=True)
    extracted_phones = Column(Text, nullable=True)
    extracted_socials = Column(Text, nullable=True)

    # Audit details & error notes
    evidence_notes = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)

    business = relationship("Business", back_populates="audits")
