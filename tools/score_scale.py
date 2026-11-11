"""Median |carrier score| on clean screen+tune tiles, per backbone (sets each backbone's margin).

    python -m tools.score_scale resnet18 convnext_tiny ...
"""
import json
import sys
from pathlib import Path

import numpy as np
import torch

from ghostframe import load_model
from ghostframe_png import backbones
from ghostframe_png.core import InputError, Profile, load_cover, read_scores

ROOT = Path(__file__).resolve().parents[1]


def main():
    torch.set_num_threads(4)
    manifest = json.loads((ROOT / "bench" / "manifest-v1.json").read_text())
    out = {}
    for name in sys.argv[1:] or ["squeezenet1_1", *backbones.BACKBONES]:
        model = load_model("cpu") if name == "squeezenet1_1" else backbones.load(name)
        profile = Profile("scale-probe", 10, 8, 16, 48, 2, backbone=name)
        scores = []
        for entry in manifest["covers"]:
            if entry["split"] not in ("screen", "tune"):
                continue
            try:
                scores.append(read_scores(load_cover(ROOT / manifest["covers_dir"] / entry["file"]), profile, model))
            except InputError:
                continue
        scores = np.abs(np.concatenate(scores))
        out[name] = dict(median_abs=float(np.median(scores)), p10_abs=float(np.quantile(scores, .1)), n=int(scores.size))
        print(name, json.dumps(out[name]), flush=True)


if __name__ == "__main__":
    main()
