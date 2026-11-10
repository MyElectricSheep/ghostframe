import unittest

from importlib.util import find_spec

if find_spec("cryptography") is None:
    raise unittest.SkipTest("Install the tiled experiment extra")

from experiments.tiled import FRAME_BYTES, open_frame, seal, tile_boxes


class TiledTests(unittest.TestCase):
    def test_frame_authentication(self):
        password = b"test passphrase"
        message = b"Meet at dawn!"
        frame = seal(message, password)
        self.assertEqual(len(frame), FRAME_BYTES)
        self.assertEqual(open_frame(frame, password), message)
        with self.assertRaises(ValueError):
            open_frame(frame, b"wrong password")
        tampered = frame[:-1] + bytes([frame[-1] ^ 1])
        with self.assertRaises(ValueError):
            open_frame(tampered, password)
        with self.assertRaises(ValueError):
            seal(b"x" * 14, password)

    def test_tile_coverage_at_odd_dimensions(self):
        width, height = 451, 301
        boxes = tile_boxes((width, height))
        self.assertEqual(len(boxes), 30)
        self.assertEqual(boxes[0][:2], (0, 0))
        self.assertEqual(boxes[-1][2:], (width, height))
        self.assertEqual(sum((r-l)*(b-t) for l,t,r,b in boxes), width*height)
