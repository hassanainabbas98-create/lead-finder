"""Website Audit service orchestrating reachability, feature detectors, contact extraction, and audit history."""

import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app.models.business import Business, BusinessContact
from app.models.audit import WebsiteAudit
from app.models.lead import SavedLead
from app.services.website.checker import SafeWebsiteChecker, WebsiteCheckResult
from app.services.website.contacts import extract_website_contacts, ExtractedContacts
from app.services.website.detectors import detect_features_from_html, FeatureDetections
from app.services.scoring import OpportunityScoringEngine
from app.services.recommendation import ServiceRecommendationEngine


class WebsiteAuditService:
    """Orchestrates website presence checks, feature detection, contact extraction, and audit persistence."""

    def __init__(self, checker: Optional[SafeWebsiteChecker] = None):
        self.checker = checker or SafeWebsiteChecker()
        self.scoring_engine = OpportunityScoringEngine()
        self.recommendation_engine = ServiceRecommendationEngine()

    def audit_business(self, db: Session, business_id: int) -> Dict[str, Any]:
        """Audit the website of an existing business and record the audit."""
        business = db.query(Business).filter(Business.id == business_id).first()
        if not business:
            return {"success": False, "message": "Business record not found."}

        if not business.website:
            # Record audit as No Website Listed
            business.website_status = "No Website Listed"
            business.last_checked_at = datetime.now(timezone.utc)
            db.commit()
            return {
                "success": False,
                "status": "No Website Listed",
                "message": f"'{business.name}' does not have an official website listed in source records.",
            }

        check_res = self.checker.check_website(business.website)
        return self._persist_audit_results(db, check_res, business=business)

    def audit_url(self, db: Session, url: str) -> Dict[str, Any]:
        """Audit an arbitrary public URL safely with SSRF protection."""
        check_res = self.checker.check_website(url)
        return self._persist_audit_results(db, check_res, business=None)

    def _find_contact_page_url(self, html_content: str, base_url: str) -> Optional[str]:
        """Discover an internal contact or about page link from HTML."""
        try:
            from bs4 import BeautifulSoup
            from urllib.parse import urljoin, urlparse

            soup = BeautifulSoup(html_content, "html.parser")
            base_parsed = urlparse(base_url)
            base_netloc = base_parsed.netloc.lower()
            candidates = []

            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                lower_href = href.lower()
                text = (a.get_text() or "").strip().lower()

                if lower_href.startswith(("mailto:", "tel:", "javascript:", "#")):
                    continue

                is_contact = any(k in lower_href for k in ["/contact", "contact-us", "contact_us", "contact.", "reach-us", "get-in-touch"]) or \
                             any(k in text for k in ["contact", "get in touch", "reach us"])
                is_about = any(k in lower_href for k in ["/about", "about-us", "about_us"]) or "about" in text

                if is_contact or is_about:
                    full_url = urljoin(base_url, href)
                    parsed = urlparse(full_url)
                    if parsed.netloc.lower() == base_netloc and parsed.scheme in ("http", "https"):
                        priority = 0 if is_contact else 1
                        candidates.append((priority, full_url))

            if candidates:
                candidates.sort(key=lambda x: x[0])
                return candidates[0][1]
        except Exception:
            pass
        return None

    def _persist_audit_results(
        self,
        db: Session,
        res: WebsiteCheckResult,
        business: Optional[Business] = None,
    ) -> Dict[str, Any]:
        """Parse contacts and features from HTML, persist WebsiteAudit, and update business opportunity score."""
        contacts: Optional[ExtractedContacts] = None
        features: Optional[FeatureDetections] = None
        evidence_items = []

        if res.html_content:
            contacts = extract_website_contacts(res.html_content, base_url=res.final_url or res.url)
            features = detect_features_from_html(res.html_content, has_https=res.has_https)

            # Deep Contact Crawl: If no email found on homepage, safely inspect contact/about subpage
            if not contacts.emails and (res.final_url or res.url):
                contact_page_url = self._find_contact_page_url(res.html_content, res.final_url or res.url)
                if contact_page_url and contact_page_url != (res.final_url or res.url):
                    try:
                        contact_res = self.checker.check_website(contact_page_url)
                        if contact_res.html_content:
                            subpage_contacts = extract_website_contacts(
                                contact_res.html_content,
                                base_url=contact_res.final_url or contact_page_url
                            )
                            contacts.emails.update(subpage_contacts.emails)
                            contacts.phones.update(subpage_contacts.phones)
                            contacts.whatsapps.update(subpage_contacts.whatsapps)
                            if subpage_contacts.emails:
                                evidence_items.append(f"Discovered via contact page ({contact_page_url})")
                    except Exception:
                        pass

            if contacts.title:
                evidence_items.append(f"Title: {contacts.title}")

            # Evidence from features
            if features.booking_evidence:
                evidence_items.append(f"Booking: {', '.join(features.booking_evidence)}")
            if features.chatbot_evidence:
                evidence_items.append(f"Chatbot: {', '.join(features.chatbot_evidence)}")
            if features.ordering_evidence:
                evidence_items.append(f"Ordering: {', '.join(features.ordering_evidence)}")
            if features.portal_evidence:
                evidence_items.append(f"Portal: {', '.join(features.portal_evidence)}")

            # Evidence from contacts
            if contacts.emails:
                evidence_items.append(f"Emails: {', '.join(sorted(contacts.emails))}")
            if contacts.phones:
                evidence_items.append(f"Phones: {', '.join(sorted(contacts.phones))}")
            if contacts.whatsapps:
                evidence_items.append(f"WhatsApp: {', '.join(sorted(contacts.whatsapps))}")

        # Determine audit record status
        if res.status_classification == "Website Found":
            audit_status = "Success"
        elif res.status_classification == "Website Inaccessible":
            audit_status = "Inaccessible"
        else:
            audit_status = "Failed"

        audit_entry = WebsiteAudit(
            business_id=business.id if business else None,
            url_checked=res.url,
            http_status=res.http_status,
            status=audit_status,
            has_online_booking=features.has_online_booking if features else "Unknown",
            has_chatbot=features.has_chatbot if features else "Unknown",
            has_online_ordering=features.has_online_ordering if features else "Unknown",
            has_customer_portal=features.has_customer_portal if features else "Unknown",
            is_mobile_friendly=features.is_mobile_friendly if features else "Unknown",
            has_https=res.has_https,
            title=contacts.title if contacts else None,
            meta_description=contacts.meta_description if contacts else None,
            extracted_emails=json.dumps(sorted(list(contacts.emails))) if contacts and contacts.emails else None,
            extracted_phones=json.dumps(sorted(list(contacts.phones))) if contacts and contacts.phones else None,
            extracted_socials=json.dumps(contacts.socials) if contacts and contacts.socials else None,
            evidence_notes="; ".join(evidence_items) if evidence_items else res.error_message,
            error_message=res.error_message,
            created_at=datetime.now(timezone.utc),
        )
        db.add(audit_entry)

        # Update business entity and recalculate opportunity score
        if business:
            business.website_status = res.status_classification
            business.last_checked_at = datetime.now(timezone.utc)

            # Store any newly extracted contact details with Gmail prioritization
            if contacts:
                if contacts.emails:
                    # Sort emails: prioritize @gmail.com or @googlemail.com first
                    sorted_emails = sorted(
                        list(contacts.emails),
                        key=lambda em: (0 if ("@gmail." in em.lower() or "@googlemail." in em.lower()) else 1, em)
                    )
                    best_email = sorted_emails[0]
                    # Update if business had no email or if we found a Gmail and the current one is not Gmail
                    if not business.email or ("@gmail." in best_email and "@gmail." not in (business.email or "")):
                        business.email = best_email
                        db.add(BusinessContact(business_id=business.id, type="email", value=best_email, source="website_audit"))

                if contacts.phones and not business.phone:
                    first_phone = sorted(list(contacts.phones))[0]
                    business.phone = first_phone
                    db.add(BusinessContact(business_id=business.id, type="phone", value=first_phone, source="website_audit"))

                if contacts.whatsapps and not business.whatsapp:
                    first_wa = sorted(list(contacts.whatsapps))[0]
                    business.whatsapp = first_wa
                    db.add(BusinessContact(business_id=business.id, type="whatsapp", value=first_wa, source="website_audit"))

            # Recalculate Opportunity Score and Priorities
            scoring_res = self.scoring_engine.evaluate(business, audit_entry)
            business.opportunity_score = scoring_res.score
            business.opportunity_priority = scoring_res.priority

            # Recalculate Service Recommendation
            recom = self.recommendation_engine.recommend(
                db=db,
                category=business.category or "",
                website_status=business.website_status,
                has_booking=audit_entry.has_online_booking,
                has_chatbot=audit_entry.has_chatbot,
                has_ordering=audit_entry.has_online_ordering,
                is_mobile=audit_entry.is_mobile_friendly,
            )
            business.suggested_service = recom.primary_service

            # Sync with SavedLead if exists
            lead = db.query(SavedLead).filter(SavedLead.business_id == business.id).first()
            if lead:
                lead.opportunity_score = scoring_res.score
                lead.priority = scoring_res.priority
                lead.score_reasons = json.dumps(scoring_res.reasons)
                lead.suggested_services = json.dumps(recom.suggested_services)

        db.commit()
        db.refresh(audit_entry)

        return {
            "success": audit_status == "Success",
            "audit_id": audit_entry.id,
            "url": res.url,
            "status": audit_entry.status,
            "website_classification": res.status_classification,
            "http_status": res.http_status,
            "title": audit_entry.title,
            "has_online_booking": audit_entry.has_online_booking,
            "has_chatbot": audit_entry.has_chatbot,
            "has_online_ordering": audit_entry.has_online_ordering,
            "has_customer_portal": audit_entry.has_customer_portal,
            "is_mobile_friendly": audit_entry.is_mobile_friendly,
            "has_https": audit_entry.has_https,
            "emails": sorted(list(contacts.emails)) if contacts else [],
            "phones": sorted(list(contacts.phones)) if contacts else [],
            "whatsapps": sorted(list(contacts.whatsapps)) if contacts else [],
            "socials": contacts.socials if contacts else {},
            "evidence_notes": audit_entry.evidence_notes,
            "error_message": res.error_message,
        }
