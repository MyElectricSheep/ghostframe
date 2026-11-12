# Experiments

## Setup

Linux x86-64, AMD EPYC 9V74 CPU, 8 CPU-equivalent quota, 8 GiB memory limit, no GPU used. Python 3.12.14, PyTorch 2.7.1+cpu, Torchvision 0.22.1+cpu. Four intra-op threads during benchmarks. Model setup and file I/O are excluded from the timing columns. First calls can incur runtime warm-up. The checkpoint is SqueezeNet 1.1 ImageNet1K V1, verified by full SHA-256. It supplies the frozen convolutional trunk with 512 pooled features.

Each cover and bit length received one deterministic pseudo-random payload with seed 42 and one experimental key. The three independent covers are a portrait, a landscape with architecture, and a textured flower. The sky is a crop of the landscape and acts as a separate low-detail stress case. Default optimization allows up to 100 Adam updates, a target margin of 0.035, and eight 8-bit levels of change per RGB channel. JPEG uses Pillow with 4:2:0 chroma subsampling. See the README for exact commands and examples/ATTRIBUTION.md for sources.

## Eight-level baseline

Error columns count wrong bits. A zero is an exact recovery. PSNR and SSIM compare the original RGB pixels against the reopened PNG.

| Cover | Bits | PNG | JPEG 95 / 85 / 70 | 75% resize | 90% center crop | +5% brightness | PSNR dB | SSIM | Max / mean delta | Encode s | Decode ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| grace_hopper.jpg | 16 | 0 | 0 / 0 / 0 | 0 | 2 | 0 | 41.73 | 0.974 | 3 / 1.94 | 0.72 | 139.4 |
| grace_hopper.jpg | 32 | 0 | 0 / 0 / 0 | 0 | 14 | 0 | 33.23 | 0.864 | 8 / 4.88 | 2.21 | 16.8 |
| china.jpg | 16 | 0 | 0 / 0 / 0 | 0 | 6 | 0 | 37.09 | 0.945 | 7 / 3.13 | 0.65 | 12.3 |
| china.jpg | 32 | 0 | 0 / 0 / 0 | 0 | 12 | 0 | 34.11 | 0.906 | 8 / 4.31 | 0.80 | 22.4 |
| flower.jpg | 16 | 0 | 0 / 0 / 0 | 0 | 4 | 0 | 37.75 | 0.898 | 7 / 2.77 | 1.04 | 14.3 |
| flower.jpg | 32 | 0 | 0 / 0 / 0 | 0 | 15 | 0 | 33.91 | 0.805 | 8 / 4.27 | 1.53 | 18.3 |
| china-sky.png | 16 | 0 | 0 / 5 / 6 | 0 | 4 | 5 | 36.11 | 0.810 | 8 / 3.18 | 0.47 | 25.0 |
| china-sky.png | 32 | 0 | 4 / 10 / 14 | 6 | 15 | 11 | 35.07 | 0.768 | 8 / 3.60 | 2.83 | 14.0 |

All eight payloads decoded exactly in memory and after PNG serialization. The wrong key produced 7–18 errors per case, and the unmodified covers also yielded incorrect payloads. Those controls illustrate that the raw decoder always emits bits. PNG yielded 192/192 bits. JPEG at quality 70 yielded 172/192 bits and 6/8 complete payloads, with all 20 errors from the sky stress case. Center cropping broke all eight payloads.

At 32 bits, the marked images show visible fine texture, especially on smooth backgrounds and sky. The default 32-bit setting therefore fails the original fidelity goal even though it recovers every PNG payload. See benchmarks/comparison-32bit.jpg, whose columns are original, marked and 24× absolute difference.

## Tighter pixel budgets

| Maximum RGB change | PNG exact | JPEG 70 exact | JPEG 70 errors | Crop exact | 32-bit PSNR range |
|---:|---:|---:|---:|---:|---:|
| 2 levels | 8/8 | 2/8 | 42/192 | 0/8 | 42.60–44.55 dB |
| 4 levels | 8/8 | 5/8 | 21/192 | 0/8 | 37.51–39.26 dB |
| 8 levels | 8/8 | 6/8 | 20/192 | 0/8 | 33.23–35.07 dB |

The 2-level run also recovered every PNG payload and reduced pixel distortion substantially. Its JPEG 70 failures include every 32-bit payload. The 2- and 4-level runs reused the same covers, key and payloads to isolate the pixel budget. They are paired comparisons on a small sample.

## Independent decoding and scope

All eight 8-level outputs recovered exactly when decoded in fresh processes using one CPU thread. The installed CLI also independently recovered the README example, and both unit tests passed. Device-to-device reproducibility, LPIPS, screenshots, and real social-media pipelines were outside the measured set.

The PNG channel is worth pursuing. The next experiment is crop-aware optimization versus the clean-only baseline at the same 2-level budget, scored on held-out crop locations and several keys and messages per cover. The current payload and visual results justify research only.
