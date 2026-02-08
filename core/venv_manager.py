"""
Virtual Environment Manager for ComfyUI Module

When embedded Python is available (USE_EMBEDDED=True), all methods delegate
to the embedded Python environment — no venv is created. When running in
legacy mode (existing venv/ folder, no embedded Python), the original venv
behavior is preserved.
"""
import subprocess
import sys
from pathlib import Path
from typing import Optional, Callable

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import VENV_DIR, PYTHON_PATH, PYTHON_EMBEDDED_DIR, USE_EMBEDDED


class VenvManager:
    """Manages Python environment for package installation and execution.

    Transparently delegates to embedded Python when available,
    falls back to traditional venv otherwise.
    """

    def __init__(self, venv_path: Optional[Path] = None, python_path: Optional[Path] = None):
        self._use_embedded = USE_EMBEDDED
        self._packages_cache: Optional[list] = None

        if self._use_embedded:
            self._python_dir = PYTHON_EMBEDDED_DIR
            self.venv_path = self._python_dir  # Backward compat for purge_all etc.
        else:
            self.venv_path = venv_path or VENV_DIR
            self.python_path = python_path or PYTHON_PATH

    @property
    def venv_python(self) -> Path:
        """Get the Python executable path."""
        if self._use_embedded:
            return self._python_dir / "python.exe"
        return self.venv_path / "Scripts" / "python.exe"

    @property
    def venv_pip(self) -> Path:
        """Get the pip executable path."""
        if self._use_embedded:
            return self._python_dir / "Scripts" / "pip.exe"
        return self.venv_path / "Scripts" / "pip.exe"

    @property
    def is_created(self) -> bool:
        """Check if the Python environment exists."""
        return self.venv_python.exists()

    def create_venv(self, progress_callback: Optional[Callable] = None) -> bool:
        """Create or verify the Python environment.

        For embedded Python: verifies it exists, downloads if needed.
        For legacy venv: creates a venv from system Python.
        """
        if self.is_created:
            if progress_callback:
                progress_callback(100, 100, "Python environment ready")
            return True

        if self._use_embedded:
            # Download embedded Python if not present
            try:
                from core.python_manager import PythonManager
                pm = PythonManager()
                return pm.download_and_setup(progress_callback)
            except Exception as e:
                if progress_callback:
                    progress_callback(0, 100, f"Error: {e}")
                return False

        # Legacy venv creation
        try:
            if progress_callback:
                progress_callback(0, 100, "Creating virtual environment...")

            result = subprocess.run(
                [str(self.python_path), "-m", "venv", str(self.venv_path)],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                if progress_callback:
                    progress_callback(0, 100, f"Error: {result.stderr}")
                return False

            if progress_callback:
                progress_callback(100, 100, "Virtual environment created")
            return True

        except Exception as e:
            if progress_callback:
                progress_callback(0, 100, f"Error: {e}")
            return False

    def install_package(
        self,
        package: str,
        progress_callback: Optional[Callable] = None,
        extra_args: Optional[list] = None
    ) -> bool:
        """Install a package in the Python environment."""
        if not self.is_created:
            if progress_callback:
                progress_callback(0, 100, "Error: Python environment not ready")
            return False

        try:
            if progress_callback:
                progress_callback(0, 100, f"Installing {package}...")

            # Use python -m pip for embedded Python (more reliable)
            if self._use_embedded:
                cmd = [str(self.venv_python), "-m", "pip", "install", package]
            else:
                cmd = [str(self.venv_pip), "install", package]

            if extra_args:
                cmd.extend(extra_args)

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                if progress_callback:
                    progress_callback(0, 100, f"Error installing {package}: {result.stderr}")
                return False

            self.invalidate_cache()
            if progress_callback:
                progress_callback(100, 100, f"Installed {package}")
            return True

        except Exception as e:
            if progress_callback:
                progress_callback(0, 100, f"Error: {e}")
            return False

    def install_requirements(
        self,
        requirements_file: Path,
        progress_callback: Optional[Callable] = None
    ) -> bool:
        """Install packages from requirements.txt."""
        if not self.is_created:
            if progress_callback:
                progress_callback(0, 100, "Error: Python environment not ready")
            return False

        if not requirements_file.exists():
            if progress_callback:
                progress_callback(0, 100, f"Error: {requirements_file} not found")
            return False

        try:
            if progress_callback:
                progress_callback(0, 100, "Installing requirements...")

            if self._use_embedded:
                cmd = [str(self.venv_python), "-m", "pip", "install",
                       "-r", str(requirements_file)]
            else:
                cmd = [str(self.venv_pip), "install", "-r", str(requirements_file)]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                if progress_callback:
                    progress_callback(0, 100, f"Error: {result.stderr}")
                return False

            self.invalidate_cache()
            if progress_callback:
                progress_callback(100, 100, "Requirements installed")
            return True

        except Exception as e:
            if progress_callback:
                progress_callback(0, 100, f"Error: {e}")
            return False

    def install_pytorch_cuda(self, progress_callback: Optional[Callable] = None) -> bool:
        """Install PyTorch with CUDA 12.8 support."""
        return self.install_package(
            "torch torchvision torchaudio",
            progress_callback,
            extra_args=["--index-url", "https://download.pytorch.org/whl/cu128"]
        )

    def install_sage_attention(self, progress_callback: Optional[Callable] = None) -> bool:
        """Install Triton (Windows) + SageAttention for faster inference.

        SageAttention provides ~2-3x speedup for attention operations,
        especially beneficial for video generation workflows.
        Requires CUDA 12.8+ PyTorch (cu128).
        """
        if not self.is_created:
            if progress_callback:
                progress_callback(0, 100, "Error: Python environment not ready")
            return False

        # Step 1: Install triton-windows
        if progress_callback:
            progress_callback(0, 100, "Installing Triton for Windows...")
        if not self.install_package("triton-windows", progress_callback):
            return False

        # Step 2: Install sageattention
        if progress_callback:
            progress_callback(50, 100, "Installing SageAttention...")
        if not self.install_package("sageattention", progress_callback):
            return False

        if progress_callback:
            progress_callback(100, 100, "SageAttention installed successfully")
        return True

    def is_package_installed(self, package_name: str) -> bool:
        """Check if a specific package is installed."""
        installed = self.get_installed_packages()
        # Normalize names: pip uses dashes, package names may use underscores
        normalized = package_name.lower().replace("-", "_")
        return any(p.lower().replace("-", "_") == normalized for p in installed)

    def run_command(
        self,
        cmd: list,
        cwd: Optional[Path] = None,
        progress_callback: Optional[Callable] = None
    ) -> tuple:
        """Run a command using the environment's Python."""
        if not self.is_created:
            return False, "Python environment not ready"

        try:
            full_cmd = [str(self.venv_python)] + cmd
            result = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                cwd=cwd
            )

            if result.returncode != 0:
                return False, result.stderr

            return True, result.stdout

        except Exception as e:
            return False, str(e)

    def get_installed_packages(self) -> list:
        """Get list of installed packages (cached per session)."""
        if self._packages_cache is not None:
            return self._packages_cache

        if not self.is_created:
            return []

        try:
            if self._use_embedded:
                cmd = [str(self.venv_python), "-m", "pip", "list", "--format=freeze"]
            else:
                cmd = [str(self.venv_pip), "list", "--format=freeze"]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                packages = [line.split("==")[0] for line in result.stdout.strip().split("\n") if line]
                self._packages_cache = packages
                return packages
            return []

        except Exception:
            return []

    def invalidate_cache(self):
        """Clear the installed packages cache (call after install/uninstall)."""
        self._packages_cache = None
