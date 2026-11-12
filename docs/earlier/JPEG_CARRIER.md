# JPEG carrier experiment

## Design

The tiled embedding carrier lost 47–57 of 60 bytes at JPEG quality 95, well past the seven-byte Reed–Solomon correction bound. This follow-up keeps the same one-byte AES-GCM frame, 14 parity bytes, and a two-level maximum RGB change, and replaces the carrier with aligned luminance modulation. The mean luminance of a complete 8×8 block is proportional to its DC term. The encoder tries uniform integer RGB offsets from −2 to +2, with clipping, and chooses the one closest to the lattice for the requested bit. The decoder reads the phase of the resulting block mean and sums the scores across copies when repetition is enabled. It uses a deterministic public block order. The passphrase protects the frame, and the public carrier is a research design with no steganalysis claim.

The three tested settings are two luminance levels of spacing with one or three copies, and three levels of spacing with three copies. Repetition increases the block requirement from 480 to 1,440 complete blocks. The spatial geometry and chosen setting must be known to the decoder. The three JPEG conditions use Pillow 4:2:0 encoding followed by RGB decoding, without a geometry change. Resizing, cropping, and brightness are separate tests. The 480-bit codewords for the six matched covers are reused from the prior tiled experiment. Four additional covers were excluded from that benchmark, although rocket and Chelsea were used in earlier experiments. One codeword per cover is used across settings.

The prior tiled timings used the four-thread CPU setup and included image optimization. The new timings cover luminance embedding only. Authentication, JPEG conversion, and file I/O are excluded. These are pilot measurements on a small sample.

[Chen and Wornell, Quantization Index Modulation](https://sia.mit.edu/wp-content/uploads/2015/04/2001-chen-wornell-it.pdf)

## Results

| Spacing / copies | PNG | JPEG 95 | JPEG 85 | JPEG 70 | Resize | Crop | Brightness | Median PSNR | Embed median |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2 / 1 | 10/10 | 10/10 | 10/10 | 0/10 | 0/10 | 0/10 | 0/10 | 55.58 dB | 8.6 ms |
| 2 / 3 | 10/10 | 10/10 | 10/10 | 10/10 | 0/10 | 0/10 | 1/10 | 50.80 dB | 18.3 ms |
| 3 / 3 | 10/10 | 10/10 | 10/10 | 10/10 | 0/10 | 0/10 | 1/10 | 48.98 dB | 18.8 ms |

## Stress test for spacing two and three copies

| Channel | Raw exact | Corrected exact | Byte error range |
|---|---:|---:|---:|
| jpeg_60_420 | 0/10 | 9/10 | 1–9 |
| jpeg_50_420 | 10/10 | 10/10 | 0–0 |
| jpeg_85_444 | 10/10 | 10/10 | 0–0 |
| jpeg_85_then_70_420 | 1/10 | 9/10 | 0–14 |
| jpeg_70_then_70_420 | 6/10 | 9/10 | 0–9 |

### Stress test for spacing three and three copies

| Channel | Raw exact | Corrected exact | Maximum wrong bytes |
|---|---:|---:|---:|
| JPEG 60, 4:2:0 | 9/10 | 10/10 | 7 |
| JPEG 50, 4:2:0 | 7/10 | 10/10 | 2 |
| JPEG 85, 4:4:4 | 10/10 | 10/10 | 0 |
| JPEG 85 then 70, 4:2:0 | 8/10 | 10/10 | 1 |
| JPEG 70 twice, 4:2:0 | 8/10 | 10/10 | 4 |

## Interpretation

The three-copy luminance arms authenticated all six matched images at quality 95, 85 and 70. The tiled embedding arm authenticated none. Spacing three had zero wrong codeword bytes at quality 70 and authenticated all ten cases in each same-size stress condition after correction. The benchmark includes a standalone quality-70 JPEG fixture. It decodes to the one-byte message with the public test passphrase and no original image. Use `python -m experiments.jpeg_stress` to generate and verify the fixture.

JPEG quality behavior can be nonmonotonic for a lattice carrier. In this Pillow setup the luminance DC quantization steps at qualities 60 and 50 were 13 and 16. The latter coincides with two luminance levels on an 8×8 block, which may explain the spacing-two result at quality 50. These observations apply to the tested codec and alignment. Resizing or cropping changes the block grid, and brightness changes the block means. Those operations remain outside the supported channel. No real messaging-service round trips or steganalysis tests were performed. The embedding experiment and this conventional luminance carrier answer different questions.

The native-scale coffee comparison is in benchmarks/jpeg-carrier/coffee-detail.png. It shows the source, spacing-two output, spacing-three output and the spacing-three absolute difference amplified 96×, in reading order. The block pattern is clear in the amplified difference. The two-level bound and PSNR are fidelity measurements, and detection resistance is unverified.
