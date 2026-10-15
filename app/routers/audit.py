"""Website Audit router for digital presence checks and contact extraction."""

from typing import List
from fastapi import APIRouter, Request, Depends, HTTPException, Body
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.audit import WebsiteAudit
from app.models.business import Business
from app.schemas.audit import AuditRequest, BatchAuditRequest
from app.services.website import WebsiteAuditService

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
audit_service = WebsiteAuditService()


@router.get("/audit", response_class=HTMLResponse)
def get_audit_page(request: Request, db: Session = Depends(get_db)):
    """Render Website Audit dashboard with recent audit logs."""
    audits = (
        db.query(WebsiteAudit)
        .order_by(WebsiteAudit.created_at.desc())
        .limit(30)
        .all()
    )
    return templates.TemplateResponse(
        request=request,
        name="audit.html",
        context={
            "active_page": "audit",
            "audits": audits,
        },
    )


@router.post("/api/audit/run")
def run_website_audit(
    payload: AuditRequest,
    db: Session = Depends(get_db),
):
    """Trigger a website audit for a business or manual URL with SSRF protection."""
    if payload.business_id:
        res = audit_service.audit_business(db=db, business_id=payload.business_id)
        if not res.get("success") and "does not have an official website" in res.get("message", ""):
            return JSONResponse(status_code=400, content={"success": False, "message": res.get("message")})
        return res

    elif payload.target_url:
        return audit_service.audit_url(db=db, url=payload.target_url)

    else:
        raise HTTPException(status_code=400, detail="Must provide either business_id or target_url")


@router.post("/api/audit/batch")
def run_batch_audit(
    payload: BatchAuditRequest,
    db: Session = Depends(get_db),
):
    """Audit multiple business websites safely in sequence."""
    results = []
    success_count = 0

    for b_id in payload.business_ids[:20]:  # Cap single batch to 20 to protect local threads
        try:
            res = audit_service.audit_business(db=db, business_id=b_id)
            results.append(res)
            if res.get("success"):
                success_count += 1
        except Exception as e:
            results.append({"business_id": b_id, "success": False, "error": str(e)})

    return {
        "success": True,
        "total_attempted": len(payload.business_ids[:20]),
        "success_count": success_count,
        "results": results,
    }
