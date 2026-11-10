"""Color and synthetic display capture tests on authenticated neural PNGs."""
import json

import numpy as np
from PIL import Image, ImageOps
import torch

from experiments.goal_validation import FIXTURES, OUT
from experiments.message_cli import neural_recover
from experiments.robustness import transcode
from experiments.tiled import PASSWORD
from ghostframe import load_model, read_image


def main():
    torch.set_num_threads(4)
    model = load_model("cpu")
    rows = []
    for path, ecc, expected in FIXTURES:
        image = read_image(path)
        rgb = np.asarray(image, dtype=np.float32)
        color = Image.fromarray(np.clip(np.rint(rgb * [1.02, 1, .98]), 0, 255).astype(np.uint8))
        display = ImageOps.contain(image, (400, 400), Image.Resampling.BICUBIC)
        canvas = Image.new("RGB", (800, 600), "#282828")
        canvas.paste(display, (40, 72))
        capture = transcode(canvas, "PNG").crop((40, 72, 40 + display.width, 72 + display.height))
        results = {}
        for label, view in (("color_balance", color), ("synthetic_display_capture", capture)):
            try:
                results[label] = neural_recover(view, PASSWORD, model, ecc=ecc) == expected
            except ValueError:
                results[label] = False
        rows.append(dict(fixture=path, cases=results))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "neural-transform-controls.json").write_text(json.dumps(rows, indent=2) + "\n")
    print(rows)


if __name__ == "__main__":
    main()
