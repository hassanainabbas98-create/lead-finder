"""Pydantic schemas for Follow-up Tasks."""

from datetime import date
from typing import Optional
from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    saved_lead_id: int
    title: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    due_date: date
    priority: str = Field("Medium", pattern="^(High|Medium|Low)$")


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[date] = None
    priority: Optional[str] = None
    is_completed: Optional[bool] = None
