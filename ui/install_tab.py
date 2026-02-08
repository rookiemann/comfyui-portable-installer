"""
Installation Tab for ComfyUI Module Installer
"""
import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    DEFAULT_HOST, DEFAULT_PORT, VRAM_MODES,
    VRAM_DESCRIPTIONS, EXTRA_FLAGS,
    COMFYUI_DIR, get_active_comfyui_dir, save_settings, load_settings,
    get_saved_comfyui_dirs, get_extra_model_dirs,
)

from core.comfy_installer import ComfyInstaller
from core.venv_manager import VenvManager
from core.gpu_manager import GPUManager
from core.instance_manager import InstanceManager, InstanceConfig
from ui.widgets import (
    ProgressFrame, StatusIndicator,
    ButtonBar, LabeledEntry, LabeledCombobox, ToolTip
)


class InstallTab(ttk.Frame):
    """Installation and server control tab."""

    def __init__(self, parent, main_window):
        super().__init__(parent, padding=10)
        self.main_window = main_window

        # Active ComfyUI path (may be external)
        self.active_comfyui_dir = get_active_comfyui_dir()

        # Initialize managers with the active path
        self.venv_manager = VenvManager()
        self.installer = ComfyInstaller(
            comfyui_dir=self.active_comfyui_dir,
            models_dir=self.active_comfyui_dir / "models",
            venv_manager=self.venv_manager,
        )
        self.instance_manager = InstanceManager(
            log_callback=self._shared_log,
            comfyui_dir=self.active_comfyui_dir,
        )

        # Detect GPUs
        self.gpu_list = GPUManager.get_gpu_display_list()
        self._gpu_map = {label: value for label, value in self.gpu_list}

        self._setup_ui()
        self._update_install_button_labels()
        # Defer heavy init (nvidia-smi, pip list) so the window appears immediately
        self.after(1, self._deferred_init)

    def _deferred_init(self):
        """Run heavy initialization in a background thread.

        Subprocess calls (nvidia-smi, pip list) block for several seconds;
        doing them here keeps the window responsive on startup.
        """
        def do_heavy_work():
            status = self.installer.check_installation()
            sa_installed = self.venv_manager.is_package_installed("sageattention")
            return status, sa_installed

        def on_complete(result):
            status, sa_installed = result
            # Update status indicators
            self.venv_status.set_status("ok" if status["venv_created"] else "pending")
            self.comfyui_status.set_status("ok" if status["comfyui_installed"] else "pending")
            self._update_status_bar()

            # Update SageAttention checkbox label
            sa_label = "SageAttention (installed)" if sa_installed else "SageAttention (not installed)"
            self.flag_checkbuttons["sage_attention"].config(text=sa_label)

            self._log(f"Status: Python={'ready' if status['venv_created'] else 'not set up'}, "
                      f"ComfyUI={'installed' if status['comfyui_installed'] else 'not installed'}")

            # Show first-launch hint if applicable
            if not status["comfyui_installed"]:
                self._show_first_launch_hint(status)

        self.main_window.run_async(do_heavy_work, on_complete)

    def _setup_ui(self):
        # Single full-width layout (log lives on the dedicated Log tab)
        main_panel = ttk.Frame(self)
        main_panel.pack(fill=tk.BOTH, expand=True)

        # === Target ComfyUI ===
        self._setup_target_section(main_panel)

        # === Installation ===
        install_frame = ttk.LabelFrame(main_panel, text="Installation", padding=10)
        install_frame.pack(fill=tk.X, pady=(0, 10))

        # Status indicators
        status_frame = ttk.Frame(install_frame)
        status_frame.pack(fill=tk.X, pady=(0, 5))

        self.venv_status = StatusIndicator(status_frame, "Python Environment")
        self.venv_status.pack(anchor=tk.W, pady=2)

        self.comfyui_status = StatusIndicator(status_frame, "ComfyUI")
        self.comfyui_status.pack(anchor=tk.W, pady=2)

        # Install info text
        info_text = (
            "Full Install will: set up the Python environment, install PyTorch "
            "with CUDA support, clone ComfyUI from GitHub, install all "
            "dependencies, and create model directories."
        )
        info_label = ttk.Label(
            install_frame, text=info_text,
            wraplength=800, foreground="#555555",
            font=("Segoe UI", 8)
        )
        info_label.pack(fill=tk.X, pady=(0, 5))

        # Install buttons
        self.install_buttons = ButtonBar(install_frame)
        self.install_buttons.pack(fill=tk.X, pady=5)

        self.install_buttons.add_button(
            "full_install", "Full Install",
            self._full_install, width=15
        )
        self.install_buttons.add_button(
            "update", "Update ComfyUI",
            self._update_comfyui, width=15
        )
        self.install_buttons.add_button(
            "sage", "Install SageAttention",
            self._install_sage_attention, width=20
        )
        self.install_buttons.add_button(
            "purge", "Purge ComfyUI",
            self._purge_comfyui, width=15
        )
        self.install_buttons.add_button(
            "refresh", "Refresh",
            self._refresh_status, width=10
        )

        # Progress
        self.install_progress = ProgressFrame(install_frame)
        self.install_progress.pack(fill=tk.X, pady=5)

        # === Server Instances ===
        server_frame = ttk.LabelFrame(main_panel, text="Server Instances", padding=10)
        server_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # --- Add Instance controls (compact) ---
        add_frame = ttk.Frame(server_frame)
        add_frame.pack(fill=tk.X, pady=(0, 5))

        # Row 1: GPU dropdown (full width — labels are long)
        row1 = ttk.Frame(add_frame)
        row1.pack(fill=tk.X, pady=2)

        gpu_labels = [label for label, _ in self.gpu_list]
        # Default to the first GPU if available, otherwise CPU
        default_gpu = gpu_labels[1] if len(gpu_labels) > 1 else gpu_labels[0]
        self.gpu_combo = LabeledCombobox(row1, "Device:", gpu_labels, default_gpu, width=45)
        self.gpu_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ToolTip(self.gpu_combo, "Select a GPU to run ComfyUI on, or CPU for no-GPU mode.\n"
                "Each instance can be pinned to a different GPU.")

        # Row 2: Port + Host + VRAM + Add button
        row2 = ttk.Frame(add_frame)
        row2.pack(fill=tk.X, pady=2)

        self.port_entry = LabeledEntry(
            row2, "Port:", str(self.instance_manager.next_available_port())
        )
        self.port_entry.entry.config(width=6)
        self.port_entry.pack(side=tk.LEFT, padx=(0, 8))

        self.host_entry = LabeledEntry(row2, "Host:", DEFAULT_HOST)
        self.host_entry.entry.config(width=12)
        self.host_entry.pack(side=tk.LEFT, padx=(0, 8))

        self.vram_combo = LabeledCombobox(
            row2, "VRAM:", list(VRAM_MODES.keys()), "normal", width=8
        )
        self.vram_combo.pack(side=tk.LEFT, padx=(0, 8))
        self.vram_combo.combo.bind("<<ComboboxSelected>>", self._on_vram_change)
        ToolTip(self.vram_combo, "VRAM management mode. Use 'normal' for 8GB+ GPUs,\n"
                "'low' for 4-6GB, 'none' for 2-4GB, 'cpu' for no GPU.")

        ttk.Button(
            row2, text="Add Instance", command=self._add_instance, width=13
        ).pack(side=tk.LEFT)

        # Row 3: VRAM description
        self.vram_desc_label = ttk.Label(
            add_frame,
            text=VRAM_DESCRIPTIONS.get("normal", ""),
            wraplength=800, foreground="#555555",
            font=("Segoe UI", 8)
        )
        self.vram_desc_label.pack(fill=tk.X, pady=(0, 2))

        # Row 4: Startup flags (compact horizontal layout, no descriptions)
        flags_frame = ttk.Frame(add_frame)
        flags_frame.pack(fill=tk.X, pady=(0, 2))

        ttk.Label(flags_frame, text="Flags:", font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(0, 5))

        self.flag_vars = {}
        self.flag_checkbuttons = {}
        for flag_id, flag_info in EXTRA_FLAGS.items():
            var = tk.BooleanVar(value=False)
            self.flag_vars[flag_id] = var
            cb = ttk.Checkbutton(flags_frame, text=flag_info["label"], variable=var)
            cb.pack(side=tk.LEFT, padx=(0, 6))
            self.flag_checkbuttons[flag_id] = cb
            ToolTip(cb, flag_info["description"])

        # --- Instance Table ---
        table_frame = ttk.Frame(server_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        columns = ("gpu", "port", "vram", "status", "url")
        self.instance_tree = ttk.Treeview(
            table_frame, columns=columns, show="headings",
            height=5, selectmode="browse"
        )
        self.instance_tree.heading("gpu", text="Device")
        self.instance_tree.heading("port", text="Port")
        self.instance_tree.heading("vram", text="VRAM")
        self.instance_tree.heading("status", text="Status")
        self.instance_tree.heading("url", text="URL")

        self.instance_tree.column("gpu", width=200, minwidth=140)
        self.instance_tree.column("port", width=50, minwidth=40)
        self.instance_tree.column("vram", width=60, minwidth=45)
        self.instance_tree.column("status", width=65, minwidth=50)
        self.instance_tree.column("url", width=140, minwidth=90)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.instance_tree.yview)
        self.instance_tree.configure(yscrollcommand=scrollbar.set)

        self.instance_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind selection change to enable/disable per-instance buttons
        self.instance_tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        # Double-click to open in browser
        self.instance_tree.bind("<Double-1>", self._on_tree_dblclick)

        # --- Instance Control Buttons ---
        self.instance_buttons = ButtonBar(server_frame)
        self.instance_buttons.pack(fill=tk.X, pady=(5, 0))

        self.instance_buttons.add_button(
            "start_sel", "Start",
            self._start_selected, width=8
        )
        self.instance_buttons.add_button(
            "stop_sel", "Stop",
            self._stop_selected, width=8
        )
        self.instance_buttons.add_button(
            "start_all", "Start All",
            self._start_all, width=9
        )
        self.instance_buttons.add_button(
            "stop_all", "Stop All",
            self._stop_all, width=9
        )
        self.instance_buttons.add_button(
            "remove", "Remove",
            self._remove_selected, width=9
        )
        self.instance_buttons.add_button(
            "open_ui", "Open UI",
            self._open_browser, width=9
        )

        # Per-instance buttons start disabled (no row selected)
        for name in ("start_sel", "stop_sel", "remove", "open_ui"):
            self.instance_buttons.disable(name)

    # ---- Target ComfyUI path ----

    def _setup_target_section(self, parent):
        """Add the compact 'Target ComfyUI' path selector at the top of the left panel."""
        target_frame = ttk.LabelFrame(parent, text="Target ComfyUI", padding=6)
        target_frame.pack(fill=tk.X, pady=(0, 6))

        # Path display
        path_row = ttk.Frame(target_frame)
        path_row.pack(fill=tk.X)

        self._target_path_var = tk.StringVar(value=str(self.active_comfyui_dir))
        self._target_entry = ttk.Entry(
            path_row, textvariable=self._target_path_var, state="readonly"
        )
        self._target_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        ttk.Button(
            path_row, text="Browse...", command=self._browse_comfyui, width=9
        ).pack(side=tk.LEFT, padx=(0, 3))

        self._reset_btn = ttk.Button(
            path_row, text="Reset", command=self._reset_to_builtin, width=7
        )
        self._reset_btn.pack(side=tk.LEFT, padx=(0, 3))

        ttk.Button(
            path_row, text="Manage Paths...", command=self._open_paths_dialog, width=14
        ).pack(side=tk.LEFT)

        # Status label
        self._target_status = ttk.Label(
            target_frame, font=("Segoe UI", 8), foreground="#555555"
        )
        self._target_status.pack(anchor=tk.W, pady=(2, 0))
        self._update_target_status()

    def _update_target_status(self):
        """Update the target status label and reset button state."""
        if self.installer.is_external:
            self._target_status.config(text="Mode: External ComfyUI", foreground="#0066cc")
            self._reset_btn.state(["!disabled"])
        else:
            self._target_status.config(text="Mode: Built-in", foreground="#555555")
            self._reset_btn.state(["disabled"])

    # ---- Manage Paths dialog ----

    def _open_paths_dialog(self):
        """Open a dialog to manage saved ComfyUI installs and extra model directories."""
        dlg = tk.Toplevel(self.winfo_toplevel())
        dlg.title("Manage Paths")
        dlg.geometry("550x420")
        dlg.resizable(True, True)
        dlg.transient(self.winfo_toplevel())
        dlg.grab_set()

        # --- Saved ComfyUI Installs ---
        saved_frame = ttk.LabelFrame(dlg, text="Saved ComfyUI Installs (model cross-referencing)", padding=8)
        saved_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 5))

        self._saved_listbox = tk.Listbox(saved_frame, height=5, font=("Segoe UI", 9))
        self._saved_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        saved_btns = ttk.Frame(saved_frame)
        saved_btns.pack(side=tk.RIGHT, fill=tk.Y)

        ttk.Button(saved_btns, text="Add", command=self._add_saved_comfyui, width=8).pack(pady=(0, 3))
        ttk.Button(saved_btns, text="Remove", command=self._remove_saved_comfyui, width=8).pack(pady=(0, 3))
        ttk.Button(saved_btns, text="Switch", command=self._switch_to_saved, width=8).pack()

        self._refresh_saved_list()

        # --- Extra Model Directories ---
        extra_frame = ttk.LabelFrame(dlg, text="Extra Model Search Directories", padding=8)
        extra_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 5))

        self._extra_listbox = tk.Listbox(extra_frame, height=5, font=("Segoe UI", 9))
        self._extra_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        extra_btns = ttk.Frame(extra_frame)
        extra_btns.pack(side=tk.RIGHT, fill=tk.Y)

        ttk.Button(extra_btns, text="Add", command=self._add_extra_model_dir, width=8).pack(pady=(0, 3))
        ttk.Button(extra_btns, text="Remove", command=self._remove_extra_model_dir, width=8).pack()

        self._refresh_extra_list()

        # --- Info + Close ---
        ttk.Label(
            dlg,
            text="Models from all saved installs and extra directories are automatically "
                 "visible to the active ComfyUI on server start.",
            wraplength=500, foreground="#555555", font=("Segoe UI", 8),
        ).pack(padx=10, pady=(0, 5))

        ttk.Button(dlg, text="Close", command=dlg.destroy, width=10).pack(pady=(0, 10))

    # ---- Saved ComfyUI installs ----

    def _refresh_saved_list(self):
        """Reload the saved ComfyUI installs listbox from settings."""
        self._saved_listbox.delete(0, tk.END)
        for d in get_saved_comfyui_dirs():
            label = d
            if str(COMFYUI_DIR) == d:
                label += "  (built-in)"
            self._saved_listbox.insert(tk.END, label)

    def _add_saved_comfyui(self):
        """Add a ComfyUI install to the saved list."""
        chosen = filedialog.askdirectory(
            title="Select ComfyUI Directory (must contain main.py)"
        )
        if not chosen:
            return
        path = Path(chosen)
        if not (path / "main.py").exists():
            from tkinter import messagebox
            messagebox.showwarning(
                "Invalid Directory",
                f"No main.py found in:\n{path}\n\n"
                "Please select a valid ComfyUI installation directory."
            )
            return
        settings = load_settings()
        saved = settings.get("saved_comfyui_dirs", [])
        path_str = str(path)
        if path_str not in saved and path_str != str(COMFYUI_DIR):
            saved.append(path_str)
            save_settings({"saved_comfyui_dirs": saved})
        self._refresh_saved_list()
        self._log(f"Added saved ComfyUI: {path}", tag="config")

    def _remove_saved_comfyui(self):
        """Remove the selected entry from saved installs (can't remove built-in)."""
        sel = self._saved_listbox.curselection()
        if not sel:
            return
        entry = self._saved_listbox.get(sel[0])
        dir_str = entry.replace("  (built-in)", "")
        if dir_str == str(COMFYUI_DIR):
            self._log("Cannot remove the built-in ComfyUI.", tag="config")
            return
        settings = load_settings()
        saved = settings.get("saved_comfyui_dirs", [])
        if dir_str in saved:
            saved.remove(dir_str)
            save_settings({"saved_comfyui_dirs": saved})
        self._refresh_saved_list()
        self._log(f"Removed saved ComfyUI: {dir_str}", tag="config")

    def _switch_to_saved(self):
        """Switch the active target to the selected saved install."""
        sel = self._saved_listbox.curselection()
        if not sel:
            return
        entry = self._saved_listbox.get(sel[0])
        dir_str = entry.replace("  (built-in)", "")
        path = Path(dir_str)
        if not (path / "main.py").exists():
            self._log(f"Invalid install (main.py not found): {path}", tag="config")
            return
        if dir_str == str(COMFYUI_DIR):
            self._reset_to_builtin()
        else:
            save_settings({"comfyui_dir": dir_str})
            self._apply_comfyui_dir(path)
            self._log(f"Switched to: {path}", tag="config")

    # ---- Extra model directories ----

    def _refresh_extra_list(self):
        """Reload the extra model directories listbox from settings."""
        self._extra_listbox.delete(0, tk.END)
        for d in get_extra_model_dirs():
            self._extra_listbox.insert(tk.END, d)

    def _add_extra_model_dir(self):
        """Add an extra model search directory."""
        chosen = filedialog.askdirectory(
            title="Select a directory containing models"
        )
        if not chosen:
            return
        settings = load_settings()
        extras = settings.get("extra_model_dirs", [])
        if chosen not in extras:
            extras.append(chosen)
            save_settings({"extra_model_dirs": extras})
        self._refresh_extra_list()
        self._log(f"Added extra model directory: {chosen}", tag="config")

    def _remove_extra_model_dir(self):
        """Remove the selected extra model directory."""
        sel = self._extra_listbox.curselection()
        if not sel:
            return
        dir_str = self._extra_listbox.get(sel[0])
        settings = load_settings()
        extras = settings.get("extra_model_dirs", [])
        if dir_str in extras:
            extras.remove(dir_str)
            save_settings({"extra_model_dirs": extras})
        self._refresh_extra_list()
        self._log(f"Removed extra model directory: {dir_str}", tag="config")

    # ---- Target path selection ----

    def _browse_comfyui(self):
        """Open folder picker to select an external ComfyUI directory."""
        chosen = filedialog.askdirectory(
            title="Select ComfyUI Directory (must contain main.py)"
        )
        if not chosen:
            return

        path = Path(chosen)
        if not (path / "main.py").exists():
            from tkinter import messagebox
            messagebox.showwarning(
                "Invalid Directory",
                f"No main.py found in:\n{path}\n\n"
                "Please select a valid ComfyUI installation directory."
            )
            return

        path_str = str(path)
        # Auto-add to saved installs list
        settings = load_settings()
        saved = settings.get("saved_comfyui_dirs", [])
        updates = {"comfyui_dir": path_str}
        if path_str not in saved and path_str != str(COMFYUI_DIR):
            saved.append(path_str)
            updates["saved_comfyui_dirs"] = saved
        save_settings(updates)
        self._refresh_saved_list()
        self._apply_comfyui_dir(path)
        self._log(f"Switched to external ComfyUI: {path}", tag="config")

    def _reset_to_builtin(self):
        """Reset back to the built-in ComfyUI directory."""
        save_settings({"comfyui_dir": None})
        self._apply_comfyui_dir(COMFYUI_DIR)
        self._log("Switched back to built-in ComfyUI", tag="config")

    def _apply_comfyui_dir(self, path: Path):
        """Apply a new ComfyUI directory across all managers and tabs."""
        self.active_comfyui_dir = path

        # Rebuild managers
        self.installer = ComfyInstaller(
            comfyui_dir=path,
            models_dir=path / "models",
            venv_manager=self.venv_manager,
        )
        # Stop all instances before switching (they point to the old path)
        if self.instance_manager.any_running():
            self.instance_manager.stop_all()
            for state in self.instance_manager.get_all_instances():
                self._update_tree_status(state.instance_id, "Stopped")
        # Clear instance table — instances are tied to the old path
        for item in self.instance_tree.get_children():
            self.instance_tree.delete(item)
        self.instance_manager = InstanceManager(
            log_callback=self._shared_log,
            comfyui_dir=path,
        )

        # Update UI
        self._target_path_var.set(str(path))
        self._update_target_status()
        self._update_install_button_labels()
        self._refresh_status()

        # Propagate to other tabs via main_window
        self.main_window.set_comfyui_dir(path)

    def _update_install_button_labels(self):
        """Adapt button labels and state for external vs built-in mode."""
        if self.installer.is_external:
            self.install_buttons.set_text("full_install", "Install Deps")
            self.install_buttons.disable("purge")
        else:
            self.install_buttons.set_text("full_install", "Full Install")
            self.install_buttons.enable("purge")

    def set_comfyui_dir(self, path: Path):
        """Public API called by main_window when the path changes externally."""
        if path.resolve() != self.active_comfyui_dir.resolve():
            self._apply_comfyui_dir(path)

    # ---- Logging helpers ----

    def _log(self, message: str, tag: str = "install"):
        """Write to the central Log tab."""
        self.main_window.log(message, tag=tag)

    def _shared_log(self, line: str):
        """Thread-safe log callback used by InstanceManager."""
        if self.winfo_exists():
            self.after(0, lambda: self._log(line, tag="server"))

    # ---- Tree selection / double-click ----

    def _on_tree_select(self, event=None):
        """Enable/disable per-instance buttons based on selection."""
        has_sel = bool(self.instance_tree.selection())
        for name in ("start_sel", "stop_sel", "remove", "open_ui"):
            if has_sel:
                self.instance_buttons.enable(name)
            else:
                self.instance_buttons.disable(name)

    def _on_tree_dblclick(self, event=None):
        """Open selected instance in browser on double-click."""
        self._open_browser()

    # ---- VRAM description ----

    def _on_vram_change(self, event=None):
        """Update VRAM description when mode changes."""
        mode = self.vram_combo.get()
        desc = VRAM_DESCRIPTIONS.get(mode, "")
        self.vram_desc_label.config(text=desc)

    # ---- Extra args ----

    def _get_extra_args(self):
        """Build extra args list from checked startup flags."""
        args = []
        for flag_id, var in self.flag_vars.items():
            if var.get():
                flag_str = EXTRA_FLAGS[flag_id]["flag"]
                args.extend(flag_str.split())
        return args

    # ---- Instance management ----

    def _add_instance(self):
        """Add a new server instance from the UI fields."""
        gpu_label = self.gpu_combo.get()
        gpu_device = self._gpu_map.get(gpu_label, "cpu")

        try:
            port = int(self.port_entry.get())
        except ValueError:
            self._log("Error: Invalid port number.", tag="server")
            return

        if port < 1024 or port > 65535:
            self._log("Error: Port must be between 1024 and 65535.", tag="server")
            return

        host = self.host_entry.get().strip() or DEFAULT_HOST
        vram_mode = self.vram_combo.get()
        extra_args = self._get_extra_args()

        # Auto-set CPU VRAM mode when CPU device is selected
        if gpu_device == "cpu" and vram_mode != "cpu":
            vram_mode = "cpu"
            self._log("Note: Forced VRAM mode to 'cpu' for CPU device.", tag="server")

        config = InstanceConfig(
            gpu_device=gpu_device,
            gpu_label=gpu_label,
            port=port,
            host=host,
            vram_mode=vram_mode,
            extra_args=extra_args,
        )

        try:
            instance_id = self.instance_manager.add_instance(config)
        except ValueError as e:
            self._log(f"Error: {e}", tag="server")
            return

        # Add row to table
        url = f"http://{host}:{port}"
        self.instance_tree.insert(
            "", tk.END, iid=instance_id,
            values=(gpu_label, port, vram_mode, "Stopped", url)
        )

        self._log(f"Added instance {instance_id} ({gpu_label} on port {port})", tag="server")

        # Auto-advance port for next add
        next_port = self.instance_manager.next_available_port()
        self.port_entry.entry.delete(0, tk.END)
        self.port_entry.entry.insert(0, str(next_port))

    def _get_selected_id(self) -> str:
        """Return the instance_id of the selected tree row, or empty string."""
        sel = self.instance_tree.selection()
        return sel[0] if sel else ""

    def _start_selected(self):
        """Start the selected instance."""
        instance_id = self._get_selected_id()
        if not instance_id:
            self._log("No instance selected.", tag="server")
            return

        if not self.installer.is_installed:
            self._log("ComfyUI not installed! Run Full Install first.", tag="server")
            return

        state = self.instance_manager.get_instance(instance_id)
        if state and state.server.is_running:
            self._log(f"Instance {instance_id} is already running.", tag="server")
            return

        self._log(f"Starting instance {instance_id}...", tag="server")
        self._update_tree_status(instance_id, "Starting")

        def progress_callback(current, total, message):
            if self.winfo_exists():
                self.after(0, lambda: self._log(message, tag="server"))

        def do_start():
            return self.instance_manager.start_instance(instance_id, progress_callback)

        def on_complete(success):
            if success:
                self._update_tree_status(instance_id, "Running")
                self._log(f"Instance {instance_id} is running.", tag="server")
            else:
                self._update_tree_status(instance_id, "Error")
                self._log(f"Instance {instance_id} failed to start.", tag="server")
            self._update_status_bar()

        self.main_window.run_async(do_start, on_complete)

    def _stop_selected(self):
        """Stop the selected instance."""
        instance_id = self._get_selected_id()
        if not instance_id:
            self._log("No instance selected.", tag="server")
            return

        state = self.instance_manager.get_instance(instance_id)
        if state and not state.server.is_running:
            self._log(f"Instance {instance_id} is not running.", tag="server")
            return

        self._log(f"Stopping instance {instance_id}...", tag="server")

        def progress_callback(current, total, message):
            if self.winfo_exists():
                self.after(0, lambda: self._log(message, tag="server"))

        def do_stop():
            return self.instance_manager.stop_instance(instance_id, progress_callback)

        def on_complete(success):
            if success:
                self._update_tree_status(instance_id, "Stopped")
                self._log(f"Instance {instance_id} stopped.", tag="server")
            else:
                self._log(f"Failed to stop instance {instance_id}.", tag="server")
            self._update_status_bar()

        self.main_window.run_async(do_stop, on_complete)

    def _start_all(self):
        """Start all stopped instances."""
        if not self.installer.is_installed:
            self._log("ComfyUI not installed! Run Full Install first.", tag="server")
            return

        instances = self.instance_manager.get_all_instances()
        to_start = [s for s in instances if not s.server.is_running]

        if not to_start:
            self._log("No stopped instances to start.", tag="server")
            return

        self._log(f"Starting {len(to_start)} instance(s)...", tag="server")

        for state in to_start:
            self._update_tree_status(state.instance_id, "Starting")

        def do_start_all():
            # Start all instances in parallel threads so they don't block each other
            import concurrent.futures
            results = {}
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(to_start)) as executor:
                futures = {
                    executor.submit(self.instance_manager.start_instance, s.instance_id): s.instance_id
                    for s in to_start
                }
                for future in concurrent.futures.as_completed(futures):
                    iid = futures[future]
                    try:
                        results[iid] = future.result()
                    except Exception:
                        results[iid] = False
            return results

        def on_complete(results):
            for iid, success in results.items():
                self._update_tree_status(iid, "Running" if success else "Error")
            running = sum(1 for v in results.values() if v)
            self._log(f"Started {running}/{len(results)} instance(s).", tag="server")
            self._update_status_bar()

        self.main_window.run_async(do_start_all, on_complete)

    def _stop_all(self):
        """Stop all running instances."""
        instances = self.instance_manager.get_all_instances()
        to_stop = [s for s in instances if s.server.is_running]

        if not to_stop:
            self._log("No running instances to stop.", tag="server")
            return

        self._log(f"Stopping {len(to_stop)} instance(s)...", tag="server")

        def do_stop_all():
            return self.instance_manager.stop_all()

        def on_complete(success):
            for state in self.instance_manager.get_all_instances():
                self._update_tree_status(state.instance_id, "Stopped")
            self._log("All instances stopped.", tag="server")
            self._update_status_bar()

        self.main_window.run_async(do_stop_all, on_complete)

    def _remove_selected(self):
        """Remove the selected instance (stops it first if running)."""
        instance_id = self._get_selected_id()
        if not instance_id:
            self._log("No instance selected.", tag="server")
            return

        state = self.instance_manager.get_instance(instance_id)
        if state and state.server.is_running:
            from tkinter import messagebox
            if not messagebox.askyesno(
                "Instance Running",
                f"Instance {instance_id} is running.\nStop and remove it?"
            ):
                return

        def do_remove():
            return self.instance_manager.remove_instance(instance_id)

        def on_complete(success):
            if success:
                self.instance_tree.delete(instance_id)
                self._log(f"Removed instance {instance_id}.", tag="server")
            else:
                self._log(f"Failed to remove instance {instance_id}.", tag="server")
            self._update_status_bar()

        self.main_window.run_async(do_remove, on_complete)

    def _open_browser(self):
        """Open the selected instance in a browser."""
        instance_id = self._get_selected_id()
        if not instance_id:
            self._log("No instance selected.", tag="server")
            return

        state = self.instance_manager.get_instance(instance_id)
        if not state:
            return

        import webbrowser
        url = f"http://{state.config.host}:{state.config.port}"
        self._log(f"Opening {url} in browser...", tag="server")
        webbrowser.open(url)

    # ---- Tree / status helpers ----

    def _update_tree_status(self, instance_id: str, status: str):
        """Update the status column for an instance row."""
        if self.winfo_exists() and self.instance_tree.exists(instance_id):
            values = list(self.instance_tree.item(instance_id, "values"))
            values[3] = status
            self.instance_tree.item(instance_id, values=values)

    def _update_status_bar(self):
        """Update the main window status bar with running instance count."""
        count = self.instance_manager.get_running_count()
        if count == 0:
            self.main_window.set_server_status(False)
        elif count == 1:
            # Find the one running instance URL
            for s in self.instance_manager.get_all_instances():
                if s.server.is_running:
                    url = f"http://{s.config.host}:{s.config.port}"
                    self.main_window.set_server_status(True, url)
                    break
        else:
            self.main_window.set_server_status(True, count=count)

    # ---- Status refresh ----

    def _refresh_status(self):
        """Refresh installation status indicators."""
        status = self.installer.check_installation()

        self.venv_status.set_status("ok" if status["venv_created"] else "pending")
        self.comfyui_status.set_status("ok" if status["comfyui_installed"] else "pending")

        # Refresh instance table statuses
        for state in self.instance_manager.get_all_instances():
            if state.server.is_running:
                self._update_tree_status(state.instance_id, "Running")
            elif state.status == "error":
                self._update_tree_status(state.instance_id, "Error")
            else:
                self._update_tree_status(state.instance_id, "Stopped")

        self._update_status_bar()

        # Update SageAttention checkbox label based on install status
        sa_installed = self.venv_manager.is_package_installed("sageattention")
        sa_label = "SageAttention (installed)" if sa_installed else "SageAttention (not installed)"
        self.flag_checkbuttons["sage_attention"].config(text=sa_label)

        self._log(f"Status: Python={'ready' if status['venv_created'] else 'not set up'}, "
                    f"ComfyUI={'installed' if status['comfyui_installed'] else 'not installed'}")

    # ---- Installation operations (unchanged) ----

    def _full_install(self):
        """Perform full installation."""
        self._log("Starting full installation...")
        self._log("  Step 1: Set up Python environment")
        self._log("  Step 2: Install PyTorch with CUDA")
        self._log("  Step 3: Clone ComfyUI from GitHub")
        self._log("  Step 4: Install ComfyUI dependencies")
        self._log("  Step 5: Create model directories")
        self.main_window.set_status("Installing...")

        def progress_callback(current, total, message):
            if self.winfo_exists():
                self.after(0, lambda: self._update_progress(current, total, message))

        def do_install():
            return self.installer.full_install(progress_callback)

        def on_complete(success):
            if success:
                self._log("Installation completed successfully!")
                self._log("Next steps: Go to the Models tab to download models,")
                self._log("then add an instance, select it, and click 'Start'.")
                self.main_window.set_status("Installation complete")
            else:
                self._log("Installation failed! Check the log for details.")
                self.main_window.set_status("Installation failed")
            self._refresh_status()

        self.main_window.run_async(do_install, on_complete)

    def _install_sage_attention(self):
        """Install Triton + SageAttention."""
        if not self.venv_manager.is_created:
            self._log("Python environment not set up. Run Full Install first.")
            return

        if self.venv_manager.is_package_installed("sageattention"):
            from tkinter import messagebox
            if not messagebox.askyesno(
                "Already Installed",
                "SageAttention is already installed.\n\nReinstall?"
            ):
                return

        self._log("Installing Triton + SageAttention...")
        self._log("  This enables 2-3x faster attention operations,")
        self._log("  especially useful for video generation workflows.")
        self.main_window.set_status("Installing SageAttention...")

        def progress_callback(current, total, message):
            if self.winfo_exists():
                self.after(0, lambda: self._update_progress(current, total, message))

        def do_install():
            return self.venv_manager.install_sage_attention(progress_callback)

        def on_complete(success):
            if success:
                self._log("SageAttention installed! Enable the checkbox below to use it.")
                self.main_window.set_status("SageAttention installed")
            else:
                self._log("SageAttention installation failed. Check the log for details.")
                self.main_window.set_status("SageAttention install failed")
            self._refresh_status()

        self.main_window.run_async(do_install, on_complete)

    def _update_comfyui(self):
        """Update ComfyUI."""
        if not self.installer.is_installed:
            self._log("ComfyUI not installed. Use Full Install first.")
            return

        self._log("Updating ComfyUI (pulling latest from GitHub)...")
        self.main_window.set_status("Updating...")

        def progress_callback(current, total, message):
            if self.winfo_exists():
                self.after(0, lambda: self._update_progress(current, total, message))

        def do_update():
            return self.installer.update_comfyui(progress_callback)

        def on_complete(success):
            if success:
                self._log("Update completed!")
                self.main_window.set_status("Update complete")
            else:
                self._log("Update failed!")
                self.main_window.set_status("Update failed")

        self.main_window.run_async(do_update, on_complete)

    def _purge_comfyui(self):
        """Purge ComfyUI installation (keeps Python env and models)."""
        from tkinter import messagebox

        if not self.installer.is_installed:
            self._log("ComfyUI not installed. Nothing to purge.")
            return

        # Stop all instances first if any are running
        if self.instance_manager.any_running():
            count = self.instance_manager.get_running_count()
            if not messagebox.askyesno(
                "Instances Running",
                f"{count} instance(s) running. Stop all and purge?"
            ):
                return
            self.instance_manager.stop_all()
            import time
            time.sleep(2)

        # Confirm purge
        if not messagebox.askyesno(
            "Confirm Purge",
            "This will DELETE the ComfyUI installation.\n\n"
            "KEPT: Python environment\n"
            "BACKED UP: Downloaded models (auto-restored on reinstall)\n"
            "DELETED: ComfyUI repo, Custom nodes\n\n"
            "You can run 'Full Install' again after purging.\n\n"
            "Continue?"
        ):
            return

        self._log("Purging ComfyUI installation...")
        self.main_window.set_status("Purging...")

        def progress_callback(current, total, message):
            if self.winfo_exists():
                self.after(0, lambda: self._update_progress(current, total, message))

        def do_purge():
            return self.installer.purge_comfyui(progress_callback)

        def on_complete(success):
            if success:
                self._log("Purge completed! Use 'Full Install' for fresh installation.")
                self.main_window.set_status("Purge complete")
            else:
                self._log("Purge failed!")
                self.main_window.set_status("Purge failed")
            self._refresh_status()

        self.main_window.run_async(do_purge, on_complete)

    def _update_progress(self, current, total, message):
        """Update progress from main thread."""
        self.install_progress.update_progress(current, total, message)
        self._log(message)

    def _show_first_launch_hint(self, status=None):
        """Show helpful guidance on first launch when nothing is installed."""
        if status is None:
            status = self.installer.check_installation()
        if status["comfyui_installed"]:
            return  # Not a first launch

        gpu_count = len(self.gpu_list) - 1  # Subtract CPU entry
        gpu_msg = f"Detected {gpu_count} GPU(s)." if gpu_count > 0 else "No NVIDIA GPU detected (CPU mode available)."

        self._log("=" * 50, tag="system")
        self._log("  Welcome to ComfyUI Module!", tag="system")
        self._log("=" * 50, tag="system")
        self._log("", tag="system")
        self._log(f"  {gpu_msg}", tag="system")
        self._log("", tag="system")
        if not status["venv_created"]:
            self._log("Getting started:", tag="system")
            self._log("  1. Click 'Full Install' to set up everything.", tag="system")
            self._log("     This will download ComfyUI, PyTorch, and", tag="system")
            self._log("     all dependencies (~5-15 min).", tag="system")
            self._log("", tag="system")
            self._log("  2. After install, go to the Models tab to", tag="system")
            self._log("     download AI models (required to generate).", tag="system")
            self._log("", tag="system")
            self._log("  3. Then add a server instance (pick a GPU),", tag="system")
            self._log("     select it, click 'Start', and 'Open UI'", tag="system")
            self._log("     to launch ComfyUI in your browser.", tag="system")
        else:
            self._log("Python environment is ready.", tag="system")
            self._log("Click 'Full Install' to download and set up ComfyUI.", tag="system")
        self._log("", tag="system")
        self._log("Tip: Check Help > Getting Started for a full guide.", tag="system")
        self._log("     Check Help > VRAM Guide to pick the right models", tag="system")
        self._log("     for your GPU.", tag="system")
