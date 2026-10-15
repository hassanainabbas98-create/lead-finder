"""Thread-safe background job manager for asynchronous discovery and batch auditing."""

import uuid
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Callable


class BackgroundJobManager:
    """Manages asynchronous tasks without requiring external queues (Celery/Redis)."""

    def __init__(self, max_workers: int = 3):
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="bg_job")
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def submit_job(self, job_type: str, func: Callable, *args, **kwargs) -> str:
        """Submit a task to be processed asynchronously by worker threads."""
        job_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()

        with self._lock:
            self._jobs[job_id] = {
                "job_id": job_id,
                "job_type": job_type,
                "status": "queued",  # 'queued', 'running', 'completed', 'failed'
                "progress": 0,
                "message": "Task queued for processing...",
                "result": None,
                "error": None,
                "created_at": now_iso,
                "completed_at": None,
            }

        def _worker_wrapper():
            try:
                self.update_job(job_id, status="running", progress=10, message="Task running...")
                result = func(job_id=job_id, manager=self, *args, **kwargs)
                self.update_job(
                    job_id,
                    status="completed",
                    progress=100,
                    message="Task completed successfully.",
                    result=result,
                    completed_at=datetime.now(timezone.utc).isoformat(),
                )
            except Exception as e:
                self.update_job(
                    job_id,
                    status="failed",
                    progress=100,
                    error=str(e),
                    message=f"Task failed: {str(e)}",
                    completed_at=datetime.now(timezone.utc).isoformat(),
                )

        self._executor.submit(_worker_wrapper)
        return job_id

    def update_job(self, job_id: str, **kwargs) -> None:
        """Thread-safe update of job fields."""
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].update(kwargs)

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a copy of a job's current status and results."""
        with self._lock:
            job = self._jobs.get(job_id)
            return dict(job) if job else None

    def list_jobs(self, limit: int = 25) -> List[Dict[str, Any]]:
        """List recent jobs ordered by creation time."""
        with self._lock:
            all_jobs = list(self._jobs.values())
        all_jobs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return [dict(j) for j in all_jobs[:limit]]

    def shutdown(self, wait: bool = False):
        """Clean shutdown of worker threads."""
        self._executor.shutdown(wait=wait)


# Global singleton instance
job_manager = BackgroundJobManager()
