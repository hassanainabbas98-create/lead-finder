"""Follow-up Tasks router."""

from datetime import datetime, date, timezone
from typing import Optional
from fastapi import APIRouter, Request, Depends, Form, HTTPException, Body
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.task import FollowUpTask
from app.models.lead import SavedLead

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/tasks", response_class=HTMLResponse)
def get_tasks_page(
    request: Request,
    completed: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Render follow-up tasks page."""
    query = db.query(FollowUpTask)
    if completed == "true":
        query = query.filter(FollowUpTask.is_completed == True)
    else:
        query = query.filter(FollowUpTask.is_completed == False)

    tasks = query.order_by(FollowUpTask.due_date.asc()).all()
    leads_for_task = db.query(SavedLead).all()

    return templates.TemplateResponse(
        request=request,
        name="tasks.html",
        context={
            "active_page": "tasks",
            "tasks": tasks,
            "leads_for_task": leads_for_task,
        },
    )


@router.post("/api/tasks/create")
def create_task(
    saved_lead_id: int = Form(...),
    title: str = Form(...),
    due_date: str = Form(...),
    priority: str = Form("Medium"),
    description: str = Form(None),
    db: Session = Depends(get_db),
):
    """Create a new follow-up task via HTML form."""
    due = datetime.strptime(due_date, "%Y-%m-%d").date()
    task = FollowUpTask(
        saved_lead_id=saved_lead_id,
        title=title.strip(),
        due_date=due,
        priority=priority,
        description=description.strip() if description else None,
    )
    db.add(task)
    db.commit()
    return RedirectResponse(url="/tasks", status_code=303)


@router.post("/api/tasks")
def create_task_json(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
):
    """Create a new follow-up task via JSON payload."""
    saved_lead_id = payload.get("saved_lead_id")
    title = payload.get("title")
    due_date_str = payload.get("due_date")
    priority = payload.get("priority", "Medium")
    description = payload.get("description")

    if not saved_lead_id or not title or not due_date_str:
        raise HTTPException(status_code=422, detail="saved_lead_id, title, and due_date are required")

    lead = db.query(SavedLead).filter(SavedLead.id == saved_lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Saved lead not found")

    try:
        due = datetime.strptime(due_date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid date format, expected YYYY-MM-DD")

    task = FollowUpTask(
        saved_lead_id=saved_lead_id,
        title=title.strip(),
        due_date=due,
        priority=priority,
        description=description.strip() if description else None,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return {"success": True, "message": "Task created successfully", "task_id": task.id, "title": task.title}



@router.post("/api/tasks/{task_id}/toggle")
def toggle_task(
    task_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
):
    """Toggle completed state of task."""
    task = db.query(FollowUpTask).filter(FollowUpTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    is_completed = payload.get("is_completed", False)
    task.is_completed = is_completed
    task.completed_at = datetime.now(timezone.utc) if is_completed else None
    db.commit()
    return {"success": True, "is_completed": task.is_completed}


@router.delete("/api/tasks/{task_id}")
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
):
    """Delete a task."""
    task = db.query(FollowUpTask).filter(FollowUpTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    db.delete(task)
    db.commit()
    return {"success": True}
