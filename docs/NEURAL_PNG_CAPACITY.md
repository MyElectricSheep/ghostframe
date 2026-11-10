# Embedding-only PNG capacity experiment

The experiment asks how much authenticated payload can survive a saved and reopened PNG with a frozen SqueezeNet 1.1 reader. Each tile yields an embedding. Projection signs supply the bits. The encoder optimizes 8-bit RGB pixels while holding the model weights fixed. The extractor needs the PNG, matching profile and checkpoint. It reads no cover image and no image metadata.

The baseline is the existing 6×5 layout with 16 bits per tile and a 13-byte authenticated payload. The new profiles vary the number of tiles, the bits per tile, projection orthogonalization, and the number of Reed–Solomon parity bytes. They process same-size tiles in batches and stop updating each tile once all its bits match. This differs from the baseline optimizer, which uses up to 100 updates per tile and aims for a positive margin even after signs match. The new profiles used up to 35 updates. The screen compares complete profiles. It cannot isolate the effect of a single variable from these runs.

The 161-byte profile uses 10×8 tiles with 24 bits per tile, for a 240-byte codeword. Thirty-two bytes are reserved for parity and 47 for the version, salt, nonce, authentication tag and payload length. The remaining 161 bytes are the authenticated payload. Every trial was scored on exact plaintext equality after successful AES-GCM authentication. Raw errors are recorded before error correction. All candidate frames use a public test passphrase and fresh random salts and nonces.

## Results

| Profile | Payload | At an eight-level cap | At a two-level cap |
|---|---:|---:|---:|
| Existing 6×5 layout | 13 bytes | 3/3 | 3/3 |
| 24 bits per tile | 43 bytes | 3/3 | 0/1 |
| 24 bits per tile, orthogonal directions | 43 bytes | 3/3 | 0/1 |
| 24 bits per tile, orthogonal directions, parity | 27 bytes | 3/3 | 1/1 |
| 8×8 grid, 16 bits per tile, parity | 57 bytes | 3/3 | 1/1 |
| 8×8 grid, 24 bits per tile, orthogonal directions and parity | 113 bytes | 3/3 | 0/1 |
| 10×8 grid, 24 bits per tile, orthogonal directions and parity | 161 bytes | 3/3 | — |
| 8×8 grid, 12 bits per tile, orthogonal directions and parity | 25 bytes | — | 3/3 |
| 10×8 grid, 12 bits per tile, orthogonal directions and parity | 49 bytes | — | 3/3 |

The 35 screening trials are in `benchmarks/neural-png-capacity-results.json`. The 161-byte profile had zero raw errors across the three screening covers. Its median mean squared RGB change was 11.73 squared channel levels versus 16.45 for the 13-byte baseline at the same cap. This compares the whole encoder profiles and does not measure how visible the changes are. The 49-byte profile had 5, 0 and 0 incorrect bytes before correction. The 113-byte profile at the two-level cap had 35 incorrect bytes on the first cover, beyond its 16-byte correction budget. The two 43-byte profiles without parity both failed at that cap, so this screen does not establish a benefit from orthogonalization alone.

## Verification

The included 161-byte portrait fixture was written to disk and recovered in a second Python process using only the marked PNG, profile, pinned model and fixture password. Its expected message is the sequence of bytes from 0 through 160. A direct corruption control repaired 16 altered codeword bytes, rejected 17, and rejected the unmarked portrait. The ordinary 13-byte fixture remains the primary showcase example. Its original cover rejected authentication and emitted no message in the CLI. All 26 existing automated tests passed.

These are small CPU experiments on PNG pixel-preserving round trips. The capacity measured here is the tested payload size. General image success rates, cross-device inference and visibility thresholds require separate tests. PNG optimization results do not establish robustness to lossy recompression, resizing or cropping. The new profiles are research code and are separate from the existing CLI wire formats.

## Reproduce

Install the pinned project dependencies and tiled extra. Set `SKIMAGE_DATA` to the scikit-image 0.25.2 package data directory containing the three source images.

```bash
python -m experiments.neural_png_capacity \
  "$SKIMAGE_DATA"/{motorcycle_right,ihc,cell}.png \
  --profiles baseline dense dense_qr dense_ecc grid_ecc grid_dense_ecc grid_wide_ecc \
  --caps 8 --steps 35 --output /tmp/ghostframe-capacity-8.json
python -m experiments.neural_png_capacity \
  "$SKIMAGE_DATA"/{motorcycle_right,ihc,cell}.png \
  --profiles baseline grid_light_ecc grid_light_wide_ecc \
  --caps 2 --steps 35 --output /tmp/ghostframe-capacity-2.json
```

Repeat the first-cover, two-level screen with the other profiles if needed.

```bash
python -m experiments.neural_png_capacity "$SKIMAGE_DATA/motorcycle_right.png" \
  --profiles dense dense_qr dense_ecc grid_ecc grid_dense_ecc \
  --caps 2 --steps 35 --output /tmp/ghostframe-capacity-2-screen.json
```

Decode the archived high-capacity PNG directly.

```python
import torch
from experiments.neural_png_capacity import read_codeword, recover
from ghostframe import load_model, read_image

torch.set_num_threads(2)
model = load_model("cpu")
profile = "grid_wide_ecc"
image = read_image("benchmarks/embedding-showcase/neural-161-byte.png")
assert recover(read_codeword(model, image, profile), profile) == bytes(range(161))
```
