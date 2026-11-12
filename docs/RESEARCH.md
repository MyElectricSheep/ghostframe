# Research

## Closest prior work

The current `ghostframe-png` profiles use an idea with several precedents: optimise an image's
pixels so that a frozen network reads hidden data out of its features.

- Vukotić, Chappelier and Furon, ["Are Deep Neural Networks good for blind image watermarking?"](https://doi.org/10.1109/wifs.2018.8630768),
  IEEE WIFS 2018: zero-bit watermarking (presence only) through the features of a frozen
  pretrained network.
- Ghamizi, Cordy, Papadakis and Le Traon, ["Adversarial Embedding: A robust and elusive
  Steganography and Watermarking technique"](https://arxiv.org/abs/1912.01487), arXiv 2019,
  peer-reviewed as "Evasion Attack STeganography…" (ICCV Workshops 2021): messages hidden in the
  outputs of pretrained classifiers using adversarial attacks.
- Fernandez et al., [Watermarking Images in Self-Supervised Latent Spaces](https://arxiv.org/abs/2112.09581),
  ICASSP 2022: secret random carrier directions in a self-supervised (DINO) feature space, with
  bits read from projection signs and augmentation during optimisation for robustness. This is
  the closest to Ghostframe's carriers, which are public.
- Kishore et al., ["Fixed Neural Network Steganography: Train the images, not the network"](https://openreview.net/forum?id=hcMvApxGSzZ),
  ICLR 2022 ([code](https://github.com/varshakishore/FNNS)): the idea developed for
  steganography, with several decoder variants.
- Luo, Li, Li, Qian and Zhang, ["Securing Fixed Neural Network Steganography"](https://arxiv.org/abs/2309.09700),
  ACM MM 2023 ([DOI](https://doi.org/10.1145/3581783.3611920)): adds a key to FNNS.
- Li, Li, Qian and Zhang, ["Cover-separable Fixed Neural Network Steganography via Deep
  Generative Models"](https://arxiv.org/abs/2407.11405) (Cs-FNNS), ACM MM 2024.
- Cornell University holds a US patent on adversarial-perturbation steganography with a fixed
  decoder: [US 12,033,233, "Image steganography utilizing adversarial perturbations"](https://patents.google.com/patent/US12033233B2/en).

Relative to these papers, the differences are practical rather than a new method: tiles with
authenticated encryption and interleaved Reed–Solomon codes, an encoder that verifies the saved
file before writing it, and a preregistered held-out benchmark on CPU
([BENCHMARK.md](BENCHMARK.md)). Error correction on its own is standard in learned tools:
SteganoGAN ships Reed–Solomon, and StegaStamp and TrustMark use BCH codes.

The capacities are not comparable budgets. FNNS reports up to 3 bits per pixel with decoders
built for steganography; Ghostframe carries about 0.004 bits per pixel (494 B on a 1280 × ~850
photo) through a stock classifier.

## Original survey

The section below is the survey written at the start of the project, for the raw-bit channel.

Fernandez et al. are the closest direct precedent. Their ICASSP 2022 system modifies the pixels of an existing photograph through a fixed DINO-trained feature extractor and reads a multibit message from latent-space directions. Their implementation uses learned whitening statistics and includes image transformations during optimization. Ghostframe v1 uses a stock supervised ImageNet encoder, unwhitened features and keyed sign projections as a minimal comparison. This establishes precedent for the method, independent of Ghostframe's results. [Paper and examples](https://pierrefdz.github.io/publications/sslwatermarking/) · [Official implementation](https://github.com/facebookresearch/ssl_watermarking)

| Candidate | Capacity and robustness | Cost and dependencies | Security and maturity |
|---|---|---|---|
| A. Frozen encoder and pixel optimization | Benchmarked separately in EXPERIMENTS.md. Feature anisotropy, correlated projections and transform drift may constrain scaling. | Gradient steps per image, a single model forward pass for decoding. No additional model training. SqueezeNet has a 4.729 MB checkpoint. | Raw keyed projections offer no authentication. Implemented and measured locally. |
| B. Learned watermarking | StegaStamp reports recovery after physical recapture. HiDDeN studies noise, crop and JPEG approximations. Stable Signature addresses generated images, so its results cannot be transferred directly to arbitrary photos. | Typically needs specialized trained components. Amortized encoding can avoid per-image gradient descent. | Evaluate on identical covers and distortion budgets before comparing capacity or latency. Direct comparator results are in GOAL_STATUS.md. |
| C. Coverless selection | Under independent uniform bits, a fixed target of length b needs 2^b independent candidates on average. Real feature biases can make specific targets rarer or unattainable. | Retrieval can amortize feature extraction but requires a large collection. Generation adds computation. | Pixel modifications are absent, but repeated covers or biased selection may disclose patterns. Empirical codebook results are in FULL_REPORT.md. |

Sources for B. [StegaStamp paper](https://openaccess.thecvf.com/content_CVPR_2020/html/Tancik_StegaStamp_Invisible_Hyperlinks_in_Physical_Photographs_CVPR_2020_paper.html) · [HiDDeN paper](https://openaccess.thecvf.com/content_ECCV_2018/html/Jiren_Zhu_HiDDeN_Hiding_Data_ECCV_2018_paper.html) · [Stable Signature](https://ai.meta.com/research/publications/the-stable-signature-rooting-watermarks-in-latent-diffusion-models/)

Sources for C. [Coverless Image Steganography survey](https://doi.org/10.1109/ACCESS.2019.2955452)

The baseline uses [Torchvision SqueezeNet 1.1](https://docs.pytorch.org/vision/stable/models/squeezenet.html) for its compact checkpoint and differentiable feature trunk. The upstream architecture repository is BSD-2-Clause. The Torchvision ImageNet checkpoint is fetched separately and has no separate checkpoint license asserted here. A later comparison can use [DINOv2](https://github.com/facebookresearch/dinov2), whose model card lists Apache 2.0, and a selected [OpenCLIP](https://github.com/mlfoundations/open_clip) checkpoint after verifying its terms.

Measure complete-payload recovery at a fixed distortion budget first. Check whether augmentation during optimization improves held-out JPEG and resizing outcomes before introducing ECC. Evaluate detectability independently using clean/marked pairs and a held-out steganalysis baseline.

## Empirical follow-up

The final evaluation directly ran the trained TrustMark C watermark model as an optional comparator. On matched 16- and 32-bit target prefixes, it recovered 8/8 JPEG 70 images and 24/24 crops at an eight-level RGB cap. At two levels it recovered 4/8 PNGs, while the frozen SqueezeNet projection baseline recovered 7/8. Coverless selection was also measured empirically. The 14-cover pool covered a median 4.30% of 8-bit targets after JPEG 70 across eight projection keys. See [objective verification](earlier/GOAL_STATUS.md) and [the full report](earlier/FULL_REPORT.md). [TrustMark source and model terms](https://github.com/adobe/trustmark)
