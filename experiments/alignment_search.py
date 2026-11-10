"""Bounded geometry search for the 60-byte luminance profile."""
from fractions import Fraction
import math
import heapq
import json
from pathlib import Path
from time import perf_counter

import numpy as np
from PIL import Image, ImageOps
from skimage import data

from experiments.jpeg_carrier import BITS, BLOCK, OUT as JPEG_OUT, embed, luminance, positions
from experiments.robustness import COPIES, SPACING, recover, transcode
from experiments.tiled_ecc import PARITY_BYTES

OUT = Path("benchmarks/alignment-search")
MAX_TRIM = 64
TOP = 12
SCALES = (.5, .625, .75, .8, .9)
WIDE_SCALES = tuple(sorted({.625, *(percent / 100 for percent in range(50, 96))}))


def block_phases(image):
    values = luminance(np.asarray(image.convert("RGB")))
    integral = np.pad(values.cumsum(axis=0).cumsum(axis=1), ((1, 0), (1, 0)))
    sums = (integral[BLOCK:, BLOCK:] - integral[:-BLOCK, BLOCK:]
            - integral[BLOCK:, :-BLOCK] + integral[:-BLOCK, :-BLOCK])
    return np.cos(np.pi * (sums / BLOCK**2) / SPACING)


def grid_angles(image):
    """Compute the lattice angles of aligned complete blocks."""
    width, height = image.width // BLOCK, image.height // BLOCK
    pixels = np.asarray(image if image.mode == "RGB" else image.convert("RGB"))
    blocks = pixels[:height * BLOCK, :width * BLOCK].reshape(height, BLOCK, width, BLOCK, 3)
    averages = blocks.sum(axis=(1, 3), dtype=np.uint32) / BLOCK**2
    return np.pi * luminance(averages) / SPACING


def grid_phases(image):
    return np.cos(grid_angles(image))


def coherence(scores, seen):
    # Ignore missing replicas and rank by average agreement strength.
    counts = seen.sum(axis=0)
    return float(np.abs(scores.sum(axis=0) / np.maximum(counts, 1)).mean())


def confidence_erasures(scores, missing, parity_bytes):
    """Yield bounded sets of low-confidence byte erasures."""
    order = np.argsort(np.abs(scores).reshape(-1, 8).min(axis=1), kind="stable")
    known = set(missing)
    ranked = [int(index) for index in order if index not in known]
    budget = min(parity_bytes - len(missing), len(ranked))
    if budget > 0:
        for extra in sorted({min(count, budget) for count in (4, 8, 12, 16, 20, 24)}):
            yield [*missing, *ranked[:extra]]


def authenticate_best(hypotheses, start, verify, parity_bytes, soft=False):
    top = []
    checked = 0
    for geometry, scores, seen in hypotheses:
        checked += 1
        missing = (~seen.any(axis=0)).reshape(-1, 8).any(axis=1)
        if missing.sum() > parity_bytes:
            continue
        rank = coherence(scores, seen)
        if len(top) < TOP or rank > top[0][0]:
            summed = scores.sum(axis=0)
            received = np.packbits(summed < 0).tobytes()
            entry = (rank, checked, geometry, received, np.flatnonzero(missing).tolist(), summed)
            if len(top) == TOP:
                heapq.heapreplace(top, entry)
            else:
                heapq.heappush(top, entry)
    ranked = sorted(top, reverse=True)
    attempts = 0
    for retry in (False, True) if soft else (False,):
        for rank, _, geometry, received, erasures, scores in ranked:
            options = confidence_erasures(scores, erasures, parity_bytes) if retry else (erasures,)
            for option in options:
                attempts += 1
                if verify(received, option):
                    return dict(authenticated=True, candidates=checked, attempts=attempts,
                                geometry=geometry, score=rank, seconds=perf_counter()-start)
    return dict(authenticated=False, candidates=checked, attempts=attempts, seconds=perf_counter()-start)


def search_crop(image, original_size, *, bits=BITS, parity_bytes=PARITY_BYTES, verify=recover, soft=False):
    """Find an unknown pixel offset when original width and height are supplied."""
    start = perf_counter()
    trim_x, trim_y = original_size[0]-image.width, original_size[1]-image.height
    if not (0 <= trim_x <= MAX_TRIM and 0 <= trim_y <= MAX_TRIM):
        raise ValueError("Crop exceeds the bounded search")
    phases = block_phases(image)
    y, x = positions(original_size, COPIES, bits)
    bx, by = x[:, 0, 0], y[:, 0, 0]

    def hypotheses():
        for dx in range(trim_x+1):
            for dy in range(trim_y+1):
                x, y = bx-dx, by-dy
                visible = (x >= 0) & (y >= 0) & (x < phases.shape[1]) & (y < phases.shape[0])
                scores = np.zeros(bits * COPIES)
                scores[visible] = phases[y[visible], x[visible]]
                yield dict(size=original_size, offset=(dx,dy)), scores.reshape(COPIES,bits), visible.reshape(COPIES,bits)

    return authenticate_best(hypotheses(), start, verify, parity_bytes, soft=soft)


def resize_dimensions(length, scale, include_rounding):
    ratio = Fraction(str(scale))
    # A floor-based output n corresponds to n <= original*scale < n+1.
    # Also admit nearest rounding, including half-to-even ties, in wide mode.
    lower = length - Fraction(1, 2) if include_rounding else length
    minimum = math.ceil(lower / ratio)
    maximum = math.ceil((length + 1) / ratio)
    return range(minimum, maximum)


def search_resize(image, *, bits=BITS, parity_bytes=PARITY_BYTES, verify=recover, wide=False, soft=False, phase=None):
    """Try dimensions compatible with floor-based resizing at listed scales."""
    start = perf_counter()

    def hypotheses():
        sizes = set()
        for scale in WIDE_SCALES if wide else SCALES:
            for width in resize_dimensions(image.width, scale, wide):
                for height in resize_dimensions(image.height, scale, wide):
                    size = (width,height)
                    if size in sizes or width*height > 4_000_000:
                        continue
                    sizes.add(size)
                    try:
                        y, x = positions(size, COPIES, bits)
                    except ValueError:
                        continue
                    restored = image.resize(size, Image.Resampling.LANCZOS)
                    locations = y[:, 0, 0] // BLOCK, x[:, 0, 0] // BLOCK
                    if phase is None:
                        values = grid_phases(restored)[locations]
                    else:
                        values = np.cos(grid_angles(restored)[locations] - np.pi * phase)
                    scores = values.reshape(COPIES, bits)
                    yield dict(size=size, scale=scale), scores, np.ones_like(scores, dtype=bool)

    return authenticate_best(hypotheses(), start, verify, parity_bytes, soft=soft)


def search_exposure(image, *, bits=BITS, parity_bytes=PARITY_BYTES, verify=recover, soft=False):
    """Try whole-percent brightness multipliers from 0.85 through 1.15."""
    start = perf_counter()
    y, x = positions(image.size, COPIES, bits)
    pixels = np.asarray(image.convert("RGB"), dtype=np.float32)

    def hypotheses():
        for percent in range(85, 116):
            factor = percent / 100
            restored = np.clip(np.floor((pixels + .5) / factor + .5), 0, 255).astype(np.uint8)
            scores = grid_phases(Image.fromarray(restored))[
                y[:, 0, 0] // BLOCK, x[:, 0, 0] // BLOCK
            ].reshape(COPIES, bits)
            yield dict(factor=factor), scores, np.ones_like(scores, dtype=bool)

    return authenticate_best(hypotheses(), start, verify, parity_bytes, soft=soft)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    rows = json.loads((JPEG_OUT/"results.json").read_text())
    records = []
    for row in rows:
        if (row["spacing"],row["repetitions"]) != (SPACING,COPIES):
            continue
        name = row["cover"]
        original = Image.fromarray(getattr(data,name)()).convert("RGB")
        clean = ImageOps.contain(original,(512,512),Image.Resampling.LANCZOS)
        marked = embed(clean,bytes.fromhex(row["codeword"]),SPACING,COPIES)
        width,height = marked.size
        crop = marked.crop((13,21,width-17,height-9))
        resized = {scale: marked.resize((int(width*scale),int(height*scale)),Image.Resampling.LANCZOS)
                   for scale in (.625,.75,.8,.73)}
        cases = {
            "off_center_crop":search_crop(crop,marked.size),
            "off_center_crop_jpeg70":search_crop(transcode(crop,"JPEG",quality=70,subsampling=2),marked.size),
            "resize_625":search_resize(resized[.625]),
            "resize_75":search_resize(resized[.75]),
            "resize_80":search_resize(resized[.8]),
            "resize_73_unlisted":search_resize(resized[.73]),
            "resize_75_jpeg70":search_resize(transcode(resized[.75],"JPEG",quality=70,subsampling=2)),
            "clean_crop_control":search_crop(clean.crop((13,21,width-17,height-9)),clean.size),
        }
        records.append(dict(cover=name, cases=cases))
        pending=OUT/"results.tmp"
        pending.write_text(json.dumps(records,indent=2,allow_nan=False)+"\n")
        pending.replace(OUT/"results.json")
        print(name,{key:value["authenticated"] for key,value in cases.items()},flush=True)


if __name__=="__main__":
    main()
