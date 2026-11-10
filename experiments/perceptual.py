"""Score saved marks with the pretrained SqueezeNet LPIPS configuration."""
import json
from pathlib import Path

import torch

from experiments.extended import fresh_covers
from experiments.goal_validation import OUT
from ghostframe import read_image, tensor


def main():
    import lpips

    torch.set_num_threads(4)
    metric = lpips.LPIPS(net="squeeze").eval()
    baseline = json.loads(Path("benchmarks/baseline/results.json").read_text())
    pairs = [(f"baseline/{row['encoded_file']}", read_image(Path("examples") / row["image"]))
             for row in baseline["records"]]
    covers = fresh_covers()
    pairs.extend((f"tiled/{name}-{bound}.png", covers[name])
                 for name in ("astronaut", "coffee", "rocket", "chelsea") for bound in (2, 8))
    rows = []
    with torch.inference_mode():
        for name, clean in pairs:
            marked = read_image(Path("benchmarks") / name)
            value = metric(tensor(clean, "cpu") * 2 - 1, tensor(marked, "cpu") * 2 - 1)
            rows.append(dict(fixture=name, lpips=float(value.item())))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "lpips.json").write_text(json.dumps(rows, indent=2, allow_nan=False) + "\n")
    print(f"{len(rows)} saved-image comparisons")


if __name__ == "__main__":
    main()
