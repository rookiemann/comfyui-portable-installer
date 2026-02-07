"""
ComfyUI Server Manager
Handles starting, stopping, and monitoring the ComfyUI server.
"""
import subprocess
import time
import os
from pathlib import Path
from typing import Optional, Callable, Dict
import threading

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import COMFYUI_DIR, DEFAULT_HOST, DEFAULT_PORT, VRAM_MODES

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class ServerManager:
    """Manages the ComfyUI server process."""

    def __init__(self, comfyui_dir: Optional[Path] = None):
        self.comfyui_dir = comfyui_dir or COMFYUI_DIR
        self.process: Optional[subprocess.Popen] = None
        self.host = DEFAULT_HOST
        self.port = DEFAULT_PORT
        self.gpu_device: Optional[str] = None
        self._log_thread: Optional[threading.Thread] = None
        self._log_callback: Optional[Callable] = None
        self._log_prefix: str = ""

    @property
    def main_py(self) -> Path:
        """Path to ComfyUI main.py."""
        return self.comfyui_dir / "main.py"

    @property
    def is_running(self) -> bool:
        """Check if server process is running."""
        if self.process is None:
            return False
        return self.process.poll() is None

    @property
    def server_url(self) -> str:
        """Get the server URL."""
        return f"http://{self.host}:{self.port}"

    def start_server(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        vram_mode: str = "normal",
        extra_args: Optional[list] = None,
        progress_callback: Optional[Callable] = None,
        log_callback: Optional[Callable] = None,
        python_exe: Optional[Path] = None,
        gpu_device: Optional[str] = None,
        log_prefix: str = ""
    ) -> bool:
        """
        Start the ComfyUI server.

        Args:
            host: Host to listen on
            port: Port to listen on
            vram_mode: VRAM management mode (normal, low, none, cpu)
            extra_args: Additional command line arguments
            progress_callback: Called with (current, total, message)
            log_callback: Called with log lines from server
            python_exe: Python executable to use (defaults to venv python)
        """
        if self.is_running:
            if progress_callback:
                progress_callback(100, 100, "Server already running")
            return True

        if not self.main_py.exists():
            if progress_callback:
                progress_callback(0, 100, "Error: ComfyUI not installed")
            return False

        self.host = host
        self.port = port
        self.gpu_device = gpu_device
        self._log_callback = log_callback
        self._log_prefix = log_prefix

        # Determine Python executable
        if python_exe is None:
            from config import PYTHON_EMBEDDED_DIR, VENV_DIR
            # Prefer embedded Python, fall back to legacy venv
            embedded = PYTHON_EMBEDDED_DIR / "python.exe"
            if embedded.exists():
                python_exe = embedded
            else:
                python_exe = VENV_DIR / "Scripts" / "python.exe"

        if not python_exe.exists():
            if progress_callback:
                progress_callback(0, 100, f"Error: Python not found at {python_exe}")
            return False

        try:
            if progress_callback:
                progress_callback(0, 100, "Starting ComfyUI server...")

            # Build command
            cmd = [str(python_exe), str(self.main_py)]
            cmd.extend(["--listen", host])
            cmd.extend(["--port", str(port)])

            # Add VRAM mode args
            if vram_mode in VRAM_MODES:
                cmd.extend(VRAM_MODES[vram_mode])

            # Add extra args
            if extra_args:
                cmd.extend(extra_args)

            # Set up environment
            env = os.environ.copy()
            # Pin to a specific GPU, hide all GPUs for CPU mode, or clear restrictions
            if gpu_device is not None:
                if gpu_device == "cpu":
                    env["CUDA_VISIBLE_DEVICES"] = ""
                else:
                    env["CUDA_VISIBLE_DEVICES"] = gpu_device
            else:
                env.pop("CUDA_VISIBLE_DEVICES", None)

            # Ensure portable Git and FFmpeg are on PATH for custom nodes
            from config import GIT_PORTABLE_DIR, FFMPEG_PORTABLE_DIR
            path_additions = []
            git_cmd = GIT_PORTABLE_DIR / "cmd"
            if git_cmd.exists():
                path_additions.append(str(git_cmd))
            ffmpeg_bin = FFMPEG_PORTABLE_DIR / "bin"
            if ffmpeg_bin.exists():
                path_additions.append(str(ffmpeg_bin))
            if path_additions:
                env["PATH"] = os.pathsep.join(path_additions) + os.pathsep + env.get("PATH", "")

            # Start process
            # Use CREATE_NO_WINDOW on Windows
            startupinfo = None
            creationflags = 0
            if os.name == "nt":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                creationflags = subprocess.CREATE_NO_WINDOW

            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=self.comfyui_dir,
                env=env,
                startupinfo=startupinfo,
                creationflags=creationflags,
                text=True,
                bufsize=1
            )

            # Start log reader thread
            if log_callback:
                self._log_thread = threading.Thread(
                    target=self._read_logs,
                    daemon=True
                )
                self._log_thread.start()

            # Wait for server to be ready
            if progress_callback:
                progress_callback(50, 100, "Waiting for server to start...")

            if self._wait_for_server(timeout=120):
                if progress_callback:
                    progress_callback(100, 100, f"Server running at {self.server_url}")
                return True
            else:
                # Process may still be starting up — don't kill it if it's alive
                if self.is_running:
                    if progress_callback:
                        progress_callback(50, 100, f"Server still starting (process alive, not responding yet)")
                    return True  # Treat as success — process is running, just slow
                else:
                    if progress_callback:
                        progress_callback(0, 100, "Server process died during startup")
                    return False

        except Exception as e:
            if progress_callback:
                progress_callback(0, 100, f"Error: {str(e)}")
            return False

    def _read_logs(self):
        """Read and forward server logs."""
        if self.process and self.process.stdout:
            for line in self.process.stdout:
                if self._log_callback:
                    text = line.rstrip()
                    if self._log_prefix:
                        text = f"{self._log_prefix} {text}"
                    self._log_callback(text)

    def _wait_for_server(self, timeout: int = 60) -> bool:
        """Wait for server to be ready."""
        if not REQUESTS_AVAILABLE:
            # Can't check, just wait a bit
            time.sleep(5)
            return self.is_running

        start_time = time.time()
        while time.time() - start_time < timeout:
            if not self.is_running:
                return False

            try:
                response = requests.get(f"{self.server_url}/system_stats", timeout=2)
                if response.status_code == 200:
                    return True
            except requests.exceptions.RequestException:
                pass

            time.sleep(1)

        return False

    def stop_server(self, progress_callback: Optional[Callable] = None) -> bool:
        """Stop the ComfyUI server."""
        if not self.is_running:
            if progress_callback:
                progress_callback(100, 100, "Server not running")
            return True

        try:
            if progress_callback:
                progress_callback(0, 100, "Stopping server...")

            pid = self.process.pid

            # On Windows, kill the entire process tree FIRST to avoid orphaned children
            # (torch CUDA workers, etc.). taskkill /T kills the tree; /F forces it.
            if os.name == "nt":
                try:
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(pid)],
                        capture_output=True,
                        timeout=15,
                    )
                except Exception:
                    pass

            # If process is still alive (non-Windows, or taskkill missed it), terminate
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=5)
            else:
                # Reap the zombie so the handle is released
                self.process.wait(timeout=5)

            self.process = None
            self.gpu_device = None
            self._log_prefix = ""

            if progress_callback:
                progress_callback(100, 100, "Server stopped")
            return True

        except Exception as e:
            if progress_callback:
                progress_callback(0, 100, f"Error stopping server: {str(e)}")
            return False

    def restart_server(
        self,
        progress_callback: Optional[Callable] = None,
        **start_kwargs
    ) -> bool:
        """Restart the server, preserving current settings unless overridden."""
        if progress_callback:
            progress_callback(0, 100, "Restarting server...")

        # Preserve current settings so callers don't need to re-supply them
        saved = {
            "host": self.host,
            "port": self.port,
            "gpu_device": self.gpu_device,
            "log_prefix": self._log_prefix,
            "log_callback": self._log_callback,
        }
        self.stop_server()
        time.sleep(2)

        # Merge saved defaults with any explicit overrides
        for key, value in saved.items():
            start_kwargs.setdefault(key, value)

        return self.start_server(progress_callback=progress_callback, **start_kwargs)

    def check_health(self) -> Dict:
        """Check server health and get stats."""
        if not self.is_running:
            return {"status": "stopped", "healthy": False}

        if not REQUESTS_AVAILABLE:
            return {"status": "running", "healthy": True}

        try:
            response = requests.get(f"{self.server_url}/system_stats", timeout=5)
            if response.status_code == 200:
                stats = response.json()
                return {
                    "status": "running",
                    "healthy": True,
                    "stats": stats
                }
            else:
                return {"status": "unhealthy", "healthy": False}
        except requests.exceptions.RequestException:
            return {"status": "unreachable", "healthy": False}

    def get_object_info(self, class_type: Optional[str] = None) -> Dict:
        """Query ComfyUI's object_info endpoint."""
        if not self.is_running or not REQUESTS_AVAILABLE:
            return {}

        try:
            if class_type:
                url = f"{self.server_url}/object_info/{class_type}"
            else:
                url = f"{self.server_url}/object_info"

            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
            return {}
        except requests.exceptions.RequestException:
            return {}

    def get_queue(self) -> Dict:
        """Get the current queue status."""
        if not self.is_running or not REQUESTS_AVAILABLE:
            return {}

        try:
            response = requests.get(f"{self.server_url}/queue", timeout=5)
            if response.status_code == 200:
                return response.json()
            return {}
        except requests.exceptions.RequestException:
            return {}

    def get_history(self, prompt_id: Optional[str] = None) -> Dict:
        """Get execution history."""
        if not self.is_running or not REQUESTS_AVAILABLE:
            return {}

        try:
            if prompt_id:
                url = f"{self.server_url}/history/{prompt_id}"
            else:
                url = f"{self.server_url}/history"

            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
            return {}
        except requests.exceptions.RequestException:
            return {}

    def queue_prompt(self, prompt: Dict) -> Optional[str]:
        """Queue a workflow prompt for execution."""
        if not self.is_running or not REQUESTS_AVAILABLE:
            return None

        try:
            response = requests.post(
                f"{self.server_url}/prompt",
                json={"prompt": prompt},
                timeout=10
            )
            if response.status_code == 200:
                result = response.json()
                return result.get("prompt_id")
            return None
        except requests.exceptions.RequestException:
            return None
