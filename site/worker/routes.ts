// Pure request rules for the Worker (no Cloudflare APIs), so they can be tested with plain Node:
// npm run test:worker.

export type ApiRoute = 'status' | 'quota' | 'encode' | 'decode' | 'job' | 'cancel' | 'result';

// Every /api request the engine serves, and nothing else. Job ids are uuid4().hex.
const ROUTES: [method: string, path: RegExp, route: ApiRoute][] = [
  ['GET', /^\/api\/status$/, 'status'],
  ['GET', /^\/api\/quota$/, 'quota'],
  ['POST', /^\/api\/encode$/, 'encode'],
  ['POST', /^\/api\/decode$/, 'decode'],
  ['GET', /^\/api\/jobs\/[0-9a-f]{32}$/, 'job'],
  ['POST', /^\/api\/jobs\/[0-9a-f]{32}\/cancel$/, 'cancel'],
  ['GET', /^\/api\/jobs\/[0-9a-f]{32}\/(?:marked|difference)\.png$/, 'result'],
];

export const isApiPath = (pathname: string) => pathname === '/api' || pathname.startsWith('/api/');

/** The engine route for a request, or null (answer 404 without waking the engine). `pathname` is
 *  the raw, still percent-encoded path from `new URL(request.url)`: any '%' is refused, so an
 *  encoded slash (/api/internal%2Flimits) can never be decoded into another route further on. */
export function apiRoute(method: string, pathname: string): ApiRoute | null {
  if (pathname.includes('%')) return null;
  for (const [m, path, route] of ROUTES) if (m === method && path.test(pathname)) return route;
  return null;
}

/** True if a path names the engine's internal route in any spelling or encoding. */
export function mentionsInternal(pathname: string): boolean {
  let path = pathname;
  for (let i = 0; i < 4; i++) {
    let next: string;
    try {
      next = decodeURIComponent(path);
    } catch {
      return true;  // undecodable: treat as hostile
    }
    if (next === path) break;
    path = next;
  }
  return path.includes('%') || /\/api\/+internal/i.test(path.replace(/\\/g, '/'));
}

// The largest upload the engine accepts (server/inputs.py MAX_UPLOAD) plus 1 MiB for the multipart
// framing and the text fields: the same limit as server/app.py MAX_BODY.
export const MAX_UPLOAD = 40 * 1024 * 1024;
export const MAX_BODY = MAX_UPLOAD + 1024 * 1024;

/** Body checks for encode and decode, before anything is forwarded: null, or [status, error code]. */
export function uploadProblem(headers: Headers): [number, string] | null {
  const type = (headers.get('content-type') ?? '').split(';', 1)[0].trim().toLowerCase();
  if (type !== 'multipart/form-data') return [415, 'bad_request'];
  const length = headers.get('content-length');
  if (length === null) return [411, 'bad_request'];
  if (!/^\d{1,12}$/.test(length)) return [400, 'bad_request'];
  if (Number(length) > MAX_BODY) return [413, 'too_large'];
  return null;
}

function ipv6Groups(address: string): number[] | null {
  let s = address.toLowerCase().split('%', 1)[0];
  let v4: number[] = [];
  const dotted = s.match(/(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/);
  if (dotted) {
    const p = dotted.slice(1).map(Number);
    if (p.some((x) => x > 255)) return null;
    v4 = [(p[0] << 8) | p[1], (p[2] << 8) | p[3]];
    s = s.slice(0, -dotted[0].length);
    if (s.endsWith(':') && !s.endsWith('::')) s = s.slice(0, -1);
  }
  const halves = s.split('::');
  if (halves.length > 2) return null;
  const parse = (h: string) => (h ? h.split(':').map((g) => (/^[0-9a-f]{1,4}$/.test(g) ? parseInt(g, 16) : NaN)) : []);
  const head = parse(halves[0]);
  const tail = halves.length === 2 ? [...parse(halves[1]), ...v4] : [];
  const groups = halves.length === 2 ? head : [...head, ...v4];
  if ([...groups, ...tail].some(Number.isNaN)) return null;
  if (halves.length === 2) {
    const fill = 8 - groups.length - tail.length;
    if (fill < 1) return null;
    return [...groups, ...new Array<number>(fill).fill(0), ...tail];
  }
  return groups.length === 8 ? groups : null;
}

/** The key a visitor is counted under: IPv4 as is, IPv6 cut to its /64 (as server/jobs.py does). */
export function visitorKey(address: string): string {
  const ip = address.trim();
  if (!ip.includes(':')) return ip;
  const g = ipv6Groups(ip);
  if (!g) return ip;
  if (g.slice(0, 5).every((x) => x === 0) && g[5] === 0xffff) return `${g[6] >> 8}.${g[6] & 255}.${g[7] >> 8}.${g[7] & 255}`;
  return g.slice(0, 4).map((x) => x.toString(16)).join(':') + '::/64';
}

export interface TurnstileCheck {
  token: string | null;
  secret: string | undefined;
  ip: string | null;
  hostname: string;
  action: string;
}

const SITEVERIFY = 'https://challenges.cloudflare.com/turnstile/v0/siteverify';

/** Turnstile siteverify, failing closed: 'ok', 'failed' (403 bot_check) or 'unavailable' (503: no
 *  secret configured, or siteverify could not be reached or answered something unreadable). */
export async function verifyTurnstile(check: TurnstileCheck, fetcher: typeof fetch = fetch): Promise<'ok' | 'failed' | 'unavailable'> {
  if (!check.secret) return 'unavailable';
  if (!check.token || check.token.length > 2048) return 'failed';
  const form = new FormData();
  form.set('secret', check.secret);
  form.set('response', check.token);
  if (check.ip) form.set('remoteip', check.ip);
  let outcome: { success?: unknown; hostname?: unknown; action?: unknown };
  try {
    const r = await fetcher(SITEVERIFY, { method: 'POST', body: form, signal: AbortSignal.timeout(10_000) });
    if (!r.ok) return 'unavailable';
    outcome = await r.json();
  } catch {
    return 'unavailable';
  }
  if (outcome?.success !== true) return 'failed';
  if (outcome.hostname !== check.hostname) return 'failed';
  if (outcome.action !== check.action) return 'failed';
  return 'ok';
}
