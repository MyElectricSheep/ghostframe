# Ghostframe demo site: brief for Claude Design

A small public website where anyone can hide a short message in their own photo and read one back.
This brief records what Ghostframe does, what it was measured to do, what a design may promise, and
what the site has to handle. Every number here comes from the 2026-11-10 audit. The evidence is in
`docs/BENCHMARK.md` and `docs/AUDIT_REPORT.md`.

This brief extends `docs/EMBEDDING_PNG_SHOWCASE.md`, which covered a read-only showcase. This site
adds user uploads, encoding and decoding. That requires a server, explained below.

---

## 1. What Ghostframe is, in one paragraph

Ghostframe hides a short text message inside a photo by changing every pixel's colour by a tiny,
capped amount: at most 2 or 8 steps out of 255 per colour channel. A frozen, public image
recognition model, SqueezeNet 1.1, reads the photo in a grid of tiles. The way it "sees" each tile
spells out bits. The encoder nudges pixels until the model's readings spell the encrypted message.
Reading it back needs only the saved PNG, the same model and the passphrase. Without the passphrase
nothing comes out. If anyone alters the hidden message, it is rejected instead of being misread.

**The message is private and tamper-evident. Its existence is not hidden.** Anyone with the free,
public reader can tell that a photo carries a Ghostframe message. They cannot read it or forge it.

---

## 2. Measured facts the design can rely on

### Modes to offer

These are the three verified options. The mode names are suggestions; the technical profile names
must be kept exactly, because they are part of the format.

| Suggested UI name | Technical profile | Max message | Max colour change per channel | Evidence | Status |
|---|---|---:|---:|---|---|
| **Classic** (default) | `legacy-v1` | 13 bytes ("Meet at dawn.") | 8 / 255 | 41/41 held-out photos | original, verified showcase format |
| **Subtle** | `sw-l2-c10x8b16p48` | 79 bytes | 2 / 255 | 123/123 held-out trials | experimental |
| **Long** | `sw-l8-c10x8b40p64` | 302 bytes | 8 / 255 | 123/123 held-out trials | experimental |

- Limits are in **bytes of UTF-8**, not characters. Plain English letters are 1 byte. Accented
  letters take 2 bytes and most emoji take 4. Show a live byte counter, such as "41 / 79 bytes", not
  a character count.
- **Held-out trials** means 41 photographs the system had never seen, all 1280 px wide, with three
  separate messages per photo. A separate program read each one back, given only the file and the
  passphrase.
- Image quality on those photos (median): Subtle 42.9 dB PSNR and SSIM 0.979; Long 35.0 dB and SSIM
  0.885. Classic is 36.5 dB and 0.924. Long changes the image visibly more than Subtle. Do not call
  any mode "invisible".

### Speed and resources (measured on a 4-core CPU server, also running other services)

| | Typical | Slow cases |
|---|---|---|
| Encode | 30–40 s | about 1 min. Hard images can take 5–15 min, and a refusal takes 6–10 min |
| Decode | about 2–4 s per mode, plus about 3 s of model loading if it is not kept warm | — |
| Memory | about 1.4 GB per worker process | — |

Encoding is slow because the encoder optimises the pixels, then saves, reopens and checks its own
output before handing anything back. **The design must treat encoding as a background job that can
take a minute, with real progress states, not a spinner on a button.**

### What can fail, and how often

- **The encoder can refuse.** On flat, synthetic or tiny images (blank backgrounds, solid colours,
  colour bars, line art, images near the minimum size), refusals were common: Subtle succeeded on
  3/9 of these and Long on 6/9.
  - When the encoder refuses, it produces **no file**. It never returns an image that fails to decode.
  - Message to show: "This picture doesn't have enough texture to carry the message. Try a busier
    photo, a shorter message, or the Long mode."
- **Small photos are slower, and Subtle is a little less reliable on them.** The same 41 test
  photos were tried at 640 px wide:
  - Long passed 41/41. Subtle passed 40/41, and its one failure was a clean refusal.
  - Typical encodes took about 45–50 s, but the slowest took up to 16 minutes before succeeding
    or refusing.
  - Recommend photos at least about 1000 px wide, and never promise success.
- **Decoding fails cleanly.** A wrong passphrase, the wrong mode, an untouched photo, or a damaged
  or re-saved file all give the same result: "No message found." Nothing partial is ever shown. The
  system cannot tell the user which of these causes applies, and should not guess.

### What destroys the message

The hidden message survives **only an exact copy of the PNG file**. All of these destroy it:
- re-saving as JPEG
- sending through WhatsApp, Instagram, Messenger or most chat apps, which recompress images
- screenshots
- resizing, cropping, rotating or filters
- some "optimise image" tools

Email attachments, file-sharing links, AirDrop and USB copies preserve it. The download screen must
say this clearly. It is the most likely reason a real user's decode fails.

---

## 3. Inputs and outputs (enforced by the engine)

**Accepted uploads:** PNG or JPEG, up to 4 megapixels (for example 2448 × 1632).
- Minimum size: 160 × 128 for Subtle and Long. Larger is better, see above.
- Phone orientation (EXIF) is applied automatically.
- Photos with a wide-gamut colour profile (Display P3 from iPhones, Adobe RGB) are converted to
  standard sRGB first. The colours may shift very slightly. Tell the user when this happens.

**Rejected uploads** (show a specific message for each):
- an image with transparent pixels
- 16-bit or HDR images
- CMYK or Lab images
- a file over 4 MP, or smaller than the minimum for the chosen mode
- a file that isn't PNG or JPEG
- **For decoding, PNG only.** A JPEG can never contain a readable message, so say that directly.

**Output:** always a PNG. It contains only pixels: no location, camera or other metadata. The output
is typically larger than a JPEG original, often 0.5–3 MB.

**Passphrase:** any text. The message is encrypted with AES-256-GCM, and the key is derived from the
passphrase with scrypt, which deliberately makes guessing slow. A weak passphrase is still weak.
Show a short strength hint and suggest three or more random words. Never store it, never put it in
the URL, and never send it anywhere except the encode or decode request.

---

## 4. Pages and flows

One page with two tabs is enough: **Hide a message** and **Read a message**, plus a "How it works"
section and a "Limits and evidence" section.

### Try it first: no upload needed

Above the fold, keep the existing entry point: the "Meet at dawn." portrait (Grace Hopper, public
domain).
- The user compares the original and the encoded photo with an A/B toggle or a split slider. Give
  the slider a keyboard and button alternative.
- They reveal the amplified difference view.
- They press **Read the message** to see "Meet at dawn." appear.
- They press **Try the untouched original** to see "No message found."

This works even if the server is busy, using recorded results that are clearly labelled as
recorded. Ready-made files are in `benchmarks/embedding-showcase/`:

| File | What it is |
|---|---|
| `grace-hopper-original.png` | untouched cover, the negative control: no message |
| `../goal-validation/neural-demo.png` + `neural-difference.png` (×24) | Classic: "Meet at dawn." |
| `png-l2-sentence.png` + `png-l2-sentence-difference.png` (×96) | Subtle: "Meet at dawn. The north gate stays open until six. Bring the blue notebook." |
| `png-l8-paragraph.png` + `png-l8-paragraph-difference.png` (×24) | Long: a 299-byte paragraph, with exact text in `fixtures-v2.json` |

The public passphrase for all fixtures is `ghostframe public benchmark fixture`.

### Hide a message

1. **Upload a photo.** Drag and drop or pick a file. Show the size and a quick pass or fail on the
   input rules before anything else happens.
2. **Choose a mode:** Classic, Subtle or Long. Each card shows its max length, max colour change
   and "experimental" where it applies.
3. **Type the message** with a live byte counter. Block submission when it is over the limit.
4. **Set a passphrase**, entered twice, with a show/hide toggle and a strength hint.
5. **Encode.** This is a queued job, about 30–60 s. Show honest stages: "Queued (2 ahead)",
   "Adjusting pixels", "Checking the saved file", "Done". If the user's request is refused or times
   out, show the refusal message above. Do not say "error".
6. **Result:**
   - before/after compare, and the amplified difference image with its multiplier stated
     ("differences ×96, real maximum 2/255")
   - **Download PNG**
   - the "how to send it without destroying it" note
   - "The photo still looks like a photo, but anyone with the public reader can tell it carries a
     message."

### Read a message

1. **Upload a PNG.** Reject JPEG with an explanation.
2. **Enter the passphrase.**
3. **Mode:** default to "Try all modes". The server tries Classic, Subtle and Long, about 2–4 s
   each. Offer a manual choice for speed.
4. **Result:** either the exact message, shown as plain text with a copy button, or "No message
   found." The possible reasons are a wrong passphrase, a different mode, a re-saved or compressed
   file, or no message at all. Never show a partial or "best guess" message.

### How it works (schematic)

1. The passphrase locks the message.
2. Error-correction bytes are added.
3. The photo is split into a grid of tiles: 10 × 8 for Subtle and Long, 6 × 5 for Classic.
4. Each tile is nudged so that a frozen, public image model reads it as specific bits.
5. Reading back runs the same model on each tile, repairs a few wrong bits, then unlocks with the
   passphrase.

Explain an "embedding" as "the list of numbers the model produces to describe a tile". The model's
weights never change. Only the pixels do.

### Limits and evidence

A plain list:
- **Exact PNG copies only.** Recompressing, resizing or cropping destroys the message.
- **Not invisible to software.** It is detectable by anyone with the public reader: a test
  separated marked from clean photos 100 % of the time.
- **Not every photo works.** Flat, synthetic and small images can be refused.
- **Experimental modes.** Subtle and Long are experimental: measured on 41 large photographs, with
  no guarantee for any particular image.
- **Short messages only.** The limits are 13, 79 or 302 bytes.

Link to the source code, `docs/BENCHMARK.md` and `docs/AUDIT_REPORT.md`, with the measured numbers
next to the claims (for example "123 of 123 held-out trials").

---

## 5. Copy rules: what not to claim

Avoid all of these:
- "invisible", "undetectable", "untraceable" or "military-grade"
- "works with any photo"
- "share anywhere"
- "AI hides your message" (the model only reads; a standard optimiser makes the changes)

Say instead:
- "barely visible changes, capped at 2 or 8 levels out of 255"
- "private and tamper-evident, but detectable"
- "keep the PNG file exact"

Label recorded demo results as recorded, and live results as live. It is a public engineering
experiment: no accounts, pricing or sign-up.

---

## 6. Privacy and safety for a public upload site

- **Retention:** do not keep uploads, messages, passphrases or outputs. Process in memory or in a
  temporary directory, delete after the download (for example within 15 minutes), and say so on the
  page.
- **Logging:** never log the message or the passphrase.
- **Abuse limits:** encoding costs about 30–60 s of a CPU core and 1.4 GB of memory, so the site
  needs a queue, per-visitor rate limits (for example 5 encodes per hour), a maximum queue length
  with a "busy, try later" state, and a hard timeout of about 3 minutes per encode. The engine does
  not time out by itself.
- **Bot protection:** use a CAPTCHA-style check, for example Cloudflare Turnstile, on encode and
  decode.
- **Uploads may contain faces:** don't show other users' images anywhere, with no gallery and no
  "recent" list.
- **Content:** the site is a demo for short messages. A short line in the terms ("don't use this to
  hide illegal content; nothing is stored") is enough.

---

## 7. Technical constraints for whoever builds it

- **Runtime:** the engine is Python (PyTorch 2.7.1 CPU, torchvision 0.22.1) with a pinned
  SqueezeNet 1.1 checkpoint (sha256 `b8a52dc0…`) and a pinned calibration file. Encoding and
  decoding must run **on a server** with these exact versions.
- **No browser decoding yet:** running the model in the browser (ONNX or WebGPU) would change the
  numerics, and has not been validated. Matching results across CPU thread counts were verified on
  this server only. Don't design a "runs entirely in your browser" claim.
- **Hosting:** this does not fit on Cloudflare Workers. It needs a container or VM host with at
  least about 2 GB RAM per worker and 2–4 vCPUs, such as a small VPS, Fly.io, Cloud Run or a
  Cloudflare Container. The front end can be a static site anywhere.
- **Engine entry points:** the backend can call the CLI or the Python API.

  ```
  ghostframe-png encode COVER OUT.png --profile <name> --message-file <f> --passphrase-file <f>
  ghostframe-png decode IMAGE.png --profile <name> --passphrase-file <f>     # message on stdout
  ```

  Exit codes map directly to UI states:

  | Exit code | Meaning |
  |---:|---|
  | 0 | success |
  | 1 | no message found |
  | 2 | bad input or usage, with the reason on stderr |
  | 3 | message too long, or the image can't carry it (refusal) |

  The Python API (`ghostframe_png.encode_message` and `decode_message`) avoids reloading the model
  for every request, which saves about 3 s and is recommended for a server. `legacy-v1` (Classic)
  goes through the same CLI.
- **Suggested API:**

  | Request | Body | Returns |
  |---|---|---|
  | `POST /api/encode` | image, mode, message, passphrase | `202 {job_id}` |
  | `GET /api/jobs/{id}` | — | `{state: queued\|running\|done\|refused\|failed, position, result_url}` |
  | `POST /api/decode` | image, passphrase, mode \| "auto" | `200 {found: true, message}` or `200 {found: false}` |

  Use HTTPS only, and send passphrases in the POST body only.
- **The output PNG** must be served byte-for-byte as produced: no image CDN resizing, no
  "polish/optimise" features, no format conversion to WebP or AVIF. **Cloudflare Polish or Image
  Resizing would silently destroy the messages.**

---

## 8. Visual direction (carried over from the showcase brief)

- **Layout:** a photographic contact-sheet layout with a large image stage, collapsing to a single
  image on narrow screens.
- **Tone:** conversational headings with precise numbers.
- **Accessibility:** visible focus, reduced motion supported, and authentication status always
  written as text, not only as a colour or icon.
- **Screens to deliver:**
  - desktop and mobile versions of the try-it, hide and read flows
  - upload validation errors
  - encode in progress, queued, success, refused and busy
  - decode found and not found
  - the schematic
  - the limits and evidence section
