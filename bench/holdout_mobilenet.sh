#!/usr/bin/env bash
# MobileNetV3-Small holdout (bench/PREREGISTRATION-BACKBONES.md, Amendment 2). Resumable.
set -euo pipefail
cd "$(dirname "$0")/.."
arms="bb-mobilenet_v3_small-l8-b64p112,bb-mobilenet_v3_small-l8-b40p64,bb-mobilenet_v3_small-l2-b16p48"
run() { .venv/bin/python -m bench.run "$@"; }
run --suite "$arms" --split holdout --frames 1 --out runs/holdout-mobilenet
run --suite "$arms" --split holdout --frames 3 --out runs/holdout-mobilenet
run --suite "$arms" --split stress --frames 1 --out runs/stress-mobilenet
