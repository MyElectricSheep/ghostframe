# Demo site brief: addendum (small photos and hosting)

> **Engine update, 2026-11-11.** Subtle and Long now use the MobileNetV3-Small profiles
> (`bb-mobilenet_v3_small-l2-b16p48`, 79 B, and `bb-mobilenet_v3_small-l8-b64p112`, **494 B**).
> Encodes are about 1.6× faster, and Classic is unchanged. Where this brief gives SqueezeNet
> profile names, the 302 B limit or encode times, the current figures are in
> [design-handoff/mobilenet-v3/](../design-handoff/mobilenet-v3/README.md). The product rules,
> states and copy here still apply.


This adds to [DEMO_SITE_BRIEF.md](DEMO_SITE_BRIEF.md). Where they disagree, this file wins.
It covers two new findings:
1. How the engine behaves on smaller photos.
2. What the likely free hosting setup means for the interface.

## 1. Small photos: test results

The 41 test photos were shrunk to 640 px wide and encoded again. Each photo was encoded once per
mode and read back by a separate process.

| Mode | Message size | Result at 640 px | When it failed |
|---|---|---|---|
| **Subtle** | up to 79 B | 40/41 | One photo (a neon sign at night) was refused. No file was produced. |
| **Long** | up to 302 B | 41/41 | Never. |
| **Classic** | 13 B | not retested at this size | — |

For comparison, the old 49-byte mode passed only 28/41, and its 13 failures produced images that
cannot be read back. The demo uses the new modes, which never return a broken image: they either
return a file that has already been checked to decode, or they refuse.

### Encoding time

| | Typical (median) | Slow (1 in 10) | Slowest seen |
|---|---|---|---|
| Subtle at 640 px | ~45 s | ~4–5 min | ~16 min |
| Long at 640 px | ~50 s | ~3–4 min | ~10 min |
| Either mode at 1280 px (earlier test) | 30–40 s | — | — |

These times come from a shared 4-core server, so treat them as rough. A hosted container with 1–2
cores will probably be slower: plan for **about 1–3 minutes** for a typical encode.

## 2. What this means for the interface

### Photo guidance (upload step)

- Recommend **at least 1000 px on the long side**. Photos smaller than that are accepted, but
  show a soft warning.
  - Copy: "Small photos take longer and are more likely to be refused. Bigger, busier photos work best."
- Below the hard minimum (160 × 128), or above 4 MP, reject the photo before upload with a clear
  reason.
- Busy, detailed photos (food, textures, crowds, foliage) work best. Avoid flat skies, plain
  walls, logos and screenshots. Show this as a short tip, not as a rule.

### Waiting states (encode)

The encoder needs a waiting experience designed for minutes, not seconds. Design these states:

1. **Queued:** "You're next in line" or "2 people ahead of you". Only one encode runs at a time.
2. **Waking up:** this applies only to the first visitor after a quiet period, and adds ~10–20 s.
   Copy: "Starting the engine…"
3. **Encoding:** a real progress indicator, plus "This usually takes 1–3 minutes. You can keep
   this tab open."
4. **Taking longer than usual:** shown after about 2 min. Copy: "This photo is a tough one. Still
   working…" Offer a **Cancel** button.
5. **Timed out:** the server stops at a fixed limit (planned: 5 min) to protect the free budget.
   Treat it like a refusal. Copy: "This photo took too long to encode. Try a larger or more
   detailed photo, or a shorter message."
6. **Refused:** "This picture doesn't have enough texture to carry the message. Try a busier
   photo, a shorter message, or Long mode."
7. **Done:** download the marked PNG, with the difference view next to it.

States 5 and 6 never produce a file. Never show a partial or "best effort" image.

### Daily limit

To stay free, the live demo caps the number of encodes per day. Two caps are planned:
- a site-wide daily number
- a few per visitor

Design for both:

- **Visitor limit reached:** "You've used today's encodes. You can still decode any image, or
  try the ready-made examples."
- **Site limit reached:** "The demo has hit today's limit. Encoding comes back tomorrow (UTC).
  Decoding still works."
- A bot check (Cloudflare Turnstile) runs before an encode starts. Keep it unobtrusive and place it
  next to the Encode button.

**Decoding is fast** (a few seconds) and is not capped. When encoding is unavailable, push
visitors towards:
- the nine ready-made example images (coffee beans, Milky Way, Antonello portrait × Classic /
  Subtle / Long)
- decoding their own previously marked files

The examples should always work, even when encoding is closed.

## 3. Technical shape (for context, not for design)

- The static site and the API run on **Cloudflare Workers**.
- The engine (Python + PyTorch, ~1.2 GB of memory per encode) runs in **one Cloudflare
  Container**:
  - It wakes on demand and sleeps after 1–2 idle minutes.
  - A Durable Object holds the queue, so only one job runs at a time.
- Encode jobs are asynchronous:
  - `POST /api/encode` returns a job ID.
  - The page polls `GET /api/jobs/{id}` (or listens on a stream) for the states in section 2.
  - States: `queued` → `starting` → `encoding` (with progress) → `done` | `refused` |
    `timed_out` | `cancelled`.
- Uploaded photos and results are deleted once the job finishes, or after a short expiry. Nothing is kept.
- If the hosting choice changes (for example to a self-hosted server), the states and copy above
  stay the same. Only the waiting times change.
