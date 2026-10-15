"""Automated tests for Feature Detectors (Chatbot, Booking, Ordering), Opportunity Scoring, and Service Recommendations."""

import pytest
from app.services.website.detectors import detect_features_from_html
from app.services.scoring import OpportunityScoringEngine
from app.services.recommendation import ServiceRecommendationEngine
from app.models.business import Business
from app.models.audit import WebsiteAudit


def test_feature_detectors_booking_and_chat():
    """Verify detection of online booking widgets and chatbot scripts."""
    html_with_features = """
    <html>
    <head>
        <title>Grand Barber Studio</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <script src="//code.tidio.co/xyz123.js" async></script>
    </head>
    <body>
        <div id="booking-section">
            <a href="https://calendly.com/grandbarber/appointment">Schedule Appointment</a>
            <button class="btn">Book Now</button>
        </div>
        <div id="order-section">
            <a href="https://order.online/store/grand-barber">Order Grooming Kit</a>
        </div>
        <div id="portal-section">
            <a href="/client-area/login">Client Login</a>
        </div>
    </body>
    </html>
    """

    detections = detect_features_from_html(html_with_features, has_https=True)
    assert detections.has_online_booking == "Detected"
    assert any("calendly" in e.lower() or "booking" in e.lower() for e in detections.booking_evidence)

    assert detections.has_chatbot == "Detected"
    assert any("tidio" in e.lower() for e in detections.chatbot_evidence)

    assert detections.has_online_ordering == "Detected"
    assert detections.has_customer_portal == "Detected"
    assert detections.is_mobile_friendly == "Detected"
    assert detections.has_https is True


def test_feature_detectors_negative_case():
    """Verify that a basic HTML page reports Not Detected for features."""
    plain_html = """
    <html>
    <head><title>Simple Local Shop</title></head>
    <body>
        <p>Welcome to our family owned grocery store since 1990.</p>
        <p>Visit us on Main Street.</p>
    </body>
    </html>
    """
    detections = detect_features_from_html(plain_html, has_https=False)
    assert detections.has_online_booking == "Not Detected"
    assert detections.has_chatbot == "Not Detected"
    assert detections.has_online_ordering == "Not Detected"
    assert detections.has_customer_portal == "Not Detected"
    assert detections.is_mobile_friendly == "Not Detected"
    assert detections.has_https is False


def test_opportunity_scoring_no_website():
    """Verify scoring logic for a business with no website and actionable phone number."""
    engine = OpportunityScoringEngine()
    b = Business(
        source="osm",
        source_id="osm:node/101",
        name="Lahore Cuts",
        category="barber",
        website=None,
        website_status="No Website Listed",
        phone="+923001234567",
        whatsapp="+923001234567",
    )

    result = engine.evaluate(b, latest_audit=None)
    # Expected points: No site (35) + phone (15) + whatsapp (10) + target industry (10) = 70 points
    assert result.score >= 70
    assert result.priority == "High Priority"
    assert any("No official website" in r for r in result.reasons)
    assert any("phone number" in r for r in result.reasons)


def test_opportunity_scoring_with_audited_features():
    """Verify score adjustment when an audit reveals no booking and no chatbot."""
    engine = OpportunityScoringEngine()
    b = Business(
        source="osm",
        source_id="osm:node/102",
        name="Metro Medical Clinic",
        category="clinic",
        website="https://metromedical.example.com",
        website_status="Website Found",
        phone="+924231112233",
    )
    audit = WebsiteAudit(
        url_checked="https://metromedical.example.com",
        status="Success",
        http_status=200,
        has_online_booking="Not Detected",
        has_chatbot="Not Detected",
        is_mobile_friendly="Detected",
        has_https=True,
    )

    result = engine.evaluate(b, latest_audit=audit)
    # Expected: Has site (5) + no booking (15) + no chatbot (15) + phone (15) + target industry (10) = 60 pts
    assert result.score >= 50
    assert result.priority in ("Medium Priority", "High Priority")
    assert any("booking functionality" in r for r in result.reasons)
    assert any("chatbot" in r for r in result.reasons)


def test_service_recommendations():
    """Verify that ServiceRecommendationEngine suggests relevant packages per industry & gaps."""
    engine = ServiceRecommendationEngine()

    # Barber without website
    recom_barber = engine.recommend(
        db=None,
        category="Barber Shop",
        website_status="No Website Listed",
    )
    assert "Website Development" in recom_barber.primary_service or "Booking" in recom_barber.primary_service
    assert any("Booking" in s for s in recom_barber.suggested_services)

    # Restaurant with website but no online ordering
    recom_rest = engine.recommend(
        db=None,
        category="Italian Restaurant",
        website_status="Website Found",
        has_ordering="Not Detected",
        has_booking="Not Detected",
    )
    assert any("Ordering" in s for s in recom_rest.suggested_services)
    assert "Restaurant" in recom_rest.pitch_value_hook

    # Clinic with website but no booking
    recom_clinic = engine.recommend(
        db=None,
        category="Dental Clinic",
        website_status="Website Found",
        has_booking="Not Detected",
    )
    assert any("Booking" in s or "Scheduling" in s for s in recom_clinic.suggested_services)
    assert any("Voice" in s for s in recom_clinic.suggested_services)
