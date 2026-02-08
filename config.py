"""
ComfyUI Module Configuration
"""
import json
import shutil
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.resolve()
COMFYUI_DIR = BASE_DIR / "comfyui"
MODELS_DIR = COMFYUI_DIR / "models"  # Models go into ComfyUI's native models directory

# Environment paths
PYTHON_EMBEDDED_DIR = BASE_DIR / "python_embedded"
GIT_PORTABLE_DIR = BASE_DIR / "git_portable"
FFMPEG_PORTABLE_DIR = BASE_DIR / "ffmpeg_portable"
VENV_DIR = BASE_DIR / "venv"  # Legacy, kept for backward compatibility


# Dynamic Python path resolution
def _resolve_python_path() -> Path:
    """Find the best available Python executable.

    Priority: embedded Python > legacy venv > system Python
    """
    # 1. Embedded Python (preferred for portable installs)
    embedded = PYTHON_EMBEDDED_DIR / "python.exe"
    if embedded.exists():
        return embedded

    # 2. Legacy venv Python (backward compatibility)
    venv_python = VENV_DIR / "Scripts" / "python.exe"
    if venv_python.exists():
        return venv_python

    # 3. System Python (last resort)
    system_python = shutil.which("python")
    if system_python:
        return Path(system_python)

    # 4. Return embedded path even if not yet downloaded
    #    (install.bat or PythonManager will create it)
    return embedded


def _resolve_git_path() -> str:
    """Find the best available git executable.

    Priority: portable Git > system Git
    """
    portable_git = GIT_PORTABLE_DIR / "cmd" / "git.exe"
    if portable_git.exists():
        return str(portable_git)
    return "git"


def _resolve_ffmpeg_path() -> str:
    """Find the best available ffmpeg executable.

    Priority: portable FFmpeg > system FFmpeg
    """
    portable_ffmpeg = FFMPEG_PORTABLE_DIR / "bin" / "ffmpeg.exe"
    if portable_ffmpeg.exists():
        return str(portable_ffmpeg)
    return "ffmpeg"


PYTHON_PATH = _resolve_python_path()
GIT_PATH = _resolve_git_path()
FFMPEG_PATH = _resolve_ffmpeg_path()

# Whether we're running with embedded Python
USE_EMBEDDED = (PYTHON_EMBEDDED_DIR / "python.exe").exists()

# ComfyUI settings
COMFYUI_REPO = "https://github.com/Comfy-Org/ComfyUI.git"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8188

# Multi-instance defaults
MAX_INSTANCES = 8
PORT_RANGE_START = 8188
PORT_RANGE_END = 8199

# Model categories matching ComfyUI structure
MODEL_CATEGORIES = [
    "checkpoints",
    "diffusion_models",   # New models use this folder
    "vae",
    "clip",
    "text_encoders",      # Text encoders for newer models
    "loras",
    "controlnet",
    "gguf",
    "unet",
    "embeddings",
    "upscale_models",
    "clip_vision",
    "model_patches",      # For control adapters, projectors
    "latent_upscale_models",  # For video upscalers
]

# Model subdirectories to create
MODEL_SUBDIRS = MODEL_CATEGORIES.copy()

# VRAM modes for ComfyUI
VRAM_MODES = {
    "normal": [],
    "low": ["--lowvram"],
    "none": ["--novram"],
    "cpu": ["--cpu"],
}

# Human-readable VRAM mode descriptions (shown in UI)
VRAM_DESCRIPTIONS = {
    "normal": "Default mode. Uses GPU normally. Best for GPUs with 8GB+ VRAM.",
    "low": "Low VRAM mode. Offloads model parts to CPU as needed. For 4-6GB GPUs.",
    "none": "No VRAM mode. Keeps models in CPU RAM, runs compute on GPU. For 2-4GB GPUs. Slower.",
    "cpu": "CPU only. No GPU used at all. Very slow, but works without a compatible GPU.",
}

# Extra ComfyUI startup flags (toggled independently)
EXTRA_FLAGS = {
    "sage_attention": {
        "flag": "--use-sage-attention",
        "label": "SageAttention",
        "description": "2-3x faster attention. Great for video. Use 'Install SageAttention' button first.",
    },
    "cuda_malloc": {
        "flag": "--cuda-malloc",
        "label": "CUDA Malloc",
        "description": "Enable CUDA malloc for faster memory allocation. May improve speed on modern GPUs.",
    },
    "bf16_unet": {
        "flag": "--force-bf16-unet",
        "label": "BF16 UNet",
        "description": "Force BF16 precision for UNet. Can save VRAM on Ampere+ GPUs (RTX 30xx/40xx).",
    },
    "fp16_vae": {
        "flag": "--force-fp16-vae",
        "label": "FP16 VAE",
        "description": "Force FP16 precision for VAE. Saves VRAM but may cause slight quality differences.",
    },
    "preview_auto": {
        "flag": "--preview-method auto",
        "label": "Live Preview",
        "description": "Show live image previews during generation. Small performance cost.",
    },
    "disable_metadata": {
        "flag": "--disable-metadata",
        "label": "No Metadata",
        "description": "Don't save workflow metadata in output images. Reduces file size.",
    },
}


# UI Settings
WINDOW_TITLE = "ComfyUI Module - Installer & Manager"
WINDOW_SIZE = "1150x850"
APP_VERSION = "1.0.0"


# --- User settings persistence ---

SETTINGS_FILE = BASE_DIR / "settings.json"
MODULE_MODEL_PATHS_YAML = BASE_DIR / "module_model_paths.yaml"


def load_settings() -> dict:
    """Load user settings from settings.json. Returns {} on missing/corrupt."""
    try:
        if SETTINGS_FILE.exists():
            return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def save_settings(data: dict):
    """Merge *data* into the existing settings file and write it back."""
    settings = load_settings()
    settings.update(data)
    SETTINGS_FILE.write_text(json.dumps(settings, indent=2), encoding="utf-8")


def get_active_comfyui_dir() -> Path:
    """Return the active ComfyUI directory.

    Uses the external path from settings if set and valid,
    otherwise falls back to the built-in COMFYUI_DIR.
    """
    settings = load_settings()
    ext = settings.get("comfyui_dir")
    if ext:
        p = Path(ext)
        if p.is_dir() and (p / "main.py").exists():
            return p
    return COMFYUI_DIR


def get_active_models_dir() -> Path:
    """Return the models directory for the active ComfyUI."""
    return get_active_comfyui_dir() / "models"


def get_saved_comfyui_dirs() -> list[str]:
    """Return all saved ComfyUI directories.

    The built-in COMFYUI_DIR is always included.
    """
    dirs = [str(COMFYUI_DIR)]
    for d in load_settings().get("saved_comfyui_dirs", []):
        if d not in dirs:
            dirs.append(d)
    return dirs


def get_extra_model_dirs() -> list[str]:
    """Return user-added extra model search directories."""
    return load_settings().get("extra_model_dirs", [])
