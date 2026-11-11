# Master prompt for Claude Design: move Ghostframe v3 to the MobileNetV3 engine

Paste everything below the line into the Claude Design project that holds
`Ghostframe v3.dc.html`. Do it after the fixtures in this folder are on GitHub `main`, so the
project's GitHub sync can pull them.

---

## Context

Ghostframe v3 (`Ghostframe v3.dc.html`) was designed around the first engine, which read every
mode with **SqueezeNet 1.1**. Since then a preregistered benchmark has replaced the model behind
two of the three modes:

| Mode | Before | Now |
|---|---|---|
| Classic | `legacy-v1`, SqueezeNet 1.1, 13 B | **unchanged** (`legacy-v1`, SqueezeNet 1.1, 13 B) |
| Subtle | `sw-l2-c10x8b16p48`, SqueezeNet, 79 B | `bb-mobilenet_v3_small-l2-b16p48`, **MobileNetV3-Small**, 79 B |
| Long | `sw-l8-c10x8b40p64`, SqueezeNet, **302 B** | `bb-mobilenet_v3_small-l8-b64p112`, **MobileNetV3-Small**, **494 B** |

Why the change: MobileNetV3-Small (2019) passed the same held-out test as SqueezeNet, 123 of 123
trials for each mode. It carries **494 B instead of 302 B** in Long, and **encodes about 1.6×
faster** in both modes.

Update the whole design to the new engine: every example, number, chart, data table and line of
copy. Keep the layout, interactions, visual language, tone and the Classic mode exactly as they
are. This is a data and copy update, not a redesign.

## Source of truth

Repository `MyElectricSheep/ghostframe`, branch `main`.

| What | Where |
|---|---|
| Every number below, in the shapes the page script already uses | `design-handoff/mobilenet-v3/design-data.json` |
| The 9 verified example images, now made with the new profiles | `demo-photos/fixtures/<photo>/` (re-import the folder) |
| Per-tile embedding data for the "What the model sees" view | `demo-photos/fixtures/EMBEDDINGS.md` and `demo-photos/fixtures/embeddings/*.json` |
| Benchmark write-up | `docs/BENCHMARK.md`, section "Backbone comparison: MobileNetV3-Small" |

**Pending values.** A few values, written ⟨LIKE_THIS⟩ below, come from runs that were still in
progress when this prompt was written: the 640-px small-photo check and the detector. Fill them
from `small640` and `detect` in `design-data.json` if those keys are filled. Otherwise leave the
old sentence in place, add a visible `TODO(data)`, and say so.

Use the numbers in `design-data.json` as they are. Do not round them differently, re-derive them
or invent any. If something you need is missing, leave a visible `TODO(data)` and say so.

## 1. Re-import the fixtures

Re-sync `demo-photos/` from GitHub. The file names have not changed, but the content of these
has:
- `demo-photos/fixtures/<photo>/subtle.png` and `subtle-difference.png`
- `demo-photos/fixtures/<photo>/long.png` and `long-difference.png`
- `demo-photos/fixtures/<photo>/fixtures.json`
- `demo-photos/fixtures/EMBEDDINGS.md`

`classic.png`, `classic-difference.png` and `original.png` are unchanged. The passphrase is
still `ghostframe public benchmark fixture`.

## 2. Replace the page script's data constants

Each constant in the `<script data-dc-script>` block maps to a key of `design-data.json`:

| Constant in the page | Replace with |
|---|---|
| `MODES` (and `PROF`, `AMP`, `TIPS`) | `modes`. Profile names, `bytes`, `cap`, `amp`, `grid`, `ev`, `psnr`, `ssim`, `status` |
| `FIX` | `fix`. `[message, bytes, changed_fraction]` per photo and mode. Long messages are now 480–493 bytes |
| `PHOTOS[*].res` and `RES` | build the strings from `res` (see below) |
| `SUM` | `sum`. `[tiles, hidden bits, cos median, cos lowest, shift median, bits flipped]` |
| `HEAT` | `heat`. Long is still 10 × 8, but its values are new |
| `RAW` | `raw`. `u10`, `subtle` and `long` are MobileNetV3 numbers; `u6` and `classic` are unchanged SqueezeNet numbers |
| `hardRows` (stress) | `stress`. Subtle 4/9, Long 6/9 |

**The "Recorded result" strings per photo**, built from `res`, in the existing format:

| Photo | Subtle | Long |
|---|---|---|
| Portrait | `3 / 3 read back · 0 wrong bytes · SSIM ≥ 0.976 · encode ≤ 20 s` | `3 / 3 read back · 0 wrong bytes · SSIM ≥ 0.863 · encode ≤ 31 s` |
| Coffee beans | `3 / 3 read back · 0 wrong bytes · SSIM ≥ 0.983 · encode ≤ 18 s` | `3 / 3 read back · 0 wrong bytes · SSIM ≥ 0.899 · encode ≤ 27 s` |
| Milky Way | `3 / 3 read back · 0 wrong bytes · SSIM ≥ 0.989 · encode ≤ 20 s` | `3 / 3 read back · 0 wrong bytes · SSIM ≥ 0.924 · encode ≤ 32 s` |

Classic stays `1 / 1 read back`. The Milky Way Subtle line used to say "≤ 4 wrong bytes of 24
correctable". It now has 0 wrong bytes, so drop that clause.

**Modes table** (the "Limits and evidence → Measured" section, from `modes`):

| Mode | Profile · status | Max message | Max change | Read back | PSNR · SSIM |
|---|---|---:|---:|---|---|
| Classic | `legacy-v1` · verified | 13 B | 8 / 255 | 41 / 41 held-out photos | 36.5 dB · 0.924 |
| Subtle | `bb-mobilenet_v3_small-l2-b16p48` · experimental | 79 B | 2 / 255 | 123 / 123 held-out trials | 43.0 dB · 0.979 |
| Long | `bb-mobilenet_v3_small-l8-b64p112` · experimental | **494 B** | 8 / 255 | 123 / 123 held-out trials | 34.1 dB · 0.872 |

## 3. Copy changes, section by section

Exact before → after. Anything not listed stays word for word.

### Hero
No change. "An AI image model" is still true for both models.

### Try it (ready-made examples)
- Mode tooltip for Long (`TIPS.long`): "up to 302 bytes" → **"up to 494 bytes"**. Tip text:
  "Holds a short paragraph." → **"Holds a long paragraph, about 80 words."** Keep the rest.
- Mode chip for Long: `302 B · ≤8` → **`494 B · ≤8`**.
- "About this file → profile" shows the new profile names. They are long, so let them wrap or
  truncate in the middle with the full name in a tooltip. Do not shorten the names: they are
  part of the cryptographic identity.
- The Long message panel now holds about 490 bytes, roughly 1.6× the old text. Check that the
  "Hidden in this photo" card fits it on desktop and on phones (clamp it with a "Show all" if
  needed).
- Quality line under the stage (`tQuality`): "(median, 41 photos)" stays, and the values come
  from `modes`.

### What the model sees (embedding view)
- "The model describes each tile with **512 numbers**, its embedding." →
  **"The model describes each tile with a list of numbers, its embedding: 576 for Subtle and
  Long, 512 for Classic."** Better still, make the number follow the selected mode (`dim` in
  `modes`).
- Add one small model label to this view, next to the mode, e.g. **"read by MobileNetV3-Small"**
  or **"read by SqueezeNet 1.1"** (Classic). The two models describe tiles differently, so their
  angles are not directly comparable.
- **Retune the colour scale.** MobileNetV3 tiles turn further than SqueezeNet's did:
  - Long median cosine is 0.53–0.63, against 0.64–0.75 before.
  - The lowest tile is 0.17, about 80°. The old `eTint` / `wTint` scale saturates below cosine
    0.38.

  Change both to cover cosine 0.95 → 0.15:
  `t = clamp((0.95 - cos) / 0.80, 0, 1)`. Keep the same blue and alpha range. Check the legend
  ("barely turned → turned most") still matches.
- The dot strip "Every tile's turn" keeps its 0°–90° axis. All values fit, the largest being
  about 80°.

### How it works
- "A frozen, public image model, **SqueezeNet 1.1**, looks at the photo one tile at a time." →
  **"A frozen, public image model, MobileNetV3-Small, looks at the photo one tile at a time.
  (Classic mode uses the older SqueezeNet 1.1.)"**
- Animation step 03 detail ("10 × 8 tiles for Subtle and Long, 6 × 5 for Classic.") is
  unchanged.
- The illustration caption ("the numbers inside the model are simplified") is unchanged.

### Technical detail (collapsed block)
Replace the Model line with:

> **Models:** MobileNetV3-Small for Subtle and Long
> ([Howard et al., *Searching for MobileNetV3*, ICCV 2019](https://arxiv.org/abs/1905.02244)),
> torchvision checkpoint (sha256 `047dcff4…`), and SqueezeNet 1.1 for Classic
> ([original paper](https://arxiv.org/abs/1602.07360)), checkpoint (sha256 `b8a52dc0…`). Each
> has its own pinned calibration file. PyTorch 2.7.1 CPU, torchvision 0.22.1.

Encryption, tamper evidence, related work and "Encoding and decoding run on a server" are
unchanged.

### Use your own photo (Hide)
- Mode card for Long: "up to 302 bytes" → **"up to 494 bytes"**. Blurb: "A short paragraph.
  More visible change." → **"A long paragraph. More visible change."**
- Byte-counter help (`bc.help`): "Long fits up to 302 bytes." → **"Long fits up to 494
  bytes."** The condition `n <= 302` becomes `n <= 494`.
- Waiting copy. Encodes are faster now: on the 4-vCPU test server, the median is 19 s for Subtle
  and 33 s for Long on 1280-px photos, and 23–44 s per fixture including model start-up. The
  demo host may be smaller, so keep some margin:
  - "This usually takes 1–3 minutes. You can keep this tab open." → **"This usually takes under
    2 minutes. You can keep this tab open."**
  - Encode button helper "Usually 1–3 minutes." → **"Usually under 2 minutes."**
  - The 5-minute stop, the cancel button and the "taking longer" state are unchanged.
  - Prototype note "This prototype runs about 15× faster than real time." stays, and `SPEED` is
    unchanged.
- "Done" panel: "mode · profile" shows the new profile name (same wrapping rule as above).

### Read a message
- Mode select options: `Subtle · sw-l2-c10x8b16p48` → **`Subtle · bb-mobilenet_v3_small-l2-b16p48`**,
  and `Long · sw-l8-c10x8b40p64` → **`Long · bb-mobilenet_v3_small-l8-b64p112`**.
- "Try all modes (about 6–12 s)" is unchanged, since decoding is still about 2 s per mode.

### Limits and evidence
- "Short messages only." note: `13, 79 or 302 bytes` → **`13, 79 or 494 bytes`**.
- "Not every photo works." note: `hard images: Subtle 3/9, Long 6/9 · 640 px photos: Subtle
  40/41, Long 41/41` → **`hard images: Subtle 4/9, Long 6/9 · 640 px photos: Subtle
  ⟨SMALL640_SUBTLE⟩, Long ⟨SMALL640_LONG⟩`** (from `small640` in `design-data.json`).
- The hard-image dot rows (`hardRows`): Subtle **4** of 9 (was 3), Long 6 of 9.
- The paragraph under "Flat, synthetic or tiny images": "At 640 px wide, ordinary photos did
  well: Subtle 40/41 (one refusal, a neon sign at night), Long 41/41." →
  **⟨SMALL640_SENTENCE⟩**
- "Not invisible to software." note: "a detection test separated marked from clean photos 100%
  of the time" → **⟨DETECT_NOTE⟩** (from `detect`).
- "Subtle and Long are experimental." note: `123 of 123 held-out trials each` is unchanged.
- "How long it takes → encode": "usually a few minutes; stopped after 5 min" → **"usually under 2
  minutes; stopped after 5 min"**.

### Footer and credits
No change.

## 4. Optional, if it fits the page: one line on why the model changed

In "Limits and evidence", under the modes table, a single muted line:

> Subtle and Long moved from SqueezeNet 1.1 to MobileNetV3-Small after a preregistered
> comparison of five image models. Same held-out reliability, 494 B instead of 302 B in Long,
> and about 1.6× faster encodes.

## 5. Checks before you hand it back

1. Search the file: no remaining `302`, `sw-l2-c10x8b16p48`, `sw-l8-c10x8b40p64` or `512 numbers`
   (except the Classic-specific 512). "SqueezeNet" appears only next to Classic or in the
   technical detail.
2. For each of the 3 photos × 3 modes, the recorded message shown equals `fix` and the image
   drawn is the re-imported PNG.
3. The heat-map and dot views show the new Long values, the darkest tile is visibly darkest, and
   nothing is clipped at either end of the colour scale.
4. The Long message card fits the 493-byte portrait text at 375 px wide.
5. Update `github.md` with a sync entry: "Moved Subtle/Long to MobileNetV3 profiles; fixtures and
   data from design-handoff/mobilenet-v3".
