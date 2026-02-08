"""Installation endpoints (install, update, purge, SageAttention)."""
import asyncio
from aiohttp import web

from api.jobs import JobManager
from api.log_hub import LogHub
from core.comfy_installer import ComfyInstaller
from core.venv_manager import VenvManager


async def post_install(request: web.Request) -> web.Response:
    """Trigger full install. Returns a job ID."""
    jm: JobManager = request.app["job_manager"]
    installer: ComfyInstaller = request.app["installer"]
    log_hub: LogHub = request.app["log_hub"]

    job = jm.create_job("install")
    progress_cb = jm.make_progress_callback(job)

    def run():
        jm.start_job(job)
        log_hub.emit("Starting full installation...", tag="install")
        try:
            success = installer.full_install(progress_cb)
            if success:
                jm.complete_job(job, result=True)
                log_hub.emit("Installation completed successfully!", tag="install")
            else:
                jm.fail_job(job, "Installation failed")
                log_hub.emit("Installation failed!", tag="install")
        except Exception as e:
            jm.fail_job(job, str(e))
            log_hub.emit(f"Installation error: {e}", tag="install")

    asyncio.get_event_loop().run_in_executor(None, run)
    return web.json_response(job.to_dict(), status=202)


async def post_install_sage(request: web.Request) -> web.Response:
    """Install SageAttention. Returns a job ID."""
    jm: JobManager = request.app["job_manager"]
    venv: VenvManager = request.app["venv_manager"]
    log_hub: LogHub = request.app["log_hub"]

    if not venv.is_created:
        raise ValueError("Python environment not set up. Run install first.")

    job = jm.create_job("install_sage_attention")
    progress_cb = jm.make_progress_callback(job)

    def run():
        jm.start_job(job)
        log_hub.emit("Installing Triton + SageAttention...", tag="install")
        try:
            success = venv.install_sage_attention(progress_cb)
            if success:
                jm.complete_job(job, result=True)
                log_hub.emit("SageAttention installed!", tag="install")
            else:
                jm.fail_job(job, "SageAttention installation failed")
                log_hub.emit("SageAttention installation failed!", tag="install")
        except Exception as e:
            jm.fail_job(job, str(e))
            log_hub.emit(f"SageAttention error: {e}", tag="install")

    asyncio.get_event_loop().run_in_executor(None, run)
    return web.json_response(job.to_dict(), status=202)


async def post_update(request: web.Request) -> web.Response:
    """Update ComfyUI. Returns a job ID."""
    jm: JobManager = request.app["job_manager"]
    installer: ComfyInstaller = request.app["installer"]
    log_hub: LogHub = request.app["log_hub"]

    if not installer.is_installed:
        raise ValueError("ComfyUI not installed.")

    job = jm.create_job("update_comfyui")
    progress_cb = jm.make_progress_callback(job)

    def run():
        jm.start_job(job)
        log_hub.emit("Updating ComfyUI...", tag="install")
        try:
            success = installer.update_comfyui(progress_cb)
            if success:
                jm.complete_job(job, result=True)
                log_hub.emit("Update completed!", tag="install")
            else:
                jm.fail_job(job, "Update failed")
                log_hub.emit("Update failed!", tag="install")
        except Exception as e:
            jm.fail_job(job, str(e))
            log_hub.emit(f"Update error: {e}", tag="install")

    asyncio.get_event_loop().run_in_executor(None, run)
    return web.json_response(job.to_dict(), status=202)


async def post_purge(request: web.Request) -> web.Response:
    """Purge ComfyUI (keeps Python env and models)."""
    installer: ComfyInstaller = request.app["installer"]
    log_hub: LogHub = request.app["log_hub"]
    im = request.app["instance_manager"]

    if not installer.is_installed:
        raise ValueError("ComfyUI not installed. Nothing to purge.")

    # Stop running instances first
    if im.any_running():
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, im.stop_all)

    def run():
        log_hub.emit("Purging ComfyUI...", tag="install")
        return installer.purge_comfyui()

    loop = asyncio.get_event_loop()
    success = await loop.run_in_executor(None, run)

    if success:
        log_hub.emit("Purge completed!", tag="install")
    else:
        log_hub.emit("Purge failed!", tag="install")

    return web.json_response({"ok": success})


async def post_purge_all(request: web.Request) -> web.Response:
    """Purge everything including models and Python env."""
    installer: ComfyInstaller = request.app["installer"]
    log_hub: LogHub = request.app["log_hub"]
    im = request.app["instance_manager"]

    if im.any_running():
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, im.stop_all)

    def run():
        log_hub.emit("Purging all (ComfyUI + models + Python env)...", tag="install")
        return installer.purge_all()

    loop = asyncio.get_event_loop()
    success = await loop.run_in_executor(None, run)

    if success:
        log_hub.emit("Full purge completed!", tag="install")
    else:
        log_hub.emit("Full purge failed!", tag="install")

    return web.json_response({"ok": success})


def setup(app: web.Application):
    app.router.add_post("/api/install", post_install)
    app.router.add_post("/api/install/sage-attention", post_install_sage)
    app.router.add_post("/api/update", post_update)
    app.router.add_post("/api/purge", post_purge)
    app.router.add_post("/api/purge-all", post_purge_all)
