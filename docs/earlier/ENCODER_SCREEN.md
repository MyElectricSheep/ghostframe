# Encoder screening

## Method

Screened the pooled final convolutional features of SqueezeNet 1.1, MobileNetV3 Small and ResNet-18. All checkpoints are frozen ImageNet models, verified by full SHA-256. The same differentiable 224×224 resize and RGB normalization were used for all three architectures. The screen checks whether the sign of each keyed projection stays the same between the unmodified source image and its crop. It uses 4,096 deterministic probes per cover/crop pair, four image inputs and five crop boxes, yielding 81,920 sign comparisons per model. One input is a low-detail crop of another, and the probes share images and views, so this is a descriptive comparison.

The alternative with the lowest mean flip rate advances to a paired embedding pilot. It uses the same eight cover and payload-size combinations as trial 0 of the previous SqueezeNet experiment, with identical keys, target bits, crop boxes, 100-step cap and two-level RGB limit. Both clean-only and four-crop optimization are measured. The pilot reuses the same covers and transform grid as the screen, so it tests transfer from natural features to marked features on these examples. It does not estimate generalization to new covers. The SqueezeNet comparator comes from the previously recorded run, so timing ratios are approximate.

Sources for checkpoint architectures. [Torchvision MobileNetV3 Small](https://docs.pytorch.org/vision/main/models/generated/torchvision.models.mobilenet_v3_small.html) · [Torchvision ResNet-18](https://docs.pytorch.org/vision/main/models/generated/torchvision.models.resnet18.html)

Reproduce with `python -m experiments.encoder_screen`. The screen and per-case payload outcomes are in `benchmarks/encoder-screen/`.

## Natural-image screening

| Model | Projection signs flipped | Mean embedding cosine similarity |
|---|---:|---:|
| squeezenet | 6.80% | 0.9746 |
| mobilenet | 6.74% | 0.9747 |
| resnet18 | 6.32% | 0.9761 |

## Paired payload pilot

| Encoder and objective | PNG exact | Held-out crop exact | Crop bit error | JPEG 70 exact | Median encode |
|---|---:|---:|---:|---:|---:|
| SqueezeNet, baseline | 7/8 | 0/40 | 42.7% | 1/8 | 2.24 s |
| ResNet-18, baseline | 7/8 | 0/40 | 44.9% | 2/8 | 3.19 s |
| SqueezeNet, crop_aware | 4/8 | 0/40 | 37.4% | 1/8 | 11.09 s |
| ResNet-18, crop_aware | 5/8 | 3/40 | 34.7% | 1/8 | 33.37 s |

## Decision

The natural-image screen separated the models by less than half a percentage point. Clean-only payload encoding gave both SqueezeNet and ResNet-18 seven exact PNG decodes and zero exact crop decodes. Crop-aware ResNet-18 recovered three held-out cases, but the added compute and the remaining failures make this a weak basis for replacing the default. The screen probes read natural features, while the embedding optimizer tries to push selected projections across a sign boundary under a tight pixel budget. Stability on unmarked images alone did not predict exact recovery after that optimization.

Two earlier SqueezeNet benchmark PNGs in the prior archive were truncated. They were regenerated from the original cover, key, and target. All recorded transformations of the repaired files match their original decoded bit strings. The new archive includes the repaired PNGs. All benchmark PNGs in this archive were loaded successfully.
