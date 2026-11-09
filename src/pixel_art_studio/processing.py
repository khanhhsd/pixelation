"""Image discovery and pixel-art rendering methods."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image, ImageFilter, ImageOps

SUPPORTED_EXTENSIONS = frozenset(
    {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp"}
)


def discover_images(folder: Path, excluded_folder: Path | None = None) -> list[Path]:
    """Return supported images below a folder, sorted by relative path."""
    folder = folder.expanduser().resolve()
    if not folder.is_dir():
        raise NotADirectoryError(f"Image folder not found: {folder}")

    excluded = excluded_folder.expanduser().resolve() if excluded_folder else None
    images = []
    for path in folder.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        if excluded and path.resolve().is_relative_to(excluded):
            continue
        if any(part.startswith(".") for part in path.relative_to(folder).parts):
            continue
        images.append(path)
    return sorted(images, key=lambda path: path.relative_to(folder).as_posix().casefold())


def downsample_size(image: Image.Image, pixel_size: int) -> tuple[int, int]:
    if pixel_size < 1:
        raise ValueError("Pixel size must be at least 1.")
    return max(1, image.width // pixel_size), max(1, image.height // pixel_size)


def enlarge_nearest(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    return image.resize(size, Image.Resampling.NEAREST)


def _small_image(image: Image.Image, pixel_size: int) -> Image.Image:
    return image.resize(downsample_size(image, pixel_size), Image.Resampling.BOX)


def _palette(image: Image.Image, pixel_size: int, color_count: int) -> Image.Image:
    _validate_color_count(color_count)
    small = _small_image(image, pixel_size)
    reduced = small.quantize(
        colors=color_count,
        method=Image.Quantize.MEDIANCUT,
        dither=Image.Dither.NONE,
    ).convert("RGB")
    return enlarge_nearest(reduced, image.size)


def _validate_color_count(color_count: int) -> None:
    if not 2 <= color_count <= 256:
        raise ValueError("Color count must be between 2 and 256.")


def _bayer_matrix(order: int = 4) -> np.ndarray:
    matrix = np.array([[0, 2], [3, 1]], dtype=np.float32)
    while matrix.shape[0] < order:
        matrix = np.block(
            [
                [4 * matrix, 4 * matrix + 2],
                [4 * matrix + 3, 4 * matrix + 1],
            ]
        )
    return matrix


def _quantize_ordered(image: Image.Image, levels: int = 4) -> Image.Image:
    values = np.asarray(image, dtype=np.float32)
    order = 4
    thresholds = (_bayer_matrix(order) + 0.5) / (order * order)
    thresholds = np.tile(
        thresholds,
        (
            int(np.ceil(values.shape[0] / order)),
            int(np.ceil(values.shape[1] / order)),
        ),
    )[: values.shape[0], : values.shape[1], None]
    scaled = values / 255.0 * (levels - 1)
    lower = np.floor(scaled)
    indices = lower + ((scaled - lower) > thresholds)
    quantized = np.clip(indices, 0, levels - 1) * (255.0 / (levels - 1))
    return Image.fromarray(np.rint(quantized).astype(np.uint8))


def _quantize_error_diffusion(
    image: Image.Image, levels: int, atkinson: bool = False
) -> Image.Image:
    work = np.asarray(image, dtype=np.float32).copy()
    height, width, _ = work.shape
    step = 255.0 / (levels - 1)
    if atkinson:
        neighbors = ((1, 0, 1 / 8), (2, 0, 1 / 8), (-1, 1, 1 / 8),
                     (0, 1, 1 / 8), (1, 1, 1 / 8), (0, 2, 1 / 8))
    else:
        neighbors = ((1, 0, 7 / 16), (-1, 1, 3 / 16),
                     (0, 1, 5 / 16), (1, 1, 1 / 16))

    for y in range(height):
        for x in range(width):
            old = np.clip(work[y, x], 0, 255)
            new = np.rint(old / step) * step
            work[y, x] = new
            error = old - new
            for dx, dy, weight in neighbors:
                nx, ny = x + dx, y + dy
                if 0 <= nx < width and ny < height:
                    work[ny, nx] += error * weight
    return Image.fromarray(np.clip(np.rint(work), 0, 255).astype(np.uint8))


def _kmeans_palette(
    image: Image.Image, pixel_size: int, color_count: int, max_iterations: int = 20
) -> Image.Image:
    _validate_color_count(color_count)
    small = _small_image(image, pixel_size)
    sample = small.copy()
    sample.thumbnail((128, 128), Image.Resampling.BOX)
    pixels = np.asarray(sample, dtype=np.float32).reshape(-1, 3)
    cluster_count = min(color_count, len(pixels))
    rng = np.random.default_rng(0)
    centers = pixels[rng.choice(len(pixels), size=cluster_count, replace=False)].copy()

    for _ in range(max_iterations):
        distances = ((pixels[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
        labels = distances.argmin(axis=1)
        counts = np.bincount(labels, minlength=cluster_count)
        new_centers = centers.copy()
        for index in range(cluster_count):
            if counts[index]:
                new_centers[index] = pixels[labels == index].mean(axis=0)
            else:
                new_centers[index] = pixels[distances.min(axis=1).argmax()]
        if np.allclose(new_centers, centers):
            centers = new_centers
            break
        centers = new_centers

    distances = ((pixels[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
    clustered = centers[distances.argmin(axis=1)].reshape(np.asarray(sample).shape)
    reduced = Image.fromarray(np.clip(np.rint(clustered), 0, 255).astype(np.uint8))
    if reduced.size != small.size:
        reduced = reduced.resize(small.size, Image.Resampling.NEAREST)
    return enlarge_nearest(reduced, image.size)


def _outlined(image: Image.Image, pixel_size: int, color_count: int) -> Image.Image:
    base = _palette(image, pixel_size, color_count)
    edges = _small_image(image, pixel_size).convert("L").filter(ImageFilter.FIND_EDGES)
    edge_mask = edges.point(lambda value: 255 if value >= 48 else 0)
    edge_mask = enlarge_nearest(edge_mask, image.size)
    outlined = Image.new("RGB", image.size, (20, 20, 24))
    outlined.paste(base, mask=ImageOps.invert(edge_mask))
    return outlined


@dataclass(frozen=True)
class Method:
    key: str
    label: str
    description: str
    render: Callable[[Image.Image, int, int], Image.Image]


def _nearest(image: Image.Image, pixel_size: int, _colors: int) -> Image.Image:
    return enlarge_nearest(
        image.resize(downsample_size(image, pixel_size), Image.Resampling.NEAREST),
        image.size,
    )


def _box_average(image: Image.Image, pixel_size: int, _colors: int) -> Image.Image:
    return enlarge_nearest(_small_image(image, pixel_size), image.size)


def _ordered(image: Image.Image, pixel_size: int, _colors: int) -> Image.Image:
    return enlarge_nearest(_quantize_ordered(_small_image(image, pixel_size)), image.size)


def _floyd_steinberg(image: Image.Image, pixel_size: int, _colors: int) -> Image.Image:
    return enlarge_nearest(
        _quantize_error_diffusion(_small_image(image, pixel_size), 4), image.size
    )


def _atkinson(image: Image.Image, pixel_size: int, _colors: int) -> Image.Image:
    return enlarge_nearest(
        _quantize_error_diffusion(_small_image(image, pixel_size), 4, atkinson=True),
        image.size,
    )


METHODS = (
    Method("nearest", "Nearest neighbor", "Hard-edged blocks; preserves source samples.", _nearest),
    Method("box-average", "Box average", "Average each block for smooth color transitions.", _box_average),
    Method("palette", "Adaptive palette", "Limit the image to a compact adaptive palette.", _palette),
    Method("kmeans", "K-means palette", "Cluster block colors into a balanced palette.", _kmeans_palette),
    Method("ordered", "Ordered dithering", "Repeating Bayer pattern simulates extra tones.", _ordered),
    Method("floyd-steinberg", "Floyd–Steinberg", "Classic error diffusion for smooth tonal detail.", _floyd_steinberg),
    Method("atkinson", "Atkinson dithering", "High-contrast, classic computer-art texture.", _atkinson),
    Method("outline", "Pixel outlines", "Add dark outlines around strong pixel-grid edges.", _outlined),
)

METHOD_BY_KEY = {method.key: method for method in METHODS}


def process_image(
    image: Image.Image, method_key: str, pixel_size: int, color_count: int
) -> Image.Image:
    """Render an RGB image with one named pixel-art method."""
    if method_key not in METHOD_BY_KEY:
        raise ValueError(f"Unknown method: {method_key}")
    if pixel_size < 1:
        raise ValueError("Pixel size must be at least 1.")
    return METHOD_BY_KEY[method_key].render(image.convert("RGB"), pixel_size, color_count)
