# Tiled carrier

The single embedding recovered 0/4 of the earlier 384-bit test payloads from untouched PNGs. This experiment divides each image into 30 nonoverlapping tiles and encodes 16 bits per tile, giving a nominal 480-bit frame. Each tile is independently scored by the same pinned SqueezeNet checkpoint, and the original image dimensions are preserved. The decoder needs the marked image, the model, the fixed grid rules, and the passphrase.

The 60-byte frame comprises a one-byte version, 16-byte random scrypt salt, 12-byte random AES-GCM nonce, 15 bytes of ciphertext, and the 16-byte authentication tag. The encrypted content comprises a two-byte length and 13 bytes of message/padding. The benchmark uses fresh random salt and nonce per cover, shared across that cover's two budget arms for a paired comparison. Tile carriers are public and independently derived by index. The demo passphrase is public. Confidentiality for a private passphrase relies on the authenticated frame and its KDF. The carrier offers no claim of undetectability, and the construction is a research prototype.

The same four cover images from the extended benchmark receive the tiled frame at two and eight RGB levels per channel. A global 480-bit control uses the same frame and the same pixel bound. Both arms use the baseline 100-step cap per optimizer call, so the tiled arm has a larger total compute allowance. There is one randomized frame per cover. Exact recovery requires decryption and an authenticated match to the original 13-byte message. JPEG, scaling, cropping and brightness are measured as independent transformations of the serialized PNG.

[Cryptography AES-GCM documentation](https://cryptography.io/en/stable/hazmat/primitives/aead/)

## Results

| Cover | RGB levels | Tiled PNG errors | Global PNG errors | JPEG 95 errors | Resize errors | Center crop errors | PSNR | Tiled encoding |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| astronaut | 2 | 5 | 190 | 104 | 156 | 188 | 43.25 dB | 33.88 s |
| astronaut | 8 | 0 | 127 | 22 | 81 | 169 | 36.39 dB | 11.44 s |
| coffee | 2 | 4 | 208 | 115 | 160 | 199 | 42.95 dB | 48.21 s |
| coffee | 8 | 0 | 130 | 25 | 77 | 161 | 34.91 dB | 15.18 s |
| rocket | 2 | 0 | 183 | 129 | 165 | 190 | 43.15 dB | 44.33 s |
| rocket | 8 | 0 | 117 | 52 | 119 | 169 | 35.11 dB | 15.34 s |
| chelsea | 2 | 0 | 182 | 122 | 157 | 192 | 42.96 dB | 40.05 s |
| chelsea | 8 | 0 | 113 | 58 | 78 | 165 | 35.27 dB | 14.06 s |

At two levels, 2/4 untouched PNGs and 1/4 brightness-adjusted PNGs authenticated. At eight levels, both conditions authenticated on all four covers. None authenticated after any of the three JPEG settings, the 75% resize, or the center crop. The global control recovered zero frames. A new Python process independently decoded and authenticated the eight-level astronaut PNG without its cover or benchmark result file.

Two-level SSIM ranged from 0.966 to 0.982. Eight-level SSIM ranged from 0.828 to 0.909, and the native-scale coffee comparison shows additional visible texture. The visual panel in benchmarks/tiled/coffee-comparison.png shows the source, two-level result, eight-level result, and the eight-level absolute difference amplified 24×, in reading order.

The 480-bit tiled frame is feasible for this lossless PNG sample. The fixed grid is sensitive to geometric changes and the format has no redundancy. These trials reused four known covers and drew one frame per cover. This does not establish a population-level success rate or concealment from steganalysis. The next targeted experiment is to reduce the message size and reserve the freed capacity for error correction, then measure authenticated recovery at the two-level budget on a larger cover set.
