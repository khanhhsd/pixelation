# Pixel Art Studio

A small desktop app for previewing and batch-converting pictures into pixel art. It uses Python, Tkinter, Pillow, and NumPy.

## Features

- **One image:** choose one image, explicitly click **Generate previews**, compare eight pixel-art styles, click one or more previews, and save the selected styles. Double-click a preview to inspect it full-size; zoom with the mouse wheel or toolbar.
- **Multiple images:** select any number of files and convert all of them with one chosen style.
- **All images in a folder:** choose a folder to recursively find supported images, then batch convert them with one style.
- Batch modes do not generate or show previews.
- Results are written as PNG files under the project `results/` folder. Existing output files are not overwritten.
- Pixel size and palette color count can be adjusted in the app. In single-image mode, changing either setting refreshes previews after they have first been generated.

Supported inputs: JPEG, PNG, BMP, GIF, TIFF, and WebP. Animated files use their first frame.

## Setup

Python 3.10 or later is required. Tkinter must be available in the Python installation.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

## Run

```powershell
python -m pixel_art_studio
```

Or, after installing the package:

```powershell
pixel-art-studio
```

## Tests

```powershell
python -m unittest discover -s tests -v
```

## Pixel-art styles

Nearest neighbor, box average, adaptive palette, K-means palette, ordered dithering, Floyd–Steinberg dithering, Atkinson dithering, and pixel outlines.

## Project layout

```text
src/pixel_art_studio/
├── app.py              # Desktop entry point
├── controller.py       # Selection, preview, and batch workflow
├── processing.py       # Image discovery and rendering algorithms
├── preview_window.py   # Full-size zoomable image viewer
└── studio_view.py      # Main window layout and preview cards
tests/
└── test_processing.py
```
