"""Custom Lists management router."""

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.lead import LeadList, LeadListItem

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/lists", response_class=HTMLResponse)
def get_lists_page(request: Request, db: Session = Depends(get_db)):
    """Render Saved Lists page."""
    lists = db.query(LeadList).order_by(LeadList.name.asc()).all()
    return templates.TemplateResponse(
        request=request,
        name="lists.html",
        context={
            "active_page": "lists",
            "lists": lists,
        },
    )


@router.post("/api/lists/create")
def create_list(
    name: str = Form(...),
    description: str = Form(None),
    color: str = Form("#10b981"),
    db: Session = Depends(get_db),
):
    """Create a new custom prospect list."""
    existing = db.query(LeadList).filter(LeadList.name.ilike(name.strip())).first()
    if existing:
        return RedirectResponse(url="/lists?error=List+already+exists", status_code=303)

    lead_list = LeadList(
        name=name.strip(),
        description=description.strip() if description else None,
        color=color.strip() if color else "#10b981",
    )
    db.add(lead_list)
    db.commit()
    return RedirectResponse(url="/lists", status_code=303)


@router.delete("/api/lists/{list_id}")
def delete_list(
    list_id: int,
    db: Session = Depends(get_db),
):
    """Delete a custom prospect list."""
    lead_list = db.query(LeadList).filter(LeadList.id == list_id).first()
    if not lead_list:
        raise HTTPException(status_code=404, detail="List not found")

    db.delete(lead_list)
    db.commit()
    return {"success": True, "message": "List deleted"}
