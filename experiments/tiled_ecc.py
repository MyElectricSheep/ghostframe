"""Benchmark one authenticated byte and Reed-Solomon parity on the tiled carrier."""
import json
import os
from pathlib import Path
from time import perf_counter

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import numpy as np
from PIL import Image, ImageOps
from reedsolo import RSCodec, ReedSolomonError
from skimage import data
from skimage.metrics import peak_signal_noise_ratio, structural_similarity
import torch

from experiments.tiled import (
    FRAME_BYTES, PASSWORD, bit_string, derive, embed_tiles, read_tiles, tile_boxes,
)
from ghostframe import load_model, transforms

VERSION = b"\x02"
AAD = b"Ghostframe tiled research v2" + VERSION
DATA_BYTES = 46
PARITY_BYTES = FRAME_BYTES - DATA_BYTES
OUT = Path("benchmarks/tiled-ecc")
COVERS = ("camera", "brick", "grass", "hubble_deep_field", "astronaut", "coffee")
FRESH = frozenset(COVERS[:4])
MESSAGE = b"!"


def seal(message, password):
    if len(message) != 1:
        raise ValueError("The experimental frame takes exactly one byte")
    salt, nonce = os.urandom(16), os.urandom(12)
    return VERSION + salt + nonce + AESGCM(derive(password, salt)).encrypt(nonce, message, AAD)


def authenticate(frame, password):
    if len(frame) != DATA_BYTES or frame[:1] != VERSION:
        raise ValueError("Invalid frame")
    salt, nonce = frame[1:17], frame[17:29]
    try:
        return AESGCM(derive(password, salt)).decrypt(nonce, frame[29:], AAD)
    except InvalidTag as exc:
        raise ValueError("Invalid frame") from exc


def decode_frame(received, password, *, correct=True):
    if len(received) != FRAME_BYTES:
        raise ValueError("Invalid codeword")
    if correct:
        try:
            frame, _, positions = RSCodec(PARITY_BYTES).decode(received)
        except ReedSolomonError as exc:
            raise ValueError("Invalid codeword") from exc
    else:
        frame, positions = received[:DATA_BYTES], ()
    return authenticate(bytes(frame), password), tuple(positions)


def evaluate(image, codeword, model):
    received = int(read_tiles(image, model), 2).to_bytes(FRAME_BYTES, "big")
    result = {
        "bit_errors": sum((a ^ b).bit_count() for a, b in zip(received, codeword)),
        "byte_errors": sum(a != b for a, b in zip(received, codeword)),
        "received": received.hex(),
    }
    for correct, label in ((False, "raw"), (True, "corrected")):
        try:
            message, positions = decode_frame(received, PASSWORD, correct=correct)
            result[label] = message == MESSAGE
            if correct:
                result["corrected_positions"] = positions
        except ValueError:
            result[label] = False
    return result



def tile_restoration_control(image, marked, codeword, model):
    restored = marked.copy()
    for bounds in tile_boxes(image.size)[:3]:
        restored.paste(image.crop(bounds), bounds[:2])
    return evaluate(restored, codeword, model)


def main():
    torch.set_num_threads(4)
    OUT.mkdir(parents=True, exist_ok=True)
    model = load_model("cpu")
    rows = []
    for name in COVERS:
        original = Image.fromarray(getattr(data, name)()).convert("RGB")
        image = ImageOps.contain(original, (512, 512), Image.Resampling.LANCZOS)
        codeword = bytes(RSCodec(PARITY_BYTES).encode(seal(MESSAGE, PASSWORD)))
        started = perf_counter()
        marked = embed_tiles(image, bit_string(codeword), model, 2)
        seconds = perf_counter() - started
        path = OUT / f"{name}.png"
        pending = path.with_suffix(".tmp")
        marked.save(pending, format="PNG")
        with Image.open(pending, formats=["PNG"]) as png:
            reopened = png.convert("RGB")
        pending.replace(path)
        before, after = np.asarray(image), np.asarray(reopened)
        max_delta = int(np.abs(before.astype(np.int16) - after).max())
        assert max_delta <= 2
        cases = {label: evaluate(view, codeword, model)
                 for label, view in [("png", reopened), *transforms(reopened)]}
        cases["restore_first_three_tiles"] = tile_restoration_control(image, reopened, codeword, model)
        row = dict(cover=name, fresh=name in FRESH, dimensions=image.size,
                   seconds=seconds, max_delta=max_delta, codeword=codeword.hex(),
                   psnr=float(peak_signal_noise_ratio(before, after)),
                   ssim=float(structural_similarity(before, after, channel_axis=-1)),
                   cases=cases)
        rows.append(row)
        pending = OUT / "results.tmp"
        pending.write_text(json.dumps(rows, indent=2, allow_nan=False) + "\n")
        pending.replace(OUT / "results.json")
        print(name, cases["png"], flush=True)


if __name__ == "__main__":
    main()
