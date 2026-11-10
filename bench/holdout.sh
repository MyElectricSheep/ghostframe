#!/usr/bin/env bash
# Preregistered holdout evaluation (bench/PREREGISTRATION.md). Resumable: rerun to continue.
#   bench/holdout.sh L2_FINALIST L8_FINALIST
# Order: frame 0 for every arm first (paired comparison), then frames 1-2 for finalists,
# then the stress split, so a partial run still yields a matched frame-0 comparison.
set -euo pipefail
cd "$(dirname "$0")/.."
l2="$1"; l8="$2"
run() { .venv/bin/python -m bench.run "$@"; }
run --suite "$l2,$l8" --split holdout --frames 1 --out runs/holdout-finalists
run --suite legacy-49B,legacy-161B,legacy-v1-13B --split holdout --frames 1 --out runs/holdout-legacy
run --suite "$l8" --split holdout --frames 1 --length 13 --out runs/holdout-fixed13
run --suite "$l2,$l8" --split holdout --frames 3 --out runs/holdout-finalists
run --suite "$l2,$l8" --split stress --frames 1 --out runs/stress-finalists
