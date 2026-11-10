# Ghostframe authenticated JPEG holdout

The earlier JPEG pilot measured raw bit errors on previously marked fixtures. This run compared the current aligned encoder to seven candidates on nine previously unmarked sources outside that pilot, with two independently sealed payloads per image. The frame and block layout are the current 96-byte v3 format and three replicas. Every profile gets the same sealed frame per image and trial. A success requires Reed–Solomon decoding, AES-GCM authentication and exact plaintext equality. The four spacing-3, zero-phase candidates use the current extractor, as does the baseline. Optional erasure and geometry searches are excluded. This isolates encoder behavior and holds the decoder fixed for the compatible profiles. The original dimensions are supplied in the resize test.

The compressor-in-the-loop idea adapts the use of actual encoder outputs from [Butora, Puteaux and Bas](https://arxiv.org/abs/2211.04750). Sparse fitting probes Q35, Q50, Q70 and Q85. Dense fitting probes Q35 through Q95 in steps of five. The low-quality grid also probes Q37, Q39, Q41, Q43 and Q45. Joint selection evaluates all 125 combinations of the three replicas (five shifts per replica). A clean decoding constraint was carried forward from the pilot. WebP, 4:4:4 JPEG, double JPEG and resizing were outside the fit.

## Authenticated recoveries out of 18

| Profile | PNG | Q70 | Q60 | Q50 | Q42 | Q41 | Q40 | Q39 | Q38 | Q35 | Q95 then Q50 | 75% resize then Q70 | 4:4:4 Q50 | WebP 75 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Baseline | 18 | 18 | 14 | 12 | 14 | 14 | 16 | 16 | 10 | 9 | 12 | 16 | 14 | 8 |
| Mixed spacing | 18 | 18 | 14 | 16 | 12 | 12 | 17 | 16 | 7 | 5 | 14 | 15 | 16 | 8 |
| Mixed phase | 18 | 14 | 14 | 14 | 13 | 13 | 12 | 12 | 12 | 10 | 13 | 14 | 14 | 8 |
| Actual JPEG, independent | 18 | 18 | 14 | 14 | 14 | 14 | 16 | 14 | 10 | 15 | 14 | 16 | 14 | 8 |
| Actual JPEG, joint sparse | 18 | 18 | 14 | 14 | 12 | 12 | 14 | 14 | 8 | 17 | 14 | 16 | 14 | 7 |
| Actual JPEG, joint dense | 18 | 18 | 14 | 14 | 14 | 14 | 18 | 18 | 7 | 16 | 14 | 16 | 14 | 8 |
| Actual JPEG, joint low-quality grid | 18 | 18 | 14 | 14 | 14 | 14 | 18 | 18 | 10 | 16 | 14 | 16 | 14 | 8 |
| Actual JPEG, joint diverse | 18 | 14 | 14 | 14 | 11 | 9 | 10 | 9 | 9 | 12 | 14 | 13 | 14 | 3 |

Q80, Q85 and Q95 results are included in the JSON. The low-quality grid matched or improved the baseline totals in every measured channel, although aggregate ties do not imply paired equivalence. It recovered seven more Q35 frames across four covers and lost none of the baseline's successes at Q35. The sparse fit recovered one additional frame at Q35, but regressed across Q38 through Q42 and WebP. Mixed spacing did best at Q50 and 4:4:4 Q50, but lost four Q35 frames relative to the baseline. The low-quality grid's aggregate mean squared RGB change was 1.540, matching the baseline to three decimal places. The benchmark checked the maximum two-level change per channel for all 144 marked outputs. It measured a median 0.442 seconds per cover to probe the full quality grid, shared across frames and variants. This is not a production latency measurement.

The dataset includes photographs, microscopy, document text and binary test patterns. Two frames per cover are repeated measurements, not independent images. These results verify an aligned JPEG recovery gain in this holdout. They do not establish blind resize recovery, robustness across arbitrary encoders, or resistance to steganalysis. The experimental encoder is separate from the default CLI and neural path.

## Reproduce

Install NumPy, Pillow, cryptography and reedsolo 1.7.0. Pillow 13.0.0 was used. For the original inputs, use the bundled image data from the scikit-image 0.25.2 wheel and the three files installed by TeX Live and Inkscape. Set the three variables to those directories and run from the archive root.

```bash
python -m experiments.jpeg_authenticated_holdout \
  "$SKIMAGE_DATA"/{cell,ihc,motorcycle_left,page,horse,chessboard_RGB}.png \
  "$IFMSLIDE_DATA"/{aqua_ravines,liquid_helium}.jpg \
  "$INKSCAPE_PIXMAPS"/ticotico.jpg
python -m unittest discover -s tests -p test_jpeg_carrier.py
```

The runner records SHA-256 hashes for inputs and uses fresh cryptographic salts and nonces on each run, so scores can vary. It preserves aspect ratio and initially fits images within 512×512, then enlarges narrow fixtures as needed to fit the frame. Three carrier tests passed, and direct checks rejected an incorrect password and an all-zero frame. The full suite was not rerun in this environment.
