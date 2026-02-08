"""
In-memory job tracker for long-running operations.

Long-running API operations (install, download, node updates) return
immediately with a job ID. Clients poll GET /api/jobs/{id} for progress.
"""
import uuid
import time
from dataclasses import dataclass, field
from typing import Optional, Callable, Dict, Any
from enum import Enum


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class JobProgress:
    current: int = 0
    total: int = 0
    message: str = ""


@dataclass
class JobState:
    job_id: str
    operation: str
    status: JobStatus = JobStatus.PENDING
    progress: JobProgress = field(default_factory=JobProgress)
    result: Any = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "operation": self.operation,
            "status": self.status.value,
            "progress": {
                "current": self.progress.current,
                "total": self.progress.total,
                "message": self.progress.message,
            },
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


class JobManager:
    """Manages in-memory job tracking for long-running operations."""

    MAX_JOBS = 100

    def __init__(self):
        self._jobs: Dict[str, JobState] = {}

    def create_job(self, operation: str) -> JobState:
        """Create a new pending job."""
        job_id = str(uuid.uuid4())[:8]
        job = JobState(job_id=job_id, operation=operation)
        self._jobs[job_id] = job
        self._prune()
        return job

    def get_job(self, job_id: str) -> Optional[JobState]:
        return self._jobs.get(job_id)

    def list_jobs(self) -> list:
        return [j.to_dict() for j in self._jobs.values()]

    def make_progress_callback(self, job: JobState) -> Callable:
        """Create a progress_callback(current, total, message) that updates the job."""
        def callback(current: int, total: int, message: str):
            job.progress.current = current
            job.progress.total = total
            job.progress.message = message
        return callback

    def start_job(self, job: JobState):
        job.status = JobStatus.RUNNING
        job.started_at = time.time()

    def complete_job(self, job: JobState, result: Any = None):
        job.status = JobStatus.COMPLETED
        job.completed_at = time.time()
        job.result = result

    def fail_job(self, job: JobState, error: str):
        job.status = JobStatus.FAILED
        job.completed_at = time.time()
        job.error = error

    def _prune(self):
        """Remove oldest completed jobs when over MAX_JOBS."""
        if len(self._jobs) <= self.MAX_JOBS:
            return
        completed = sorted(
            [(jid, j) for jid, j in self._jobs.items()
             if j.status in (JobStatus.COMPLETED, JobStatus.FAILED)],
            key=lambda x: x[1].created_at,
        )
        while len(self._jobs) > self.MAX_JOBS and completed:
            jid, _ = completed.pop(0)
            del self._jobs[jid]
