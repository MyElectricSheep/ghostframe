"""Build the pinned tile-mean calibration vector from screening and tuning covers only."""
import hashlib
import json
from pathlib import Path

import numpy as np
import torch

from ghostframe import embedding, load_model
from ghostframe_png.core import CALIBRATION, InputError, Profile, _tensor, load_cover, tile_boxes

ROOT = Path(__file__).resolve().parents[1]


def main():
    torch.set_num_threads(4)
    model = load_model("cpu")
    manifest = json.loads((ROOT / "bench" / "manifest-v1.json").read_text())
    total, count, used = torch.zeros(512, dtype=torch.float64), 0, []
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
                    total += embedding(model, _tensor(rgb[t:b, l:r]))[0].double()
                    count += 1
    mean = (total / count).float().numpy()
    np.save(CALIBRATION, mean, allow_pickle=False)
    print(json.dumps(dict(covers=used, tiles=count, sha256=hashlib.sha256(CALIBRATION.read_bytes()).hexdigest())))


if __name__ == "__main__":
    main()
