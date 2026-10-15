"""Automated tests for Phase 6: Background Jobs Manager and Asynchronous Task Processing."""

import time
from app.services.jobs.manager import BackgroundJobManager
from app.models.business import Business


def test_job_manager_success_flow():
    """Test submitting a successful task to BackgroundJobManager."""
    manager = BackgroundJobManager(max_workers=1)

    def sample_task(job_id, manager, value):
        manager.update_job(job_id, progress=50, message="Halfway there")
        return {"doubled": value * 2}

    job_id = manager.submit_job("test_task", sample_task, value=21)
    assert job_id is not None

    # Wait for completion (fast mock)
    for _ in range(20):
        job = manager.get_job(job_id)
        if job and job["status"] in ("completed", "failed"):
            break
        time.sleep(0.05)

    job = manager.get_job(job_id)
    assert job is not None
    assert job["status"] == "completed"
    assert job["progress"] == 100
    assert job["result"] == {"doubled": 42}
    assert job["error"] is None

    manager.shutdown(wait=False)


def test_job_manager_failure_flow():
    """Test that BackgroundJobManager captures task exceptions gracefully."""
    manager = BackgroundJobManager(max_workers=1)

    def failing_task(job_id, manager):
        raise ValueError("Simulated network timeout")

    job_id = manager.submit_job("failing_task", failing_task)

    for _ in range(20):
        job = manager.get_job(job_id)
        if job and job["status"] in ("completed", "failed"):
            break
        time.sleep(0.05)

    job = manager.get_job(job_id)
    assert job is not None
    assert job["status"] == "failed"
    assert "Simulated network timeout" in job["error"]

    manager.shutdown(wait=False)


def test_api_jobs_endpoints(client, db_session):
    """Test FastAPI background job endpoints."""
    b = Business(source="osm", source_id="osm:node/9001", name="Job Test Clinic", city="Lahore", website="https://example.com")
    db_session.add(b)
    db_session.commit()

    # Test starting batch audit job
    res_batch = client.post("/api/jobs/audit-batch", json={"business_ids": [b.id]})
    assert res_batch.status_code == 200
    data = res_batch.json()
    assert "job_id" in data
    job_id = data["job_id"]

    # Test checking job status
    res_status = client.get(f"/api/jobs/{job_id}")
    assert res_status.status_code == 200
    job_data = res_status.json()
    assert job_data["job_id"] == job_id
    assert job_data["status"] in ("queued", "running", "completed")

    # Test listing recent jobs
    res_list = client.get("/api/jobs")
    assert res_list.status_code == 200
    assert "jobs" in res_list.json()
    job_ids = [j["job_id"] for j in res_list.json()["jobs"]]
    assert job_id in job_ids

    # Test 404 for unknown job
    res_404 = client.get("/api/jobs/nonexistent-uuid")
    assert res_404.status_code == 404
