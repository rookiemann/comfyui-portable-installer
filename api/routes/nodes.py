"""Custom node registry, install, update, and remove endpoints."""
import asyncio
from aiohttp import web

from core.custom_node_manager import CustomNodeManager
from data.custom_nodes_registry import (
    CUSTOM_NODES, get_nodes_by_category, get_all_categories,
)
from api.jobs import JobManager
from api.log_hub import LogHub


async def get_registry(request: web.Request) -> web.Response:
    """List nodes from the registry with optional category filter."""
    category = request.query.get("category")
    node_mgr: CustomNodeManager = request.app["node_manager"]

    if category and category != "all":
        filtered = get_nodes_by_category(category)
    else:
        filtered = CUSTOM_NODES

    loop = asyncio.get_event_loop()

    def gather():
        result = []
        for nid, info in filtered.items():
            status = node_mgr.get_node_status(info)
            desc = info.get("description", "")
            result.append({
                "id": nid,
                "name": info.get("name", nid),
                "category": info.get("category", ""),
                "description": desc,
                "repo": info.get("repo", ""),
                "required": info.get("required", False),
                "status": status,
            })
        return result

    nodes = await loop.run_in_executor(None, gather)
    return web.json_response({
        "nodes": nodes,
        "count": len(nodes),
        "categories": get_all_categories(),
    })


async def get_installed(request: web.Request) -> web.Response:
    """List installed custom nodes."""
    node_mgr: CustomNodeManager = request.app["node_manager"]
    loop = asyncio.get_event_loop()
    installed = await loop.run_in_executor(None, node_mgr.list_installed_nodes)

    return web.json_response({
        "nodes": installed,
        "count": len(installed),
    })


async def post_install(request: web.Request) -> web.Response:
    """Install custom nodes by ID. Returns a job ID."""
    data = await request.json()
    node_ids = data.get("node_ids", [])
    if not node_ids:
        raise ValueError("'node_ids' list is required")

    nodes_to_install = []
    for nid in node_ids:
        if nid not in CUSTOM_NODES:
            raise ValueError(f"Unknown node ID: {nid}")
        nodes_to_install.append({**CUSTOM_NODES[nid], "id": nid})

    node_mgr: CustomNodeManager = request.app["node_manager"]
    jm: JobManager = request.app["job_manager"]
    log_hub: LogHub = request.app["log_hub"]

    job = jm.create_job("install_nodes")
    progress_cb = jm.make_progress_callback(job)

    def run():
        jm.start_job(job)
        names = [n.get("name", n["id"]) for n in nodes_to_install]
        log_hub.emit(f"Installing {len(nodes_to_install)} node(s): {', '.join(names)}", tag="nodes")
        try:
            results = node_mgr.install_multiple(nodes_to_install, progress_cb)
            success = sum(1 for v in results.values() if v)
            failed = len(results) - success
            jm.complete_job(job, result={
                "success": success,
                "failed": failed,
                "details": {k: v for k, v in results.items()},
            })
            log_hub.emit(f"Node install complete: {success} succeeded, {failed} failed", tag="nodes")
        except Exception as e:
            jm.fail_job(job, str(e))
            log_hub.emit(f"Node install error: {e}", tag="nodes")

    asyncio.get_event_loop().run_in_executor(None, run)
    return web.json_response(job.to_dict(), status=202)


async def post_update(request: web.Request) -> web.Response:
    """Update specific installed nodes by name. Returns a job ID."""
    data = await request.json()
    node_names = data.get("node_names", [])
    if not node_names:
        raise ValueError("'node_names' list is required")

    node_mgr: CustomNodeManager = request.app["node_manager"]
    jm: JobManager = request.app["job_manager"]
    log_hub: LogHub = request.app["log_hub"]

    job = jm.create_job("update_nodes")
    progress_cb = jm.make_progress_callback(job)

    def run():
        jm.start_job(job)
        log_hub.emit(f"Updating {len(node_names)} node(s)...", tag="nodes")
        try:
            results = {}
            for i, name in enumerate(node_names):
                progress_cb(i, len(node_names), f"Updating {name}...")
                results[name] = node_mgr.update_node(name)
            success = sum(1 for v in results.values() if v)
            jm.complete_job(job, result={
                "success": success,
                "failed": len(results) - success,
                "details": results,
            })
            log_hub.emit(f"Node update complete: {success}/{len(results)} succeeded", tag="nodes")
        except Exception as e:
            jm.fail_job(job, str(e))
            log_hub.emit(f"Node update error: {e}", tag="nodes")

    asyncio.get_event_loop().run_in_executor(None, run)
    return web.json_response(job.to_dict(), status=202)


async def post_update_all(request: web.Request) -> web.Response:
    """Update all installed nodes. Returns a job ID."""
    node_mgr: CustomNodeManager = request.app["node_manager"]
    jm: JobManager = request.app["job_manager"]
    log_hub: LogHub = request.app["log_hub"]

    job = jm.create_job("update_all_nodes")
    progress_cb = jm.make_progress_callback(job)

    def run():
        jm.start_job(job)
        log_hub.emit("Updating all installed nodes...", tag="nodes")
        try:
            results = node_mgr.update_all_nodes(progress_cb)
            success = sum(1 for v in results.values() if v)
            jm.complete_job(job, result={
                "success": success,
                "failed": len(results) - success,
                "details": {k: v for k, v in results.items()},
            })
            log_hub.emit(f"Update all complete: {success}/{len(results)} succeeded", tag="nodes")
        except Exception as e:
            jm.fail_job(job, str(e))
            log_hub.emit(f"Update all error: {e}", tag="nodes")

    asyncio.get_event_loop().run_in_executor(None, run)
    return web.json_response(job.to_dict(), status=202)


async def delete_node(request: web.Request) -> web.Response:
    """Remove a single installed node by name."""
    node_name = request.match_info["name"]
    node_mgr: CustomNodeManager = request.app["node_manager"]
    log_hub: LogHub = request.app["log_hub"]

    loop = asyncio.get_event_loop()
    success = await loop.run_in_executor(None, node_mgr.remove_node, node_name)

    if success:
        log_hub.emit(f"Removed node: {node_name}", tag="nodes")
    else:
        log_hub.emit(f"Failed to remove node: {node_name}", tag="nodes")

    return web.json_response({"ok": success, "name": node_name})


def setup(app: web.Application):
    app.router.add_get("/api/nodes/registry", get_registry)
    app.router.add_get("/api/nodes/installed", get_installed)
    app.router.add_post("/api/nodes/install", post_install)
    app.router.add_post("/api/nodes/update", post_update)
    app.router.add_post("/api/nodes/update-all", post_update_all)
    app.router.add_delete("/api/nodes/{name}", delete_node)
