from importlib.util import find_spec
import unittest

if any(find_spec(name) is None for name in ("cryptography", "reedsolo")):
    raise unittest.SkipTest("Install the tiled experiment extra")

import numpy as np
from PIL import Image

from experiments.luminance import embed, extract


class JPEGCarrierTests(unittest.TestCase):
    def test_odd_sized_image_preserves_grid_and_rgb_bound(self):
        rng = np.random.default_rng(401)
        source = rng.integers(0, 256, (319, 401, 3), dtype=np.uint8)
        frame = bytes(range(60))
        marked = embed(Image.fromarray(source), frame, spacing=2, repetitions=3)
        self.assertEqual(marked.size, (401, 319))
        self.assertLessEqual(np.abs(np.asarray(marked, dtype=np.int16) - source).max(), 2)
        self.assertEqual(extract(marked, spacing=2, repetitions=3), frame)

    def test_dithered_lattice_roundtrip_at_same_pixel_bound(self):
        rng = np.random.default_rng(717)
        source = rng.integers(0, 256, (319, 401, 3), dtype=np.uint8)
        frame = bytes(range(60))
        phase = rng.uniform(0, 2, 60 * 8 * 3)
        marked = embed(Image.fromarray(source), frame, 3, 3, phase=phase)
        self.assertLessEqual(np.abs(np.asarray(marked, dtype=np.int16) - source).max(), 2)
        self.assertEqual(extract(marked, 3, 3, phase=phase), frame)
        self.assertNotEqual(extract(marked, 3, 3), frame)

    def test_small_image_fails_cleanly(self):
        with self.assertRaises(ValueError):
            extract(Image.new("RGB", (32, 32)), spacing=2, repetitions=3)
