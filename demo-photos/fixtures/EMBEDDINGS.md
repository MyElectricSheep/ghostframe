# Embedding data for the demo fixtures

This file holds the data for a graphic showing how each photo's embedding changes when a
message is hidden in it. Each photo appears four ways: untouched, then Classic, Subtle and Long.
It covers the 12 images in `demo-photos/fixtures/`: 3 photos, each untouched and in 3 marked
versions. All numbers were measured by reading the saved PNGs with the same frozen model the
decoder uses (`python -m tools.dump_embeddings`).

## What an "embedding" is here

1. The engine cuts the photo into a grid of tiles:
   - Classic: 6 × 5 = 30 tiles.
   - Subtle and Long: 10 × 8 = 80 tiles.
2. Each tile is shown to a frozen image-recognition network, which summarises it as a list of
   numbers, its embedding:
   - Classic: SqueezeNet 1.1, **512 numbers** per tile.
   - Subtle and Long: MobileNetV3-Small, **576 numbers** per tile.

   The embedding is normalised to length 1, so it is a point on a 512- or 576-dimensional
   sphere.
3. Each hidden bit has a fixed, public direction in that space. The bit's **score**
   is how far the tile's embedding points along that direction (a dot product). Positive reads as
   1, negative as 0.
4. Each tile carries several bits: 16 for Classic and Subtle, 64 for Long.

The encoder changes pixels by at most 8 levels (Classic, Long) or 2 levels (Subtle) out of 255.
That moves each tile's embedding until every score sits on the correct side of zero, with a
safety gap.


## Three things worth showing

1. **The pixels barely change, but the embedding moves a lot.** The median cosine similarity
   between a tile's embedding before and after, where 1 means unchanged, is:
   - Classic: 0.59–0.76
   - Subtle: 0.68–0.80
   - Long: 0.53–0.63

   The lowest single tile is 0.17. The network is very sensitive to tiny,
   targeted pixel changes, and that is exactly what the engine exploits.
2. **About half the bits flip.** The hidden data is encrypted, so it looks random, and roughly
   half the scores have to change sign. The rest only need to be pushed further from zero.
3. **A gap opens around zero.** In the untouched photo, scores form a smooth hump centred on
   zero. In every marked photo, nothing is left near zero:
   - Classic: every score is beyond ±0.029.
   - Subtle and Long: every score is beyond ±0.011, the encoder's
     margin for MobileNetV3.

   That empty band is what makes the message readable, and it is also why the presence of a
   message is detectable.

   Histograms of before and after scores, showing this gap, make the clearest single graphic.

## Summary per photo and mode

"Shift" is the straight-line distance each tile's embedding moved, on a sphere where 2 is the
largest possible distance. Scores are given as absolute values.

| Photo | Mode | Tiles | Hidden bits | Cosine to original (median / lowest) | Shift (median) | Bits flipped | Median score size: original → marked | Smallest marked score |
|---|---|---:|---:|---|---:|---:|---|---:|
| Coffee beans | Classic | 30 | 480 | 0.759 / 0.625 | 0.695 | 239 (50 %) | 0.0297 → 0.0378 | 0.0301 |
| Coffee beans | Subtle | 80 | 1280 | 0.787 / 0.566 | 0.652 | 639 (50 %) | 0.0264 → 0.0240 | 0.0108 |
| Coffee beans | Long | 80 | 5120 | 0.627 / 0.380 | 0.863 | 2559 (50 %) | 0.0271 → 0.0195 | 0.0108 |
| Milky Way | Classic | 30 | 480 | 0.589 / 0.447 | 0.907 | 246 (51 %) | 0.0280 → 0.0365 | 0.0311 |
| Milky Way | Subtle | 80 | 1280 | 0.798 / 0.449 | 0.635 | 668 (52 %) | 0.0255 → 0.0187 | 0.0108 |
| Milky Way | Long | 80 | 5120 | 0.572 / 0.337 | 0.925 | 2580 (50 %) | 0.0256 → 0.0183 | 0.0108 |
| Antonello portrait | Classic | 30 | 480 | 0.617 / 0.397 | 0.875 | 250 (52 %) | 0.0285 → 0.0377 | 0.0294 |
| Antonello portrait | Subtle | 80 | 1280 | 0.678 / 0.218 | 0.803 | 645 (50 %) | 0.0253 → 0.0256 | 0.0109 |
| Antonello portrait | Long | 80 | 5120 | 0.534 / 0.169 | 0.965 | 2507 (49 %) | 0.0264 → 0.0204 | 0.0108 |

## Score histograms (the "gap" graphic)

Each cell counts the scores that fall in one bin. Bins are 0.01 wide, from −0.08 to +0.08. Scores
beyond ±0.08 are counted in the end bins. Each row sums to that mode's total number of hidden bits.

### Coffee beans

| Series | -0.08…-0.07 | -0.07…-0.06 | -0.06…-0.05 | -0.05…-0.04 | -0.04…-0.03 | -0.03…-0.02 | -0.02…-0.01 | -0.01…0.00 | 0.00…+0.01 | +0.01…+0.02 | +0.02…+0.03 | +0.03…+0.04 | +0.04…+0.05 | +0.05…+0.06 | +0.06…+0.07 | +0.07…+0.08 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Classic: untouched | 24 | 16 | 16 | 21 | 29 | 33 | 38 | 40 | 52 | 32 | 47 | 37 | 33 | 25 | 13 | 24 |
| Classic: marked | 13 | 9 | 23 | 43 | 142 | 0 | 0 | 0 | 0 | 0 | 0 | 158 | 51 | 19 | 8 | 14 |
| Subtle: untouched | 40 | 32 | 47 | 78 | 80 | 101 | 126 | 121 | 132 | 129 | 105 | 85 | 74 | 38 | 43 | 49 |
| Subtle: marked | 20 | 21 | 31 | 65 | 98 | 149 | 264 | 0 | 0 | 239 | 147 | 99 | 48 | 39 | 29 | 31 |
| Long: untouched | 189 | 141 | 216 | 266 | 339 | 402 | 472 | 540 | 519 | 481 | 394 | 330 | 264 | 217 | 154 | 196 |
| Long: marked | 116 | 70 | 94 | 175 | 258 | 551 | 1290 | 0 | 0 | 1348 | 517 | 245 | 159 | 114 | 72 | 111 |

### Milky Way

| Series | -0.08…-0.07 | -0.07…-0.06 | -0.06…-0.05 | -0.05…-0.04 | -0.04…-0.03 | -0.03…-0.02 | -0.02…-0.01 | -0.01…0.00 | 0.00…+0.01 | +0.01…+0.02 | +0.02…+0.03 | +0.03…+0.04 | +0.04…+0.05 | +0.05…+0.06 | +0.06…+0.07 | +0.07…+0.08 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Classic: untouched | 18 | 16 | 21 | 21 | 28 | 37 | 57 | 40 | 36 | 45 | 37 | 27 | 23 | 27 | 16 | 31 |
| Classic: marked | 16 | 3 | 17 | 36 | 170 | 0 | 0 | 0 | 0 | 0 | 0 | 165 | 34 | 14 | 10 | 15 |
| Subtle: untouched | 34 | 30 | 43 | 71 | 100 | 124 | 130 | 132 | 115 | 123 | 110 | 89 | 72 | 40 | 30 | 37 |
| Subtle: marked | 19 | 13 | 27 | 45 | 56 | 136 | 344 | 0 | 0 | 345 | 126 | 61 | 46 | 26 | 15 | 21 |
| Long: untouched | 162 | 131 | 193 | 270 | 351 | 432 | 500 | 534 | 528 | 513 | 428 | 341 | 288 | 179 | 120 | 150 |
| Long: marked | 95 | 79 | 117 | 166 | 219 | 445 | 1417 | 0 | 0 | 1423 | 471 | 257 | 162 | 107 | 76 | 86 |

### Antonello portrait

| Series | -0.08…-0.07 | -0.07…-0.06 | -0.06…-0.05 | -0.05…-0.04 | -0.04…-0.03 | -0.03…-0.02 | -0.02…-0.01 | -0.01…0.00 | 0.00…+0.01 | +0.01…+0.02 | +0.02…+0.03 | +0.03…+0.04 | +0.04…+0.05 | +0.05…+0.06 | +0.06…+0.07 | +0.07…+0.08 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Classic: untouched | 28 | 11 | 20 | 16 | 28 | 32 | 57 | 38 | 40 | 43 | 36 | 40 | 27 | 18 | 15 | 31 |
| Classic: marked | 13 | 11 | 25 | 52 | 140 | 1 | 0 | 0 | 0 | 0 | 1 | 147 | 48 | 16 | 12 | 14 |
| Subtle: untouched | 41 | 32 | 51 | 62 | 88 | 119 | 140 | 120 | 99 | 136 | 117 | 72 | 72 | 56 | 32 | 43 |
| Subtle: marked | 32 | 18 | 36 | 65 | 92 | 161 | 234 | 0 | 0 | 199 | 157 | 106 | 74 | 50 | 22 | 34 |
| Long: untouched | 163 | 139 | 207 | 299 | 364 | 403 | 477 | 549 | 500 | 468 | 422 | 348 | 304 | 173 | 121 | 183 |
| Long: marked | 117 | 71 | 106 | 179 | 292 | 552 | 1259 | 0 | 0 | 1246 | 575 | 271 | 181 | 96 | 67 | 108 |

The "untouched" rows differ between modes because each mode reads the photo through its own
grid and its own directions. For one picture per photo, show the Subtle or Long pair: they share
the 10 × 8 grid.

## Change per tile (heat-map data)

The cosine similarity between each tile's embedding before and after marking. Rows and columns
follow the photo's layout, top-left first. Lower numbers mean the tile moved more. Draw these as
a heat map over the photo.

### Coffee beans

**Classic** (6 × 5)

| | c1 | c2 | c3 | c4 | c5 | c6 |
|---|---:|---:|---:|---:|---:|---:|
| r1 | 0.73 | 0.77 | 0.66 | 0.81 | 0.73 | 0.62 |
| r2 | 0.86 | 0.66 | 0.72 | 0.78 | 0.80 | 0.72 |
| r3 | 0.71 | 0.78 | 0.83 | 0.78 | 0.77 | 0.78 |
| r4 | 0.70 | 0.72 | 0.79 | 0.74 | 0.75 | 0.73 |
| r5 | 0.75 | 0.78 | 0.76 | 0.81 | 0.82 | 0.75 |

**Subtle** (10 × 8)

| | c1 | c2 | c3 | c4 | c5 | c6 | c7 | c8 | c9 | c10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| r1 | 0.65 | 0.88 | 0.57 | 0.73 | 0.85 | 0.73 | 0.72 | 0.76 | 0.75 | 0.78 |
| r2 | 0.71 | 0.81 | 0.86 | 0.85 | 0.68 | 0.89 | 0.76 | 0.71 | 0.84 | 0.76 |
| r3 | 0.78 | 0.82 | 0.85 | 0.80 | 0.82 | 0.83 | 0.89 | 0.87 | 0.64 | 0.68 |
| r4 | 0.68 | 0.85 | 0.87 | 0.90 | 0.82 | 0.84 | 0.74 | 0.76 | 0.87 | 0.79 |
| r5 | 0.87 | 0.71 | 0.83 | 0.75 | 0.86 | 0.78 | 0.78 | 0.83 | 0.87 | 0.79 |
| r6 | 0.85 | 0.74 | 0.76 | 0.81 | 0.89 | 0.81 | 0.77 | 0.83 | 0.71 | 0.81 |
| r7 | 0.66 | 0.77 | 0.79 | 0.79 | 0.72 | 0.68 | 0.62 | 0.67 | 0.76 | 0.85 |
| r8 | 0.85 | 0.70 | 0.73 | 0.80 | 0.82 | 0.57 | 0.83 | 0.79 | 0.71 | 0.75 |

**Long** (10 × 8)

| | c1 | c2 | c3 | c4 | c5 | c6 | c7 | c8 | c9 | c10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| r1 | 0.60 | 0.61 | 0.67 | 0.61 | 0.44 | 0.61 | 0.65 | 0.65 | 0.57 | 0.68 |
| r2 | 0.65 | 0.77 | 0.57 | 0.57 | 0.77 | 0.65 | 0.63 | 0.58 | 0.62 | 0.51 |
| r3 | 0.75 | 0.66 | 0.68 | 0.63 | 0.59 | 0.75 | 0.71 | 0.59 | 0.60 | 0.45 |
| r4 | 0.64 | 0.70 | 0.63 | 0.67 | 0.57 | 0.70 | 0.55 | 0.57 | 0.71 | 0.52 |
| r5 | 0.65 | 0.70 | 0.66 | 0.68 | 0.62 | 0.66 | 0.66 | 0.59 | 0.73 | 0.57 |
| r6 | 0.70 | 0.64 | 0.62 | 0.65 | 0.69 | 0.61 | 0.65 | 0.57 | 0.62 | 0.56 |
| r7 | 0.55 | 0.71 | 0.74 | 0.75 | 0.64 | 0.42 | 0.64 | 0.55 | 0.54 | 0.45 |
| r8 | 0.65 | 0.54 | 0.53 | 0.62 | 0.38 | 0.59 | 0.69 | 0.58 | 0.64 | 0.40 |

### Milky Way

**Classic** (6 × 5)

| | c1 | c2 | c3 | c4 | c5 | c6 |
|---|---:|---:|---:|---:|---:|---:|
| r1 | 0.58 | 0.62 | 0.52 | 0.59 | 0.72 | 0.53 |
| r2 | 0.48 | 0.57 | 0.66 | 0.71 | 0.68 | 0.58 |
| r3 | 0.66 | 0.47 | 0.55 | 0.66 | 0.59 | 0.60 |
| r4 | 0.76 | 0.68 | 0.57 | 0.45 | 0.57 | 0.50 |
| r5 | 0.58 | 0.74 | 0.69 | 0.79 | 0.82 | 0.54 |

**Subtle** (10 × 8)

| | c1 | c2 | c3 | c4 | c5 | c6 | c7 | c8 | c9 | c10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| r1 | 0.74 | 0.72 | 0.87 | 0.68 | 0.83 | 0.83 | 0.66 | 0.82 | 0.76 | 0.45 |
| r2 | 0.68 | 0.64 | 0.87 | 0.80 | 0.75 | 0.72 | 0.87 | 0.74 | 0.69 | 0.72 |
| r3 | 0.83 | 0.45 | 0.90 | 0.87 | 0.84 | 0.69 | 0.70 | 0.62 | 0.64 | 0.86 |
| r4 | 0.88 | 0.82 | 0.82 | 0.83 | 0.84 | 0.90 | 0.73 | 0.82 | 0.76 | 0.84 |
| r5 | 0.80 | 0.79 | 0.72 | 0.81 | 0.75 | 0.78 | 0.74 | 0.80 | 0.82 | 0.58 |
| r6 | 0.84 | 0.78 | 0.86 | 0.82 | 0.83 | 0.80 | 0.64 | 0.73 | 0.75 | 0.84 |
| r7 | 0.76 | 0.87 | 0.83 | 0.88 | 0.78 | 0.83 | 0.77 | 0.84 | 0.64 | 0.60 |
| r8 | 0.77 | 0.80 | 0.78 | 0.91 | 0.80 | 0.95 | 0.87 | 0.67 | 0.85 | 0.77 |

**Long** (10 × 8)

| | c1 | c2 | c3 | c4 | c5 | c6 | c7 | c8 | c9 | c10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| r1 | 0.61 | 0.34 | 0.50 | 0.41 | 0.68 | 0.67 | 0.46 | 0.49 | 0.61 | 0.51 |
| r2 | 0.39 | 0.43 | 0.52 | 0.68 | 0.66 | 0.58 | 0.54 | 0.64 | 0.42 | 0.63 |
| r3 | 0.66 | 0.63 | 0.60 | 0.60 | 0.48 | 0.60 | 0.35 | 0.64 | 0.46 | 0.61 |
| r4 | 0.56 | 0.49 | 0.43 | 0.56 | 0.62 | 0.62 | 0.42 | 0.39 | 0.57 | 0.46 |
| r5 | 0.59 | 0.66 | 0.50 | 0.76 | 0.47 | 0.41 | 0.53 | 0.67 | 0.35 | 0.47 |
| r6 | 0.55 | 0.60 | 0.52 | 0.62 | 0.60 | 0.47 | 0.61 | 0.65 | 0.59 | 0.66 |
| r7 | 0.62 | 0.57 | 0.75 | 0.49 | 0.67 | 0.61 | 0.44 | 0.74 | 0.46 | 0.59 |
| r8 | 0.59 | 0.51 | 0.53 | 0.64 | 0.55 | 0.52 | 0.65 | 0.51 | 0.58 | 0.57 |

### Antonello portrait

**Classic** (6 × 5)

| | c1 | c2 | c3 | c4 | c5 | c6 |
|---|---:|---:|---:|---:|---:|---:|
| r1 | 0.64 | 0.59 | 0.61 | 0.69 | 0.64 | 0.62 |
| r2 | 0.43 | 0.84 | 0.65 | 0.71 | 0.65 | 0.52 |
| r3 | 0.40 | 0.67 | 0.60 | 0.42 | 0.53 | 0.48 |
| r4 | 0.58 | 0.72 | 0.70 | 0.77 | 0.67 | 0.46 |
| r5 | 0.80 | 0.57 | 0.62 | 0.58 | 0.60 | 0.72 |

**Subtle** (10 × 8)

| | c1 | c2 | c3 | c4 | c5 | c6 | c7 | c8 | c9 | c10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| r1 | 0.82 | 0.73 | 0.49 | 0.39 | 0.59 | 0.61 | 0.57 | 0.75 | 0.71 | 0.69 |
| r2 | 0.84 | 0.56 | 0.44 | 0.81 | 0.68 | 0.73 | 0.78 | 0.55 | 0.75 | 0.32 |
| r3 | 0.55 | 0.29 | 0.84 | 0.88 | 0.84 | 0.82 | 0.55 | 0.62 | 0.63 | 0.79 |
| r4 | 0.71 | 0.71 | 0.60 | 0.56 | 0.79 | 0.74 | 0.79 | 0.68 | 0.73 | 0.84 |
| r5 | 0.77 | 0.74 | 0.68 | 0.84 | 0.68 | 0.28 | 0.76 | 0.51 | 0.87 | 0.64 |
| r6 | 0.67 | 0.39 | 0.45 | 0.82 | 0.70 | 0.87 | 0.70 | 0.61 | 0.54 | 0.76 |
| r7 | 0.60 | 0.65 | 0.65 | 0.61 | 0.56 | 0.84 | 0.70 | 0.22 | 0.73 | 0.45 |
| r8 | 0.67 | 0.59 | 0.74 | 0.67 | 0.54 | 0.60 | 0.44 | 0.72 | 0.54 | 0.67 |

**Long** (10 × 8)

| | c1 | c2 | c3 | c4 | c5 | c6 | c7 | c8 | c9 | c10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| r1 | 0.45 | 0.50 | 0.38 | 0.44 | 0.49 | 0.50 | 0.59 | 0.43 | 0.40 | 0.69 |
| r2 | 0.40 | 0.51 | 0.58 | 0.52 | 0.72 | 0.74 | 0.32 | 0.57 | 0.51 | 0.48 |
| r3 | 0.58 | 0.58 | 0.51 | 0.72 | 0.56 | 0.61 | 0.61 | 0.66 | 0.44 | 0.61 |
| r4 | 0.62 | 0.64 | 0.65 | 0.59 | 0.67 | 0.46 | 0.44 | 0.67 | 0.45 | 0.46 |
| r5 | 0.39 | 0.45 | 0.53 | 0.64 | 0.59 | 0.59 | 0.34 | 0.50 | 0.71 | 0.57 |
| r6 | 0.59 | 0.63 | 0.31 | 0.50 | 0.55 | 0.43 | 0.56 | 0.54 | 0.43 | 0.51 |
| r7 | 0.44 | 0.51 | 0.43 | 0.63 | 0.59 | 0.62 | 0.36 | 0.39 | 0.48 | 0.64 |
| r8 | 0.65 | 0.62 | 0.55 | 0.62 | 0.59 | 0.49 | 0.39 | 0.17 | 0.50 | 0.64 |

## A sample of the raw embedding

These are the first 12 numbers for the top-left tile of each photo, untouched and marked. Subtle
and Long share the 10 × 8 grid and MobileNetV3-Small (576 numbers per tile). Classic uses a
coarser 6 × 5 grid and SqueezeNet 1.1 (512 numbers), so its rows are listed separately and are
not comparable with the others.

### Coffee beans

| Series | d0 | d1 | d2 | d3 | d4 | d5 | d6 | d7 | d8 | d9 | d10 | d11 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Untouched (10 × 8 tile) | -0.0014 | -0.0114 | -0.0066 | 0.0094 | -0.0078 | -0.0053 | 0.0073 | 0.0397 | 0.0039 | 0.0170 | 0.0589 | -0.0206 |
| Subtle | -0.0080 | -0.0112 | -0.0066 | 0.0017 | -0.0262 | -0.0086 | -0.0132 | -0.0080 | -0.0072 | -0.0189 | 0.0044 | -0.0257 |
| Long | 0.0032 | -0.0133 | 0.0030 | 0.0138 | 0.0298 | 0.0269 | 0.0483 | 0.0540 | -0.0077 | 0.0390 | 0.0152 | -0.0148 |
| Untouched (6 × 5 tile) | 0.1269 | 0.0889 | 0.0172 | 0.0211 | 0.0293 | 0.0047 | 0.0014 | 0.0365 | 0.0022 | 0.0064 | 0.0000 | 0.0012 |
| Classic | 0.0748 | 0.0199 | 0.0000 | 0.0092 | 0.0130 | 0.0017 | 0.0010 | 0.0834 | 0.0031 | 0.0099 | 0.0014 | 0.0284 |

### Milky Way

| Series | d0 | d1 | d2 | d3 | d4 | d5 | d6 | d7 | d8 | d9 | d10 | d11 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Untouched (10 × 8 tile) | 0.0143 | -0.0339 | -0.0217 | -0.0410 | -0.0371 | -0.0176 | 0.0000 | -0.0425 | -0.0164 | -0.0389 | -0.0471 | -0.0438 |
| Subtle | 0.0204 | -0.0185 | -0.0205 | -0.0276 | 0.0599 | -0.0299 | -0.0060 | -0.0388 | -0.0344 | -0.0079 | -0.0379 | -0.0402 |
| Long | -0.0223 | -0.0294 | 0.0007 | -0.0319 | -0.0434 | -0.0114 | -0.0171 | -0.0351 | -0.0336 | -0.0245 | -0.0379 | 0.0071 |
| Untouched (6 × 5 tile) | 0.0052 | 0.0000 | 0.0008 | 0.0000 | 0.0008 | 0.0000 | 0.0414 | 0.0016 | 0.0000 | 0.0164 | 0.0558 | 0.0014 |
| Classic | 0.0184 | 0.0427 | 0.0103 | 0.0000 | 0.0191 | 0.0000 | 0.0044 | 0.1154 | 0.0000 | 0.0364 | 0.0241 | 0.0001 |

### Antonello portrait

| Series | d0 | d1 | d2 | d3 | d4 | d5 | d6 | d7 | d8 | d9 | d10 | d11 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Untouched (10 × 8 tile) | -0.0120 | -0.0347 | -0.0239 | -0.0391 | -0.0259 | 0.0244 | -0.0331 | -0.0115 | 0.0096 | -0.0259 | -0.0288 | -0.0278 |
| Subtle | -0.0176 | -0.0207 | -0.0110 | -0.0269 | 0.0158 | 0.0270 | -0.0200 | -0.0307 | -0.0064 | -0.0206 | -0.0197 | -0.0254 |
| Long | -0.0193 | -0.0307 | 0.0675 | -0.0333 | -0.0278 | -0.0098 | -0.0252 | 0.0312 | -0.0108 | 0.0200 | -0.0263 | -0.0101 |
| Untouched (6 × 5 tile) | 0.0003 | 0.0029 | 0.0005 | 0.0001 | 0.0025 | 0.0000 | 0.0103 | 0.0180 | 0.0000 | 0.0880 | 0.0215 | 0.0029 |
| Classic | 0.0101 | 0.0259 | 0.0273 | 0.0038 | 0.0046 | 0.0001 | 0.0144 | 0.0691 | 0.0000 | 0.0522 | 0.0516 | 0.0000 |

The two models' numbers look different:
- **SqueezeNet (Classic)** clips negative values to zero, so many values are exactly zero. In the
  untouched photos it is 13 % for the coffee beans, 35 % for the portrait and 57 % for
  the Milky Way, where a dark sky leaves many features unused.
- **MobileNetV3 (Subtle, Long)** ends in a smooth activation that allows small negative values.
  None of its values is exactly zero, and 44 % (coffee beans), 68 % (portrait) and 77 % (Milky Way) are negative.

## Full data

`demo-photos/fixtures/embeddings/<photo>.json` holds everything, for each mode:

| Key | Contents | Shape |
|---|---|---|
| `embeddings_original`, `embeddings_marked` | every tile's embedding, before and after | tiles × 512 (Classic) or 576 (Subtle, Long) |
| `scores_original`, `scores_marked` | every bit's score, before and after | tiles × bits per tile |
| `tile_cosine`, `tile_shift` | how much each tile moved | tiles |
| `bits_flipped_per_tile` | how many bits changed sign in each tile | tiles |

Values are rounded to 5 decimals. `summary.json` has the per-mode figures above.

### Ideas for the graphic

- **Before/after histograms** (the clearest): a smooth hump turns into two humps with an empty
  band in the middle.
- **Heat map over the photo:** shows which parts of the picture moved most.
- **2-D scatter:** project the 80 tile embeddings to 2-D (PCA or UMAP, fitted on the untouched
  tiles) and draw an arrow from each untouched tile to its marked position for Subtle and Long.
  It is a lossy view of 576 dimensions; say so in the caption.

Keep one caveat in the caption: these numbers come from one model build on one CPU. Other
hardware has not been tested.
