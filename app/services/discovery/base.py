"""Base interface for business discovery providers."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class DiscoveredRecord(BaseModel):
    """Normalized business discovery record."""
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
    website_status: str = "Not Checked"
    phone: Optional[str] = None
    email: Optional[str] = None
    whatsapp: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None


class BaseDiscoveryProvider(ABC):
    """Abstract provider for business discovery."""

    @abstractmethod
    def search_businesses(
        self,
        category: str,
        city: str,
        country: str,
        state: Optional[str] = None,
        radius_meters: Optional[int] = 5000,
        max_results: int = 100,
    ) -> List[DiscoveredRecord]:
        """Discover businesses given location and category."""
        pass
