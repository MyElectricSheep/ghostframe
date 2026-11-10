"""Evaluate JPEG encoder candidates with the actual Ghostframe v3 frame."""
import argparse
from functools import lru_cache
import hashlib
import io
import json
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

import numpy as np
from PIL import Image, ImageOps

from experiments import jpeg_frame
from experiments.frame_keys import PASSWORD
from experiments.jpeg_roundtrip_search import (
    BITS, DENSE, LOW_GRID, PROFILES, REPETITIONS, SHIFTS, TRAIN, block_mean, choose, jpeg, views,
)
from experiments.luminance import embed, extract, luminance, positions

MESSAGES = (b"Meet at the station at 6.", "Caf\u00e9 amanh\u00e3?".encode())
OUTPUT = Path("benchmarks/jpeg-authenticated-holdout.json")


def transcode(image, fmt, **options):
    buffer = io.BytesIO()
    image.save(buffer, fmt, **options)
    buffer.seek(0)
    with Image.open(buffer) as decoded:
        return decoded.convert("RGB")


def evaluate(view, codeword, message, y, x, spacing, offset):
    if np.all(spacing == 3) and not offset.any():
        received = extract(view, 3, REPETITIONS, jpeg_frame.FRAME_BYTES)
    else:
        scores = np.cos(np.pi * block_mean(view, y, x) / spacing - np.pi * offset)
        received = np.packbits(scores.sum(axis=0) < 0).tobytes()
    recovered = None
    try:
        recovered = jpeg_frame.unseal(received, PASSWORD)
    except ValueError:
        pass
    return dict(authenticated=recovered == message,
                byte_errors=sum(a != b for a, b in zip(received, codeword, strict=True)))


def run(path):
    with Image.open(path) as original:
        cover = ImageOps.contain(original.convert("RGB"), (512, 512), Image.Resampling.LANCZOS)
    # Retain aspect ratio for normal images. Enlarge narrow fixtures only
    # enough to fit the same fixed frame and replication count.
    while cover.width // 8 * (cover.height // 8) < BITS * REPETITIONS:
        cover = cover.resize(tuple(max(n + 1, round(n * 1.1)) for n in cover.size), Image.Resampling.LANCZOS)
    pixels = np.asarray(cover)
    y, x = (axis.reshape(REPETITIONS, BITS, *axis.shape[1:])
            for axis in positions(cover.size, REPETITIONS, BITS))
    options = np.clip(pixels[y, x][:, :, None].astype(np.int16)
                      + SHIFTS[:, None, None, None], 0, 255).astype(np.uint8)
    clean = luminance(options).mean(axis=(-2, -1))
    start = perf_counter()
    trials = []
    for index in range(len(SHIFTS)):
        candidate = pixels.copy()
        candidate[y, x] = options[:, :, index]
        trials.append(Image.fromarray(candidate))
    measured = {quality: np.stack([block_mean(jpeg(trial, quality), y, x)
                                   for trial in trials], axis=-1) for quality in LOW_GRID}
    probe_seconds = perf_counter() - start
    rows = []
    for index, message in enumerate(MESSAGES):
        codeword = jpeg_frame.seal(message, PASSWORD)
        targets = np.unpackbits(np.frombuffer(codeword, dtype=np.uint8))[:, None]
        for profile, (spacings, phases, mode) in PROFILES.items():
            start = perf_counter()
            spacing = np.array(spacings)[:, None, None]
            offset = np.array(phases)[:, None, None]
            if profile == "baseline":
                marked = embed(cover, codeword, 3, REPETITIONS)
            else:
                levels = clean / spacing - offset
                nearest = 2 * np.round((levels - targets) / 2) + targets
                training = {"dense": DENSE, "low_grid": LOW_GRID}.get(mode, TRAIN)
                samples = np.stack([clean, *(measured[q] for q in training)])
                margins = np.cos(np.pi * (samples / spacing - offset - targets))
                shifts = choose(margins, abs(levels - nearest), mode)
                result = pixels.copy()
                result[y, x] = options[np.arange(REPETITIONS)[:, None], np.arange(BITS), shifts]
                marked = Image.fromarray(result)
            seconds = perf_counter() - start
            delta = np.asarray(marked).astype(np.int16) - pixels
            max_delta = int(abs(delta).max())
            assert max_delta <= 2
            channels = dict(views(marked))
            channels["png"] = transcode(marked, "PNG")
            channels["jpeg444_q50"] = transcode(marked, "JPEG", quality=50, subsampling=0)
            channels["webp75"] = transcode(marked, "WEBP", quality=75)
            cases = {name: evaluate(view, codeword, message, y, x, spacing[..., 0], offset[..., 0])
                     for name, view in channels.items()}
            # An authenticated but different plaintext would indicate a benchmark bug.
            assert jpeg_frame.unseal(codeword, PASSWORD) == message
            rows.append(dict(cover=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                             dimensions=cover.size, frame=index, profile=profile, cases=cases,
                             max_delta=max_delta, mse=float(np.mean(delta.astype(float) ** 2)),
                             encode_seconds=seconds,
                             shared_probe_seconds=probe_seconds if mode != "clean" else 0))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("covers", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    rows = []
    # Cache only within this benchmark process. The scrypt output is identical.
    with patch.object(jpeg_frame, "derive", lru_cache(maxsize=32)(jpeg_frame.derive)):
        for path in args.covers:
            rows.extend(run(path))
            args.output.write_text(json.dumps(rows, indent=2) + "\n")
            print(path.name, flush=True)


if __name__ == "__main__":
    main()
