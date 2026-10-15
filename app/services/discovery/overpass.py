"""Overpass API client for OpenStreetMap business discovery."""

import json
import logging
import re
import requests
from typing import List, Optional, Tuple, Dict, Any

from app.config import settings
from app.services.discovery.base import BaseDiscoveryProvider, DiscoveredRecord
from app.services.discovery.tag_mappings import resolve_osm_tags
from app.services.discovery.geocoding import geocode_location

logger = logging.getLogger(__name__)
EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')


class OverpassDiscoveryProvider(BaseDiscoveryProvider):
    """Business discovery provider using OpenStreetMap Overpass API."""

    def __init__(self, servers: Optional[List[str]] = None, timeout_seconds: int = 45):
        if servers:
            self.servers = servers
        elif isinstance(settings.OVERPASS_SERVERS, list):
            self.servers = settings.OVERPASS_SERVERS
        else:
            self.servers = [
                "https://overpass-api.de/api/interpreter",
                "https://overpass.kumi.systems/api/interpreter",
                "https://lz4.overpass-api.de/api/interpreter",
            ]
        self.timeout_seconds = timeout_seconds

    def search_businesses(
        self,
        category: str,
        city: str,
        country: str,
        state: Optional[str] = None,
        radius_meters: Optional[int] = 5000,
        max_results: int = 100,
    ) -> Tuple[List[DiscoveredRecord], str, str]:
        """
        Query Overpass API for matching businesses.

        Returns:
            (records, server_used, status_message)
        """
        # Step 1: Resolve Category Tags
        osm_tags, is_structured, friendly_category, default_service = resolve_osm_tags(category)

        # Step 2: Geocode Location to Bounding Box
        geo = geocode_location(city=city, country=country, state=state)
        if not geo:
            error_msg = f"Could not determine geographical bounds for '{city}, {country}'. Please check spelling."
            return ([], "none", error_msg)

        south, west, north, east, center_lat, center_lon = geo
        bbox_str = f"{south},{west},{north},{east}"

        # Step 3: Build Overpass QL Query
        query_statements = []
        for tag in osm_tags:
            query_statements.append(f"node{tag}({bbox_str});")
            query_statements.append(f"way{tag}({bbox_str});")
            query_statements.append(f"relation{tag}({bbox_str});")

        query_body = "\n  ".join(query_statements)
        # Fetch sufficient headroom to account for unnamed elements or geometry deduplication
        query_limit = max(max_results * 2, 100)
        overpass_ql = f"""[out:json][timeout:{self.timeout_seconds}];
(
  {query_body}
);
out center {query_limit};"""

        # Step 4: Execute query with mirror server failover
        last_error = ""
        for server in self.servers:
            try:
                headers = {
                    "User-Agent": settings.NOMINATIM_USER_AGENT,
                    "Accept": "application/json",
                }
                resp = requests.post(
                    server,
                    data={"data": overpass_ql},
                    headers=headers,
                    timeout=self.timeout_seconds,
                )

                if resp.status_code == 200:
                    data = resp.json()
                    elements = data.get("elements", [])
                    records = self._normalize_elements(
                        elements=elements,
                        category=friendly_category,
                        city=city,
                        country=country,
                        max_results=max_results,
                    )
                    status_msg = f"Successfully retrieved {len(records)} records via {server.split('/')[2]}"
                    if not is_structured:
                        status_msg += " (via commercial keyword search)"
                    return (records, server, status_msg)

                elif resp.status_code in (429, 504, 502, 500):
                    last_error = f"Server {server} returned HTTP {resp.status_code}. Trying next mirror..."
                    continue
                else:
                    last_error = f"Server {server} returned HTTP {resp.status_code}: {resp.text[:100]}"
                    continue

            except (requests.Timeout, requests.ConnectionError) as e:
                last_error = f"Timeout/Connection error with {server}: {str(e)}"
                continue
            except Exception as e:
                last_error = f"Unexpected error querying {server}: {str(e)}"
                continue

        return ([], "all_mirrors_failed", f"Overpass query could not be completed: {last_error}")

    def _normalize_elements(
        self,
        elements: List[Dict[str, Any]],
        category: str,
        city: str,
        country: str,
        max_results: int,
    ) -> List[DiscoveredRecord]:
        """Convert raw OpenStreetMap JSON elements into normalized DiscoveredRecord objects."""
        records: List[DiscoveredRecord] = []
        seen_ids = set()

        for elem in elements:
            if len(records) >= max_results:
                break

            elem_type = elem.get("type", "node")
            elem_id = elem.get("id")
            source_id = f"osm:{elem_type}/{elem_id}"

            if source_id in seen_ids:
                continue
            seen_ids.add(source_id)

            tags = elem.get("tags", {})
            name = (
                tags.get("name")
                or tags.get("name:en")
                or tags.get("name:ur")
                or tags.get("int_name")
                or tags.get("official_name")
                or tags.get("short_name")
                or tags.get("brand")
                or tags.get("operator")
            )
            if not name:
                # If element has no name, provide an informative descriptor rather than skipping or fabricating
                shop_type = tags.get("shop") or tags.get("amenity") or tags.get("tourism") or category
                name = f"Unnamed {shop_type.replace('_', ' ').title()}"


            # Coordinates
            lat = elem.get("lat")
            lon = elem.get("lon")
            if lat is None and "center" in elem:
                lat = elem["center"].get("lat")
                lon = elem["center"].get("lon")

            # Address synthesis
            street = tags.get("addr:street")
            housenumber = tags.get("addr:housenumber")
            postcode = tags.get("addr:postcode")
            elem_city = tags.get("addr:city") or city
            elem_country = tags.get("addr:country") or country

            address_parts = [p for p in [housenumber, street, elem_city, postcode] if p]
            address = ", ".join(address_parts) if address_parts else None

            # Contact info extraction
            phone = tags.get("phone") or tags.get("contact:phone") or tags.get("mobile") or tags.get("contact:mobile")
            
            # Comprehensive email extraction checking multiple OSM tag conventions
            email = (
                tags.get("email")
                or tags.get("contact:email")
                or tags.get("operator:email")
                or tags.get("owner:email")
                or tags.get("contact:mail")
                or tags.get("user:email")
                or tags.get("admin:email")
            )

            # If no direct tag, scan textual fields (description, note, operator, comment) for emails/Gmail
            if not email:
                for candidate_key in ("description", "note", "comment", "operator", "brand", "source:contact"):
                    val = tags.get(candidate_key)
                    if val and isinstance(val, str) and "@" in val:
                        found_emails = EMAIL_REGEX.findall(val)
                        if found_emails:
                            # Prioritize @gmail.com if present
                            gmail_matches = [m for m in found_emails if "@gmail" in m.lower() or "@googlemail" in m.lower()]
                            email = gmail_matches[0] if gmail_matches else found_emails[0]
                            break

            website = tags.get("website") or tags.get("contact:website") or tags.get("url")
            whatsapp = tags.get("contact:whatsapp") or tags.get("whatsapp")

            # Clean website URL if present
            if website:
                website = website.strip()
                if not (website.startswith("http://") or website.startswith("https://")):
                    website = "https://" + website

            website_status = "Website Found" if website else "No Website Listed"

            record = DiscoveredRecord(
                source="osm",
                source_id=source_id,
                name=name.strip(),
                category=category,
                address=address,
                city=elem_city.strip() if elem_city else city,
                country=elem_country.strip() if elem_country else country,
                latitude=lat,
                longitude=lon,
                website=website,
                website_status=website_status,
                phone=phone.strip() if phone else None,
                email=email.strip().lower() if email else None,
                whatsapp=whatsapp.strip() if whatsapp else None,
                raw_data=tags,
            )
            records.append(record)

        return records
