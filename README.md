# ComfyUI Module

![License: MIT](https://img.shields.io/github/license/rookiemann/comfyui-portable-installer) ![Platform: Windows](https://img.shields.io/badge/Platform-Windows%2010%2F11-blue) ![Python](https://img.shields.io/badge/Python-3.12-green) ![ComfyUI](https://img.shields.io/badge/ComfyUI-Latest-purple)

**One click. No Docker. No Python. No Git. No admin rights. Fully portable.**

Drop this folder on any Windows 10/11 machine, double-click `install.bat`, and walk away. When it's done you have a complete, working [ComfyUI](https://github.com/comfyanonymous/ComfyUI) installation with GPU acceleration, model downloads, and a management GUI. Copy the folder to a USB drive and it still works.

---

## Highlights

- **Multi-GPU support** -- Auto-detects all NVIDIA GPUs and lets you run a separate ComfyUI instance on each one, simultaneously. Got two GPUs? Run two workflows at once. Got four? Run four.
- **Multi-instance management** -- Spin up multiple ComfyUI servers from the GUI with one click. Each gets its own GPU, port, VRAM mode, and log prefix. Start All / Stop All controls for easy batch management.
- **101 pre-built models** -- Covers every default ComfyUI workflow template. Flux 1.x & 2, SDXL, SD 3.5, SD 1.5, LTX-2, HunyuanVideo, Wan 2.1, and more. Download with one click, sorted by category and VRAM tier.
- **16 curated custom nodes** -- Essential and recommended extensions, one-click install with automatic dependency handling.
- **SageAttention** -- One-click install for 2-3x faster attention computation (Triton + SageAttention), especially beneficial for video generation.
- **Zero dependencies** -- No Python, no Git, no CUDA toolkit, no Docker, no admin rights. Everything downloads automatically into one portable folder.

---

## Why This Exists

Getting ComfyUI running typically means:
- Installing Python and fighting PATH issues
- Installing Git
- Finding and installing CUDA/cuDNN
- Running `pip install` commands that may or may not work
- Figuring out which models to download and where to put them
- ...or pulling a multi-gigabyte Docker image and wrestling with GPU passthrough

**This project eliminates all of that.** Everything is downloaded, configured, and isolated automatically inside a single folder. Nothing touches your system. Nothing requires admin rights. Nothing installs globally. If you want it gone, delete the folder.

---

## Quick Start

```
1. Download or clone this repository
2. Double-click install.bat
3. Click "Full Install" in the GUI
4. Go to Models tab, download a model
5. Add a server instance (pick your GPU), click "Start", then "Open UI"
```

That's it. No `pip install`, no `conda activate`, no `docker compose up`, no YAML configs.

> **Multiple GPUs?** Add an instance for each GPU from the GUI. Each gets its own port and runs independently. Or from the CLI: `launcher.bat run --gpu 0` in one terminal, `launcher.bat run --gpu 1 --port 8189` in another.

### Command Line

```batch
install.bat                        :: First time setup (downloads everything)
launcher.bat                       :: Launch the management GUI
launcher.bat run                   :: Start ComfyUI server directly
launcher.bat run --port 8189       :: Custom port
launcher.bat run --vram low        :: Low VRAM mode for 4-6GB GPUs
launcher.bat run --gpu 0           :: Pin to GPU 0
launcher.bat run --gpu 1 --port 8189  :: GPU 1 on port 8189
launcher.bat run --gpu cpu         :: CPU-only mode
launcher.bat purge                 :: Remove ComfyUI (keeps models + Python)
launcher.bat help                  :: Show all commands
```

---

## What Gets Downloaded Automatically

| Component | Version | Source | Purpose |
|-----------|---------|--------|---------|
| Python | 3.12.8 (embeddable) | [python.org](https://www.python.org/downloads/) | Runs everything. No system Python needed. |
| pip | Latest | [bootstrap.pypa.io](https://bootstrap.pypa.io/get-pip.py) | Python package installer |
| tkinter | 3.12.8 | [python.org](https://www.python.org/ftp/python/3.12.8/amd64/) | GUI toolkit for the installer |
| Git | MinGit 2.47.1 | [git-for-windows](https://github.com/git-for-windows/git/releases) | Clones ComfyUI + custom nodes |
| FFmpeg | Latest stable | [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) | Video encode/decode for custom nodes |
| PyTorch | Latest (cu128) | [pytorch.org](https://pytorch.org/) | GPU-accelerated inference |
| ComfyUI | Latest | [Comfy-Org/ComfyUI](https://github.com/comfyanonymous/ComfyUI) | The image/video generation engine |

Everything lives inside the project folder. Nothing is installed system-wide.

---

## Features

### Portable Installation
- **Zero system dependencies** -- works on a clean Windows install
- **No Docker** -- no images to pull, no containers to manage, no GPU passthrough config
- **No admin rights** -- everything runs in user space
- **Fully relocatable** -- copy the folder anywhere and it still works
- **Clean uninstall** -- delete the folder, done

### Management GUI
- Visual installer with real-time progress and log output
- **Multi-GPU instance management** -- auto-detects all NVIDIA GPUs, run one ComfyUI instance per GPU (or multiple per GPU)
- Instance table showing device, port, VRAM mode, status, and URL for each instance
- Start/stop individual instances, or Start All/Stop All with one click
- Per-instance VRAM mode, startup flags, and port configuration
- **One-click SageAttention install** (Triton + SageAttention for 2-3x faster attention, great for video)
- Startup flag tooltips explaining each option (hover for details)
- First-launch guidance and help menus for new users

### Model Management
- **101 pre-defined models** covering every ComfyUI default workflow template
- Browse by category (checkpoints, LoRAs, ControlNets, GGUF, VAE, etc.)
- Download from [HuggingFace](https://huggingface.co/) with progress tracking
- Search HuggingFace for additional models
- Beginner recommendations by GPU VRAM tier
- Models stored in ComfyUI's native directory (preserved across reinstalls)

### Custom Nodes
- **16 curated custom nodes** with descriptions and categories
- One-click install, update, and removal
- "Essential" and "Recommended" quick-select buttons
- Automatic requirements installation

### Developer API
- **48-method REST API client** covering every ComfyUI endpoint
- WebSocket support for real-time progress
- Workflow execution with progress callbacks
- All core modules importable for use in other applications

---

## Models Registry (101 Models)

Pre-defined models for all of ComfyUI's 312 default workflow templates:

| Family | Count | Description |
|--------|-------|-------------|
| [Flux 1.x](https://huggingface.co/black-forest-labs) | 16 | Schnell/Dev in BF16, FP8, GGUF (Q4/Q5/Q8), text encoders, VAE |
| [Flux 2](https://huggingface.co/Comfy-Org) | 8 | Dev FP8, Klein 4B, Mistral text encoders, Turbo LoRA, VAE |
| [SDXL](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0) | 14 | Base, Refiner, Turbo, Lightning, Hyper, VAE |
| [SD 3.x](https://huggingface.co/stabilityai) | 9 | SD3 Medium, SD 3.5 Medium/Large/Turbo, ControlNets |
| [SD 1.5](https://huggingface.co/runwayml/stable-diffusion-v1-5) | 8 | Pruned, FP16, Inpainting, VAEs, ControlNets |
| [LTX-2](https://huggingface.co/Lightricks) | 9 | 19B Dev/Distilled (FP8 & full), LoRAs, upscaler |
| [Qwen Image](https://huggingface.co/Comfy-Org) | 7 | 2512 FP8, Edit, VAE, Lightning, ControlNet |
| [HunyuanVideo](https://huggingface.co/Comfy-Org) | 4 | 720p I2V, VAE, 1080p upscaler |
| [Wan 2.1](https://huggingface.co/Kijai) | 3 | I2V 14B FP8, VAE, UMT5 encoder |
| [Z-Image](https://huggingface.co/Comfy-Org) | 4 | Turbo, VAE, ControlNet Union |
| [HiDream](https://huggingface.co/Comfy-Org) | 4 | I1 FP8, E1 BF16, CLIP encoders |
| [Kandinsky 5](https://huggingface.co/kandinskylab) | 2 | T2V, I2V lite |
| [Chroma](https://huggingface.co/Comfy-Org) | 2 | HD FP8, Radiance |
| Other | 11 | CLIP, embeddings, upscalers, video models |

### What Should I Download?

| Your GPU VRAM | Recommended First Model | Size |
|---------------|------------------------|------|
| **24GB+** (RTX 3090, 4090) | Flux.1 Dev BF16 -- best quality | 23.8 GB |
| **12-16GB** (RTX 3060 12GB, 4070 Ti) | Flux.1 Schnell FP8 -- fast & great quality | 11.9 GB |
| **8GB** (RTX 3070, 4060) | Flux.1 Schnell GGUF Q5 -- quantized, good quality | 8.5 GB |
| **6GB** (RTX 2060, 3050) | Flux.1 Schnell GGUF Q4 -- fits in 6GB | 7.0 GB |
| **4GB** (GTX 1660, older) | SD 1.5 FP16 -- lightweight classic | 1.7 GB |

---

## Custom Nodes (16 Curated)

| Node | Author | Category | Description |
|------|--------|----------|-------------|
| [ComfyUI Manager](https://github.com/ltdrdata/ComfyUI-Manager) | ltdrdata | Essential | Install/update nodes from the ComfyUI web UI |
| [Impact Pack](https://github.com/ltdrdata/ComfyUI-Impact-Pack) | ltdrdata | Recommended | Face detection, SAM, batch processing |
| [rgthree Nodes](https://github.com/rgthree/rgthree-comfy) | rgthree | Recommended | Workflow organization, reroute, bookmarks |
| [Efficiency Nodes](https://github.com/jags111/efficiency-nodes-comfyui) | jags111 | Recommended | Simplified sampling, batch processing |
| [Tooling Nodes](https://github.com/Acly/comfyui-tooling-nodes) | Acly | Recommended | Image I/O, API integration helpers |
| [WAS Node Suite](https://github.com/WASasquatch/was-node-suite-comfyui) | WASasquatch | Popular | 100+ utility nodes for image processing |
| [Essentials](https://github.com/cubiq/ComfyUI_essentials) | cubiq | Popular | Core utilities missing from base ComfyUI |
| [AnimateDiff Evolved](https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved) | Kosinkadink | Popular | Animation/video generation |
| [IPAdapter Plus](https://github.com/cubiq/ComfyUI_IPAdapter_plus) | cubiq | Popular | Image-guided generation (style/face transfer) |
| [ControlNet Aux](https://github.com/Fannovel16/comfyui_controlnet_aux) | Fannovel16 | Popular | ControlNet preprocessors (Canny, depth, pose) |
| [Ultimate SD Upscale](https://github.com/ssitu/ComfyUI_UltimateSDUpscale) | ssitu | Popular | Tiled upscaling for large images |
| [Video Helper Suite](https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite) | Kosinkadink | Video | Load/export video, frame handling |
| [Frame Interpolation](https://github.com/Fannovel16/ComfyUI-Frame-Interpolation) | Fannovel16 | Video | RIFE/FILM frame interpolation |
| [CrysTools](https://github.com/crystian/ComfyUI-Crystools) | crystian | API | Debugging, metadata, integration tools |
| [Segment Anything](https://github.com/storyicon/comfyui_segment_anything) | storyicon | Image | SAM segmentation for masking |
| [Inpaint Nodes](https://github.com/Acly/comfyui-inpaint-nodes) | Acly | Image | Advanced inpainting workflows |

---

## VRAM Modes

| Mode | Flag | Use Case |
|------|------|----------|
| **normal** | (default) | GPUs with 8GB+ VRAM |
| **low** | `--lowvram` | 4-6GB GPUs. Offloads model parts to CPU as needed. |
| **none** | `--novram` | 2-4GB GPUs. Keeps models in CPU RAM, runs compute on GPU. Slower. |
| **cpu** | `--cpu` | No GPU at all. Very slow but works without a compatible GPU. |

---

## Multi-GPU & Multi-Instance

**Run multiple ComfyUI servers in parallel** -- one per GPU, or several per GPU if VRAM allows. Saturate all your hardware with zero configuration.

### How It Works

1. **GPU Detection** -- On launch, the GUI runs `nvidia-smi` to enumerate all NVIDIA GPUs. A dropdown lists each GPU with its name and VRAM, plus a "CPU (no GPU)" fallback.

2. **Instance Management** -- Add instances from the GUI, each configured with:
   - GPU device (pinned via `CUDA_VISIBLE_DEVICES`)
   - Port (auto-increments: 8188, 8189, ...)
   - VRAM mode and startup flags

3. **Parallel Execution** -- Start all instances simultaneously. Each runs as an isolated subprocess with its own GPU, port, and log prefix (e.g., `[GPU0:8188]`, `[GPU1:8189]`).

### Example: Dual GPU Setup

| Instance | GPU | Port | URL |
|----------|-----|------|-----|
| gpu0_8188 | GPU 0: RTX 3060 (12GB) | 8188 | http://127.0.0.1:8188 |
| gpu1_8189 | GPU 1: RTX 3090 (24GB) | 8189 | http://127.0.0.1:8189 |

Both instances run independently -- submit different workflows to each, or batch the same workflow across both GPUs.

### CLI Multi-GPU

```batch
:: Terminal 1: GPU 0 on default port
launcher.bat run --gpu 0

:: Terminal 2: GPU 1 on port 8189
launcher.bat run --gpu 1 --port 8189

:: CPU-only mode
launcher.bat run --gpu cpu
```

### Limits

- Up to **8 simultaneous instances** (configurable in `config.py`)
- Port range: 8188-8199 by default
- Each instance uses its own VRAM -- make sure your GPU has enough for the model + workflow

---

## Directory Structure

```
comfy_module/
├── install.bat               # Entry point -- run this first
├── launcher.bat              # Day-to-day launcher
├── installer_app.py          # Python entry point (GUI + CLI modes)
├── config.py                 # All paths, settings, flags
├── requirements.txt          # Installer's own Python dependencies
│
├── core/                     # Reusable Python modules
│   ├── python_manager.py     #   Embedded Python download/setup
│   ├── git_manager.py        #   Portable MinGit download/setup
│   ├── ffmpeg_manager.py     #   Portable FFmpeg download/setup
│   ├── venv_manager.py       #   Python environment management
│   ├── comfy_installer.py    #   ComfyUI clone, install, purge
│   ├── model_downloader.py   #   HuggingFace model downloads
│   ├── custom_node_manager.py #  Custom node install/update/remove
│   ├── server_manager.py     #   Start/stop ComfyUI server process
│   ├── gpu_manager.py        #   NVIDIA GPU detection via nvidia-smi
│   ├── instance_manager.py   #   Multi-instance server orchestration
│   ├── comfy_api.py          #   Full ComfyUI REST API client (48 methods)
│   └── workflow_executor.py  #   Workflow execution with progress tracking
│
├── ui/                       # Tkinter GUI
│   ├── main_window.py        #   Main window with tab navigation
│   ├── install_tab.py        #   Installation & server control
│   ├── models_tab.py         #   Model browser & downloader
│   ├── nodes_tab.py          #   Custom node management
│   └── widgets.py            #   Reusable UI components
│
├── data/                     # Registries
│   ├── models_registry.py    #   101 pre-defined models
│   └── custom_nodes_registry.py # 16 curated custom nodes
│
├── python_embedded/          # [AUTO-DOWNLOADED] Python 3.12.8
├── git_portable/             # [AUTO-DOWNLOADED] MinGit 2.47.1
├── ffmpeg_portable/          # [AUTO-DOWNLOADED] FFmpeg
└── comfyui/                  # [AUTO-INSTALLED] ComfyUI
    ├── main.py
    ├── custom_nodes/
    └── models/               # All downloaded models live here
```

Auto-downloaded directories are created by `install.bat` and excluded from git.

---

## Developer Usage

All core modules are importable for use in your own applications:

```python
import sys
sys.path.insert(0, "path/to/comfy_module")

from core import (
    ComfyAPI, ComfyInstaller, ModelDownloader,
    ServerManager, WorkflowExecutor,
    PythonManager, GitManager, FfmpegManager,
    GPUManager, GPUInfo, InstanceManager, InstanceConfig,
)

# Detect GPUs
gpus = GPUManager.detect_gpus()
for gpu in gpus:
    print(f"GPU {gpu.index}: {gpu.name} ({gpu.memory_total_mb} MB)")

# Start a single server on a specific GPU
server = ServerManager()
server.start_server(port=8188, vram_mode="normal", gpu_device="0")

# Or manage multiple instances
mgr = InstanceManager()
mgr.add_instance(InstanceConfig(gpu_device="0", gpu_label="GPU 0", port=8188))
mgr.add_instance(InstanceConfig(gpu_device="1", gpu_label="GPU 1", port=8189))
mgr.start_instance("gpu0_8188")
mgr.start_instance("gpu1_8189")
# ... later
mgr.stop_all()

# Full REST API
api = ComfyAPI(port=8188)
api.get_system_stats()
result = api.execute_workflow(workflow, wait=True, timeout=300)
images = api.get_output_images(result)

# Download models
from data import MODELS
downloader = ModelDownloader()
downloader.download_model(MODELS["flux_schnell_fp8"], progress_callback)
```

---

## Purge & Reinstall

| Action | What's Removed | What's Kept |
|--------|----------------|-------------|
| **Purge ComfyUI** | ComfyUI repo, custom nodes | Python env. Models are backed up to `_models_backup/` and auto-restored on reinstall. |
| **Purge All** | Everything (ComfyUI, models, Python env) | Only the installer scripts. Run `install.bat` again for fresh start. |

---

## Credits & Acknowledgments

This project is a wrapper/installer. The real work is done by these incredible projects:

### Core

| Project | Authors | License | Link |
|---------|---------|---------|------|
| **ComfyUI** | [comfyanonymous](https://github.com/comfyanonymous) & [Comfy-Org](https://github.com/Comfy-Org) | GPL-3.0 | [github.com/comfyanonymous/ComfyUI](https://github.com/comfyanonymous/ComfyUI) |
| **PyTorch** | Meta AI | BSD-3 | [pytorch.org](https://pytorch.org/) |
| **Python** | Python Software Foundation | PSF License | [python.org](https://www.python.org/) |

### Bundled Tools

| Tool | Authors | License | Link |
|------|---------|---------|------|
| **MinGit** | Git for Windows team | GPL-2.0 | [github.com/git-for-windows/git](https://github.com/git-for-windows/git) |
| **FFmpeg** | FFmpeg team, builds by [Gyan Doshi](https://www.gyan.dev/) | LGPL/GPL | [ffmpeg.org](https://ffmpeg.org/) / [gyan.dev/ffmpeg](https://www.gyan.dev/ffmpeg/builds/) |

### Python Dependencies

| Package | Authors | Link |
|---------|---------|------|
| **huggingface_hub** | [Hugging Face](https://huggingface.co/) | [github.com/huggingface/huggingface_hub](https://github.com/huggingface/huggingface_hub) |
| **requests** | [Kenneth Reitz](https://github.com/psf/requests) | [docs.python-requests.org](https://docs.python-requests.org/) |
| **GitPython** | [gitpython-developers](https://github.com/gitpython-developers/GitPython) | [github.com/gitpython-developers/GitPython](https://github.com/gitpython-developers/GitPython) |
| **PyYAML** | [Kirill Simonov](https://pyyaml.org/) | [pyyaml.org](https://pyyaml.org/) |
| **tqdm** | [tqdm developers](https://github.com/tqdm/tqdm) | [github.com/tqdm/tqdm](https://github.com/tqdm/tqdm) |
| **websocket-client** | [websocket-client team](https://github.com/websocket-client/websocket-client) | [github.com/websocket-client/websocket-client](https://github.com/websocket-client/websocket-client) |
| **triton-windows** | [woct0rdho](https://github.com/woct0rdho/triton-windows) | [github.com/woct0rdho/triton-windows](https://github.com/woct0rdho/triton-windows) |
| **SageAttention** | [SageAttention team](https://github.com/thu-ml/SageAttention) | [github.com/thu-ml/SageAttention](https://github.com/thu-ml/SageAttention) |

### Model Providers

Models in the registry are hosted by their respective creators on [HuggingFace](https://huggingface.co/):

| Provider | Models | Link |
|----------|--------|------|
| **Black Forest Labs** | Flux.1 Schnell, Flux.1 Dev | [huggingface.co/black-forest-labs](https://huggingface.co/black-forest-labs) |
| **Stability AI** | SD 1.5, SDXL, SD 3.x, SVD | [huggingface.co/stabilityai](https://huggingface.co/stabilityai) |
| **Comfy-Org** | FP8 conversions, Flux 2, LTX-2, Qwen, Z-Image, HiDream | [huggingface.co/Comfy-Org](https://huggingface.co/Comfy-Org) |
| **Runway** | Stable Diffusion 1.5 | [huggingface.co/runwayml](https://huggingface.co/runwayml) |
| **Lightricks** | LTX Video, LTX-2 | [huggingface.co/Lightricks](https://huggingface.co/Lightricks) |
| **ByteDance** | SDXL Lightning, Hyper-SD | [huggingface.co/ByteDance](https://huggingface.co/ByteDance) |
| **Kandinsky Lab** | Kandinsky 5 | [huggingface.co/kandinskylab](https://huggingface.co/kandinskylab) |
| **city96** | GGUF quantized models | [huggingface.co/city96](https://huggingface.co/city96) |
| **lllyasviel** | ControlNet models | [huggingface.co/lllyasviel](https://huggingface.co/lllyasviel) |
| **OpenAI / LAION** | CLIP text/vision encoders | [huggingface.co/openai](https://huggingface.co/openai) |

### Custom Node Authors

| Author | Nodes |
|--------|-------|
| [ltdrdata](https://github.com/ltdrdata) | ComfyUI Manager, Impact Pack |
| [rgthree](https://github.com/rgthree) | rgthree Nodes |
| [cubiq](https://github.com/cubiq) | Essentials, IPAdapter Plus |
| [Kosinkadink](https://github.com/Kosinkadink) | AnimateDiff Evolved, Video Helper Suite |
| [Fannovel16](https://github.com/Fannovel16) | ControlNet Aux, Frame Interpolation |
| [Acly](https://github.com/Acly) | Tooling Nodes, Inpaint Nodes |
| [WASasquatch](https://github.com/WASasquatch) | WAS Node Suite |
| [jags111](https://github.com/jags111) | Efficiency Nodes |
| [ssitu](https://github.com/ssitu) | Ultimate SD Upscale |
| [crystian](https://github.com/crystian) | CrysTools |
| [storyicon](https://github.com/storyicon) | Segment Anything |

---

### Built With

This project was designed and built by **[@rookiemann](https://github.com/rookiemann)** with **[Claude Code](https://claude.ai/claude-code)** (Anthropic's Claude Opus 4.6) as a pair-programming partner -- architecture, implementation, testing, and documentation.

---

## Platform Support

| Platform | Status |
|----------|--------|
| **Windows 10/11 (x64)** | Fully supported |
| Linux / macOS | Not currently supported (batch scripts are Windows-only) |

---

## License

MIT License. See [LICENSE](LICENSE).

This project is an installer/wrapper. ComfyUI itself is licensed under [GPL-3.0](https://github.com/comfyanonymous/ComfyUI/blob/master/LICENSE). Models have their own licenses as specified by their creators. Check each model's HuggingFace page for details.
