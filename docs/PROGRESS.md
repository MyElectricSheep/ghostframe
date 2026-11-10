# Progress

## First execution

1. Confirmed Linux x86-64 CPU environment, 8 CPU-equivalent quota and 8 GiB memory limit. Installed CPU PyTorch and Torchvision and pinned the published SqueezeNet checkpoint by SHA-256.
2. Identified the direct DINO latent-space watermarking precedent and compared three candidate approaches in RESEARCH.md. Implemented the simpler keyed projection baseline with native-resolution pixel updates, 8-bit-aware optimization and a separate decoder.
3. Verified the installed encode/decode CLI in separate processes and passed both automated tests. Ran the 16-bit and 32-bit benchmark on three photos and one low-detail crop, including unmarked covers, wrong keys and transformations.
4. Reviewed original, marked and amplified difference images. Recovery is repeatable on PNG. Crop sensitivity and visible texture at 32 bits limit product readiness. Measured tighter pixel budgets as a comparison. See EXPERIMENTS.md and benchmarks for measurements.

## Handoff

Keep the current baseline fixed. Run a paired comparison with clean-only versus crop-aware optimization at the same low perturbation budget, with multiple payloads and keys per image, held-out crop offsets, and explicit fidelity review. Use full-payload recovery as the primary outcome. Verify a second platform once the protocol is stable. Product UI, encrypted framing, ECC and dead-drop service remain behind the research gates.

## Crop robustness follow-up

Implemented an optional crop-aware optimization objective and ran 24 matched inputs per method at a 2/255 pixel budget. The five held-out crop conditions recovered 4/120 payloads with crop-aware optimization and 0/120 with the baseline. Untouched PNG recovery fell from 21/24 to 15/24. Both methods stayed within the pixel budget. Kept the clean-only CLI default. See CROP_ROBUSTNESS.md for the full comparison and the recommended encoder-screening experiment.

## Encoder screening follow-up

Screened MobileNetV3 Small and ResNet-18 against SqueezeNet on unmarked images. Advanced ResNet-18 to a matched trial-0 payload pilot. Clean-only ResNet-18 recovered no held-out crop payloads, and crop-aware ResNet-18 recovered 3/40. The CLI default remains SqueezeNet clean-only. The natural sign-flip screen is insufficient on its own for selecting a payload encoder. See ENCODER_SCREEN.md for results and evidence validation.

## Extended validation and capacity

Re-scored 32 historical records and ran 108 new attempts across fresh-cover validation, capacity, repetition, orthogonal projections, and JPEG-aware optimization. At eight RGB levels, 64 bits recovered from 4/4 untouched PNGs and 384 bits from 0/4. JPEG-aware encoding improved JPEG quality-70 recovery at 16 bits from 1/4 to 3/4 at the two-level budget. This improvement did not transfer to the thumbnail chain. See EXTENDED.md for the full results and product gates.

## Tiled authenticated frame

Measured a 6×5 tiled SqueezeNet carrier with 16 bits per tile and a 60-byte authenticated frame. At two RGB levels, 2/4 untouched PNGs authenticated. At eight levels, 4/4 authenticated, with visible added texture on the coffee sample. JPEG, resizing, and cropping broke all tested frames. See TILED.md for the matched global control, independent decode and protocol details.

## Tiled error correction

Added a one-byte authenticated payload with 14 Reed–Solomon parity bytes in the same 480-bit grid. Untouched PNG recovery improved from 5/6 to 6/6 on the same codewords. The controlled restoration of three original tiles improved from 0/6 to 5/6. JPEG, resizing and cropping remained outside the correction budget. See TILED_ECC.md for the full experiment.

## JPEG-oriented luminance carrier

Compared an aligned 8×8 luminance carrier with the earlier tiled embedding arm using identical 480-bit authenticated codewords on six matched covers, plus four additional covers. Three copies authenticated 10/10 at quality 70 under the same two-level RGB cap. Spacing three also authenticated all ten covers in five further JPEG conditions, with Reed–Solomon correction. Resize and crop remain unsupported. See JPEG_CARRIER.md for details.

## Geometry, codecs, detectability and larger messages

The luminance carrier recovered ten centered crops with bounded blind search, ten asymmetric crops with known geometry, and ten test resizes after restoring their original dimensions. The protocol-aware detector separated all held-out marked and clean samples in the PNG and JPEG cohorts. A larger authenticated frame recovered 25-byte messages from all ten PNG, JPEG 70, and JPEG 50 tests. See ROBUSTNESS.md for methods and scope.

## Bounded alignment search

Recovered 10/10 off-center crops with supplied original dimensions and unknown offset, including after JPEG 70. Recovered 10/10 resizes at each of three tested listed scales without supplied original dimensions. The unlisted 73% scale and clean negative control authenticated 0/10. See ALIGNMENT_SEARCH.md for settings and timing.

## Local message command

Added encode and decode commands for the 26-byte authenticated luminance profile. The encoder verifies the serialized output before publishing it. The decoder supports bounded crop and resize alignment search. The saved-file benchmark authenticated 10/10 direct JPEGs, 10/10 cropped and recompressed JPEGs, and 10/10 resized and recompressed JPEGs under the tested assumptions. See MESSAGE_CLI.md.

## Wider resize search

Added an opt-in integer-percent search from 50% through 95%, plus 62.5%, with floor and nearest dimension candidates. At the 96-byte frame size, the wider search recovered 8/10 at 67% and 10/10 at 73% and 87% after JPEG recompression. Both negative conditions authenticated 0/10. See WIDE_RESIZE.md for timings and the independently verified JPEG fixture.

## Final autonomous sweep

Validated the luminance carrier on 14 covers, including four fresh samples, and measured alternate resize kernels, confidence erasures, compound edits, exposure, and paired detectability. Added a faster aligned resize calculation and optional exposure recovery to the CLI. Re-tested the neural path on the fresh covers and measured JPEG-stable cover selection. See FULL_REPORT.md for consolidated findings and raw evidence locations.

## Confidence-assisted CLI search

Added optional `--soft` retries for direct decoding and the existing bounded search modes. On six matched covers the retry recovered one additional authenticated message in each of two resize chains. Clean controls never authenticated. See SOFT_SEARCH.md for the comparison.

## Compound JPEG recovery in the CLI

Added optional pre-resize crop dimensions to the existing original-dimensions recovery mode. The decoder restores crop size and searches the unknown offset. On 14 saved JPEGs it authenticated 12/14 at the 75% crop resize and 8/14 at 67%. See COMPOUND_SEARCH.md for the test conditions and demo.

## Original brief verification

Exposed the two authenticated neural PNG profiles in the local CLI and verified fresh encodes through independent processes. Rechecked six older authenticated fixtures under two CPU thread configurations, rejecting all wrong-password and alternate-checkpoint controls. Ran the trained TrustMark C comparator, color-balance and synthetic-display checks. Added architecture, security, and scope documentation. See GOAL_STATUS.md for the requirement-by-requirement ledger and remaining independent device verification.

Measured SqueezeNet LPIPS on 14 saved pairs and completed a matched multiscale neural comparison. The added scales raised median encode time and did not improve held-out resize recovery, so they remain experimental.

## Alternative carrier experiments

Compared smooth perturbations, a JPEG/resize-aware objective, and their combination at the same neural pixel bound. Evaluated a keyed phase-shifted luminance lattice against fixed-phase and generic boundary detectors and under JPEG and resize. See CREATIVE_EXPERIMENTS.md for trade-offs. The tested alternatives remain experimental.
