"""Feature detection engine for Online Booking, Chatbots, Online Ordering, and Customer Portals."""

import re
from typing import Tuple, List, Dict
from bs4 import BeautifulSoup
from pydantic import BaseModel


class FeatureDetections(BaseModel):
    has_online_booking: str  # 'Detected', 'Not Detected', 'Unknown'
    booking_evidence: List[str] = []

    has_chatbot: str  # 'Detected', 'Not Detected', 'Unknown'
    chatbot_evidence: List[str] = []

    has_online_ordering: str  # 'Detected', 'Not Detected', 'Unknown'
    ordering_evidence: List[str] = []

    has_customer_portal: str  # 'Detected', 'Not Detected', 'Unknown'
    portal_evidence: List[str] = []

    is_mobile_friendly: str  # 'Detected', 'Not Detected', 'Unknown'
    has_https: bool = False


# Known booking providers, widgets, and keywords
BOOKING_DOMAINS = [
    "calendly.com", "acuityscheduling.com", "fresha.com", "booksy.com",
    "mindbodyonline.com", "opentable.com", "resy.com", "simplybook.me",
    "setmore.com", "vagaro.com", "timely.com", "appointlet.com",
    "square.site/appointments", "zoho.com/bookings", "superpeer.com",
    "tidycal.com", "youcanbook.me", "genbook.com",
]

BOOKING_KEYWORDS = [
    "book now", "book online", "schedule appointment", "book appointment",
    "make reservation", "reserve a table", "book consultation", "reserve now",
    "online booking", "appointment scheduling",
]

# Known chatbot providers and widget signatures
CHATBOT_SIGNATURES = [
    ("intercom", ["widget.intercom.io", "intercomSettings", "intercom-container"]),
    ("tidio", ["code.tidio.co", "tidio-chat", "tidioChatApi"]),
    ("crisp", ["client.crisp.chat", "$crisp", "crisp-client"]),
    ("livechat", ["cdn.livechatinc.com", "__lc.license"]),
    ("drift", ["js.driftt.com", "drift.load"]),
    ("zendesk", ["static.zdassets.com/ekr/snippet.js", "zE('webWidget'"]),
    ("tawk.to", ["embed.tawk.to", "Tawk_API"]),
    ("hubspot", ["js.hs-scripts.com", "hubspot-messages-iframe"]),
    ("freshchat", ["wchat.freshchat.com", "window.fcWidget"]),
    ("jivosite", ["code.jivosite.com", "jivo_api"]),
    ("chaport", ["app.chaport.com", "window.chaport"]),
    ("smartsupp", ["smartsuppchat.com", "_smartsupp"]),
    ("voiceflow", ["voiceflow.com", "voiceflow-chat"]),
    ("botpress", ["botpress.cloud", "bp-web-widget"]),
]

# Known online ordering platforms and keywords
ORDERING_SIGNATURES = [
    ("shopify", ["cdn.shopify.com", "/cart.js", "Shopify.theme"]),
    ("woocommerce", ["woocommerce", "wc-add-to-cart"]),
    ("toast", ["toasttab.com"]),
    ("chownow", ["chownow.com"]),
    ("menufy", ["menufy.com"]),
    ("gloriafood", ["gloriafood.com"]),
    ("clover", ["clover.com/online-ordering"]),
    ("ubereats", ["ubereats.com"]),
    ("doordash", ["doordash.com"]),
    ("foodpanda", ["foodpanda"]),
    ("talabat", ["talabat.com"]),
    ("deliveroo", ["deliveroo.com"]),
]

ORDERING_KEYWORDS = [
    "order online", "order now", "view menu & order", "place order",
    "online ordering", "start order", "food delivery",
]

# Known customer portal patterns
PORTAL_KEYWORDS = [
    "client portal", "customer portal", "patient portal", "parent portal",
    "client login", "customer login", "my account", "sign in", "member login",
]


def detect_features_from_html(html_text: str, has_https: bool = False) -> FeatureDetections:
    """Analyze website HTML to detect observable digital features with evidence."""
    if not html_text or not html_text.strip():
        return FeatureDetections(
            has_online_booking="Unknown",
            has_chatbot="Unknown",
            has_online_ordering="Unknown",
            has_customer_portal="Unknown",
            is_mobile_friendly="Unknown",
            has_https=has_https,
        )

    try:
        soup = BeautifulSoup(html_text, "html.parser")
    except Exception:
        return FeatureDetections(
            has_online_booking="Unknown",
            has_chatbot="Unknown",
            has_online_ordering="Unknown",
            has_customer_portal="Unknown",
            is_mobile_friendly="Unknown",
            has_https=has_https,
        )

    html_lower = html_text.lower()

    # 1. Mobile friendliness via viewport meta tag
    viewport = soup.find("meta", attrs={"name": re.compile(r"^viewport$", re.I)})
    is_mobile_friendly = "Detected" if viewport else "Not Detected"

    # 2. Detect Online Booking
    booking_status, booking_evidence = _detect_booking(soup, html_lower)

    # 3. Detect Chatbot Widget
    chatbot_status, chatbot_evidence = _detect_chatbot(soup, html_lower)

    # 4. Detect Online Ordering
    ordering_status, ordering_evidence = _detect_ordering(soup, html_lower)

    # 5. Detect Customer Portal
    portal_status, portal_evidence = _detect_portal(soup, html_lower)

    return FeatureDetections(
        has_online_booking=booking_status,
        booking_evidence=booking_evidence,
        has_chatbot=chatbot_status,
        chatbot_evidence=chatbot_evidence,
        has_online_ordering=ordering_status,
        ordering_evidence=ordering_evidence,
        has_customer_portal=portal_status,
        portal_evidence=portal_evidence,
        is_mobile_friendly=is_mobile_friendly,
        has_https=has_https,
    )


def _detect_booking(soup: BeautifulSoup, html_lower: str) -> Tuple[str, List[str]]:
    """Inspect scripts, iframes, anchors, and buttons for booking signatures."""
    evidence = []

    # Check for known 3rd-party booking platform links or iframes
    for domain in BOOKING_DOMAINS:
        if domain in html_lower:
            evidence.append(f"Booking platform integration ({domain})")

    # Check for anchor links with booking intent
    for a in soup.find_all("a", href=True):
        href = a["href"].lower()
        text = a.get_text(strip=True).lower()

        if any(w in href for w in ("/book", "/appointment", "/reservation", "/schedule")):
            if not any("Booking link" in e for e in evidence):
                evidence.append(f"Booking link found: '{href[:60]}'")

        for kw in BOOKING_KEYWORDS:
            if kw in text:
                evidence.append(f"Booking action text: '{text[:40]}'")
                break

    # Check for button tags with booking intent
    for btn in soup.find_all(["button", "input"], attrs={"type": re.compile(r"^(button|submit)?$", re.I)}):
        btn_text = (btn.get_text(strip=True) or btn.get("value", "")).lower()
        for kw in BOOKING_KEYWORDS:
            if kw in btn_text:
                evidence.append(f"Booking button: '{btn_text[:40]}'")
                break

    if evidence:
        return ("Detected", list(dict.fromkeys(evidence))[:3])
    return ("Not Detected", [])


def _detect_chatbot(soup: BeautifulSoup, html_lower: str) -> Tuple[str, List[str]]:
    """Inspect scripts and DOM elements for recognizable chatbot widgets."""
    evidence = []

    # Check script tags & raw signatures
    for bot_name, signatures in CHATBOT_SIGNATURES:
        for sig in signatures:
            if sig.lower() in html_lower:
                evidence.append(f"{bot_name.title()} chat widget ({sig})")
                break

    # Check for generic chatbot element IDs or classes
    chat_elements = soup.find_all(attrs={"id": re.compile(r"(chat-widget|chatbot|live-chat|chat-launcher)", re.I)})
    if chat_elements and not evidence:
        evidence.append(f"Visible chat container: #{chat_elements[0].get('id')}")

    if evidence:
        return ("Detected", list(dict.fromkeys(evidence))[:3])
    return ("Not Detected", [])


def _detect_ordering(soup: BeautifulSoup, html_lower: str) -> Tuple[str, List[str]]:
    """Inspect for online ordering platforms, menus, and e-commerce carts."""
    evidence = []

    # Check for known online ordering platforms
    for platform_name, sigs in ORDERING_SIGNATURES:
        for sig in sigs:
            if sig.lower() in html_lower:
                evidence.append(f"{platform_name.title()} ordering integration")
                break

    # Check for ordering links or anchors
    for a in soup.find_all("a", href=True):
        href = a["href"].lower()
        text = a.get_text(strip=True).lower()

        if any(w in href for w in ("order.online", "/order", "order-now", "/menu", "/cart", "checkout")):
            evidence.append(f"Ordering link: '{href[:60]}'")
            break

        for kw in ORDERING_KEYWORDS:
            if kw in text:
                evidence.append(f"Ordering text: '{text[:40]}'")
                break

    if evidence:
        return ("Detected", list(dict.fromkeys(evidence))[:3])
    return ("Not Detected", [])


def _detect_portal(soup: BeautifulSoup, html_lower: str) -> Tuple[str, List[str]]:
    """Inspect for customer/patient/client login or account portals."""
    evidence = []

    for a in soup.find_all("a", href=True):
        href = a["href"].lower()
        text = a.get_text(strip=True).lower()

        if any(p in href for p in ("/login", "/signin", "/portal", "/client-area", "/my-account")):
            evidence.append(f"Portal login link: '{href[:50]}'")
            break

        for kw in PORTAL_KEYWORDS:
            if kw in text:
                evidence.append(f"Portal access link: '{text[:40]}'")
                break

    if evidence:
        return ("Detected", list(dict.fromkeys(evidence))[:2])
    return ("Not Detected", [])
