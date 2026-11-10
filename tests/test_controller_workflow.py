import sys
from pathlib import Path as _Path

sys.path.insert(0, str(_Path(__file__).resolve().parents[1] / "code"))
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from pixel_art_studio.controller import PixelArtStudio


class FakeVariable:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value


class FakeView:
    def __init__(self):
        self.mode = FakeVariable("one")
        self.pixel_size = FakeVariable(8)
        self.color_count = FakeVariable(32)
        self.batch_method = FakeVariable("Adaptive palette")
        self.clear_cards = Mock()
        self.set_preview_available = Mock()
        self.set_selection_label = Mock()
        self.set_status = Mock()
        self.set_selection_count = Mock()


class ControllerWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.app = PixelArtStudio.__new__(PixelArtStudio)
        self.app.view = FakeView()
        self.app.files = []
        self.app.preview_results = {}
        self.app.selected_methods = set()
        self.app.busy = False
        self.app._preview_refresh_after = None
        self.app.root = Mock()
        self.app._start_preview = Mock()

    def test_selecting_one_image_does_not_generate_preview(self):
        selected_path = Path("selected.png")
        with patch(
            "pixel_art_studio.controller.filedialog.askopenfilename",
            return_value=str(selected_path),
        ):
            self.app._pick_images()

        self.assertEqual(self.app.files, [selected_path])
        self.app._start_preview.assert_not_called()
        self.app.view.set_preview_available.assert_called_once_with()
        self.app.view.set_status.assert_called_once_with(
            "Image selected. No preview is generated until you click Generate previews."
        )

    def test_settings_changes_before_preview_do_not_schedule_rendering(self):
        self.app.files = [Path("selected.png")]

        self.app._schedule_preview_refresh()

        self.app.root.after.assert_not_called()
        self.app._start_preview.assert_not_called()

    def test_generate_preview_uses_selected_image_and_current_settings(self):
        selected_path = Path("selected.png")
        self.app.files = [selected_path]

        self.app._request_preview()

        self.app._start_preview.assert_called_once_with(selected_path, (8, 32))


if __name__ == "__main__":
    unittest.main()
