# Ghostframe demo site

The demo page for Ghostframe: try the three modes on sample photos, hide a message in your own
photo, and read one back.

| Part | Where | What |
|---|---|---|
| Page | `site/` | Vite + React + TypeScript, built to a static `site/dist/` |
| Engine API | `server/` | Python (Starlette) around the real encoder and decoder, both models kept loaded |
| Hosting | `site/wrangler.jsonc`, `site/worker/`, `server/Dockerfile` | A Cloudflare Worker serves `dist/` and passes `/api/*` to one Cloudflare Container running the engine |

## Run it locally

```sh
# 1. engine API on :8790 (needs the repo venv with the tiled and server extras)
uv pip install --python .venv/bin/python -e '.[tiled,server]'
GF_PRELOAD=1 .venv/bin/python -m server.app

# 2. the page on :5178, proxying /api to the engine
cd site && npm ci && npm run dev
```

`npm run dev` and `npm run build` first run `scripts/prepare-assets.mjs`. It:
- reads every number from `site/data/design-data.json` (written by `python -m tools.design_data` from `bench/results/`);
- reads every example message and hash from `demo-photos/fixtures/*/fixtures.json`;
- copies the fixture PNGs into `public/demo-photos/` and checks every SHA-256.

After the build, `scripts/verify-dist.mjs` checks the copies in `dist/` again. Nothing on the
page is typed in by hand except the prose.

The cover-picker thumbnails in `public/thumbs/` are display copies made by
`.venv/bin/python site/scripts/make_thumbs.py`; they are never decoded.

The mode the page calls Short is `legacy-v1`, named Classic in the main README and in the
fixture file names (`classic.png`).

## Tests

```sh
.venv/bin/python -m unittest tests.test_server        # API: input rules, queue, caps, stop, cancel, exact bytes; real-model fixture decodes
cd site
node tests/e2e.mjs http://127.0.0.1:5178/ Subtle      # Hide -> download -> Read back, wrong passphrase, portrait sample, JPEG refusal
node tests/e2e.mjs http://127.0.0.1:5178/ Short 'Meet at dawn.'
node tests/a11y.mjs                                   # divider and tile keyboard paths, tooltips, tabs, live regions
node tests/phone.mjs                                  # below 760 px: menu, Try it sheet and switch, How it works cards (focus, Escape, scroll lock)
node tests/counter.mjs                                # daily encode counter: when it fetches, 0 on "site limit", hidden on failure
node scripts/touch-targets.mjs touch.png              # every control >= 44 px on touch
```

## Server configuration

| Variable | Default | Meaning |
|---|---|---|
| `GF_SITE_DAILY_CAP` | 50 | encodes per UTC day for the whole site; `none` for no cap. `GET /api/quota` returns `{ left, limit, resets_at }` from the same counter (404 with no cap), and the page's daily counter shows it |
| `GF_VISITOR_DAILY_CAP` | 3 | encodes per UTC day per visitor (keyed IP hash, key replaced daily, never stored) |
| `GF_ENCODE_TIMEOUT_S` | 300 | hard stop per encode; the copy promises 5 minutes |
| `GF_DECODE_SITE_DAILY_CAP` | 1000 | reads per UTC day for the whole site; `none` for no cap |
| `GF_DECODE_VISITOR_DAILY_CAP` | 20 | reads per UTC day per visitor |
| `GF_ENGINE_KEY`, `GF_INTERNAL_KEY` | unset | set by the Durable Object, fresh at every container start. With `GF_ENGINE_KEY` set, encode and decode are refused unless the request carries it (the Worker adds it after checking Turnstile). `GF_INTERNAL_KEY` guards `/api/internal/limits`, which does not exist without it. Unset means local development: no bot check, no internal route, and a warning at start-up |
| `GF_TRUST_CF_IP` | unset | `1` behind Cloudflare: the visitor address comes from `CF-Connecting-IP` |
| `GF_STATIC_DIR` | unset | also serve `site/dist` from the same process (single-host fallback) |
| `GF_PRELOAD`, `GF_THREADS` | unset, 4 | load both models at start-up; torch threads |

## Privacy

Photos, messages and passphrases are processed in memory only: the multipart spool limit is
raised so uploads never reach disk, and a job's photo, message and passphrase are dropped when
the job ends. The marked PNG and the difference image are deleted as soon as the page fetches
them, and an unfetched result is deleted after 15 minutes at most. The Short encoder also works
in memory.

Per-visitor caps use an in-memory hash of the visitor's IP address (IPv6 by /64) with a key that
changes daily and is never stored. The Durable Object stores only today's site-wide encode and read counts.
Cloudflare Workers per-request invocation logs are switched off; only the engine's own log lines (errors and count updates; no photos,
messages or passphrases) are kept by Cloudflare, for up to 7 days. The page sets no cookies and
uses no browser storage; Turnstile may set its own. The privacy notice for visitors is in the page
footer (`src/components/Footer.tsx`).

## Deploy

The site runs on Cloudflare Workers with one Cloudflare Container for the engine.
`wrangler.jsonc` is the author's deployment; for your own, copy `wrangler.example.jsonc` to
`wrangler.jsonc` and fill in the hostname. Put your own Turnstile site key in
`site/.env.production`, or remove the file to build without a bot check. Deploying needs Docker
running, because wrangler builds the engine image locally.

```sh
cd site
CLOUDFLARE_API_TOKEN=… CLOUDFLARE_ACCOUNT_ID=… npm run deploy   # build + verify-dist + wrangler deploy
```

- **One engine.** The Worker sends every `/api/*` request to a single Durable Object (`engine`), which
  starts the container and waits until it answers. There is one container, so the queue, the caps
  and one-encode-at-a-time hold as on a single server.
- **Size and sleep.** 4 vCPU, 2 GiB memory, 4 GB disk. The engine peaked at 1,416 MiB with three Long
  encodes of a 4 MP photo queued and six decodes alongside. The container stops after 3 minutes
  without requests (memory is billed while it is awake); the next visitor wakes it in about 12 s.
- **No Internet from the container.** Both checkpoints are baked into the image and checked against
  their pinned SHA-256 at build time. The Worker verifies the Turnstile token before an upload
  reaches the engine, so the container makes no outbound calls and has no Internet access.
- **Bot check and rate limits.** Hide and Read need a Turnstile token, checked by the Worker. The
  Worker also applies per-IP request rate limits.
- **Daily count.** The site-wide count is saved in the Durable Object's storage after every encode,
  cancel and job poll, and given back to the container (`/api/internal/limits`, never reachable from
  outside) before a fresh container serves its first request. It holds for the whole UTC day across
  sleeps and restarts. A queued job abandoned by a closed tab is given back inside the container
  without a request, so if the container then sleeps, that one encode stays counted.
- **Config.** The caps and the time limit are `vars` in `wrangler.jsonc`, passed to the container
  when it starts. The Turnstile secret is a Worker secret: `npx wrangler secret put GF_TURNSTILE_SECRET`.
- **Testing the live site.** No token or Access setup is needed, but every Hide and Read on the
  live site needs a Turnstile token, so `node tests/e2e.mjs https://<your host>/ Subtle` passes only
  if the headless browser gets one, and each run uses the live daily caps. Test against a local
  server first.

Measured on the live container (2026-11-12, 1920 × 1080 sample photo): Subtle 26.8 s, Long 59.7 s,
Short 48.5 s; every download read back exactly. Waking from sleep took 12 s until the models were
loaded (the very first start, which also pulled the image, took about 23 s).

## Running in public

The site has been public since 2026-11-12. There is no Cloudflare Access app in front of it.

- **Bot check.** Hide and Read need a Turnstile token. The site key is public and lives in
  `site/.env.production`; the secret is the Worker secret `GF_TURNSTILE_SECRET`, and the Worker
  verifies the token before passing the request on.
- **Caps.** 50 encodes per UTC day for the whole site and 3 per visitor. A cancelled encode gives
  its count back only if it had not started yet. Reads (decodes) are capped at 20 per visitor and
  1,000 for the whole site per UTC day. The site-wide encode and read counts are kept in the Durable Object
  across sleeps; the per-visitor counts stay in memory on purpose (persisting them would mean
  storing hashed IP addresses), so they reset when the container sleeps.
- **Serve every PNG byte for byte.** Polish, Mirage, WebP and Image Resizing are off on the
  `electricsheep.id` zone, and a configuration rule pins Polish, Mirage, Rocket Loader and email
  obfuscation off for `ghostframe.electricsheep.id`. The API already sends
  `Cache-Control: no-store, no-transform`.
