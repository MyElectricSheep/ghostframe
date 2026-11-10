from importlib.util import find_spec
from time import perf_counter
import unittest

if any(find_spec(name) is None for name in ("cryptography", "reedsolo")):
    raise unittest.SkipTest("Install the tiled experiment extra")

import numpy as np

from experiments.alignment_search import authenticate_best
from experiments.jpeg_capacity import PARITY_BYTES, seal, unseal


class SoftSearchTests(unittest.TestCase):
    def test_confidence_retries_authenticate_thirteen_damaged_bytes(self):
        password = b"fixture password"
        codeword = seal(b"soft test", password)
        bits = np.unpackbits(np.frombuffer(codeword, dtype=np.uint8))
        scores = np.where(bits, -1., 1.)
        scores[np.arange(13)*8] *= -.01
        scores = np.tile(scores, (3,1))
        seen = np.ones_like(scores, dtype=bool)

        def verify(received, erasures, phrase=password):
            try:
                return unseal(received, phrase, erasures=erasures) == b"soft test"
            except ValueError:
                return False

        candidates = [({}, scores, seen)]
        self.assertFalse(authenticate_best(candidates, perf_counter(), verify, PARITY_BYTES)["authenticated"])
        self.assertTrue(authenticate_best(candidates, perf_counter(), verify, PARITY_BYTES, soft=True)["authenticated"])
        self.assertFalse(authenticate_best(candidates, perf_counter(),
                                           lambda r,e: verify(r,e,b"wrong"),
                                           PARITY_BYTES, soft=True)["authenticated"])
