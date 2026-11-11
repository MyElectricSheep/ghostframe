# Backbone screen: preregistered decision rule

Written 2026-11-11, before any encode with an alternative backbone. The git commit timestamp is
the record. The general rules in [PREREGISTRATION.md](PREREGISTRATION.md) apply unless this file
says otherwise. Those rules cover primary success, the independent decoder, the splits and
Amendment 1 (`china_sky` is out of contract).

## Question

Does a more recent frozen ImageNet backbone carry more bytes than SqueezeNet 1.1 under the same
caps, the same reliability bar and the same encode-time budget?

## Arms

| Backbone | Year | Embedding dim | Checkpoint (torchvision, SHA-256 pinned in `ghostframe_png/backbones.py`) |
|---|---:|---:|---|
| SqueezeNet 1.1 (reference) | 2016 | 512 | `squeezenet1_1-b8a52dc0` |
| MobileNetV3-Small | 2019 | 576 | `mobilenet_v3_small-047dcff4` |
| EfficientNet-B0 | 2019 | 1280 | `efficientnet_b0_rwightman-7f5810bc` |
| ResNet-18 | 2015 | 512 | `resnet18-f37072fd` |
| ConvNeXt-Tiny | 2022 | 768 | `convnext_tiny-983f1562` |

Every backbone reads each tile the same way:
1. Resize to 224 × 224 with bilinear antialiasing.
2. Apply ImageNet normalization.
3. Take the final convolutional feature map and average it to one vector.
4. L2-normalize that vector.

SqueezeNet keeps its original code path, unchanged.

DINOv2 was considered and left out: loading it means running third-party hub code, or adding a
new dependency. It can be a follow-up.

## Fixed settings

The only things that vary between arms are the backbone and the margins below.
- Grid 10 × 8.
- Encoder settings as the finalists: 40 steps, 3 repair rounds, learning rate 1.0, 2 attempts,
  batch 16.
- Carriers centered on each backbone's own calibration mean. Each mean is built by
  `tools/calibrate.py --backbone NAME` from the screen and tune covers only (3,558 tiles), and
  pinned by SHA-256.

**Margin scaling.** Score magnitudes differ between backbones. Each backbone's optimizer margin
and safety threshold are therefore SqueezeNet's (0.01 and 0.002), multiplied by the ratio of its
median clean |score| to SqueezeNet's. The medians come from `tools/score_scale.py` on screen and
tune tiles, measured before this file was committed:

| Backbone | Median clean \|score\| | Ratio | Margin | Safety |
|---|---:|---:|---:|---:|
| SqueezeNet 1.1 | 0.0231 | 1 | 0.0100 | 0.0020 |
| MobileNetV3-Small | 0.0249 | 1.0805 | 0.0108 | 0.0022 |
| EfficientNet-B0 | 0.0167 | 0.7251 | 0.0073 | 0.0015 |
| ResNet-18 | 0.0220 | 0.9546 | 0.0095 | 0.0019 |
| ConvNeXt-Tiny | 0.0150 | 0.6510 | 0.0065 | 0.0013 |

## Ladder

Rungs are run in ascending order, separately for each cap:

| Cap | Rung | Bits per tile / parity | Capacity |
|---:|---:|---|---:|
| 2 | 1 | 16 / 48 | 79 B (= SqueezeNet finalist) |
| 2 | 2 | 20 / 48 | 119 B |
| 2 | 3 | 24 / 64 | 143 B |
| 2 | 4 | 32 / 80 | 207 B |
| 8 | 1 | 40 / 64 | 302 B (= SqueezeNet finalist) |
| 8 | 2 | 48 / 80 | 366 B |
| 8 | 3 | 56 / 96 | 430 B |
| 8 | 4 | 64 / 112 | 494 B |

## Screen (6 screen covers, frame 0)

- A rung **passes** when it meets both conditions:
  - all 6 encodes are decoded exactly by the independent worker;
  - the median encode time is at most 90 s at 4 threads.
- Any single encode that exceeds **300 s** is stopped and counts as a failure. A 300 s encode is
  already more than three times the median budget.
- A backbone's ladder at a cap **stops at the first rung that fails**. Larger rungs are not run.
- SqueezeNet runs rungs 1 and 2 at each cap as a same-day load control.

## Tune (6 in-contract tune covers, frame 0)

1. Each backbone's largest screen-passing rung at each cap runs on the tune covers.
2. That rung is the backbone's **candidate** if the 12 screen and tune covers all succeed and the
   median encode over the 12 is at most 90 s.
3. Otherwise the next smaller screen-passing rung is tried, down to rung 1.

## Decision

- A candidate **advances to holdout** only if its capacity is strictly greater than the
  SqueezeNet finalist at the same cap (79 B at cap 2, 302 B at cap 8).
- If several backbones advance at a cap, the largest capacity wins. Ties go to the faster median
  encode.
- Holdout and promotion follow PREREGISTRATION.md unchanged: 41 covers × 3 frames, ≥ 95 %
  observed success, a cluster-bootstrap lower bound ≥ 85 %, and no more paired frame-0 losses
  than wins against the SqueezeNet finalist.
- The holdout needs the owner's go-ahead (about 6–10 h of compute).
- Nothing replaces SqueezeNet or the legacy entry point. A promoted backbone becomes a new
  experimental profile.

## Secondary measures (reported, never used to decide)

- **JPEG survival:** every screen PNG that decodes is re-saved as JPEG at quality 95 and at 90
  (Pillow, 4:4:4), then decoded. None of the profiles are designed for this. The question is only
  whether any backbone does noticeably better by accident.
- **Thread determinism:** the screen outputs are decoded again with 1 thread, and the received
  bytes must match.
- **Distortion and memory:** PSNR, SSIM and peak memory.
