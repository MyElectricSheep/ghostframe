# Handoff: Ghostframe demo site

## Overview
Ghostframe is a one-page site for an engineering experiment by Ben Paget (electricsheep.id). It hides a short encrypted message in a photo by nudging pixels until a frozen, public image model (MobileNetV3-Small, or SqueezeNet 1.1 for Short mode) reads the message back from its tile embeddings. The page lets a visitor:

1. look at three ready-made examples (no upload) and compare original vs encoded, see the amplified difference, and see how each tile's embedding turned;
2. reveal the message hidden in the example;
3. watch a five-step animated explanation;
4. hide a message in their own photo, or read one from a PNG they were sent;
5. read the limits and measured evidence.

## About the design files
`Ghostframe v3.dc.html` is a **design reference built in HTML**, a working prototype of the intended look and behaviour. It is not production code. Recreate it in the real stack of the Ghostframe repo (or, if the site has no frontend yet, the framework that best fits a static page plus a small encode/decode API). Open the file in a browser from this folder to try it; it needs `support.js` and `demo-photos/` next to it.

The prototype keeps all styles inline and all logic in one class (`class Component` in the `<script data-dc-script>` block). Read it for exact values; don't port its structure.

## Fidelity
**High fidelity.** Colours, type, spacing, copy and interactions are final. Copy is approved word for word. Recreate pixel for pixel.

## Naming: the page differs from the repo on purpose
- The first mode is labelled **Short** in the UI. The repo, `design-data.json` and the prototype's internal key still say `classic`. Keep the key `classic` in code and data; show "Short" to people.
- **No mode shows a status label** ("verified"/"experimental"), even though `design-data.json` still has `status` fields. This is deliberate.
- Profile names are part of the cryptographic identity. Never shorten or rename them. Show them after the model name: **model in ink, profile in grey** (`#625c57`), e.g. `MobileNetV3-Small · bb-mobilenet_v3_small-l2-b16p48`. Let them wrap (`overflow-wrap:anywhere`).

| Key | UI label | Model | Profile | Max message | Max change | Grid | Amp. |
|---|---|---|---|---|---|---|---|
| `classic` | Short | SqueezeNet 1.1 (512 numbers per tile) | `legacy-v1` | 13 B | 8/255 | 6 × 5 | ×24 |
| `subtle` | Subtle (default) | MobileNetV3-Small (576) | `bb-mobilenet_v3_small-l2-b16p48` | 79 B | 2/255 | 10 × 8 | ×96 |
| `long` | Long | MobileNetV3-Small (576) | `bb-mobilenet_v3_small-l8-b64p112` | 494 B | 8/255 | 10 × 8 | ×24 |

**Subtle is the default mode** everywhere a mode is preselected (Try it, Hide). The Read tab defaults to "Try all modes".

## What is real, recorded or simulated in the prototype
| Thing | Status in prototype | Production |
|---|---|---|
| Example images (`demo-photos/fixtures/*`) | **Real**, verified fixtures | Serve these exact files |
| Example messages, result lines, per-tile heat map, raw numbers | **Recorded**, from `design-data.json` / `fixtures.json` | Read from those files at build time |
| "Reveal the hidden message" | **Recorded**: plays a reveal of the recorded message; no decode runs | Either keep it recorded (honest, fast) or call decode on the fixture. Say which in the UI only if it becomes live |
| Hide (encode your own photo) | **Simulated**: queue, progress, refusal, timeout and result are faked; the result image is a synthetic noise pattern; "Download PNG" produces nothing ("Simulated: no file was produced.") | Wire to the real encoder API |
| Read (decode a PNG) | **Simulated**, except the bundled sample PNG + fixture passphrase, which returns the recorded message | Wire to the real decoder API |
| Timing (`SPEED` constant, "This prototype runs about 15× faster than real time.") | Prototype only | **Remove** the 15× note and `SPEED`; use real job state |
| Dev query params (`?hjob=`, `?hfile=`, `?herr=`, `?rstate=`, `?tab=` …) and the scenario pickers | Prototype only, for reviewing states | Remove |

### Server behaviour the copy promises (confirm before launch)
- One encode at a time, with a visible queue position, and a daily cap ("site limit" state).
- An encode is stopped after 5 minutes. Usually under 2 minutes (median 19 s Subtle / 33 s Long on a 4-vCPU test server).
- Decode takes a few seconds per mode; "Try all modes (about 6–12 s)".
- "No accounts, nothing stored." Uploads and results must not be retained.
- Encoding and decoding run on a server (stated in Technical detail).
- Input rules: PNG or JPEG in for Hide; **PNG only** for Read; max 4 MP; min 160 × 128; no transparency; no 16-bit/HDR; no CMYK/Lab; Display P3 is converted to sRGB (shown as a note).
- Output is always PNG.

### Serving the images (critical)
The fixture PNGs must be served **byte for byte unmodified**. No compression, resizing, WebP/AVIF conversion, CDN image optimisation or metadata stripping, or the hidden messages are destroyed. Use separate resized copies for any thumbnails (the `demo-photos/*.jpg` files are display/hero copies). Downloads from Hide must also be the exact PNG the encoder produced.

## Page structure (top to bottom)
Max content width 1240px, side padding `clamp(16px,4vw,40px)`. Sections are separated by a thin grey rule; "Can you spot the difference?" and "Hidden in this photo" are one section, with no rule between them.

1. **Header**: ghost logo (pixel ghost, 24px, in a framed square) + "Ghostframe". Hovering the logo inverts it (white-on-black ↔ black-on-white) with a slow transition and keeps the frame. Favicon is the same mark.
2. **Hero** (`#top`): h1 "A secret message, hidden in plain pixels." with intro copy on the left; on the right a 10 s looping canvas animation of a ghost passing over the photo (`drawHero`). Pauses off-screen; static frame under reduced motion.
3. **Entry links**: "Hide a message" / "Read a message" buttons that jump to the tool (`#tool`) on the right tab.
4. **Try it** (`#try`): "Try it · no upload needed", h2 "Can you spot the difference?" Layout: a **left control column** (photo picker: Portrait, Coffee beans, Milky Way; mode: Short / Subtle / Long, each with an info tooltip; view: Original vs encoded / Amplified difference / What the model sees), and a **large image stage** on the right.
   - *Original vs encoded*: one image with a draggable divider (original left, encoded right). The divider is also a keyboard slider (arrow keys, focus ring `2px solid #3f648c`). No separate A/B toggle.
   - *Amplified difference*: the difference PNG with the tag "Amplified difference ×{amp}"; it must never look like the real photo.
   - *What the model sees*: divider stays; the marked side gets a blue tint per tile (tint `t = clamp((0.95 − cos)/0.80, 0, 1)`). Every tile is clickable/focusable. Below the image: the legend "barely turned → turned most" at image width; the "tile that turned most" box (angle dial plus figures); a "What the angle means" chevron disclosure; and "Every tile's turn", a 0°–90° dot strip where each dot is a tile ("Each dot is one tile. Click a dot to pick it."). The view text names the model and the per-tile number count for the current mode.
   - Under the stage: profile line, quality figures (PSNR · SSIM, with acronym tooltips), and an "About this file" pop-up.
5. **Hidden in this photo** (`#reveal`): a "Reveal the hidden message" button; the message appears with an animation in which embedding-like digits resolve into the text (`rvRun`); the button changes to "Hide the message". On phones, Long messages are clamped to ~13em with "Show all / Show less".
6. **How it works** (`#how`): five steps, 01–05, each with its own 7–9 s canvas animation (`HOW_DUR`, `HOW_LABELS`, `drawHow`). Clicking a step plays it; a replay button sits at the top right of the animation. Autoplays once when scrolled into view. Links to MobileNetV3 (arXiv 1905.02244) and SqueezeNet 1.1. A collapsed "Technical detail" block covers the models with checkpoint hashes, encryption, tamper evidence, related work and links, and the server note.
7. **Use your own photo** (`#tool`): tabs **Hide** / **Read**.
   - Hide: drop zone → mode cards → message with a **UTF-8 byte counter** (bytes, not characters; warns at 85%, blocks above the limit; suggests Long when it fits) → passphrase plus repeat (show/hide, strength hint, mismatch) → Encode. The Encode button lists what is missing. Job states: queued (position), starting the engine (cold start), encoding with progress, taking longer, done (side-by-side or difference view, mode · model · profile, Download PNG), refused, timed out, site limit, visitor limit.
   - Read: drop zone (PNG only; a JPEG gets the `jpegRead` explanation) → passphrase → mode (Try all modes / a single mode) → Read. Results: message (with copy button), or "No message found" (wrong passphrase, unmarked image and wrong mode look identical by design: never say which).
   - Exact error copy is in the `ISSUE` constant and the `STOP` object in `renderVals`.
8. **Limits and evidence** (`#limits`): limit items with short notes, the hard-image dot rows (Subtle 4/9, Long 6/9), a "How long it takes" box, and the modes table (Mode · model/profile · max message · max change · read back · PSNR · SSIM). One muted line under the table explains the model change. Link list with placeholders: `[REPOSITORY_URL]`, `docs/BENCHMARK.md`, `docs/AUDIT_REPORT.md` ("Method notes"). Fill in the real URLs.
9. **Footer**: "Ghostframe is an engineering experiment by Ben Paget" (link to https://electricsheep.id). On its own line: "No accounts, nothing stored. Don't use it to hide illegal content." Then photo credits. Credits appear only here, not under the images.

## Interactions and accessibility
- Every control is a real `<button>`, `<input>` or `<select>` with visible focus. Segmented groups use `aria-pressed`.
- The divider: pointer drag on the stage, plus a keyboard range input (0–100).
- Embedding tiles and dots are buttons with labels like "Tile row 3, column 5, 41 degrees". Keyboard: Tab to the tiles, arrows to move (the hint is on its own line under the image).
- Tooltips (mode info, acronyms PSNR/SSIM/AES-256-GCM/scrypt): open on click or tap, close on outside click or Esc, width 260px, placed above or below to fit. Acronyms have a subtle dashed underline. Common terms (CPU, sha256) have none.
- Status regions (`role="status"`, `aria-live="polite"`) for reveal, encode and read results.
- `prefers-reduced-motion`: the hero and How animations show a static frame, the reveal is instant, and transitions are ~0.
- Status never relies on colour alone: each has a glyph and text (✓ / !).
- Hit targets are at least 44px on touch.

## Responsive
- ≥ 960px: the Try it control column sits left of the stage; How it works has steps beside the animation.
- < 760px (`narrow`): the controls stack above the stage; the stage is full width (don't shrink photos); the Long reveal is clamped with Show all; tables scroll horizontally inside their card.
- The Portrait is tall (1280 × 1782). The stage caps its width (~420px desktop) so it doesn't overflow the viewport.

## Data
- `data/design-data.json`: the source of truth for `modes`, `fix` ([message, bytes, changed_fraction] per photo × mode), `res` (result strings), `sum` (tile summary), `heat` (per-tile cosine grids), `raw` (sample embedding numbers), `stress`, `small640` and `detect`.
- `demo-photos/fixtures/<photo>/`: `original.png`, `{classic,subtle,long}.png`, `*-difference.png`, `fixtures.json` (exact messages, hashes, checks). Passphrase for all fixtures: `ghostframe public benchmark fixture`.
- `demo-photos/fixtures/EMBEDDINGS.md`: how the per-tile data was produced.

## Design tokens
Use the project's design system. The values used:
- Ink `rgba(18,16,14,0.96)` (near `#12100e`), secondary text `#625c57`, muted `#8a837c`, faint `#a39b93`.
- Surfaces: page white, panel `#f6f4f1`, `#f1eee9`, rules `#d9d3cc` / `#e0dad3` / `rgba(24,20,17,0.12)`, dark `#312e2b`.
- Accent (signal and active): blue `#3f648c`, hover `#355574`, tint `#eaf1f7` / `#f5f8fb`, light `#8fb3d9`.
- Error: `#9f3b3b`, background `#fff8f8` / `#fbecec`.
- Type: Inter (UI and text; h1 bold, h2 `clamp(28px,3.4vw,40px)` 700), IBM Plex Mono for measurements, profiles and technical labels only.
- Radii: 2, 3, 4, 6 (cards and stage), 8, 10, 999px (pills).

## Files
- `Ghostframe v3.dc.html`: the full prototype (open in a browser).
- `support.js`: the runtime the prototype needs to open. Not for production.
- `demo-photos/`: verified fixtures plus display JPEGs.
- `data/design-data.json`: all numbers.
