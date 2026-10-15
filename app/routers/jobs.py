"""Background jobs router for asynchronous search discovery and batch audits."""

from typing import List
from fastapi import APIRouter, HTTPException, Body
from app.schemas.search import SearchRequest
from app.services.jobs.manager import job_manager
from app.services.jobs.tasks import run_discovery_job, run_batch_audit_job

router = APIRouter()


@router.post("/api/jobs/search")
def start_search_job(payload: SearchRequest):
    """Start an asynchronous business discovery job."""
    job_id = job_manager.submit_job(
        "discovery",
        run_discovery_job,
        category=payload.category,
        city=payload.city,
        country=payload.country,
        state=payload.state,
        max_results=payload.max_results or 50,
    )
    return {"job_id": job_id, "status": "queued", "message": "Discovery job queued"}


@router.post("/api/jobs/audit-batch")
def start_batch_audit_job(business_ids: List[int] = Body(..., embed=True)):
    """Start an asynchronous batch website audit job."""
    if not business_ids:
        raise HTTPException(status_code=400, detail="business_ids list cannot be empty")

    job_id = job_manager.submit_job(
        "batch_audit",
        run_batch_audit_job,
        business_ids=business_ids,
    )
    return {"job_id": job_id, "status": "queued", "message": "Batch audit job queued"}


@router.get("/api/jobs/{job_id}")
def get_job_status(job_id: str):
    """Retrieve current progress, status, and result of a background job."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/api/jobs")
def list_recent_jobs():
    """List recent background jobs."""
    return {"jobs": job_manager.list_jobs()}
