"""Routers package exports."""

from app.routers.dashboard import router as dashboard_router
from app.routers.search import router as search_router
from app.routers.leads import router as leads_router
from app.routers.lists import router as lists_router
from app.routers.tasks import router as tasks_router
from app.routers.audit import router as audit_router
from app.routers.export import router as export_router
from app.routers.settings import router as settings_router
from app.routers.about import router as about_router
from app.routers.jobs import router as jobs_router

__all__ = [
    "dashboard_router",
    "search_router",
    "leads_router",
    "lists_router",
    "tasks_router",
    "audit_router",
    "export_router",
    "settings_router",
    "about_router",
    "jobs_router",
]
