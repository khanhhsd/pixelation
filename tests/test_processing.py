import sys
from pathlib import Path as _Path

sys.path.insert(0, str(_Path(__file__).resolve().parents[1] / "code"))
from pathlib import Path
import tempfile
import unittest

from PIL import Image

from pixel_art_studio.processing import METHODS, discover_images, process_image


class ProcessingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.image = Image.new("RGB", (37, 29), (90, 140, 210))

    def test_every_method_returns_same_size_rgb_image(self) -> None:
        for method in METHODS:
            with self.subTest(method=method.key):
                result = process_image(self.image, method.key, pixel_size=4, color_count=8)
                self.assertEqual(result.size, self.image.size)
                self.assertEqual(result.mode, "RGB")

    def test_invalid_settings_are_reported(self) -> None:
        with self.assertRaises(ValueError):
            process_image(self.image, "nearest", pixel_size=0, color_count=8)
        with self.assertRaises(ValueError):
            process_image(self.image, "palette", pixel_size=4, color_count=1)
        with self.assertRaises(ValueError):
            process_image(self.image, "missing", pixel_size=4, color_count=8)

    def test_discovery_is_recursive_sorted_and_excludes_results(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "nested").mkdir()
            (root / "results").mkdir()
            (root / "b.PNG").write_bytes(b"image")
            (root / "nested" / "a.jpg").write_bytes(b"image")
            (root / "results" / "old.png").write_bytes(b"image")
            (root / ".hidden.png").write_bytes(b"image")
            (root / "notes.txt").write_text("not an image", encoding="utf-8")

            paths = discover_images(root, excluded_folder=root / "results")

            self.assertEqual(
                [path.relative_to(root).as_posix() for path in paths],
                ["b.PNG", "nested/a.jpg"],
            )

    def test_missing_folder_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(NotADirectoryError):
                discover_images(Path(temporary) / "missing")


if __name__ == "__main__":
    unittest.main()
