"""Log endpoints: REST history and WebSocket streaming."""
import json
from aiohttp import web

from api.log_hub import LogHub


async def get_logs(request: web.Request) -> web.Response:
    """Get recent log entries with optional tag filter."""
    log_hub: LogHub = request.app["log_hub"]
    limit = int(request.query.get("limit", "200"))
    tag = request.query.get("tag")
    entries = log_hub.get_recent(limit=limit, tag=tag)
    return web.json_response({"entries": entries, "count": len(entries)})


async def ws_logs(request: web.Request) -> web.WebSocketResponse:
    """WebSocket endpoint for real-time log streaming."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    log_hub: LogHub = request.app["log_hub"]
    log_hub.add_websocket(ws)

    # Optionally send recent history on connect
    send_history = request.query.get("history", "true") == "true"
    if send_history:
        tag_filter = request.query.get("tag")
        limit = int(request.query.get("limit", "100"))
        for entry in log_hub.get_recent(limit=limit, tag=tag_filter):
            await ws.send_str(json.dumps({"type": "log", "data": entry}))

    try:
        async for msg in ws:
            pass  # Client is read-only; ignore incoming messages
    finally:
        log_hub.remove_websocket(ws)

    return ws


def setup(app: web.Application):
    app.router.add_get("/api/logs", get_logs)
    app.router.add_get("/api/ws/logs", ws_logs)
