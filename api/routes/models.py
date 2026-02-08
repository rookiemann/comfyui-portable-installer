"""Model registry, download, search, and local scan endpoints."""
import asyncio
from aiohttp import web

from config import MODEL_CATEGORIES
from core.model_downloader import ModelDownloader
from data.models_registry import MODELS, get_models_by_category
from api.jobs import JobManager
from api.log_hub import LogHub


async def get_registry(request: web.Request) -> web.Response:
    """List models from the registry with optional category filter."""
    category = request.query.get("category")
    downloader: ModelDownloader = request.app["model_downloader"]

    if category and category != "all":
        filtered = {
            mid: info for mid, info in MODELS.items()
            if info.get("folder") == category
        }
    else:
        filtered = MODELS

    loop = asyncio.get_event_loop()

    def gather():
        result = []
        for mid, info in filtered.items():
            status = downloader.get_model_status(info)
            result.append({
                "id": mid,
                "name": info.get("name", mid),
                "folder": info.get("folder", ""),
                "size_gb": info.get("size_gb", 0),
                "repo": info.get("repo", ""),
                "filename": info.get("filename", ""),
                "status": status,
            })
        return result

    models = await loop.run_in_executor(None, gather)
    return web.json_response({"models": models, "count": len(models)})


async def get_registry_model(request: web.Request) -> web.Response:
    """Get a specific registry model's info and status."""
    model_id = request.match_info["id"]
    if model_id not in MODELS:
        raise web.HTTPNotFound(reason=f"Model {model_id} not found in registry")

    info = MODELS[model_id]
    downloader: ModelDownloader = request.app["model_downloader"]

    loop = asyncio.get_event_loop()
    status = await loop.run_in_executor(None, downloader.get_model_status, info)

    return web.json_response({
        "id": model_id,
        "name": info.get("name", model_id),
        "folder": info.get("folder", ""),
        "size_gb": info.get("size_gb", 0),
        "repo": info.get("repo", ""),
        "filename": info.get("filename", ""),
        "description": info.get("description", ""),
        "status": status,
    })


async def get_local(request: web.Request) -> web.Response:
    """Scan local models directory."""
    downloader: ModelDownloader = request.app["model_downloader"]
    loop = asyncio.get_event_loop()
    local_models = await loop.run_in_executor(None, downloader.scan_local_models)

    result = {}
    total = 0
    for category, models in local_models.items():
        result[category] = [
            {
                "name": m.get("name", ""),
                "size_gb": m.get("size_gb", 0),
                "folder": m.get("folder", ""),
                "path": m.get("path", ""),
            }
            for m in models
        ]
        total += len(models)

    return web.json_response({"models": result, "total": total})


async def post_download(request: web.Request) -> web.Response:
    """Download models by ID. Returns a job ID."""
    data = await request.json()
    model_ids = data.get("model_ids", [])
    if not model_ids:
        raise ValueError("'model_ids' list is required")

    downloader: ModelDownloader = request.app["model_downloader"]
    jm: JobManager = request.app["job_manager"]
    log_hub: LogHub = request.app["log_hub"]

    models_to_download = []
    for mid in model_ids:
        if mid not in MODELS:
            raise ValueError(f"Unknown model ID: {mid}")
        info = MODELS[mid]
        if not downloader.check_model_exists(info):
            models_to_download.append({**info, "id": mid})

    if not models_to_download:
        return web.json_response({
            "ok": True,
            "message": "All selected models are already installed.",
        })

    total_gb = sum(m.get("size_gb", 0) for m in models_to_download)
    job = jm.create_job("download_models")
    progress_cb = jm.make_progress_callback(job)

    def run():
        jm.start_job(job)
        names = [m.get("name", m.get("filename", "?")) for m in models_to_download]
        log_hub.emit(
            f"Downloading {len(models_to_download)} model(s) (~{total_gb:.1f} GB): {', '.join(names)}",
            tag="models",
        )
        try:
            results = downloader.download_multiple(models_to_download, progress_cb)
            success_count = sum(1 for v in results.values() if v)
            fail_count = len(results) - success_count
            jm.complete_job(job, result={
                "success": success_count,
                "failed": fail_count,
                "details": {k: v for k, v in results.items()},
            })
            log_hub.emit(
                f"Download complete: {success_count} succeeded, {fail_count} failed",
                tag="models",
            )
        except Exception as e:
            jm.fail_job(job, str(e))
            log_hub.emit(f"Download error: {e}", tag="models")

    asyncio.get_event_loop().run_in_executor(None, run)
    return web.json_response(job.to_dict(), status=202)


async def get_search(request: web.Request) -> web.Response:
    """Search HuggingFace for models."""
    query = request.query.get("q", "").strip()
    if not query:
        raise ValueError("'q' query parameter is required")

    limit = int(request.query.get("limit", "20"))
    downloader: ModelDownloader = request.app["model_downloader"]

    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(
        None, lambda: downloader.search_huggingface(query, limit=limit)
    )

    return web.json_response({"results": results or [], "count": len(results or [])})


async def get_categories(request: web.Request) -> web.Response:
    """List model categories."""
    return web.json_response({"categories": MODEL_CATEGORIES})


def setup(app: web.Application):
    app.router.add_get("/api/models/registry", get_registry)
    app.router.add_get("/api/models/registry/{id}", get_registry_model)
    app.router.add_get("/api/models/local", get_local)
    app.router.add_post("/api/models/download", post_download)
    app.router.add_get("/api/models/search", get_search)
    app.router.add_get("/api/models/categories", get_categories)
