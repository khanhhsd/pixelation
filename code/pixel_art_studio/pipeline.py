"""Proposed multi-step pixel-art pipeline.

Steps (each one maps to a stage of the course-project pipeline):

1. Pre-processing  – normalise size (optional max side, crop to a multiple of
   the pixel size) and remove noise with a 3x3 median filter.
2. Down-sampling   – area (box) averaging onto the coarse pixel grid; this is
   an anti-aliased re-sampling of the image.
3. Colour quantisation – K-means clustering of grid colours in the perceptual
   CIELAB space (k-means++ initialisation) to build a palette of K colours.
4. Post-processing – majority (mode) filter on the label grid that removes
   isolated "stray" pixels, plus optional Sobel outlines.
5. Up-sampling     – nearest-neighbour enlargement back to the working size.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from PIL import Image, ImageFilter
from skimage.color import rgb2lab

from pixel_art_studio.processing import (
    downsample_size,
    enlarge_nearest,
    kmeans_assign,
    kmeans_fit,
)

_NEIGHBOR_OFFSETS = tuple(
    (dy, dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dy, dx) != (0, 0)
)


@dataclass(frozen=True)
class PipelineConfig:
    pixel_size: int = 4
    color_count: int = 16
    max_side: int | None = None  # resize so the longest side is at most this
    crop_to_grid: bool = False  # crop so width/height are multiples of pixel_size
    denoise: bool = True  # 3x3 median filter before down-sampling
    color_space: str = "lab"  # "lab" or "rgb" for K-means clustering
    cleanup: bool = True  # majority filter on isolated grid cells
    cleanup_passes: int = 1
    outline: bool = False  # draw dark Sobel outlines on the grid
    outline_threshold: float = 0.25  # fraction of the maximum gradient
    seed: int = 0

    def validate(self) -> None:
        if self.pixel_size < 1:
            raise ValueError("Pixel size must be at least 1.")
        if not 2 <= self.color_count <= 256:
            raise ValueError("Color count must be between 2 and 256.")
        if self.color_space not in ("lab", "rgb"):
            raise ValueError("color_space must be 'lab' or 'rgb'.")
        if self.max_side is not None and self.max_side < self.pixel_size:
            raise ValueError("max_side must be at least the pixel size.")


@dataclass
class PipelineResult:
    image: Image.Image  # final full-size pixel art
    grid: Image.Image  # one pixel per art "pixel"
    labels: np.ndarray  # palette index of every grid cell
    palette: np.ndarray  # K x 3 uint8 RGB colours
    stages: dict[str, Image.Image] = field(default_factory=dict)


# --------------------------------------------------------------------------- 1
def normalize_size(
    image: Image.Image,
    pixel_size: int,
    max_side: int | None = None,
    crop_to_grid: bool = False,
) -> Image.Image:
    """Resize (Lanczos) to a maximum side and optionally crop to the pixel grid."""
    image = image.convert("RGB")
    if max_side is not None and max(image.size) > max_side:
        scale = max_side / max(image.size)
        size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
        image = image.resize(size, Image.Resampling.LANCZOS)
    if crop_to_grid:
        width = max(pixel_size, image.width - image.width % pixel_size)
        height = max(pixel_size, image.height - image.height % pixel_size)
        image = image.crop((0, 0, min(width, image.width), min(height, image.height)))
    return image


def denoise(image: Image.Image) -> Image.Image:
    """3x3 median filter: removes impulse noise and fine texture, keeps edges."""
    return image.filter(ImageFilter.MedianFilter(3))


# --------------------------------------------------------------------------- 2
def downsample(image: Image.Image, pixel_size: int) -> Image.Image:
    """Area-average every pixel_size x pixel_size block (anti-aliased sampling)."""
    return image.resize(downsample_size(image, pixel_size), Image.Resampling.BOX)


# --------------------------------------------------------------------------- 3
def quantize_kmeans(
    grid: Image.Image, color_count: int, color_space: str = "lab", seed: int = 0
) -> tuple[np.ndarray, np.ndarray]:
    """Cluster grid colours; return (labels H x W, palette K x 3 uint8 RGB).

    Clustering happens in ``color_space``; each palette colour is the RGB mean
    of its members, so it is always a valid colour present in the image range.
    """
    rgb = np.asarray(grid, dtype=np.float64).reshape(-1, 3)
    features = rgb2lab(rgb.reshape(1, -1, 3) / 255.0).reshape(-1, 3) if color_space == "lab" else rgb
    centers = kmeans_fit(features, color_count, seed=seed)
    labels = kmeans_assign(features, centers)
    used = np.unique(labels)
    palette = np.array([rgb[labels == index].mean(axis=0) for index in used])
    labels = np.searchsorted(used, labels)  # compact indices 0..K'-1
    palette = np.clip(np.rint(palette), 0, 255).astype(np.uint8)
    return labels.reshape(grid.height, grid.width), palette


# --------------------------------------------------------------------------- 4
def _neighbor_stack(labels: np.ndarray) -> np.ndarray:
    padded = np.pad(labels, 1, mode="constant", constant_values=-1)
    height, width = labels.shape
    return np.stack(
        [padded[1 + dy : 1 + dy + height, 1 + dx : 1 + dx + width] for dy, dx in _NEIGHBOR_OFFSETS]
    )


def isolated_mask(labels: np.ndarray) -> np.ndarray:
    """True where a cell shares its label with none of its 8 neighbours."""
    if labels.size <= 1:
        return np.zeros(labels.shape, dtype=bool)
    return (_neighbor_stack(labels) == labels[None]).sum(axis=0) == 0


def majority_cleanup(labels: np.ndarray, passes: int = 1) -> np.ndarray:
    """Replace isolated cells by the most frequent label among their neighbours.

    This is a conditional mode (majority) filter: unlike a plain 3x3 mode
    filter it only touches single-cell specks, so thin lines and corners that
    are at least two cells wide survive.
    """
    labels = labels.copy()
    for _ in range(passes):
        isolated = isolated_mask(labels)
        if not isolated.any():
            break
        neighbors = _neighbor_stack(labels)[:, isolated]  # 8 x N
        label_count = int(labels.max()) + 1
        counts = np.stack([(neighbors == value).sum(axis=0) for value in range(label_count)])
        labels[isolated] = counts.argmax(axis=0)
    return labels


def outline_mask(grid_rgb: np.ndarray, threshold: float = 0.25) -> np.ndarray:
    """Sobel gradient magnitude on luminance, thresholded relative to its max."""
    luminance = grid_rgb.astype(np.float64) @ np.array([0.299, 0.587, 0.114])
    padded = np.pad(luminance, 1, mode="edge")
    gx = (
        padded[:-2, 2:] + 2 * padded[1:-1, 2:] + padded[2:, 2:]
        - padded[:-2, :-2] - 2 * padded[1:-1, :-2] - padded[2:, :-2]
    )
    gy = (
        padded[2:, :-2] + 2 * padded[2:, 1:-1] + padded[2:, 2:]
        - padded[:-2, :-2] - 2 * padded[:-2, 1:-1] - padded[:-2, 2:]
    )
    magnitude = np.hypot(gx, gy)
    peak = magnitude.max()
    return magnitude >= threshold * peak if peak > 0 else np.zeros_like(magnitude, dtype=bool)


# --------------------------------------------------------------------------- 5
def run_pipeline(
    image: Image.Image, config: PipelineConfig | None = None, keep_stages: bool = False
) -> PipelineResult:
    config = config or PipelineConfig()
    config.validate()
    stages: dict[str, Image.Image] = {}

    work = normalize_size(image, config.pixel_size, config.max_side, config.crop_to_grid)
    if keep_stages:
        stages["1_input"] = work
    if config.denoise:
        work = denoise(work)
        if keep_stages:
            stages["2_denoised"] = work

    small = downsample(work, config.pixel_size)
    if keep_stages:
        stages["3_downsampled"] = enlarge_nearest(small, work.size)

    labels, palette = quantize_kmeans(small, config.color_count, config.color_space, config.seed)
    if keep_stages:
        stages["4_quantized"] = enlarge_nearest(Image.fromarray(palette[labels]), work.size)

    if config.cleanup:
        labels = majority_cleanup(labels, config.cleanup_passes)
        if keep_stages:
            stages["5_cleaned"] = enlarge_nearest(Image.fromarray(palette[labels]), work.size)

    grid_rgb = palette[labels]
    if config.outline:
        grid_rgb = grid_rgb.copy()
        grid_rgb[outline_mask(grid_rgb, config.outline_threshold)] = (20, 20, 24)

    grid = Image.fromarray(grid_rgb)
    result = enlarge_nearest(grid, work.size)
    if keep_stages:
        stages["6_output"] = result
    return PipelineResult(result, grid, labels, palette, stages)
