"""
ComfyUI Installation Manager
"""
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Callable

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    BASE_DIR, COMFYUI_DIR, MODELS_DIR,
    COMFYUI_REPO, MODEL_SUBDIRS,
    GIT_PATH
)
from core.venv_manager import VenvManager


class ComfyInstaller:
    """Handles ComfyUI installation and configuration."""

    def __init__(
        self,
        comfyui_dir: Optional[Path] = None,
        models_dir: Optional[Path] = None,
        venv_manager: Optional[VenvManager] = None
    ):
        self.comfyui_dir = comfyui_dir or COMFYUI_DIR
        self.models_dir = models_dir or MODELS_DIR
        self.venv_manager = venv_manager or VenvManager()

    @property
    def is_installed(self) -> bool:
        """Check if ComfyUI is installed."""
        return (self.comfyui_dir / "main.py").exists()

    @property
    def is_external(self) -> bool:
        """True when targeting an external ComfyUI (not the built-in one)."""
        try:
            return self.comfyui_dir.resolve() != COMFYUI_DIR.resolve()
        except (OSError, ValueError):
            return False

    def clone_comfyui(
        self,
        progress_callback: Optional[Callable] = None,
        repo_url: str = COMFYUI_REPO
    ) -> bool:
        """Clone ComfyUI repository."""
        if self.is_installed:
            if progress_callback:
                progress_callback(100, 100, "ComfyUI already installed")
            return True

        try:
            if progress_callback:
                progress_callback(0, 100, "Cloning ComfyUI repository...")

            # Ensure parent directory exists
            self.comfyui_dir.parent.mkdir(parents=True, exist_ok=True)

            # Clone using git command
            result = subprocess.run(
                [GIT_PATH, "clone", "--depth", "1", repo_url, str(self.comfyui_dir)],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                if progress_callback:
                    progress_callback(0, 100, f"Error cloning: {result.stderr}")
                return False

            # Restore backed-up models if they exist (from a previous purge)
            models_backup = BASE_DIR / "_models_backup"
            if models_backup.exists():
                if progress_callback:
                    progress_callback(80, 100, "Restoring backed-up models...")
                # Remove the freshly-cloned empty models dir and replace with backup
                if self.models_dir.exists():
                    shutil.rmtree(self.models_dir)
                shutil.move(str(models_backup), str(self.models_dir))

            if progress_callback:
                progress_callback(100, 100, "ComfyUI cloned successfully")
            return True

        except FileNotFoundError:
            if progress_callback:
                progress_callback(0, 100, "Error: git not found. Run install.bat to set up portable Git.")
            return False
        except Exception as e:
            if progress_callback:
                progress_callback(0, 100, f"Error: {str(e)}")
            return False

    def install_requirements(self, progress_callback: Optional[Callable] = None) -> bool:
        """Install ComfyUI requirements."""
        if not self.is_installed:
            if progress_callback:
                progress_callback(0, 100, "Error: ComfyUI not installed")
            return False

        requirements_file = self.comfyui_dir / "requirements.txt"
        if not requirements_file.exists():
            if progress_callback:
                progress_callback(0, 100, "Error: requirements.txt not found")
            return False

        return self.venv_manager.install_requirements(requirements_file, progress_callback)

    def create_model_directories(self, progress_callback: Optional[Callable] = None) -> bool:
        """Create model subdirectories."""
        try:
            if progress_callback:
                progress_callback(0, 100, "Creating model directories...")

            self.models_dir.mkdir(parents=True, exist_ok=True)

            for i, subdir in enumerate(MODEL_SUBDIRS):
                (self.models_dir / subdir).mkdir(exist_ok=True)
                if progress_callback:
                    progress = int((i + 1) / len(MODEL_SUBDIRS) * 100)
                    progress_callback(progress, 100, f"Created {subdir}/")

            if progress_callback:
                progress_callback(100, 100, "Model directories created")
            return True

        except Exception as e:
            if progress_callback:
                progress_callback(0, 100, f"Error: {str(e)}")
            return False

    def check_installation(self) -> dict:
        """Check installation status of all components."""
        return {
            "venv_created": self.venv_manager.is_created,
            "comfyui_installed": self.is_installed,
            "models_dir_exists": self.models_dir.exists(),
            "requirements_installed": self._check_requirements_installed(),
        }

    def _check_requirements_installed(self) -> bool:
        """Check if ComfyUI requirements are installed."""
        if not self.venv_manager.is_created:
            return False

        installed = self.venv_manager.get_installed_packages()
        # Check for key packages
        required = ["torch", "safetensors", "aiohttp"]
        return all(pkg in installed for pkg in required)

    def full_install(self, progress_callback: Optional[Callable] = None) -> bool:
        """Perform full installation: Python env, PyTorch, clone, requirements, model dirs.

        When targeting an external ComfyUI the clone step is skipped
        (the repo already exists on disk).
        """
        steps = [
            ("Setting up Python environment...", self.venv_manager.create_venv),
            ("Installing PyTorch...", self.venv_manager.install_pytorch_cuda),
        ]

        if not self.is_external:
            steps.append(("Cloning ComfyUI...", self.clone_comfyui))

        steps += [
            ("Installing ComfyUI requirements...", self.install_requirements),
            ("Creating model directories...", self.create_model_directories),
        ]

        total_steps = len(steps)
        for i, (msg, func) in enumerate(steps):
            if progress_callback:
                overall_progress = int(i / total_steps * 100)
                progress_callback(overall_progress, 100, msg)

            def step_callback(current, total, message):
                if progress_callback:
                    step_progress = current / total if total > 0 else 0
                    overall = int((i + step_progress) / total_steps * 100)
                    progress_callback(overall, 100, message)

            success = func(step_callback)
            if not success:
                return False

        if progress_callback:
            progress_callback(100, 100, "Installation complete!")
        return True

    def update_comfyui(self, progress_callback: Optional[Callable] = None) -> bool:
        """Update ComfyUI by pulling latest changes."""
        if not self.is_installed:
            if progress_callback:
                progress_callback(0, 100, "Error: ComfyUI not installed")
            return False

        try:
            if progress_callback:
                progress_callback(0, 100, "Updating ComfyUI...")

            result = subprocess.run(
                [GIT_PATH, "pull"],
                capture_output=True,
                text=True,
                cwd=self.comfyui_dir
            )

            if result.returncode != 0:
                if progress_callback:
                    progress_callback(0, 100, f"Error updating: {result.stderr}")
                return False

            if progress_callback:
                progress_callback(100, 100, "ComfyUI updated")
            return True

        except Exception as e:
            if progress_callback:
                progress_callback(0, 100, f"Error: {str(e)}")
            return False

    def get_workflows_dir(self) -> Path:
        """Get the workflows directory path."""
        return self.comfyui_dir / "user" / "default" / "workflows"

    def list_workflows(self) -> list[Path]:
        """List available workflow files."""
        workflows_dir = self.get_workflows_dir()
        if not workflows_dir.exists():
            return []
        return list(workflows_dir.glob("*.json"))

    def purge_comfyui(self, progress_callback: Optional[Callable] = None) -> bool:
        """
        Purge ComfyUI installation completely.

        This removes:
        - The comfyui/ directory (cloned repo + custom nodes)

        This KEEPS:
        - The Python environment
        - Downloaded models (backed up to _models_backup/ then restored on reinstall)

        After purge, you can run full_install() again for a fresh start.
        Purging is blocked when targeting an external ComfyUI.
        """
        if self.is_external:
            if progress_callback:
                progress_callback(0, 100, "Cannot purge an external ComfyUI installation")
            return False

        if not self.comfyui_dir.exists():
            if progress_callback:
                progress_callback(100, 100, "ComfyUI not installed, nothing to purge")
            return True

        try:
            if progress_callback:
                progress_callback(0, 100, "Stopping any running ComfyUI processes...")

            # Try to stop server if running
            try:
                from core.server_manager import ServerManager
                server = ServerManager(self.comfyui_dir)
                if server.is_running:
                    server.stop_server()
            except Exception:
                pass  # Server might not be running

            # Back up models before deleting comfyui/
            models_backup = BASE_DIR / "_models_backup"
            if self.models_dir.exists():
                if progress_callback:
                    progress_callback(10, 100, "Backing up downloaded models...")
                if models_backup.exists():
                    shutil.rmtree(models_backup)
                shutil.move(str(self.models_dir), str(models_backup))

            if progress_callback:
                progress_callback(30, 100, "Removing ComfyUI directory...")

            # Remove the entire comfyui directory
            shutil.rmtree(self.comfyui_dir)

            if progress_callback:
                progress_callback(100, 100, "ComfyUI purged successfully. Models backed up, Python env preserved.")

            return True

        except PermissionError as e:
            if progress_callback:
                progress_callback(0, 100, f"Permission error: {e}. Close any programs using ComfyUI files.")
            return False
        except Exception as e:
            if progress_callback:
                progress_callback(0, 100, f"Error purging: {str(e)}")
            return False

    def purge_all(self, progress_callback: Optional[Callable] = None) -> bool:
        """
        Purge EVERYTHING including models and Python environment.

        WARNING: This removes all downloaded models!

        After this, run install.bat and full_install() for a complete fresh start.
        Purging is blocked when targeting an external ComfyUI.
        """
        if self.is_external:
            if progress_callback:
                progress_callback(0, 100, "Cannot purge an external ComfyUI installation")
            return False

        try:
            if progress_callback:
                progress_callback(0, 100, "Purging all installations...")

            # Stop server if running
            try:
                from core.server_manager import ServerManager
                server = ServerManager(self.comfyui_dir)
                if server.is_running:
                    server.stop_server()
            except Exception:
                pass

            if progress_callback:
                progress_callback(10, 100, "Removing ComfyUI directory (includes models)...")

            # Remove comfyui/ entirely (models are inside it)
            if self.comfyui_dir.exists():
                shutil.rmtree(self.comfyui_dir)

            # Also remove any leftover model backup
            models_backup = BASE_DIR / "_models_backup"
            if models_backup.exists():
                shutil.rmtree(models_backup)

            if progress_callback:
                progress_callback(50, 100, "Removing Python environment...")

            # Remove Python environment
            if self.venv_manager.venv_path.exists():
                shutil.rmtree(self.venv_manager.venv_path)

            if progress_callback:
                progress_callback(100, 100, "Complete purge finished. Run install.bat to reinstall.")

            return True

        except Exception as e:
            if progress_callback:
                progress_callback(0, 100, f"Error during purge: {str(e)}")
            return False
