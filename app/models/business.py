"""Business and BusinessContact models."""

from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Text,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Business(Base):
    """Discovered business entity from OpenStreetMap or other permitted sources."""

    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(50), default="osm", nullable=False)
    source_id = Column(String(100), nullable=False)  # e.g., 'osm:node/12345'
    name = Column(String(255), nullable=False, index=True)
    category = Column(String(100), nullable=True, index=True)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True, index=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True, index=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Contact & web presence fields
    website = Column(String(500), nullable=True)
    website_status = Column(
        String(50),
        default="Not Checked",
        nullable=False,
        index=True
    )  # 'Website Found', 'No Website Listed', 'Website Inaccessible', 'Website Check Failed', 'Not Checked'
    phone = Column(String(100), nullable=True)
    email = Column(String(255), nullable=True)
    whatsapp = Column(String(100), nullable=True)

    # Raw source payload / attributes (stored as JSON string for auditability)
    raw_data = Column(Text, nullable=True)

    # Opportunity signals summary
    opportunity_score = Column(Integer, default=0)
    opportunity_priority = Column(String(50), default="Needs Review")  # High Priority, Medium Priority, Low Priority, Needs Review
    suggested_service = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
    last_checked_at = Column(DateTime, nullable=True)

    # Relationships
    contacts = relationship("BusinessContact", back_populates="business", cascade="all, delete-orphan")
    audits = relationship("WebsiteAudit", back_populates="business", cascade="all, delete-orphan")
    saved_lead = relationship("SavedLead", back_populates="business", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("source", "source_id", name="uq_business_source_id"),
        Index("ix_business_location_cat", "category", "city", "country"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "source": self.source,
            "source_id": self.source_id,
            "name": self.name,
            "category": self.category,
            "address": self.address,
            "city": self.city,
            "state": self.state,
            "country": self.country,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "website": self.website,
            "website_status": self.website_status,
            "phone": self.phone,
            "email": self.email,
            "whatsapp": self.whatsapp,
            "opportunity_score": self.opportunity_score,
            "opportunity_priority": self.opportunity_priority,
            "suggested_service": self.suggested_service,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_checked_at": self.last_checked_at.isoformat() if self.last_checked_at else None,
        }


class BusinessContact(Base):
    """Discrete contact channel discovered for a business."""

    __tablename__ = "business_contacts"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(50), nullable=False)  # 'phone', 'email', 'whatsapp', 'social'
    value = Column(String(255), nullable=False)
    source = Column(String(50), default="osm")  # 'osm', 'website_audit', 'manual'
    verified = Column(Integer, default=0)  # 0 or 1
    created_at = Column(DateTime, default=utc_now, nullable=False)

    business = relationship("Business", back_populates="contacts")
