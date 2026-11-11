# Master prompt for Claude Code: build the Ghostframe demo site (MobileNetV3 engine)

Start Claude Code in the root of the `ghostframe` repository and paste everything below the
line.

---

You are building the public demo website for **Ghostframe**, an engineering experiment that
hides a short encrypted message in a photo's neural-network embeddings. The engine already
exists in this repository and is benchmarked. Your job is the website, the API and the engine
container around it, implemented faithfully from the design.

Read this whole prompt first, then the files it names, before writing code.

## 0. Ground rules

- **Do not change the engine's numerics.** Leave alone the profiles, carriers, margins, the
  calibration files and the checkpoints. The one allowed engine change is the progress callback
  in §4. `python -m unittest discover -s tests` must still pass, and the profile identities are
  pinned in `tests/test_png_profiles.py`.
- **Never invent a number.** Every figure shown on the site comes from
  `design-handoff/mobilenet-v3/design-data.json`, a fixture's `fixtures.json`, or a live engine
  result. Hard-code nothing that isn't there.
- **No browser-side decoding.** The model runs on the server only. Do not claim otherwise.
- **Ask Ben before** anything that costs money or is public:
  - deploying, creating Cloudflare resources, or buying or attaching a domain;
  - changing DNS or making the repository public.

  Build and test locally first.
- Commit on a feature branch, never on `main`. Commit as Ben
  `<17719054+MyElectricSheep@users.noreply.github.com>`. Open a PR when a milestone is green.
- This box is a 4-vCPU / 7.6 GB VPS that also runs other services. Run torch, Docker builds and
  browser tests in their own scope:
  `systemd-run --user --scope --quiet --slice=claude.slice -p MemoryMax=3G -- <command>`.
  Run one heavy job at a time.

## 1. What to read, in this order

| # | File | Why |
|---|---|---|
| 1 | `design-handoff/mobilenet-v3/README.md` | what this handoff contains |
| 2 | **The design.** The Claude Design project `79ad5e5b-69bd-47ae-8cc5-aaf613d5a201`, file `Ghostframe v3.dc.html` (with its `support.js`). Read it through the DesignSync / Claude Design tool (`list_files`, then `get_file`) | the source of truth for layout, copy and interactions |
| 3 | `design-handoff/mobilenet-v3/CLAUDE_DESIGN_PROMPT.md` | the MobileNetV3 changes that were requested of the design. If the live design still shows `302`, `sw-l8-…` or `SqueezeNet` for Subtle/Long, that update hasn't been applied: apply these changes yourself while implementing, and tell Ben |
| 4 | `design-handoff/mobilenet-v3/reference/Ghostframe v3.dc.html` | snapshot of the design **before** the MobileNetV3 update. Use it only if the live project can't be read |
| 5 | `design-handoff/mobilenet-v3/design-data.json` | every number the site shows (`modes`, `fix`, `res`, `sum`, `heat`, `raw`, `stress`, `small640`, `detect`) |
| 6 | `docs/DEMO_SITE_BRIEF.md` and `docs/DEMO_SITE_BRIEF_ADDENDUM.md` | product rules: input checks, waiting states, daily caps, Turnstile, retention, API shape, hosting shape |
| 7 | `demo-photos/README.md`, `demo-photos/fixtures/*/fixtures.json` | the 9 verified example images and their exact messages |
| 8 | `docs/PNG_PROFILES.md` and the "Backbone comparison" section of `docs/BENCHMARK.md` | engine contract and evidence |

The design is a Claude Design "dc" document: an `<x-dc>` template with `{{ }}` bindings, and a
page script whose class builds the view state. Treat it as a high-fidelity spec, not as code to
ship. Re-implement it as maintainable components. Match the copy character for character, the
layout, the states and the interactions:
- the before/after divider, with arrow-key support;
- the tile picker;
- the "How it works" animation steps;
- the tooltips and the abbreviation pop-overs.

## 2. Engine facts (MobileNetV3 era)

| Mode | Profile | Reader model | Max bytes | Pixel cap | Grid × bits per tile |
|---|---|---|---:|---:|---|
| Classic | `legacy-v1` | SqueezeNet 1.1 | 13 | 8 | 6 × 5 (legacy frame) |
| Subtle | `bb-mobilenet_v3_small-l2-b16p48` | MobileNetV3-Small | 79 | 2 | 10 × 8 × 16 |
| Long | `bb-mobilenet_v3_small-l8-b64p112` | MobileNetV3-Small | 494 | 8 | 10 × 8 × 64 |

- **Profile names are part of the cryptographic identity.** Use them exactly. A file decodes
  only under its own profile.
- **Two models are needed:** SqueezeNet 1.1 for Classic and MobileNetV3-Small for Subtle and
  Long.
  - SqueezeNet: `ghostframe.load_model("cpu")`.
  - MobileNetV3: `ghostframe_png.backbones.load("mobilenet_v3_small")`.
  - Pick the model with `ghostframe_png.PROFILES[name].backbone` (`"squeezenet1_1"` or
    `"mobilenet_v3_small"`); `ghostframe_png/cli.py` does the same.
  - Load both once per worker and keep them warm.
- **Checkpoints are SHA-256 pinned** and downloaded into torch's hub cache on first use:
  - `squeezenet1_1-b8a52dc0.pth`
  - `mobilenet_v3_small-047dcff4.pth`

  **Bake both into the container image at build time.** Run one encode and one decode per
  model during `docker build`, or copy the files into `$TORCH_HOME/hub/checkpoints/`. The
  container must never download weights at request time.
- The calibration means ship as package data, under `ghostframe_png/data/*.npy`.
- **Python API** (preferred over the CLI, because it avoids reloading models):
  - `encode_message(cover_rgb, message_bytes, passphrase_bytes, profile_name, model)` returns
    PNG bytes that were already reopened and authenticated.
  - `decode_message(rgb, passphrase_bytes, profile_name, model)` returns the plaintext, or
    raises `DecodeError`.
  - Use `load_cover(path, info)` for uploads: it handles PNG or JPEG, sRGB conversion and EXIF
    orientation, and fills `info["colour_conversion"]`.
  - Use `load_png` for decode input.
  - Errors: `InputError` means bad input, `CapacityError` means the message is too long or the
    image was refused, and `DecodeError` means no message.

  The CLI exit codes 0/1/2/3 map to the same states (see the brief).
- **Classic (legacy-v1)** goes through the legacy path: copy what `ghostframe_png/cli.py` does
  for `LEGACY` profiles.
- **Measured costs** (4-vCPU test server, 4 torch threads, 1280-px photos):
  - Encode median: Subtle 19 s, Long 33 s.
  - Slowest held-out encode: Subtle 34 s, Long 43 s.
  - A fresh CLI encode, including model load, took 23–44 s.
  - Decode: about 2 s per mode.
  - Memory: about 0.9–1.0 GB RSS for a MobileNetV3 encode; plan 2 GB per worker with both
    models resident.
  - Refusals on hard images take 3½–5 minutes. Small photos (640 px) are slower: see
    `small640` in `design-data.json`.
- **"Try all modes"** on Read tries Classic, Subtle and Long. Use the warm models; it's about 6 s.
- Thread-count determinism was verified, with 1 and 4 threads giving identical results on this
  CPU and torch build. Pin `torch==2.7.1`, `torchvision==0.22.1`, `numpy==2.3.5` and
  `Pillow==12.3.0` exactly, as in `pyproject.toml`. Install with `.[tiled]`.

## 3. Architecture (from the addendum; confirm with Ben before provisioning)

- **Front end and API:** a Cloudflare Worker with static assets.
- **Engine:** one Cloudflare Container running a small Python HTTP service, Python 3.12, with
  the `ghostframe` package installed from this repository and both checkpoints baked in. It
  wakes on demand and sleeps after 1–2 idle minutes. The account is on Workers Paid.
- **Queue:** a Durable Object holds the queue and allows one encode at a time. It owns job state
  (`queued` → `starting` → `encoding` (with progress) → `done` | `refused` | `timed_out` |
  `cancelled`) and the daily caps (site-wide and per visitor).
- **API:**
  - `POST /api/encode` returns `202 {job_id}`.
  - `GET /api/jobs/{id}` returns the state, queue position, progress and, when done,
    `result_url`.
  - `POST /api/decode` takes `mode | "auto"` and returns `{found, message}`.
  - Passphrases travel in POST bodies only, over HTTPS.
- **Turnstile** is verified server-side before an encode is queued.
- **Retention:** nothing is stored. Process in memory or in a temp directory, and delete inputs
  and outputs when the job finishes or after a short expiry (about 15 minutes for the result
  download).
- **Result PNGs are served byte-for-byte:**
  - `Content-Type: image/png`, `Cache-Control: no-store, no-transform`;
  - no Polish, Image Resizing, WebP/AVIF conversion or other "optimise" step on that route;
  - a test must check the downloaded bytes' SHA-256 equals the engine output.
- **Hard timeout:** stop an encode after 5 minutes and report `timed_out`. Nothing is written.
- The **fallback host** if Containers doesn't work out: this VPS behind a Cloudflare Tunnel. The
  states and copy stay the same.

## 4. The one engine change: a progress callback

The design shows "NN % · reported by the encoder". Add an optional `progress` callable to
`encode_message`, threaded into `_optimize`, called with a fraction between 0 and 1. For
example, the share of tiles that have reached the margin, combined with the repair round and
attempt.
- It must not change any result: same inputs and salt give the same bytes, with or without a
  callback.
- Add a unit test for that.
- It must be cheap: at most a few calls per optimiser step.
- Report it through `GET /api/jobs/{id}`.

## 5. The ready-made examples must work with the engine off

- Use the 9 fixtures in `demo-photos/fixtures/`, made with the profiles above, as static assets,
  exactly as committed: original, the three marked PNGs, and the three difference images per
  photo.
- Show the recorded messages from `fixtures.json` and the measured lines from `res`.
- The "Read a message" sample (the portrait, Classic) should run a real decode when the engine is
  up. When the engine is down or encoding is closed, it falls back to the recorded result,
  clearly labelled as recorded.
- The "What the model sees" view draws from `heat`, `sum` and `raw`. Use the retuned colour scale
  `t = clamp((0.95 − cos) / 0.80, 0, 1)`: MobileNetV3 tiles turn up to about 80°. Show which
  model read the tile.

## 6. Milestones (stop and report after each)

1. **Static site from the design** with the examples, every section and both tabs. A simulated
   backend switch reproduces the prototype's simulated states. Run it locally with
   `npx wrangler dev`. Report it with screenshots at 375, 768 and 1280 px.
2. **Engine service and container.** A Dockerfile, a Python service exposing encode, decode and
   progress, both models baked in, and a local `docker run`. An end-to-end test encodes and
   decodes one photo per mode.
3. **Queue, caps, Turnstile and timeouts.** A Durable Object queue, daily caps, server-side
   Turnstile (with the test keys locally), the 5-minute timeout, cancel, and every waiting and
   refusal state from the addendum.
4. **Hardening.**
   - Input checks with the exact messages from the design's `ISSUE` table: type, 4 MP limit,
     minimum size, alpha, 16-bit/HDR, CMYK/Lab, and JPEG on Read.
   - No-store headers and the byte-exact PNG test.
   - Accessibility: keyboard paths through the divider and tiles, focus states, labels, reduced
     motion for the animation.
   - Error copy for every exit path.
5. **Deploy, only after Ben says yes.** Cloudflare resources, secrets (Turnstile, caps) and a
   smoke test against production.

## 7. Acceptance checks

- Each of the 9 fixtures decodes through `POST /api/decode` to exactly its `fixtures.json`
  message.
- A wrong passphrase returns `{found:false}`, and so does `original.png`.
- A fresh encode in each mode on `demo-photos/coffee-beans.jpg`, downloaded and re-uploaded to
  Read, returns the exact message. The downloaded bytes' SHA-256 equals the engine's output.
- A 495-byte message in Long is rejected client-side and server-side, with the design's
  byte-counter copy. The same goes for 80 bytes in Subtle and 14 in Classic.
- Refusal, `timed_out`, cancel, visitor cap and site cap each show the design's state and never
  offer a file.
- `grep` of the built site finds no `302`, no `sw-l2-c10x8b16p48`, no `sw-l8-c10x8b40p64`, and no
  `512 numbers` outside Classic.
- `python -m unittest discover -s tests` passes. So does the new progress-callback test.
- Lighthouse accessibility ≥ 95. No horizontal scroll at 375 px.

## 8. Report back

At each milestone, report:
- what works, with commands and the tests run;
- what is simulated or stubbed;
- every place you had to interpret the design;
- anything in the design that contradicts the engine facts above.

If the live design and this prompt disagree, tell Ben rather than picking silently.
