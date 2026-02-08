"""Server instance management endpoints."""
import asyncio
from aiohttp import web

from config import DEFAULT_HOST, VRAM_MODES, EXTRA_FLAGS
from core.instance_manager import InstanceManager, InstanceConfig


def _serialize_instance(state) -> dict:
    return {
        "instance_id": state.instance_id,
        "gpu_device": state.config.gpu_device,
        "gpu_label": state.config.gpu_label,
        "port": state.config.port,
        "host": state.config.host,
        "vram_mode": state.config.vram_mode,
        "extra_args": state.config.extra_args,
        "status": state.status,
        "is_running": state.server.is_running,
        "url": f"http://{state.config.host}:{state.config.port}",
    }


async def list_instances(request: web.Request) -> web.Response:
    """List all server instances."""
    im: InstanceManager = request.app["instance_manager"]
    instances = [_serialize_instance(s) for s in im.get_all_instances()]
    return web.json_response({
        "instances": instances,
        "running_count": im.get_running_count(),
        "vram_modes": list(VRAM_MODES.keys()),
        "extra_flags": {k: v["label"] for k, v in EXTRA_FLAGS.items()},
    })


async def add_instance(request: web.Request) -> web.Response:
    """Add a new server instance."""
    data = await request.json()
    im: InstanceManager = request.app["instance_manager"]
    log_hub = request.app["log_hub"]

    gpu_device = data.get("gpu_device", "0")
    gpu_label = data.get("gpu_label", f"GPU {gpu_device}")
    port = data.get("port", im.next_available_port())
    host = data.get("host", DEFAULT_HOST)
    vram_mode = data.get("vram_mode", "normal")
    extra_args = data.get("extra_args", [])

    if isinstance(port, str):
        port = int(port)

    if port < 1024 or port > 65535:
        raise ValueError("Port must be between 1024 and 65535.")

    if vram_mode not in VRAM_MODES:
        raise ValueError(f"Invalid vram_mode. Choose from: {list(VRAM_MODES.keys())}")

    # Auto-set CPU VRAM mode
    if gpu_device == "cpu" and vram_mode != "cpu":
        vram_mode = "cpu"

    config = InstanceConfig(
        gpu_device=gpu_device,
        gpu_label=gpu_label,
        port=port,
        host=host,
        vram_mode=vram_mode,
        extra_args=extra_args,
    )

    instance_id = im.add_instance(config)
    log_hub.emit(f"Added instance {instance_id} ({gpu_label} on port {port})", tag="server")

    state = im.get_instance(instance_id)
    return web.json_response(_serialize_instance(state), status=201)


async def remove_instance(request: web.Request) -> web.Response:
    """Remove a server instance (stops it first if running)."""
    instance_id = request.match_info["id"]
    im: InstanceManager = request.app["instance_manager"]
    log_hub = request.app["log_hub"]

    state = im.get_instance(instance_id)
    if state is None:
        raise web.HTTPNotFound(reason=f"Instance {instance_id} not found")

    loop = asyncio.get_event_loop()
    success = await loop.run_in_executor(None, im.remove_instance, instance_id)

    if success:
        log_hub.emit(f"Removed instance {instance_id}", tag="server")
    return web.json_response({"ok": success, "instance_id": instance_id})


async def start_instance(request: web.Request) -> web.Response:
    """Start a specific server instance."""
    instance_id = request.match_info["id"]
    im: InstanceManager = request.app["instance_manager"]
    installer = request.app["installer"]
    log_hub = request.app["log_hub"]

    if not installer.is_installed:
        raise ValueError("ComfyUI not installed. Run install first.")

    state = im.get_instance(instance_id)
    if state is None:
        raise web.HTTPNotFound(reason=f"Instance {instance_id} not found")

    if state.server.is_running:
        return web.json_response({
            "ok": True, "instance_id": instance_id, "message": "Already running"
        })

    def progress_cb(current, total, message):
        log_hub.emit(message, tag="server")

    log_hub.emit(f"Starting instance {instance_id}...", tag="server")

    loop = asyncio.get_event_loop()
    success = await loop.run_in_executor(
        None, lambda: im.start_instance(instance_id, progress_cb)
    )

    state = im.get_instance(instance_id)
    return web.json_response(
        _serialize_instance(state),
        status=200 if success else 500,
    )


async def stop_instance(request: web.Request) -> web.Response:
    """Stop a specific server instance."""
    instance_id = request.match_info["id"]
    im: InstanceManager = request.app["instance_manager"]
    log_hub = request.app["log_hub"]

    state = im.get_instance(instance_id)
    if state is None:
        raise web.HTTPNotFound(reason=f"Instance {instance_id} not found")

    if not state.server.is_running:
        return web.json_response({
            "ok": True, "instance_id": instance_id, "message": "Already stopped"
        })

    def progress_cb(current, total, message):
        log_hub.emit(message, tag="server")

    log_hub.emit(f"Stopping instance {instance_id}...", tag="server")

    loop = asyncio.get_event_loop()
    success = await loop.run_in_executor(
        None, lambda: im.stop_instance(instance_id, progress_cb)
    )

    state = im.get_instance(instance_id)
    return web.json_response(_serialize_instance(state))


async def start_all(request: web.Request) -> web.Response:
    """Start all stopped instances."""
    im: InstanceManager = request.app["instance_manager"]
    installer = request.app["installer"]
    log_hub = request.app["log_hub"]

    if not installer.is_installed:
        raise ValueError("ComfyUI not installed. Run install first.")

    instances = im.get_all_instances()
    to_start = [s for s in instances if not s.server.is_running]

    if not to_start:
        return web.json_response({"ok": True, "message": "No stopped instances", "started": 0})

    log_hub.emit(f"Starting {len(to_start)} instance(s)...", tag="server")

    def run():
        import concurrent.futures
        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(to_start)) as executor:
            futures = {
                executor.submit(im.start_instance, s.instance_id): s.instance_id
                for s in to_start
            }
            for future in concurrent.futures.as_completed(futures):
                iid = futures[future]
                try:
                    results[iid] = future.result()
                except Exception:
                    results[iid] = False
        return results

    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(None, run)

    started = sum(1 for v in results.values() if v)
    log_hub.emit(f"Started {started}/{len(results)} instance(s)", tag="server")

    return web.json_response({
        "ok": True,
        "results": {k: v for k, v in results.items()},
        "started": started,
        "total": len(results),
    })


async def stop_all(request: web.Request) -> web.Response:
    """Stop all running instances."""
    im: InstanceManager = request.app["instance_manager"]
    log_hub = request.app["log_hub"]

    if not im.any_running():
        return web.json_response({"ok": True, "message": "No running instances"})

    log_hub.emit("Stopping all instances...", tag="server")

    loop = asyncio.get_event_loop()
    success = await loop.run_in_executor(None, im.stop_all)

    log_hub.emit("All instances stopped", tag="server")
    return web.json_response({"ok": success})


def setup(app: web.Application):
    # Register start-all/stop-all BEFORE {id} routes to avoid matching "start-all" as an ID
    app.router.add_post("/api/instances/start-all", start_all)
    app.router.add_post("/api/instances/stop-all", stop_all)
    app.router.add_get("/api/instances", list_instances)
    app.router.add_post("/api/instances", add_instance)
    app.router.add_delete("/api/instances/{id}", remove_instance)
    app.router.add_post("/api/instances/{id}/start", start_instance)
    app.router.add_post("/api/instances/{id}/stop", stop_instance)
