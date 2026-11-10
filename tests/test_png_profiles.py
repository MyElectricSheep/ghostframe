from importlib.util import find_spec
import io
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

if any(find_spec(name) is None for name in ("cryptography", "reedsolo")):
    raise unittest.SkipTest("Install the tiled experiment extra")

import numpy as np
from PIL import Image, ImageCms

from ghostframe_png import core
from ghostframe_png.core import PROFILES, Profile

ROOT = Path(__file__).resolve().parents[1]
PASS = b"unit test passphrase"


def profile(**kw):
    base = dict(name="test", cols=6, rows=5, bits=12, parity=10, epsilon=8)
    base.update(kw)
    p = Profile(**base)
    p.validate()
    return p


class FrameTests(unittest.TestCase):
    def test_capacity_arithmetic_and_registered_profiles(self):
        self.assertEqual(PROFILES["png-l2-c10x8b12"].capacity, 120 - 24 - 33)
        self.assertEqual(PROFILES["png-l8-c10x8b24"].capacity, 240 - 32 - 33)
        two_blocks = profile(cols=10, rows=8, bits=40, parity=64)
        self.assertEqual(two_blocks.blocks, 2)
        self.assertEqual(two_blocks.block_layout(), [(200, 32), (200, 32)])
        self.assertEqual(two_blocks.length_bytes, 2)
        self.assertEqual(two_blocks.capacity, 400 - 64 - 34)
        with self.assertRaises(ValueError):
            profile(bits=11, cols=1, rows=1).validate()

    def test_exact_boundaries_binary_and_empty(self):
        p = profile()
        for message in (b"", bytes([0]), bytes(range(p.capacity)), "é✓".encode()[:p.capacity]):
            frame = core.seal(message, PASS, p)
            self.assertEqual(len(frame), p.frame_bytes)
            self.assertEqual(core.open_frame(frame, PASS, p), message)
        with self.assertRaises(core.CapacityError):
            core.seal(bytes(p.capacity + 1), PASS, p)
        with self.assertRaises(core.InputError):
            core.seal(b"x", b"", p)

    def test_fresh_salt_and_binding(self):
        p, q = profile(), profile(name="other")
        a, b = core.seal(b"hi", PASS, p), core.seal(b"hi", PASS, p)
        self.assertNotEqual(a[:16], b[:16])
        for wrong in ((a, b"wrong", p), (a, PASS, q)):
            with self.assertRaises(core.DecodeError):
                core.open_frame(*wrong)
        tampered = bytearray(a)
        tampered[-1] ^= 1
        with self.assertRaises(core.DecodeError):
            core.open_frame(bytes(tampered), PASS, p)

    def test_interleaved_rs_corrects_within_budget_and_rejects_beyond(self):
        p = profile(cols=10, rows=8, bits=32, parity=48)  # two blocks of 160 bytes, 24 parity each
        frame = core.seal(b"payload", PASS, p)
        codeword = bytearray(core.rs_encode(frame, p))
        self.assertEqual(len(codeword), p.codeword_bytes)
        confidence = np.ones(len(codeword))
        for i in range(24):  # 12 errors per block after interleaving
            codeword[i] ^= 0x5A
        frame0, corrected, _ = next(core.rs_candidates(bytes(codeword), confidence, p, levels=(0,)))
        self.assertEqual(core.open_frame(frame0, PASS, p), b"payload")
        self.assertEqual(corrected, 24)
        for i in range(24, 26):
            codeword[i] ^= 0x5A
        self.assertFalse(any(core.open_frame(f, PASS, p) == b"payload" if self._authentic(f, p) else False
                             for f, _, _ in core.rs_candidates(bytes(codeword), confidence, p, levels=(0,))))
        # Low confidence on the damaged bytes lets erasures repair up to the parity budget.
        confidence[:26] = 0
        self.assertTrue(any(self._authentic(f, p) for f, _, _ in core.rs_candidates(bytes(codeword), confidence, p)))

    @staticmethod
    def _authentic(frame, p):
        try:
            core.open_frame(frame, PASS, p)
            return True
        except core.DecodeError:
            return False


class InputContractTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.path = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def save(self, image, name, **kw):
        path = self.path / name
        image.save(path, **kw)
        return path

    def test_rejects_unsupported_inputs(self):
        cases = {
            "transparent.png": Image.new("RGBA", (64, 64), (1, 2, 3, 0)),
            "deep.png": Image.fromarray(np.full((64, 64), 40000, np.uint16)),
            "cmyk.jpg": Image.new("CMYK", (64, 64)),
        }
        for name, image in cases.items():
            with self.subTest(name), self.assertRaises(core.InputError):
                core.load_cover(self.save(image, name))
        with self.assertRaises(core.InputError):
            core.load_cover(self.save(Image.new("RGB", (64, 64)), "x.bmp", format="BMP"))
        with self.assertRaises(core.InputError):
            core.load_png(self.save(Image.new("RGB", (64, 64)), "x.jpg"))
        with self.assertRaises(core.InputError):
            core.load_cover(self.save(Image.new("RGB", (2001, 2000)), "big.png"))

    def test_documented_conversions(self):
        opaque = core.load_cover(self.save(Image.new("RGBA", (32, 32), (9, 8, 7, 255)), "opaque.png"))
        self.assertEqual(opaque[0, 0].tolist(), [9, 8, 7])
        gray = core.load_cover(self.save(Image.new("L", (32, 32), 77), "gray.png"))
        self.assertEqual(gray[0, 0].tolist(), [77, 77, 77])
        srgb = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
        tagged = core.load_cover(self.save(Image.new("RGB", (32, 32), (200, 30, 30)), "s.png", icc_profile=srgb))
        self.assertEqual(tagged[0, 0].tolist(), [200, 30, 30])
        lab = ImageCms.ImageCmsProfile(ImageCms.createProfile("LAB")).tobytes()
        with self.assertRaises(core.InputError):  # A non-RGB profile cannot describe RGB pixels.
            core.load_cover(self.save(Image.new("RGB", (32, 32)), "lab.png", icc_profile=lab))

    def test_output_is_pixels_only_and_never_overwrites(self):
        data = core.png_bytes(np.zeros((8, 8, 3), np.uint8))
        with Image.open(io.BytesIO(data)) as image:
            self.assertNotIn("icc_profile", image.info)
            self.assertNotIn("exif", image.info)
        target = self.path / "out.png"
        core.write_new(target, data)
        with self.assertRaises(FileExistsError):
            core.write_new(target, b"other")
        self.assertEqual(target.read_bytes(), data)
        self.assertEqual(sorted(p.name for p in self.path.iterdir()), ["out.png"])
        with self.assertRaises(core.InputError):
            core.check_output(self.path / "missing" / "x.png")

    def test_too_small_for_grid(self):
        with self.assertRaises(core.InputError):
            core.tile_boxes((79, 160, 3), PROFILES["png-l2-c10x8b12"])
        self.assertEqual(len(core.tile_boxes((128, 160, 3), PROFILES["png-l2-c10x8b12"])), 80)


class CLITests(unittest.TestCase):
    def run_cli(self, *args, stdin=None):
        return subprocess.run([sys.executable, "-m", "ghostframe_png.cli", *args], cwd=ROOT,
                              capture_output=True, input=stdin)

    def test_capacity_and_usage_errors_exit_before_encoding(self):
        with TemporaryDirectory() as directory:
            d = Path(directory)
            (d / "pw").write_bytes(b"pw\n")
            (d / "big").write_bytes(bytes(64))
            result = self.run_cli("encode", "examples/flower.jpg", str(d / "o.png"), "--profile", "png-l2-c10x8b12",
                                  "--message-file", str(d / "big"), "--passphrase-file", str(d / "pw"))
            self.assertEqual(result.returncode, 3)
            self.assertEqual(result.stdout, b"")
            result = self.run_cli("encode", "examples/flower.jpg", str(d / "no" / "o.png"), "--profile",
                                  "png-l2-c10x8b12", "--message-file", str(d / "pw"), "--passphrase-file", str(d / "pw"))
            self.assertEqual(result.returncode, 2)
            result = self.run_cli("decode", "x.png", "--profile", "nope", "--passphrase-file", str(d / "pw"))
            self.assertEqual(result.returncode, 2)
            self.assertEqual(list(p.name for p in d.iterdir() if p.suffix == ".png"), [])


class ModelRoundTripTests(unittest.TestCase):
    def test_png_roundtrip_soft_decode_and_rejections(self):
        import torch
        from ghostframe import load_model

        torch.set_num_threads(4)
        model = load_model("cpu")
        p = profile(epsilon=8, steps=30)
        rng = np.random.default_rng(7)
        cover = np.asarray(Image.open(ROOT / "examples" / "china-sky.png").convert("RGB").resize((192, 160)))
        message = bytes(rng.integers(0, 256, p.capacity, dtype=np.uint8))
        data = core.encode_message(cover, message, PASS, p, model)
        pixels = np.asarray(Image.open(io.BytesIO(data)).convert("RGB"))
        self.assertLessEqual(int(np.abs(pixels.astype(int) - cover).max()), 8)
        self.assertEqual(core.decode_message(pixels, PASS, p, model), message)
        # The same pixels re-serialized at another compression level decode identically.
        recompressed = io.BytesIO()
        Image.fromarray(pixels).save(recompressed, format="PNG", compress_level=0)
        self.assertEqual(core.decode_message(np.asarray(Image.open(recompressed)), PASS, p, model), message)
        for args in ((pixels, b"wrong", p), (cover, PASS, p), (pixels, PASS, profile(name="other"))):
            with self.assertRaises(core.DecodeError):
                core.decode_message(*args, model)
        # Reversing the tile order (all tiles are 32x32 here) is far beyond the parity budget.
        swapped = pixels.copy()
        boxes = core.tile_boxes(swapped.shape, p)
        for (l, t, r, b), (sl, st, sr, sb) in zip(boxes, reversed(boxes)):
            swapped[t:b, l:r] = pixels[st:sb, sl:sr]
        with self.assertRaises(core.DecodeError):
            core.decode_message(swapped, PASS, p, model)


if __name__ == "__main__":
    unittest.main()
