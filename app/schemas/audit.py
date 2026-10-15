"""Pydantic schemas for Website Audits."""

from typing import Optional, List
from pydantic import BaseModel, HttpUrl


class AuditRequest(BaseModel):
    business_id: Optional[int] = None
    target_url: Optional[str] = None


class BatchAuditRequest(BaseModel):
    business_ids: List[int]
