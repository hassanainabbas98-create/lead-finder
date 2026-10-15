"""Public business contact extraction from permitted website HTML."""

import re
from urllib.parse import urlparse, parse_qs, unquote
from typing import List, Dict, Set, Optional, Tuple
from bs4 import BeautifulSoup

EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')
PHONE_REGEX = re.compile(r'(?:\+?[0-9]{1,4}[-.\s]?)?(?:\(?\d{2,5}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}\b')

# Exclusion sets for bogus or internal library placeholders
JUNK_EMAIL_DOMAINS = {
    "example.com", "domain.com", "email.com", "yourdomain.com", "site.com",
    "mysite.com", "wixpress.com", "sentry.io", "wordpress.com", "github.com"
}
JUNK_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.css', '.js')


class ExtractedContacts:
    """Container for public contact information and page metadata."""

    def __init__(self):
        self.emails: Set[str] = set()
        self.phones: Set[str] = set()
        self.whatsapps: Set[str] = set()
        self.socials: Dict[str, str] = {}
        self.title: Optional[str] = None
        self.meta_description: Optional[str] = None
        self.has_viewport: bool = False


def extract_website_contacts(html_content: str, base_url: str = "") -> ExtractedContacts:
    """Parse public business contacts and metadata safely from HTML."""
    results = ExtractedContacts()
    if not html_content:
        return results

    try:
        soup = BeautifulSoup(html_content, "html.parser")
    except Exception:
        return results

    # 1. Page Title & Meta Description
    title_tag = soup.find("title")
    if title_tag and title_tag.string:
        results.title = title_tag.string.strip()[:400]

    desc_tag = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
    if desc_tag and desc_tag.get("content"):
        results.meta_description = desc_tag["content"].strip()[:500]

    # 2. Viewport indicator
    viewport_tag = soup.find("meta", attrs={"name": re.compile(r"^viewport$", re.I)})
    if viewport_tag:
        results.has_viewport = True

    # 3. Anchor tags inspection (mailto, tel, whatsapp, socials)
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        lower_href = href.lower()

        # Email via mailto:
        if lower_href.startswith("mailto:"):
            email_part = href[7:].split("?")[0].strip()
            clean_email = unquote(email_part).lower()
            if _is_valid_public_email(clean_email):
                results.emails.add(clean_email)

        # Phone via tel:
        elif lower_href.startswith("tel:"):
            phone_part = href[4:].split("?")[0].strip()
            clean_phone = unquote(phone_part)
            if _is_valid_phone(clean_phone):
                results.phones.add(clean_phone)

        # WhatsApp link
        elif "wa.me/" in lower_href or "api.whatsapp.com/send" in lower_href or "whatsapp://" in lower_href:
            wa_num = _extract_whatsapp_number(href)
            if wa_num:
                results.whatsapps.add(wa_num)

        # Social channels
        elif "facebook.com/" in lower_href and not results.socials.get("facebook"):
            results.socials["facebook"] = href[:200]
        elif "instagram.com/" in lower_href and not results.socials.get("instagram"):
            results.socials["instagram"] = href[:200]
        elif "linkedin.com/" in lower_href and not results.socials.get("linkedin"):
            results.socials["linkedin"] = href[:200]
        elif ("twitter.com/" in lower_href or "x.com/" in lower_href) and not results.socials.get("twitter"):
            results.socials["twitter"] = href[:200]

    # 4. Text regex scan for emails (limited to prevent massive regex processing)
    # Remove script and style elements
    for s in soup(["script", "style", "noscript"]):
        s.extract()
    text = soup.get_text(separator=" ")

    # Scan for email patterns in visible text
    found_emails = EMAIL_REGEX.findall(text)
    for em in found_emails:
        em_lower = em.strip().lower()
        if _is_valid_public_email(em_lower):
            results.emails.add(em_lower)

    return results


def _is_valid_public_email(email: str) -> bool:
    """Validate email against common bogus formats and asset extensions."""
    if not email or "@" not in email:
        return False
    if any(email.endswith(ext) for ext in JUNK_EXTENSIONS):
        return False
    parts = email.split("@")
    if len(parts) != 2:
        return False
    domain = parts[1].lower()
    if domain in JUNK_EMAIL_DOMAINS:
        return False
    if len(parts[0]) > 64 or len(domain) > 255:
        return False
    return True


def _is_valid_phone(phone: str) -> bool:
    """Validate phone string has minimum reasonable digit count."""
    digits = re.sub(r'\D', '', phone)
    return 7 <= len(digits) <= 15


def _extract_whatsapp_number(url: str) -> Optional[str]:
    """Extract clean WhatsApp phone number or link from URL."""
    # Matches wa.me/123456789 or phone=123456789
    match = re.search(r'wa\.me/([0-9+]+)', url)
    if match:
        return match.group(1).strip()
    match_phone = re.search(r'[?&]phone=([0-9+]+)', url)
    if match_phone:
        return match_phone.group(1).strip()
    return url[:100]
