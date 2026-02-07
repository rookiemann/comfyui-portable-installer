"""
Multi-Instance Manager
Orchestrates multiple ComfyUI server instances across GPUs/ports.
"""
import threading
from dataclasses import dataclass, field
from typing import Optional, Callable, Dict, List

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DEFAULT_HOST, PORT_RANGE_START, PORT_RANGE_END, MAX_INSTANCES

from core.server_manager import ServerManager


@dataclass
class InstanceConfig:
    """Configuration for a single server instance."""
    gpu_device: str          # GPU index string ("0", "1", ...) or "cpu"
    gpu_label: str           # Human-readable label, e.g. "GPU 0: RTX 4090"
    port: int
    host: str = DEFAULT_HOST
    vram_mode: str = "normal"
    extra_args: list = field(default_factory=list)


@dataclass
class InstanceState:
    """Runtime state of a single server instance."""
    instance_id: str
    config: InstanceConfig
    server: ServerManager
    status: str = "stopped"  # stopped, starting, running, error


class InstanceManager:
    """Manages multiple ComfyUI server instances."""

    def __init__(self, log_callback: Optional[Callable] = None):
        self._instances: Dict[str, InstanceState] = {}
        self._lock = threading.Lock()
        self._log_callback = log_callback

    def add_instance(self, config: InstanceConfig) -> str:
        """Add a new instance. Returns instance_id.

        Raises ValueError on port collision or instance limit.
        """
        with self._lock:
            if len(self._instances) >= MAX_INSTANCES:
                raise ValueError(f"Maximum of {MAX_INSTANCES} instances reached")

            # Check port collision
            for state in self._instances.values():
                if state.config.port == config.port:
                    raise ValueError(f"Port {config.port} already in use by instance {state.instance_id}")

            instance_id = self._make_id(config)
            # Ensure unique id
            base_id = instance_id
            counter = 2
            while instance_id in self._instances:
                instance_id = f"{base_id}_{counter}"
                counter += 1

            server = ServerManager()
            state = InstanceState(
                instance_id=instance_id,
                config=config,
                server=server,
            )
            self._instances[instance_id] = state
            return instance_id

    def remove_instance(self, instance_id: str) -> bool:
        """Stop and remove an instance. Returns True if found and removed."""
        with self._lock:
            state = self._instances.get(instance_id)
            if state is None:
                return False

        # Stop outside the lock (may block)
        if state.server.is_running:
            state.server.stop_server()

        with self._lock:
            self._instances.pop(instance_id, None)
        return True

    def start_instance(
        self,
        instance_id: str,
        progress_callback: Optional[Callable] = None,
    ) -> bool:
        """Start a specific instance. Returns True on success."""
        with self._lock:
            state = self._instances.get(instance_id)
            if state is None:
                return False

        state.status = "starting"
        cfg = state.config
        prefix = self._make_prefix(cfg)
        log_cb = self._make_log_forwarder(prefix) if self._log_callback else None

        success = state.server.start_server(
            host=cfg.host,
            port=cfg.port,
            vram_mode=cfg.vram_mode,
            extra_args=cfg.extra_args if cfg.extra_args else None,
            progress_callback=progress_callback,
            log_callback=log_cb,
            gpu_device=cfg.gpu_device,
            log_prefix=prefix,
        )

        state.status = "running" if success else "error"
        return success

    def stop_instance(
        self,
        instance_id: str,
        progress_callback: Optional[Callable] = None,
    ) -> bool:
        """Stop a specific instance."""
        with self._lock:
            state = self._instances.get(instance_id)
            if state is None:
                return False

        success = state.server.stop_server(progress_callback)
        if success:
            state.status = "stopped"
        return success

    def stop_all(self, progress_callback: Optional[Callable] = None) -> bool:
        """Stop all running instances."""
        with self._lock:
            running = [s for s in self._instances.values() if s.server.is_running]

        all_ok = True
        for state in running:
            if not state.server.stop_server(progress_callback):
                all_ok = False
            else:
                state.status = "stopped"
        return all_ok

    def get_instance(self, instance_id: str) -> Optional[InstanceState]:
        with self._lock:
            return self._instances.get(instance_id)

    def get_all_instances(self) -> List[InstanceState]:
        with self._lock:
            return list(self._instances.values())

    def get_running_count(self) -> int:
        with self._lock:
            return sum(1 for s in self._instances.values() if s.server.is_running)

    def any_running(self) -> bool:
        with self._lock:
            return any(s.server.is_running for s in self._instances.values())

    def next_available_port(self, base_port: int = PORT_RANGE_START) -> int:
        """Find the next port not already claimed by an instance."""
        with self._lock:
            used = {s.config.port for s in self._instances.values()}
        port = base_port
        while port <= PORT_RANGE_END:
            if port not in used:
                return port
            port += 1
        # Fallback: return one past the range end
        return port

    # ---- internal helpers ----

    @staticmethod
    def _make_id(config: InstanceConfig) -> str:
        dev = config.gpu_device
        return f"{'cpu' if dev == 'cpu' else f'gpu{dev}'}_{config.port}"

    @staticmethod
    def _make_prefix(config: InstanceConfig) -> str:
        dev = "CPU" if config.gpu_device == "cpu" else f"GPU{config.gpu_device}"
        return f"[{dev}:{config.port}]"

    def _make_log_forwarder(self, prefix: str) -> Callable:
        cb = self._log_callback

        def forwarder(line: str):
            if cb:
                # If the line already contains the prefix (from server_manager), don't double it
                if line.startswith(prefix):
                    cb(line)
                else:
                    cb(f"{prefix} {line}")

        return forwarder
