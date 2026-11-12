// Cloudflare Worker for the demo site: static assets from site/dist, and /api/* passed to the
// engine (server/app.py) running in one Container. There is exactly one engine instance, so the
// queue, the daily caps and the one-encode-at-a-time rule hold as on a single server.
import { DurableObject } from 'cloudflare:workers';

interface Env {
  ENGINE: DurableObjectNamespace<Engine>;
  ASSETS: Fetcher;
  GF_SITE_DAILY_CAP: string;
  GF_VISITOR_DAILY_CAP: string;
  GF_ENCODE_TIMEOUT_S: string;
  GF_TURNSTILE_SECRET?: string;
  ACCESS_TEAM_DOMAIN: string;
  ACCESS_AUD: string;
  REVIEW_HOST: string;
  REVIEW_KEY?: string;
}

const PORT = 8790;
// Results expire after 15 minutes on the server; a page polls every second while it waits.
const INACTIVITY_TIMEOUT_MS = 10 * 60 * 1000;
const READY_TIMEOUT_MS = 90 * 1000;
// 4 vCPU like the test server; an encode peaked at about 1 GB, and the image is 1.8 GB on disk.
const INSTANCE = { vcpu: 4, memoryMib: 4096, diskMb: 4000 };

export class Engine extends DurableObject<Env> {
  starting?: Promise<void>;

  constructor(ctx: DurableObjectState, env: Env) {
    super(ctx, env);
    const container = ctx.container;
    if (container?.running) void ctx.blockConcurrencyWhile(() => container.setInactivityTimeout(INACTIVITY_TIMEOUT_MS));
  }

  async fetch(request: Request): Promise<Response> {
    this.starting ??= this.startAndWait().finally(() => { this.starting = undefined; });
    try {
      await this.starting;
    } catch (error) {
      console.error('engine did not start', error);
      return Response.json({ error: 'unreachable' }, { status: 503, headers: { 'Cache-Control': 'no-store' } });
    }
    const url = new URL(request.url);
    if (url.pathname.startsWith('/api/internal/')) return new Response('Not found', { status: 404 });
    url.protocol = 'http:';
    url.host = 'container';
    const forwarded = new Request(url, request);
    forwarded.headers.delete('host');
    const response = await this.ctx.container!.getTcpPort(PORT).fetch(forwarded);
    // Encodes, cancels and job polls are where the site-wide count changes: save it each time.
    if (url.pathname === '/api/encode' || url.pathname.startsWith('/api/jobs/')) void this.saveCount();
    return response;
  }

  // The site-wide daily count lives in the container's memory while it runs, and in this Durable
  // Object's storage across sleeps and restarts, so it holds for the whole UTC day. The per-visitor
  // counts are not persisted: they are keyed by a hashed IP whose key is never stored.
  restored = false;

  async saveCount(): Promise<void> {
    try {
      const r = await this.ctx.container!.getTcpPort(PORT).fetch('http://container/api/internal/limits');
      if (r.ok) await this.ctx.storage.put('siteCount', await r.json());
    } catch (error) {
      console.error('could not save the daily count', error);
    }
  }

  async restoreCount(): Promise<void> {
    const saved = await this.ctx.storage.get<{ day: string; site: number }>('siteCount');
    if (saved) {
      const r = await this.ctx.container!.getTcpPort(PORT).fetch('http://container/api/internal/limits', { method: 'POST', body: JSON.stringify(saved), headers: { 'content-type': 'application/json' } });
      // Never block the site on this: log it and try again on the next request.
      if (!r.ok) { console.error('could not restore the daily count', r.status); return; }
    }
    this.restored = true;
  }

  async startAndWait(): Promise<void> {
    const container = this.ctx.container!;
    if (!container.running) {
      this.restored = false;
      const env: Record<string, string> = {
        GF_SITE_DAILY_CAP: this.env.GF_SITE_DAILY_CAP,
        GF_VISITOR_DAILY_CAP: this.env.GF_VISITOR_DAILY_CAP,
        GF_ENCODE_TIMEOUT_S: this.env.GF_ENCODE_TIMEOUT_S,
      };
      if (this.env.GF_TURNSTILE_SECRET) env.GF_TURNSTILE_SECRET = this.env.GF_TURNSTILE_SECRET;
      // No Internet access: the checkpoints are baked into the image, and Turnstile is the only
      // outbound call, so it is allowed only once a secret is configured.
      container.start({ image: container.images.base, instance: INSTANCE, enableInternet: Boolean(this.env.GF_TURNSTILE_SECRET), env });
    }
    await container.setInactivityTimeout(INACTIVITY_TIMEOUT_MS);
    const port = container.getTcpPort(PORT);
    const deadline = Date.now() + READY_TIMEOUT_MS;
    let lastError: unknown;
    while (Date.now() < deadline) {
      try {
        const response = await port.fetch('http://container/api/status', { signal: AbortSignal.timeout(2000) });
        await response.body?.cancel();
        // Before the first request reaches a fresh container, give it today's saved count.
        if (response.ok) { if (!this.restored) await this.restoreCount(); return; }
        lastError = new Error(`status returned ${response.status}`);
      } catch (error) {
        lastError = error;
      }
      await scheduler.wait(250);
    }
    throw new Error(`engine not ready on port ${PORT}`, { cause: lastError });
  }
}

// Cloudflare Access sits in front of the hostname. Every request, assets included, must also carry
// a valid Access token for this application, so the site stays closed even if the Access app is
// missing or misconfigured. ACCESS_AUD = "off" opens the site.
type Jwk = JsonWebKey & { kid: string };
let certs: { keys: Jwk[]; fetched: number } | undefined;

const b64url = (part: string) => Uint8Array.from(atob(part.replace(/-/g, '+').replace(/_/g, '/')), (c) => c.charCodeAt(0));

async function accessKeys(team: string, refresh: boolean): Promise<Jwk[]> {
  if (!certs || refresh || Date.now() - certs.fetched > 3600_000) {
    const r = await fetch(`https://${team}/cdn-cgi/access/certs`);
    certs = { keys: ((await r.json()) as { keys: Jwk[] }).keys, fetched: Date.now() };
  }
  return certs.keys;
}

async function hasAccess(request: Request, env: Env): Promise<boolean> {
  if (env.ACCESS_AUD === 'off') return true;
  const token = request.headers.get('cf-access-jwt-assertion');
  if (!token) return false;
  try {
    const [head, body, sig] = token.split('.');
    const header = JSON.parse(new TextDecoder().decode(b64url(head)));
    const claims = JSON.parse(new TextDecoder().decode(b64url(body)));
    const aud = Array.isArray(claims.aud) ? claims.aud : [claims.aud];
    if (header.alg !== 'RS256' || !aud.includes(env.ACCESS_AUD) || claims.iss !== `https://${env.ACCESS_TEAM_DOMAIN}`) return false;
    if (typeof claims.exp !== 'number' || claims.exp * 1000 < Date.now()) return false;
    let jwk = (await accessKeys(env.ACCESS_TEAM_DOMAIN, false)).find((k) => k.kid === header.kid);
    jwk ??= (await accessKeys(env.ACCESS_TEAM_DOMAIN, true)).find((k) => k.kid === header.kid);
    if (!jwk) return false;
    const key = await crypto.subtle.importKey('jwk', jwk, { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' }, false, ['verify']);
    return await crypto.subtle.verify('RSASSA-PKCS1-v1_5', key, b64url(sig), new TextEncoder().encode(`${head}.${body}`));
  } catch {
    return false;
  }
}

// A temporary review address (REVIEW_HOST) without Access, for design reviews. It needs the
// REVIEW_KEY secret: `?review=<key>` once sets a cookie (SameSite=None and Partitioned, so it also
// works inside another site's frame), then the cookie lets the page load its
// files. Encoding is refused there with the designed daily-limit state; reading still works.
// Without the secret the review address refuses everything.
const REVIEW_COOKIE = 'gf_review';

function sameKey(given: string | null | undefined, key: string): boolean {
  if (!given) return false;
  const a = new TextEncoder().encode(given), b = new TextEncoder().encode(key);
  return a.byteLength === b.byteLength && crypto.subtle.timingSafeEqual(a, b);
}

const cookie = (request: Request, name: string) =>
  request.headers.get('cookie')?.split(';').map((c) => c.trim().split('=')).find(([k]) => k === name)?.[1];

async function review(request: Request, env: Env): Promise<Response> {
  const forbidden = new Response('Forbidden', { status: 403, headers: { 'Cache-Control': 'no-store', 'X-Robots-Tag': 'noindex' } });
  if (!env.REVIEW_KEY) return forbidden;
  const url = new URL(request.url);
  const fromQuery = sameKey(url.searchParams.get('review'), env.REVIEW_KEY);
  if (!fromQuery && !sameKey(cookie(request, REVIEW_COOKIE), env.REVIEW_KEY)) return forbidden;
  let response = url.pathname === '/api/encode'
    ? Response.json({ error: 'site_limit' }, { status: 429, headers: { 'Cache-Control': 'no-store' } })
    : await route(request, env);
  response = new Response(response.body, response);
  response.headers.set('X-Robots-Tag', 'noindex');
  if (fromQuery) response.headers.append('Set-Cookie', `${REVIEW_COOKIE}=${env.REVIEW_KEY}; Path=/; Max-Age=604800; HttpOnly; Secure; SameSite=None; Partitioned`);
  return response;
}

function route(request: Request, env: Env): Promise<Response> {
  const { pathname } = new URL(request.url);
  if (pathname.startsWith('/api/internal/')) return Promise.resolve(new Response('Not found', { status: 404 }));
  if (pathname.startsWith('/api/')) return env.ENGINE.getByName('engine').fetch(request);
  return env.ASSETS.fetch(request);
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    if (new URL(request.url).hostname === env.REVIEW_HOST) return review(request, env);
    if (!(await hasAccess(request, env))) return new Response('Forbidden', { status: 403, headers: { 'Cache-Control': 'no-store' } });
    return route(request, env);
  },
} satisfies ExportedHandler<Env>;
