"""Status and settings endpoints."""
import asyncio
from aiohttp import web

from config import load_settings, save_settings
from core.gpu_manager import GPUManager


async def get_status(request: web.Request) -> web.Response:
    """Overall system status."""
    loop = asyncio.get_event_loop()
    installer = request.app["installer"]
    im = request.app["instance_manager"]

    status = await loop.run_in_executor(None, installer.check_installation)
    gpus = await loop.run_in_executor(None, GPUManager.detect_gpus)

    instances = im.get_all_instances()

    return web.json_response({
        "version": request.app["version"],
        "comfyui_dir": str(request.app["comfyui_dir"]),
        "base_dir": str(request.app["base_dir"]),
        "python_ready": status["venv_created"],
        "comfyui_installed": status["comfyui_installed"],
        "requirements_installed": status.get("requirements_installed", False),
        "models_dir_exists": status.get("models_dir_exists", False),
        "gpu_count": len(gpus),
        "gpus": [
            {"index": g.index, "name": g.name, "memory_total_mb": g.memory_total_mb}
            for g in gpus
        ],
        "instances_running": im.get_running_count(),
        "instances_total": len(instances),
    })


async def get_gpus(request: web.Request) -> web.Response:
    """List detected GPUs with VRAM info."""
    loop = asyncio.get_event_loop()
    gpus = await loop.run_in_executor(None, GPUManager.detect_gpus)

    return web.json_response({
        "gpus": [
            {
                "index": g.index,
                "name": g.name,
                "memory_total_mb": g.memory_total_mb,
                "memory_free_mb": g.memory_free_mb,
                "uuid": g.uuid,
            }
            for g in gpus
        ],
        "nvidia_available": len(gpus) > 0,
    })


async def get_settings(request: web.Request) -> web.Response:
    """Get current settings."""
    return web.json_response(load_settings())


async def put_settings(request: web.Request) -> web.Response:
    """Update settings (merge)."""
    data = await request.json()
    save_settings(data)
    return web.json_response({"ok": True})


def setup(app: web.Application):
    app.router.add_get("/api/status", get_status)
    app.router.add_get("/api/gpus", get_gpus)
    app.router.add_get("/api/settings", get_settings)
    app.router.add_put("/api/settings", put_settings)
