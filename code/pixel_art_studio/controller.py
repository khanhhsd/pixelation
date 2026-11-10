"""Application controller for Pixel Art Studio workflows."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from PIL import Image, ImageOps

from pixel_art_studio.preview_window import ImagePreviewWindow
from pixel_art_studio.processing import METHODS, discover_images, process_image
from pixel_art_studio.studio_view import StudioView

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = PROJECT_ROOT / "results"


class PixelArtStudio:
    """Coordinates selection, processing jobs, and output for the desktop UI."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Pixel Art Studio")
        self.root.geometry("1180x850")
        self.root.minsize(900, 650)

        self.files: list[Path] = []
        self.preview_results: dict[str, Image.Image] = {}
        self.selected_methods: set[str] = set()
        self.events: queue.Queue[tuple] = queue.Queue()
        self.busy = False
        self._preview_refresh_after: str | None = None

        self.view = StudioView(
            root=root,
            on_mode_changed=self._update_mode,
            on_pick_images=self._pick_images,
            on_preview=self._request_preview,
            on_start=self._start,
            on_settings_changed=self._schedule_preview_refresh,
            on_method_toggle=self._toggle_method,
            on_open_preview=self._open_preview,
        )
        self.root.after(100, self._poll_events)

    def _update_mode(self) -> None:
        if self.busy:
            return
        self._cancel_preview_refresh()
        self.files = []
        self.preview_results.clear()
        self.selected_methods.clear()
        self.view.update_mode(self.view.mode.get())

    def _pick_images(self) -> None:
        mode = self.view.mode.get()
        if mode == "one":
            selected = filedialog.askopenfilename(
                title="Choose an image",
                filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp *.gif *.tif *.tiff *.webp")],
            )
            files = [Path(selected)] if selected else []
        elif mode == "many":
            selected = filedialog.askopenfilenames(
                title="Choose images",
                filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp *.gif *.tif *.tiff *.webp")],
            )
            files = [Path(path) for path in selected]
        else:
            selected = filedialog.askdirectory(title="Choose a folder containing images")
            if not selected:
                return
            try:
                files = discover_images(Path(selected), excluded_folder=RESULTS_DIR)
            except (OSError, NotADirectoryError) as error:
                messagebox.showerror("Could not scan folder", str(error))
                return
            if not files:
                messagebox.showinfo(
                    "No images found", "No supported images were found in that folder."
                )
                return

        if not files:
            return
        self._cancel_preview_refresh()
        self.files = files
        if mode == "one":
            self.selected_methods.clear()
            self.preview_results.clear()
            self.view.clear_cards()
            self.view.set_preview_available()
            self.view.set_selection_label(files[0].name)
            self.view.set_status(
                "Image selected. No preview is generated until you click Generate previews."
            )
        else:
            self.view.set_selection_label(f"{len(files)} image(s) selected")
            self.view.set_status(f"Ready to convert {len(files)} image(s).")
            self.view.set_selection_count(f"Output folder: {RESULTS_DIR}")

    def _request_preview(self) -> None:
        if self.busy or self.view.mode.get() != "one" or not self.files:
            return
        try:
            settings = self._settings()
        except ValueError as error:
            messagebox.showerror("Invalid settings", str(error))
            return
        self._start_preview(self.files[0], settings)

    def _start_preview(self, path: Path, settings: tuple[int, int]) -> None:
        self._set_busy(True, "Generating style previews…")

        def worker() -> None:
            try:
                with Image.open(path) as source:
                    image = ImageOps.exif_transpose(source).convert("RGB")
                results = {
                    method.key: process_image(image, method.key, *settings)
                    for method in METHODS
                }
                self.events.put(("preview_done", path, results))
            except Exception as error:
                self.events.put(("error", f"Could not preview {path.name}: {error}"))

        threading.Thread(target=worker, daemon=True).start()

    def _schedule_preview_refresh(self, *_args: str) -> None:
        if (
            self.view.mode.get() != "one"
            or not self.files
            or not self.preview_results
            or self.busy
        ):
            return
        self._cancel_preview_refresh()
        self.view.set_status("Settings changed; refreshing previews…")
        self._preview_refresh_after = self.root.after(400, self._refresh_single_preview)

    def _cancel_preview_refresh(self) -> None:
        if self._preview_refresh_after is not None:
            self.root.after_cancel(self._preview_refresh_after)
            self._preview_refresh_after = None

    def _refresh_single_preview(self) -> None:
        self._preview_refresh_after = None
        if self.view.mode.get() != "one" or not self.files or self.busy:
            return
        try:
            settings = self._settings()
        except ValueError as error:
            self.view.set_status(f"Invalid settings: {error}")
            return
        self._start_preview(self.files[0], settings)

    def _start(self) -> None:
        if self.busy:
            return
        if not self.files:
            messagebox.showinfo("Select images", "Choose one or more images first.")
            return
        try:
            settings = self._settings()
        except ValueError as error:
            messagebox.showerror("Invalid settings", str(error))
            return

        if self.view.mode.get() == "one":
            if not self.preview_results:
                self.view.set_status("Click Generate previews before saving a style.")
                return
            if not self.selected_methods:
                messagebox.showinfo(
                    "Select styles", "Click one or more previews before saving."
                )
                return
            self._start_single_save()
            return

        method = next(
            (method for method in METHODS if method.label == self.view.batch_method.get()),
            None,
        )
        if method is None:
            messagebox.showerror("Invalid method", "Choose a pixel-art method from the list.")
            return
        self._start_batch(method.key, settings)

    def _start_single_save(self) -> None:
        selected = sorted(self.selected_methods)
        path = self.files[0]
        results = self.preview_results.copy()
        self._set_busy(True, "Saving selected styles…")

        def worker() -> None:
            try:
                saved = []
                for key in selected:
                    output = self._new_output_path(path, key)
                    results[key].save(output, format="PNG")
                    saved.append(output)
                    self.events.put(("progress", len(saved), len(selected)))
                self.events.put(("batch_done", saved))
            except Exception as error:
                self.events.put(("error", f"Could not save result: {error}"))

        threading.Thread(target=worker, daemon=True).start()

    def _start_batch(self, method_key: str, settings: tuple[int, int]) -> None:
        files = list(self.files)
        self._set_busy(True, "Converting images…")
        self.view.set_progress(0, len(files))

        def worker() -> None:
            saved = []
            failures = []
            for index, path in enumerate(files, start=1):
                try:
                    with Image.open(path) as source:
                        image = ImageOps.exif_transpose(source).convert("RGB")
                    result = process_image(image, method_key, *settings)
                    output = self._new_output_path(path, method_key)
                    result.save(output, format="PNG")
                    saved.append(output)
                except Exception as error:
                    failures.append(f"{path}: {error}")
                self.events.put(("progress", index, len(files)))
            self.events.put(("batch_done", saved, failures))

        threading.Thread(target=worker, daemon=True).start()

    def _new_output_path(self, source: Path, method_key: str) -> Path:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        base = f"{source.stem}_{method_key}"
        output = RESULTS_DIR / f"{base}.png"
        suffix = 2
        while output.exists():
            output = RESULTS_DIR / f"{base}_{suffix}.png"
            suffix += 1
        return output

    def _settings(self) -> tuple[int, int]:
        try:
            pixel_size = self.view.pixel_size.get()
            color_count = self.view.color_count.get()
        except tk.TclError as error:
            raise ValueError("Pixel size and color count must be whole numbers.") from error
        if not 1 <= pixel_size <= 128:
            raise ValueError("Pixel size must be between 1 and 128.")
        if not 2 <= color_count <= 256:
            raise ValueError("Palette color count must be between 2 and 256.")
        return pixel_size, color_count

    def _set_busy(self, busy: bool, message: str) -> None:
        self.busy = busy
        self.view.set_busy(busy, message)

    def _poll_events(self) -> None:
        try:
            while True:
                event = self.events.get_nowait()
                if event[0] == "preview_done":
                    _, path, self.preview_results = event
                    self.view.render_cards(path, self.preview_results, self.selected_methods)
                    self.view.set_preview_ready(True)
                    self._set_busy(False, "Click previews to select styles, then save.")
                elif event[0] == "progress":
                    _, current, total = event
                    self.view.set_progress(current, total)
                    self.view.set_status(f"Processing {current} of {total}…")
                elif event[0] == "batch_done":
                    saved = event[1]
                    failures = event[2] if len(event) > 2 else []
                    self._set_busy(False, f"Saved {len(saved)} image(s) to {RESULTS_DIR}")
                    if failures:
                        messagebox.showwarning(
                            "Conversion finished with errors",
                            f"Saved {len(saved)} image(s); {len(failures)} failed.\n\n"
                            + "\n".join(failures[:8]),
                        )
                    else:
                        messagebox.showinfo(
                            "Conversion complete",
                            f"Saved {len(saved)} image(s) in:\n{RESULTS_DIR}",
                        )
                elif event[0] == "error":
                    self._set_busy(False, "Operation failed.")
                    self.view.set_preview_ready(False)
                    messagebox.showerror("Pixel Art Studio", event[1])
        except queue.Empty:
            pass
        self.root.after(100, self._poll_events)

    def _toggle_method(self, method_key: str) -> None:
        if method_key in self.selected_methods:
            self.selected_methods.remove(method_key)
        else:
            self.selected_methods.add(method_key)
        self.view.update_selected_methods(self.selected_methods)
        self.view.set_selection_count(
            f"{len(self.selected_methods)} style(s) selected · click cards to toggle"
        )

    def _open_preview(self, method_key: str) -> None:
        method = next(method for method in METHODS if method.key == method_key)
        ImagePreviewWindow(self.root, method.label, self.preview_results[method_key])
