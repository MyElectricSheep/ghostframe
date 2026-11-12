# Ghostframe adversarial verification: final report

Date: 2026-11-10. Source: archive sha256 `b6cb7c14…`, imported as commit `7370fa0`. All work is
offline on a 4-vCPU Linux VPS with CPU-only PyTorch 2.7.1 and torchvision 0.22.1. The model is
the SqueezeNet 1.1 checkpoint `b8a52dc0…`. The demo site came later and is not covered here. The
13-byte "Meet at dawn." legacy frame remains the default.

## 1. Baseline audit

| Claim in the archive | How checked | Verdict |
|---|---|---|
| 26 tests pass | Ran them (`bench/results/logs/baseline-tests.log`) | Confirmed |
| "Meet at dawn." fixture decodes and its cover rejects | Fresh process, 1 and 4 threads; max delta 8/8/8 | Confirmed |
| "!" v2 fixture decodes at a 2-level cap | Same; max delta 2/2/2 | Confirmed |
| 161-byte fixture recovers `bytes(range(161))` | Same | Confirmed, but the weakest bit has a margin of 1.1·10⁻⁵ and 15 bits sit below 10⁻³, so it is fragile across numerical environments |
| 35 capacity trials | Re-derived from the raw JSON | Numbers match |
| 161 B at an 8-level cap, 3/3 | Rerun: screen 6/6, holdout 41/41 | Holds |
| 49 B at a 2-level cap, 3/3 | Rerun: screen **2/6** (fails four 300–640 px covers, 16–24 wrong bytes against a 12-byte budget); holdout 41/41 at 1280 px | **Size-dependent; the claim is overstated** |
| Encoded PNGs carry no metadata | Inspected chunks | **Broken:** the ECC demo path copied the source ICC profile into the output. Fixed |
| Capacity script supports larger frames | Constructed a 300-byte frame | **Broken:** above 255 − parity bytes the RS codeword silently grows (300 → 364 bytes) and no longer matches the layout. Fixed in the new code by multi-block RS; the legacy script is documented, not changed |
| Input handling | `bench/probe_inputs.py` | **Broken:** 16-bit, float and transparent images were silently flattened; the CLI could spend a full encode before discovering that the output directory was missing. Fixed |

Legacy fixes (`tests/test_legacy_fixes.py`, 3 tests, all failing on the original code):
- `read_image` rejects 16-bit, float and transparent images.
- `publish_encoded` writes pixels only.
- The encode commands check the output directory before encoding.

Legacy wire formats and decoding are unchanged. The original fixtures still decode.

## 2. What was built

- **`ghostframe_png`**: an embedding-only PNG carrier with explicit profiles and the
  `ghostframe-png` CLI. Exit codes are 0 success, 1 no authenticated message, 2 input or usage,
  3 capacity or budget. Legacy formats are reachable as the `legacy-v1` and `legacy-v2` profiles.
  Details are in [PNG_PROFILES.md](PNG_PROFILES.md).
  - Frame: salt ‖ AES-256-GCM, with scrypt deriving both the key and the nonce. The AAD is the
    full profile identity. Overhead is 33 bytes, against 47 for the legacy capacity frames.
  - Error correction: interleaved multi-block Reed–Solomon, with soft erasure retries. The
    decoder tries at most eight distinct salts.
  - **Centered carriers.** SqueezeNet features are non-negative, so random ±1 directions were
    biased: 11 % of bits were almost constant on clean tiles. Projecting out a pinned mean from
    the screen and tune covers fixed this. It is the main source of the capacity gain. Matched
    ablation at 63 B and a 2-level cap: median raw wrong bytes 1.5 against 7, encode 36 s
    against 64 s.
  - **Encoder**: batched, quantization-aware, per-tile Adam. It runs an explicit safety check on
    the reopened PNG (2·(wrong + at-risk bytes) ≤ parity in every block), does targeted repair
    rounds, then retries with a fresh salt. Output is written only after the saved file
    authenticates, and it never overwrites.
  - **Input contract**: PNG or JPEG up to 4 MP with EXIF orientation applied. Non-sRGB ICC
    profiles are converted with LittleCMS. Unsupported modes and transparency are rejected
    cleanly.
- **Benchmark harness** (`bench/`):
  - A hashed manifest with source-disjoint splits.
  - Resumable encode logs.
  - An independent decode worker that receives only the PNG, the profile and the passphrase
    file.
  - Wilson and cover-clustered bootstrap intervals.
  - A declared detector.
  - A preregistered decision rule, committed before the holdout run.

## 3. Results

The full tables are in [BENCHMARK.md](BENCHMARK.md). The headline is that the held-out
photographs are 1280 px wide: 41 covers, with 3 independently sealed frames per finalist.

| Cap | Profile | Payload | Holdout | Wilson 95 % | Median PSNR / SSIM | Median encode | Status |
|---:|---|---:|---:|---|---|---:|---|
| 2 | `sw-l2-c10x8b16p48` | **79 B** | 123/123 | 97.0–100 % | 42.9 dB / 0.979 | 30 s | recommended experimental |
| 8 | `sw-l8-c10x8b40p64` | **302 B** | 123/123 | 97.0–100 % | 35.0 dB / 0.885 | 41 s | recommended experimental |
| 2 | legacy 49 B | 49 B | 41/41 | 91.4–100 % | 43.6 dB / 0.981 | 21 s | legacy |
| 8 | legacy 161 B | 161 B | 41/41 | 91.4–100 % | 38.6 dB / 0.949 | 23 s | legacy |
| 8 | legacy v1 | 13 B | 41/41 | 91.4–100 % | 36.5 dB / 0.924 | 24 s | default |

- **Promotion rule met** for both finalists:
  - Observed success is ≥ 95 %.
  - The cluster lower bound is 100 %, against the required ≥ 85 %.
  - Paired frame-0 results show 0 losses and 0 wins, because every arm passed every cover.
- **Capacity gain** at equal measured reliability: 1.6× the legacy payload at a 2-level cap and
  1.9× at an 8-level cap.
- **Costs**:
  - The 8-level finalist distorts noticeably more within the same cap: PSNR −3.6 dB and SSIM
    0.885 against 0.949.
  - Encodes take 1.4–1.8× longer.
  - For short messages, legacy v1 is better, because the finalist always fills 400 coded bytes.
- **Thread determinism**: 246/246 held-out PNGs gave identical received bytes at 1 and 4
  threads. Only one CPU and one torch build were tested.
- **Detectability**: the protocol-aware detector reaches AUC 1.00 for both profiles, so the
  frame's presence is visible to anyone running the public reader. Only confidentiality and
  integrity are claimed.
- **Stress covers** (synthetic, flat and minimum size): 3/9 at a 2-level cap and 6/9 at an
  8-level cap. Every failure was a clean refusal with no output written, but refusals take 6–10
  minutes.
- **Small covers** (640 px, exploratory, after the fact): the 41 held-out covers resized to 640 px, one frame per arm.
  - 2-level cap: the 79 B finalist passed 40/41, and its one failure was a clean refusal. Legacy
    49 B passed only 28/41, and all 13 of its failures **wrote a PNG that does not decode**. On
    the same covers the finalist won 12 and lost 0.
  - 8-level cap: both 302 B and legacy 161 B passed 41/41.
  - Median encodes were slower than at 1280 px: 44 s and 52 s, with a long tail up to 16 min.
  - Details are in [BENCHMARK.md](BENCHMARK.md#exploratory-held-out-covers-at-640-px).
- **Newer backbone** (second preregistration, after the above): four torchvision backbones were
  screened against SqueezeNet on the same grid, ladder and 90 s budget. MobileNetV3-Small was
  held out (41 × 3) at three sizes, and all three passed 123/123:
  - **494 B at an 8-level cap**: 1.6× the SqueezeNet finalist, PSNR 34.1 dB / SSIM 0.872,
    median encode 33 s.
  - 302 B and 79 B: the same sizes as the finalists, with matching distortion and about 1.6×
    faster encodes (25 s and 19 s).
  - 640-px covers: 41/41 for both demo profiles (SqueezeNet 79 B was 40/41). The detector still reaches AUC 1.0.
  - Details are in [BENCHMARK.md](BENCHMARK.md#backbone-comparison-mobilenetv3-small).

## 4. Example fixtures

"Meet at dawn." remains the default example. The new fixtures are in
`benchmarks/embedding-showcase/`, listed in `fixtures-v2.json` with their hashes, and can be
regenerated with `python -m tools.make_showcase`.

| Fixture | Profile | Message | Measured max change | Difference image |
|---|---|---|---:|---|
| `png-l2-sentence.png` | `sw-l2-c10x8b16p48` | "Meet at dawn. The north gate stays open until six. Bring the blue notebook." (75 B) | 2/255 | ×96 |
| `png-l8-paragraph.png` | `sw-l8-c10x8b40p64` | 299-byte paragraph | 8/255 | ×24 |
| negative control `grace-hopper-original.png` | both | none: exit 1, no output | 0 | — |

Each fixture was checked with the public CLI in fresh processes:
- It decodes to the exact message at 1 and 4 threads.
- The unmarked cover exits 1 with no output.
- A wrong passphrase exits 1 with no output.

## 5. Withheld candidates

| Candidate | Why withheld |
|---|---|
| 2-level cap, 95 / 111 / 119 B | Failed the `china` tuning cover. 9–15 tiles in its flat bright sky never reached the margin |
| 2-level cap, 151 B | Median encode 94 s, over the preregistered 90 s budget |
| 8-level cap, 374 B | Passed 12/12 on screen and tune, but the median encode of 93 s was over budget. It is the most likely next step on faster hardware |
| 8-level cap, 470 / 542 B | Encodes of 98 s and 134 s, over budget |
| `png-l2-c10x8b12` (63 B), `png-l8-c10x8b24` (175 B) | Registered as experimental. Not held out, so not recommended |

## 6. Not done, and why

- **Content-adaptive allocation** (fewer bits on flat tiles). This is the obvious fix for the
  `china` and stress failures. It is untested.
- **Other frozen models.** Done afterwards; see §3. Still open:
  - ResNet-18 at 143 B (cap 2) qualified, but was not held out.
  - The MobileNetV3 ladder above 494 B.
  - DINOv2, which was left out to avoid running hub code.
  SqueezeNet remains the reader for the legacy frames and the `sw-` profiles.
- **PNG interoperability.** Re-serialization at other compression levels is covered by tests.
  Third-party encoders and colour-managed viewers re-saving with an ICC profile are not covered.
  JPEG, resizing and cropping are out of scope, and the profiles have no robustness to them.
- **Kodak covers.** The host served a bot challenge, which was not worked around. Wikimedia
  Commons PD/CC0 covers were used instead.
- **Timing.** The box ran other services at a load average of 4–8. Timings are upper-bound
  indications, not performance claims.

## 7. Reproduce

```sh
uv venv && uv pip install -e '.[tiled]'
python -m unittest discover -s tests                 # full suite
python -m bench.build_manifest                       # covers + SHA-256 check
bench/holdout.sh sw-l2-c10x8b16p48 sw-l8-c10x8b40p64 # preregistered holdout (≈6 h here)
python -m bench.summarize runs/holdout-finalists --by-cover
python -m tools.make_showcase                        # fixtures + negative controls
```

Raw per-trial encode and decode records, including every failure and refusal, are in
`bench/results/`. The decision rule and its amendment are in `bench/PREREGISTRATION.md`, and
its git history shows it was committed before the holdout run.
