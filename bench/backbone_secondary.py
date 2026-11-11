"""Secondary measures for the backbone screen: JPEG re-save survival and 1-thread determinism.

    python -m bench.backbone_secondary   # writes runs/backbones/secondary.jsonl

Reported only; never used for the decision (bench/PREREGISTRATION-BACKBONES.md).
"""
import io
import json
from pathlib import Path

import numpy as np
from PIL import Image
import torch

from bench.configs import PASSPHRASE, from_spec
from ghostframe_png import backbones, core

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs" / "backbones"


def model_for(profile, cache={}):
    if profile.backbone not in cache:
        from ghostframe import load_model
        cache[profile.backbone] = load_model("cpu") if profile.backbone == "squeezenet1_1" else \
            backbones.load(profile.backbone)
    return cache[profile.backbone]


def attempt(rgb, profile, expected):
    try:
        return core.decode_message(rgb, PASSPHRASE, profile, model_for(profile)) == expected
    except Exception:
        return False


def jpeg(rgb, quality):
    buffer = io.BytesIO()
    Image.fromarray(rgb).save(buffer, format="JPEG", quality=quality, subsampling=0)
    return np.asarray(Image.open(io.BytesIO(buffer.getvalue())).convert("RGB"))


def main():
    out = (RUNS / "secondary.jsonl").open("a")
    done = set()
    if (RUNS / "secondary.jsonl").exists():
        done = {json.loads(line)["png"] for line in (RUNS / "secondary.jsonl").open()}
    for decode_log in sorted(RUNS.glob("*/*/decode.jsonl")):
        jobs = {j["png"]: j for j in json.loads((decode_log.parent / "decode-jobs.json").read_text())} \
            if (decode_log.parent / "decode-jobs.json").exists() else {}
        for line in decode_log.open():
            row = json.loads(line)
            if not row["ok"] or row["png"] in done or row["png"] not in jobs:
                continue
            profile = from_spec(jobs[row["png"]]["spec"])
            rgb = core.load_png(row["png"])
            expected = bytes.fromhex(row["message"])
            torch.set_num_threads(1)
            received1 = core.scores_to_bytes(core.read_scores(rgb, profile, model_for(profile)))[0].hex()
            torch.set_num_threads(4)
            record = dict(png=row["png"], profile=profile.name, backbone=profile.backbone,
                          threads1_identical=received1 == row["received"],
                          jpeg95=attempt(jpeg(rgb, 95), profile, expected),
                          jpeg90=attempt(jpeg(rgb, 90), profile, expected))
            out.write(json.dumps(record) + "\n")
            out.flush()
            print(json.dumps(record), flush=True)


if __name__ == "__main__":
    main()
