"""Quantitative metrics for comparing pixel-art renderings with their source.

* PSNR / SSIM   – standard fidelity measures (scikit-image implementations).
* Delta E 2000  – mean perceptual colour difference in CIELAB (lower = better).
* Colours       – number of distinct colours actually used by the output.
* Isolated (%)  – share of art-grid cells whose colour matches none of their
                  8 neighbours: a measure of "noisy" stray pixels, which pixel
                  artists avoid (lower = cleaner).
"""

from __future__ import annotations

import numpy as np
from PIL import Image
from skimage.color import deltaE_ciede2000, rgb2lab
from skimage.metrics import peak_signal_noise_ratio, structural_similarity

from pixel_art_studio.pipeline import isolated_mask


def _rgb(image: Image.Image | np.ndarray) -> np.ndarray:
    array = np.asarray(image.convert("RGB") if isinstance(image, Image.Image) else image)
    if array.ndim != 3 or array.shape[2] != 3:
        raise ValueError("Expected an RGB image.")
    return array.astype(np.uint8)


def psnr(reference, result) -> float:
    ref, res = _rgb(reference), _rgb(result)
    if np.array_equal(ref, res):
        return float("inf")
    return float(peak_signal_noise_ratio(ref, res, data_range=255))


def ssim(reference, result) -> float:
    ref, res = _rgb(reference), _rgb(result)
    window = min(7, min(ref.shape[:2]) // 2 * 2 - 1)
    return float(structural_similarity(ref, res, data_range=255, channel_axis=2, win_size=max(3, window)))


def delta_e(reference, result) -> float:
    ref, res = _rgb(reference), _rgb(result)
    return float(deltaE_ciede2000(rgb2lab(ref / 255.0), rgb2lab(res / 255.0)).mean())


def color_count(result) -> int:
    return int(len(np.unique(_rgb(result).reshape(-1, 3), axis=0)))


def art_grid(result, pixel_size: int) -> np.ndarray:
    """Sample one value per art pixel (image size must be a multiple of pixel_size)."""
    array = _rgb(result)
    return array[pixel_size // 2 :: pixel_size, pixel_size // 2 :: pixel_size]


def isolated_ratio(result, pixel_size: int) -> float:
    """Percentage of grid cells whose colour differs from all 8 neighbours."""
    grid = art_grid(result, pixel_size)
    packed = (grid[..., 0].astype(np.int64) << 16) | (grid[..., 1].astype(np.int64) << 8) | grid[..., 2]
    return float(isolated_mask(packed).mean() * 100.0)


def evaluate(reference, result, pixel_size: int) -> dict[str, float]:
    return {
        "psnr": psnr(reference, result),
        "ssim": ssim(reference, result),
        "delta_e": delta_e(reference, result),
        "colors": color_count(result),
        "isolated_pct": isolated_ratio(result, pixel_size),
    }
