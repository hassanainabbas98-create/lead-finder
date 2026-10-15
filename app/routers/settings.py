"""Settings and Service Rules router."""

import json
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.rules import ServiceRule, AppSetting

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/settings", response_class=HTMLResponse)
def get_settings_page(request: Request, db: Session = Depends(get_db)):
    """Render Settings & Service Rules configuration page."""
    rules = db.query(ServiceRule).order_by(ServiceRule.category_keyword.asc()).all()
    webhook_setting = db.query(AppSetting).filter(AppSetting.key == "n8n_webhook_url").first()
    webhook_url = webhook_setting.value if webhook_setting else ""

    # Parse JSON services list for display
    rules_data = []
    for r in rules:
        services_list = []
        try:
            services_list = json.loads(r.services)
        except Exception:
            services_list = [r.services]
        rules_data.append({
            "id": r.id,
            "category_keyword": r.category_keyword,
            "services": r.services,
            "services_list": services_list,
            "pitch_hook": r.pitch_hook,
            "is_active": r.is_active,
        })

    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={
            "active_page": "settings",
            "rules": rules_data,
            "webhook_url": webhook_url,
        },
    )


@router.post("/api/settings/webhook")
def save_webhook_setting(
    webhook_url: str = Form(""),
    db: Session = Depends(get_db),
):
    """Save or update n8n Webhook URL configuration."""
    url_clean = webhook_url.strip()
    setting = db.query(AppSetting).filter(AppSetting.key == "n8n_webhook_url").first()
    if not setting:
        setting = AppSetting(key="n8n_webhook_url", value=url_clean)
        db.add(setting)
    else:
        setting.value = url_clean
    db.commit()
    return RedirectResponse(url="/settings?saved=webhook", status_code=303)


@router.post("/api/settings/rules")
def add_service_rule(
    category_keyword: str = Form(...),
    services: str = Form(...),
    pitch_hook: str = Form(None),
    db: Session = Depends(get_db),
):
    """Add a new industry-to-service recommendation rule."""
    keyword = category_keyword.strip().lower()
    services_list = [s.strip() for s in services.split(",") if s.strip()]

    existing = db.query(ServiceRule).filter(ServiceRule.category_keyword == keyword).first()
    if existing:
        existing.services = json.dumps(services_list)
        existing.pitch_hook = pitch_hook.strip() if pitch_hook else None
    else:
        new_rule = ServiceRule(
            category_keyword=keyword,
            services=json.dumps(services_list),
            pitch_hook=pitch_hook.strip() if pitch_hook else None,
            is_active=True,
        )
        db.add(new_rule)

    db.commit()
    return RedirectResponse(url="/settings", status_code=303)

