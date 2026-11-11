"""Build the pinned tile-mean calibration vector from screening and tuning covers only.

    python -m tools.calibrate                      # SqueezeNet (the original file)
    python -m tools.calibrate --backbone resnet18  # an alternative backbone; pin the printed digest
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch

from ghostframe import load_model
from ghostframe_png import backbones
from ghostframe_png.core import CALIBRATION, InputError, Profile, _embed, _tensor, load_cover, tile_boxes

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backbone", default="squeezenet1_1")
    args = parser.parse_args()
    torch.set_num_threads(4)
    if args.backbone == "squeezenet1_1":
        model, dim, out = load_model("cpu"), 512, CALIBRATION
    else:
        backbone = backbones.BACKBONES[args.backbone]
        model, dim, out = backbones.load(args.backbone), backbone.dim, backbone.calibration
    manifest = json.loads((ROOT / "bench" / "manifest-v1.json").read_text())
    total, count, used = torch.zeros(dim, dtype=torch.float64), 0, []
    with torch.inference_mode():
        for entry in manifest["covers"]:
            if entry["split"] not in ("screen", "tune"):
                continue
            rgb = load_cover(ROOT / manifest["covers_dir"] / entry["file"])
            used.append(entry["id"])
            for cols, rows in ((6, 5), (8, 8), (10, 8), (12, 10)):
                grid = Profile("calibration", cols, rows, 8, 0, 2, centered=False)
                try:
                    boxes = tile_boxes(rgb.shape, grid)
                except InputError:
                    continue
                for l, t, r, b in boxes:
                    total += _embed(model, _tensor(rgb[t:b, l:r]))[0].double()
                    count += 1
    mean = (total / count).float().numpy()
    np.save(out, mean, allow_pickle=False)
    print(json.dumps(dict(backbone=args.backbone, covers=used, tiles=count,
                          sha256=hashlib.sha256(out.read_bytes()).hexdigest())))


if __name__ == "__main__":
    main()
