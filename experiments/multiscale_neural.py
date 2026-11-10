"""Matched differentiable multiscale neural embedding comparison."""
import json
from pathlib import Path

import torch
import torch.nn.functional as F

from experiments.carrier_controls import source_image
from experiments.extended import run_trial
from experiments.goal_validation import OUT
from ghostframe import load_model


def scale_view(scale):
    def transform(image):
        height, width = image.shape[-2:]
        return F.interpolate(image, size=(round(height * scale), round(width * scale)),
                             mode="bilinear", align_corners=False, antialias=True)
    return transform


def main():
    torch.set_num_threads(4)
    model = load_model("cpu")
    baseline = json.loads(Path("benchmarks/final-sweep/neural-holdout.json").read_text())
    rows = []
    for previous in baseline:
        if previous["epsilon"] != 2:
            continue
        name = previous["cover"]
        row = run_trial(model, source_image(name), name, previous["target"], previous["key"],
                        2, "baseline", "multiscale",
                        extra_views=(scale_view(.65), scale_view(.85)))
        rows.append(row)
        print(name, len(previous["target"]), flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "multiscale.json").write_text(json.dumps(rows, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
