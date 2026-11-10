# Non-UI objective verification

This ledger traces the original development prompt to working commands, measurements, and remaining limits. It distinguishes a successful feasibility result from robust recovery on uncontrolled channels.

| Original objective | Evidence and disposition |
|---|---|
| Research and three architectures | [Research](RESEARCH.md) covers the closest frozen-feature precedent, trained watermarking, and coverless selection. The repository includes empirical runs for all three and a separate conventional luminance baseline. |
| 16- and 32-bit frozen-encoder proof of concept | Verified in memory, after PNG serialization, with separate decoding and wrong-key controls. [Initial evidence](EXPERIMENTS.md) and [fresh-cover evidence](FULL_REPORT.md). |
| Fidelity, capacity, and robustness | Measured 16–512 bits, PSNR, SSIM, pixel error, runtime, bit errors, and exact recovery. The evidence includes visual difference maps, JPEG quality sweeps, crops, resizes, exposure and simulated recompression. Color and synthetic display capture controls are recorded below. LPIPS was added on 14 archived neural output pairs. |
| Optimization and alternate architectures | Tested projection margins, QR-orthogonal directions, crop and JPEG-aware objectives, different frozen backbones, repetition, independent tiles, and Reed–Solomon parity. The tests include multiple image scales as transforms. A matched multiscale neural loss was measured in the follow-up below. |
| Authenticated offline messages | The local CLI encodes and decodes up to 13 bytes through neural embeddings, one byte with neural ECC, or up to 26 bytes through the conventional luminance carrier. Encoding verifies the serialized result. [Architecture](ARCHITECTURE.md) and [wire format and threat assessment](SECURITY.md). |
| Conditional encrypted dead drop | Offline short messages work, and the implementation retains that workflow. No external service was introduced. This still leaves long messages outside the validated product scope. |
| Independent model and restart checks | Two fresh CPU processes with one and four threads each authenticated six prior files and rejected six wrong-password and six wrong-checkpoint cases. Same-host verification does not establish cross-device recovery. |
| Developer and quality deliverables | Version-pinned core dependencies, digest-pinned SqueezeNet assets, documented CLI and benchmark commands, machine-readable outputs, tests, and ongoing progress are included. |

## New neural CLI verification

Two independent command-line round trips encoded fresh payloads from the included source photos. The first encoded the 13-byte message on the portrait using the neural profile and the second encoded one byte on the flower photo using the lower-budget ECC profile. Separate processes recovered the exact bytes. The saved fixtures are in `benchmarks/goal-validation/`.

```sh
python -m experiments.message_cli decode benchmarks/goal-validation/neural-demo.png --carrier neural
python -m experiments.message_cli decode benchmarks/goal-validation/neural-ecc-demo.png --carrier neural-ecc
python -m experiments.goal_validation
python -m experiments.neural_transform_controls
```

Both example files use the public benchmark passphrase `ghostframe public benchmark fixture`. The restart check compares the pinned model with pretrained ResNet-18, whose embedding dimension allows the same projection reader to run. The raw-bit benchmark remains available through the installed `ghostframe benchmark` command.

The local execution host was an AMD EPYC 9V74 environment with an eight-CPU-equivalent quota and an 8 GiB memory limit. Neither CUDA nor Apple MPS was available. The authenticated neural command runs on CPU. The comparison includes local Pillow simulations and no real messenger or native screenshot capture. No protocol can guarantee arbitrary photo transformations on the evidence collected here.

## Matched trained-watermark comparison

TrustMark 0.9.2, compact C model with the package's default BCH profile, was tested on the same four fresh covers, 16- and 32-bit target prefixes, and transformations as the final SqueezeNet holdout. The requested prefix was padded to TrustMark's native payload size. Exact recovery requires detection and the exact prefix. Clipping the native residual after encoding imposes the same pixel bound, without retraining or optimizing TrustMark for that bound. The native profile uses specialized pretrained weights, whereas SqueezeNet uses a fixed classifier backbone and optimizes pixels per image. The models use different coding methods. The matched observable quantities are target prefix, input cover, transform, and maximum RGB delta.

| Carrier | Pixel cap | PNG | JPEG 70 | Three crop positions | Median PSNR |
|---|---:|---:|---:|---:|---:|
| SqueezeNet, raw global | 2 | 7/8 | 1/8 | 0/24 | See per-case holdout data |
| SqueezeNet, raw global | 8 | 8/8 | 7/8 | 0/24 | See per-case holdout data |
| TrustMark C | 2 | 4/8 | 4/8 | 13/24 | 46.10 dB |
| TrustMark C | 8 | 8/8 | 8/8 | 24/24 | 42.56 dB |
| TrustMark C | Native, observed max 18 | 8/8 | 8/8 | 24/24 | 42.54 dB |

TrustMark's median forward encode time was 0.15 s and median PNG decode was about 0.04 s on this host, excluding model setup. The checkpoint hashes and per-file results are in `benchmarks/goal-validation/`. Source photos were reused across payload sizes, so the observations are paired and the denominators should not be read as independent samples. This comparator neither encrypts nor authenticates the 16- or 32-bit trial messages. The historical raw-bit tests provide no guarantee that 32 bits can be recovered consistently with imperceptible changes on new covers. The visible eight-level neural examples fail that visual target.

[Adobe TrustMark implementation and model license](https://github.com/adobe/trustmark)

## Additional transform checks

The six authenticated neural fixtures were tested with an RGB balance change that scales red by 1.02 and blue by 0.98, then rounds and clips. All six authenticated. A separate synthetic display-capture arm fit each image to 400×400 with bicubic interpolation, drew it on a simulated viewport, encoded the viewport as PNG, and extracted the displayed region. None authenticated. This is a synthetic display operation. The actual screenshot and real messaging-service cases remain unverified.

## Remaining verification

All 25 automated tests passed, including input format, size, preprocessing, authentication, parity, and wrong-password checks. The fresh CLI files and wrong-passphrase subprocess checks verify the local workflow. The major unresolved verification item is independent hardware or OS execution. The interface was excluded by request. The offline endpoint is validated within its short-message limits. Longer payloads, a large independent cover corpus and real delivery channels remain outside the measured result.

## Perceptual distances

SqueezeNet LPIPS 0.1.4 measured 14 archived clean/marked pairs. Median distances were 0.0882 for the six initial global samples, 0.0360 for four two-level tiled samples, and 0.1281 for four eight-level tiled samples. These scores are model-based distances rather than human visibility thresholds. The shared backbone is a limitation when scoring perturbations optimized against the same backbone. The visual difference maps and pixel-level measurements remain useful independent views of the changes.

Reproduce with `python -m pip install -e '.[perceptual]'` followed by `python -m experiments.perceptual`. The LPIPS calibrated checkpoint is bundled by its pinned package. The result JSON is in `benchmarks/goal-validation/lpips.json`.

## Matched multiscale loss

The additional objective used differentiable bilinear views at 65% and 85% of the original dimensions alongside the untransformed view. It used the same 16- and 32-bit targets, four covers, 100-step cap and two-level RGB budget as the prior clean-only baseline. The additional views increased model evaluations per step. The two runs were on the same host but under different concurrent workloads, so timings are indicative.

| Objective | PNG | JPEG 70 | 75% resize | Thumbnail JPEG 85 | Median PSNR | Median encode |
|---|---:|---:|---:|---:|---:|---:|
| Clean-only | 7/8 | 1/8 | 6/8 | 0/8 | 43.19 dB | 2.52 s |
| Clean + 65% + 85% | 6/8 | 2/8 | 6/8 | 1/8 | 43.23 dB | 7.90 s |

The experiment found a modest gain in two recompression arms, one fewer exact PNG result, and no gain for the held-out scale. The original objective remains the default. Reproduce with `python -m experiments.multiscale_neural`.
