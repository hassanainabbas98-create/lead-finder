"""Dashboard router."""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import date

from app.database import get_db
from app.models.business import Business
from app.models.lead import SavedLead
from app.models.task import FollowUpTask

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def get_dashboard(request: Request, db: Session = Depends(get_db)):
    """Render main dashboard with live metrics and recent items."""
    total_businesses = db.query(Business).count()
    no_website_count = db.query(Business).filter(
        (Business.website == None) | (Business.website == "") | (Business.website_status == "No Website Listed")
    ).count()
    total_leads = db.query(SavedLead).count()
    pending_tasks = db.query(FollowUpTask).filter(FollowUpTask.is_completed == False).count()

    stats = {
        "total_businesses": total_businesses,
        "no_website_count": no_website_count,
        "total_leads": total_leads,
        "pending_tasks": pending_tasks,
    }

    recent_businesses = (
        db.query(Business)
        .order_by(Business.id.desc())
        .limit(8)
        .all()
    )

    upcoming_tasks = (
        db.query(FollowUpTask)
        .filter(FollowUpTask.is_completed == False)
        .order_by(FollowUpTask.due_date.asc())
        .limit(5)
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "active_page": "dashboard",
            "stats": stats,
            "recent_businesses": recent_businesses,
            "upcoming_tasks": upcoming_tasks,
        },
    )
