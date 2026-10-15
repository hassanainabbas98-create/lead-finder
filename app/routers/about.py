"""About and Data Sources router."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/about", response_class=HTMLResponse)
def get_about_page(request: Request):
    """Render About & Data Sources explanation page."""
    return templates.TemplateResponse(
        request=request,
        name="about.html",
        context={
            "active_page": "about",
        },
    )
