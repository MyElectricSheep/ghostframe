"""Authenticated capacity screen using only frozen embeddings and saved PNGs."""
import argparse
import io
import json
from pathlib import Path
from time import perf_counter

import numpy as np
from PIL import Image
from reedsolo import RSCodec, ReedSolomonError
import torch

from experiments import tiled
from ghostframe import decode, embedding, load_model, pixels, projections, read_image, tensor

# Each tuple is (columns, rows, bits per tile, parity bytes, orthogonal).
PROFILES = {
    "baseline": (6, 5, 16, 0, False),
    "dense": (6, 5, 24, 0, False),
    "dense_qr": (6, 5, 24, 0, True),
    "dense_ecc": (6, 5, 24, 16, True),
    "grid_ecc": (8, 8, 16, 24, False),
    "grid_dense_ecc": (8, 8, 24, 32, True),
    "grid_wide_ecc": (10, 8, 24, 32, True),
    "grid_light_ecc": (8, 8, 12, 24, True),
    "grid_light_wide_ecc": (10, 8, 12, 24, True),
}


def boxes(size, cols, rows):
    width, height = size
    if min(width // cols, height // rows) < 16:
        raise ValueError("Image is too small for the selected tile grid")
    return [(c*width//cols, r*height//rows, (c+1)*width//cols, (r+1)*height//rows)
            for r in range(rows) for c in range(cols)]


def directions(index, bits, orthogonal):
    carriers = projections(tiled.tile_key(index), bits)
    if orthogonal:
        q, r = torch.linalg.qr(carriers.T)
        carriers = (q * torch.sign(r.diagonal())).T
    return carriers


def mark_batch(model, original, carriers, targets, epsilon, steps):
    delta = torch.zeros_like(original, requires_grad=True)
    optimizer = torch.optim.Adam([delta], lr=1/255)
    best = original.clone()
    best_errors = torch.full((len(original),), targets.shape[1] + 1)
    best_mse = torch.full((len(original),), float("inf"))
    for step in range(steps + 1):
        candidate = (original + delta).clamp(0, 1)
        quantized = (candidate * 255).round() / 255
        straight = quantized.detach() + (candidate - candidate.detach())
        scores = torch.einsum("bd,bnd->bn", embedding(model, straight), carriers)
        errors = ((scores.detach() > 0) != (targets > 0)).sum(dim=1)
        mse = (quantized.detach() - original).square().mean(dim=(1, 2, 3))
        better = (errors < best_errors) | ((errors == best_errors) & (mse < best_mse))
        best[better] = quantized.detach()[better]
        best_errors[better] = errors[better]
        best_mse[better] = mse[better]
        active = errors > 0
        if not active.any() or step == steps:
            break
        loss = (.035 - scores[active] * targets[active]).relu().square().mean()
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        with torch.no_grad():
            delta.grad[~active] = 0
            frozen = delta[~active].clone()
            optimizer.step()
            delta[~active] = frozen
            delta.clamp_(-epsilon/255, epsilon/255)
    return [pixels(tile[None]) for tile in best]


def roundtrip(model, cover, profile, epsilon, steps, fixture=None):
    cols, rows, bits, parity, orthogonal = PROFILES[profile]
    frame_bytes = cols * rows * bits // 8
    payload = bytes(range(frame_bytes - parity - 47))
    # Preserve the v1 frame construction and give experimental profiles
    # distinct associated data bound to their carrier layout.
    if profile == "baseline":
        frame = tiled.seal(payload, tiled.PASSWORD)
    else:
        frame = seal(payload, frame_bytes - parity, profile)
    codeword = bytes(RSCodec(parity).encode(frame)) if parity else frame
    tile_boxes = boxes(cover.size, cols, rows)
    start = perf_counter()
    if profile == "baseline":
        marked = tiled.embed_tiles(cover, tiled.bit_string(codeword), model, epsilon)
    else:
        marked = cover.copy()
        groups = {}
        for index, (left, top, right, bottom) in enumerate(tile_boxes):
            groups.setdefault((right-left, bottom-top), []).append(index)
        targets = torch.from_numpy(np.unpackbits(np.frombuffer(codeword, dtype=np.uint8))
                                  .reshape(-1, bits)).float() * 2 - 1
        for group in groups.values():
            for offset in range(0, len(group), 8):
                batch = group[offset:offset+8]
                images = torch.cat([tensor(cover.crop(tile_boxes[i]), "cpu") for i in batch])
                carriers = torch.stack([directions(i, bits, orthogonal) for i in batch])
                tiles = mark_batch(model, images, carriers, targets[batch], epsilon, steps)
                for index, tile in zip(batch, tiles, strict=True):
                    marked.paste(tile, tile_boxes[index][:2])
    seconds = perf_counter() - start
    stream = io.BytesIO()
    marked.save(stream, "PNG")
    stream.seek(0)
    with Image.open(stream) as png:
        reopened = png.convert("RGB")
    received = read_codeword(model, reopened, profile)
    try:
        message = recover(received, profile)
        success = message == payload
    except ValueError:
        success = False
    if success and fixture is not None:
        with fixture.open("xb") as output:
            output.write(stream.getvalue())
    delta = np.asarray(reopened, dtype=np.int16) - np.asarray(cover, dtype=np.int16)
    assert abs(delta).max() <= epsilon
    return dict(profile=profile, payload_bytes=len(payload), epsilon=epsilon,
                authenticated=success, bit_errors=sum((a ^ b).bit_count()
                for a, b in zip(received, codeword, strict=True)),
                byte_errors=sum(a != b for a,b in zip(received, codeword, strict=True)),
                max_delta=int(abs(delta).max()), mse=float(np.mean(delta.astype(float)**2)),
                encode_seconds=seconds)


def read_codeword(model, reopened, profile):
    cols, rows, bits, _, orthogonal = PROFILES[profile]
    tile_boxes = boxes(reopened.size, cols, rows)
    frame_bytes = cols * rows * bits // 8
    if orthogonal:
        with torch.inference_mode():
            result = [(embedding(model, tensor(reopened.crop(box), "cpu"))
                       @ directions(i, bits, True).T)[0] > 0 for i, box in enumerate(tile_boxes)]
        received = np.packbits(torch.cat(result).numpy()).tobytes()
    else:
        recovered = "".join(decode(reopened.crop(box), tiled.tile_key(i), bits, model)
                            for i, box in enumerate(tile_boxes))
        received = int(recovered, 2).to_bytes(frame_bytes, "big")
    return received


def recover(received, profile):
    cols, rows, bits, parity, _ = PROFILES[profile]
    if len(received) != cols * rows * bits // 8:
        raise ValueError("Invalid codeword length")
    try:
        raw = bytes(RSCodec(parity).decode(received)[0]) if parity else received
    except ReedSolomonError as exc:
        raise ValueError("Invalid codeword") from exc
    return tiled.open_frame(raw, tiled.PASSWORD) if profile == "baseline" else unseal(raw, profile)


def seal(payload, frame_bytes, profile):
    from os import urandom
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    salt, nonce = urandom(16), urandom(12)
    plain = len(payload).to_bytes(2, "big") + payload.ljust(frame_bytes - 47, b"\0")
    cipher = AESGCM(tiled.derive(tiled.PASSWORD, salt))
    return b"\x04" + salt + nonce + cipher.encrypt(nonce, plain, profile.encode())


def unseal(frame, profile):
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    if frame[:1] != b"\x04":
        raise ValueError("Invalid frame")
    cipher = AESGCM(tiled.derive(tiled.PASSWORD, frame[1:17]))
    try:
        plain = cipher.decrypt(frame[17:29], frame[29:], profile.encode())
    except InvalidTag as exc:
        raise ValueError("Invalid frame") from exc
    length = int.from_bytes(plain[:2], "big")
    if length > len(plain) - 2:
        raise ValueError("Invalid payload length")
    return plain[2:2+length]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images", nargs="+", type=Path)
    parser.add_argument("--profiles", nargs="+", choices=PROFILES, default=list(PROFILES))
    parser.add_argument("--caps", nargs="+", type=int, choices=(2, 4, 8), default=[2, 8])
    parser.add_argument("--steps", type=int, default=35)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    torch.set_num_threads(4)
    model = load_model("cpu")
    results = []
    for path in args.images:
        cover = read_image(path)
        for epsilon in args.caps:
            for profile in args.profiles:
                row = dict(cover=path.name, **roundtrip(model, cover, profile, epsilon, args.steps))
                results.append(row)
                args.output.write_text(json.dumps(results, indent=2) + "\n")
                print(row, flush=True)


if __name__ == "__main__":
    main()
