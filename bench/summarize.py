"""Join encode and independent-decode logs; print per-profile tables with intervals.

    python -m bench.summarize runs/centering-l2 [runs/other ...] [--by-cover]
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0.0, centre - half), min(1.0, centre + half)


def cluster_interval(success_by_cover, draws=4000, seed=0):
    """Percentile bootstrap over covers, keeping each cover's frames together."""
    if not success_by_cover:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    groups = list(success_by_cover.values())
    stats = []
    for _ in range(draws):
        pick = rng.integers(0, len(groups), len(groups))
        k = sum(sum(groups[i]) for i in pick)
        n = sum(len(groups[i]) for i in pick)
        stats.append(k / n)
    return float(np.percentile(stats, 2.5)), float(np.percentile(stats, 97.5))


def load(dirs):
    rows = []
    for d in dirs:
        d = Path(d)
        decoded = {}
        if (d / "decode.jsonl").exists():
            for line in (d / "decode.jsonl").open():
                r = json.loads(line)
                decoded[Path(r["png"]).name] = r
        import hashlib
        for line in (d / "encode.jsonl").open():
            r = json.loads(line)
            name = hashlib.sha256(r["trial"].encode()).hexdigest()[:16] + ".png"
            r["decode"] = decoded.get(name)
            dec = r["decode"]
            r["success"] = bool(dec and dec["ok"] and dec["message"] == r["message"])
            if dec and dec.get("received") and r.get("codeword"):
                a, b = bytes.fromhex(dec["received"]), bytes.fromhex(r["codeword"])
                r["byte_errors"] = sum(x != y for x, y in zip(a, b))
                r["bit_errors"] = sum((x ^ y).bit_count() for x, y in zip(a, b))
            rows.append(r)
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dirs", nargs="+")
    parser.add_argument("--by-cover", action="store_true")
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    rows = load(args.dirs)
    table = []
    for profile in dict.fromkeys(r["profile"] for r in rows):
        group = [r for r in rows if r["profile"] == profile and r.get("status") != "over_capacity"]
        by_cover = {}
        for r in group:
            by_cover.setdefault(r["cover"], []).append(r["success"])
        k, n = sum(r["success"] for r in group), len(group)
        enc = [r["encode_s"] for r in group if "encode_s" in r]
        dec = [r["decode"]["decode_s"] for r in group if r.get("decode")]
        errs = [r["byte_errors"] for r in group if "byte_errors" in r]
        maxd = max((max(r["max_per_channel"]) for r in group if "max_per_channel" in r), default=None)
        summary = dict(
            profile=profile, epsilon=group[0].get("epsilon") if group else None,
            payload=group[0]["payload_bytes"] if group else None, coded=group[0].get("coded_bytes") if group else None,
            success=k, trials=n, covers=len(by_cover), wilson95=wilson(k, n), cluster95=cluster_interval(by_cover),
            encode_failed=sum(1 for r in group if r["status"].startswith("encode_failed")),
            median_encode_s=float(np.median(enc)) if enc else None, median_decode_s=float(np.median(dec)) if dec else None,
            median_byte_errors=float(np.median(errs)) if errs else None, max_byte_errors=max(errs) if errs else None,
            max_rgb_delta=maxd,
            median_mean_abs=float(np.median([r["mean_abs"] for r in group if "mean_abs" in r])) if group else None,
            median_psnr=float(np.median([r["psnr"] for r in group if r.get("psnr")])) if any(r.get("psnr") for r in group) else None,
            median_ssim=float(np.median([r["ssim"] for r in group if "ssim" in r])) if any("ssim" in r for r in group) else None,
            failures=sorted({r["cover"] for r in group if not r["success"]}),
        )
        table.append(summary)
        lo, hi = summary["wilson95"]
        print(f"{profile:32s} eps={summary['epsilon']} payload={summary['payload']:>4} coded={summary['coded']} "
              f"{k}/{n} [{lo:.2f},{hi:.2f}] enc={summary['median_encode_s'] or 0:.0f}s "
              f"bytes_err med/max={summary['median_byte_errors']}/{summary['max_byte_errors']} "
              f"psnr={summary['median_psnr'] or 0:.1f} fail={summary['failures']}")
        if args.by_cover:
            for cover, results in by_cover.items():
                print(f"    {cover:30s} {sum(results)}/{len(results)}")
    if args.json:
        args.json.write_text(json.dumps(table, indent=1) + "\n")


if __name__ == "__main__":
    main()
