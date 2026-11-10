"""Independent decoder process. Receives only PNG paths, profiles and a passphrase file.

It never sees the cover, the expected message or the codeword. Usage:
    python -m bench.decode_worker JOBS.json OUT.jsonl [--threads N]
"""
import argparse
import json
from pathlib import Path
import resource
import sys
from time import perf_counter

import numpy as np
import torch


def legacy_received(png, config, model):
    from experiments import neural_png_capacity as cap
    from experiments import tiled
    from ghostframe import read_image

    image = read_image(png)
    if config["kind"] in ("v1", "v2"):
        return image, int(tiled.read_tiles(image, model), 2).to_bytes(tiled.FRAME_BYTES, "big")
    return image, cap.read_codeword(model, image, config["profile"])


def legacy_message(image, received, config, password, model):
    from experiments import neural_png_capacity as cap
    from experiments.message_cli import neural_recover

    if config["kind"] in ("v1", "v2"):
        return neural_recover(image, password, model, ecc=config["kind"] == "v2")
    return cap.recover(received, config["profile"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("jobs", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--threads", type=int, default=4)
    args = parser.parse_args()
    torch.set_num_threads(args.threads)
    started = perf_counter()
    from ghostframe import load_model
    from ghostframe_png import core
    from bench.configs import LEGACY, from_spec

    model = load_model("cpu")
    load_s = perf_counter() - started
    jobs = json.loads(args.jobs.read_text())
    with args.out.open("a") as out:
        for job in jobs:
            password = Path(job["passphrase_file"]).read_bytes()
            t = perf_counter()
            row = dict(png=job["png"], model_load_s=load_s, threads=args.threads)
            received, info = None, {}
            try:
                if job["profile"] in LEGACY:
                    config = LEGACY[job["profile"]]
                    image, received = legacy_received(job["png"], config, model)
                    message = legacy_message(image, received, config, password, model)
                else:
                    profile = from_spec(job["spec"])
                    info = {}
                    message = core.decode_message(core.load_png(job["png"]), password, profile, model, report=info)
                    received = info.pop("received")
                row.update(ok=True, message=message.hex())
            except Exception as exc:  # Record every failure; a failure never yields plaintext.
                row.update(ok=False, error=f"{type(exc).__name__}: {exc}")
                if received is None and job["profile"] not in LEGACY:
                    try:
                        profile = from_spec(job["spec"])
                        received = core.scores_to_bytes(core.read_scores(core.load_png(job["png"]), profile, model))[0]
                    except Exception:
                        pass
            row.update(decode_s=perf_counter() - t, received=None if received is None else bytes(received).hex(),
                       corrected_symbols=info.get("corrected_symbols"), erasures=info.get("erasures"),
                       peak_rss_mb=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024)
            out.write(json.dumps(row) + "\n")
            out.flush()
    print(f"decoded {len(jobs)} files", file=sys.stderr)


if __name__ == "__main__":
    main()
