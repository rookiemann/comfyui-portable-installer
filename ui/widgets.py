"""
Reusable Tkinter Widgets for ComfyUI Module
"""
import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable


class ProgressFrame(ttk.Frame):
    """A frame with a progress bar and status label."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._setup_ui()

    def _setup_ui(self):
        self.status_label = ttk.Label(self, text="Ready")
        self.status_label.pack(fill=tk.X, padx=5, pady=(5, 2))

        self.progress_bar = ttk.Progressbar(
            self, orient=tk.HORIZONTAL, mode="determinate"
        )
        self.progress_bar.pack(fill=tk.X, padx=5, pady=(2, 5))

    def update_progress(self, current: int, total: int, message: str = ""):
        """Update progress bar and status."""
        if not self.winfo_exists():
            return

        if total > 0:
            self.progress_bar["value"] = (current / total) * 100
        else:
            self.progress_bar["value"] = 0

        if message:
            self.status_label.config(text=message)

        self.update_idletasks()

    def reset(self):
        """Reset progress to initial state."""
        self.progress_bar["value"] = 0
        self.status_label.config(text="Ready")


class LogFrame(ttk.Frame):
    """A frame with a scrollable log text area."""

    def __init__(self, parent, height: int = 10, **kwargs):
        super().__init__(parent, **kwargs)
        self._setup_ui(height)

    def _setup_ui(self, height: int):
        # Create text widget with scrollbar
        self.text = tk.Text(
            self, height=height, wrap=tk.WORD,
            state=tk.DISABLED, font=("Consolas", 9)
        )
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.text.yview)
        self.text.configure(yscrollcommand=scrollbar.set)

        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def log(self, message: str, newline: bool = True):
        """Add a message to the log."""
        if not self.winfo_exists():
            return

        self.text.configure(state=tk.NORMAL)
        if newline and not message.endswith("\n"):
            message += "\n"
        self.text.insert(tk.END, message)
        self.text.see(tk.END)
        self.text.configure(state=tk.DISABLED)
        self.update_idletasks()

    def clear(self):
        """Clear the log."""
        self.text.configure(state=tk.NORMAL)
        self.text.delete("1.0", tk.END)
        self.text.configure(state=tk.DISABLED)


class StatusIndicator(ttk.Frame):
    """A status indicator with label and colored indicator."""

    def __init__(self, parent, label: str, **kwargs):
        super().__init__(parent, **kwargs)
        self._setup_ui(label)

    def _setup_ui(self, label: str):
        self.indicator = tk.Canvas(self, width=16, height=16, highlightthickness=0)
        self.indicator.pack(side=tk.LEFT, padx=(0, 5))

        self.label = ttk.Label(self, text=label)
        self.label.pack(side=tk.LEFT)

        self._draw_indicator("gray")

    def _draw_indicator(self, color: str):
        self.indicator.delete("all")
        self.indicator.create_oval(2, 2, 14, 14, fill=color, outline="")

    def set_status(self, status: str):
        """Set status: 'ok', 'error', 'warning', 'pending'."""
        colors = {
            "ok": "#4CAF50",      # Green
            "error": "#F44336",   # Red
            "warning": "#FF9800", # Orange
            "pending": "#9E9E9E", # Gray
            "running": "#2196F3", # Blue
        }
        self._draw_indicator(colors.get(status, "gray"))


class CheckboxTreeview(ttk.Frame):
    """A treeview with checkboxes for selection."""

    def __init__(
        self,
        parent,
        columns: list,
        show_checkboxes: bool = True,
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        self.show_checkboxes = show_checkboxes
        self.checked_items = set()
        self._setup_ui(columns)

    def _setup_ui(self, columns):
        # Create treeview
        display_columns = columns if not self.show_checkboxes else ["select"] + columns

        self.tree = ttk.Treeview(
            self, columns=display_columns, show="headings", selectmode="extended"
        )

        # Configure columns
        if self.show_checkboxes:
            self.tree.heading("select", text="")
            self.tree.column("select", width=30, stretch=False, anchor="center")

        for col in columns:
            self.tree.heading(col, text=col.replace("_", " ").title())
            self.tree.column(col, width=100)

        # Scrollbars
        vsb = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        hsb = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # Grid layout
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Bind click for checkbox toggle
        if self.show_checkboxes:
            self.tree.bind("<Button-1>", self._on_click)

    def _on_click(self, event):
        """Handle click for checkbox toggle."""
        region = self.tree.identify_region(event.x, event.y)
        if region == "cell":
            column = self.tree.identify_column(event.x)
            if column == "#1":  # First column (select)
                item = self.tree.identify_row(event.y)
                if item:
                    self.toggle_item(item)

    def toggle_item(self, item: str):
        """Toggle checkbox state for an item."""
        if item in self.checked_items:
            self.checked_items.remove(item)
            self.tree.set(item, "select", "")
        else:
            self.checked_items.add(item)
            self.tree.set(item, "select", "✓")

    def insert_item(self, values: tuple, item_id: Optional[str] = None, checked: bool = False):
        """Insert an item into the treeview."""
        if self.show_checkboxes:
            check_mark = "✓" if checked else ""
            values = (check_mark,) + values

        iid = self.tree.insert("", tk.END, values=values, iid=item_id)

        if checked:
            self.checked_items.add(iid)

        return iid

    def get_checked_items(self) -> list:
        """Get list of checked item IDs."""
        return list(self.checked_items)

    def get_all_items(self) -> list:
        """Get all item IDs."""
        return self.tree.get_children()

    def clear(self):
        """Clear all items."""
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.checked_items.clear()

    def select_all(self):
        """Select all items."""
        for item in self.tree.get_children():
            if item not in self.checked_items:
                self.toggle_item(item)

    def select_none(self):
        """Deselect all items."""
        for item in list(self.checked_items):
            self.toggle_item(item)


class ButtonBar(ttk.Frame):
    """A horizontal bar of buttons."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.buttons = {}

    def add_button(
        self,
        name: str,
        text: str,
        command: Callable,
        **kwargs
    ) -> ttk.Button:
        """Add a button to the bar."""
        btn = ttk.Button(self, text=text, command=command, **kwargs)
        btn.pack(side=tk.LEFT, padx=5, pady=5)
        self.buttons[name] = btn
        return btn

    def enable(self, name: str):
        """Enable a button."""
        if name in self.buttons:
            self.buttons[name].config(state=tk.NORMAL)

    def disable(self, name: str):
        """Disable a button."""
        if name in self.buttons:
            self.buttons[name].config(state=tk.DISABLED)

    def set_text(self, name: str, text: str):
        """Set button text."""
        if name in self.buttons:
            self.buttons[name].config(text=text)


class LabeledEntry(ttk.Frame):
    """An entry field with a label."""

    def __init__(self, parent, label: str, default: str = "", **kwargs):
        super().__init__(parent, **kwargs)
        self._setup_ui(label, default)

    def _setup_ui(self, label: str, default: str):
        ttk.Label(self, text=label).pack(side=tk.LEFT, padx=(0, 5))

        self.var = tk.StringVar(value=default)
        self.entry = ttk.Entry(self, textvariable=self.var, width=30)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def get(self) -> str:
        """Get the entry value."""
        return self.var.get()

    def set(self, value: str):
        """Set the entry value."""
        self.var.set(value)


class ToolTip:
    """Hover tooltip for any tkinter widget."""

    def __init__(self, widget, text: str, delay: int = 400):
        self.widget = widget
        self.text = text
        self.delay = delay
        self._tip_window = None
        self._after_id = None
        widget.bind("<Enter>", self._on_enter, add="+")
        widget.bind("<Leave>", self._on_leave, add="+")

    def _on_enter(self, event=None):
        self._after_id = self.widget.after(self.delay, self._show)

    def _on_leave(self, event=None):
        if self._after_id:
            self.widget.after_cancel(self._after_id)
            self._after_id = None
        self._hide()

    def _show(self):
        if self._tip_window:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self._tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tw, text=self.text, justify=tk.LEFT,
            background="#ffffe1", relief=tk.SOLID, borderwidth=1,
            font=("Segoe UI", 8), wraplength=300, padx=6, pady=4,
        )
        label.pack()

    def _hide(self):
        if self._tip_window:
            self._tip_window.destroy()
            self._tip_window = None

    def update_text(self, text: str):
        """Change the tooltip text."""
        self.text = text


class LabeledCombobox(ttk.Frame):
    """A combobox with a label."""

    def __init__(
        self,
        parent,
        label: str,
        values: list,
        default: Optional[str] = None,
        width: int = 15,
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        self._setup_ui(label, values, default, width)

    def _setup_ui(self, label: str, values: list, default: Optional[str], width: int):
        ttk.Label(self, text=label).pack(side=tk.LEFT, padx=(0, 5))

        self.var = tk.StringVar(value=default or (values[0] if values else ""))
        self.combo = ttk.Combobox(
            self, textvariable=self.var, values=values, state="readonly", width=width
        )
        self.combo.pack(side=tk.LEFT)

    def get(self) -> str:
        """Get the selected value."""
        return self.var.get()

    def set(self, value: str):
        """Set the selected value."""
        self.var.set(value)
