"""Pydantic schemas for Saved Lead management."""

from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class SaveLeadRequest(BaseModel):
    business_id: int
    status: Optional[str] = "New"
    priority: Optional[str] = "Needs Review"
    notes: Optional[str] = None
    offered_service: Optional[str] = None
    last_contact_date: Optional[date] = None
    next_follow_up_date: Optional[date] = None
    list_id: Optional[int] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class BatchSaveLeadsRequest(BaseModel):
    business_ids: List[int]
    status: Optional[str] = "New"
    priority: Optional[str] = "Needs Review"
    list_id: Optional[int] = None


class UpdateLeadRequest(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    notes: Optional[str] = None
    offered_service: Optional[str] = None
    last_contact_date: Optional[date] = None
    next_follow_up_date: Optional[date] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class LeadListCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    color: Optional[str] = "#10b981"


class UpdateLeadStatusRequest(BaseModel):
    status: str


class WebhookDispatchRequest(BaseModel):
    business_ids: List[int]
    custom_webhook_url: Optional[str] = None
    source: Optional[str] = "leads_pipeline"

