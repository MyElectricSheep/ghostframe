# Bounded alignment search

This pilot uses the earlier 60-byte authenticated luminance profile and its ten covers, not the separate 96-byte capacity profile. The encoder changes each RGB channel by at most two levels. The payload and public test passphrase match the earlier benchmark.

For off-center crops, the decoder takes the original width and height and searches every possible integer crop offset, up to 64 total trimmed pixels along each axis. The benchmark trims 13 pixels from the left, 21 from the top, 17 from the right and 9 from the bottom. The exact offset is withheld. A summed-area table lets the decoder read every candidate 8×8 block mean without re-reading the pixels. The search ranks candidates by agreement among the three repeated projections and tries up to 12 Reed–Solomon and authenticated decodes. An aligned clean crop is included as a negative control.

For resizing, the decoder only sees the resized image. It tries integer original dimensions consistent with floor-based scaling by 50%, 62.5%, 75%, 80% or 90%, up to four megapixels. It restores each candidate using Lanczos and uses the same ranking and authentication procedure. The benchmark tests 62.5%, 75% and 80%, plus an unlisted 73% scale. For crop and 75% resize, a separate compound arm adds JPEG quality 70 with 4:2:0 subsampling after the geometry change.

Timing includes alignment search and authenticated decode. This is a constrained pilot on the existing ten covers, with one crop geometry and one frame per cover. No native screenshot or messaging-app workflow was tested.

## Results

| Case | Authenticated | Median decode time |
|---|---:|---:|
| off_center_crop | 10/10 | 0.467 s |
| off_center_crop_jpeg70 | 10/10 | 0.492 s |
| resize_625 | 10/10 | 0.587 s |
| resize_75 | 10/10 | 0.602 s |
| resize_80 | 10/10 | 0.546 s |
| resize_73_unlisted | 0/10 | 0.170 s |
| resize_75_jpeg70 | 10/10 | 0.563 s |
| clean_crop_control | 0/10 | 0.070 s |

All successful cases authenticated on the top-ranked hypothesis. Recovery on the listed scales is limited to the tested resize kernel and rounding convention. The 73% negative arm and clean crop controls produced no authenticated frames. Unknown original dimensions for asymmetric crops and unlisted resizes remain outside the implemented search. The JPEG compound tests use the same local encoder, and the prior protocol-aware detectability result still applies to this carrier.
