"""Test all application web routes and API endpoints."""

from app.models.business import Business
from app.models.lead import SavedLead


def test_dashboard_route(client):
    """Test dashboard loads with HTTP 200 and security headers."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Business Opportunity Finder" in response.text
    assert "X-Content-Type-Options" in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_all_pages_render(client):
    """Test that all primary application pages render successfully."""
    routes = [
        "/",
        "/search",
        "/leads",
        "/lists",
        "/tasks",
        "/audit",
        "/export",
        "/settings",
        "/about",
    ]
    for route in routes:
        res = client.get(route)
        assert res.status_code == 200, f"Failed on route {route}"


def test_lead_save_and_detail_route(client, db_session):
    """Test saving a business as a lead via API and viewing its detail page."""
    b = Business(
        source="osm",
        source_id="osm:node/3003",
        name="Grand City Hotel",
        city="Dubai",
        country="UAE",
        website="https://grandcityhotel.example.com",
    )
    db_session.add(b)
    db_session.commit()

    # Save as lead
    payload = {
        "business_id": b.id,
        "status": "New",
        "priority": "High Priority",
        "offered_service": "Room Booking Engine",
        "notes": "Target for Q4",
    }
    post_res = client.post("/api/leads/save", json=payload)
    assert post_res.status_code == 200
    assert post_res.json()["success"] is True

    # View lead detail page
    detail_res = client.get(f"/leads/view/{b.id}")
    assert detail_res.status_code == 200
    assert "Grand City Hotel" in detail_res.text


def test_export_endpoints(client, db_session):
    """Test CSV export endpoints return valid CSV media type."""
    b = Business(source="osm", source_id="osm:node/4004", name="Peshawar Dental", city="Peshawar")
    db_session.add(b)
    db_session.commit()

    res_b = client.get("/api/export/businesses")
    assert res_b.status_code == 200
    assert res_b.headers["content-type"].startswith("text/csv")
    assert "Peshawar Dental" in res_b.text

    res_l = client.get("/api/export/leads")
    assert res_l.status_code == 200
    assert res_l.headers["content-type"].startswith("text/csv")
