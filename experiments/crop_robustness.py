"""Paired crop experiment. Run from the repository root as a module."""
import hashlib
import json
from pathlib import Path
from time import perf_counter

import numpy as np
from skimage.metrics import peak_signal_noise_ratio, structural_similarity
import torch

from ghostframe import decode, encode, load_model, read_image, transforms

# Retained fraction, relative horizontal offset, relative vertical offset.
TRAIN = ((0.90, 0, 0), (0.90, 1, 0), (0.90, 0, 1), (0.90, 1, 1))
HELD_OUT = {
    "center90": (0.90, .5, .5),
    "left92": (0.92, 0, .5),
    "bottom92": (0.92, .5, 1),
    "upper_right88": (0.88, .8, .2),
    "lower_left88": (0.88, .2, .8),
}
COVERS = ("grace_hopper.jpg", "china.jpg", "flower.jpg", "china-sky.png")
BUDGET = 2
STEPS = 100


def box(size, spec):
    width, height = size
    fraction, x, y = spec
    kept_width, kept_height = round(width * fraction), round(height * fraction)
    left, top = round((width - kept_width) * x), round((height - kept_height) * y)
    return left, top, left + kept_width, top + kept_height


def main():
    torch.set_num_threads(4)
    model = load_model("cpu")
    out = Path("benchmarks/crop-robustness")
    out.mkdir(parents=True, exist_ok=True)
    records = []
    for cover in COVERS:
        image = read_image(Path("examples") / cover)
        clean = np.asarray(image)
        train_boxes = [box(image.size, spec) for spec in TRAIN]
        held_out = {name: box(image.size, spec) for name, spec in HELD_OUT.items()}
        assert set(train_boxes).isdisjoint(held_out.values())
        for length in (16, 32):
            for trial in range(3):
                key = f"ghostframe-crop-eval-{trial}"
                digest = hashlib.sha256(f"{cover}/{length}/{trial}".encode()).digest()
                bits = "".join(f"{byte:08b}" for byte in digest)[:length]
                for method, crops in (("baseline", ()), ("crop_aware", train_boxes)):
                    started = perf_counter()
                    marked = encode(image, bits, key, model, epsilon=BUDGET, steps=STEPS, crops=crops)
                    elapsed = perf_counter() - started
                    path = out / f"{Path(cover).stem}-{length}-{trial}-{method}.png"
                    marked.save(path)
                    marked = read_image(path)
                    pixels = np.asarray(marked)
                    cases = {"png": marked}
                    cases.update({name: marked.crop(coords) for name, coords in held_out.items()})
                    cases.update({name: transformed for name, transformed in transforms(marked)
                                  if name in ("jpeg70_420", "resize_75pct")})
                    cases.update({f"train_{i}": marked.crop(coords)
                                  for i, coords in enumerate(train_boxes)})
                    recovered = {name: decode(case, key, length, model) for name, case in cases.items()}
                    errors = {name: sum(a != b for a, b in zip(bits, result))
                              for name, result in recovered.items()}
                    record = dict(cover=cover, length=length, trial=trial, key=key, target=bits,
                                  method=method, file=path.name, seconds=elapsed, errors=errors,
                                  recovered=recovered,
                                  max_delta=int(np.abs(pixels.astype(np.int16) - clean).max()),
                                  psnr=float(peak_signal_noise_ratio(clean, pixels)),
                                  ssim=float(structural_similarity(clean, pixels, channel_axis=-1)))
                    records.append(record)
                    print(cover, length, trial, method, round(elapsed, 2), errors, flush=True)
                    report = dict(budget=BUDGET, steps=STEPS, threads=4, training_crops=TRAIN,
                                  held_out_crops=HELD_OUT, records=records)
                    pending = out / "results.tmp"
                    pending.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
                    pending.replace(out / "results.json")


if __name__ == "__main__":
    main()
