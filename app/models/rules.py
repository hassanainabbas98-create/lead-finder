"""Service recommendation rules model."""

from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
)
from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class ServiceRule(Base):
    """Industry/category keyword mapping to potential digital services and pitch hooks."""

    __tablename__ = "service_rules"

    id = Column(Integer, primary_key=True, index=True)
    category_keyword = Column(String(100), unique=True, nullable=False, index=True)
    services = Column(Text, nullable=False)  # JSON array of suggested services
    pitch_hook = Column(Text, nullable=True)  # Value proposition context
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)


class AppSetting(Base):
    """Generic application configuration storage (e.g. n8n webhook URL)."""

    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

