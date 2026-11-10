# Ghostframe PNG benchmark

What was measured, on which images, under which rule, and how to reproduce it. The decision
rule was committed before any held-out image was encoded: [bench/PREREGISTRATION.md](../bench/PREREGISTRATION.md).
Profiles and the frame format: [PNG_PROFILES.md](PNG_PROFILES.md).

## Summary

| Cap (RGB levels per channel) | Profile | Payload | Held-out success (41 covers × 3 frames) | Wilson 95 % | Status |
|---:|---|---:|---:|---|---|
| 2 | `sw-l2-c10x8b16p48` | 79 B | 123/123 | 97.0–100 % | recommended experimental |
| 8 | `sw-l8-c10x8b40p64` | 302 B | 123/123 | 97.0–100 % | recommended experimental |
| 2 | legacy 49-byte capacity profile | 49 B | 41/41 (frame 0) | 91.4–100 % | legacy research profile |
| 8 | legacy 161-byte capacity profile | 161 B | 41/41 (frame 0) | 91.4–100 % | legacy research profile |
| 8 | legacy v1 CLI frame (`Meet at dawn.`) | 13 B | 41/41 (frame 0) | 91.4–100 % | default showcase frame |

Both finalists met the preregistered promotion rule: observed success ≥ 95 %, cover-clustered
bootstrap lower bound ≥ 85 % (it is 100 %: no cover failed), and no paired frame-0 losses
against the matched-cap legacy baseline (0 losses, 0 wins: every arm succeeded on every
held-out cover). With zero failures on 41 covers, the data are consistent with a per-cover
failure rate up to about 7 % (rule of three); they do not show the rate is zero.

**At equal held-out reliability, the finalists carry 1.6× (cap 2) and 1.9× (cap 8) the payload
of the legacy capacity profiles.** The cost is distortion within the same cap, chiefly at cap 8
(median PSNR 35.0 vs 38.6 dB), and roughly 1.4–1.8× the median encode time.

The legacy 49-byte claim does not generalize to small covers: it authenticated on 2 of the 6
screening covers (it failed `astronaut`, `chelsea`, `coffee` and `rocket`, 300–640 px; raw
byte errors 16–24 against a 12-byte correction budget) although it passed all 41 held-out
covers, which are 1280 px wide. The archive's 3/3 used three covers on which it passes. The
2-level finalist passed all 12 in-contract screening and tuning covers, including those four.
The held-out set therefore does not test small covers; see [the exploratory 640-px
check](#exploratory-held-out-covers-at-640-px).

## Protocol

- **Covers.** `bench/manifest-v1.json` pins every cover by SHA-256 and assigns splits by
  source image: screen (6, scikit-image), tune (7, scikit-image and `examples/`), holdout (41
  Wikimedia Commons PD/CC0 1280-px thumbnails: food, people, animals, architecture, night,
  text, macro, textiles, landscapes), stress (9: page and text renders, flat black and white,
  colour bars, gradients, odd-size noise, the 160×128 minimum). Kodak was planned but its host
  returned a bot challenge; it was not worked around.
- **Calibration.** The centering mean (`ghostframe_png/data/squeezenet1_1-tile-mean-v1.npy`)
  uses screen and tune tiles only.
- **Payloads.** Random bytes at the profile's full capacity, deterministic per trial id, fresh
  random salt per frame. The fixed-13 arm carries the same 13-byte payloads through the cap-8
  finalist.
- **Success.** A separate process (`bench/decode_worker.py`) that is given only the saved PNG,
  the profile and the passphrase file must authenticate and return exactly the payload, and the
  saved pixels must be within the cap. An encode that refuses to write output counts as a
  failure.
- **Environment.** CPU, 4 threads, torch 2.7.1, torchvision 0.22.1 SqueezeNet 1.1 checkpoint
  `b8a52dc0…`, a 4-vCPU VPS that also runs other services (load average 4–5 during parts of
  the runs). Timings include that contention.

## Selection (screen and tune only)

| Candidate | Cap | Payload | Screen | Tune | Median encode | Outcome |
|---|---:|---:|---:|---:|---:|---|
| `sw-l2-c10x8b16p48` | 2 | 79 B | 6/6 | 6/6 in-contract | 42 s | **finalist** |
| `sw-l2-c10x8b20p48` | 2 | 119 B | 6/6 | failed `china` | — | rejected |
| `sw-l2-c12x10b12p36` | 2 | 111 B | 6/6 | failed `china` | — | rejected |
| `sw-l2-c10x8b16p32` | 2 | 95 B | 6/6 | failed `china` | — | rejected |
| `sw-l2-c12x10b16p56` | 2 | 151 B | 6/6 | not run | 94 s | over the 90 s budget |
| `png-l2-c10x8b12` | 2 | 63 B | 6/6 | 6/6 | 34 s | smaller fallback |
| `sw-l2-c8x6b20p32` | 2 | 55 B | 6/6 | 6/6 | 26 s | smaller fallback |
| `sw-l8-c10x8b40p64` | 8 | 302 B | 6/6 | 6/6 in-contract | 62 s | **finalist** |
| `sw-l8-c12x10b32p72` | 8 | 374 B | 6/6 | 6/6 | 93 s | over the 90 s budget |
| `sw-l8-c12x10b40p96` | 8 | 470 B | 6/6 | not run | 98 s | over the 90 s budget |
| `sw-l8-c14x12b32p96` | 8 | 542 B | 6/6 | not run | 134 s | over the 90 s budget |

Names: `sw` sweep, `c10x8` tile grid, `b16` bits per tile, `p48` Reed–Solomon parity bytes.
`china_sky` (245×125) is below every 10×8 grid's 160×128 minimum and is rejected as input
(Amendment 1); it is not a channel failure. The 2-level limit at this layout is the flat,
bright sky of `china`: 9–15 tiles stayed below the margin at 95–119 B.

### Ablations (screen, 6 covers, matched settings)

| Change | Cap | Success | Raw wrong bytes median / max | Median encode |
|---|---:|---:|---|---:|
| centered directions (63 B) | 2 | 6/6 | 1.5 / 4 | 36 s |
| uncentered directions (63 B) | 2 | 6/6 | 7 / 11 | 64 s |
| centered directions (239 B) | 8 | 6/6 | 0 / 0 | 47 s |
| uncentered directions (239 B) | 8 | 6/6 | 2.5 / 9 | 60 s |
| margin 0.005 or 0.02, learning rate 0.5 or 2 | 2 | 6/6 each | no consistent difference | — |

SqueezeNet's pooled features are non-negative, so an uncentered ±1 direction mostly measures
the average embedding: on clean tiles 11 % of directions read the same sign more than 90 % of
the time. Removing the calibration mean is what made the extra capacity reachable.

## Held-out results

### Reliability and distortion (frame 0–2 for finalists, frame 0 for baselines)

| Arm | Trials | Success | Raw wrong bytes median / max | PSNR median / min | SSIM median / min | Mean abs change | Encode p50 / p90 / max |
|---|---:|---:|---|---|---|---:|---|
| `sw-l2-c10x8b16p48`, 79 B | 123 | 123 | 0 / 17 (parity 48) | 42.9 / 42.7 dB | 0.979 / 0.955 | 1.73 | 30 / 48 / 264 s |
| legacy 49 B | 41 | 41 | 0 / 12 (parity 24) | 43.6 / 43.3 dB | 0.981 / 0.959 | 1.55 | 21 / 47 / 55 s |
| `sw-l8-c10x8b40p64`, 302 B | 123 | 123 | 0 / 9 (parity 64) | 35.0 / 33.5 dB | 0.885 / 0.746 | 3.91 | 41 / 52 / 68 s |
| `sw-l8-c10x8b40p64`, 13 B | 41 | 41 | 0 / 8 | 35.0 / 33.5 dB | 0.887 / 0.748 | 3.91 | 40 / 46 / 65 s |
| legacy 161 B | 41 | 41 | 0 / 1 (parity 32) | 38.6 / 35.6 dB | 0.949 / 0.823 | 2.54 | 23 / 30 / 40 s |
| legacy v1, 13 B | 41 | 41 | 0 / 0 (no parity) | 36.5 / 34.8 dB | 0.924 / 0.781 | 3.27 | 24 / 28 / 36 s |

Every finalist encode was accepted on its first attempt (no fresh-salt retry). The 264 s
maximum was the first trial of the run, with no repair round, and reflects load at start-up.
Lowest SSIM: the `insect_macro` cover at cap 8 (0.746), a smooth out-of-focus background.
Fixed-payload comparison: at cap 8 the finalist carried the 13-byte payloads on 41/41 covers,
as did legacy v1, but with more distortion (PSNR 35.0 vs 36.5 dB), because it fills all 400
coded bytes regardless of message length. For a 13-byte message, legacy v1 is the better choice.

Peak memory: encode ≤ 1.36 GB RSS, decode ≤ 1.36 GB (one process decoding a batch); median
decode 2.3 s per image after a 3 s model load.

### Paired frame-0 comparison

| Cap | Finalist vs baseline | Both succeed | Finalist only (win) | Baseline only (loss) | Both fail |
|---:|---|---:|---:|---:|---:|
| 2 | 79 B vs legacy 49 B | 41 | 0 | 0 | 0 |
| 8 | 302 B vs legacy 161 B | 41 | 0 | 0 | 0 |
| 8 | 13 B fixed payload vs legacy v1 13 B | 41 | 0 | 0 | 0 |

### Stress covers (reported separately)

| Profile | Success | Failures (all clean refusals: no output written) |
|---|---:|---|
| `sw-l2-c10x8b16p48` | 3/9 | `colour_bars`, `flat_black`, `flat_white`, `minimum_160x128`, `noise_odd`, `page` |
| `sw-l8-c10x8b40p64` | 6/9 | `colour_bars`, `minimum_160x128`, `noise_odd` |

No stress trial produced a PNG that failed to decode: the encoder refused instead. Refusals are
slow (6–10 minutes of repair rounds before giving up). Flat and saturated images cannot move at
a 2-level cap without clipping; the 160×128 minimum gives 16×16 tiles, too few pixels for 16 or
40 bits each.

## Detectability

A declared protocol-aware detector (`bench/detect.py`) knows the public profile but not the
passphrase. It computes the fraction of carrier scores with |score| < 0.002 on each held-out
cover, clean and marked (frame 0, 41 pairs per profile).

| Profile | AUC | Clean median / min | Marked median / max |
|---|---:|---|---|
| `sw-l2-c10x8b16p48` | 1.00 | 4.1 % / 2.3 % | 0.0 % / 1.8 % |
| `sw-l8-c10x8b40p64` | 1.00 | 4.0 % / 3.2 % | 0.0 % / 0.3 % |

The detector separates every clean cover from every marked one. This follows from the design:
the encoder pushes every score past a margin. Anyone who has the public reader can tell that an
image carries a frame for these profiles. Without the passphrase they cannot read it or forge it.
No steganographic claim is made.

## Determinism across thread counts

Every held-out finalist PNG (246) was decoded again in a fresh worker process with one CPU
thread instead of four. All 246 authenticated, and the raw received codeword bytes matched the
four-thread decode exactly, before error correction (`decode-threads1*.jsonl`). The showcase
fixtures were also decoded at both thread counts through the CLI. These checks cover one CPU
and one torch build. Other hardware, BLAS builds or GPUs are untested. The 2·10⁻³ safety
margin is meant to absorb those differences, but that has not been demonstrated.

## Reproduce

```sh
uv venv && uv pip install -e '.[tiled]'
python -m bench.build_manifest          # fetches covers, checks SHA-256 against the manifest
python -m tools.calibrate               # optional: recomputes the pinned calibration mean
SPLIT=screen bench/screen.sh            # screening suites
bench/holdout.sh sw-l2-c10x8b16p48 sw-l8-c10x8b40p64
python -m bench.summarize runs/holdout-finalists --by-cover
python -m bench.detect runs/holdout-finalists --profile sw-l2-c10x8b16p48 --out runs/detect-l2.json
```

Raw per-trial records (encode and independent decode, including failures and refusals) are in
`bench/results/`, one directory per run, with a `summary.json` per run directory.
Marked PNGs are not committed (1.2 GB); rerunning regenerates them with fresh salts.
