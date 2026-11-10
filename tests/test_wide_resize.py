from importlib.util import find_spec
import unittest

if any(find_spec(name) is None for name in ("cryptography", "reedsolo")):
    raise unittest.SkipTest("Install the tiled experiment extra")

from PIL import Image

from experiments.alignment_search import resize_dimensions
from experiments.jpeg_capacity import seal
from experiments.jpeg_carrier import embed
from experiments.message_cli import recover_message


class WideResizeTests(unittest.TestCase):
    def test_dimension_candidates_cover_floor_and_nearest(self):
        for length in range(300, 520):
            for percent in (50, 67, 73, 80, 87, 95):
                scale = percent / 100
                floor_size = length * percent // 100
                nearest_size = round(length * percent / 100)
                self.assertIn(length, resize_dimensions(floor_size, scale, False))
                self.assertIn(length, resize_dimensions(nearest_size, scale, True))

    def test_wide_mode_recovers_unlisted_scale(self):
        image = Image.new("RGB", (480, 400), "#647080")
        password = b"benchmark"
        marked = embed(image, seal(b"wide", password), 3, 3)
        resized = marked.resize((350,292), Image.Resampling.LANCZOS)
        with self.assertRaises(ValueError):
            recover_message(resized, password, try_resize=True)
        self.assertEqual(recover_message(resized, password, wide_resize=True), b"wide")
