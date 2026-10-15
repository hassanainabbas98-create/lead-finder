"""Geocoding helper using Nominatim with caching and rate limiting."""

import time
import requests
from typing import Optional, Tuple, Dict
from app.config import settings

# In-memory geocoding cache: key is (city.lower(), country.lower())
# Stores: (south, west, north, east, lat, lon)
_GEOCODE_CACHE: Dict[Tuple[str, str], Tuple[float, float, float, float, float, float]] = {
    # Pre-populate well-known major cities to avoid immediate network round-trips
    ("lahore", "pakistan"): (31.35, 74.15, 31.65, 74.45, 31.5204, 74.3587),
    ("islamabad", "pakistan"): (33.55, 72.85, 33.78, 73.20, 33.6844, 73.0479),
    ("karachi", "pakistan"): (24.75, 66.85, 25.10, 67.25, 24.8607, 67.0011),
    ("peshawar", "pakistan"): (33.92, 71.45, 34.08, 71.65, 34.0151, 71.5249),
    ("dubai", "uae"): (24.95, 55.05, 25.35, 55.45, 25.2048, 55.2708),
    ("dubai", "united arab emirates"): (24.95, 55.05, 25.35, 55.45, 25.2048, 55.2708),
    ("london", "uk"): (51.28, -0.51, 51.69, 0.33, 51.5074, -0.1278),
    ("london", "united kingdom"): (51.28, -0.51, 51.69, 0.33, 51.5074, -0.1278),
    ("new york", "usa"): (40.49, -74.26, 40.92, -73.70, 40.7128, -74.0060),
    ("new york", "united states"): (40.49, -74.26, 40.92, -73.70, 40.7128, -74.0060),
}

_LAST_NOMINATIM_CALL: float = 0.0


def geocode_location(city: str, country: str, state: Optional[str] = None) -> Optional[Tuple[float, float, float, float, float, float]]:
    """
    Resolve city and country to bounding box and center coordinate.

    Returns:
        (south, west, north, east, center_lat, center_lon) or None if not found.
    """
    global _LAST_NOMINATIM_CALL
    cache_key = (city.strip().lower(), country.strip().lower())
    if cache_key in _GEOCODE_CACHE:
        return _GEOCODE_CACHE[cache_key]

    # Enforce Nominatim politeness (at least 1.1s between external requests)
    now = time.time()
    elapsed = now - _LAST_NOMINATIM_CALL
    if elapsed < 1.1:
        time.sleep(1.1 - elapsed)

    url = "https://nominatim.openstreetmap.org/search"
    query_str = f"{city}, {country}"
    if state and state.strip():
        query_str = f"{city}, {state}, {country}"

    params = {
        "q": query_str,
        "format": "json",
        "limit": 1,
        "addressdetails": 1,
    }
    headers = {
        "User-Agent": settings.NOMINATIM_USER_AGENT,
    }

    try:
        _LAST_NOMINATIM_CALL = time.time()
        resp = requests.get(url, params=params, headers=headers, timeout=12)
        if resp.status_code != 200:
            return None

        data = resp.json()
        if not data or len(data) == 0:
            return None

        result = data[0]
        # Nominatim returns boundingbox as [south, north, west, east] strings
        bbox = result.get("boundingbox", [])
        if len(bbox) == 4:
            south = float(bbox[0])
            north = float(bbox[1])
            west = float(bbox[2])
            east = float(bbox[3])
            center_lat = float(result.get("lat", (south + north) / 2))
            center_lon = float(result.get("lon", (west + east) / 2))

            geo_result = (south, west, north, east, center_lat, center_lon)
            _GEOCODE_CACHE[cache_key] = geo_result
            return geo_result

    except Exception as e:
        print(f"Nominatim geocoding error for {query_str}: {e}")
        return None

    return None
