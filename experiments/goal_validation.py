"""Recheck authenticated neural fixtures across independent CPU processes."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

import torch

from experiments.encoder_screen import build
from experiments.message_cli import neural_recover
from experiments.tiled import PASSWORD
from ghostframe import load_model, read_image

OUT = Path("benchmarks/goal-validation")
FIXTURES = (
    ("benchmarks/tiled/astronaut-8.png", False, b"Meet at dawn."),
    ("benchmarks/tiled/coffee-8.png", False, b"Meet at dawn."),
    ("benchmarks/tiled/rocket-8.png", False, b"Meet at dawn."),
    ("benchmarks/tiled/chelsea-8.png", False, b"Meet at dawn."),
    ("benchmarks/tiled-ecc/coffee.png", True, b"!"),
    ("benchmarks/tiled-ecc/camera.png", True, b"!"),
)


def worker(threads):
    torch.set_num_threads(threads)
    model, other = load_model("cpu"), build("resnet18")
    rows = []
    for path, ecc, expected in FIXTURES:
        image = read_image(path)
        outcomes = {}
        for label, candidate, password in (
            ("correct", model, PASSWORD), ("wrong_passphrase", model, b"wrong"),
            ("wrong_checkpoint", other, PASSWORD),
        ):
            try:
                outcomes[label] = neural_recover(image, password, candidate, ecc=ecc) == expected
            except ValueError:
                outcomes[label] = False
        rows.append(dict(fixture=path, threads=threads, outcomes=outcomes))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", type=int, choices=(1, 4))
    args = parser.parse_args()
    if args.worker:
        print(json.dumps(worker(args.worker)))
        return
    OUT.mkdir(parents=True, exist_ok=True)
    records = []
    for threads in (1, 4):
        raw = subprocess.check_output([sys.executable, "-m", "experiments.goal_validation",
                                       "--worker", str(threads)])
        records.extend(json.loads(raw))
    (OUT / "cpu-restarts.json").write_text(json.dumps(records, indent=2) + "\n")
    assert all(row["outcomes"] == dict(correct=True, wrong_passphrase=False,
                                      wrong_checkpoint=False) for row in records)
    print(f"{len(records)} authenticated restart decodes and {len(records)*2} rejected controls")


if __name__ == "__main__":
    main()
