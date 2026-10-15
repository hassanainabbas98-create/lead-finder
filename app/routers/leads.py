"""Leads management router."""

from typing import Optional, List
from datetime import datetime, timezone
import httpx
from fastapi import APIRouter, Request, Depends, HTTPException, Query, Body
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.models.business import Business, BusinessContact
from app.models.lead import SavedLead, LeadList, LeadListItem
from app.models.audit import WebsiteAudit
from app.models.task import FollowUpTask
from app.models.rules import AppSetting
from app.schemas.lead import (
    SaveLeadRequest,
    UpdateLeadRequest,
    BatchSaveLeadsRequest,
    UpdateLeadStatusRequest,
    WebhookDispatchRequest,
)
from app.services.scoring import OpportunityScoringEngine
from app.services.recommendation import ServiceRecommendationEngine
from app.services.discovery import get_category_search_variants


router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


@router.get("/leads", response_class=HTMLResponse)
def get_leads_page(
    request: Request,
    q: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    list_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Render My Leads page with filters."""
    query = db.query(SavedLead).join(Business)

    if q and q.strip():
        term = f"%{q.strip()}%"
        variants = get_category_search_variants(q.strip())
        cat_conds = [Business.category.ilike(f"%{v}%") for v in variants]
        cat_conds.extend([
            Business.name.ilike(term),
            Business.city.ilike(term),
        ])
        query = query.filter(or_(*cat_conds))

    if status and status.strip():

        query = query.filter(SavedLead.status == status.strip())

    if priority and priority.strip():
        query = query.filter(SavedLead.priority == priority.strip())

    if list_id:
        query = query.join(LeadListItem).filter(LeadListItem.list_id == list_id)

    leads = query.order_by(SavedLead.updated_at.desc()).all()
    lists = db.query(LeadList).order_by(LeadList.name.asc()).all()

    return templates.TemplateResponse(
        request=request,
        name="leads.html",
        context={
            "active_page": "leads",
            "leads": leads,
            "lists": lists,
            "selected_list_id": list_id,
        },
    )


@router.get("/leads/view/{business_id}", response_class=HTMLResponse)
def view_lead_detail(
    request: Request,
    business_id: int,
    db: Session = Depends(get_db),
):
    """Render full profile details for a specific business/lead."""
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    lead = db.query(SavedLead).filter(SavedLead.business_id == business_id).first()
    latest_audit = (
        db.query(WebsiteAudit)
        .filter(WebsiteAudit.business_id == business_id)
        .order_by(WebsiteAudit.created_at.desc())
        .first()
    )
    tasks = []
    if lead:
        tasks = db.query(FollowUpTask).filter(FollowUpTask.saved_lead_id == lead.id).order_by(FollowUpTask.due_date.asc()).all()

    scoring_res = OpportunityScoringEngine().evaluate(business, latest_audit)
    recommendation_res = ServiceRecommendationEngine().recommend(
        db=db,
        category=business.category or "",
        website_status=business.website_status,
        has_booking=latest_audit.has_online_booking if latest_audit else "Unknown",
        has_chatbot=latest_audit.has_chatbot if latest_audit else "Unknown",
        has_ordering=latest_audit.has_online_ordering if latest_audit else "Unknown",
        is_mobile=latest_audit.is_mobile_friendly if latest_audit else "Unknown",
    )

    available_lists = db.query(LeadList).order_by(LeadList.name.asc()).all()
    assigned_list_ids = []
    if lead:
        assigned_list_ids = [item.list_id for item in lead.list_items]

    return templates.TemplateResponse(
        request=request,
        name="lead_detail.html",
        context={
            "active_page": "leads",
            "business": business,
            "lead": lead,
            "latest_audit": latest_audit,
            "tasks": tasks,
            "scoring_res": scoring_res,
            "recommendation_res": recommendation_res,
            "available_lists": available_lists,
            "assigned_list_ids": assigned_list_ids,
        },
    )


@router.post("/api/leads/save")
def save_or_update_lead(
    payload: SaveLeadRequest,
    db: Session = Depends(get_db),
):
    """Save a business as a prospect or update an existing lead's status/notes."""
    business = db.query(Business).filter(Business.id == payload.business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    lead = db.query(SavedLead).filter(SavedLead.business_id == payload.business_id).first()
    if not lead:
        lead = SavedLead(
            business_id=payload.business_id,
            status=payload.status or "New",
            priority=payload.priority or business.opportunity_priority or "Needs Review",
            opportunity_score=business.opportunity_score or 50,
            offered_service=payload.offered_service or business.suggested_service,
            notes=payload.notes,
            last_contact_date=payload.last_contact_date,
            next_follow_up_date=payload.next_follow_up_date,
        )
        db.add(lead)
        db.commit()
        db.refresh(lead)

        # If email or phone provided, update business record
        if payload.email:
            business.email = payload.email.strip().lower()
            db.add(BusinessContact(business_id=business.id, type="email", value=business.email, source="manual_entry"))
        if payload.phone:
            business.phone = payload.phone.strip()
            db.add(BusinessContact(business_id=business.id, type="phone", value=business.phone, source="manual_entry"))

        # If list_id provided, add to list
        if payload.list_id:
            item = LeadListItem(list_id=payload.list_id, saved_lead_id=lead.id)
            db.add(item)
            
        db.commit()
        return {"success": True, "message": "Lead saved to pipeline", "lead_id": lead.id}
    else:
        # Update existing lead
        if payload.status:
            lead.status = payload.status
        if payload.priority:
            lead.priority = payload.priority
        if payload.notes is not None:
            lead.notes = payload.notes
        if payload.offered_service is not None:
            lead.offered_service = payload.offered_service
        if payload.last_contact_date is not None:
            lead.last_contact_date = payload.last_contact_date
        if payload.next_follow_up_date is not None:
            lead.next_follow_up_date = payload.next_follow_up_date

        # If email provided, update business record and contact history
        if payload.email is not None:
            clean_email = payload.email.strip().lower() if payload.email.strip() else None
            business.email = clean_email
            existing_c = db.query(BusinessContact).filter(BusinessContact.business_id == business.id, BusinessContact.type == "email").first()
            if existing_c:
                existing_c.value = clean_email
            elif clean_email:
                db.add(BusinessContact(business_id=business.id, type="email", value=clean_email, source="manual_entry"))

        if payload.phone is not None:
            clean_phone = payload.phone.strip() if payload.phone.strip() else None
            business.phone = clean_phone
            existing_p = db.query(BusinessContact).filter(BusinessContact.business_id == business.id, BusinessContact.type == "phone").first()
            if existing_p:
                existing_p.value = clean_phone
            elif clean_phone:
                db.add(BusinessContact(business_id=business.id, type="phone", value=clean_phone, source="manual_entry"))

        db.commit()
        return {"success": True, "message": "Lead updated successfully", "lead_id": lead.id}


@router.post("/api/leads/batch-save")
def batch_save_leads(
    payload: BatchSaveLeadsRequest,
    db: Session = Depends(get_db),
):
    """Save multiple businesses to the lead pipeline simultaneously."""
    saved_count = 0
    for b_id in payload.business_ids:
        b = db.query(Business).filter(Business.id == b_id).first()
        if not b:
            continue
        existing_lead = db.query(SavedLead).filter(SavedLead.business_id == b_id).first()
        if not existing_lead:
            new_lead = SavedLead(
                business_id=b_id,
                status=payload.status or "New",
                priority=payload.priority or b.opportunity_priority or "Needs Review",
                opportunity_score=b.opportunity_score or 50,
                offered_service=b.suggested_service,
            )
            db.add(new_lead)
            db.flush()
            if payload.list_id:
                db.add(LeadListItem(list_id=payload.list_id, saved_lead_id=new_lead.id))
            saved_count += 1
        else:
            if payload.list_id:
                exists_in_list = db.query(LeadListItem).filter(
                    LeadListItem.list_id == payload.list_id,
                    LeadListItem.saved_lead_id == existing_lead.id
                ).first()
                if not exists_in_list:
                    db.add(LeadListItem(list_id=payload.list_id, saved_lead_id=existing_lead.id))

    db.commit()
    return {"success": True, "saved_count": saved_count, "total_submitted": len(payload.business_ids)}


@router.post("/api/leads/{lead_id}/add-to-list")
def add_lead_to_list(
    lead_id: int,
    list_id: int = Body(..., embed=True),
    db: Session = Depends(get_db),
):
    """Associate a lead with a custom list."""
    existing = db.query(LeadListItem).filter(
        LeadListItem.saved_lead_id == lead_id,
        LeadListItem.list_id == list_id
    ).first()
    if existing:
        return {"success": True, "message": "Lead is already in this list"}

    item = LeadListItem(saved_lead_id=lead_id, list_id=list_id)
    db.add(item)
    db.commit()
    return {"success": True, "message": "Lead added to list"}


@router.post("/api/leads/{lead_id}/remove-from-list")
def remove_lead_from_list(
    lead_id: int,
    list_id: int = Body(..., embed=True),
    db: Session = Depends(get_db),
):
    """Remove a lead from a custom list."""
    existing = db.query(LeadListItem).filter(
        LeadListItem.saved_lead_id == lead_id,
        LeadListItem.list_id == list_id
    ).first()
    if existing:
        db.delete(existing)
        db.commit()
    return {"success": True, "message": "Lead removed from list"}


@router.delete("/api/leads/{lead_id}")
def delete_lead(
    lead_id: int,
    db: Session = Depends(get_db),
):
    """Remove a lead from saved prospects pipeline."""
    lead = db.query(SavedLead).filter(SavedLead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    db.delete(lead)
    db.commit()
    return {"success": True, "message": "Lead deleted from pipeline"}


@router.post("/api/leads/{lead_id}/status")
def update_lead_status(
    lead_id: int,
    payload: UpdateLeadStatusRequest,
    db: Session = Depends(get_db),
):
    """Quickly update lead status (e.g. from Kanban drag-and-drop)."""
    lead = db.query(SavedLead).filter(SavedLead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead.status = payload.status
    db.commit()
    return {
        "success": True,
        "lead_id": lead.id,
        "status": lead.status,
        "message": f"Moved to {lead.status}",
    }


@router.post("/api/webhook/dispatch")
def dispatch_to_webhook(
    payload: WebhookDispatchRequest,
    db: Session = Depends(get_db),
):
    """
    Dispatch selected business records directly to an external n8n or custom webhook.
    Sends structured business data including contacts, opportunity priority, and suggested services.
    """
    webhook_url = payload.custom_webhook_url
    if not webhook_url or not webhook_url.strip():
        setting = db.query(AppSetting).filter(AppSetting.key == "n8n_webhook_url").first()
        if setting and setting.value and setting.value.strip():
            webhook_url = setting.value.strip()

    if not webhook_url:
        raise HTTPException(
            status_code=400,
            detail="No n8n Webhook URL configured. Please set your Webhook URL in Settings first."
        )

    # If test ping with empty business_ids
    if not payload.business_ids:
        test_payload = {
            "event": "ping_test",
            "source": payload.source or "settings_test",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "Connection test from Business Opportunity Finder",
            "sample_lead": {
                "name": "Sample Business Prospect",
                "category": "Restaurant",
                "city": "Peshawar",
                "country": "Pakistan",
                "phone": "+92 300 1234567",
                "email": "prospect@example.com",
                "website_status": "No Website Listed",
                "opportunity_score": 85,
                "opportunity_priority": "High Priority",
                "suggested_service": "Online Food Ordering & Website",
            }
        }
        try:
            with httpx.Client(timeout=8.0) as client:
                res = client.post(webhook_url, json=test_payload)
                return {
                    "success": res.status_code < 400,
                    "dispatched_count": 1,
                    "webhook_url": webhook_url,
                    "status_code": res.status_code,
                    "message": f"Test ping sent to {webhook_url} (HTTP {res.status_code})",
                }
        except Exception as e:
            return {
                "success": False,
                "webhook_url": webhook_url,
                "detail": f"Failed to connect to webhook: {str(e)}",
            }

    # Fetch matching businesses
    businesses = db.query(Business).filter(Business.id.in_(payload.business_ids)).all()
    if not businesses:
        raise HTTPException(status_code=404, detail="No matching businesses found to dispatch")

    leads_payload = []
    for b in businesses:
        lead = db.query(SavedLead).filter(SavedLead.business_id == b.id).first()
        leads_payload.append({
            "id": b.id,
            "name": b.name,
            "category": b.category,
            "address": b.address,
            "city": b.city,
            "country": b.country,
            "phone": b.phone,
            "email": b.email,
            "whatsapp": b.whatsapp,
            "website": b.website,
            "website_status": b.website_status,
            "opportunity_score": b.opportunity_score,
            "opportunity_priority": b.opportunity_priority,
            "suggested_service": b.suggested_service or (lead.offered_service if lead else "Website Development"),
            "pipeline_status": lead.status if lead else "Discovered",
            "lead_id": lead.id if lead else None,
            "latitude": b.latitude,
            "longitude": b.longitude,
        })

    dispatch_event = {
        "event": "leads_dispatched",
        "source": payload.source or "web_ui",
        "count": len(leads_payload),
        "dispatched_at": datetime.now(timezone.utc).isoformat(),
        "leads": leads_payload,
    }

    try:
        with httpx.Client(timeout=8.0) as client:
            res = client.post(webhook_url, json=dispatch_event)
            return {
                "success": res.status_code < 400,
                "dispatched_count": len(leads_payload),
                "webhook_url": webhook_url,
                "status_code": res.status_code,
                "message": f"Successfully delivered {len(leads_payload)} lead(s) to n8n webhook",
            }
    except Exception as e:
        return {
            "success": False,
            "dispatched_count": len(leads_payload),
            "webhook_url": webhook_url,
            "detail": f"Delivery error: {str(e)}",
        }

