"""SavedLead, LeadList, and LeadListItem models."""

from datetime import datetime, date, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Date,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship
from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class SavedLead(Base):
    """Personal prospect pipeline record linked to a discovered business."""

    __tablename__ = "saved_leads"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(
        Integer,
        ForeignKey("businesses.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Lead pipeline status:
    # 'New', 'To Review', 'Contacted', 'Interested', 'Follow-up Required', 'Converted', 'Not Interested'
    status = Column(String(50), default="New", nullable=False, index=True)

    # Priority: 'High Priority', 'Medium Priority', 'Low Priority', 'Needs Review'
    priority = Column(String(50), default="Needs Review", nullable=False, index=True)

    opportunity_score = Column(Integer, default=0)
    score_reasons = Column(Text, nullable=True)  # JSON array of reasons
    suggested_services = Column(Text, nullable=True)  # JSON array of suggested services
    offered_service = Column(String(255), nullable=True)

    notes = Column(Text, nullable=True)
    last_contact_date = Column(Date, nullable=True)
    next_follow_up_date = Column(Date, nullable=True, index=True)

    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    business = relationship("Business", back_populates="saved_lead")
    tasks = relationship("FollowUpTask", back_populates="lead", cascade="all, delete-orphan")
    list_items = relationship("LeadListItem", back_populates="saved_lead", cascade="all, delete-orphan")


class LeadList(Base):
    """Custom organizational list or campaign (e.g. 'Lahore Barber Shops')."""

    __tablename__ = "lead_lists"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    color = Column(String(30), default="#10b981")  # Hex color for badge
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    items = relationship("LeadListItem", back_populates="lead_list", cascade="all, delete-orphan")


class LeadListItem(Base):
    """Mapping between a SavedLead and a LeadList."""

    __tablename__ = "lead_list_items"

    id = Column(Integer, primary_key=True, index=True)
    list_id = Column(Integer, ForeignKey("lead_lists.id", ondelete="CASCADE"), nullable=False, index=True)
    saved_lead_id = Column(Integer, ForeignKey("saved_leads.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    lead_list = relationship("LeadList", back_populates="items")
    saved_lead = relationship("SavedLead", back_populates="list_items")

    __table_args__ = (
        UniqueConstraint("list_id", "saved_lead_id", name="uq_list_saved_lead"),
    )
