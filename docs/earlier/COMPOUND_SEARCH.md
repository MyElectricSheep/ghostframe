# Compound JPEG recovery

The 26-byte CLI now supports `--crop-size WIDTH HEIGHT` alongside `--original-size WIDTH HEIGHT`. Crop size means the dimensions after cropping and before resizing. The decoder restores the received image to that size using Lanczos, then runs the existing bounded crop-offset search. The crop offset does not need to be supplied. Confidence-assisted decoding is optional. The authenticated frame format remains compatible with existing files.

This benchmark uses the same 14 covers as the final sweep, with a new randomized 96-byte frame carrying the 25-byte test message on each. It writes JPEG 95, removes 13 pixels from the left, 21 from the top, 17 from the right and 9 from the bottom, then resizes the crop to 75% or 67% using Lanczos and saves it as JPEG 70. Both decoder modes read the same saved JPEG. The clean control undergoes the same 75% chain without a payload. The decoder receives both dimension pairs but does not receive the actual offset. One randomized frame and one crop geometry per cover make this a controlled local test.

Run `python -m experiments.compound_search` to reproduce. Per-cover results are in `benchmarks/compound-search/results.json`.

| File condition | Regular | With confidence retries | Median regular | Median with retries |
|---|---:|---:|---:|---:|
| Crop → 75% resize → JPEG 70 | 12/14 | 12/14 | 0.52 s | 0.53 s |
| Crop → 67% resize → JPEG 70 | 8/14 | 8/14 | 0.46 s | 0.57 s |
| Clean control | 0/14 | 0/14 | 0.10 s | 0.17 s |

A separate process authenticated the 25-byte message from the included demo JPEG with `--original-size 512 512 --crop-size 482 482 --soft`. The public demo passphrase is `ghostframe public benchmark fixture`. Confidence retries produced no gain in these compound trials. This mode assumes the crop dimensions before resizing are available and tests one edit order and resampling kernel. All 23 automated tests passed.
