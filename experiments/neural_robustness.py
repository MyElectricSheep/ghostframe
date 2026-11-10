"""Compare smooth perturbations and transformation-aware objectives."""
import json
from pathlib import Path

import torch

from experiments.carrier_controls import source_image
from experiments.extended import jpeg80_view, run_trial
from experiments.multiscale_neural import scale_view
from ghostframe import load_model

OUT = Path("benchmarks/neural-robustness")
SETTINGS = (
    ("smooth", 4, ()),
    ("transform_aware", 1, (jpeg80_view, scale_view(.8))),
    ("smooth_transform_aware", 4, (jpeg80_view, scale_view(.8))),
)


def main():
    torch.set_num_threads(4)
    model = load_model("cpu")
    OUT.mkdir(parents=True, exist_ok=True)
    baseline = json.loads(Path("benchmarks/final-sweep/neural-holdout.json").read_text())
    rows = []
    for prior in baseline:
        if prior["epsilon"] != 2:
            continue
        name = prior["cover"]
        image = source_image(name)
        for label, stride, views in SETTINGS:
            record = run_trial(model, image, name, prior["target"], prior["key"], 2, "baseline",
                               label, extra_views=views, delta_stride=stride)
            rows.append(record)
            pending = OUT / "results.tmp"
            pending.write_text(json.dumps(rows, indent=2, allow_nan=False) + "\n")
            pending.replace(OUT / "results.json")
            print(name, len(prior["target"]), label, flush=True)


if __name__ == "__main__":
    main()
