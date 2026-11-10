from pathlib import Path
import tempfile
import unittest

import numpy as np
from PIL import Image
import torch

from experiments.crop_robustness import HELD_OUT, TRAIN, box
from ghostframe import decode, encode, load_model, projections, read_image


class ChannelTests(unittest.TestCase):
    def test_projection_protocol(self):
        matrix = projections("test-key", 32)
        self.assertTrue(torch.equal(matrix[:16], projections("test-key", 16)))
        self.assertFalse(torch.equal(matrix, projections("other-key", 32)))
        torch.testing.assert_close(matrix.norm(dim=1), torch.ones(32))

    def test_crop_split_has_no_overlapping_boxes(self):
        for filename in ("grace_hopper.jpg", "china.jpg", "flower.jpg", "china-sky.png"):
            size = read_image(Path(__file__).parents[1] / "examples" / filename).size
            training = {box(size, spec) for spec in TRAIN}
            evaluation = {box(size, spec) for spec in HELD_OUT.values()}
            self.assertEqual(len(training), len(TRAIN))
            self.assertEqual(len(evaluation), len(HELD_OUT))
            self.assertTrue(training.isdisjoint(evaluation))

    def test_crop_optimizer_respects_rgb_budget(self):
        torch.set_num_threads(4)
        model = load_model("cpu")
        source = Path(__file__).parents[1] / "examples" / "china-sky.png"
        image = read_image(source)
        crop = box(image.size, TRAIN[0])
        for stride in (1, 4):
            marked = encode(image, "1010110011010010", "test-key", model,
                            steps=3, epsilon=2, crops=[crop], delta_stride=stride)
            self.assertEqual(marked.size, image.size)
            difference = np.asarray(marked, dtype=np.int16) - np.asarray(image, dtype=np.int16)
            self.assertLessEqual(np.abs(difference).max(), 2)

    def test_pretrained_png_roundtrip(self):
        torch.set_num_threads(4)
        model = load_model("cpu")
        self.assertFalse(model.training)
        self.assertFalse(any(parameter.requires_grad for parameter in model.parameters()))
        image = read_image(Path(__file__).parents[1] / "examples" / "grace_hopper.jpg")
        target = "1010110011010010"
        marked = encode(image, target, "test-key", model)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "encoded.png"
            marked.save(path)
            self.assertEqual(decode(read_image(path), "test-key", 16, model), target)
            self.assertNotEqual(decode(read_image(path), "wrong-key", 16, model), target)
            with self.assertRaises(ValueError):
                encode(image, "0102", "test-key", model)

class InputContractTests(unittest.TestCase):
    def test_embedding_preprocessing_matches_protocol(self):
        from ghostframe import embedding, tensor

        image = Image.new("RGB", (17, 19), (25, 127, 231))
        expected = (torch.tensor([25., 127., 231.]) / 255
                    - torch.tensor([.485, .456, .406])) / torch.tensor([.229, .224, .225])
        actual = embedding(torch.nn.Identity(), tensor(image, "cpu"))[0]
        torch.testing.assert_close(actual, expected / expected.norm())

    def test_image_format_and_dimension_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture"
            for size in ((15, 100), (2001, 2000)):
                Image.new("RGB", size).save(path, format="PNG")
                with self.assertRaises(ValueError):
                    read_image(path)
            Image.new("RGB", (64, 64)).save(path, format="BMP")
            with self.assertRaises(OSError):
                read_image(path)


if __name__ == "__main__":
    unittest.main()
