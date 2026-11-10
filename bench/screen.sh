#!/usr/bin/env bash
# Phase-3 screening runs on the screening split. Each suite resumes if interrupted.
set -euo pipefail
cd "$(dirname "$0")/.."
run() { .venv/bin/python -m bench.run --split "${SPLIT:-screen}" --frames 1 "$@"; }
for suite in "$@"; do
  case "$suite" in
    legacy) run --suite legacy-49B,legacy-161B,legacy-v1-13B --out runs/screen-legacy ;;
    *) run --suite "$suite" --out "runs/screen-$suite" ;;
  esac
done
