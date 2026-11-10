"""Regressions for defects found in the 2026-11 audit of the legacy entry points."""
from importlib.util import find_spec
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import numpy as np
from PIL import Image, ImageCms

from ghostframe import read_image


class LegacyInputTests(unittest.TestCase):
    def test_sixteen_bit_and_transparent_inputs_are_rejected(self):
        with TemporaryDirectory() as directory:
            deep = Path(directory) / "deep.png"
            Image.fromarray(np.full((64, 64), 40000, np.uint16)).save(deep)
            with self.assertRaisesRegex(ValueError, "8-bit"):
                read_image(deep)  # Previously returned clipped (255, 255, 255) pixels.
            clear = Path(directory) / "clear.png"
            Image.new("RGBA", (64, 64), (200, 10, 10, 0)).save(clear)
            with self.assertRaisesRegex(ValueError, "transparent"):
                read_image(clear)  # Previously exposed the hidden (200, 10, 10).
            opaque = Path(directory) / "opaque.png"
            Image.new("RGBA", (64, 64), (200, 10, 10, 255)).save(opaque)
            self.assertEqual(read_image(opaque).getpixel((0, 0)), (200, 10, 10))


@unittest.skipIf(find_spec("cryptography") is None or find_spec("reedsolo") is None, "Install the tiled extra")
class LegacyOutputTests(unittest.TestCase):
    def test_published_png_carries_no_icc_profile(self):
        from experiments.message_cli import publish_encoded

        icc = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
        marked = Image.new("RGB", (32, 32), (1, 2, 3))
        marked.info["icc_profile"] = icc  # As inherited from a JPEG cover via image.copy().
        with TemporaryDirectory() as directory:
            output = Path(directory) / "marked.png"
            publish_encoded(marked, output, lambda reopened: True)
            with Image.open(output) as image:
                self.assertNotIn("icc_profile", image.info)
                self.assertEqual(image.getpixel((0, 0)), (1, 2, 3))

    def test_neural_encode_checks_output_directory_before_optimizing(self):
        from experiments.message_cli import neural_encode_file

        with TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "directory does not exist"):
                neural_encode_file(Image.new("RGB", (96, 80)), b"x", b"pw", Path(directory) / "no" / "o.png", model=None)


if __name__ == "__main__":
    unittest.main()
