"""ComfyUI target path, saved installs, and extra model directories."""
from pathlib import Path
from aiohttp import web

from config import (
    COMFYUI_DIR, get_active_comfyui_dir,
    load_settings, save_settings,
    get_saved_comfyui_dirs, get_extra_model_dirs,
)
from api.server import rebuild_managers


async def get_target(request: web.Request) -> web.Response:
    """Get the active ComfyUI directory."""
    installer = request.app["installer"]
    return web.json_response({
        "active_dir": str(request.app["comfyui_dir"]),
        "builtin_dir": str(COMFYUI_DIR),
        "is_external": installer.is_external,
    })


async def put_target(request: web.Request) -> web.Response:
    """Set the active ComfyUI directory."""
    data = await request.json()
    path_str = data.get("path")
    if not path_str:
        raise ValueError("'path' is required")

    path = Path(path_str)
    if not (path / "main.py").exists():
        raise ValueError(f"No main.py found in {path}")

    # Persist + auto-add to saved list
    settings = load_settings()
    saved = settings.get("saved_comfyui_dirs", [])
    updates = {"comfyui_dir": str(path)}
    if str(path) not in saved and str(path) != str(COMFYUI_DIR):
        saved.append(str(path))
        updates["saved_comfyui_dirs"] = saved
    save_settings(updates)

    rebuild_managers(request.app, path)
    request.app["log_hub"].emit(f"Switched to: {path}", tag="config")

    return web.json_response({"ok": True, "active_dir": str(path)})


async def post_reset_target(request: web.Request) -> web.Response:
    """Reset to the built-in ComfyUI directory."""
    save_settings({"comfyui_dir": None})
    rebuild_managers(request.app, COMFYUI_DIR)
    request.app["log_hub"].emit("Switched back to built-in ComfyUI", tag="config")
    return web.json_response({"ok": True, "active_dir": str(COMFYUI_DIR)})


# ---- Saved ComfyUI installs ----

async def get_saved(request: web.Request) -> web.Response:
    """List saved ComfyUI installs."""
    dirs = get_saved_comfyui_dirs()
    return web.json_response({
        "saved": dirs,
        "builtin_dir": str(COMFYUI_DIR),
    })


async def post_saved(request: web.Request) -> web.Response:
    """Add a ComfyUI install to the saved list."""
    data = await request.json()
    path_str = data.get("path")
    if not path_str:
        raise ValueError("'path' is required")

    path = Path(path_str)
    if not (path / "main.py").exists():
        raise ValueError(f"No main.py found in {path}")

    settings = load_settings()
    saved = settings.get("saved_comfyui_dirs", [])
    if str(path) not in saved and str(path) != str(COMFYUI_DIR):
        saved.append(str(path))
        save_settings({"saved_comfyui_dirs": saved})

    request.app["log_hub"].emit(f"Added saved ComfyUI: {path}", tag="config")
    return web.json_response({"ok": True, "saved": get_saved_comfyui_dirs()})


async def delete_saved(request: web.Request) -> web.Response:
    """Remove a ComfyUI install from the saved list."""
    data = await request.json()
    path_str = data.get("path")
    if not path_str:
        raise ValueError("'path' is required")

    if path_str == str(COMFYUI_DIR):
        raise ValueError("Cannot remove the built-in ComfyUI.")

    settings = load_settings()
    saved = settings.get("saved_comfyui_dirs", [])
    if path_str in saved:
        saved.remove(path_str)
        save_settings({"saved_comfyui_dirs": saved})

    request.app["log_hub"].emit(f"Removed saved ComfyUI: {path_str}", tag="config")
    return web.json_response({"ok": True, "saved": get_saved_comfyui_dirs()})


# ---- Extra model directories ----

async def get_extra_dirs(request: web.Request) -> web.Response:
    """List extra model directories."""
    return web.json_response({"extra_dirs": get_extra_model_dirs()})


async def post_extra_dir(request: web.Request) -> web.Response:
    """Add an extra model directory."""
    data = await request.json()
    path_str = data.get("path")
    if not path_str:
        raise ValueError("'path' is required")

    settings = load_settings()
    extras = settings.get("extra_model_dirs", [])
    if path_str not in extras:
        extras.append(path_str)
        save_settings({"extra_model_dirs": extras})

    request.app["log_hub"].emit(f"Added extra model dir: {path_str}", tag="config")
    return web.json_response({"ok": True, "extra_dirs": get_extra_model_dirs()})


async def delete_extra_dir(request: web.Request) -> web.Response:
    """Remove an extra model directory."""
    data = await request.json()
    path_str = data.get("path")
    if not path_str:
        raise ValueError("'path' is required")

    settings = load_settings()
    extras = settings.get("extra_model_dirs", [])
    if path_str in extras:
        extras.remove(path_str)
        save_settings({"extra_model_dirs": extras})

    request.app["log_hub"].emit(f"Removed extra model dir: {path_str}", tag="config")
    return web.json_response({"ok": True, "extra_dirs": get_extra_model_dirs()})


def setup(app: web.Application):
    app.router.add_get("/api/comfyui/target", get_target)
    app.router.add_put("/api/comfyui/target", put_target)
    app.router.add_post("/api/comfyui/target/reset", post_reset_target)
    app.router.add_get("/api/comfyui/saved", get_saved)
    app.router.add_post("/api/comfyui/saved", post_saved)
    app.router.add_delete("/api/comfyui/saved", delete_saved)
    app.router.add_get("/api/comfyui/extra-dirs", get_extra_dirs)
    app.router.add_post("/api/comfyui/extra-dirs", post_extra_dir)
    app.router.add_delete("/api/comfyui/extra-dirs", delete_extra_dir)
