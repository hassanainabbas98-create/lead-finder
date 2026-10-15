"""Search router for finding businesses and discovering prospects via OpenStreetMap."""

from typing import Optional, List
from fastapi import APIRouter, Request, Depends, Query, Body, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.models.business import Business
from app.models.lead import LeadList
from app.schemas.search import SearchRequest
from app.services.discovery import DiscoveryService, get_category_search_variants

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
discovery_service = DiscoveryService()


@router.get("/search", response_class=HTMLResponse)
def search_page(
    request: Request,
    category: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    website_filter: Optional[str] = Query("all"),
    contact_filter: Optional[str] = Query("all"),
    max_results: Optional[int] = Query(50),
    discover: Optional[str] = Query("1"),  # Default: perform live discovery if query submitted
    db: Session = Depends(get_db),
):
    """
    Render search page. If query parameters are supplied and discover=1,
    queries OpenStreetMap Overpass, persists and deduplicates records, and displays results.
    """
    results: List[Business] = []
    status_message: Optional[str] = None
    server_used: Optional[str] = None
    new_count: int = 0
    total_found: int = 0
    error_message: Optional[str] = None

    if category and city and country:
        discovered_business_ids: List[int] = []

        # Step 1: Perform discovery if requested
        if discover in ("1", "true", "yes"):
            try:
                res = discovery_service.discover_and_persist(
                    db=db,
                    category=category.strip(),
                    city=city.strip(),
                    country=country.strip(),
                    state=state.strip() if state else None,
                    max_results=max_results or 50,
                )
                status_message = res.get("message")
                server_used = res.get("server_used")
                new_count = res.get("new_count", 0)
                total_found = res.get("total_found", 0)
                if res.get("businesses"):
                    discovered_business_ids = [b.id for b in res["businesses"]]
                if not res.get("success") and not res.get("businesses"):
                    error_message = res.get("message")
            except Exception as e:
                error_message = f"Error during discovery: {str(e)}"

        # Step 2: Query database with filters applied
        query = db.query(Business)

        # Build category matching variants (supports plurals, stems, and OSM display categories)
        variants = get_category_search_variants(category.strip())
        cat_conditions = [Business.category.ilike(f"%{v}%") for v in variants]
        cat_conditions.extend([Business.name.ilike(f"%{v}%") for v in variants])

        if discovered_business_ids:
            query = query.filter(
                or_(
                    Business.id.in_(discovered_business_ids),
                    or_(*cat_conditions),
                )
            )
        else:
            query = query.filter(or_(*cat_conditions))

        query = query.filter(Business.city.ilike(f"%{city.strip()}%"))
        query = query.filter(Business.country.ilike(f"%{country.strip()}%"))

        if website_filter == "no_website":
            query = query.filter(
                or_(
                    Business.website == None,
                    Business.website == "",
                    Business.website_status == "No Website Listed",
                )
            )
        elif website_filter == "has_website":
            query = query.filter(Business.website != None, Business.website != "")

        if contact_filter == "has_gmail":
            query = query.filter(or_(Business.email.ilike("%@gmail.%"), Business.email.ilike("%@googlemail.%")))
        elif contact_filter == "has_email":
            query = query.filter(Business.email != None, Business.email != "")
        elif contact_filter == "has_phone":
            query = query.filter(Business.phone != None, Business.phone != "")

        results = query.order_by(Business.opportunity_score.desc()).limit(max_results or 50).all()
        if results and (total_found == 0 or total_found < len(results)):
            total_found = len(results)

    available_lists = db.query(LeadList).order_by(LeadList.name.asc()).all()

    return templates.TemplateResponse(
        request=request,
        name="search.html",
        context={
            "active_page": "search",
            "results": results,
            "status_message": status_message,
            "server_used": server_used,
            "new_count": new_count,
            "total_found": total_found,
            "error_message": error_message,
            "available_lists": available_lists,
        },
    )


@router.post("/api/search/discover")
def discover_businesses_api(
    payload: SearchRequest,
    db: Session = Depends(get_db),
):
    """API endpoint to trigger live OpenStreetMap discovery."""
    try:
        res = discovery_service.discover_and_persist(
            db=db,
            category=payload.category,
            city=payload.city,
            country=payload.country,
            state=payload.state,
            radius_meters=payload.radius_meters,
            max_results=payload.max_results,
        )
        return {
            "success": res.get("success", False),
            "message": res.get("message"),
            "server_used": res.get("server_used"),
            "new_count": res.get("new_count", 0),
            "total_found": res.get("total_found", 0),
            "records": [b.to_dict() for b in res.get("businesses", [])],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
