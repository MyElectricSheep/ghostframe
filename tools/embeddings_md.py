"""Write demo-photos/fixtures/EMBEDDINGS.md from the tools.dump_embeddings export.

    python -m tools.dump_embeddings && python -m tools.embeddings_md
"""
import json
from pathlib import Path

import numpy as np

D=Path('demo-photos/fixtures/embeddings')
PH={'coffee-beans':'Coffee beans','milky-way':'Milky Way','antonello-portrait-of-a-man':'Antonello portrait'}
MO={'classic':'Classic','subtle':'Subtle','long':'Long'}
edges=np.round(np.arange(-0.08,0.0801,0.01),2)
def hist(s):
    s=np.clip(np.asarray(s).ravel(),-0.0799,0.0799); return np.histogram(s,bins=edges)[0].tolist()
recs={p:json.loads((D/f'{p}.json').read_text()) for p in PH}
cos_med = {m: [float(np.median(recs[p]['modes'][m]['tile_cosine'])) for p in PH] for m in MO}
cos_min = {m: min(min(recs[p]['modes'][m]['tile_cosine']) for p in PH) for m in MO}
gap = {m: min(float(np.abs(recs[p]['modes'][m]['scores_marked']).min()) for p in PH) for m in MO}
zero = {p: 100 * float((np.array(recs[p]['modes']['classic']['embeddings_original']) == 0).mean()) for p in PH}
neg = {p: 100 * float((np.array(recs[p]['modes']['subtle']['embeddings_original']) < 0).mean()) for p in PH}
rng = lambda m: f"{min(cos_med[m]):.2f}–{max(cos_med[m]):.2f}"
o=[]
o.append('''# Embedding data for the demo fixtures

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

''')
o.append(f'''## Three things worth showing

1. **The pixels barely change, but the embedding moves a lot.** The median cosine similarity
   between a tile's embedding before and after, where 1 means unchanged, is:
   - Classic: {rng('classic')}
   - Subtle: {rng('subtle')}
   - Long: {rng('long')}

   The lowest single tile is {min(cos_min.values()):.2f}. The network is very sensitive to tiny,
   targeted pixel changes, and that is exactly what the engine exploits.
2. **About half the bits flip.** The hidden data is encrypted, so it looks random, and roughly
   half the scores have to change sign. The rest only need to be pushed further from zero.
3. **A gap opens around zero.** In the untouched photo, scores form a smooth hump centred on
   zero. In every marked photo, nothing is left near zero:
   - Classic: every score is beyond ±{gap['classic']:.3f}.
   - Subtle and Long: every score is beyond ±{min(gap['subtle'], gap['long']):.3f}, the encoder's
     margin for MobileNetV3.

   That empty band is what makes the message readable, and it is also why the presence of a
   message is detectable.

   Histograms of before and after scores, showing this gap, make the clearest single graphic.

## Summary per photo and mode

"Shift" is the straight-line distance each tile's embedding moved, on a sphere where 2 is the
largest possible distance. Scores are given as absolute values.

| Photo | Mode | Tiles | Hidden bits | Cosine to original (median / lowest) | Shift (median) | Bits flipped | Median score size: original → marked | Smallest marked score |
|---|---|---:|---:|---|---:|---:|---|---:|''')
for p,name in PH.items():
    for m,mn in MO.items():
        d=recs[p]['modes'][m]; c=np.array(d['tile_cosine']); sh=np.array(d['tile_shift'])
        s0=np.abs(np.array(d['scores_original'])); s1=np.abs(np.array(d['scores_marked']))
        n=s1.size; f=sum(d['bits_flipped_per_tile'])
        o.append(f"| {name} | {mn} | {c.size} | {n} | {np.median(c):.3f} / {c.min():.3f} | {np.median(sh):.3f} | {f} ({100*f/n:.0f} %) | {np.median(s0):.4f} → {np.median(s1):.4f} | {s1.min():.4f} |")
o.append('''
## Score histograms (the "gap" graphic)

Each cell counts the scores that fall in one bin. Bins are 0.01 wide, from −0.08 to +0.08. Scores
beyond ±0.08 are counted in the end bins. Each row sums to that mode's total number of hidden bits.
''')
fmt=lambda v: "0.00" if abs(v)<1e-9 else f"{v:+.2f}"
lab=[f"{fmt(a)}…{fmt(b)}" for a,b in zip(edges[:-1],edges[1:])]
for p,name in PH.items():
    o.append(f"### {name}\n")
    o.append('| Series | '+' | '.join(lab)+' |'); o.append('|---|'+'---:|'*len(lab))
    for m,mn in MO.items():
        d=recs[p]['modes'][m]
        o.append(f"| {mn}: untouched | "+' | '.join(map(str,hist(d['scores_original'])))+' |')
        o.append(f"| {mn}: marked | "+' | '.join(map(str,hist(d['scores_marked'])))+' |')
    o.append('')
o.append('''The "untouched" rows differ between modes because each mode reads the photo through its own
grid and its own directions. For one picture per photo, show the Subtle or Long pair: they share
the 10 × 8 grid.

## Change per tile (heat-map data)

The cosine similarity between each tile's embedding before and after marking. Rows and columns
follow the photo's layout, top-left first. Lower numbers mean the tile moved more. Draw these as
a heat map over the photo.
''')
for p,name in PH.items():
    o.append(f"### {name}\n")
    for m,mn in MO.items():
        d=recs[p]['modes'][m]; c=np.array(d['tile_cosine']).reshape(d['rows'],d['cols'])
        o.append(f"**{mn}** ({d['cols']} × {d['rows']})\n")
        o.append('| |'+''.join(f" c{i+1} |" for i in range(d['cols']))); o.append('|---|'+'---:|'*d['cols'])
        for r,row in enumerate(c): o.append(f"| r{r+1} |"+''.join(f" {v:.2f} |" for v in row))
        o.append('')
o.append('''## A sample of the raw embedding

These are the first 12 numbers for the top-left tile of each photo, untouched and marked. Subtle
and Long share the 10 × 8 grid and MobileNetV3-Small (576 numbers per tile). Classic uses a
coarser 6 × 5 grid and SqueezeNet 1.1 (512 numbers), so its rows are listed separately and are
not comparable with the others.
''')
for p,name in PH.items():
    o.append(f"### {name}\n")
    o.append('| Series |'+''.join(f" d{i} |" for i in range(12))); o.append('|---|'+'---:|'*12)
    sub=recs[p]['modes']['subtle']
    o.append('| Untouched (10 × 8 tile) |'+''.join(f" {v:.4f} |" for v in sub['embeddings_original'][0][:12]))
    for m in ('subtle','long'):
        o.append(f"| {MO[m]} |"+''.join(f" {v:.4f} |" for v in recs[p]['modes'][m]['embeddings_marked'][0][:12]))
    cl=recs[p]['modes']['classic']
    o.append('| Untouched (6 × 5 tile) |'+''.join(f" {v:.4f} |" for v in cl['embeddings_original'][0][:12]))
    o.append('| Classic |'+''.join(f" {v:.4f} |" for v in cl['embeddings_marked'][0][:12]))
    o.append('')
o.append(f'''The two models' numbers look different:
- **SqueezeNet (Classic)** clips negative values to zero, so many values are exactly zero. In the
  untouched photos it is {zero['coffee-beans']:.0f} % for the coffee beans, {zero['antonello-portrait-of-a-man']:.0f} % for the portrait and {zero['milky-way']:.0f} % for
  the Milky Way, where a dark sky leaves many features unused.
- **MobileNetV3 (Subtle, Long)** ends in a smooth activation that allows small negative values.
  None of its values is exactly zero, and {neg['coffee-beans']:.0f} % (coffee beans), {neg['antonello-portrait-of-a-man']:.0f} % (portrait) and {neg['milky-way']:.0f} % (Milky Way) are negative.

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
''')
Path('demo-photos/fixtures/EMBEDDINGS.md').write_text('\n'.join(o))
