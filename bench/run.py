"""Encode benchmark trials, then decode every saved PNG in a fresh worker process.

    python -m bench.run --suite centering-l2 --split screen --frames 1 --out runs/centering-l2

Trials are appended to OUT/encode.jsonl and skipped when already present, so an
interrupted run resumes. Every attempted encode is recorded, including failures.
Payloads and salts are derived from the trial key here, in benchmark code only.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import resource
import subprocess
import sys
from time import perf_counter

import numpy as np
from PIL import Image
import torch

from bench.configs import LEGACY, PASSPHRASE, spec, suites
from ghostframe_png import core

ROOT = Path(__file__).resolve().parents[1]
UTF8 = "Встреча на рассвете. 夜明けに会いましょう。 Rendez-vous à l'aube ✓ "


def payload(kind, length, key):
    stream = hashlib.shake_256(f"payload/{key}".encode()).digest(max(length, 1))
    if kind == "random":
        return stream[:length]
    if kind == "ascii":
        return bytes(65 + b % 26 for b in stream[:length])
    if kind == "utf8":
        text = (UTF8 * (length // len(UTF8.encode()) + 2)).encode()[:length]
        return text.decode("utf-8", "ignore").encode()
    raise ValueError(kind)


def covers(split, only=None):
    manifest = json.loads((ROOT / "bench" / "manifest-v1.json").read_text())
    for entry in manifest["covers"]:
        if entry["split"] == split and (not only or entry["id"] in only):
            path = ROOT / manifest["covers_dir"] / entry["file"]
            if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
                raise RuntimeError(f"Cover hash mismatch: {entry['id']}")
            yield entry, path


def distortion(cover, marked):
    from skimage.metrics import peak_signal_noise_ratio, structural_similarity

    diff = np.abs(marked.astype(np.int16) - cover.astype(np.int16))
    hist = np.bincount(diff.ravel(), minlength=9)[:9]
    return dict(max_per_channel=diff.reshape(-1, 3).max(0).tolist(), mean_abs=float(diff.mean()),
                changed_pixel_frac=float((diff.max(-1) > 0).mean()), delta_hist=hist.tolist(),
                psnr=float(peak_signal_noise_ratio(cover, marked, data_range=255)) if diff.any() else None,
                ssim=float(structural_similarity(cover, marked, channel_axis=-1, data_range=255)))


def encode_legacy(name, cover_path, message, model):
    from experiments import neural_png_capacity as cap
    from experiments import tiled, tiled_ecc
    from ghostframe import read_image
    from reedsolo import RSCodec

    config = LEGACY[name]
    image = read_image(cover_path)
    if config["kind"] == "v1":
        codeword = tiled.seal(message, PASSPHRASE)
        marked = tiled.embed_tiles(image, tiled.bit_string(codeword), model, 8)
    elif config["kind"] == "v2":
        codeword = bytes(RSCodec(tiled_ecc.PARITY_BYTES).encode(tiled_ecc.seal(message, PASSPHRASE)))
        marked = tiled.embed_tiles(image, tiled.bit_string(codeword), model, 2)
    else:
        cols, rows, bits, parity, _ = cap.PROFILES[config["profile"]]
        frame = cap.seal(message, cols * rows * bits // 8 - parity, config["profile"])
        codeword = bytes(RSCodec(parity).encode(frame)) if parity else frame
        marked = cap.mark_codeword(model, image, config["profile"], codeword, config["epsilon"], config["steps"])
    buffer = io.BytesIO()
    marked.save(buffer, format="PNG")  # The legacy writers' own serialization.
    return buffer.getvalue(), codeword, np.asarray(image)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", required=True, help="suite name from bench.configs, or comma-separated legacy names")
    parser.add_argument("--split", required=True)
    parser.add_argument("--covers", nargs="*")
    parser.add_argument("--frames", type=int, default=1)
    parser.add_argument("--kind", default="random", choices=("random", "ascii", "utf8"))
    parser.add_argument("--length", type=int, help="fixed payload length; default is each profile's capacity")
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--no-decode", action="store_true")
    args = parser.parse_args()
    torch.set_num_threads(args.threads)
    from ghostframe import load_model

    model = load_model("cpu")
    known = {p.name: p for suite in suites().values() for p in suite} | dict(core.PROFILES)
    profiles = suites().get(args.suite) or [n if n in LEGACY else known[n] for n in args.suite.split(",")]
    (args.out / "png").mkdir(parents=True, exist_ok=True)
    log = args.out / "encode.jsonl"
    done = {json.loads(line)["trial"] for line in log.open()} if log.exists() else set()
    passphrase_file = args.out / "passphrase.txt"
    passphrase_file.write_bytes(PASSPHRASE)
    jobs = []
    for entry, path in covers(args.split, args.covers):
        for profile in profiles:
            name = profile if isinstance(profile, str) else profile.name
            capacity = LEGACY[name]["capacity"] if isinstance(profile, str) else profile.capacity
            length = capacity if args.length is None else args.length
            for frame_index in range(args.frames):
                trial = f"{name}|{entry['id']}|{args.kind}{length}|f{frame_index}"
                png = args.out / "png" / (hashlib.sha256(trial.encode()).hexdigest()[:16] + ".png")
                job = dict(trial=trial, png=str(png), profile=name, passphrase_file=str(passphrase_file))
                if not isinstance(profile, str):
                    job["spec"] = spec(profile)
                if trial in done:
                    if png.exists():
                        jobs.append(job)
                    continue
                message = payload(args.kind, length, f"{entry['id']}|{args.kind}{length}|f{frame_index}")
                row = dict(trial=trial, profile=name, cover=entry["id"], split=args.split, frame=frame_index,
                           kind=args.kind, payload_bytes=len(message), threads=args.threads,
                           message=message.hex())
                if length > capacity:
                    row.update(status="over_capacity")
                else:
                    t = perf_counter()
                    report, codeword = {}, None
                    try:
                        if isinstance(profile, str):
                            row["epsilon"] = LEGACY[name]["epsilon"]
                            data, codeword, cover = encode_legacy(name, path, message, model)
                        else:
                            row["epsilon"] = profile.epsilon
                            info = {}
                            cover = core.load_cover(path, info)
                            row["colour_conversion"] = info.get("colour_conversion")
                            salt = hashlib.sha256(f"salt/{trial}".encode()).digest()[:core.SALT_BYTES]
                            data = core.encode_message(cover, message, PASSPHRASE, profile, model,
                                                       report=report, _salt=salt)
                            codeword = report["codeword"]
                        row["status"] = "encoded"
                    except (core.CapacityError, core.InputError, ValueError) as exc:
                        row["status"] = f"encode_failed: {type(exc).__name__}: {exc}"
                        data, codeword = None, report.get("codeword")
                    row["encode_s"] = perf_counter() - t
                    row["attempts"] = report.get("attempts", [])
                    row["coded_bytes"] = len(codeword) if codeword else None
                    row["codeword"] = codeword.hex() if codeword else None
                    if data is not None:
                        png.write_bytes(data)
                        marked = np.asarray(Image.open(png).convert("RGB"))
                        row.update(distortion(cover, marked))
                        jobs.append(job)
                row["peak_rss_mb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
                with log.open("a") as handle:
                    handle.write(json.dumps(row) + "\n")
                print(trial, row["status"][:60], f"{row.get('encode_s', 0):.0f}s", flush=True)
    if jobs and not args.no_decode:
        decoded = {json.loads(line)["png"] for line in (args.out / "decode.jsonl").open()} \
            if (args.out / "decode.jsonl").exists() else set()
        pending = [j for j in jobs if j["png"] not in decoded]
        if pending:
            jobs_file = args.out / "decode-jobs.json"
            jobs_file.write_text(json.dumps([{k: v for k, v in j.items() if k != "trial"} for j in pending]))
            subprocess.run([sys.executable, "-m", "bench.decode_worker", str(jobs_file),
                            str(args.out / "decode.jsonl"), "--threads", str(args.threads)], check=True, cwd=ROOT)


if __name__ == "__main__":
    main()
