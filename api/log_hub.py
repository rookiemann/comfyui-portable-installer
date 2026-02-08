"""
Centralized log aggregation with WebSocket fan-out.

Collects log messages from all sources (core managers, API handlers)
and broadcasts them to connected WebSocket clients. Thread-safe:
emit() can be called from any thread (e.g., thread pool executors).
"""
import asyncio
import json
import time
from collections import deque
from typing import Optional, Set
from aiohttp import web


class LogEntry:
    __slots__ = ("timestamp", "tag", "message")

    def __init__(self, tag: str, message: str):
        self.timestamp = time.time()
        self.tag = tag
        self.message = message

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "tag": self.tag,
            "message": self.message,
        }


class LogHub:
    """Thread-safe log collector with WebSocket broadcast."""

    MAX_HISTORY = 2000

    def __init__(self):
        self._history: deque = deque(maxlen=self.MAX_HISTORY)
        self._websockets: Set[web.WebSocketResponse] = set()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        """Set the event loop (call from on_startup)."""
        self._loop = loop

    def emit(self, message: str, tag: str = "system"):
        """Thread-safe: emit a log message from any thread."""
        entry = LogEntry(tag=tag, message=message)
        self._history.append(entry)

        if self._loop and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(
                asyncio.ensure_future,
                self._broadcast(entry),
            )

    async def _broadcast(self, entry: LogEntry):
        """Send log entry to all connected WebSocket clients."""
        dead = set()
        data = json.dumps({"type": "log", "data": entry.to_dict()})
        for ws in self._websockets:
            try:
                await ws.send_str(data)
            except Exception:
                dead.add(ws)
        self._websockets -= dead

    def add_websocket(self, ws: web.WebSocketResponse):
        self._websockets.add(ws)

    def remove_websocket(self, ws: web.WebSocketResponse):
        self._websockets.discard(ws)

    async def close_all(self):
        """Close all WebSocket connections."""
        for ws in list(self._websockets):
            try:
                await ws.close()
            except Exception:
                pass
        self._websockets.clear()

    def get_recent(self, limit: int = 200, tag: Optional[str] = None) -> list:
        """Get recent log entries, optionally filtered by tag."""
        entries = list(self._history)
        if tag:
            entries = [e for e in entries if e.tag == tag]
        return [e.to_dict() for e in entries[-limit:]]
