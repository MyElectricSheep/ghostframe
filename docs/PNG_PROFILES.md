# ghostframe-png profiles

`ghostframe_png` is the embedding-only PNG carrier with explicit, versioned profiles. It
reuses the frozen SqueezeNet 1.1 reader and preprocessing of `ghostframe.py` and adds
framing, interleaved Reed–Solomon, a margin-verified encoder and a safe I/O contract. The
legacy `message_cli --carrier neural|neural-ecc` formats are unchanged and are available in
the new CLI as `legacy-v1` and `legacy-v2`. Measured results: [BENCHMARK.md](BENCHMARK.md).

## Profiles

| Profile | Cap | Payload | Grid × bits | Parity | Status |
|---|---:|---:|---|---:|---|
| `sw-l2-c10x8b16p48` | 2 | 79 B | 10×8 × 16 | 48 | recommended experimental: held-out 123/123 |
| `sw-l8-c10x8b40p64` | 8 | 302 B | 10×8 × 40 | 64 (2 blocks) | recommended experimental: held-out 123/123 |
| `bb-mobilenet_v3_small-l8-b64p112` | 8 | 494 B | 10×8 × 64 | 112 (3 blocks) | recommended experimental, MobileNetV3-Small reader: held-out 123/123 |
| `bb-mobilenet_v3_small-l8-b40p64` | 8 | 302 B | 10×8 × 40 | 64 (2 blocks) | recommended experimental, MobileNetV3-Small reader: held-out 123/123, ~1.6× faster than `sw-l8` |
| `bb-mobilenet_v3_small-l2-b16p48` | 2 | 79 B | 10×8 × 16 | 48 | recommended experimental, MobileNetV3-Small reader: held-out 123/123, ~1.6× faster than `sw-l2` |
| `png-l2-c10x8b12` | 2 | 63 B | 10×8 × 12 | 24 | experimental: screen and tune 12/12, not held out |
| `png-l8-c10x8b24` | 8 | 175 B | 10×8 × 24 | 32 | experimental: screen 6/6, not held out |
| `legacy-v1` | 8 | 13 B | 6×5 | — | legacy CLI frame; default showcase |
| `legacy-v2` | 2 | 1 B | 6×5 | 14 | legacy CLI frame |

"Recommended experimental" means the profile met the preregistered promotion rule
([BENCHMARK.md](BENCHMARK.md)) on 1280-px photographs. It is not a default, and no stability
promise attaches to it. The profile name is part of the identity, which seeds the carriers and
is the AAD, so a frame decodes only under its exact name.
The `bb-mobilenet_v3_small-*` profiles read tiles with torchvision's MobileNetV3-Small
(checkpoint `047dcff4…`, SHA-256 pinned in `ghostframe_png/backbones.py`) instead of
SqueezeNet. The backbone, its checkpoint and its calibration mean are also part of the identity.

## Command line

```sh
python -m pip install -e '.[tiled]'
ghostframe-png profiles
printf '%s' 'Meet at dawn.' > message.txt
ghostframe-png encode examples/grace_hopper.jpg marked.png --profile sw-l2-c10x8b16p48 --message-file message.txt
ghostframe-png decode marked.png --profile sw-l2-c10x8b16p48 > recovered.txt
```

The commands prompt for a passphrase, or read it from `--passphrase-file` (one trailing
newline is stripped). Decode writes exactly the authenticated bytes to stdout and nothing
else. Exit status: 0 success; 1 no authenticated message (wrong passphrase, wrong profile,
unmarked or damaged image); 2 invalid input or usage; 3 message too long or encoding budget
exhausted. No output file is written unless the saved PNG has already been reopened and
authenticated, and an existing file is never replaced.

## Input contract

- Covers: PNG or JPEG, at most 4 MP, EXIF orientation applied. 8-bit RGB, grayscale and
  palette images are converted to RGB. Opaque alpha is dropped; any transparent pixel is
  rejected. 16-bit, float, CMYK and Lab images are rejected.
- Colour: a cover with an embedded non-sRGB ICC profile (Adobe RGB, Display P3, gray
  dot-gain profiles…) is converted to sRGB with LittleCMS, perceptual intent, and the CLI
  says so on stderr. The RGB cap is measured against the converted cover. sRGB-tagged inputs
  (including the compact "c2" profile Wikimedia thumbnails embed) are used as stored.
- Output: pixels only. No ICC, EXIF, text or time chunks are written.
- Marked images: PNG only. Only the decoded pixel values are read; metadata, filename and
  compression settings are ignored (tests re-serialize at another compression level).
- Size: each tile must be at least 16 pixels on each side, e.g. 160×128 for a 10×8 grid.

## Frame

```
codeword = interleave(RS blocks(frame))
frame    = salt[16] || AES-256-GCM(key, nonce, plaintext, aad = profile identity) incl. tag[16]
plaintext = length[1 or 2, big-endian] || message || zero padding to the frame size
key[32] || nonce[12] = scrypt(passphrase, salt, N=2^17, r=8, p=1, dklen=44)
```

The salt is random per frame (16 bytes from `os.urandom`), so every frame uses a fresh key;
deriving the nonce from the same scrypt output removes 12 bytes of wire overhead compared to
the legacy frames without reusing a (key, nonce) pair. There is no version byte: the profile
identity, which includes the layout, parity, centering flag, the checkpoint digest and the
calibration digest, is the AES-GCM associated data, so a frame only authenticates under the
exact profile and model that produced it. The decoder also requires the zero padding to be
intact. Fixed overhead is 33 bytes (34 when the payload limit exceeds 255 bytes), against 47
in the legacy capacity profiles and 45 + framing in v1/v2.

Codewords longer than 255 bytes are split into ⌈n/255⌉ Reed–Solomon blocks with parity spread
evenly, and codeword byte *j* belongs to block *j* mod *blocks*, so the bits of one tile land in
different blocks. (The legacy capacity script assumed a single block; a frame above 255 − parity
bytes would silently become a longer, mismatched codeword there.)

## Carriers and reader

Each tile is resized to 224×224 (antialiased bilinear), normalized with ImageNet statistics,
passed through the frozen SqueezeNet 1.1 feature stack, spatially averaged and L2-normalized.
Bit *k* of tile *i* is the sign of the dot product with a public ±1 direction derived by
HMAC-SHA256 and SHAKE256 from the profile identity, tile and bit index.

SqueezeNet's pooled features are non-negative, so a random ±1 direction has a large
projection on the average embedding: on the screening and tuning tiles the median per-direction
mean score was about half its spread, and 11 % of directions read the same sign on more than
90 % of unmarked tiles. Centered profiles remove the component along a pinned calibration mean
(computed by `tools/calibrate.py` from screening and tuning covers only; SHA-256 pinned in
`core.py`) before normalizing. The directions remain public; confidentiality and integrity
come from the frame.

## Encoder

Tiles are optimized in batches on quantized 8-bit pixels with a straight-through estimator,
under the per-channel cap. Tiles leave the batch as soon as every signed score reaches the
target margin. After each round the encoder serializes the PNG, reopens it and reads every tile
with the independent single-tile reader. A byte whose weakest bit is below the safety margin
(2·10⁻³; measured CPU batch-vs-single and 1-vs-4-thread differences were ≈10⁻⁷) counts as
possibly wrong; the encode is accepted only when twice the wrong plus at-risk bytes fits in
every block's parity and the saved PNG authenticates. Otherwise only the at-risk tiles are
re-optimized, up to three rounds, then once more with a fresh salt.

## Decoder

One forward pass per tile, then errors-only Reed–Solomon, then up to four retries that erase
the 25/50/75/100 % least-confident bytes of each block (the confidence of a byte is its weakest
bit's |score|). Every candidate must pass AES-GCM; at most eight distinct salts are tried, so
work is bounded for any input. A failure returns no bytes.
