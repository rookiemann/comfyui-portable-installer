"""Job tracking endpoints."""
from aiohttp import web

from api.jobs import JobManager


async def list_jobs(request: web.Request) -> web.Response:
    """List all jobs."""
    jm: JobManager = request.app["job_manager"]
    return web.json_response({"jobs": jm.list_jobs()})


async def get_job(request: web.Request) -> web.Response:
    """Get a specific job's status and progress."""
    job_id = request.match_info["id"]
    jm: JobManager = request.app["job_manager"]
    job = jm.get_job(job_id)
    if job is None:
        raise web.HTTPNotFound(reason=f"Job {job_id} not found")
    return web.json_response(job.to_dict())


def setup(app: web.Application):
    app.router.add_get("/api/jobs", list_jobs)
    app.router.add_get("/api/jobs/{id}", get_job)
