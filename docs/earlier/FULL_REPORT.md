# Ghostframe research report

## What the project established

Ghostframe started with a question about deterministic image embeddings as a message carrier. It now has two experimentally distinct branches.

| Branch | Verified milestone | Main constraint |
|---|---|---|
| Neural embedding, global | A frozen SqueezeNet recovered raw 16- and 32-bit payloads in lossless PNG. The original run recovered eight of eight. | Fresh-cover performance varied. Crops broke most payloads. A single 384-bit authenticated-frame-sized payload recovered on 0/4 clean PNGs at either tested bound. |
| Neural embedding, tiled | A 30-tile design recovered an authenticated 13-byte message on 4/4 preserved PNGs at an eight-level RGB budget. | JPEG 95, resizing, and cropping defeated all four frames. Visible texture changes appeared at eight levels. |
| Neural embedding, tiled with parity | A one-byte authenticated frame recovered on 6/6 preserved PNGs at two RGB levels, compared with 5/6 without correction on the same images. | JPEG 95 introduced at least 47 wrong bytes of 60. |
| Conventional luminance modulation | An authenticated 25-byte message recovered on 10/10 images as PNG and after same-size JPEG 70 or 50. | Geometry, processing history, and detector knowledge materially affect results. |
| Local CLI | Binary-safe encode/decode, passphrase-based authentication, and bounded geometry recovery. The decoder opens the marked file independently. | Maximum 26 bytes, at least 2,304 complete 8×8 blocks, and a four-megapixel input cap. |

The neural work demonstrates feasibility on preserved PNGs. The conventional luminance carrier provides the more robust file workflow. AES-GCM authenticates the frame, scrypt derives its key, and Reed–Solomon corrects carrier errors before authentication. The carrier uses a public block layout and detectable signal. A private passphrase protects the message under the protocol's assumptions and does not conceal the carrier.

Earlier methods and results are in [progress](PROGRESS.md), [extended neural experiments](EXTENDED.md), [tiled parity](TILED_ECC.md), [JPEG comparison](JPEG_CARRIER.md), [geometry and codecs](ROBUSTNESS.md), and [CLI](MESSAGE_CLI.md).

## Final sweep

The luminance experiments reuse ten prior covers and add four unused in earlier Ghostframe runs: coins, clock, color wheel, and retina. These are convenience samples from scikit-image. They do not constitute a representative collection or establish that the neural model never encountered them during pretraining. Each file experiment uses one fresh randomized 96-byte frame per cover. The public benchmark passphrase and the 25-byte message are fixed. Images are fitted within 512×512. [scikit-image data and credits](https://scikit-image.org/docs/stable/api/skimage.data.html)

- **Search speed.** The optimized decoder caches bounded block orderings and computes phases only for complete aligned blocks during resize search. The crop search retains full pixel-offset phases. Three matched files compare the old full phase map and the new aligned phase calculation with the same cache cleared at the start of each run. This isolates the phase computation change. Each arm ran once per file.
- **Resize and recompression.** Compare alignment search with an oracle given the original dimensions. The oracle restores with Lanczos and decodes the same frame. Test 67% and 73% Lanczos, 73% bilinear, bicubic, and box filtering, and the stronger JPEG 70 → 73% Lanczos → JPEG 70 chain. The oracle-only confidence variant retries Reed–Solomon with 4, 8, 12, 16, 20 or 24 low-confidence bytes marked as erasures. The score for each byte is its weakest absolute bit confidence. A success still requires AES-GCM authentication.
- **Combined edit.** Crop off center, resize the crop to 75%, and write JPEG 70. Restore the known crop dimensions, then search for the pixel offset using the known original dimensions. This arm supplies both dimension pairs and withholds the offset. It is not the CLI's automatic recovery path.
- **Exposure.** Test a bounded inverse-brightness search at integer multipliers from 85% to 115%, ranking by repeated-block agreement. Compare directly decoded images with the search at 105% and 93% brightness, including JPEG 70 after the adjustment. A clean brightened image acts as a control. This method is available via the opt-in CLI flag `--try-exposure`.
- **Detection.** Compare the protocol-aware repeated phase score to a generic 8×8 boundary-energy statistic on clean/marked pairs, both PNG and JPEG 70. Report paired ordering and leave-one-cover-out classification. For the generic statistic, threshold and score direction are selected on training pairs by balanced accuracy. Neither detector uses the original at prediction time.
- **Cover selection.** With no pixel modification, use eight fixed keys to read 16-bit SqueezeNet signatures on the 14 images. Count distinct signatures that remain unchanged after JPEG 70 for each key and prefix length. Dividing by the number of possible prefixes gives exact-message coverage under a uniform independent target for this finite collection. This is a codebook experiment, with no embedded encryption.
- **Neural holdout.** Test 16- and 32-bit raw SqueezeNet targets on the four fresh covers, at two and eight RGB levels. Report clean PNG, JPEG 70, and three crop positions separately.

These were local processing chains, not tests of WhatsApp, social media services, native screenshots, or a second hardware backend. The published trained-watermark comparison remains literature-based. No model was trained in this sweep.

## Reproduction

From the repository root with the optional tiled dependencies installed:

```sh
python -m pip install -e '.[tiled]'
python -m experiments.final_sweep
python -m experiments.exposure
python -m experiments.carrier_controls
python -m experiments.neural_holdout
python -m experiments.summarize_sweep
python -m unittest discover -s tests -v
```

The commands use the previous JPEG benchmark included in the archive. Per-cover JSON files are in `benchmarks/final-sweep/`. Fresh salt and nonce bytes can change the payload errors from run to run.

## Final measurements

### Resize and compression

| Condition | Known dimensions, hard | Known dimensions, confidence erasures | Geometry search | Fresh covers, best oracle or search for combined case | Median wrong bytes |
|---|---|---|---|---|---|
| jpeg70 | 14/14 | 14/14 | — | 4/4 | 0.0 |
| 67_lanczos | 11/14 | 12/14 | 12/14 | 2/4 | 4.5 |
| 73_lanczos | 13/14 | 13/14 | 13/14 | 3/4 | 3.0 |
| 73_from_jpeg70 | 9/14 | 10/14 | 9/14 | 2/4 | 9.0 |
| 73_bilinear | 11/14 | 11/14 | — | 3/4 | 8.0 |
| 73_bicubic | 13/14 | 13/14 | — | 3/4 | 3.5 |
| 73_box | 2/14 | 3/14 | — | 2/4 | 37.0 |
| brightness | 1/14 | 1/14 | — | 0/4 | 87.5 |
| crop_resize_jpeg_oracle | — | — | 12/14 | 3/4 | — |

### Exposure search

| Condition | Direct | Exposure search | Median search time |
|---|---|---|---|
| bright_105 | 1/14 | 13/14 | 0.66 s |
| dark_93 | 0/14 | 14/14 | 0.68 s |
| bright_105_jpeg70 | 1/14 | 13/14 | 0.63 s |
| dark_93_jpeg70 | 0/14 | 11/14 | 0.64 s |
| clean_bright_105 | 0/14 | 0/14 | 0.23 s |

### Detection

| Detector and channel | Clean flagged | Marked flagged | Fresh clean flagged | Fresh marked flagged |
|---|---|---|---|---|
| png_protocol | 0/14 | 14/14 | 0/4 | 4/4 |
| jpeg_protocol | 0/14 | 14/14 | 0/4 | 4/4 |
| png_edges | 2/14 | 12/14 | 0/4 | 4/4 |
| jpeg_edges | 7/14 | 8/14 | 3/4 | 3/4 |

The fresh-only detector column uses three fresh training pairs per fold.

### Search timing

| Cover | Full phase map | Aligned blocks | Authenticated in both |
|---|---|---|---|
| camera | 5.66 s | 4.55 s | True |
| coffee | 3.98 s | 2.96 s | True |
| rocket | 3.30 s | 2.81 s | True |

### Cover selection

| Bits | Distinct stable prefixes per key | Median exact target coverage |
|---|---|---|
| 2 | 2–4 | 75.0000% |
| 4 | 5–8 | 43.7500% |
| 8 | 10–12 | 4.2969% |
| 16 | 10–12 | 0.0168% |

### Fresh neural covers

| RGB levels | Bits | PNG exact | JPEG 70 exact | Crop exact |
|---|---|---|---|---|
| 2 | 16 | 4/4 | 1/4 | 0/12 |
| 2 | 32 | 3/4 | 0/4 | 0/12 |
| 8 | 16 | 4/4 | 4/4 | 0/12 |
| 8 | 32 | 4/4 | 3/4 | 0/12 |


## Interpretation and scope

- **The post-processing chain matters as much as the scale.** The wider search recovered 13/14 at 73% after JPEG 95, versus 9/14 when the first JPEG was quality 70. With original dimensions supplied, the 73% Lanczos and bicubic arms recovered 13/14, bilinear recovered 11/14, and box recovered only 2/14 before confidence erasures. A correct size hypothesis alone cannot restore signal lost in filtering or recompression. At 67%, a nearby size hypothesis can occasionally outperform restoration to the known dimensions, so the known-dimensions column is a diagnostic, not an upper bound.
- **Confidence erasures helped narrowly.** They recovered one additional frame in each of the 67% Lanczos, stronger recompression, and box-filtered arms. The test supplied dimensions. That retry path remains experimental and is not wired into the CLI's search.
- **Compound recovery needs geometry.** Crop → resize → JPEG 70 worked on 12/14 when the original and pre-resize crop dimensions were given. No blind compound search was validated. The opt-in exposure CLI addresses a separate uniform brightness operation and does not compose searches automatically.
- **The luminance signal remains detectable.** The protocol-aware detector flagged every held-out marked sample before and after JPEG, without flagging the paired clean files. The generic grid-boundary statistic performed considerably worse on JPEG in this corpus. This does not imply that detectors without protocol knowledge cannot detect it. Small pixel changes and visually subtle output do not imply concealment.
- **Cover selection scales poorly in a small collection.** Across eight keys, the median fraction of possible 8-bit targets covered by a JPEG-stable candidate was 4.30%. At 16 bits it was about 0.017%. The cover-only method requires a larger pool or a much smaller message.
- **The original neural idea remains a useful demonstration.** Fresh-cover results strengthen the PNG finding and show occasional JPEG recovery at the larger perturbation budget. The tested crop cases all failed, and the earlier tiled authenticated neural frames remain a PNG-only result.

The current CLI can encode and authenticate short messages and offers individually bounded recovery modes. It is suited to controlled demonstrations with known image-processing assumptions. This report leaves real messaging-app transfer, native screenshots, arbitrary compound edits, trained-watermark replication, second-device validation, and population-level reliability unresolved. All 20 automated tests passed.
