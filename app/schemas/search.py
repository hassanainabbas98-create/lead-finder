"""Pydantic schemas for business search queries and results."""

from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class SearchRequest(BaseModel):
    category: str = Field(..., min_length=2, max_length=100, description="Business category or keyword (e.g. Barber shop, Clinic, Restaurant)")
    city: str = Field(..., min_length=2, max_length=100, description="City name (e.g. Lahore, Dubai, Peshawar)")
    state: Optional[str] = Field(None, max_length=100, description="Region or state (optional)")
    country: str = Field(..., min_length=2, max_length=100, description="Country name (e.g. Pakistan, UAE, United States)")
    radius_meters: Optional[int] = Field(5000, ge=500, le=50000, description="Search radius in meters")
    max_results: int = Field(50, ge=5, le=300, description="Maximum number of business records to fetch")
    website_status_filter: Optional[str] = Field("all", description="all, no_website, has_website")
    contact_filter: Optional[str] = Field("all", description="all, has_phone, has_email, has_whatsapp")


class BusinessResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    source_id: str
    name: str
    category: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    website: Optional[str] = None
    website_status: str
    phone: Optional[str] = None
    email: Optional[str] = None
    whatsapp: Optional[str] = None
    opportunity_score: int
    opportunity_priority: str
    suggested_service: Optional[str] = None
    is_saved: bool = False
