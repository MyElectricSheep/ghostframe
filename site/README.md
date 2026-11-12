# Ghostframe demo site

The public page for Ghostframe, built from the design handoff in
[`design-handoff/ghostframe-site/`](../design-handoff/ghostframe-site/README.md) (the spec).

| Part | Where | What |
|---|---|---|
| Page | `site/` | Vite + React + TypeScript, built to a static `site/dist/` |
| Engine API | `server/` | Python (Starlette) around the real encoder and decoder, both models kept loaded |

## Run it locally

```sh
# 1. engine API on :8790 (needs the repo venv with the tiled and server extras)
uv pip install --python .venv/bin/python -e '.[tiled,server]'
GF_PRELOAD=1 .venv/bin/python -m server.app

# 2. the page on :5178, proxying /api to the engine
cd site && npm ci && npm run dev
```

`npm run dev` and `npm run build` first run `scripts/prepare-assets.mjs`. It:
- reads every number from `design-handoff/ghostframe-site/data/design-data.json`;
- reads every example message and hash from `demo-photos/fixtures/*/fixtures.json`;
- copies the fixture PNGs into `public/demo-photos/` and checks every SHA-256.

After the build, `scripts/verify-dist.mjs` checks the copies in `dist/` again. Nothing on the
page is typed in by hand, except the approved copy.

## Tests

```sh
.venv/bin/python -m unittest tests.test_server        # API: input rules, queue, caps, stop, cancel, exact bytes; real-model fixture decodes
cd site
node tests/e2e.mjs http://127.0.0.1:5178/ Subtle      # Hide -> download -> Read back, wrong passphrase, portrait sample, JPEG refusal
node tests/e2e.mjs http://127.0.0.1:5178/ Short 'Meet at dawn.'
node tests/a11y.mjs                                   # divider and tile keyboard paths, tooltips, tabs, live regions
node scripts/touch-targets.mjs /tmp/touch.png         # every control >= 44 px on touch
node scripts/compare.mjs try 1280,768,375 /tmp/cmp    # side by side with the prototype (serve it on :5190)
```

## Server configuration

| Variable | Default | Meaning |
|---|---|---|
| `GF_SITE_DAILY_CAP` | 50 (placeholder) | encodes per UTC day for the whole site; `none` for no cap |
| `GF_VISITOR_DAILY_CAP` | 3 (placeholder) | encodes per UTC day per visitor (keyed IP hash, key replaced daily, never stored) |
| `GF_ENCODE_TIMEOUT_S` | 300 | hard stop per encode; the copy promises 5 minutes |
| `GF_TURNSTILE_SECRET` | unset | when set, encode and decode need a Turnstile token (build the page with `VITE_TURNSTILE_SITEKEY`) |
| `GF_TRUST_CF_IP` | unset | `1` behind Cloudflare: the visitor address comes from `CF-Connecting-IP` |
| `GF_STATIC_DIR` | unset | also serve `site/dist` from the same process (single-host fallback) |
| `GF_PRELOAD`, `GF_THREADS` | unset, 4 | load both models at start-up; torch threads |

Nothing is stored. Uploads stay in memory: the multipart spool limit is raised so they never
reach disk. A job's photo, message and passphrase are dropped when the job ends. The marked PNG
is released as soon as the page fetches it, and anything left expires after 15 minutes. The
`legacy-v1` (Short) encoder writes one temporary file inside a private temporary directory and
deletes it immediately.

## Before launch

- **Hosting is not decided.** Measure encode times on the chosen host: the copy says "usually
  under 2 minutes", and medians were 19 s / 33 s on the 4-vCPU test server. Also measure the
  engine's wake-up time, which the copy puts at "10–20 seconds".
- **Keep the live site behind Cloudflare Access** until it is opened up.
- **Serve every PNG byte for byte.** Turn off Polish, Image Resizing and any WebP/AVIF
  conversion on this hostname. The API already sends `Cache-Control: no-store, no-transform`.
- **The three link placeholders** (`[REPOSITORY_URL]`, `docs/BENCHMARK.md`,
  `docs/AUDIT_REPORT.md`) stay as in the design until the repository is public.
