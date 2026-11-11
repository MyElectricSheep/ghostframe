"""Export tile embeddings and carrier scores for the demo fixtures (original vs marked).

Classic is read by SqueezeNet 1.1 (512 numbers per tile); Subtle and Long by the profile's own
backbone (MobileNetV3-Small, 576 numbers per tile).

    python -m tools.dump_embeddings   # writes demo-photos/fixtures/embeddings/
"""
import json
from pathlib import Path

import numpy as np
import torch

from experiments import tiled
from ghostframe import embedding, load_model, projections
from ghostframe_png import backbones, core

ROOT = Path("demo-photos/fixtures")
OUT = ROOT / "embeddings"
PHOTOS = ["coffee-beans", "milky-way", "antonello-portrait-of-a-man"]
MODES = {
    "classic": ("legacy-v1", tiled.COLS, tiled.ROWS, tiled.TILE_BITS, 8),
    "subtle": ("bb-mobilenet_v3_small-l2-b16p48",) + (None,) * 4,
    "long": ("bb-mobilenet_v3_small-l8-b64p112",) + (None,) * 4,
}


def grid(mode):
    name, cols, rows, bits, cap = MODES[mode]
    if name in core.PROFILES:
        p = core.PROFILES[name]
        return name, p.cols, p.rows, p.bits, p.epsilon, p
    return name, cols, rows, bits, cap, None


def tiles(rgb, cols, rows):
    h, w = rgb.shape[:2]
    return [rgb[r * h // rows:(r + 1) * h // rows, c * w // cols:(c + 1) * w // cols]
            for r in range(rows) for c in range(cols)]


def directions(profile, index, bits):
    if profile is None:
        return projections(tiled.tile_key(index), bits)
    return core.carriers(profile, index)


def model_for(profile, cache={}):
    name = "squeezenet1_1" if profile is None else profile.backbone
    if name not in cache:
        cache[name] = load_model("cpu") if name == "squeezenet1_1" else backbones.load(name)
    return cache[name]


def read(rgb, cols, rows, bits, profile):
    model = model_for(profile)
    vectors, scores = [], []
    with torch.inference_mode():
        for index, tile in enumerate(tiles(rgb, cols, rows)):
            e = (embedding(model, core._tensor(tile)) if profile is None else core._embed(model, core._tensor(tile)))[0]
            vectors.append(e.numpy())
            scores.append((e @ directions(profile, index, bits).T).numpy())
    return np.stack(vectors), np.stack(scores)


def r(x, digits=5):
    return np.round(np.asarray(x, dtype=np.float64), digits).tolist()


def main():
    torch.set_num_threads(4)
    OUT.mkdir(exist_ok=True)
    summary = {}
    for photo in PHOTOS:
        original = core.load_png(ROOT / photo / "original.png")
        record = {"photo": photo, "modes": {}}
        for mode in MODES:
            name, cols, rows, bits, cap, profile = grid(mode)
            marked = core.load_png(ROOT / photo / f"{mode}.png")
            ev0, s0 = read(original, cols, rows, bits, profile)
            ev1, s1 = read(marked, cols, rows, bits, profile)
            cos = (ev0 * ev1).sum(1)
            flipped = (np.sign(s0) != np.sign(s1))
            record["modes"][mode] = {
                "profile": name, "backbone": "squeezenet1_1" if profile is None else profile.backbone,
                "embedding_dim": int(ev0.shape[1]), "cols": cols, "rows": rows, "bits_per_tile": bits, "cap": cap,
                "tile_cosine": r(cos, 6),
                "tile_shift": r(np.linalg.norm(ev1 - ev0, axis=1), 6),
                "scores_original": r(s0), "scores_marked": r(s1),
                "bits_flipped_per_tile": flipped.sum(1).tolist(),
                "embeddings_original": r(ev0), "embeddings_marked": r(ev1),
            }
            summary.setdefault(photo, {})[mode] = {
                "profile": name, "embedding_dim": int(ev0.shape[1]),
                "tiles": cols * rows, "bits": cols * rows * bits,
                "cos_min": float(cos.min()), "cos_median": float(np.median(cos)),
                "shift_median": float(np.median(np.linalg.norm(ev1 - ev0, axis=1))),
                "flipped": int(flipped.sum()),
                "abs0_median": float(np.median(np.abs(s0))), "abs1_median": float(np.median(np.abs(s1))),
                "abs1_min": float(np.abs(s1).min()),
                "hist0": np.histogram(s0, bins=12, range=(-0.06, 0.06))[0].tolist(),
                "hist1": np.histogram(s1, bins=12, range=(-0.06, 0.06))[0].tolist(),
                "tile_cosine": r(cos, 4), "cols": cols, "rows": rows,
            }
        (OUT / f"{photo}.json").write_text(json.dumps(record, separators=(",", ":")))
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
