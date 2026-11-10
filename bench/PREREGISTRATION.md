# Ghostframe PNG benchmark: preregistered decision rule

Written 2026-11-10 before any held-out cover was encoded. Committed to git before the
held-out runs; the commit timestamp is the record.

## Primary success

A trial succeeds only when a separate decoder process (`bench/decode_worker.py`), given
only the saved PNG, the profile and the passphrase file, authenticates the frame and returns
exactly the application bytes, and the saved pixels are within the profile's per-channel cap.
Every attempted encode counts. An encode that refuses to write output (budget exhausted) is a
failure, not an exclusion.

## Splits

`bench/manifest-v1.json`, by source image: screen (6), tune (7), holdout (41 Wikimedia
Commons PD/CC0 files), stress (9 synthetic/line-art covers, reported separately, not part of
any headline). Calibration (`ghostframe_png/data/…-tile-mean-v1.npy`) uses screen+tune only.
No parameter is tuned on holdout or stress results.

## Finalist selection (screen + tune only)

For each primary cap (2 and 8 RGB levels), the finalist is the largest-capacity configuration
that

1. succeeds on every screen and tune cover (13/13, one frame each), and
2. has a median encode time of at most 90 s at 4 threads on the reference box.

Ties go to the smaller coded size, then the faster encode.

## Holdout evaluation

- Finalists: 41 covers × 3 independently sealed frames (fresh salt per frame; random payload
  at full capacity).
- Baselines on the same covers, frame 0 only (compute): legacy 49-byte profile at cap 2,
  legacy 161-byte profile at cap 8, legacy v1 13-byte CLI frame at cap 8.
- Fixed-payload comparison at cap 8: the cap-8 finalist carrying the same 13-byte payload as
  the v1 baseline, frame 0.

## Reliability target and promotion

Target: ≥ 95 % observed success on holdout. Report the Wilson 95 % interval over trials and a
cover-clustered bootstrap interval. A finalist is promoted from "candidate" to "recommended
experimental profile" when, on holdout,

- its observed success is ≥ 95 % and its cluster-bootstrap lower bound is ≥ 85 %, and
- on frame 0 its paired losses against the matched-cap baseline (covers where the baseline
  succeeds and the finalist fails) number no more than its paired wins.

No profile becomes the CLI default on this evidence: the default remains the verified
`legacy-v1` showcase frame. If any holdout failure is inspected to change a profile, the
changed profile cannot be re-scored on this holdout set.

## Amendment 1 (2026-11-10, after screening, before any tuning-split encode)

`china_sky` (245×125, tuning split) is below the documented minimum size (16-pixel tiles) of
every 10×8 or larger grid, including the legacy 49- and 161-byte profiles. A clean size
rejection is part of the input contract, not a channel failure, so finalist selection uses the
12 in-contract screen+tune covers and reports the rejection separately. Holdout covers are all
at least 1280×826, so this changes nothing there.

## Finalists (recorded before the holdout run)

| Cap | Finalist | Payload | Screen+tune (in-contract) | Median encode | Rejected larger candidates |
|---|---|---:|---:|---:|---|
| 2 | `sw-l2-c10x8b16p48` | 79 B | 12/12 | 42 s | 119 B, 111 B, 95 B failed `china`; 151 B 94 s on screen |
| 8 | `sw-l8-c10x8b40p64` | 302 B | 12/12 | 62 s | 374 B 12/12 but 93 s; 470 B, 542 B > 90 s on screen |
