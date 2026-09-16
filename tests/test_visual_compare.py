from io import BytesIO
from pathlib import Path
import sys
import unittest

try:
    from PIL import Image
except ImportError:
    Image = None

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from visual_compare import compare_images  # noqa: E402


def png(size, color):
    image = Image.new("RGB", size, color)
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


@unittest.skipIf(Image is None, "Pillow is an optional visual-check dependency")
class VisualCompareTests(unittest.TestCase):
    def test_detects_content_change_and_keeps_identical_images_clean(self):
        original = png((10, 10), "white")
        self.assertEqual(compare_images(original, original, 16)["changed_pixels"], 0)
        changed = compare_images(original, png((10, 10), "black"), 16)
        self.assertEqual(changed["changed_pixels"], 100)
        self.assertEqual(changed["changed_percent"], 100)

    def test_reports_page_height_change(self):
        comparison = compare_images(png((10, 10), "white"), png((10, 12), "white"), 16)
        self.assertTrue(comparison["size_changed"])
        self.assertEqual(comparison["before_size"], (10, 10))
        self.assertEqual(comparison["after_size"], (10, 12))


if __name__ == "__main__":
    unittest.main()
