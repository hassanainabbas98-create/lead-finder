"""Opportunity Scoring Engine evaluating business sales relevance transparently."""

from typing import List, Tuple, Optional
from pydantic import BaseModel
from app.services.scoring.rules import SCORE_WEIGHTS, HIGH_OPPORTUNITY_CATEGORIES, get_priority_tier


class ScoringResult(BaseModel):
    score: int
    priority: str
    reasons: List[str]


class OpportunityScoringEngine:
    """Transparent rule-based scoring engine evaluating business sales potential."""

    def __init__(self, weights: Optional[dict] = None):
        self.weights = weights or SCORE_WEIGHTS

    def evaluate(self, business, latest_audit=None) -> ScoringResult:
        """
        Evaluate a business and its latest website audit to compute an opportunity score.

        Returns:
            ScoringResult containing numeric score (0-100), priority tier, and explicit reason items.
        """
        score = 0
        reasons = []

        # 1. Website Presence Signals
        website = getattr(business, "website", None)
        website_status = getattr(business, "website_status", "Not Checked")

        if not website or website_status == "No Website Listed":
            pts = self.weights.get("no_website_listed", 35)
            score += pts
            reasons.append(f"No official website listed in public records (+{pts} pts: High need for website development)")
        elif website_status in ("Website Inaccessible", "Website Check Failed"):
            pts = self.weights.get("website_inaccessible", 25)
            score += pts
            reasons.append(f"Website is currently inaccessible or failing (+{pts} pts: Needs recovery or modern redesign)")
        else:
            # Website found
            pts = self.weights.get("has_website", 5)
            score += pts
            reasons.append(f"Existing web presence found (+{pts} pts: Candidate for digital upgrades & AI bots)")

            # Inspect feature audit signals if available
            if latest_audit:
                if latest_audit.has_online_booking == "Not Detected":
                    pts = self.weights.get("no_booking_detected", 15)
                    score += pts
                    reasons.append(f"No online booking functionality detected (+{pts} pts: Opportunity for appointment scheduling)")

                if latest_audit.has_chatbot == "Not Detected":
                    pts = self.weights.get("no_chatbot_detected", 15)
                    score += pts
                    reasons.append(f"No customer chatbot detected (+{pts} pts: Opportunity for AI support or WhatsApp bot)")

                cat_lower = (getattr(business, "category", "") or "").lower()
                if latest_audit.has_online_ordering == "Not Detected" and any(k in cat_lower for k in ("restaurant", "cafe", "food", "bakery")):
                    pts = self.weights.get("no_ordering_detected", 10)
                    score += pts
                    reasons.append(f"No direct food ordering detected (+{pts} pts: Opportunity for direct ordering system)")

                if latest_audit.is_mobile_friendly == "Not Detected":
                    pts = self.weights.get("not_mobile_friendly", 10)
                    score += pts
                    reasons.append(f"Website lacks mobile viewport configuration (+{pts} pts: Needs mobile redesign)")

                if not latest_audit.has_https:
                    pts = self.weights.get("no_https", 10)
                    score += pts
                    reasons.append(f"Website lacks secure HTTPS certificate (+{pts} pts: Security upgrade needed)")

        # 2. Contact Outreach Channels
        phone = getattr(business, "phone", None)
        whatsapp = getattr(business, "whatsapp", None)
        email = getattr(business, "email", None)

        if phone:
            pts = self.weights.get("has_phone", 15)
            score += pts
            reasons.append(f"Public phone number available (+{pts} pts: Actionable for phone calls or AI voice agent demo)")

        if whatsapp:
            pts = self.weights.get("has_whatsapp", 10)
            score += pts
            reasons.append(f"Public WhatsApp number available (+{pts} pts: Direct messaging channel)")

        if email:
            pts = self.weights.get("has_email", 10)
            score += pts
            reasons.append(f"Public email address available (+{pts} pts: Email outreach channel)")

        # 3. Target Industry Match
        cat = (getattr(business, "category", "") or "").lower()
        if any(target in cat for target in HIGH_OPPORTUNITY_CATEGORIES):
            pts = self.weights.get("target_industry_match", 10)
            score += pts
            reasons.append(f"Industry aligns with high-demand digital agency services (+{pts} pts)")

        # Enforce bounds [10, 100]
        final_score = max(10, min(100, score))
        priority = get_priority_tier(final_score)

        return ScoringResult(score=final_score, priority=priority, reasons=reasons)
