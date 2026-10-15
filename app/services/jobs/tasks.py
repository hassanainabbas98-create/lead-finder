"""Asynchronous background tasks executed by worker threads."""

from typing import List, Optional, Dict, Any
from app.database import SessionLocal
from app.models.business import Business
from app.services.discovery import DiscoveryService
from app.services.website import WebsiteAuditService


def run_discovery_job(
    job_id: str,
    manager,
    category: str,
    city: str,
    country: str,
    state: Optional[str] = None,
    max_results: int = 50,
) -> Dict[str, Any]:
    """Execute live OpenStreetMap discovery in background thread."""
    manager.update_job(job_id, progress=20, message=f"Geocoding '{city}, {country}' and querying Overpass servers...")

    db = SessionLocal()
    try:
        discovery_service = DiscoveryService()
        manager.update_job(job_id, progress=45, message="Fetching tags and normalizing business entities...")
        res = discovery_service.discover_and_persist(
            db=db,
            category=category,
            city=city,
            country=country,
            state=state,
            max_results=max_results,
        )
        manager.update_job(job_id, progress=90, message="Persisting and calculating opportunity scores...")

        return {
            "success": res.get("success", False),
            "message": res.get("message", ""),
            "server_used": res.get("server_used", ""),
            "new_count": res.get("new_count", 0),
            "total_found": res.get("total_found", 0),
        }
    finally:
        db.close()


def run_batch_audit_job(
    job_id: str,
    manager,
    business_ids: List[int],
) -> Dict[str, Any]:
    """Execute batch digital audits on selected businesses in background thread."""
    total = len(business_ids)
    if total == 0:
        return {"audited_count": 0, "success_count": 0, "failed_count": 0}

    db = SessionLocal()
    audit_service = WebsiteAuditService()
    success_count = 0
    failed_count = 0

    try:
        for idx, bid in enumerate(business_ids):
            pct = int(10 + (idx / total) * 85)
            biz = db.query(Business).filter(Business.id == bid).first()
            biz_name = biz.name if biz else f"ID {bid}"

            manager.update_job(
                job_id,
                progress=pct,
                message=f"Auditing website ({idx + 1} of {total}): {biz_name}...",
            )

            try:
                res = audit_service.audit_business(db=db, business_id=bid)
                if res.get("success"):
                    success_count += 1
                else:
                    failed_count += 1
            except Exception:
                failed_count += 1

        return {
            "audited_count": total,
            "success_count": success_count,
            "failed_count": failed_count,
        }
    finally:
        db.close()
