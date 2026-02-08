"""
aiohttp-based REST API server for the ComfyUI Module.

Usage:
    python installer_app.py --api
    python installer_app.py --api --api-port 5000 --api-host 0.0.0.0
"""
import asyncio
import json
import sys
from pathlib import Path
from typing import Optional
from aiohttp import web

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    get_active_comfyui_dir, BASE_DIR, APP_VERSION,
)
from core.comfy_installer import ComfyInstaller
from core.venv_manager import VenvManager
from core.instance_manager import InstanceManager
from core.model_downloader import ModelDownloader
from core.custom_node_manager import CustomNodeManager
from api.jobs import JobManager
from api.log_hub import LogHub


def create_app(comfyui_dir: Optional[Path] = None) -> web.Application:
    """Create and configure the aiohttp Application."""
    app = web.Application(middlewares=[error_middleware])

    active_dir = comfyui_dir or get_active_comfyui_dir()
    venv = VenvManager()
    log_hub = LogHub()

    app["comfyui_dir"] = active_dir
    app["venv_manager"] = venv
    app["installer"] = ComfyInstaller(
        comfyui_dir=active_dir,
        models_dir=active_dir / "models",
        venv_manager=venv,
    )
    app["instance_manager"] = InstanceManager(
        log_callback=lambda line: log_hub.emit(line, tag="server"),
        comfyui_dir=active_dir,
    )
    app["model_downloader"] = ModelDownloader(models_dir=active_dir / "models")
    app["node_manager"] = CustomNodeManager(comfyui_dir=active_dir, venv_manager=venv)
    app["job_manager"] = JobManager()
    app["log_hub"] = log_hub
    app["version"] = APP_VERSION
    app["base_dir"] = BASE_DIR

    # Wire up routes
    from api.routes import setup_routes
    setup_routes(app)

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    return app


async def on_startup(app: web.Application):
    """Called when the server starts."""
    app["log_hub"].set_loop(asyncio.get_event_loop())
    app["log_hub"].emit("[API] Server started", tag="system")


async def on_shutdown(app: web.Application):
    """Graceful shutdown: stop all ComfyUI instances, close WebSockets."""
    app["log_hub"].emit("[API] Server shutting down...", tag="system")
    im: InstanceManager = app["instance_manager"]
    if im.any_running():
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, im.stop_all)
    await app["log_hub"].close_all()


@web.middleware
async def error_middleware(request, handler):
    """Catch exceptions and return uniform JSON error responses."""
    try:
        return await handler(request)
    except web.HTTPException as e:
        # Return JSON for HTTP errors too
        return web.json_response(
            {"error": e.reason},
            status=e.status,
        )
    except ValueError as e:
        return web.json_response({"error": str(e)}, status=400)
    except Exception as e:
        return web.json_response(
            {"error": "Internal server error", "detail": str(e)},
            status=500,
        )


def rebuild_managers(app: web.Application, new_dir: Path):
    """Rebuild all managers for a new ComfyUI directory.

    Stops running instances first (they point to the old path).
    Mirrors install_tab._apply_comfyui_dir().
    """
    im = app["instance_manager"]
    if im.any_running():
        im.stop_all()

    venv = app["venv_manager"]
    log_hub = app["log_hub"]

    app["comfyui_dir"] = new_dir
    app["installer"] = ComfyInstaller(
        comfyui_dir=new_dir,
        models_dir=new_dir / "models",
        venv_manager=venv,
    )
    app["instance_manager"] = InstanceManager(
        log_callback=lambda line: log_hub.emit(line, tag="server"),
        comfyui_dir=new_dir,
    )
    app["model_downloader"] = ModelDownloader(models_dir=new_dir / "models")
    app["node_manager"] = CustomNodeManager(comfyui_dir=new_dir, venv_manager=venv)


def run_server(app: web.Application, host: str = "127.0.0.1", port: int = 5000):
    """Run the API server (blocking)."""
    web.run_app(app, host=host, port=port)
