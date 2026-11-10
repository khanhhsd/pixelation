import sys
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))

from pixel_art_studio import metrics  # noqa: E402
from pixel_art_studio.pipeline import (  # noqa: E402
    PipelineConfig,
    isolated_mask,
    majority_cleanup,
    normalize_size,
    outline_mask,
    quantize_kmeans,
    run_pipeline,
)
from pixel_art_studio.processing import kmeans_assign, kmeans_fit, process_image  # noqa: E402


def gradient_image(width=64, height=48) -> Image.Image:
    x = np.linspace(0, 255, width)[None, :].repeat(height, axis=0)
    y = np.linspace(0, 255, height)[:, None].repeat(width, axis=1)
    rgb = np.stack([x, y, 255 - x], axis=2).astype(np.uint8)
    return Image.fromarray(rgb)


class PipelineTests(unittest.TestCase):
    def test_output_size_palette_and_grid(self):
        image = gradient_image()
        result = run_pipeline(image, PipelineConfig(pixel_size=4, color_count=8), keep_stages=True)
        self.assertEqual(result.image.size, image.size)
        self.assertEqual(result.grid.size, (16, 12))
        self.assertLessEqual(len(result.palette), 8)
        self.assertLessEqual(metrics.color_count(result.image), 8)
        self.assertEqual(
            list(result.stages),
            ["1_input", "2_denoised", "3_downsampled", "4_quantized", "5_cleaned", "6_output"],
        )

    def test_normalize_size_resizes_and_crops_to_grid(self):
        image = Image.new("RGB", (1001, 503))
        out = normalize_size(image, pixel_size=8, max_side=500, crop_to_grid=True)
        self.assertLessEqual(max(out.size), 500)
        self.assertEqual(out.width % 8, 0)
        self.assertEqual(out.height % 8, 0)

    def test_invalid_config_is_rejected(self):
        for config in (
            PipelineConfig(pixel_size=0),
            PipelineConfig(color_count=1),
            PipelineConfig(color_space="hsv"),
        ):
            with self.subTest(config=config), self.assertRaises(ValueError):
                run_pipeline(gradient_image(), config)

    def test_majority_cleanup_removes_only_isolated_cells(self):
        labels = np.zeros((5, 5), dtype=int)
        labels[2, 2] = 1  # single stray cell -> removed
        labels[0, 3:5] = 2  # two-cell run -> kept
        cleaned = majority_cleanup(labels)
        self.assertEqual(cleaned[2, 2], 0)
        self.assertTrue((cleaned[0, 3:5] == 2).all())
        self.assertFalse(isolated_mask(cleaned).any())

    def test_kmeans_recovers_well_separated_clusters(self):
        rng = np.random.default_rng(1)
        truth = np.array([[0, 0, 0], [200, 0, 0], [0, 200, 0]], dtype=float)
        points = np.concatenate([c + rng.normal(0, 3, (200, 3)) for c in truth])
        centers = kmeans_fit(points, 3, seed=0)
        found = sorted(map(tuple, np.rint(centers / 50) * 50))
        self.assertEqual(found, sorted(map(tuple, truth)))
        self.assertEqual(len(np.unique(kmeans_assign(points, centers))), 3)

    def test_kmeans_handles_fewer_colors_than_k(self):
        grid = Image.new("RGB", (6, 4), (10, 20, 30))
        labels, palette = quantize_kmeans(grid, 16)
        self.assertEqual(palette.tolist(), [[10, 20, 30]])
        self.assertTrue((labels == 0).all())

    def test_kmeans_method_keeps_full_grid_resolution(self):
        # Regression: grids wider than 128 cells used to be clustered on a
        # thumbnail and stretched, losing resolution.
        rng = np.random.default_rng(0)
        image = Image.fromarray(rng.integers(0, 2, (8, 300, 1)).repeat(3, axis=2).astype(np.uint8) * 255)
        out = np.asarray(process_image(image, "kmeans", pixel_size=1, color_count=2))
        np.testing.assert_array_equal(out, np.asarray(image))

    def test_outline_marks_edges_only(self):
        grid = np.zeros((6, 6, 3), dtype=np.uint8)
        grid[:, 3:] = 255
        mask = outline_mask(grid)
        self.assertTrue(mask[:, 2:4].all())
        self.assertFalse(mask[:, 0].any() or mask[:, 5].any())


class MetricTests(unittest.TestCase):
    def test_identical_images(self):
        image = gradient_image()
        self.assertEqual(metrics.psnr(image, image), float("inf"))
        self.assertAlmostEqual(metrics.ssim(image, image), 1.0)
        self.assertAlmostEqual(metrics.delta_e(image, image), 0.0)

    def test_isolated_ratio(self):
        grid = np.zeros((4, 4, 3), dtype=np.uint8)
        grid[1, 1] = 255  # 1 of 16 cells is isolated
        image = Image.fromarray(grid).resize((16, 16), Image.Resampling.NEAREST)
        self.assertAlmostEqual(metrics.isolated_ratio(image, 4), 100 / 16)


if __name__ == "__main__":
    unittest.main()
