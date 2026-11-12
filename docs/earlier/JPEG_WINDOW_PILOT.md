# Ghostframe JPEG carrier pilot

This experiment screened four luminance profiles and five lattice spacings on 11 bundled images. The encoder changes each RGB channel by at most two levels. The same 768 deterministic test bits and block assignments are used across profiles for each image, with three copies per bit. The inputs are previously marked benchmark PNGs. A separate block permutation is used for the pilot. This is an aligned raw-bit comparison without authentication, error correction, resizing, or cropping.

The baseline shifts the whole 8×8 block equally. The inset and taper profiles reduce changes near block borders and put more weight on the center when decoding. The JPEG-aware profile retains the flat block and existing readout but scores candidate shifts using the predicted rounded block brightness at JPEG qualities 85, 70, 50 and 35. The experiment tests actual Pillow JPEG round trips at those and four additional qualities.

| Profile | Spacing | PNG | JPEG 95 | JPEG 85 | JPEG 80 | JPEG 70 | JPEG 60 | JPEG 50 | JPEG 40 | JPEG 35 | Mean squared RGB change |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Flat | 3 | 0 | 0 | 2 | 7 | 24 | 38 | 36 | 137 | 192 | 1.565 |
| Inset | 3 | 0 | 0 | 5 | 12 | 76 | 173 | 351 | 810 | 1096 | 0.881 |
| Taper | 2.5 | 0 | 2 | 18 | 32 | 54 | 145 | 253 | 655 | 1172 | 0.783 |
| Flat, JPEG-aware | 3 | 0 | 0 | 3 | 9 | 25 | 59 | 46 | 194 | 82 | 1.562 |

Each channel column counts bit errors out of 8,448. At JPEG 35, the JPEG-aware profile cut errors by 57% and delivered exact raw bits on four images, up from one. At JPEG 40, a quality absent from the encoder's scoring, errors rose 42% and neither profile yielded a perfect image. JPEG 60 also regressed. The inset and taper profiles changed fewer pixels or changed them less, with more raw errors after compression. No detectability inference follows from mean squared change. The production encoder remains unchanged.

Run from the extracted archive root with Python, NumPy and Pillow:

```sh
python -m experiments.jpeg_window_pilot
```

The included run used Pillow 13.0.0. The JSON contains all 220 image and profile combinations. The pilot completed and enforced the pixel cap on every combination. The full project suite was not rerun in this environment because PyTorch and scikit-image were unavailable.
