// Cloudflare Worker for the demo site. Static assets from site/dist are served without the Worker
// (assets.run_worker_first is ["/api/*"]); /api/* comes here and goes to the engine
// (server/app.py) running in one Container. There is exactly one engine instance, so the queue,
// the daily caps and the one-encode-at-a-time rule hold as on a single server.
//
// The Worker answers only the engine's public routes (worker/routes.ts), rate-limits them per
// visitor, checks upload sizes and Turnstile itself, and only then wakes the engine.
import { DurableObject } from 'cloudflare:workers';
import { apiRoute, isApiPath, mentionsInternal, uploadProblem, verifyTurnstile, visitorKey } from './routes';

interface Env {
  ENGINE: DurableObjectNamespace<Engine>;
  ASSETS: Fetcher;
  GF_POST_LIMIT: RateLimit;
  GF_API_LIMIT: RateLimit;
  GF_SITE_DAILY_CAP: string;
  GF_VISITOR_DAILY_CAP: string;
  GF_DECODE_SITE_DAILY_CAP: string;
  GF_DECODE_VISITOR_DAILY_CAP: string;
  GF_ENCODE_TIMEOUT_S: string;
  GF_TURNSTILE_SECRET?: string;
}

const PORT = 8790;
// Memory is billed for every second the container is awake, so it sleeps soon after the last
// request. A page polls every second while an encode runs, which keeps it awake until the result
// has been fetched; results expire after 15 minutes on the server.
const INACTIVITY_TIMEOUT_MS = 3 * 60 * 1000;
const READY_TIMEOUT_MS = 90 * 1000;
// 4 vCPU like the test server. 2 GiB: the engine peaked at 1,416 MiB with three Long encodes of a
// 4 MP photo queued and six decodes alongside, in a 2 GiB cgroup with no swap. The image is 1.8 GB on disk.
const INSTANCE = { vcpu: 4, memoryMib: 2048, diskMb: 4000 };
// Per-start secrets shared only by this Durable Object and the container it starts (server/app.py).
const ENGINE_KEY_HEADER = 'x-gf-engine-key';
const INTERNAL_KEY_HEADER = 'x-gf-internal-key';
const NO_STORE = { 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' };

const fail = (status: number, error: string) => Response.json({ error }, { status, headers: NO_STORE });

interface Keys { engine: string; internal: string }
interface SavedCount { day: string; site: number; read?: number }

function randomKey(): string {
  return [...crypto.getRandomValues(new Uint8Array(32))].map((b) => b.toString(16).padStart(2, '0')).join('');
}

const today = () => new Date().toISOString().slice(0, 10);

export class Engine extends DurableObject<Env> {
  starting?: Promise<void>;
  keys?: Keys;

  constructor(ctx: DurableObjectState, env: Env) {
    super(ctx, env);
    const container = ctx.container;
    if (container?.running) void ctx.blockConcurrencyWhile(() => container.setInactivityTimeout(INACTIVITY_TIMEOUT_MS));
  }

  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);
    // The Worker forwards only allow-listed routes; check again here, in every decoded form.
    if (mentionsInternal(url.pathname) || url.pathname.includes('%')) return fail(404, 'not_found');
    // The daily counter must not wake (and bill) the engine: when it sleeps, answer from storage.
    if (request.method === 'GET' && url.pathname === '/api/quota' && !this.ctx.container!.running) return this.storedQuota();
    this.starting ??= this.startAndWait().finally(() => { this.starting = undefined; });
    try {
      await this.starting;
    } catch (error) {
      console.error('engine did not start', error);
      return fail(503, 'unreachable');
    }
    const encode = request.method === 'POST' && url.pathname === '/api/encode';
    // Without today's restored count a fresh container would allow the whole daily cap again.
    if (encode && !this.restored) return fail(503, 'unreachable');
    const keys = await this.loadKeys();
    if (!keys) return fail(503, 'unreachable');
    url.protocol = 'http:';
    url.host = 'container';
    const forwarded = new Request(url, request);
    forwarded.headers.delete('host');
    forwarded.headers.delete(INTERNAL_KEY_HEADER);
    forwarded.headers.set(ENGINE_KEY_HEADER, keys.engine);  // the Worker has checked Turnstile
    const response = await this.ctx.container!.getTcpPort(PORT).fetch(forwarded);
    // Only an encode or a cancel changes the site-wide count (job polls do not), so save after those.
    const counts = request.method === 'POST' && (encode || url.pathname.endsWith('/cancel') || url.pathname === '/api/decode');
    if (counts) void this.saveCount();
    return response;
  }

  async loadKeys(): Promise<Keys | undefined> {
    this.keys ??= await this.ctx.storage.get<Keys>('keys');
    return this.keys;
  }

  internal(init?: RequestInit): Promise<Response> {
    const headers = new Headers(init?.headers);
    headers.set(INTERNAL_KEY_HEADER, this.keys!.internal);
    return this.ctx.container!.getTcpPort(PORT).fetch('http://container/api/internal/limits', { ...init, headers });
  }

  async storedQuota(): Promise<Response> {
    const cap = (this.env.GF_SITE_DAILY_CAP ?? '').trim().toLowerCase();
    if (['', 'none', 'off'].includes(cap)) return fail(404, 'no_limit');
    const saved = await this.ctx.storage.get<SavedCount>('siteCount');
    const day = today(), limit = Number(cap);
    const used = saved?.day === day ? saved.site : 0;
    const tomorrow = new Date(`${day}T00:00:00Z`);
    tomorrow.setUTCDate(tomorrow.getUTCDate() + 1);
    return Response.json({ left: Math.max(0, limit - used), limit, resets_at: tomorrow.toISOString().replace('.000Z', 'Z') }, { headers: NO_STORE });
  }

  // The site-wide daily counts live in the container's memory while it runs, and in this Durable
  // Object's storage across sleeps and restarts, so they hold for the whole UTC day. The per-visitor
  // counts are not persisted: they are keyed by a hashed IP whose key is never stored.
  restored = false;
  lastSaved = '';

  async saveCount(): Promise<void> {
    // Before the saved count is back in the container, its count is a fresh 0: never store that.
    if (!this.restored || !this.keys) return;
    try {
      const r = await this.internal();
      if (!r.ok) { console.error('could not save the daily count', r.status); return; }
      const count = await r.json<SavedCount>(), text = JSON.stringify(count);
      if (text === this.lastSaved) return;  // write only when it changes
      await this.ctx.storage.put('siteCount', count);
      this.lastSaved = text;
      console.log('saved daily count', text);
    } catch (error) {
      console.error('could not save the daily count', error);
    }
  }

  async restoreCount(): Promise<void> {
    const saved = await this.ctx.storage.get<SavedCount>('siteCount');
    if (saved) {
      const r = await this.internal({ method: 'POST', body: JSON.stringify(saved), headers: { 'content-type': 'application/json' } });
      // Never block reading on this: log it and try again on the next request (encodes wait for it).
      if (!r.ok) { console.error('could not restore the daily count', r.status); return; }
      console.log('restored daily count', JSON.stringify(saved), '->', await r.text());
    } else console.log('no saved daily count to restore');
    this.restored = true;
  }

  async startAndWait(): Promise<void> {
    const container = this.ctx.container!;
    if (!container.running) {
      this.restored = false;
      // Fresh secrets for every start, kept in this Durable Object's storage so they survive an
      // eviction of the object while the container keeps running.
      this.keys = { engine: randomKey(), internal: randomKey() };
      await this.ctx.storage.put('keys', this.keys);
      const env: Record<string, string> = {
        GF_SITE_DAILY_CAP: this.env.GF_SITE_DAILY_CAP,
        GF_VISITOR_DAILY_CAP: this.env.GF_VISITOR_DAILY_CAP,
        GF_DECODE_SITE_DAILY_CAP: this.env.GF_DECODE_SITE_DAILY_CAP,
        GF_DECODE_VISITOR_DAILY_CAP: this.env.GF_DECODE_VISITOR_DAILY_CAP,
        GF_ENCODE_TIMEOUT_S: this.env.GF_ENCODE_TIMEOUT_S,
        GF_ENGINE_KEY: this.keys.engine,
        GF_INTERNAL_KEY: this.keys.internal,
      };
      // No Internet access: the checkpoints are baked into the image and Turnstile is checked in
      // the Worker, so the engine never makes an outbound call.
      container.start({ image: container.images.base, instance: INSTANCE, enableInternet: false, env });
    } else {
      await this.loadKeys();
    }
    await container.setInactivityTimeout(INACTIVITY_TIMEOUT_MS);
    const port = container.getTcpPort(PORT);
    const deadline = Date.now() + READY_TIMEOUT_MS;
    let lastError: unknown;
    while (Date.now() < deadline) {
      try {
        const response = await port.fetch('http://container/api/status', { signal: AbortSignal.timeout(2000) });
        await response.body?.cancel();
        // Before the first encode reaches a fresh container, give it today's saved count.
        if (response.ok) { if (!this.restored && this.keys) await this.restoreCount(); return; }
        lastError = new Error(`status returned ${response.status}`);
      } catch (error) {
        lastError = error;
      }
      await scheduler.wait(250);
    }
    throw new Error(`engine not ready on port ${PORT}`, { cause: lastError });
  }
}

async function api(request: Request, env: Env): Promise<Response> {
  const url = new URL(request.url);
  const route = apiRoute(request.method, url.pathname);
  if (!route) return fail(404, 'not_found');  // unknown paths never wake the engine
  const ip = request.headers.get('cf-connecting-ip');
  const limiter = request.method === 'POST' ? env.GF_POST_LIMIT : env.GF_API_LIMIT;
  const { success } = await limiter.limit({ key: visitorKey(ip ?? 'unknown') });
  if (!success) return fail(429, 'rate_limited');
  if (route === 'encode' || route === 'decode') {
    const problem = uploadProblem(request.headers);
    if (problem) return fail(...problem);
    const verdict = await verifyTurnstile({
      token: request.headers.get('cf-turnstile-response'), secret: env.GF_TURNSTILE_SECRET,
      ip, hostname: url.hostname, action: route,
    });
    if (verdict === 'unavailable') console.error('turnstile unavailable', env.GF_TURNSTILE_SECRET ? 'siteverify failed' : 'no secret');
    if (verdict !== 'ok') return verdict === 'failed' ? fail(403, 'bot_check') : fail(503, 'bot_check_unavailable');
  }
  const forwarded = new Request(request);
  forwarded.headers.delete(ENGINE_KEY_HEADER);
  forwarded.headers.delete(INTERNAL_KEY_HEADER);
  forwarded.headers.delete('cf-turnstile-response');
  return env.ENGINE.getByName('engine').fetch(forwarded);
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    if (isApiPath(new URL(request.url).pathname)) return api(request, env);
    return env.ASSETS.fetch(request);
  },
} satisfies ExportedHandler<Env>;
