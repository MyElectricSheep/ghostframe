#!/usr/bin/env bash
# Post-hoc exploratory split (not preregistered): the holdout covers at 640 px wide.
# Tests whether the 1280-px holdout is easier than the small screening covers. No selection on it.
#   python -m bench.derive_small && bench/holdout640.sh
set -euo pipefail
cd "$(dirname "$0")/.."
.venv/bin/python -m bench.run --suite sw-l2-c10x8b16p48,legacy-49B,sw-l8-c10x8b40p64,legacy-161B \
  --split holdout640 --manifest bench/manifest-holdout640-v1.json --frames 1 --out runs/holdout640
