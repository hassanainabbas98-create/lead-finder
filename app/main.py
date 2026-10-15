"""Main FastAPI application factory and configuration."""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.database import init_db
from app.routers import (
    dashboard_router,
    search_router,
    leads_router,
    lists_router,
    tasks_router,
    audit_router,
    export_router,
    settings_router,
    about_router,
    jobs_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context for startup and shutdown events."""
    # Initialize SQLite database and default seeds
    init_db()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="Personal prospecting tool discovering businesses, analyzing web presence, and prioritizing leads.",
    version="1.0.0",
    lifespan=lifespan,
    debug=settings.DEBUG,
)

templates = Jinja2Templates(directory="app/templates")


# Security Headers Middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response


app.add_middleware(SecurityHeadersMiddleware)

# Mount static assets
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Register all page and API routers
app.include_router(dashboard_router)
app.include_router(search_router)
app.include_router(leads_router)
app.include_router(lists_router)
app.include_router(tasks_router)
app.include_router(audit_router)
app.include_router(export_router)
app.include_router(settings_router)
app.include_router(about_router)
app.include_router(jobs_router)


# Custom 404 Handler
@app.exception_handler(404)
async def custom_404_handler(request: Request, exc):
    return templates.TemplateResponse(
        request=request,
        name="base.html",
        context={
            "active_page": "",
            "page_title": "Page Not Found",
        },
        status_code=404,
    )
