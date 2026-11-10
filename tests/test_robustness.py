from importlib.util import find_spec
import unittest

if any(find_spec(name) is None for name in ("cryptography", "reedsolo")):
    raise unittest.SkipTest("Install the tiled experiment extra")

import numpy as np
from PIL import Image
from reedsolo import RSCodec

from experiments.jpeg_capacity import FRAME_BYTES, seal, unseal
from experiments.jpeg_carrier import embed, extract
from experiments.robustness import candidate


class RobustnessTests(unittest.TestCase):
    def test_original_grid_recovers_asymmetric_crop(self):
        source = Image.fromarray(np.full((400, 480, 3), 100, dtype=np.uint8))
        codec = RSCodec(14)
        data = bytes(range(46))
        marked = embed(source, codec.encode(data), 3, 3)
        cropped = marked.crop((11, 19, 463, 385))
        received, erasures = candidate(cropped, marked.size, (11, 19))
        self.assertEqual(bytes(codec.decode(received, erase_pos=erasures)[0]), data)

    def test_larger_frame_and_wrong_password(self):
        password = b"benchmark test"
        message = b"x" * 26
        codeword = seal(message, password)
        self.assertEqual(len(codeword), FRAME_BYTES)
        source = Image.new("RGB", (480, 400), "#646464")
        marked = embed(source, codeword, 3, 3)
        received = extract(marked, 3, 3, FRAME_BYTES)
        self.assertEqual(unseal(received, password), message)
        with self.assertRaises(ValueError):
            unseal(received, b"wrong password")
        with self.assertRaises(ValueError):
            seal(b"x" * 27, password)
