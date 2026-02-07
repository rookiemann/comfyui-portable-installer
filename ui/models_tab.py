"""
Models Tab for ComfyUI Module Installer
"""
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import threading

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import MODEL_CATEGORIES

from core.model_downloader import ModelDownloader
from data.models_registry import MODELS, get_models_by_category
from ui.widgets import (
    ProgressFrame, LogFrame, CheckboxTreeview,
    ButtonBar, LabeledEntry, LabeledCombobox
)

# Model category descriptions for the UI
CATEGORY_TIPS = {
    "all": "Showing all available models. Use the category filter to narrow down.",
    "checkpoints": "Full model files (largest). These are all-in-one models that include the UNet, VAE, and text encoder.",
    "diffusion_models": "Newer model format (UNet/DiT only). Requires separate VAE and text encoder files.",
    "vae": "Variational Autoencoders. Encode/decode images to/from latent space. Required by diffusion_models.",
    "clip": "CLIP text encoders for SD 1.5 and SDXL models.",
    "text_encoders": "Text encoders for newer models (Flux 2, LTX-2, etc.). Required by diffusion_models.",
    "loras": "LoRA adapters. Small files that modify model behavior (styles, characters, concepts).",
    "controlnet": "ControlNet models for guided generation (Canny edges, depth maps, poses).",
    "gguf": "GGUF quantized models. Smaller files that use less VRAM with some quality tradeoff.",
    "unet": "Standalone UNet models (older format). Used by SDXL Lightning and similar.",
    "embeddings": "Textual inversions. Small files used in prompts for specific concepts (e.g., negative embeddings).",
    "upscale_models": "Upscaling models (ESRGAN, etc.). Increase image resolution after generation.",
    "clip_vision": "CLIP Vision models for image-guided generation (IP-Adapter, etc.).",
    "model_patches": "Control adapters and projectors for advanced workflows.",
    "latent_upscale_models": "Latent-space upscalers for video models.",
}


class ModelsTab(ttk.Frame):
    """Models download and management tab."""

    def __init__(self, parent, main_window):
        super().__init__(parent, padding=10)
        self.main_window = main_window
        self.downloader = ModelDownloader()

        self._setup_ui()
        self._populate_models()

    def _setup_ui(self):
        # Top controls
        controls_frame = ttk.Frame(self)
        controls_frame.pack(fill=tk.X, pady=(0, 5))

        # Category filter
        self.category_combo = LabeledCombobox(
            controls_frame, "Category:",
            ["all"] + MODEL_CATEGORIES, "all"
        )
        self.category_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.category_combo.combo.bind("<<ComboboxSelected>>", self._on_category_change)

        # Search
        search_frame = ttk.Frame(controls_frame)
        search_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Label(search_frame, text="Search HuggingFace:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        self.search_entry.pack(side=tk.LEFT, padx=5)
        self.search_entry.bind("<Return>", lambda e: self._search_huggingface())

        ttk.Button(search_frame, text="Search", command=self._search_huggingface).pack(side=tk.LEFT)

        # Refresh button
        ttk.Button(controls_frame, text="Refresh", command=self._refresh_models).pack(side=tk.RIGHT)

        # Category description / tip
        self.category_tip = ttk.Label(
            self,
            text=CATEGORY_TIPS.get("all", ""),
            wraplength=900, foreground="#555555",
            font=("Segoe UI", 8)
        )
        self.category_tip.pack(fill=tk.X, pady=(0, 5))

        # Main content - split view
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Left: Registry models
        left_frame = ttk.LabelFrame(paned, text="Available Models (from registry)", padding=5)
        paned.add(left_frame, weight=1)

        self.models_tree = CheckboxTreeview(
            left_frame,
            columns=["name", "folder", "size", "status"]
        )
        self.models_tree.pack(fill=tk.BOTH, expand=True)

        # Configure columns
        self.models_tree.tree.column("name", width=200)
        self.models_tree.tree.column("folder", width=100)
        self.models_tree.tree.column("size", width=80)
        self.models_tree.tree.column("status", width=80)

        # Left buttons
        left_buttons = ButtonBar(left_frame)
        left_buttons.pack(fill=tk.X, pady=(5, 0))

        left_buttons.add_button("select_all", "Select All", self._select_all)
        left_buttons.add_button("select_none", "Select None", self._select_none)

        # Right: Search results / Local models
        right_frame = ttk.LabelFrame(paned, text="Search Results / Local Models", padding=5)
        paned.add(right_frame, weight=1)

        self.results_tree = CheckboxTreeview(
            right_frame,
            columns=["name", "repo", "folder"]
        )
        self.results_tree.pack(fill=tk.BOTH, expand=True)

        self.results_tree.tree.column("name", width=150)
        self.results_tree.tree.column("repo", width=200)
        self.results_tree.tree.column("folder", width=100)

        # Right buttons
        right_buttons = ButtonBar(right_frame)
        right_buttons.pack(fill=tk.X, pady=(5, 0))

        right_buttons.add_button("show_local", "Show Local", self._show_local_models)

        # Bottom: Progress and actions
        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(fill=tk.X)

        # Progress
        self.progress = ProgressFrame(bottom_frame)
        self.progress.pack(fill=tk.X, pady=(0, 5))

        # Action buttons
        action_buttons = ButtonBar(bottom_frame)
        action_buttons.pack(fill=tk.X)

        action_buttons.add_button(
            "download", "Download Selected",
            self._download_selected, width=20
        )
        action_buttons.add_button(
            "download_search", "Download from Search",
            self._download_from_search, width=20
        )

        # Beginner guidance panel (shown below action buttons)
        self.starter_frame = ttk.LabelFrame(bottom_frame, text="New to ComfyUI?", padding=8)
        self.starter_frame.pack(fill=tk.X, pady=(5, 0))

        starter_text = (
            "Start with one of these beginner-friendly setups:\n\n"
            "  8GB+ GPU:  Filter by 'checkpoints', download 'Flux.1 Schnell FP8' (11.9 GB)\n"
            "                    Fast generation, great quality. Works out of the box.\n\n"
            "  6GB GPU:   Filter by 'gguf', download 'Flux.1 Schnell GGUF Q4' (7.0 GB)\n"
            "                    Same model, quantized to fit lower VRAM.\n\n"
            "  4GB GPU:   Filter by 'checkpoints', download 'SD 1.5 FP16' (1.7 GB)\n"
            "                    Older but lightweight. Use 'low' VRAM mode.\n\n"
            "After downloading, go back to Install & Run, add an instance, click Start, then Open UI."
        )
        ttk.Label(
            self.starter_frame, text=starter_text,
            wraplength=900, foreground="#555555",
            font=("Segoe UI", 8), justify=tk.LEFT
        ).pack(fill=tk.X)

    def _populate_models(self):
        """Populate models tree from registry."""
        self.models_tree.clear()

        category = self.category_combo.get()

        for model_id, info in MODELS.items():
            # Filter by category
            if category != "all" and info.get("folder") != category:
                continue

            # Check status
            status = self.downloader.get_model_status(info)

            self.models_tree.insert_item(
                values=(
                    info.get("name", model_id),
                    info.get("folder", ""),
                    f"{info.get('size_gb', 0):.2f} GB",
                    status
                ),
                item_id=model_id,
                checked=False
            )

    def _on_category_change(self, event=None):
        """Handle category filter change."""
        category = self.category_combo.get()
        tip = CATEGORY_TIPS.get(category, "")
        self.category_tip.config(text=tip)
        self._populate_models()

    def _refresh_models(self):
        """Refresh model list and status."""
        self._populate_models()
        self.main_window.set_status("Models refreshed")

    def _select_all(self):
        """Select all models."""
        self.models_tree.select_all()

    def _select_none(self):
        """Deselect all models."""
        self.models_tree.select_none()

    def _search_huggingface(self):
        """Search HuggingFace for models."""
        query = self.search_var.get().strip()
        if not query:
            messagebox.showwarning("Search", "Enter a search term (e.g., 'flux lora', 'sdxl checkpoint')")
            return

        self.main_window.set_status(f"Searching HuggingFace for '{query}'...")
        self.results_tree.clear()

        def do_search():
            return self.downloader.search_huggingface(query, limit=20)

        def on_complete(results):
            if not results:
                self.main_window.set_status("No results found. Try different search terms.")
                return

            for i, result in enumerate(results):
                self.results_tree.insert_item(
                    values=(
                        result.get("name", ""),
                        result.get("repo", ""),
                        result.get("folder", "checkpoints")
                    ),
                    item_id=f"search_{i}"
                )
                # Store full result for download
                self.results_tree.tree.set(f"search_{i}", "repo", result.get("repo", ""))

            self.main_window.set_status(f"Found {len(results)} results")

        self.main_window.run_async(do_search, on_complete)

    def _show_local_models(self):
        """Show locally installed models."""
        self.results_tree.clear()

        local_models = self.downloader.scan_local_models()

        for category, models in local_models.items():
            for model in models:
                self.results_tree.insert_item(
                    values=(
                        model.get("name", ""),
                        f"{model.get('size_gb', 0):.2f} GB",
                        model.get("folder", "")
                    ),
                    item_id=model.get("path", "")
                )

        total = sum(len(models) for models in local_models.values())
        self.main_window.set_status(f"Found {total} local models")

    def _download_selected(self):
        """Download selected models from registry."""
        selected = self.models_tree.get_checked_items()

        if not selected:
            messagebox.showwarning("Download", "Select models to download by clicking the checkbox column.")
            return

        models_to_download = []
        already_installed = []
        total_size = 0
        for model_id in selected:
            if model_id in MODELS:
                info = MODELS[model_id]
                if self.downloader.check_model_exists(info):
                    already_installed.append(info.get("name", model_id))
                else:
                    models_to_download.append({**info, "id": model_id})
                    total_size += info.get("size_gb", 0)

        if already_installed:
            self.main_window.log(f"{len(already_installed)} model(s) already installed, skipping:")
            for name in already_installed:
                self.main_window.log(f"  - {name}")

        if not models_to_download:
            self.main_window.set_status("All selected models are already installed.")
            self.main_window.log("All selected models are already installed.")
            return

        if not messagebox.askyesno(
            "Confirm Download",
            f"Download {len(models_to_download)} model(s)?\n"
            f"Total size: ~{total_size:.1f} GB\n\n"
            "Models are saved into ComfyUI's native models/ directory\n"
            "and will be preserved if you purge and reinstall."
        ):
            return

        self._start_download(models_to_download)

    def _download_from_search(self):
        """Download selected models from search results."""
        selected = self.results_tree.get_checked_items()

        if not selected:
            messagebox.showwarning("Download", "Select search results to download by clicking the checkbox column.")
            return

        models_to_download = []
        for item_id in selected:
            if item_id.startswith("search_"):
                # Get values from tree
                values = self.results_tree.tree.item(item_id)["values"]
                if len(values) >= 3:
                    models_to_download.append({
                        "name": values[1],  # After checkbox column
                        "repo": values[2],
                        "filename": "",  # Will need to be determined
                        "folder": values[3] if len(values) > 3 else "checkpoints"
                    })

        if models_to_download:
            self._start_download(models_to_download)

    def _start_download(self, models: list):
        """Start downloading models."""
        total = len(models)
        names = [m.get("name", m.get("filename", "?")) for m in models]
        total_gb = sum(m.get("size_gb", 0) for m in models)

        self.main_window.set_status(f"Downloading {total} model(s)...")
        self.main_window.log(f"Starting download of {total} model(s) (~{total_gb:.1f} GB):")
        for name in names:
            self.main_window.log(f"  - {name}")

        # Track the last message to avoid flooding the log with duplicate percent updates
        last_logged = {"msg": ""}

        def progress_callback(current, total_steps, message):
            if self.winfo_exists():
                self.after(0, lambda: self.progress.update_progress(current, total_steps, message))
                # Forward meaningful messages to the log (skip repeated % updates)
                base = message.split("...")[0] + "..." if "..." in message else message
                if base != last_logged["msg"]:
                    last_logged["msg"] = base
                    self.after(0, lambda m=message: self.main_window.log(m))

        def do_download():
            return self.downloader.download_multiple(models, progress_callback)

        def on_complete(results):
            success_count = sum(1 for v in results.values() if v)
            fail_count = len(results) - success_count

            if fail_count == 0:
                msg = f"Downloaded {success_count} model(s) successfully."
                self.main_window.set_status(msg)
                self.main_window.log(msg)
            else:
                msg = f"Downloads finished: {success_count} succeeded, {fail_count} failed."
                self.main_window.set_status(msg)
                self.main_window.log(msg)
                for name, ok in results.items():
                    if not ok:
                        self.main_window.log(f"  FAILED: {name}")

            self.progress.update_progress(100, 100, "Done")
            self._refresh_models()

        self.main_window.run_async(do_download, on_complete)
