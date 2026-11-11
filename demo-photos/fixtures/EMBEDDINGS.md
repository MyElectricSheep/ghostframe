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
2. Each tile is shown to a frozen image-recognition network (SqueezeNet 1.1). The network
   summarises the tile as **512 numbers**, its embedding. It is normalised to length 1, so it is
   a point on a 512-dimensional sphere.
3. Each hidden bit has a fixed, public direction in that 512-number space. The bit's **score**
   is how far the tile's embedding points along that direction (a dot product). Positive reads as
   1, negative as 0.
4. Each tile carries several bits: 16 for Classic and Subtle, 40 for Long.

The encoder changes pixels by at most 8 levels (Classic, Long) or 2 levels (Subtle) out of 255.
That moves each tile's embedding until every score sits on the correct side of zero, with a
safety gap.

## Three things worth showing

1. **The pixels barely change, but the embedding moves a lot.** The median cosine similarity
   between a tile's embedding before and after is only 0.59–0.86, where 1 means unchanged. The
   lowest is 0.39.
   The network is very sensitive to tiny, targeted pixel changes, and that is exactly what the
   engine exploits.
2. **About half the bits flip.** The hidden data is encrypted, so it looks random, and roughly
   half the scores have to change sign. The rest only need to be pushed further from zero.
3. **A gap opens around zero.** In the untouched photo, scores form a smooth hump centred on
   zero. In every marked photo, nothing is left near zero:
   - Classic: every score is beyond about ±0.03.
   - Subtle and Long: every score is beyond ±0.01.

   That empty band is what makes the message readable, and it is also why the presence of a
   message is detectable.

   Histograms of before and after scores, showing this gap, make the clearest single graphic.

## Summary per photo and mode

"Shift" is the straight-line distance each tile's embedding moved, on a sphere where 2 is the
largest possible distance. Scores are given as absolute values.

| Photo | Mode | Tiles | Hidden bits | Cosine to original (median / lowest) | Shift (median) | Bits flipped | Median score size: original → marked | Smallest marked score |
|---|---|---:|---:|---|---:|---:|---|---:|
| Coffee beans | Classic | 30 | 480 | 0.759 / 0.625 | 0.695 | 239 (50 %) | 0.0297 → 0.0378 | 0.0301 |
| Coffee beans | Subtle | 80 | 1280 | 0.861 / 0.784 | 0.527 | 638 (50 %) | 0.0261 → 0.0201 | 0.0100 |
| Coffee beans | Long | 80 | 3200 | 0.751 / 0.601 | 0.705 | 1616 (50 %) | 0.0259 → 0.0185 | 0.0100 |
| Milky Way | Classic | 30 | 480 | 0.589 / 0.447 | 0.907 | 246 (51 %) | 0.0280 → 0.0365 | 0.0311 |
| Milky Way | Subtle | 80 | 1280 | 0.795 / 0.577 | 0.640 | 621 (49 %) | 0.0273 → 0.0166 | 0.0100 |
| Milky Way | Long | 80 | 3200 | 0.637 / 0.405 | 0.852 | 1634 (51 %) | 0.0291 → 0.0158 | 0.0100 |
| Antonello portrait | Classic | 30 | 480 | 0.617 / 0.397 | 0.875 | 250 (52 %) | 0.0285 → 0.0377 | 0.0294 |
| Antonello portrait | Subtle | 80 | 1280 | 0.745 / 0.546 | 0.715 | 639 (50 %) | 0.0284 → 0.0208 | 0.0100 |
| Antonello portrait | Long | 80 | 3200 | 0.662 / 0.388 | 0.823 | 1627 (51 %) | 0.0264 → 0.0175 | 0.0100 |

## Score histograms (the "gap" graphic)

Each cell counts the scores that fall in one bin. Bins are 0.01 wide, from −0.08 to +0.08. Scores
beyond ±0.08 are counted in the end bins. Each row sums to that mode's total number of hidden bits.

### Coffee beans

| Series | -0.08…-0.07 | -0.07…-0.06 | -0.06…-0.05 | -0.05…-0.04 | -0.04…-0.03 | -0.03…-0.02 | -0.02…-0.01 | -0.01…0.00 | 0.00…+0.01 | +0.01…+0.02 | +0.02…+0.03 | +0.03…+0.04 | +0.04…+0.05 | +0.05…+0.06 | +0.06…+0.07 | +0.07…+0.08 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Classic: untouched | 24 | 16 | 16 | 21 | 29 | 33 | 38 | 40 | 52 | 32 | 47 | 37 | 33 | 25 | 13 | 24 |
| Classic: marked | 13 | 9 | 23 | 43 | 142 | 0 | 0 | 0 | 0 | 0 | 0 | 158 | 51 | 19 | 8 | 14 |
| Subtle: untouched | 39 | 31 | 44 | 54 | 107 | 93 | 125 | 129 | 137 | 116 | 113 | 92 | 70 | 52 | 38 | 40 |
| Subtle: marked | 19 | 16 | 26 | 39 | 77 | 134 | 325 | 0 | 0 | 312 | 141 | 71 | 50 | 31 | 21 | 18 |
| Long: untouched | 114 | 81 | 110 | 164 | 222 | 267 | 318 | 335 | 324 | 305 | 245 | 224 | 180 | 121 | 82 | 108 |
| Long: marked | 36 | 41 | 61 | 97 | 157 | 329 | 867 | 0 | 0 | 927 | 319 | 149 | 97 | 49 | 40 | 31 |

### Milky Way

| Series | -0.08…-0.07 | -0.07…-0.06 | -0.06…-0.05 | -0.05…-0.04 | -0.04…-0.03 | -0.03…-0.02 | -0.02…-0.01 | -0.01…0.00 | 0.00…+0.01 | +0.01…+0.02 | +0.02…+0.03 | +0.03…+0.04 | +0.04…+0.05 | +0.05…+0.06 | +0.06…+0.07 | +0.07…+0.08 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Classic: untouched | 18 | 16 | 21 | 21 | 28 | 37 | 57 | 40 | 36 | 45 | 37 | 27 | 23 | 27 | 16 | 31 |
| Classic: marked | 16 | 3 | 17 | 36 | 170 | 0 | 0 | 0 | 0 | 0 | 0 | 165 | 34 | 14 | 10 | 15 |
| Subtle: untouched | 48 | 41 | 52 | 52 | 79 | 99 | 117 | 121 | 118 | 136 | 111 | 82 | 75 | 57 | 45 | 47 |
| Subtle: marked | 16 | 12 | 30 | 41 | 53 | 105 | 358 | 1 | 0 | 381 | 85 | 62 | 44 | 30 | 30 | 32 |
| Long: untouched | 130 | 96 | 138 | 191 | 218 | 268 | 261 | 287 | 298 | 289 | 262 | 215 | 182 | 116 | 89 | 160 |
| Long: marked | 63 | 45 | 77 | 91 | 133 | 206 | 967 | 0 | 0 | 1010 | 242 | 119 | 80 | 47 | 49 | 71 |

### Antonello portrait

| Series | -0.08…-0.07 | -0.07…-0.06 | -0.06…-0.05 | -0.05…-0.04 | -0.04…-0.03 | -0.03…-0.02 | -0.02…-0.01 | -0.01…0.00 | 0.00…+0.01 | +0.01…+0.02 | +0.02…+0.03 | +0.03…+0.04 | +0.04…+0.05 | +0.05…+0.06 | +0.06…+0.07 | +0.07…+0.08 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Classic: untouched | 28 | 11 | 20 | 16 | 28 | 32 | 57 | 38 | 40 | 43 | 36 | 40 | 27 | 18 | 15 | 31 |
| Classic: marked | 13 | 11 | 25 | 52 | 140 | 1 | 0 | 0 | 0 | 0 | 1 | 147 | 48 | 16 | 12 | 14 |
| Subtle: untouched | 44 | 33 | 53 | 69 | 85 | 88 | 119 | 130 | 120 | 115 | 105 | 95 | 76 | 55 | 33 | 60 |
| Subtle: marked | 20 | 14 | 35 | 35 | 70 | 141 | 321 | 0 | 0 | 289 | 152 | 60 | 49 | 43 | 17 | 34 |
| Long: untouched | 120 | 80 | 114 | 182 | 241 | 250 | 308 | 304 | 320 | 308 | 277 | 195 | 167 | 112 | 84 | 138 |
| Long: marked | 69 | 55 | 68 | 82 | 145 | 243 | 938 | 0 | 0 | 950 | 264 | 129 | 87 | 72 | 43 | 55 |

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
| r1 | 0.83 | 0.86 | 0.84 | 0.83 | 0.92 | 0.83 | 0.87 | 0.87 | 0.79 | 0.85 |
| r2 | 0.84 | 0.79 | 0.79 | 0.85 | 0.87 | 0.88 | 0.86 | 0.86 | 0.89 | 0.85 |
| r3 | 0.87 | 0.88 | 0.86 | 0.81 | 0.88 | 0.91 | 0.86 | 0.88 | 0.92 | 0.88 |
| r4 | 0.92 | 0.85 | 0.85 | 0.87 | 0.89 | 0.90 | 0.85 | 0.90 | 0.89 | 0.84 |
| r5 | 0.88 | 0.86 | 0.90 | 0.92 | 0.83 | 0.83 | 0.88 | 0.89 | 0.89 | 0.81 |
| r6 | 0.80 | 0.87 | 0.88 | 0.89 | 0.86 | 0.91 | 0.83 | 0.85 | 0.84 | 0.89 |
| r7 | 0.81 | 0.91 | 0.90 | 0.84 | 0.86 | 0.84 | 0.88 | 0.86 | 0.84 | 0.78 |
| r8 | 0.85 | 0.90 | 0.90 | 0.85 | 0.88 | 0.86 | 0.82 | 0.83 | 0.88 | 0.85 |

**Long** (10 × 8)

| | c1 | c2 | c3 | c4 | c5 | c6 | c7 | c8 | c9 | c10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| r1 | 0.77 | 0.82 | 0.72 | 0.70 | 0.69 | 0.68 | 0.72 | 0.67 | 0.78 | 0.69 |
| r2 | 0.82 | 0.68 | 0.77 | 0.68 | 0.79 | 0.77 | 0.79 | 0.71 | 0.80 | 0.78 |
| r3 | 0.77 | 0.75 | 0.78 | 0.76 | 0.72 | 0.80 | 0.77 | 0.72 | 0.74 | 0.80 |
| r4 | 0.67 | 0.73 | 0.76 | 0.71 | 0.71 | 0.74 | 0.68 | 0.73 | 0.72 | 0.79 |
| r5 | 0.77 | 0.74 | 0.83 | 0.78 | 0.73 | 0.60 | 0.74 | 0.76 | 0.65 | 0.73 |
| r6 | 0.71 | 0.68 | 0.78 | 0.82 | 0.79 | 0.77 | 0.75 | 0.80 | 0.67 | 0.77 |
| r7 | 0.79 | 0.68 | 0.78 | 0.70 | 0.78 | 0.79 | 0.78 | 0.78 | 0.83 | 0.75 |
| r8 | 0.73 | 0.70 | 0.73 | 0.78 | 0.72 | 0.75 | 0.79 | 0.80 | 0.78 | 0.66 |

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
| r1 | 0.83 | 0.79 | 0.89 | 0.91 | 0.74 | 0.87 | 0.64 | 0.85 | 0.64 | 0.76 |
| r2 | 0.78 | 0.77 | 0.82 | 0.90 | 0.88 | 0.79 | 0.87 | 0.77 | 0.73 | 0.74 |
| r3 | 0.67 | 0.84 | 0.79 | 0.70 | 0.78 | 0.59 | 0.64 | 0.80 | 0.75 | 0.81 |
| r4 | 0.90 | 0.72 | 0.90 | 0.69 | 0.60 | 0.74 | 0.74 | 0.83 | 0.84 | 0.66 |
| r5 | 0.72 | 0.79 | 0.75 | 0.70 | 0.85 | 0.87 | 0.69 | 0.83 | 0.74 | 0.68 |
| r6 | 0.90 | 0.72 | 0.77 | 0.91 | 0.78 | 0.80 | 0.71 | 0.88 | 0.69 | 0.88 |
| r7 | 0.77 | 0.84 | 0.87 | 0.82 | 0.80 | 0.85 | 0.70 | 0.58 | 0.72 | 0.83 |
| r8 | 0.89 | 0.93 | 0.80 | 0.83 | 0.90 | 0.84 | 0.85 | 0.83 | 0.82 | 0.89 |

**Long** (10 × 8)

| | c1 | c2 | c3 | c4 | c5 | c6 | c7 | c8 | c9 | c10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| r1 | 0.64 | 0.73 | 0.65 | 0.53 | 0.62 | 0.68 | 0.58 | 0.64 | 0.50 | 0.66 |
| r2 | 0.61 | 0.65 | 0.64 | 0.71 | 0.80 | 0.57 | 0.47 | 0.65 | 0.60 | 0.69 |
| r3 | 0.57 | 0.62 | 0.59 | 0.54 | 0.66 | 0.56 | 0.66 | 0.53 | 0.60 | 0.49 |
| r4 | 0.76 | 0.62 | 0.69 | 0.53 | 0.54 | 0.57 | 0.61 | 0.70 | 0.67 | 0.56 |
| r5 | 0.70 | 0.60 | 0.79 | 0.47 | 0.41 | 0.59 | 0.63 | 0.57 | 0.60 | 0.41 |
| r6 | 0.75 | 0.75 | 0.70 | 0.65 | 0.52 | 0.61 | 0.63 | 0.68 | 0.70 | 0.69 |
| r7 | 0.71 | 0.74 | 0.77 | 0.62 | 0.77 | 0.44 | 0.54 | 0.48 | 0.66 | 0.60 |
| r8 | 0.69 | 0.58 | 0.74 | 0.67 | 0.81 | 0.71 | 0.72 | 0.72 | 0.74 | 0.61 |

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
| r1 | 0.75 | 0.56 | 0.63 | 0.77 | 0.73 | 0.72 | 0.68 | 0.78 | 0.73 | 0.68 |
| r2 | 0.80 | 0.56 | 0.83 | 0.86 | 0.83 | 0.67 | 0.72 | 0.81 | 0.77 | 0.73 |
| r3 | 0.66 | 0.66 | 0.83 | 0.89 | 0.83 | 0.84 | 0.72 | 0.74 | 0.84 | 0.64 |
| r4 | 0.70 | 0.65 | 0.82 | 0.79 | 0.83 | 0.78 | 0.74 | 0.66 | 0.63 | 0.75 |
| r5 | 0.83 | 0.80 | 0.83 | 0.83 | 0.72 | 0.59 | 0.71 | 0.63 | 0.77 | 0.86 |
| r6 | 0.73 | 0.55 | 0.70 | 0.81 | 0.92 | 0.87 | 0.87 | 0.79 | 0.59 | 0.77 |
| r7 | 0.72 | 0.87 | 0.67 | 0.67 | 0.79 | 0.61 | 0.57 | 0.57 | 0.79 | 0.81 |
| r8 | 0.81 | 0.72 | 0.72 | 0.75 | 0.81 | 0.78 | 0.71 | 0.84 | 0.64 | 0.70 |

**Long** (10 × 8)

| | c1 | c2 | c3 | c4 | c5 | c6 | c7 | c8 | c9 | c10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| r1 | 0.68 | 0.53 | 0.41 | 0.62 | 0.74 | 0.74 | 0.46 | 0.77 | 0.55 | 0.58 |
| r2 | 0.68 | 0.55 | 0.72 | 0.69 | 0.78 | 0.67 | 0.61 | 0.71 | 0.69 | 0.55 |
| r3 | 0.72 | 0.66 | 0.78 | 0.78 | 0.72 | 0.71 | 0.63 | 0.73 | 0.67 | 0.55 |
| r4 | 0.45 | 0.39 | 0.77 | 0.75 | 0.76 | 0.72 | 0.63 | 0.66 | 0.64 | 0.52 |
| r5 | 0.60 | 0.57 | 0.67 | 0.65 | 0.66 | 0.52 | 0.58 | 0.60 | 0.55 | 0.52 |
| r6 | 0.68 | 0.58 | 0.43 | 0.80 | 0.70 | 0.75 | 0.61 | 0.70 | 0.48 | 0.66 |
| r7 | 0.68 | 0.55 | 0.62 | 0.73 | 0.82 | 0.61 | 0.64 | 0.69 | 0.63 | 0.65 |
| r8 | 0.75 | 0.55 | 0.75 | 0.75 | 0.67 | 0.62 | 0.67 | 0.67 | 0.65 | 0.65 |

## A sample of the raw embedding

These are the first 12 of the 512 numbers for the top-left tile of each photo, untouched and
marked, all on the 10 × 8 grid. Classic uses a coarser grid, so its top-left tile covers a
different area and is listed separately.

### Coffee beans

| Series | d0 | d1 | d2 | d3 | d4 | d5 | d6 | d7 | d8 | d9 | d10 | d11 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Untouched (10 × 8 tile) | 0.0993 | 0.0592 | 0.0117 | 0.0019 | 0.0286 | 0.0000 | 0.0000 | 0.0259 | 0.0162 | 0.0007 | 0.0003 | 0.0006 |
| Subtle | 0.1229 | 0.0333 | 0.0063 | 0.0036 | 0.0527 | 0.0054 | 0.0124 | 0.0155 | 0.0288 | 0.0023 | 0.0020 | 0.0077 |
| Long | 0.1045 | 0.0263 | 0.0185 | 0.0069 | 0.0319 | 0.0149 | 0.0000 | 0.0531 | 0.0082 | 0.0267 | 0.0014 | 0.0091 |
| Untouched (6 × 5 tile) | 0.1269 | 0.0889 | 0.0172 | 0.0211 | 0.0293 | 0.0047 | 0.0014 | 0.0365 | 0.0022 | 0.0064 | 0.0000 | 0.0012 |
| Classic | 0.0748 | 0.0199 | 0.0000 | 0.0092 | 0.0130 | 0.0017 | 0.0010 | 0.0834 | 0.0031 | 0.0099 | 0.0014 | 0.0284 |

### Milky Way

| Series | d0 | d1 | d2 | d3 | d4 | d5 | d6 | d7 | d8 | d9 | d10 | d11 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Untouched (10 × 8 tile) | 0.0223 | 0.0000 | 0.0000 | 0.0000 | 0.0044 | 0.0000 | 0.0781 | 0.0087 | 0.0000 | 0.0100 | 0.1010 | 0.0000 |
| Subtle | 0.0092 | 0.0000 | 0.0000 | 0.0000 | 0.0012 | 0.0000 | 0.1279 | 0.0092 | 0.0004 | 0.0060 | 0.0840 | 0.0000 |
| Long | 0.0139 | 0.0473 | 0.0060 | 0.0068 | 0.0216 | 0.0000 | 0.1585 | 0.0605 | 0.0044 | 0.0821 | 0.0566 | 0.0000 |
| Untouched (6 × 5 tile) | 0.0052 | 0.0000 | 0.0008 | 0.0000 | 0.0008 | 0.0000 | 0.0414 | 0.0016 | 0.0000 | 0.0164 | 0.0558 | 0.0014 |
| Classic | 0.0184 | 0.0427 | 0.0103 | 0.0000 | 0.0191 | 0.0000 | 0.0044 | 0.1154 | 0.0000 | 0.0364 | 0.0241 | 0.0001 |

### Antonello portrait

| Series | d0 | d1 | d2 | d3 | d4 | d5 | d6 | d7 | d8 | d9 | d10 | d11 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Untouched (10 × 8 tile) | 0.0079 | 0.0000 | 0.0100 | 0.0000 | 0.0040 | 0.0000 | 0.0919 | 0.0411 | 0.0000 | 0.0908 | 0.0466 | 0.0012 |
| Subtle | 0.0108 | 0.0000 | 0.0047 | 0.0096 | 0.0357 | 0.0000 | 0.2485 | 0.0629 | 0.0029 | 0.0432 | 0.0901 | 0.0005 |
| Long | 0.0067 | 0.0024 | 0.0081 | 0.0051 | 0.0261 | 0.0089 | 0.2999 | 0.0642 | 0.0038 | 0.0542 | 0.0712 | 0.0000 |
| Untouched (6 × 5 tile) | 0.0003 | 0.0029 | 0.0005 | 0.0001 | 0.0025 | 0.0000 | 0.0103 | 0.0180 | 0.0000 | 0.0880 | 0.0215 | 0.0029 |
| Classic | 0.0101 | 0.0259 | 0.0273 | 0.0038 | 0.0046 | 0.0001 | 0.0144 | 0.0691 | 0.0000 | 0.0522 | 0.0516 | 0.0000 |

Many of the 512 values are exactly zero. In the untouched photos it is 15 % for the coffee
beans, 39 % for the portrait and 52 % for the Milky Way. The network clips negative values to
zero, and a dark sky leaves many features unused.

## Full data

`demo-photos/fixtures/embeddings/<photo>.json` holds everything, for each mode:

| Key | Contents | Shape |
|---|---|---|
| `embeddings_original`, `embeddings_marked` | every tile's embedding, before and after | tiles × 512 |
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
  It is a lossy view of 512 dimensions; say so in the caption.

Keep one caveat in the caption: these numbers come from one model build on one CPU. Other
hardware has not been tested.
