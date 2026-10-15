"""Export Center router with safe CSV streaming."""

from typing import Optional, List
from fastapi import APIRouter, Request, Depends, Response, Query, Body
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime, timezone

from app.database import get_db
from app.models.lead import SavedLead, LeadList, LeadListItem
from app.models.business import Business
from app.models.audit import WebsiteAudit
from app.services.export.csv_exporter import generate_safe_csv
from app.services.discovery import get_category_search_variants


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/export", response_class=HTMLResponse)
def get_export_page(request: Request, db: Session = Depends(get_db)):
    """Render Data Export Center."""
    lists = db.query(LeadList).order_by(LeadList.name.asc()).all()
    return templates.TemplateResponse(
        request=request,
        name="export.html",
        context={
            "active_page": "export",
            "lists": lists,
        },
    )


@router.get("/api/export/leads")
def export_saved_leads_csv(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    list_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Export saved pipeline leads to safe CSV with optional filters."""
    query = db.query(SavedLead).join(Business)

    if status and status.strip():
        query = query.filter(SavedLead.status == status.strip())
    if priority and priority.strip():
        query = query.filter(SavedLead.priority == priority.strip())
    if list_id:
        query = query.join(LeadListItem).filter(LeadListItem.list_id == list_id)

    leads = query.order_by(SavedLead.updated_at.desc()).all()
    return _build_leads_csv_response(leads, db)


@router.post("/api/export/selected-leads")
def export_selected_leads_csv(
    lead_ids: List[int] = Body(..., embed=True),
    db: Session = Depends(get_db),
):
    """Export specifically selected leads to safe CSV."""
    leads = db.query(SavedLead).filter(SavedLead.id.in_(lead_ids)).all()
    return _build_leads_csv_response(leads, db)


def _build_leads_csv_response(leads: List[SavedLead], db: Session) -> Response:
    """Helper to format and stream leads CSV with latest audit statuses."""
    headers = [
        "Business Name",
        "Category",
        "City",
        "Country",
        "Phone",
        "Email",
        "WhatsApp",
        "Website",
        "Website Status",
        "Chatbot Status",
        "Booking Status",
        "Opportunity Score",
        "Suggested Service",
        "Offered Service",
        "Pipeline Status",
        "Priority",
        "Last Contact Date",
        "Next Follow-up Date",
        "Notes",
        "Source ID",
    ]

    rows = []
    for l in leads:
        b = l.business
        # Look up latest audit feature signals
        latest_audit = (
            db.query(WebsiteAudit)
            .filter(WebsiteAudit.business_id == b.id)
            .order_by(WebsiteAudit.created_at.desc())
            .first()
        )

        chatbot_status = latest_audit.has_chatbot if latest_audit else "Unknown"
        booking_status = latest_audit.has_online_booking if latest_audit else "Unknown"

        rows.append([
            b.name,
            b.category or "",
            b.city or "",
            b.country or "",
            b.phone or "",
            b.email or "",
            b.whatsapp or "",
            b.website or "",
            b.website_status or "",
            chatbot_status,
            booking_status,
            l.opportunity_score or b.opportunity_score or 0,
            b.suggested_service or "",
            l.offered_service or "",
            l.status or "",
            l.priority or "",
            str(l.last_contact_date) if l.last_contact_date else "",
            str(l.next_follow_up_date) if l.next_follow_up_date else "",
            l.notes or "",
            b.source_id or "",
        ])

    csv_data = generate_safe_csv(headers, rows)
    filename = f"saved_leads_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/api/export/businesses")
def export_businesses_csv(
    city: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Export discovered businesses to safe CSV with optional filters."""
    query = db.query(Business)
    if city and city.strip():
        query = query.filter(Business.city.ilike(f"%{city.strip()}%"))
    if category and category.strip():
        variants = get_category_search_variants(category.strip())
        conds = [Business.category.ilike(f"%{v}%") for v in variants]
        conds.extend([Business.name.ilike(f"%{v}%") for v in variants])
        query = query.filter(or_(*conds))

    businesses = query.order_by(Business.id.desc()).all()
    return _build_businesses_csv_response(businesses, db)



@router.post("/api/export/selected-businesses")
def export_selected_businesses_csv(
    business_ids: List[int] = Body(..., embed=True),
    db: Session = Depends(get_db),
):
    """Export specifically selected discovered businesses to safe CSV."""
    businesses = db.query(Business).filter(Business.id.in_(business_ids)).all()
    return _build_businesses_csv_response(businesses, db)


def _build_businesses_csv_response(businesses: List[Business], db: Session) -> Response:
    """Helper to format and stream businesses CSV."""
    headers = [
        "Business Name",
        "Category",
        "Address",
        "City",
        "Country",
        "Latitude",
        "Longitude",
        "Phone",
        "Email",
        "WhatsApp",
        "Website",
        "Website Status",
        "Chatbot Status",
        "Booking Status",
        "Opportunity Priority",
        "Opportunity Score",
        "Suggested Service",
        "Source",
        "Source ID",
        "Discovered Date",
    ]

    rows = []
    for b in businesses:
        latest_audit = (
            db.query(WebsiteAudit)
            .filter(WebsiteAudit.business_id == b.id)
            .order_by(WebsiteAudit.created_at.desc())
            .first()
        )
        chatbot_status = latest_audit.has_chatbot if latest_audit else "Unknown"
        booking_status = latest_audit.has_online_booking if latest_audit else "Unknown"

        rows.append([
            b.name,
            b.category or "",
            b.address or "",
            b.city or "",
            b.country or "",
            b.latitude or "",
            b.longitude or "",
            b.phone or "",
            b.email or "",
            b.whatsapp or "",
            b.website or "",
            b.website_status or "",
            chatbot_status,
            booking_status,
            b.opportunity_priority or "",
            b.opportunity_score or 0,
            b.suggested_service or "",
            b.source or "",
            b.source_id or "",
            b.created_at.strftime("%Y-%m-%d %H:%M") if b.created_at else "",
        ])

    csv_data = generate_safe_csv(headers, rows)
    filename = f"discovered_businesses_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/api/export/audits")
def export_audits_csv(db: Session = Depends(get_db)):
    """Export website audit records to safe CSV."""
    audits = db.query(WebsiteAudit).order_by(WebsiteAudit.created_at.desc()).all()

    headers = [
        "Business Name",
        "URL Checked",
        "HTTP Status",
        "Audit Status",
        "Online Booking",
        "Chatbot",
        "Online Ordering",
        "Customer Portal",
        "Mobile Friendly",
        "HTTPS",
        "Audit Notes",
        "Audit Date",
    ]

    rows = []
    for a in audits:
        rows.append([
            a.business.name if a.business else "Manual URL",
            a.url_checked,
            a.http_status or "",
            a.status or "",
            a.has_online_booking or "",
            a.has_chatbot or "",
            a.has_online_ordering or "",
            a.has_customer_portal or "",
            a.is_mobile_friendly or "",
            "Yes" if a.has_https else "No",
            a.evidence_notes or "",
            a.created_at.strftime("%Y-%m-%d %H:%M") if a.created_at else "",
        ])

    csv_data = generate_safe_csv(headers, rows)
    filename = f"website_audits_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
