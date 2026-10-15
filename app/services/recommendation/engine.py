"""Service Recommendation Engine suggesting tailored digital agency offerings."""

import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.models.rules import ServiceRule


class RecommendationResult(BaseModel):
    primary_service: str
    suggested_services: List[str]
    pitch_value_hook: str
    rationale: List[str]


class ServiceRecommendationEngine:
    """Generates tailored digital services and pitch hooks based on industry and audit signals."""

    def recommend(
        self,
        db: Optional[Session],
        category: str,
        website_status: str,
        has_booking: str = "Unknown",
        has_chatbot: str = "Unknown",
        has_ordering: str = "Unknown",
        is_mobile: str = "Unknown",
    ) -> RecommendationResult:
        """Analyze business category and audit findings to generate concrete service suggestions."""
        cat_lower = (category or "").lower()
        services: List[str] = []
        rationale: List[str] = []

        # 1. First consult DB custom ServiceRule if available
        custom_rule = None
        if db:
            rules = db.query(ServiceRule).filter(ServiceRule.is_active == True).all()
            for r in rules:
                if r.category_keyword.lower() in cat_lower or cat_lower in r.category_keyword.lower():
                    custom_rule = r
                    break

        # 2. Evaluate Core Website Presence
        if website_status in ("No Website Listed", None, ""):
            services.append("Custom Responsive Website Development")
            services.append("Mobile-Optimized Booking System")
            services.append("Google Business Profile Optimization")
            rationale.append("Business has no listed website in public mapping data.")
            pitch = f"Build an official modern website for {category.title()} to capture online search traffic and allow 24/7 client booking."

        elif website_status in ("Website Inaccessible", "Website Check Failed"):
            services.append("Modern Website Redesign & Hosting Migration")
            services.append("Website Recovery & SSL Security Hardening")
            rationale.append("Current website is inaccessible or down.")
            pitch = f"Recover and modernize the web presence for {category.title()} with guaranteed 99.9% uptime and fast loading speeds."

        else:
            # Website exists: check specific digital upgrades
            if has_booking == "Not Detected":
                services.append("Online Appointment Booking & Scheduling System")
                services.append("Automated WhatsApp / SMS Appointment Reminders")
                rationale.append("No online booking functionality was detected on the website.")

            if has_chatbot == "Not Detected":
                services.append("24/7 AI Customer Support & Inquiry Chatbot")
                services.append("WhatsApp Business Automation Widget")
                rationale.append("No conversational chatbot or automated inquiry tool was detected.")

            if is_mobile == "Not Detected":
                services.append("Mobile-First Responsive Website Redesign")
                rationale.append("Website lacks mobile viewport configuration.")

            if any(k in cat_lower for k in ("restaurant", "cafe", "food", "bakery")) and has_ordering == "Not Detected":
                services.append("Direct Online Food Ordering System")
                services.append("Digital QR Contactless Menu")
                rationale.append("No direct ordering system detected; can save 20-30% aggregator commission.")

            pitch = f"Enhance {category.title()}'s website with 24/7 automated booking and an AI chatbot to turn casual visitors into paying customers."

        # 3. Add Industry-Specific Add-ons
        if "clinic" in cat_lower or "doctor" in cat_lower or "dentist" in cat_lower:
            services.append("AI Voice-Call Agent for Front-Desk Scheduling")
            services.append("Patient Intake & Medical Consultation Portal")
        elif "restaurant" in cat_lower or "cafe" in cat_lower:
            services.append("AI Voice Agent for Table Reservations & Hours Info")
            services.append("Digital Menu & Inventory Tracking")
        elif "hotel" in cat_lower:
            services.append("Direct Room Reservation Engine")
            services.append("Bilingual Guest Concierge Chatbot")
        elif "school" in cat_lower or "college" in cat_lower:
            services.append("Student Admissions & Enrollment Portal")
            services.append("Admissions Inquiry Chatbot")
        elif "real estate" in cat_lower:
            services.append("Property Listings Search Portal")
            services.append("Automated Viewing Scheduling Calendar")
        elif "barber" in cat_lower or "salon" in cat_lower:
            services.append("Online Chair & Stylist Booking System")
            services.append("WhatsApp Automated No-Show Reduction")

        # Merge custom rule recommendations if present
        if custom_rule and custom_rule.services:
            try:
                rule_services = json.loads(custom_rule.services)
                for s in rule_services:
                    if s not in services:
                        services.insert(0, s)
                if custom_rule.pitch_hook:
                    pitch = custom_rule.pitch_hook
            except Exception:
                pass

        # Deduplicate while preserving order
        unique_services = list(dict.fromkeys(services))
        primary = unique_services[0] if unique_services else "Website Development & AI Automation"

        return RecommendationResult(
            primary_service=primary,
            suggested_services=unique_services[:5],
            pitch_value_hook=pitch,
            rationale=rationale,
        )
