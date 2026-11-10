"""Shared aligned luminance carrier."""
from functools import lru_cache
import hashlib
import heapq

import numpy as np
from PIL import Image

# Default frame size of the original tiled comparison.
FRAME_BYTES = 60
BITS = FRAME_BYTES * 8
BLOCK = 8
EPSILON = 2


@lru_cache(maxsize=16)
def block_order(count, needed):
    def digest(index):
        return hashlib.sha256(b"ghostframe-luminance-v1" + index.to_bytes(8, "big")).digest()

    if needed * 4 >= count:
        return tuple(sorted(range(count), key=digest)[:needed])
    return tuple(heapq.nsmallest(needed, range(count), key=digest))


def positions(size, repetitions, bit_count=BITS):
    width, height = size[0] // BLOCK, size[1] // BLOCK
    count = width * height
    if count < bit_count * repetitions:
        raise ValueError("Not enough complete 8×8 blocks for the selected repetition count")
    index = np.asarray(block_order(count, bit_count * repetitions))
    rows, columns = (index // width) * BLOCK, (index % width) * BLOCK
    offsets = np.arange(BLOCK)
    return rows[:, None, None] + offsets[None, :, None], columns[:, None, None] + offsets[None, None, :]


def luminance(rgb):
    # Compute JPEG-style luma directly, keeping fractional precision.
    return rgb @ np.array([.299, .587, .114])


def embed(image, codeword, spacing, repetitions, *, phase=None):
    if not codeword:
        raise ValueError("Empty codeword")
    y, x = positions(image.size, repetitions, len(codeword)*8)
    pixels = np.array(image.convert("RGB"))
    blocks = pixels[y, x].astype(np.int16)
    candidates = np.arange(-EPSILON, EPSILON+1)
    values = np.clip(blocks[:, None] + candidates[None, :, None, None, None], 0, 255)
    means = luminance(values).mean(axis=(-1, -2))
    target = np.tile(np.unpackbits(np.frombuffer(codeword, np.uint8)), repetitions)[:, None]
    # Nearest lattice point with the requested parity. Small tie-breaker favors less change.
    normalized = means / spacing
    if phase is not None:
        normalized = normalized - np.asarray(phase).reshape(len(blocks), 1)
    nearest = 2 * np.round((normalized - target) / 2) + target
    cost = abs(normalized - nearest) + abs(candidates)[None, :] * 1e-6
    pixels[y, x] = values[np.arange(len(blocks)), cost.argmin(axis=1)]
    return Image.fromarray(pixels)


def extract(image, spacing, repetitions, frame_bytes=FRAME_BYTES, *, phase=None):
    bit_count = frame_bytes * 8
    y, x = positions(image.size, repetitions, bit_count)
    means = luminance(np.asarray(image.convert("RGB"))[y, x]).mean(axis=(-1, -2))
    angles = np.pi * means / spacing
    if phase is not None:
        angles = angles - np.pi * np.asarray(phase).reshape(bit_count * repetitions)
    confidence = np.cos(angles)
    bits = confidence.reshape(repetitions, bit_count).sum(axis=0) < 0
    return np.packbits(bits).tobytes()


