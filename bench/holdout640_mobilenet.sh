#!/usr/bin/env bash
# Post-hoc exploratory split (not preregistered): the MobileNetV3-Small demo profiles on the
# holdout covers at 640 px wide, one frame each, as bench/holdout640.sh did for SqueezeNet.
set -euo pipefail
cd "$(dirname "$0")/.."
.venv/bin/python -m bench.run --suite bb-mobilenet_v3_small-l2-b16p48,bb-mobilenet_v3_small-l8-b64p112 \
  --split holdout640 --manifest bench/manifest-holdout640-v1.json --frames 1 --out runs/holdout640-mobilenet
