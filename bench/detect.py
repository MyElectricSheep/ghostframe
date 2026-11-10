"""Declared protocol-aware detector on paired clean and marked PNGs.

Statistic: the fraction of carrier scores with |score| below 0.002 under a named profile.
Clean tiles put a few percent of scores there; the encoder pushes scores past its margin, so
marked images put almost none. The detector needs the public profile, not the passphrase.

    python -m bench.detect runs/holdout-l2 --profile png-l2-c10x8b12 --out runs/detect-l2.json
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch

from bench.configs import from_spec
from bench.run import ROOT
from ghostframe import load_model
from ghostframe_png import core


def auc(negatives, positives):
    """Probability a marked image scores higher than a clean one (ties count half)."""
    wins = sum((p > n) + 0.5 * (p == n) for p in positives for n in negatives)
    return wins / (len(positives) * len(negatives))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("--profile", required=True, help="profile name in the run's encode log")
    parser.add_argument("--threshold", type=float, default=0.002)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    torch.set_num_threads(4)
    model = load_model("cpu")
    manifest = json.loads((ROOT / "bench" / "manifest-v1.json").read_text())
    files = {e["id"]: ROOT / manifest["covers_dir"] / e["file"] for e in manifest["covers"]}
    rows = [json.loads(line) for line in (args.run / "encode.jsonl").open()]
    rows = [r for r in rows if r["profile"] == args.profile and r["frame"] == 0 and r["status"] == "encoded"]
    spec = None
    for job in json.loads((args.run / "decode-jobs.json").read_text()):
        if job["profile"] == args.profile:
            spec = job["spec"]
    profile = from_spec(spec)
    clean, marked, per_cover = [], [], []
    for r in rows:
        png = args.run / "png" / (hashlib.sha256(r["trial"].encode()).hexdigest()[:16] + ".png")
        stat_clean = float((np.abs(core.read_scores(core.load_cover(files[r["cover"]]), profile, model)) < args.threshold).mean())
        stat_marked = float((np.abs(core.read_scores(core.load_png(png), profile, model)) < args.threshold).mean())
        clean.append(stat_clean)
        marked.append(stat_marked)
        per_cover.append(dict(cover=r["cover"], clean=stat_clean, marked=stat_marked))
    # A higher detector score means "marked": use the negative near-zero fraction.
    result = dict(profile=args.profile, threshold=args.threshold, pairs=len(rows),
                  auc=auc([-c for c in clean], [-m for m in marked]),
                  clean_median=float(np.median(clean)), marked_median=float(np.median(marked)),
                  clean_min=float(min(clean)), marked_max=float(max(marked)), per_cover=per_cover)
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    print({k: v for k, v in result.items() if k != "per_cover"})


if __name__ == "__main__":
    main()
