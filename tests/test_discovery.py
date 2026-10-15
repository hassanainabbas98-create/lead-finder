"""Automated tests for OpenStreetMap business discovery, normalization, and deduplication."""

import pytest
from unittest.mock import patch, MagicMock
from app.services.discovery.tag_mappings import resolve_osm_tags, CATEGORY_TAG_MAP
from app.services.discovery.geocoding import geocode_location
from app.services.discovery.overpass import OverpassDiscoveryProvider
from app.services.discovery.service import DiscoveryService
from app.models.business import Business, BusinessContact


def test_tag_mappings_structured_and_fallback():
    """Verify that known categories resolve to structured OSM tags and unknown categories fallback."""
    # Structured category
    tags, is_structured, name, service = resolve_osm_tags("Barber shops")
    assert is_structured is True
    assert any("hairdresser" in t or "barber" in t for t in tags)
    assert "Barber" in name

    tags_med, is_structured_med, name_med, _ = resolve_osm_tags("Clinic")
    assert is_structured_med is True
    assert any("clinic" in t for t in tags_med)

    # Unknown category fallback
    tags_fb, is_structured_fb, name_fb, _ = resolve_osm_tags("Specialty Pottery Studio")
    assert is_structured_fb is False
    assert any("Specialty Pottery Studio".lower() in t for t in tags_fb)


def test_geocoding_cache_resolution():
    """Verify pre-cached city bounding box resolution."""
    geo = geocode_location("Lahore", "Pakistan")
    assert geo is not None
    south, west, north, east, lat, lon = geo
    assert 31.0 < lat < 32.0
    assert 74.0 < lon < 75.0

    geo_dubai = geocode_location("Dubai", "UAE")
    assert geo_dubai is not None
    assert 24.0 < geo_dubai[4] < 26.0


def test_overpass_element_normalization():
    """Verify conversion of raw OSM JSON into DiscoveredRecord objects."""
    provider = OverpassDiscoveryProvider(servers=["https://test-overpass.local"])
    raw_elements = [
        {
            "type": "node",
            "id": 55501,
            "lat": 31.5204,
            "lon": 74.3587,
            "tags": {
                "name": "Lahore Hair Studio",
                "shop": "hairdresser",
                "addr:street": "Mall Road",
                "addr:housenumber": "12-B",
                "addr:city": "Lahore",
                "phone": "+92 42 111 222 333",
                "website": "https://lahorehairstudio.pk",
                "email": "info@lahorehairstudio.pk",
            },
        },
        {
            "type": "way",
            "id": 55502,
            "center": {"lat": 31.5210, "lon": 74.3590},
            "tags": {
                "name": "Classic Cuts",
                "shop": "hairdresser",
                "phone": "+92 300 9876543",
                # Note: No website listed
            },
        },
    ]

    records = provider._normalize_elements(
        elements=raw_elements,
        category="Barber Shop",
        city="Lahore",
        country="Pakistan",
        max_results=10,
    )

    assert len(records) == 2
    r1 = records[0]
    assert r1.source_id == "osm:node/55501"
    assert r1.name == "Lahore Hair Studio"
    assert r1.website_status == "Website Found"
    assert r1.website == "https://lahorehairstudio.pk"
    assert r1.phone == "+92 42 111 222 333"
    assert r1.email == "info@lahorehairstudio.pk"
    assert "Mall Road" in r1.address

    r2 = records[1]
    assert r2.source_id == "osm:way/55502"
    assert r2.name == "Classic Cuts"
    assert r2.website_status == "No Website Listed"
    assert r2.website is None
    assert r2.phone == "+92 300 9876543"


def test_discovery_service_persistence_and_deduplication(db_session):
    """Verify that DiscoveryService persists records and deduplicates without duplicate rows."""
    raw_elements = [
        {
            "type": "node",
            "id": 77701,
            "lat": 31.52,
            "lon": 74.35,
            "tags": {
                "name": "Prime Dental Clinic",
                "amenity": "dentist",
                "phone": "+923211234567",
            },
        }
    ]

    mock_provider = MagicMock(spec=OverpassDiscoveryProvider)
    from app.services.discovery.base import DiscoveredRecord
    mock_provider.search_businesses.return_value = (
        [
            DiscoveredRecord(
                source="osm",
                source_id="osm:node/77701",
                name="Prime Dental Clinic",
                category="Dental Clinic",
                city="Lahore",
                country="Pakistan",
                phone="+923211234567",
                website=None,
                website_status="No Website Listed",
            )
        ],
        "https://overpass-api.de/api/interpreter",
        "Retrieved 1 record",
    )

    service = DiscoveryService(provider=mock_provider)

    # First discovery run
    res1 = service.discover_and_persist(
        db=db_session,
        category="Dental Clinic",
        city="Lahore",
        country="Pakistan",
        max_results=10,
    )
    assert res1["success"] is True
    assert res1["new_count"] == 1
    assert res1["updated_count"] == 0

    # Verify record in database
    b = db_session.query(Business).filter(Business.source_id == "osm:node/77701").first()
    assert b is not None
    assert b.name == "Prime Dental Clinic"
    assert b.website_status == "No Website Listed"
    # Score should be high/medium because no website + phone available + target category
    assert b.opportunity_score >= 60
    assert b.opportunity_priority in ("High Priority", "Medium Priority")

    # Second discovery run with updated name (same source_id)
    mock_provider.search_businesses.return_value = (
        [
            DiscoveredRecord(
                source="osm",
                source_id="osm:node/77701",
                name="Prime Dental Clinic & Surgery",
                category="Dental Clinic",
                city="Lahore",
                country="Pakistan",
                phone="+923211234567",
                website="https://primedental.example.com",
                website_status="Website Found",
            )
        ],
        "https://overpass-api.de/api/interpreter",
        "Retrieved 1 record",
    )

    res2 = service.discover_and_persist(
        db=db_session,
        category="Dental Clinic",
        city="Lahore",
        country="Pakistan",
        max_results=10,
    )
    assert res2["new_count"] == 0
    assert res2["updated_count"] == 1

    # Ensure still exactly 1 record in database (no duplicates)
    total_matching = db_session.query(Business).filter(Business.source_id == "osm:node/77701").count()
    assert total_matching == 1

    # Verify updated fields
    updated_b = db_session.query(Business).filter(Business.source_id == "osm:node/77701").first()
    assert updated_b.name == "Prime Dental Clinic & Surgery"
    assert updated_b.website == "https://primedental.example.com"


def test_search_api_discover_endpoint(client, db_session):
    """Test POST /api/search/discover endpoint with mock provider."""
    with patch.object(DiscoveryService, "discover_and_persist") as mock_discover:
        mock_discover.return_value = {
            "success": True,
            "businesses": [],
            "total_found": 0,
            "new_count": 0,
            "updated_count": 0,
            "server_used": "mock_server",
            "message": "Mock discovery success",
        }

        payload = {
            "category": "Barber shop",
            "city": "Lahore",
            "country": "Pakistan",
            "max_results": 20,
        }
        res = client.post("/api/search/discover", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["message"] == "Mock discovery success"


def test_tag_mappings_plurals_and_variants():
    """Verify that plural category queries resolve correctly and generate complete search variants."""
    from app.services.discovery.tag_mappings import get_category_search_variants

    # Test plural "schools"
    tags, is_structured, name, _ = resolve_osm_tags("schools")
    assert is_structured is True
    assert name == "School / Academy"

    # Test plural "bakeries"
    tags_bakery, is_structured_b, name_b, _ = resolve_osm_tags("bakeries")
    assert is_structured_b is True
    assert name_b == "Bakery"

    # Test plural "pharmacies"
    tags_pharm, is_structured_p, name_p, _ = resolve_osm_tags("pharmacies")
    assert is_structured_p is True
    assert name_p == "Pharmacy"

    # Test variants for "schools"
    variants = get_category_search_variants("schools")
    assert "school" in variants
    assert "schools" in variants
    assert "School / Academy" in variants
    assert "School" in variants
    assert "Academy" in variants


def test_search_page_plural_category_matches_database(client, db_session):
    """Verify that searching for 'schools' in search page finds businesses stored as 'School / Academy'."""
    # Seed a business with category='School / Academy' and singular name
    school_b = Business(
        source="osm",
        source_id="osm:way/9998881",
        name="Peshawar Model High School",
        category="School / Academy",
        city="Peshawar",
        country="Pakistan",
        opportunity_score=85,
        opportunity_priority="High Priority",
    )
    db_session.add(school_b)
    db_session.commit()

    # Search with plural "schools" and discover=0 (database query mode)
    resp = client.get("/search?category=schools&city=Peshawar&country=Pakistan&discover=0")
    assert resp.status_code == 200
    assert "Peshawar Model High School" in resp.text
    assert "School / Academy" in resp.text

