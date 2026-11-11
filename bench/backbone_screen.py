"""Run the preregistered backbone ladder (bench/PREREGISTRATION-BACKBONES.md). Resumable.

    python -m bench.backbone_screen screen   # ladders on the screen split
    python -m bench.backbone_screen tune     # candidates on the tune split
    python -m bench.backbone_screen report
"""
import json
from pathlib import Path
import statistics
import subprocess
import sys

from bench.configs import backbone_ladder

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs" / "backbones"
BUDGET_S, TIMEOUT_S = 90, 300
CONTROL_RUNGS = 2  # SqueezeNet same-day load control
SMALL_BATCH = {"efficientnet_b0", "convnext_tiny"}  # Amendment 1: memory


def run(profile, split, covers=None):
    out = RUNS / split / profile.name
    cmd = [sys.executable, "-m", "bench.run", "--suite", profile.name, "--split", split, "--frames", "1",
           "--timeout", str(TIMEOUT_S), "--out", str(out)]
    if profile.backbone in SMALL_BATCH:
        cmd += ["--batch", "8"]
    if covers:
        cmd += ["--covers", *covers]
    subprocess.run(cmd, check=True, cwd=ROOT)
    return result(out)


def result(out):
    if not (out / "encode.jsonl").exists():
        return None
    enc = [json.loads(line) for line in (out / "encode.jsonl").open()]
    dec = {}
    if (out / "decode.jsonl").exists():
        dec = {json.loads(line)["png"]: json.loads(line) for line in (out / "decode.jsonl").open()}
    ok = 0
    for row in enc:
        png = next((p for p, d in dec.items() if Path(p).name.split(".")[0] == _png_key(row["trial"])), None)
        if row["status"] == "encoded" and png and dec[png]["ok"] and dec[png]["message"] == row["message"]:
            ok += 1
    times = [row["encode_s"] for row in enc]
    return dict(n=len(enc), ok=ok, median_s=statistics.median(times), covers=[r["cover"] for r in enc],
                failures=[r["cover"] for r in enc if r["status"] != "encoded"])


def _png_key(trial):
    import hashlib
    return hashlib.sha256(trial.encode()).hexdigest()[:16]


def passes(res, n):
    return res is not None and res["n"] == n and res["ok"] == n and res["median_s"] <= BUDGET_S


def screen():
    summary = {}
    for (backbone, cap), rungs in backbone_ladder().items():
        for i, profile in enumerate(rungs):
            if backbone == "squeezenet1_1" and i >= CONTROL_RUNGS:
                break
            res = run(profile, "screen")
            summary[profile.name] = res
            print("SCREEN", profile.name, json.dumps(res), flush=True)
            if not passes(res, 6) and backbone != "squeezenet1_1":
                break
    return summary


def tune():
    manifest = json.loads((ROOT / "bench" / "manifest-v1.json").read_text())
    tune_covers = [c["id"] for c in manifest["covers"] if c["split"] == "tune" and c["id"] != "china_sky"]
    for (backbone, cap), rungs in backbone_ladder().items():
        if backbone == "squeezenet1_1":
            continue
        passed = [p for p in rungs if passes(result(RUNS / "screen" / p.name), 6)]
        for profile in reversed(passed):
            res = run(profile, "tune", tune_covers)
            scr = result(RUNS / "screen" / profile.name)
            ok = res["ok"] + scr["ok"] == 12 and res["n"] + scr["n"] == 12
            median = statistics.median(_times(RUNS / "screen" / profile.name) + _times(RUNS / "tune" / profile.name))
            print("TUNE", profile.name, json.dumps(res), f"12/12={ok} median12={median:.0f}s", flush=True)
            if ok and median <= BUDGET_S:
                print("CANDIDATE", backbone, cap, profile.name, profile.capacity, flush=True)
                break
        else:
            print("CANDIDATE", backbone, cap, None, flush=True)


def _times(out):
    return [json.loads(line)["encode_s"] for line in (out / "encode.jsonl").open()]


def report():
    for split in ("screen", "tune"):
        for d in sorted((RUNS / split).glob("*")):
            print(split, d.name, json.dumps(result(d)))


if __name__ == "__main__":
    {"screen": screen, "tune": tune, "report": report}[sys.argv[1]]()
