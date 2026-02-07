"""
Main Window for ComfyUI Module Installer
"""
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import threading

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import WINDOW_TITLE, WINDOW_SIZE, BASE_DIR, APP_VERSION

from ui.install_tab import InstallTab
from ui.models_tab import ModelsTab
from ui.nodes_tab import NodesTab


class MainWindow:
    """Main application window."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title(WINDOW_TITLE)
        self.root.geometry(WINDOW_SIZE)
        self.root.minsize(1050, 750)

        # Set icon if available
        icon_path = BASE_DIR / "icon.ico"
        if icon_path.exists():
            self.root.iconbitmap(icon_path)

        self._setup_styles()
        self._setup_menu()
        self._setup_status_bar()  # Must be before _setup_ui so tabs can access server_status
        self._setup_ui()

        # Center window
        self._center_window()

    def _setup_styles(self):
        """Configure ttk styles."""
        style = ttk.Style()

        # Try to use a modern theme
        available_themes = style.theme_names()
        if "vista" in available_themes:
            style.theme_use("vista")
        elif "clam" in available_themes:
            style.theme_use("clam")

        # Custom styles
        style.configure("Title.TLabel", font=("Segoe UI", 14, "bold"))
        style.configure("Subtitle.TLabel", font=("Segoe UI", 9), foreground="#666666")
        style.configure("Status.TLabel", font=("Segoe UI", 9))
        style.configure("Tip.TLabel", font=("Segoe UI", 8), foreground="#555555")

    def _setup_menu(self):
        """Set up the menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open Models Folder", command=self._open_models_folder)
        file_menu.add_command(label="Open ComfyUI Folder", command=self._open_comfyui_folder)
        file_menu.add_command(label="Open Install Folder", command=self._open_install_folder)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_close)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Getting Started", command=self._show_getting_started)
        help_menu.add_command(label="VRAM Guide", command=self._show_vram_guide)
        help_menu.add_separator()
        help_menu.add_command(label="ComfyUI GitHub", command=self._open_comfyui_github)
        help_menu.add_command(label="ComfyUI Docs", command=self._open_comfyui_docs)
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self._show_about)

    def _setup_ui(self):
        """Set up the main UI."""
        # Main container
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        title_frame = ttk.Frame(header_frame)
        title_frame.pack(side=tk.LEFT)

        ttk.Label(
            title_frame,
            text="ComfyUI Module",
            style="Title.TLabel"
        ).pack(anchor=tk.W)

        ttk.Label(
            title_frame,
            text="Portable installer & manager -- no Python or Git required",
            style="Subtitle.TLabel"
        ).pack(anchor=tk.W)

        # Right side: location
        ttk.Label(
            header_frame,
            text=f"v{APP_VERSION}  |  {BASE_DIR}",
            style="Subtitle.TLabel"
        ).pack(side=tk.RIGHT, anchor=tk.E)

        # Notebook (tabs)
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Create tabs
        self.install_tab = InstallTab(self.notebook, self)
        self.models_tab = ModelsTab(self.notebook, self)
        self.nodes_tab = NodesTab(self.notebook, self)

        self.notebook.add(self.install_tab, text="  Install & Run  ")
        self.notebook.add(self.models_tab, text="  Models  ")
        self.notebook.add(self.nodes_tab, text="  Custom Nodes  ")

    def _setup_status_bar(self):
        """Set up the status bar."""
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.status_label = ttk.Label(
            status_frame,
            text="Ready",
            style="Status.TLabel",
            padding=(10, 5)
        )
        self.status_label.pack(side=tk.LEFT)

        # Server status indicator
        self.server_status = ttk.Label(
            status_frame,
            text="Server: Stopped",
            style="Status.TLabel",
            padding=(10, 5)
        )
        self.server_status.pack(side=tk.RIGHT)

    def _center_window(self):
        """Center the window on screen."""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"+{x}+{y}")

    def set_status(self, message: str):
        """Update the status bar message."""
        if self.root.winfo_exists():
            self.status_label.config(text=message)

    def set_server_status(self, running: bool, url: str = "", count: int = 1):
        """Update server status indicator."""
        if self.root.winfo_exists():
            if not running:
                self.server_status.config(text="Server: Stopped")
            elif count > 1:
                self.server_status.config(text=f"Server: {count} instances running")
            else:
                self.server_status.config(text=f"Server: Running ({url})")

    def run_async(self, func, callback=None):
        """Run a function in a background thread."""
        def wrapper():
            try:
                result = func()
                if callback and self.root.winfo_exists():
                    self.root.after(0, lambda: callback(result))
            except Exception as e:
                if self.root.winfo_exists():
                    self.root.after(0, lambda: self._show_error(str(e)))

        thread = threading.Thread(target=wrapper, daemon=True)
        thread.start()
        return thread

    def _show_error(self, message: str):
        """Show error dialog."""
        messagebox.showerror("Error", message)

    def _show_about(self):
        """Show about dialog."""
        messagebox.showinfo(
            "About ComfyUI Module",
            f"ComfyUI Module v{APP_VERSION}\n\n"
            "A fully autonomous, portable installer and manager for ComfyUI.\n\n"
            "This tool handles everything from scratch:\n"
            "  - Downloads and configures embedded Python\n"
            "  - Downloads portable Git (no system install needed)\n"
            "  - Installs ComfyUI and all dependencies\n"
            "  - Downloads models from HuggingFace\n"
            "  - Manages custom nodes\n"
            "  - Starts and controls the ComfyUI server\n\n"
            "The entire folder is portable -- copy it anywhere\n"
            "and it will still work.\n\n"
            f"Install location: {BASE_DIR}"
        )

    def _show_getting_started(self):
        """Show getting started guide."""
        messagebox.showinfo(
            "Getting Started",
            "Quick Start Guide\n"
            "=" * 40 + "\n\n"
            "1. INSTALL\n"
            "   Go to the 'Install & Run' tab and click 'Full Install'.\n"
            "   This downloads ComfyUI and all dependencies.\n"
            "   (Takes 5-15 min depending on internet speed)\n\n"
            "2. DOWNLOAD MODELS\n"
            "   Go to the 'Models' tab and select models to download.\n"
            "   For beginners, try 'Flux.1 Schnell FP8' -- it's fast\n"
            "   and works well on 8GB+ GPUs.\n\n"
            "3. START THE SERVER\n"
            "   Back on 'Install & Run', add an instance (pick a GPU),\n"
            "   select it, click 'Start', then 'Open UI' to use ComfyUI.\n\n"
            "4. CUSTOM NODES (Optional)\n"
            "   Go to 'Custom Nodes' and click 'Recommended' to\n"
            "   install popular quality-of-life extensions.\n\n"
            "Tips:\n"
            "  - If you have a low VRAM GPU (4-6GB), select 'low'\n"
            "    VRAM mode before starting the server.\n"
            "  - Use GGUF quantized models for lower VRAM usage.\n"
            "  - The entire folder is portable -- copy it to a USB\n"
            "    drive or another PC and it works."
        )

    def _show_vram_guide(self):
        """Show VRAM requirements guide."""
        messagebox.showinfo(
            "VRAM Guide",
            "GPU VRAM Recommendations\n"
            "=" * 40 + "\n\n"
            "24GB+ (RTX 3090, 4090, A6000):\n"
            "  Any model at full precision. Flux BF16, video models.\n\n"
            "12-16GB (RTX 3060 12GB, 4070 Ti, 4080):\n"
            "  FP8 checkpoints, GGUF Q8 models.\n"
            "  Use 'normal' VRAM mode.\n\n"
            "8GB (RTX 3060 8GB, 3070, 4060):\n"
            "  FP8 models, GGUF Q5/Q4 quantized.\n"
            "  May need 'low' VRAM mode for larger models.\n\n"
            "4-6GB (RTX 2060, 3050, GTX 1660):\n"
            "  GGUF Q4 models only. Use 'low' VRAM mode.\n"
            "  SD 1.5 works best at this level.\n\n"
            "No GPU / Integrated:\n"
            "  Use 'cpu' mode. Very slow but functional.\n"
            "  Stick to SD 1.5 or small GGUF models.\n\n"
            "Quantization Formats:\n"
            "  BF16/FP16 = Full quality, most VRAM\n"
            "  FP8 = Near-full quality, ~50% less VRAM\n"
            "  GGUF Q8 = Good quality, ~50% less VRAM\n"
            "  GGUF Q5 = Decent quality, ~65% less VRAM\n"
            "  GGUF Q4 = Acceptable quality, ~70% less VRAM"
        )

    def _open_models_folder(self):
        """Open models folder in file explorer."""
        from config import MODELS_DIR
        import os
        if MODELS_DIR.exists():
            os.startfile(str(MODELS_DIR))
        else:
            messagebox.showwarning("Warning", "Models folder does not exist yet.\nRun Full Install first.")

    def _open_comfyui_folder(self):
        """Open ComfyUI folder in file explorer."""
        from config import COMFYUI_DIR
        import os
        if COMFYUI_DIR.exists():
            os.startfile(str(COMFYUI_DIR))
        else:
            messagebox.showwarning("Warning", "ComfyUI is not installed yet.\nRun Full Install first.")

    def _open_install_folder(self):
        """Open the installation base folder in file explorer."""
        import os
        os.startfile(str(BASE_DIR))

    def _open_comfyui_github(self):
        """Open ComfyUI GitHub page."""
        import webbrowser
        webbrowser.open("https://github.com/comfyanonymous/ComfyUI")

    def _open_comfyui_docs(self):
        """Open ComfyUI documentation."""
        import webbrowser
        webbrowser.open("https://docs.comfy.org/")

    def _on_close(self):
        """Handle window close."""
        # Stop all running instances
        if hasattr(self.install_tab, 'instance_manager') and self.install_tab.instance_manager.any_running():
            count = self.install_tab.instance_manager.get_running_count()
            if messagebox.askyesno("Confirm Exit", f"{count} ComfyUI instance(s) running. Stop all and exit?"):
                self.install_tab.instance_manager.stop_all()
            else:
                return

        self.root.destroy()

    def run(self):
        """Start the application."""
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()
