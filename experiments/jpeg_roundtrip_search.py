"""Compare compressor-in-the-loop and diverse luminance replicas."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np
from PIL import Image

from experiments.jpeg_window_pilot import BITS, REPETITIONS, ROOT, jpeg, luma

OUTPUT = Path("benchmarks/jpeg-roundtrip-search.json")
TRAIN = (85, 70, 50, 35)
DENSE = tuple(range(35, 96, 5))
LOW_GRID = tuple(sorted(set(DENSE) | set(range(35, 46, 2))))
QUALITIES = (95, 85, 80, 70, 60, 50, 42, 41, 40, 39, 38, 35)
SHIFTS = np.arange(-2, 3)
COMBINATIONS = np.array(list(itertools.product(range(len(SHIFTS)), repeat=REPETITIONS)))
PROFILES = {
    "baseline": ((3, 3, 3), (0, 0, 0), "clean"),
    "mixed_spacing": ((2.5, 3, 3.5), (0, 0, 0), "clean"),
    "mixed_phase": ((3, 3, 3), (0, 2/3, 4/3), "clean"),
    "actual_independent": ((3, 3, 3), (0, 0, 0), "independent"),
    "actual_joint": ((3, 3, 3), (0, 0, 0), "joint"),
    "actual_joint_dense": ((3, 3, 3), (0, 0, 0), "dense"),
    "actual_joint_low_grid": ((3, 3, 3), (0, 0, 0), "low_grid"),
    "actual_joint_diverse": ((2.5, 3, 3.5), (0, 2/3, 4/3), "joint"),
}


def block_mean(image, y, x):
    return luma(np.asarray(image)[y, x]).mean(axis=(-1, -2))


def views(image):
    yield "png", image
    for quality in QUALITIES:
        yield str(quality), jpeg(image, quality)
    yield "95_then_50", jpeg(jpeg(image, 95), 50)
    small = image.resize(tuple(round(n * .75) for n in image.size), Image.Resampling.LANCZOS)
    yield "resize75_jpeg70", jpeg(small, 70).resize(image.size, Image.Resampling.LANCZOS)


def choose(margins, distances, mode):
    penalty = abs(SHIFTS) * 1e-6
    if mode == "clean":
        return (distances + penalty).argmin(axis=-1)
    if mode == "independent":
        return (margins.min(axis=0) + .2 * margins.mean(axis=0) - penalty).argmax(axis=-1)
    combined = sum(margins[:, replica, :, :][..., COMBINATIONS[:, replica]]
                   for replica in range(REPETITIONS))
    cost = abs(SHIFTS[COMBINATIONS]).sum(axis=1)
    score = combined.min(axis=0) + .2 * combined.mean(axis=0) - .02 * cost
    # Preserve clean recovery whenever a valid combination exists.
    clean_valid = combined[0] > 0
    score -= 10 * (~clean_valid & clean_valid.any(axis=-1, keepdims=True))
    return COMBINATIONS[score.argmax(axis=-1)].T


def run(path, seed_suffix):
    with Image.open(path) as image:
        cover = image.convert("RGB")
    pixels = np.asarray(cover)
    width, height = cover.width // 8, cover.height // 8
    if width * height < BITS * REPETITIONS:
        return []
    seed = int.from_bytes(hashlib.sha256((path.name + seed_suffix).encode()).digest()[:8], "big")
    rng = np.random.default_rng(seed)
    indices = rng.permutation(width * height)[:BITS * REPETITIONS].reshape(REPETITIONS, BITS)
    y = (indices // width * 8)[..., None, None] + np.arange(8)[None, :, None]
    x = (indices % width * 8)[..., None, None] + np.arange(8)[None, None, :]
    targets = rng.integers(0, 2, BITS)
    options = np.clip(pixels[y, x][..., None, :, :, :].astype(np.int16)
                      + SHIFTS[:, None, None, None], 0, 255).astype(np.uint8)
    clean = luma(options).mean(axis=(-1, -2))
    measured = {}
    candidates = []
    for index in range(len(SHIFTS)):
        trial = pixels.copy()
        trial[y, x] = options[:, :, index]
        candidates.append(Image.fromarray(trial))
    for quality in LOW_GRID:
        measured[quality] = np.stack([block_mean(jpeg(trial, quality), y, x)
                                      for trial in candidates], axis=-1)
    results = []
    for profile, (spacings, phases, mode) in PROFILES.items():
        spacing = np.array(spacings)[:, None, None]
        offset = np.array(phases)[:, None, None]
        levels = clean / spacing - offset
        nearest = 2 * np.round((levels - targets[:, None]) / 2) + targets[:, None]
        training = {"dense": DENSE, "low_grid": LOW_GRID}.get(mode, TRAIN)
        samples = np.stack([clean, *(measured[quality] for quality in training)])
        margins = np.cos(np.pi * (samples / spacing - offset - targets[:, None]))
        chosen = choose(margins, abs(levels - nearest), mode)
        marked = pixels.copy()
        marked[y, x] = options[np.arange(REPETITIONS)[:, None], np.arange(BITS), chosen]
        delta = marked.astype(np.int16) - pixels
        assert abs(delta).max() <= 2
        errors = {}
        for label, view in views(Image.fromarray(marked)):
            confidence = np.cos(np.pi * (block_mean(view, y, x) / spacing[..., 0] - offset[..., 0]))
            errors[label] = int(np.count_nonzero((confidence.sum(axis=0) < 0) != targets))
        results.append(dict(cover=path.stem, profile=profile, bit_errors=errors,
                            mse=float(np.mean(delta.astype(float) ** 2))))
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-suffix", default="")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    rows = [row for path in sorted(ROOT.glob("*.png")) for row in run(path, args.seed_suffix)]
    args.output.write_text(json.dumps(rows, indent=2) + "\n")


if __name__ == "__main__":
    main()
