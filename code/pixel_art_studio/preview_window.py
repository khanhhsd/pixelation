"""Full-size image preview window with fit and zoom controls."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk


class ImagePreviewWindow:
    """Display an image in a scrollable window with nearest-neighbor zoom."""

    def __init__(self, parent: tk.Tk, title: str, image: Image.Image) -> None:
        self.window = tk.Toplevel(parent)
        self.window.title(f"Preview · {title}")
        self.window.geometry("1100x800")
        self.window.minsize(500, 350)
        self.image = image.copy()
        self.zoom = 1.0
        self.fit_to_window = True
        self.photo: ImageTk.PhotoImage | None = None

        toolbar = ttk.Frame(self.window, padding=8)
        toolbar.pack(fill="x")
        ttk.Button(toolbar, text="Fit", command=self.fit).pack(side="left")
        ttk.Button(toolbar, text="−", width=4, command=lambda: self._change_zoom(1 / 1.25)).pack(
            side="left", padx=(8, 2)
        )
        ttk.Button(toolbar, text="+", width=4, command=lambda: self._change_zoom(1.25)).pack(
            side="left", padx=2
        )
        ttk.Button(toolbar, text="100%", command=lambda: self.set_zoom(1.0)).pack(
            side="left", padx=8
        )
        self.zoom_label = ttk.Label(toolbar)
        self.zoom_label.pack(side="left", padx=8)

        body = ttk.Frame(self.window)
        body.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(body, background="#202124", highlightthickness=0)
        x_scroll = ttk.Scrollbar(body, orient="horizontal", command=self.canvas.xview)
        y_scroll = ttk.Scrollbar(body, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=x_scroll.set, yscrollcommand=y_scroll.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        body.rowconfigure(0, weight=1)
        body.columnconfigure(0, weight=1)

        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>", lambda _event: self._change_zoom(1.25))
        self.canvas.bind("<Button-5>", lambda _event: self._change_zoom(1 / 1.25))
        self.canvas.bind("<Configure>", self._on_resize)
        self.window.after_idle(self.fit)

    def _render(self) -> None:
        width = max(1, round(self.image.width * self.zoom))
        height = max(1, round(self.image.height * self.zoom))
        rendered = self.image.resize((width, height), Image.Resampling.NEAREST)
        self.photo = ImageTk.PhotoImage(rendered, master=self.window)
        self.canvas.delete("preview")
        self.canvas.create_image(0, 0, image=self.photo, anchor="nw", tags="preview")
        self.canvas.configure(scrollregion=(0, 0, width, height))
        self.zoom_label.configure(text=f"{self.zoom:.0%}")

    def fit(self) -> None:
        self.fit_to_window = True
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        max_zoom = max(0.01, min(8.0, 12000 / max(self.image.size)))
        self.zoom = min(width / self.image.width, height / self.image.height, 1.0, max_zoom)
        self._render()
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)

    def set_zoom(self, zoom: float) -> None:
        max_zoom = max(0.01, min(8.0, 12000 / max(self.image.size)))
        self.fit_to_window = False
        self.zoom = min(max(zoom, 0.01), max_zoom)
        self._render()

    def _change_zoom(self, factor: float) -> None:
        self.set_zoom(self.zoom * factor)

    def _on_resize(self, _event: tk.Event) -> None:
        if self.fit_to_window:
            self.window.after_idle(self.fit)

    def _on_mousewheel(self, event: tk.Event) -> str:
        self._change_zoom(1.25 if event.delta > 0 else 1 / 1.25)
        return "break"
