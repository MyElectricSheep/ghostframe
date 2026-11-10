from importlib.util import find_spec
import unittest

if any(find_spec(name) is None for name in ("cryptography", "reedsolo")):
    raise unittest.SkipTest("Install the tiled experiment extra")

from reedsolo import RSCodec

from experiments.tiled_ecc import DATA_BYTES, PARITY_BYTES, decode_frame, seal


class TiledECCTests(unittest.TestCase):
    def test_corrects_seven_symbols_before_authentication(self):
        password = b"benchmark test"
        frame = seal(b"!", password)
        self.assertEqual(len(frame), DATA_BYTES)
        codeword = RSCodec(PARITY_BYTES).encode(frame)
        for index in range(7):
            codeword[index] ^= 0xA5
        message, positions = decode_frame(codeword, password)
        self.assertEqual(message, b"!")
        self.assertEqual(set(positions), set(range(7)))
        with self.assertRaises(ValueError):
            decode_frame(codeword, password, correct=False)
        with self.assertRaises(ValueError):
            decode_frame(codeword, b"wrong password")
        codeword[7] ^= 0xA5
        with self.assertRaises(ValueError):
            decode_frame(codeword, password)

    def test_payload_size(self):
        with self.assertRaises(ValueError):
            seal(b"two bytes or more", b"password")
        with self.assertRaises(ValueError):
            decode_frame(bytes(59), b"password")
