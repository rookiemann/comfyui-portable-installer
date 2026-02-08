"""
Log Tab for ComfyUI Module Installer
Centralized log viewer with tag filtering, clear, and max-line control.
"""
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


# Known tags (displayed in the filter dropdown)
LOG_TAGS = ["all", "server", "install", "models", "nodes", "config", "system"]

# Tag colors for visual distinction
TAG_COLORS = {
    "server":  "#2266cc",
    "install": "#228833",
    "models":  "#886611",
    "nodes":   "#884488",
    "config":  "#666666",
    "system":  "#cc4422",
}


class LogTab(ttk.Frame):
    """Centralized log viewer tab."""

    DEFAULT_MAX_LINES = 5000

    def __init__(self, parent, main_window):
        super().__init__(parent, padding=10)
        self.main_window = main_window

        # Internal store: list of (tag, message) for filtering
        self._entries: list[tuple[str, str]] = []
        self._max_lines = self.DEFAULT_MAX_LINES
        self._active_tag = "all"

        self._setup_ui()

    def _setup_ui(self):
        # --- Top controls ---
        controls = ttk.Frame(self)
        controls.pack(fill=tk.X, pady=(0, 5))

        # Tag filter
        ttk.Label(controls, text="Filter:").pack(side=tk.LEFT, padx=(0, 4))
        self._tag_var = tk.StringVar(value="all")
        self._tag_combo = ttk.Combobox(
            controls, textvariable=self._tag_var,
            values=LOG_TAGS, state="readonly", width=10,
        )
        self._tag_combo.pack(side=tk.LEFT, padx=(0, 10))
        self._tag_combo.bind("<<ComboboxSelected>>", self._on_filter_change)

        # Max lines
        ttk.Label(controls, text="Max lines:").pack(side=tk.LEFT, padx=(0, 4))
        self._max_var = tk.StringVar(value=str(self._max_lines))
        max_entry = ttk.Entry(controls, textvariable=self._max_var, width=7)
        max_entry.pack(side=tk.LEFT, padx=(0, 4))
        max_entry.bind("<Return>", self._on_max_change)
        ttk.Button(controls, text="Set", command=self._on_max_change, width=4).pack(side=tk.LEFT, padx=(0, 10))

        # Clear
        ttk.Button(controls, text="Clear Log", command=self.clear).pack(side=tk.RIGHT)

        # Line count
        self._count_label = ttk.Label(controls, text="0 lines", font=("Segoe UI", 8), foreground="#888")
        self._count_label.pack(side=tk.RIGHT, padx=(0, 10))

        # --- Log text area ---
        text_frame = ttk.Frame(self)
        text_frame.pack(fill=tk.BOTH, expand=True)

        self.text = tk.Text(
            text_frame, wrap=tk.WORD, state=tk.DISABLED,
            font=("Consolas", 9), background="#1e1e1e", foreground="#d4d4d4",
            insertbackground="#d4d4d4", selectbackground="#264f78",
        )
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.text.yview)
        self.text.configure(yscrollcommand=scrollbar.set)

        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Configure tag colors
        for tag, color in TAG_COLORS.items():
            self.text.tag_configure(f"tag_{tag}", foreground=color)
        self.text.tag_configure("timestamp", foreground="#888888")

    # ---- Public API ----

    def log(self, message: str, tag: str = "system"):
        """Append a tagged message to the log."""
        if not self.winfo_exists():
            return

        tag = tag if tag in LOG_TAGS else "system"
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] [{tag}] {message}"

        self._entries.append((tag, entry))

        # Enforce max lines on internal store
        if len(self._entries) > self._max_lines:
            self._entries = self._entries[-self._max_lines:]

        # Only show if it passes the active filter
        if self._active_tag == "all" or tag == self._active_tag:
            self._append_line(entry, tag)
            self._trim_display()

        self._update_count()

    def clear(self):
        """Clear all log entries."""
        self._entries.clear()
        self.text.configure(state=tk.NORMAL)
        self.text.delete("1.0", tk.END)
        self.text.configure(state=tk.DISABLED)
        self._update_count()

    # ---- Internal ----

    def _append_line(self, line: str, tag: str):
        """Append a single line to the text widget with coloring."""
        self.text.configure(state=tk.NORMAL)
        if not line.endswith("\n"):
            line += "\n"

        start = self.text.index(tk.END + "-1c")
        self.text.insert(tk.END, line)
        end = self.text.index(tk.END + "-1c")

        # Color the tag portion
        tag_name = f"tag_{tag}"
        if tag_name in [self.text.tag_names()]:
            pass  # always configured above
        self.text.tag_add(tag_name, start, end)

        # Color timestamp portion
        ts_end = f"{start}+11c"  # "[HH:MM:SS] " = 11 chars
        self.text.tag_add("timestamp", start, ts_end)

        self.text.see(tk.END)
        self.text.configure(state=tk.DISABLED)

    def _trim_display(self):
        """Remove excess lines from the display if over max."""
        self.text.configure(state=tk.NORMAL)
        line_count = int(self.text.index("end-1c").split(".")[0])
        if line_count > self._max_lines:
            excess = line_count - self._max_lines
            self.text.delete("1.0", f"{excess + 1}.0")
        self.text.configure(state=tk.DISABLED)

    def _rebuild_display(self):
        """Re-render the text widget from _entries based on the active filter."""
        self.text.configure(state=tk.NORMAL)
        self.text.delete("1.0", tk.END)
        self.text.configure(state=tk.DISABLED)

        for tag, entry in self._entries:
            if self._active_tag == "all" or tag == self._active_tag:
                self._append_line(entry, tag)

        self._update_count()

    def _update_count(self):
        """Update the line-count label."""
        if self._active_tag == "all":
            total = len(self._entries)
        else:
            total = sum(1 for t, _ in self._entries if t == self._active_tag)
        self._count_label.config(text=f"{total} lines")

    def _on_filter_change(self, event=None):
        """Handle tag filter dropdown change."""
        self._active_tag = self._tag_var.get()
        self._rebuild_display()

    def _on_max_change(self, event=None):
        """Handle max-lines change."""
        try:
            val = int(self._max_var.get())
            if val < 100:
                val = 100
            if val > 100000:
                val = 100000
            self._max_lines = val
        except ValueError:
            self._max_var.set(str(self._max_lines))
            return

        # Trim if needed
        if len(self._entries) > self._max_lines:
            self._entries = self._entries[-self._max_lines:]
            self._rebuild_display()
