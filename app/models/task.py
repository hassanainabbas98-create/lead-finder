"""Follow-up Tasks model."""

from datetime import datetime, date, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Date,
    Boolean,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship
from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class FollowUpTask(Base):
    """Actionable sales task associated with a saved lead."""

    __tablename__ = "follow_up_tasks"

    id = Column(Integer, primary_key=True, index=True)
    saved_lead_id = Column(Integer, ForeignKey("saved_leads.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(Date, nullable=False, index=True)
    priority = Column(String(50), default="Medium", nullable=False)  # 'High', 'Medium', 'Low'
    is_completed = Column(Boolean, default=False, nullable=False, index=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    lead = relationship("SavedLead", back_populates="tasks")

    __table_args__ = (
        Index("ix_tasks_due_status", "due_date", "is_completed"),
    )
