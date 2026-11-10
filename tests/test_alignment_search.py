from importlib.util import find_spec
import unittest

if any(find_spec(name) is None for name in ("cryptography", "reedsolo")):
    raise unittest.SkipTest("Install the tiled experiment extra")

import numpy as np
from PIL import Image
from reedsolo import RSCodec

from experiments.alignment_search import block_phases, grid_phases, search_crop, search_resize
from experiments.jpeg_carrier import embed, positions
from experiments.robustness import aligned_scores
from experiments.tiled import PASSWORD
from experiments.tiled_ecc import MESSAGE, PARITY_BYTES, seal


class AlignmentSearchTests(unittest.TestCase):
    def test_integral_matches_reference_scores(self):
        rng = np.random.default_rng(19)
        image = Image.fromarray(rng.integers(30, 220, (384, 421, 3), dtype=np.uint8))
        y, x = positions(image.size, 3)
        reference, _ = aligned_scores(image)
        actual = block_phases(image)[y[:, 0, 0], x[:, 0, 0]]
        np.testing.assert_allclose(actual, reference.ravel(), atol=1e-8)
        np.testing.assert_allclose(grid_phases(image), block_phases(image)[::8, ::8], atol=1e-8)

    def test_off_center_crop_recovers_authenticated_frame(self):
        cover = Image.new("RGB", (480, 400), "#647080")
        frame = RSCodec(PARITY_BYTES).encode(seal(MESSAGE, PASSWORD))
        marked = embed(cover, frame, 3, 3)
        crop = marked.crop((11, 19, 463, 385))
        result = search_crop(crop, marked.size)
        self.assertTrue(result["authenticated"])
        self.assertEqual(result["geometry"]["offset"], (11, 19))
        self.assertFalse(search_crop(cover.crop((11,19,463,385)), cover.size)["authenticated"])

    def test_unknown_original_size_recovers_listed_resize(self):
        cover = Image.new("RGB", (480, 400), "#647080")
        frame = RSCodec(PARITY_BYTES).encode(seal(MESSAGE, PASSWORD))
        marked = embed(cover, frame, 3, 3)
        resized = marked.resize((360,300), Image.Resampling.LANCZOS)
        result = search_resize(resized)
        self.assertTrue(result["authenticated"])
        self.assertEqual(result["geometry"]["size"], cover.size)
