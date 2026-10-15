"""Automated tests for Website Presence, Reachability Checks, SSRF Guard, and Contact Extraction."""

import pytest
from unittest.mock import patch, MagicMock
from app.services.website.ssrf_guard import validate_url_safe, is_ip_forbidden
from app.services.website.contacts import extract_website_contacts, _is_valid_public_email
from app.services.website.checker import SafeWebsiteChecker, WebsiteCheckResult
from app.services.website.service import WebsiteAuditService
from app.models.business import Business, BusinessContact
from app.models.audit import WebsiteAudit


def test_ssrf_blocking_private_and_loopback():
    """Verify SSRF guard blocks localhost, internal IPs, and non-http schemes."""
    # Loopback & Cloud metadata
    assert is_ip_forbidden("127.0.0.1") is True
    assert is_ip_forbidden("127.0.1.1") is True
    assert is_ip_forbidden("169.254.169.254") is True
    assert is_ip_forbidden("10.0.0.1") is True
    assert is_ip_forbidden("192.168.1.50") is True
    assert is_ip_forbidden("172.16.0.1") is True
    assert is_ip_forbidden("::1") is True

    # Public IPs should be permitted
    assert is_ip_forbidden("8.8.8.8") is False
    assert is_ip_forbidden("1.1.1.1") is False

    # URL Scheme checks
    is_safe, reason, _ = validate_url_safe("file:///etc/passwd")
    assert is_safe is False
    assert "Only http and https" in reason

    is_safe_ftp, _, _ = validate_url_safe("ftp://ftp.example.com")
    assert is_safe_ftp is False

    # Direct localhost hostname
    is_safe_lh, reason_lh, _ = validate_url_safe("http://localhost:8000/api")
    assert is_safe_lh is False
    assert "blocked by SSRF guard" in reason_lh

    is_safe_ip, reason_ip, _ = validate_url_safe("http://127.0.0.1/admin")
    assert is_safe_ip is False


def test_contact_extraction_from_html():
    """Verify HTML parsing extracts public emails, phones, WhatsApp links, and viewport metadata."""
    sample_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Royal Grooming Studio - Premium Barber in Lahore</title>
        <meta name="description" content="Experience master haircutting and grooming services in Lahore.">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body>
        <header>
            <a href="mailto:contact@royalgrooming.pk?subject=Appointment">Email Us</a>
            <a href="tel:+92421234567">Call Now</a>
            <a href="https://wa.me/923001234567">Chat on WhatsApp</a>
            <a href="https://facebook.com/royalgroomingpk">Facebook Page</a>
            <a href="https://instagram.com/royalgroomingpk">Instagram</a>
        </header>
        <main>
            <p>For inquiries, please reach out to hello@royalgrooming.pk or visit us.</p>
            <p>Fake asset link should be ignored: <a href="mailto:logo@2x.png">Logo</a></p>
        </main>
    </body>
    </html>
    """

    contacts = extract_website_contacts(sample_html, base_url="https://royalgrooming.pk")

    assert contacts.title == "Royal Grooming Studio - Premium Barber in Lahore"
    assert "master haircutting" in contacts.meta_description
    assert contacts.has_viewport is True

    # Emails
    assert "contact@royalgrooming.pk" in contacts.emails
    assert "hello@royalgrooming.pk" in contacts.emails
    assert "logo@2x.png" not in contacts.emails

    # Phones
    assert any("421234567" in p for p in contacts.phones)

    # WhatsApp
    assert any("923001234567" in w for w in contacts.whatsapps)

    # Socials
    assert "facebook" in contacts.socials
    assert "instagram" in contacts.socials


def test_email_validation_filters():
    """Verify filter excludes bogus and asset emails."""
    assert _is_valid_public_email("info@business.com") is True
    assert _is_valid_public_email("booking@dental-care.org") is True
    assert _is_valid_public_email("icon@button.png") is False
    assert _is_valid_public_email("banner@hero.svg") is False
    assert _is_valid_public_email("user@example.com") is False
    assert _is_valid_public_email("notanemail") is False


def test_safe_website_checker_status_classification():
    """Verify HTTP status classification into Website Found, Inaccessible, or Failed."""
    checker = SafeWebsiteChecker(timeout_seconds=5)

    # Test "No Website Listed"
    none_res = checker.check_website(None)
    assert none_res.status_classification == "No Website Listed"

    # Mock successful HTTP 200
    with patch("requests.Session.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.is_redirect = False
        mock_resp.headers = {"Content-Type": "text/html"}
        mock_resp.iter_content.return_value = ["<html><head><title>Test</title></head><body>OK</body></html>"]
        mock_get.return_value = mock_resp

        # Mock ssrf validation to pass for test domain
        with patch("app.services.website.checker.validate_url_safe", return_value=(True, "https://example.com", "example.com")):
            res = checker.check_website("https://example.com")
            assert res.status_classification == "Website Found"
            assert res.http_status == 200
            assert res.has_https is True
            assert "OK" in res.html_content

    # Mock HTTP 404 Inaccessible
    with patch("requests.Session.get") as mock_get_404:
        mock_resp_404 = MagicMock()
        mock_resp_404.status_code = 404
        mock_resp_404.is_redirect = False
        mock_resp_404.headers = {"Content-Type": "text/html"}
        mock_resp_404.iter_content.return_value = ["Not Found"]
        mock_get_404.return_value = mock_resp_404

        with patch("app.services.website.checker.validate_url_safe", return_value=(True, "https://example.com/missing", "example.com")):
            res_404 = checker.check_website("https://example.com/missing")
            assert res_404.status_classification == "Website Inaccessible"
            assert res_404.http_status == 404


def test_website_audit_service_business_flow(db_session):
    """Test full audit flow on a business record, persisting audit and updating contacts."""
    b = Business(
        source="osm",
        source_id="osm:node/88801",
        name="Lahore Dental Art",
        city="Lahore",
        country="Pakistan",
        website="https://lahoredentalart.pk",
        website_status="Not Checked",
    )
    db_session.add(b)
    db_session.commit()

    sample_html = """
    <html>
    <head><title>Lahore Dental Art - Modern Dentistry</title><meta name="viewport" content="width=device-width"></head>
    <body>
        <a href="mailto:info@lahoredentalart.pk">Email</a>
        <a href="tel:+924299887766">Phone</a>
    </body>
    </html>
    """

    mock_checker = MagicMock(spec=SafeWebsiteChecker)
    mock_checker.check_website.return_value = WebsiteCheckResult(
        url="https://lahoredentalart.pk",
        final_url="https://lahoredentalart.pk",
        http_status=200,
        status_classification="Website Found",
        has_https=True,
        html_content=sample_html,
        response_time_ms=120.0,
    )

    audit_service = WebsiteAuditService(checker=mock_checker)
    res = audit_service.audit_business(db=db_session, business_id=b.id)

    assert res["success"] is True
    assert res["status"] == "Success"
    assert res["website_classification"] == "Website Found"
    assert "info@lahoredentalart.pk" in res["emails"]
    assert any("4299887766" in p for p in res["phones"])

    # Verify database updates
    db_session.refresh(b)
    assert b.website_status == "Website Found"
    assert b.email == "info@lahoredentalart.pk"
    assert "+924299887766" in b.phone

    # Verify WebsiteAudit entry created
    audit = db_session.query(WebsiteAudit).filter(WebsiteAudit.business_id == b.id).first()
    assert audit is not None
    assert audit.http_status == 200
    assert audit.status == "Success"
    assert audit.is_mobile_friendly == "Detected"

    # Verify BusinessContact entry added
    contact = db_session.query(BusinessContact).filter(BusinessContact.business_id == b.id, BusinessContact.type == "email").first()
    assert contact is not None
    assert contact.value == "info@lahoredentalart.pk"
    assert contact.source == "website_audit"
