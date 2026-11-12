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
| `GF_TURNSTILE_SECRET` | unset | when set, encode and decode need a Turnstile token (build the page with `VITE_TURNSTILE_SITEKEY`) |
| `GF_TRUST_CF_IP` | unset | `1` behind Cloudflare: the visitor address comes from `CF-Connecting-IP` |
| `GF_STATIC_DIR` | unset | also serve `site/dist` from the same process (single-host fallback) |
| `GF_PRELOAD`, `GF_THREADS` | unset, 4 | load both models at start-up; torch threads |

Nothing is stored. Uploads stay in memory: the multipart spool limit is raised so they never
reach disk. A job's photo, message and passphrase are dropped when the job ends. The marked PNG
is released as soon as the page fetches it, and anything left expires after 15 minutes. The
`legacy-v1` (Short) encoder writes one temporary file inside a private temporary directory and
deletes it immediately.

## Deploy

The site runs on Cloudflare Workers with one Cloudflare Container for the engine. The Worker can
also sit behind Cloudflare Access and check its token. `wrangler.jsonc` is the author's deployment;
for your own, copy `wrangler.example.jsonc` to `wrangler.jsonc` and fill in the hostname and either
the Access team domain and AUD, or `ACCESS_AUD: "off"`. Put your own Turnstile site key in
`site/.env.production`, or remove the file to build without a bot check. Deploying needs Docker running, because wrangler builds the
engine image locally.

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
  their pinned SHA-256 at build time. Outbound access is turned on only when `GF_TURNSTILE_SECRET` is
  set, because Turnstile verification is the only outbound call.
- **Two locks.** Access sits in front of the hostname, and the Worker also checks every request's
  Access token (signature, audience, expiry) before serving anything, assets included. Set
  `ACCESS_AUD` to `off` in `wrangler.jsonc` only when the site is opened up.
- **Daily count.** The site-wide count is saved in the Durable Object's storage after every encode,
  cancel and job poll, and given back to the container (`/api/internal/limits`, never reachable from
  outside) before a fresh container serves its first request. It holds for the whole UTC day across
  sleeps and restarts. A queued job abandoned by a closed tab is given back inside the container
  without a request, so if the container then sleeps, that one encode stays counted.
- **Config.** The caps and the time limit are `vars` in `wrangler.jsonc`, passed to the container
  when it starts. The Turnstile secret is a Worker secret: `npx wrangler secret put GF_TURNSTILE_SECRET`.
- **Testing the live site.** Create a temporary Access service token, allow it on the app, then run
  `CF_ACCESS_CLIENT_ID=… CF_ACCESS_CLIENT_SECRET=… node tests/e2e.mjs https://<your host>/ Subtle`.
  Delete the token afterwards.

Measured on the live container (2026-11-12, 1920 × 1080 sample photo): Subtle 26.8 s, Long 59.7 s,
Short 48.5 s; every download read back exactly. Waking from sleep took 12 s until the models were
loaded (the very first start, which also pulled the image, took about 23 s).

## Running in public

The site has been public since 2026-11-12, with no Access app in front (`ACCESS_AUD` is `off`).

- **Bot check.** Hide and Read need a Turnstile token. The site key is public and lives in
  `site/.env.production`; the secret is the Worker secret `GF_TURNSTILE_SECRET`, and setting it also
  gives the container outbound access for verification.
- **Caps.** 50 encodes per UTC day for the whole site and 3 per visitor. The site-wide count is
  kept in the Durable Object across sleeps; the per-visitor counts stay in memory on purpose
  (persisting them would mean storing hashed IP addresses), so they reset when the container sleeps.
- **Serve every PNG byte for byte.** Polish, Mirage, WebP and Image Resizing are off on the
  `electricsheep.id` zone, and a configuration rule pins Polish, Mirage, Rocket Loader and email
  obfuscation off for `ghostframe.electricsheep.id`. The API already sends
  `Cache-Control: no-store, no-transform`.
