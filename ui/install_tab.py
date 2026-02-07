"""
Installation Tab for ComfyUI Module Installer
"""
import tkinter as tk
from tkinter import ttk
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    DEFAULT_HOST, DEFAULT_PORT, VRAM_MODES,
    VRAM_DESCRIPTIONS, EXTRA_FLAGS
)

from core.comfy_installer import ComfyInstaller
from core.venv_manager import VenvManager
from core.gpu_manager import GPUManager
from core.instance_manager import InstanceManager, InstanceConfig
from ui.widgets import (
    ProgressFrame, LogFrame, StatusIndicator,
    ButtonBar, LabeledEntry, LabeledCombobox, ToolTip
)


class InstallTab(ttk.Frame):
    """Installation and server control tab."""

    def __init__(self, parent, main_window):
        super().__init__(parent, padding=10)
        self.main_window = main_window

        # Initialize managers
        self.venv_manager = VenvManager()
        self.installer = ComfyInstaller(venv_manager=self.venv_manager)
        self.instance_manager = InstanceManager(log_callback=self._shared_log)

        # Detect GPUs
        self.gpu_list = GPUManager.get_gpu_display_list()
        self._gpu_map = {label: value for label, value in self.gpu_list}

        self._setup_ui()
        self._refresh_status()
        self._show_first_launch_hint()

    def _setup_ui(self):
        # Split into left and right panels
        left_panel = ttk.Frame(self)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        right_panel = ttk.Frame(self)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        # === LEFT PANEL: Installation ===
        install_frame = ttk.LabelFrame(left_panel, text="Installation", padding=10)
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
            wraplength=350, foreground="#555555",
            font=("Segoe UI", 8)
        )
        info_label.pack(fill=tk.X, pady=(0, 5))

        # Install buttons
        install_buttons = ButtonBar(install_frame)
        install_buttons.pack(fill=tk.X, pady=5)

        install_buttons.add_button(
            "full_install", "Full Install",
            self._full_install, width=15
        )
        install_buttons.add_button(
            "update", "Update ComfyUI",
            self._update_comfyui, width=15
        )
        install_buttons.add_button(
            "sage", "Install SageAttention",
            self._install_sage_attention, width=20
        )
        install_buttons.add_button(
            "purge", "Purge ComfyUI",
            self._purge_comfyui, width=15
        )
        install_buttons.add_button(
            "refresh", "Refresh",
            self._refresh_status, width=10
        )

        # Progress
        self.install_progress = ProgressFrame(install_frame)
        self.install_progress.pack(fill=tk.X, pady=5)

        # === LEFT PANEL: Server Instances ===
        server_frame = ttk.LabelFrame(left_panel, text="Server Instances", padding=10)
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
            wraplength=450, foreground="#555555",
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

        # === RIGHT PANEL: Log ===
        log_frame = ttk.LabelFrame(right_panel, text="Log", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log = LogFrame(log_frame, height=20)
        self.log.pack(fill=tk.BOTH, expand=True)

        # Log controls
        log_buttons = ttk.Frame(log_frame)
        log_buttons.pack(fill=tk.X, pady=(5, 0))

        ttk.Button(log_buttons, text="Clear Log", command=self.log.clear).pack(side=tk.RIGHT)

    # ---- Shared log callback (thread-safe) ----

    def _shared_log(self, line: str):
        """Thread-safe log callback used by InstanceManager."""
        if self.winfo_exists():
            self.after(0, lambda: self.log.log(line))

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
            self.log.log("Error: Invalid port number.")
            return

        if port < 1024 or port > 65535:
            self.log.log("Error: Port must be between 1024 and 65535.")
            return

        host = self.host_entry.get().strip() or DEFAULT_HOST
        vram_mode = self.vram_combo.get()
        extra_args = self._get_extra_args()

        # Auto-set CPU VRAM mode when CPU device is selected
        if gpu_device == "cpu" and vram_mode != "cpu":
            vram_mode = "cpu"
            self.log.log("Note: Forced VRAM mode to 'cpu' for CPU device.")

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
            self.log.log(f"Error: {e}")
            return

        # Add row to table
        url = f"http://{host}:{port}"
        self.instance_tree.insert(
            "", tk.END, iid=instance_id,
            values=(gpu_label, port, vram_mode, "Stopped", url)
        )

        self.log.log(f"Added instance {instance_id} ({gpu_label} on port {port})")

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
            self.log.log("No instance selected.")
            return

        if not self.installer.is_installed:
            self.log.log("ComfyUI not installed! Run Full Install first.")
            return

        state = self.instance_manager.get_instance(instance_id)
        if state and state.server.is_running:
            self.log.log(f"Instance {instance_id} is already running.")
            return

        self.log.log(f"Starting instance {instance_id}...")
        self._update_tree_status(instance_id, "Starting")

        def progress_callback(current, total, message):
            if self.winfo_exists():
                self.after(0, lambda: self.log.log(message))

        def do_start():
            return self.instance_manager.start_instance(instance_id, progress_callback)

        def on_complete(success):
            if success:
                self._update_tree_status(instance_id, "Running")
                self.log.log(f"Instance {instance_id} is running.")
            else:
                self._update_tree_status(instance_id, "Error")
                self.log.log(f"Instance {instance_id} failed to start.")
            self._update_status_bar()

        self.main_window.run_async(do_start, on_complete)

    def _stop_selected(self):
        """Stop the selected instance."""
        instance_id = self._get_selected_id()
        if not instance_id:
            self.log.log("No instance selected.")
            return

        state = self.instance_manager.get_instance(instance_id)
        if state and not state.server.is_running:
            self.log.log(f"Instance {instance_id} is not running.")
            return

        self.log.log(f"Stopping instance {instance_id}...")

        def progress_callback(current, total, message):
            if self.winfo_exists():
                self.after(0, lambda: self.log.log(message))

        def do_stop():
            return self.instance_manager.stop_instance(instance_id, progress_callback)

        def on_complete(success):
            if success:
                self._update_tree_status(instance_id, "Stopped")
                self.log.log(f"Instance {instance_id} stopped.")
            else:
                self.log.log(f"Failed to stop instance {instance_id}.")
            self._update_status_bar()

        self.main_window.run_async(do_stop, on_complete)

    def _start_all(self):
        """Start all stopped instances."""
        if not self.installer.is_installed:
            self.log.log("ComfyUI not installed! Run Full Install first.")
            return

        instances = self.instance_manager.get_all_instances()
        to_start = [s for s in instances if not s.server.is_running]

        if not to_start:
            self.log.log("No stopped instances to start.")
            return

        self.log.log(f"Starting {len(to_start)} instance(s)...")

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
            self.log.log(f"Started {running}/{len(results)} instance(s).")
            self._update_status_bar()

        self.main_window.run_async(do_start_all, on_complete)

    def _stop_all(self):
        """Stop all running instances."""
        instances = self.instance_manager.get_all_instances()
        to_stop = [s for s in instances if s.server.is_running]

        if not to_stop:
            self.log.log("No running instances to stop.")
            return

        self.log.log(f"Stopping {len(to_stop)} instance(s)...")

        def do_stop_all():
            return self.instance_manager.stop_all()

        def on_complete(success):
            for state in self.instance_manager.get_all_instances():
                self._update_tree_status(state.instance_id, "Stopped")
            self.log.log("All instances stopped.")
            self._update_status_bar()

        self.main_window.run_async(do_stop_all, on_complete)

    def _remove_selected(self):
        """Remove the selected instance (stops it first if running)."""
        instance_id = self._get_selected_id()
        if not instance_id:
            self.log.log("No instance selected.")
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
                self.log.log(f"Removed instance {instance_id}.")
            else:
                self.log.log(f"Failed to remove instance {instance_id}.")
            self._update_status_bar()

        self.main_window.run_async(do_remove, on_complete)

    def _open_browser(self):
        """Open the selected instance in a browser."""
        instance_id = self._get_selected_id()
        if not instance_id:
            self.log.log("No instance selected.")
            return

        state = self.instance_manager.get_instance(instance_id)
        if not state:
            return

        import webbrowser
        url = f"http://{state.config.host}:{state.config.port}"
        self.log.log(f"Opening {url} in browser...")
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

        self.log.log(f"Status: Python={'ready' if status['venv_created'] else 'not set up'}, "
                    f"ComfyUI={'installed' if status['comfyui_installed'] else 'not installed'}")

    # ---- Installation operations (unchanged) ----

    def _full_install(self):
        """Perform full installation."""
        self.log.log("Starting full installation...")
        self.log.log("  Step 1: Set up Python environment")
        self.log.log("  Step 2: Install PyTorch with CUDA")
        self.log.log("  Step 3: Clone ComfyUI from GitHub")
        self.log.log("  Step 4: Install ComfyUI dependencies")
        self.log.log("  Step 5: Create model directories")
        self.main_window.set_status("Installing...")

        def progress_callback(current, total, message):
            if self.winfo_exists():
                self.after(0, lambda: self._update_progress(current, total, message))

        def do_install():
            return self.installer.full_install(progress_callback)

        def on_complete(success):
            if success:
                self.log.log("Installation completed successfully!")
                self.log.log("Next steps: Go to the Models tab to download models,")
                self.log.log("then add an instance, select it, and click 'Start'.")
                self.main_window.set_status("Installation complete")
            else:
                self.log.log("Installation failed! Check the log for details.")
                self.main_window.set_status("Installation failed")
            self._refresh_status()

        self.main_window.run_async(do_install, on_complete)

    def _install_sage_attention(self):
        """Install Triton + SageAttention."""
        if not self.venv_manager.is_created:
            self.log.log("Python environment not set up. Run Full Install first.")
            return

        if self.venv_manager.is_package_installed("sageattention"):
            from tkinter import messagebox
            if not messagebox.askyesno(
                "Already Installed",
                "SageAttention is already installed.\n\nReinstall?"
            ):
                return

        self.log.log("Installing Triton + SageAttention...")
        self.log.log("  This enables 2-3x faster attention operations,")
        self.log.log("  especially useful for video generation workflows.")
        self.main_window.set_status("Installing SageAttention...")

        def progress_callback(current, total, message):
            if self.winfo_exists():
                self.after(0, lambda: self._update_progress(current, total, message))

        def do_install():
            return self.venv_manager.install_sage_attention(progress_callback)

        def on_complete(success):
            if success:
                self.log.log("SageAttention installed! Enable the checkbox below to use it.")
                self.main_window.set_status("SageAttention installed")
            else:
                self.log.log("SageAttention installation failed. Check the log for details.")
                self.main_window.set_status("SageAttention install failed")
            self._refresh_status()

        self.main_window.run_async(do_install, on_complete)

    def _update_comfyui(self):
        """Update ComfyUI."""
        if not self.installer.is_installed:
            self.log.log("ComfyUI not installed. Use Full Install first.")
            return

        self.log.log("Updating ComfyUI (pulling latest from GitHub)...")
        self.main_window.set_status("Updating...")

        def progress_callback(current, total, message):
            if self.winfo_exists():
                self.after(0, lambda: self._update_progress(current, total, message))

        def do_update():
            return self.installer.update_comfyui(progress_callback)

        def on_complete(success):
            if success:
                self.log.log("Update completed!")
                self.main_window.set_status("Update complete")
            else:
                self.log.log("Update failed!")
                self.main_window.set_status("Update failed")

        self.main_window.run_async(do_update, on_complete)

    def _purge_comfyui(self):
        """Purge ComfyUI installation (keeps Python env and models)."""
        from tkinter import messagebox

        if not self.installer.is_installed:
            self.log.log("ComfyUI not installed. Nothing to purge.")
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

        self.log.log("Purging ComfyUI installation...")
        self.main_window.set_status("Purging...")

        def progress_callback(current, total, message):
            if self.winfo_exists():
                self.after(0, lambda: self._update_progress(current, total, message))

        def do_purge():
            return self.installer.purge_comfyui(progress_callback)

        def on_complete(success):
            if success:
                self.log.log("Purge completed! Use 'Full Install' for fresh installation.")
                self.main_window.set_status("Purge complete")
            else:
                self.log.log("Purge failed!")
                self.main_window.set_status("Purge failed")
            self._refresh_status()

        self.main_window.run_async(do_purge, on_complete)

    def _update_progress(self, current, total, message):
        """Update progress from main thread."""
        self.install_progress.update_progress(current, total, message)
        self.log.log(message)

    def _show_first_launch_hint(self):
        """Show helpful guidance on first launch when nothing is installed."""
        status = self.installer.check_installation()
        if status["comfyui_installed"]:
            return  # Not a first launch

        gpu_count = len(self.gpu_list) - 1  # Subtract CPU entry
        gpu_msg = f"Detected {gpu_count} GPU(s)." if gpu_count > 0 else "No NVIDIA GPU detected (CPU mode available)."

        self.log.log("=" * 50)
        self.log.log("  Welcome to ComfyUI Module!")
        self.log.log("=" * 50)
        self.log.log("")
        self.log.log(f"  {gpu_msg}")
        self.log.log("")
        if not status["venv_created"]:
            self.log.log("Getting started:")
            self.log.log("  1. Click 'Full Install' to set up everything.")
            self.log.log("     This will download ComfyUI, PyTorch, and")
            self.log.log("     all dependencies (~5-15 min).")
            self.log.log("")
            self.log.log("  2. After install, go to the Models tab to")
            self.log.log("     download AI models (required to generate).")
            self.log.log("")
            self.log.log("  3. Then add a server instance (pick a GPU),")
            self.log.log("     select it, click 'Start', and 'Open UI'")
            self.log.log("     to launch ComfyUI in your browser.")
        else:
            self.log.log("Python environment is ready.")
            self.log.log("Click 'Full Install' to download and set up ComfyUI.")
        self.log.log("")
        self.log.log("Tip: Check Help > Getting Started for a full guide.")
        self.log.log("     Check Help > VRAM Guide to pick the right models")
        self.log.log("     for your GPU.")
