"""
Custom Nodes Tab for ComfyUI Module Installer
"""
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import get_active_comfyui_dir

from core.custom_node_manager import CustomNodeManager
from data.custom_nodes_registry import (
    CUSTOM_NODES, get_nodes_by_category, get_all_categories
)
from ui.widgets import (
    ProgressFrame, LogFrame, CheckboxTreeview,
    ButtonBar, LabeledCombobox
)

# Category descriptions for new users
CATEGORY_TIPS = {
    "all": "Custom nodes add new features to ComfyUI. 'Essential' nodes are strongly recommended for all users.",
    "essential": "Must-have nodes. ComfyUI Manager lets you install/update nodes directly from the ComfyUI web interface.",
    "recommended": "High-utility nodes that most users will benefit from. Includes workflow organization, face fixing, and batch tools.",
    "popular": "Widely used community nodes for advanced workflows, animations, and image processing.",
    "video": "Nodes for video generation workflows (loading, exporting, frame interpolation).",
    "api": "Debugging, metadata, and integration tools for workflow development.",
    "image": "Advanced image processing nodes (segmentation, inpainting, masking).",
}


class NodesTab(ttk.Frame):
    """Custom nodes management tab."""

    def __init__(self, parent, main_window):
        super().__init__(parent, padding=10)
        self.main_window = main_window
        active = get_active_comfyui_dir()
        self.node_manager = CustomNodeManager(comfyui_dir=active)

        self._setup_ui()
        # Defer node scanning so the window appears immediately
        self.after(1, self._populate_nodes)

    def set_comfyui_dir(self, path: Path):
        """Switch to a different ComfyUI directory and refresh."""
        self.node_manager = CustomNodeManager(comfyui_dir=path)
        self._populate_nodes()

    def _setup_ui(self):
        # Top controls
        controls_frame = ttk.Frame(self)
        controls_frame.pack(fill=tk.X, pady=(0, 5))

        # Category filter
        categories = ["all"] + get_all_categories()
        self.category_combo = LabeledCombobox(
            controls_frame, "Category:", categories, "all"
        )
        self.category_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.category_combo.combo.bind("<<ComboboxSelected>>", self._on_category_change)

        # Quick select buttons
        ttk.Button(
            controls_frame, text="Essential Only",
            command=self._select_essential
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            controls_frame, text="Recommended",
            command=self._select_recommended
        ).pack(side=tk.LEFT, padx=5)

        # Refresh
        ttk.Button(
            controls_frame, text="Refresh",
            command=self._refresh_nodes
        ).pack(side=tk.RIGHT)

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

        # Left: Registry nodes
        left_frame = ttk.LabelFrame(paned, text="Available Custom Nodes", padding=5)
        paned.add(left_frame, weight=1)

        self.nodes_tree = CheckboxTreeview(
            left_frame,
            columns=["name", "category", "description", "status"]
        )
        self.nodes_tree.pack(fill=tk.BOTH, expand=True)

        # Configure columns
        self.nodes_tree.tree.column("name", width=150)
        self.nodes_tree.tree.column("category", width=80)
        self.nodes_tree.tree.column("description", width=250)
        self.nodes_tree.tree.column("status", width=80)

        # Left buttons
        left_buttons = ButtonBar(left_frame)
        left_buttons.pack(fill=tk.X, pady=(5, 0))

        left_buttons.add_button("select_all", "Select All", self._select_all)
        left_buttons.add_button("select_none", "Select None", self._select_none)

        # Right: Installed nodes
        right_frame = ttk.LabelFrame(paned, text="Installed Nodes", padding=5)
        paned.add(right_frame, weight=1)

        self.installed_tree = CheckboxTreeview(
            right_frame,
            columns=["name", "path", "has_req"]
        )
        self.installed_tree.pack(fill=tk.BOTH, expand=True)

        self.installed_tree.tree.column("name", width=150)
        self.installed_tree.tree.column("path", width=200)
        self.installed_tree.tree.column("has_req", width=80)

        self.installed_tree.tree.heading("has_req", text="Has Reqs")

        # Right buttons
        right_buttons = ButtonBar(right_frame)
        right_buttons.pack(fill=tk.X, pady=(5, 0))

        right_buttons.add_button("update_all", "Update All", self._update_all_nodes)
        right_buttons.add_button("remove", "Remove Selected", self._remove_selected)

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
            "install", "Install Selected",
            self._install_selected, width=20
        )
        action_buttons.add_button(
            "update_selected", "Update Selected",
            self._update_selected, width=20
        )

    def _populate_nodes(self):
        """Populate nodes tree from registry (heavy work in background)."""
        self.nodes_tree.clear()
        self.installed_tree.clear()

        category_filter = self.category_combo.get()

        def do_gather():
            # Background thread: gather data (git subprocesses for installed nodes)
            registry_data = []
            for node_id, info in CUSTOM_NODES.items():
                if category_filter != "all" and info.get("category") != category_filter:
                    continue
                status = self.node_manager.get_node_status(info)
                desc = info.get("description", "")
                if len(desc) > 50:
                    desc = desc[:47] + "..."
                registry_data.append((node_id, info, status, desc))
            installed = self.node_manager.list_installed_nodes()
            return registry_data, installed

        def on_complete(result):
            if not self.winfo_exists():
                return
            registry_data, installed = result
            self.nodes_tree.clear()
            self.installed_tree.clear()
            for node_id, info, status, desc in registry_data:
                self.nodes_tree.insert_item(
                    values=(
                        info.get("name", node_id),
                        info.get("category", ""),
                        desc,
                        status
                    ),
                    item_id=node_id,
                    checked=info.get("required", False)
                )
            for node in installed:
                self.installed_tree.insert_item(
                    values=(
                        node.get("name", ""),
                        node.get("path", ""),
                        "Yes" if node.get("has_requirements") else "No"
                    ),
                    item_id=node.get("name", "")
                )

        self.main_window.run_async(do_gather, on_complete)

    def _on_category_change(self, event=None):
        """Handle category filter change."""
        category = self.category_combo.get()
        tip = CATEGORY_TIPS.get(category, "")
        self.category_tip.config(text=tip)
        self._populate_nodes()

    def _refresh_nodes(self):
        """Refresh node lists."""
        self._populate_nodes()
        self.main_window.set_status("Nodes refreshed")

    def _select_all(self):
        """Select all nodes."""
        self.nodes_tree.select_all()

    def _select_none(self):
        """Deselect all nodes."""
        self.nodes_tree.select_none()

    def _select_essential(self):
        """Select only essential nodes."""
        self.nodes_tree.select_none()
        for node_id, info in CUSTOM_NODES.items():
            if info.get("category") == "essential" or info.get("required"):
                if node_id in [self.nodes_tree.tree.item(i)["values"] for i in self.nodes_tree.tree.get_children()]:
                    # Find and check this item
                    for item in self.nodes_tree.tree.get_children():
                        if self.nodes_tree.tree.item(item)["values"][1] == info.get("name"):
                            self.nodes_tree.toggle_item(item)
                            break

    def _select_recommended(self):
        """Select essential and recommended nodes."""
        self.nodes_tree.select_none()
        for node_id, info in CUSTOM_NODES.items():
            if info.get("category") in ["essential", "recommended"] or info.get("required"):
                # Find item by node_id
                for item in self.nodes_tree.tree.get_children():
                    if item == node_id:
                        if item not in self.nodes_tree.checked_items:
                            self.nodes_tree.toggle_item(item)
                        break

    def _install_selected(self):
        """Install selected nodes."""
        selected = self.nodes_tree.get_checked_items()

        if not selected:
            messagebox.showwarning("Install", "Select nodes to install by clicking the checkbox column.")
            return

        nodes_to_install = []
        for node_id in selected:
            if node_id in CUSTOM_NODES:
                nodes_to_install.append({**CUSTOM_NODES[node_id], "id": node_id})

        if not messagebox.askyesno(
            "Confirm Install",
            f"Install {len(nodes_to_install)} custom nodes?\n\n"
            "Each node will be cloned from GitHub and its\n"
            "requirements installed automatically."
        ):
            return

        self._start_install(nodes_to_install)

    def _start_install(self, nodes: list):
        """Start installing nodes."""
        total = len(nodes)
        self.main_window.set_status(f"Installing {total} custom nodes...")
        self.main_window.log(f"Installing {total} custom node(s)...", tag="nodes")

        def progress_callback(current, total, message):
            if self.winfo_exists():
                self.after(0, lambda: self.progress.update_progress(current, total, message))

        def do_install():
            return self.node_manager.install_multiple(nodes, progress_callback)

        def on_complete(results):
            success_count = sum(1 for v in results.values() if v)
            fail_count = len(results) - success_count

            if fail_count == 0:
                self.main_window.set_status(f"Installed {success_count} nodes successfully")
                self.main_window.log(f"Installed {success_count} node(s) successfully.", tag="nodes")
            else:
                self.main_window.set_status(f"Installed {success_count}, failed {fail_count}")
                self.main_window.log(f"Nodes: {success_count} installed, {fail_count} failed.", tag="nodes")

            self._refresh_nodes()

        self.main_window.run_async(do_install, on_complete)

    def _update_selected(self):
        """Update selected installed nodes."""
        selected = self.installed_tree.get_checked_items()

        if not selected:
            messagebox.showwarning("Update", "Select installed nodes to update by clicking the checkbox column.")
            return

        self.main_window.set_status(f"Updating {len(selected)} nodes...")
        self.main_window.log(f"Updating {len(selected)} selected node(s)...", tag="nodes")

        def progress_callback(current, total, message):
            if self.winfo_exists():
                self.after(0, lambda: self.progress.update_progress(current, total, message))

        def do_update():
            results = {}
            for i, node_name in enumerate(selected):
                if self.winfo_exists():
                    self.after(0, lambda n=node_name: self.progress.update_progress(
                        i, len(selected), f"Updating {n}..."
                    ))
                results[node_name] = self.node_manager.update_node(node_name)
            return results

        def on_complete(results):
            success_count = sum(1 for v in results.values() if v)
            self.main_window.set_status(f"Updated {success_count} nodes")
            self.main_window.log(f"Updated {success_count} node(s).", tag="nodes")
            self._refresh_nodes()

        self.main_window.run_async(do_update, on_complete)

    def _update_all_nodes(self):
        """Update all installed nodes."""
        installed = self.node_manager.list_installed_nodes()

        if not installed:
            messagebox.showinfo("Info", "No custom nodes installed yet.")
            return

        if not messagebox.askyesno(
            "Update All",
            f"Update all {len(installed)} installed nodes?\n\n"
            "This will pull the latest version of each node from GitHub."
        ):
            return

        self.main_window.set_status("Updating all nodes...")
        self.main_window.log(f"Updating all {len(installed)} installed node(s)...", tag="nodes")

        def progress_callback(current, total, message):
            if self.winfo_exists():
                self.after(0, lambda: self.progress.update_progress(current, total, message))

        def do_update():
            return self.node_manager.update_all_nodes(progress_callback)

        def on_complete(results):
            success_count = sum(1 for v in results.values() if v)
            self.main_window.set_status(f"Updated {success_count} nodes")
            self.main_window.log(f"Updated {success_count} node(s).", tag="nodes")
            self._refresh_nodes()

        self.main_window.run_async(do_update, on_complete)

    def _remove_selected(self):
        """Remove selected installed nodes."""
        selected = self.installed_tree.get_checked_items()

        if not selected:
            messagebox.showwarning("Remove", "Select installed nodes to remove by clicking the checkbox column.")
            return

        if not messagebox.askyesno(
            "Confirm Remove",
            f"Remove {len(selected)} selected nodes?\n\n"
            "This deletes the node folders from custom_nodes/.\n"
            "You can reinstall them later from this tab."
        ):
            return

        self.main_window.set_status(f"Removing {len(selected)} nodes...")
        self.main_window.log(f"Removing {len(selected)} node(s)...", tag="nodes")

        def do_remove():
            results = {}
            for node_name in selected:
                results[node_name] = self.node_manager.remove_node(node_name)
            return results

        def on_complete(results):
            success_count = sum(1 for v in results.values() if v)
            self.main_window.set_status(f"Removed {success_count} nodes")
            self.main_window.log(f"Removed {success_count} node(s).", tag="nodes")
            self._refresh_nodes()

        self.main_window.run_async(do_remove, on_complete)
