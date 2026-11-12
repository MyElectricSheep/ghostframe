"""Experimental tiled carrier with authenticated 13-byte messages."""
import json
import os
from pathlib import Path
from time import perf_counter

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from PIL import Image
from skimage.metrics import peak_signal_noise_ratio, structural_similarity
import numpy as np
import torch

from experiments.frame_keys import PASSWORD, derive
from experiments.extended import fresh_covers, run_trial
from ghostframe import decode, encode, load_model, transforms

COLS, ROWS = 6, 5
TILE_BITS = 16
FRAME_BYTES = COLS * ROWS * TILE_BITS // 8
MAX_MESSAGE = 13
VERSION = b"\x01"
AAD = b"Ghostframe tiled research v1"
OUT = Path("benchmarks/tiled")


def seal(message, password):
    if len(message) > MAX_MESSAGE:
        raise ValueError("Message exceeds 13 bytes")
    salt, nonce = os.urandom(16), os.urandom(12)
    plain = len(message).to_bytes(2, "big") + message.ljust(MAX_MESSAGE, b"\0")
    return VERSION + salt + nonce + AESGCM(derive(password, salt)).encrypt(nonce, plain, AAD + VERSION)


def open_frame(frame, password):
    if len(frame) != FRAME_BYTES or frame[:1] != VERSION:
        raise ValueError("Invalid frame")
    salt, nonce = frame[1:17], frame[17:29]
    try:
        plain = AESGCM(derive(password, salt)).decrypt(nonce, frame[29:], AAD + VERSION)
    except InvalidTag as exc:
        raise ValueError("Invalid frame") from exc
    length = int.from_bytes(plain[:2], "big")
    if length > MAX_MESSAGE:
        raise ValueError("Invalid frame")
    return plain[2:2+length]


def tile_boxes(size):
    width, height = size
    if min(width // COLS, height // ROWS) < 16:
        raise ValueError("Image is too small for the tiled carrier")
    return [(c*width//COLS, r*height//ROWS, (c+1)*width//COLS, (r+1)*height//ROWS)
            for r in range(ROWS) for c in range(COLS)]


def tile_key(index):
    # Public carriers. Confidentiality is supplied by the authenticated frame.
    return f"ghostframe-tiled-public-v1/{index}"


def embed_tiles(image, bits, model, epsilon, progress=None):
    # progress(fraction) only observes; it may raise to cancel.
    if len(bits) != 8 * FRAME_BYTES:
        raise ValueError("Incorrect frame length")
    marked = image.copy()
    boxes = tile_boxes(image.size)
    for index, box in enumerate(boxes):
        start = index * TILE_BITS
        tile = encode(image.crop(box), bits[start:start+TILE_BITS], tile_key(index), model, epsilon=epsilon)
        marked.paste(tile, box[:2])
        if progress is not None:
            progress((index + 1) / len(boxes))
    return marked


def read_tiles(image, model):
    return "".join(decode(image.crop(box), tile_key(index), TILE_BITS, model)
                   for index, box in enumerate(tile_boxes(image.size)))


def bit_string(frame):
    return "".join(f"{value:08b}" for value in frame)


def main():
    torch.set_num_threads(4)
    OUT.mkdir(parents=True, exist_ok=True)
    model = load_model("cpu")
    records = []
    for name, image in fresh_covers().items():
        message = b"Meet at dawn."
        frame = seal(message, PASSWORD)
        bits = bit_string(frame)
        for epsilon in (2, 8):
            started = perf_counter()
            marked = embed_tiles(image, bits, model, epsilon)
            seconds = perf_counter() - started
            path = OUT / f"{name}-{epsilon}.png"
            marked.save(path)
            with Image.open(path) as png:
                reopened = png.convert("RGB")
            outcomes = {}
            for label, view in [("png", reopened), *transforms(reopened)]:
                recovered = read_tiles(view, model)
                recovered_frame = int(recovered, 2).to_bytes(FRAME_BYTES, "big")
                try:
                    valid = open_frame(recovered_frame, PASSWORD) == message
                except ValueError:
                    valid = False
                errors = sum(a != b for a,b in zip(bits,recovered))
                outcomes[label] = dict(errors=errors, authenticated=valid, recovered=recovered)
            original, result = np.asarray(image), np.asarray(reopened)
            max_delta = int(np.abs(original.astype(np.int16)-result).max())
            assert max_delta <= epsilon
            baseline = run_trial(model, image, name, bits, "global-480-control", epsilon, "baseline", "global")
            row = dict(cover=name, epsilon=epsilon, frame=frame.hex(), png=path.name,
                       seconds=seconds, max_delta=max_delta,
                       psnr=float(peak_signal_noise_ratio(original,result)),
                       ssim=float(structural_similarity(original,result,channel_axis=-1)),
                       tiled=outcomes, global_png_errors=baseline["cases"]["png"]["errors"])
            records.append(row)
            print(name, epsilon, outcomes["png"]["errors"], row["global_png_errors"], flush=True)
            (OUT/"results.json").write_text(json.dumps(records,indent=2,allow_nan=False)+"\n")


if __name__ == "__main__":
    main()
