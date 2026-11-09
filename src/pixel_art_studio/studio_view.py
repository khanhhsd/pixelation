"""Tkinter widgets and preview-card rendering for Pixel Art Studio."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk
from typing import Callable

from PIL import Image, ImageTk

from pixel_art_studio.processing import METHODS


class StudioView:
    """Owns the main window layout and presents controller state."""

    def __init__(
        self,
        root: tk.Tk,
        on_mode_changed: Callable[[], None],
        on_pick_images: Callable[[], None],
        on_preview: Callable[[], None],
        on_start: Callable[[], None],
        on_settings_changed: Callable[..., None],
        on_method_toggle: Callable[[str], None],
        on_open_preview: Callable[[str], None],
    ) -> None:
        self.root = root
        self.mode = tk.StringVar(value="one")
        self.pixel_size = tk.IntVar(value=8)
        self.color_count = tk.IntVar(value=32)
        self.batch_method = tk.StringVar(value=METHODS[2].label)
        self.status = tk.StringVar(value="Choose a workflow to get started.")
        self.photo_images: list[ImageTk.PhotoImage] = []
        self.cards: dict[str, tk.Frame] = {}
        self.mode_buttons: list[ttk.Radiobutton] = []

        self._configure_style()
        self._build_ui(
            on_mode_changed,
            on_pick_images,
            on_preview,
            on_start,
            on_settings_changed,
            on_method_toggle,
            on_open_preview,
        )
        self.update_mode("one")

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Title.TLabel", font=("Segoe UI", 22, "bold"))
        style.configure("Subtitle.TLabel", font=("Segoe UI", 10))

    def _build_ui(
        self,
        on_mode_changed: Callable[[], None],
        on_pick_images: Callable[[], None],
        on_preview: Callable[[], None],
        on_start: Callable[[], None],
        on_settings_changed: Callable[..., None],
        on_method_toggle: Callable[[str], None],
        on_open_preview: Callable[[str], None],
    ) -> None:
        outer = ttk.Frame(self.root, padding=(22, 18))
        outer.pack(fill="both", expand=True)
        heading = ttk.Frame(outer)
        heading.pack(fill="x")
        ttk.Label(heading, text="Pixel Art Studio", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            heading,
            text="Preview eight styles for one image, or apply a single style to a batch.",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(3, 0))

        workflow = ttk.LabelFrame(outer, text="1  Choose workflow", padding=12)
        workflow.pack(fill="x", pady=(18, 10))
        for value, label in (
            ("one", "One image · preview and select styles"),
            ("many", "Multiple images · choose files"),
            ("all", "All images · choose a folder"),
        ):
            button = ttk.Radiobutton(
                workflow,
                text=label,
                value=value,
                variable=self.mode,
                command=on_mode_changed,
            )
            button.pack(side="left", padx=(0, 20))
            self.mode_buttons.append(button)

        controls = ttk.LabelFrame(outer, text="2  Select images and settings", padding=12)
        controls.pack(fill="x")
        self.pick_button = ttk.Button(controls, text="Choose image…", command=on_pick_images)
        self.pick_button.grid(row=0, column=0, sticky="w")
        self.selection_label = ttk.Label(controls, text="No images selected")
        self.selection_label.grid(row=0, column=1, sticky="w", padx=12)
        ttk.Label(controls, text="Pixel size").grid(row=1, column=0, sticky="w", pady=(12, 0))
        self.pixel_size_input = ttk.Spinbox(
            controls, from_=1, to=128, textvariable=self.pixel_size, width=8
        )
        self.pixel_size_input.grid(row=1, column=1, sticky="w", padx=12, pady=(12, 0))
        ttk.Label(controls, text="Palette colors").grid(
            row=1, column=2, sticky="w", pady=(12, 0)
        )
        self.color_count_input = ttk.Spinbox(
            controls, from_=2, to=256, textvariable=self.color_count, width=8
        )
        self.color_count_input.grid(row=1, column=3, sticky="w", padx=12, pady=(12, 0))
        self.pixel_size.trace_add("write", on_settings_changed)
        self.color_count.trace_add("write", on_settings_changed)

        self.batch_frame = ttk.Frame(controls)
        ttk.Label(self.batch_frame, text="Method for batch").pack(side="left")
        self.method_combo = ttk.Combobox(
            self.batch_frame,
            state="readonly",
            width=24,
            textvariable=self.batch_method,
            values=[method.label for method in METHODS],
        )
        self.method_combo.pack(side="left", padx=10)
        self.batch_frame.grid(row=2, column=0, columnspan=4, sticky="w", pady=(12, 0))

        preview_header = ttk.Frame(outer)
        preview_header.pack(fill="x", pady=(16, 8))
        self.preview_title = ttk.Label(
            preview_header, text="3  Preview and select styles", font=("Segoe UI", 13, "bold")
        )
        self.preview_title.pack(side="left")
        self.selection_count = ttk.Label(preview_header, text="")
        self.selection_count.pack(side="right")

        self.preview_container = ttk.Frame(outer)
        self.preview_container.pack(fill="both", expand=True)
        self.preview_button = ttk.Button(
            self.preview_container,
            text="Generate previews",
            command=on_preview,
            state="disabled",
        )
        self.preview_button.pack(pady=(12, 4))
        self.canvas = tk.Canvas(self.preview_container, highlightthickness=0, background="#f5f6f8")
        self.scrollbar = ttk.Scrollbar(
            self.preview_container, orient="vertical", command=self.canvas.yview
        )
        self.cards_frame = ttk.Frame(self.canvas, padding=8)
        self.cards_window = self.canvas.create_window((0, 0), window=self.cards_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.cards_frame.bind(
            "<Configure>",
            lambda _event: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.bind(
            "<Configure>",
            lambda event: self.canvas.itemconfigure(self.cards_window, width=event.width),
        )

        footer = ttk.Frame(outer)
        footer.pack(fill="x", pady=(12, 0))
        self.convert_button = ttk.Button(
            footer, text="Save selected styles", command=on_start
        )
        self.convert_button.pack(side="left")
        self.progress = ttk.Progressbar(footer, mode="determinate", length=250)
        self.progress.pack(side="left", padx=12)
        ttk.Label(footer, textvariable=self.status).pack(side="left", padx=4)

        self._on_method_toggle = on_method_toggle
        self._on_open_preview = on_open_preview

    def update_mode(self, mode: str) -> None:
        labels = {"one": "Choose image…", "many": "Choose images…", "all": "Choose folder…"}
        self.pick_button.configure(text=labels[mode])
        if mode == "one":
            self.batch_frame.grid_remove()
            self.preview_title.configure(text="3  Preview and select styles")
            self.convert_button.configure(text="Save selected styles")
            self.preview_container.pack(fill="both", expand=True)
        else:
            self.batch_frame.grid()
            self.preview_title.configure(text="3  Batch conversion")
            self.convert_button.configure(text="Convert selected images")
            self.preview_container.pack_forget()
        self.clear_cards()
        self.preview_button.configure(text="Generate previews", state="disabled")
        self.selection_label.configure(text="No images selected")
        self.selection_count.configure(text="")
        self.set_status("Choose an image, image files, or a folder.")

    def clear_cards(self) -> None:
        for child in self.cards_frame.winfo_children():
            child.destroy()
        self.cards.clear()
        self.photo_images.clear()

    def render_cards(
        self,
        source_path: Path,
        results: dict[str, Image.Image],
        selected_methods: set[str],
    ) -> None:
        self.clear_cards()
        for column in range(4):
            self.cards_frame.columnconfigure(column, weight=1)
        for index, method in enumerate(METHODS):
            row, column = divmod(index, 4)
            card = tk.Frame(
                self.cards_frame,
                bg="#ffffff",
                highlightthickness=2,
                highlightbackground="#d1d5db",
                cursor="hand2",
                padx=8,
                pady=8,
            )
            card.method_key = method.key
            card.grid(row=row, column=column, sticky="nsew", padx=6, pady=6)
            thumbnail = results[method.key].copy()
            thumbnail.thumbnail((220, 170), Image.Resampling.NEAREST)
            photo = ImageTk.PhotoImage(thumbnail)
            self.photo_images.append(photo)
            image_label = tk.Label(card, image=photo, bg="#ffffff")
            image_label.pack(fill="both", expand=True)
            title = tk.Label(
                card, text=method.label, font=("Segoe UI", 10, "bold"), bg="#ffffff"
            )
            title.pack(anchor="w", pady=(7, 2))
            description = tk.Label(
                card,
                text=method.description,
                font=("Segoe UI", 8),
                bg="#ffffff",
                fg="#4b5563",
                wraplength=220,
                justify="left",
            )
            description.pack(anchor="w")
            for widget in (card, image_label, title, description):
                widget.bind(
                    "<Button-1>",
                    lambda _event, key=method.key: self._on_method_toggle(key),
                )
            image_label.bind(
                "<Double-Button-1>",
                lambda _event, key=method.key: self._on_open_preview(key),
            )
            self.cards[method.key] = card
        self.update_selected_methods(selected_methods)
        self.selection_count.configure(
            text=f"Preview: {source_path.name} · click cards to select"
        )

    def update_selected_methods(self, selected_methods: set[str]) -> None:
        for method_key, card in self.cards.items():
            selected = method_key in selected_methods
            background = "#dbeafe" if selected else "#ffffff"
            border = "#2563eb" if selected else "#d1d5db"
            card.configure(bg=background, highlightbackground=border)
            for child in card.winfo_children():
                child.configure(bg=background)

    def set_busy(self, busy: bool, message: str) -> None:
        self.pick_button.configure(state="disabled" if busy else "normal")
        self.convert_button.configure(state="disabled" if busy else "normal")
        self.preview_button.configure(state="disabled" if busy else "normal")
        self.pixel_size_input.configure(state="disabled" if busy else "normal")
        self.color_count_input.configure(state="disabled" if busy else "normal")
        self.method_combo.configure(state="disabled" if busy else "readonly")
        for button in self.mode_buttons:
            button.configure(state="disabled" if busy else "normal")
        self.set_status(message)

    def set_preview_ready(self, ready: bool) -> None:
        self.preview_button.configure(
            text="Refresh previews" if ready else "Generate previews",
            state="normal" if ready else "disabled",
        )

    def set_preview_available(self) -> None:
        self.preview_button.configure(text="Generate previews", state="normal")

    def set_selection_label(self, text: str) -> None:
        self.selection_label.configure(text=text)

    def set_selection_count(self, text: str) -> None:
        self.selection_count.configure(text=text)

    def set_status(self, text: str) -> None:
        self.status.set(text)

    def set_progress(self, current: int, total: int) -> None:
        self.progress.configure(maximum=total, value=current)
