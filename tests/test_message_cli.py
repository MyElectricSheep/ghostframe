from importlib.util import find_spec
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

if any(find_spec(name) is None for name in ("cryptography", "reedsolo")):
    raise unittest.SkipTest("Install the tiled experiment extra")

from PIL import Image, ImageEnhance

from experiments.jpeg_capacity import seal
from experiments.jpeg_carrier import embed
from experiments.message_cli import encode_file, recover_message
from ghostframe import read_image


class MessageCLITests(unittest.TestCase):
    def test_jpeg_file_preserves_binary_message_and_refuses_overwrite(self):
        source = Image.new("RGB", (480, 400), "#647080")
        payload = b"\0local message\xff"
        password = b"benchmark passphrase"
        with TemporaryDirectory() as directory:
            output = Path(directory)/"marked.jpg"
            encode_file(source, payload, password, output)
            contents = output.read_bytes()
            self.assertEqual(recover_message(read_image(output),password), payload)
            with self.assertRaises(FileExistsError):
                encode_file(source,b"different",password,output)
            self.assertEqual(output.read_bytes(),contents)
            with self.assertRaises(ValueError):
                recover_message(read_image(output),b"wrong")

    def test_failed_encode_leaves_no_output(self):
        with TemporaryDirectory() as directory:
            output = Path(directory)/"marked.png"
            with self.assertRaises(ValueError):
                encode_file(Image.new("RGB",(32,32)),b"x",b"passphrase",output)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_exposure_search_authenticates_scaled_brightness(self):
        source = Image.new("RGB", (480, 400), "#647080")
        password = b"benchmark passphrase"
        marked = embed(source, seal(b"exposure", password), 3, 3)
        changed = ImageEnhance.Brightness(marked).enhance(1.05)
        self.assertEqual(recover_message(changed, password, try_exposure=True), b"exposure")
        with self.assertRaises(ValueError):
            recover_message(changed, b"wrong", try_exposure=True)

    def test_crop_then_resize_recovers_without_crop_offset(self):
        source = Image.new("RGB", (480, 400), "#647080")
        password = b"benchmark passphrase"
        marked = embed(source, seal(b"compound", password), 3, 3)
        cropped = marked.crop((13, 21, 463, 391))
        changed = cropped.resize((337, 277), Image.Resampling.LANCZOS)
        self.assertEqual(recover_message(changed, password, original_size=source.size,
                                         crop_size=cropped.size, soft=True), b"compound")

    def test_crop_dimensions_require_valid_original_dimensions(self):
        image = Image.new("RGB", (32, 32))
        with self.assertRaisesRegex(ValueError, "requires original dimensions"):
            recover_message(image, b"password", crop_size=(32, 32))
        with self.assertRaisesRegex(ValueError, "fit within"):
            recover_message(image, b"password", original_size=(48, 48), crop_size=(49, 32))
