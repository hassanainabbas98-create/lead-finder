"""Background Search and Audit Job tracking models."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
)
from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class SearchJob(Base):
    """Background business discovery task."""

    __tablename__ = "search_jobs"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    category = Column(String(100), nullable=False)
    city = Column(String(100), nullable=False)
    country = Column(String(100), nullable=False)
    radius_meters = Column(Integer, default=5000)
    max_results = Column(Integer, default=100)

    # Job execution state: 'Pending', 'Running', 'Completed', 'Failed', 'Cancelled'
    status = Column(String(50), default="Pending", nullable=False, index=True)
    progress_count = Column(Integer, default=0)
    total_found = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utc_now, nullable=False)
    completed_at = Column(DateTime, nullable=True)


class AuditJob(Base):
    """Batch website auditing background task."""

    __tablename__ = "audit_jobs"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    total_targets = Column(Integer, default=0)
    completed_count = Column(Integer, default=0)

    # State: 'Pending', 'Running', 'Completed', 'Failed', 'Cancelled'
    status = Column(String(50), default="Pending", nullable=False, index=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utc_now, nullable=False)
    completed_at = Column(DateTime, nullable=True)
