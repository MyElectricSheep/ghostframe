"""Screen spatial windows under a two-level RGB cap on bundled fixtures."""
import hashlib
import io
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path("benchmarks/jpeg-carrier")
OUTPUT = Path("benchmarks/jpeg-window-pilot.json")
BITS = 768
REPETITIONS = 3
WINDOWS = {
    "flat": np.ones(8),
    "inset": np.array([0, 1, 1, 1, 1, 1, 1, 0]),
    "taper": np.array([.5, .5, 1, 1, 1, 1, .5, .5]),
}


def jpeg(image, quality):
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=quality)
    buffer.seek(0)
    with Image.open(buffer) as decoded:
        return decoded.convert("RGB")


def dc_step(quality):
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8)).save(buffer, "JPEG", quality=quality)
    buffer.seek(0)
    with Image.open(buffer) as encoded:
        return encoded.quantization[0][0] / 8


def luma(pixels):
    return pixels @ np.array([.299, .587, .114])


def phase(blocks, window):
    weights = np.outer(window, window)
    return (luma(blocks) * weights).sum(axis=(-2, -1)) / weights.sum()


def main():
    rows = []
    dc_steps = np.array([dc_step(quality) for quality in (85, 70, 50, 35)])
    for path in sorted(ROOT.glob("*.png")):
        with Image.open(path) as image:
            cover = image.convert("RGB")
        pixels = np.array(cover)
        width, height = cover.width // 8, cover.height // 8
        if width * height < BITS * REPETITIONS:
            continue
        # Use a separate block permutation from the source fixture's carrier.
        seed = int.from_bytes(hashlib.sha256(path.name.encode()).digest()[:8], "big")
        rng = np.random.default_rng(seed)
        indices = rng.permutation(width * height)[:BITS * REPETITIONS]
        y = (indices // width * 8)[:, None, None] + np.arange(8)[None, :, None]
        x = (indices % width * 8)[:, None, None] + np.arange(8)[None, None, :]
        targets = rng.integers(0, 2, BITS)
        repeated = np.tile(targets, REPETITIONS)[:, None]
        profiles = [(name, window, False) for name, window in WINDOWS.items()]
        profiles.append(("flat-jpeg-aware", WINDOWS["flat"], True))
        for name, window, jpeg_aware in profiles:
            # Preserve the full cap at the center of each taper.
            mask = np.minimum.outer(window, window)
            shifts = np.rint(np.arange(-2, 3)[:, None, None] * mask).astype(np.int16)
            options = np.clip(pixels[y, x][:, None].astype(np.int16) + shifts[..., None], 0, 255)
            means = phase(options, window)
            for spacing in (2, 2.5, 3, 3.5, 4):
                levels = means / spacing
                nearest = 2 * np.round((levels - repeated) / 2) + repeated
                cost = abs(levels - nearest)
                if jpeg_aware:
                    # Approximate how libjpeg quantizes the block average.
                    quantized = np.round((means[..., None] - 128) / dc_steps) * dc_steps + 128
                    margin = np.cos(np.pi * (quantized / spacing - repeated[..., None]))
                    clean_margin = np.cos(np.pi * (levels - repeated))
                    score = np.minimum(clean_margin, margin.min(axis=-1))
                    cost = -score - .1 * margin.mean(axis=-1) + .15 * cost
                chosen = (cost + abs(np.arange(-2, 3)) * 1e-6).argmin(axis=1)
                marked = pixels.copy()
                marked[y, x] = options[np.arange(len(chosen)), chosen]
                delta = marked.astype(np.int16) - pixels
                assert abs(delta).max() <= 2
                stego = Image.fromarray(marked)
                errors = {}
                for quality in (None, 95, 85, 80, 70, 60, 50, 40, 35):
                    view = stego if quality is None else jpeg(stego, quality)
                    confidence = np.cos(np.pi * phase(np.asarray(view)[y, x], window) / spacing)
                    predicted = confidence.reshape(REPETITIONS, BITS).sum(axis=0) < 0
                    errors[str(quality or "png")] = int(np.count_nonzero(predicted != targets))
                rows.append(dict(cover=path.stem, window=name, spacing=spacing,
                                 mse=float(np.mean(delta.astype(float) ** 2)), bit_errors=errors))
        print(path.stem, flush=True)
    OUTPUT.write_text(json.dumps(rows, indent=2) + "\n")


if __name__ == "__main__":
    main()
