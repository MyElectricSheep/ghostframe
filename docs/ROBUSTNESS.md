# Geometry, codec, capacity and detection follow-ups

The benchmark reuses the ten source covers and one-byte authenticated codewords from the JPEG carrier experiment. It embeds them with spacing three, three copies and the original two-level maximum RGB change. A successful decode always means the recovered frame passed AES-GCM authentication.

- **Crop with known geometry.** Read only complete blocks visible at their original coordinates. If all three copies of a bit are missing, mark its byte as a Reed–Solomon erasure. The known inputs are original width and height and the crop's top-left pixel offset.
- **Crop search.** Without the original dimensions, test symmetric trim hypotheses of 1–12% per side with ±1 pixel around each estimate. The search stops at the first authenticated result. A centered crop and a specific asymmetric crop are tested separately. The search space is intentionally bounded and assumes symmetric trimming.
- **Resize.** Downsample to 75% with Lanczos and restore the original dimensions with Lanczos before decoding. A synthetic screenshot proxy pastes that resized image into a simulated viewport, losslessly extracts the same pixel region, then restores the original dimensions. It is equivalent to the resize in this setup and provides no independent evidence about OS screenshots.
- **Codecs.** Use the local Pillow build to round-trip JPEG 70 with 4:2:0, WebP lossless, WebP quality 85, and AVIF quality 85, with unchanged dimensions. Codec settings are nominal and are not equivalent quality across formats. [Pillow format options](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html)
- **Detection.** For each expected bit, average the three cosine phase scores and take the absolute value. Average those values across all bits. A detector knowing the carrier's block layout and spacing can score images without a key or source cover. Train a midpoint threshold on all other paired covers, using the highest clean and lowest marked scores, then classify the held-out pair. Train separately on PNG and JPEG 70. This is a small protocol-aware pilot.
- **Capacity.** Use a 96-byte codeword with 24 Reed–Solomon parity bytes and a 72-byte authenticated frame. The encrypted plaintext contains a one-byte length and up to 26 message bytes. Each cover receives a fresh randomized frame containing a 25-byte message. Three copies of 768 bits require 2,304 complete blocks. Eligibility is evaluated before decode. This profile still needs a pre-agreed frame size and carrier configuration.

The corpora are small and reused across experiments. The benchmark uses a public passphrase. No real messaging service or native screenshot workflow was exercised.

## Results

| Geometry case | Authenticated |
|---|---:|
| center_crop_oracle | 10/10 |
| asymmetric_crop_oracle | 10/10 |
| center_crop_blind | 10/10 |
| asymmetric_crop_blind | 0/10 |
| center_crop_then_jpeg70_oracle | 9/10 |
| resize_then_restore_size | 10/10 |
| scaled_screenshot_then_restore_size | 10/10 |

Median centered-crop search time was 0.57 seconds.

| Same-size codec | Authenticated |
|---|---:|
| jpeg70 | 10/10 |
| webp_lossless | 10/10 |
| webp85 | 10/10 |
| avif85 | 10/10 |

| Protocol-aware detection | Marked flagged | Clean flagged |
|---|---:|---:|
| png | 10/10 | 0/10 |
| jpeg70 | 10/10 | 0/10 |

| 25-byte message | Authenticated | Max wrong codeword bytes |
|---|---:|---:|
| png | 10/10 | 0 |
| jpeg70 | 10/10 | 0 |
| jpeg50 | 10/10 | 1 |

The geometry-aware decoder needs the original grid or a search model that includes the actual edit. The results show recovery for the tested geometry with those inputs. Arbitrary framing, unknown scale and off-center crop search remain open. The carrier's repeatable block pattern makes it detectable under the tested protocol-aware threat model, even after JPEG. A larger, independently sampled corpus and detectors without protocol knowledge would be necessary to characterize broader detection rates. These experiments use the conventional luminance carrier. The neural embedding carrier still has its previously measured recompression limits.

The archive contains a quality-70 JPEG that independently decodes to the 25-byte benchmark message. To decode it from the repository root with the public benchmark passphrase:

```sh
python - <<'PY'
from experiments.jpeg_capacity import FRAME_BYTES, unseal
from experiments.jpeg_carrier import extract
from experiments.robustness import OUT
from experiments.tiled import PASSWORD
from ghostframe import read_image

image = read_image(OUT / "demo-message-quality70.jpg")
print(unseal(extract(image, 3, 3, FRAME_BYTES), PASSWORD).decode())
PY
```
