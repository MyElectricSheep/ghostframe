# Crop robustness

## Experiment

Compared the original clean-only optimizer with a crop-aware variant. The latter uses the unchanged clean view plus four 90%-width, 90%-height corner crops in its objective. Each view has equal weight. It keeps the existing image encoder, keyed projections, decoder, signed-margin objective, RGB bound of 2/255, and cap of 100 Adam updates. Both methods optimize at the original image resolution and score the exact 8-bit representation.

The evaluation uses three photo covers and one low-detail derivative of the landscape, two payload sizes, and three key/payload trials per cover and size. Each method receives exactly the same 24 cover/key/payload inputs. Held-out crops are the centered 90% view, left and bottom offsets retaining 92% per dimension, and two asymmetric offsets retaining 88%. No held-out box coincides with a training box. The transforms share source pixels and the sample is small, so per-crop results are descriptive. JPEG 70 and a 75% resize are secondary checks, applied separately to reopened PNGs.

Run `python -m experiments.crop_robustness` from the project directory. The script saves each attempted image and atomically updates its JSON results. Measurements use the same frozen SqueezeNet checkpoint and four CPU threads.

A visual spot check, `benchmarks/crop-robustness/portrait-detail.png`, was made but not kept in this repository. Clockwise from top left are the source, baseline, 96× absolute difference for the crop-aware output, and crop-aware output. The two outputs were visually close to the source in this crop at native scale. This single comparison is illustrative. PSNR and SSIM in the table cover every attempted image.
## Results

| Condition | Baseline exact | Crop-aware exact | Baseline bit error | Crop-aware bit error |
|---|---:|---:|---:|---:|
| PNG | 21/24 | 15/24 | 0.5% | 7.8% |
| Training-position crops | 0/96 | 59/96 | 43.2% | 7.2% |
| Held-out crops | 0/120 | 4/120 | 44.6% | 37.5% |
| JPEG quality 70 | 6/24 | 3/24 | 24.1% | 30.9% |
| 75% resize | 15/24 | 10/24 | 8.5% | 14.8% |

| Payload | Baseline exact on held-out crops | Crop-aware exact on held-out crops |
|---|---:|---:|
| 16 bits | 0/60 | 4/60 |
| 32 bits | 0/60 | 0/60 |

| Method | PSNR range | Mean SSIM | Median encode time |
|---|---:|---:|---:|
| Baseline | 42.51–44.54 dB | 0.973 | 2.03 s |
| Crop-aware | 42.42–44.50 dB | 0.972 | 10.77 s |

The four held-out successes all came from the same 16-bit sky payload, trial 2, across four transformations. The other 23 marked inputs had no exact held-out crop recovery.

## Decision

Keep clean-only encoding as the default. Four fixed crop views make the message more readable at those exact positions, but the improvement mostly disappears on new offsets. The variant also lowers exact recovery from untouched PNGs and adds roughly 5.3× median encode time at comparable distortion. The broader sample exposed three clean-only PNG failures at the 2-level budget, so the first experiment's 8/8 outcome was sample-specific.

If crop survival remains a requirement, compare features from a more crop-stable encoder before raising the pixel budget. Screen candidates by measuring projection sign drift on unmodified images under the same crop grid, then confirm the promising candidate with paired embedding and exact-recovery tests.
