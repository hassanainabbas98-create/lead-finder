"""High-level Discovery Service orchestrating search, deduplication, and persistence."""

import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session

from app.models.business import Business, BusinessContact
from app.services.discovery.base import BaseDiscoveryProvider, DiscoveredRecord
from app.services.discovery.overpass import OverpassDiscoveryProvider
from app.services.scoring import OpportunityScoringEngine
from app.services.recommendation import ServiceRecommendationEngine


class DiscoveryService:
    """Orchestrates business discovery queries and database persistence."""

    def __init__(self, provider: Optional[BaseDiscoveryProvider] = None):
        self.provider = provider or OverpassDiscoveryProvider()
        self.scoring_engine = OpportunityScoringEngine()
        self.recommendation_engine = ServiceRecommendationEngine()

    def discover_and_persist(
        self,
        db: Session,
        category: str,
        city: str,
        country: str,
        state: Optional[str] = None,
        radius_meters: Optional[int] = 5000,
        max_results: int = 50,
    ) -> Dict[str, Any]:
        """
        Execute discovery query, deduplicate, and persist records in SQLite.

        Returns:
            Dict containing results, counts, and status messages.
        """
        # Step 1: Call Discovery Provider
        records, server_used, status_msg = self.provider.search_businesses(
            category=category,
            city=city,
            country=country,
            state=state,
            radius_meters=radius_meters,
            max_results=max_results,
        )

        if not records:
            return {
                "success": True,
                "businesses": [],
                "total_found": 0,
                "new_count": 0,
                "updated_count": 0,
                "server_used": server_used,
                "message": status_msg,
            }

        # Step 2: Service recommendation for this category
        recom = self.recommendation_engine.recommend(
            db=db,
            category=category,
            website_status="No Website Listed",
        )
        default_suggested_service = recom.primary_service

        # Step 3: Deduplicate and persist in database
        saved_businesses: List[Business] = []
        new_count = 0
        updated_count = 0
        now = datetime.now(timezone.utc)

        for rec in records:
            existing = (
                db.query(Business)
                .filter(Business.source == rec.source, Business.source_id == rec.source_id)
                .first()
            )

            # Compute preliminary opportunity score using scoring engine
            scoring_res = self.scoring_engine.evaluate(rec)

            # Tailor recommendation based on whether this specific record has a website
            rec_recom = self.recommendation_engine.recommend(
                db=db,
                category=rec.category or category,
                website_status=rec.website_status,
            )

            if existing:
                # Update existing record
                existing.name = rec.name
                if rec.category:
                    existing.category = rec.category
                if rec.address:
                    existing.address = rec.address
                if rec.phone and not existing.phone:
                    existing.phone = rec.phone
                if rec.email and not existing.email:
                    existing.email = rec.email
                if rec.whatsapp and not existing.whatsapp:
                    existing.whatsapp = rec.whatsapp
                if rec.website:
                    existing.website = rec.website
                    existing.website_status = "Website Found"
                existing.last_checked_at = now
                existing.opportunity_score = scoring_res.score
                existing.opportunity_priority = scoring_res.priority
                if not existing.suggested_service:
                    existing.suggested_service = rec_recom.primary_service
                saved_businesses.append(existing)
                updated_count += 1
            else:
                # Insert new business
                b = Business(
                    source=rec.source,
                    source_id=rec.source_id,
                    name=rec.name,
                    category=rec.category,
                    address=rec.address,
                    city=rec.city,
                    country=rec.country,
                    latitude=rec.latitude,
                    longitude=rec.longitude,
                    website=rec.website,
                    website_status=rec.website_status,
                    phone=rec.phone,
                    email=rec.email,
                    whatsapp=rec.whatsapp,
                    raw_data=json.dumps(rec.raw_data) if rec.raw_data else None,
                    opportunity_score=scoring_res.score,
                    opportunity_priority=scoring_res.priority,
                    suggested_service=rec_recom.primary_service,
                    created_at=now,
                    updated_at=now,
                    last_checked_at=now,
                )
                db.add(b)
                db.flush()  # populate b.id

                # Save contacts if present
                if rec.phone:
                    db.add(BusinessContact(business_id=b.id, type="phone", value=rec.phone, source="osm"))
                if rec.email:
                    db.add(BusinessContact(business_id=b.id, type="email", value=rec.email, source="osm"))
                if rec.whatsapp:
                    db.add(BusinessContact(business_id=b.id, type="whatsapp", value=rec.whatsapp, source="osm"))

                saved_businesses.append(b)
                new_count += 1

        db.commit()

        return {
            "success": True,
            "businesses": saved_businesses,
            "total_found": len(saved_businesses),
            "new_count": new_count,
            "updated_count": updated_count,
            "server_used": server_used,
            "message": status_msg,
        }
