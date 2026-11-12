// Client for the engine API (server/app.py). Passphrases only ever travel in POST bodies.
import type { ModeKey } from '../data';

export type JobState = 'queued' | 'starting' | 'encoding' | 'done' | 'refused' | 'timed_out' | 'cancelled' | 'failed';
export interface JobView {
  id: string; mode: ModeKey; state: JobState; position: number; progress: number; elapsed_s: number; slow: boolean;
  colour_conversion: string | null; sha256?: string; result_available?: boolean;
}
export type EncodeRefusal = { error: 'issue'; issue: string } | { error: 'site_limit' | 'visitor_limit' | 'bot_check' | 'message_too_long' | string };

export class ApiError extends Error {
  constructor(public body: EncodeRefusal | { error: string }, public status: number) { super(body.error); }
}

async function json<T>(r: Response): Promise<T> {
  const body = await r.json().catch(() => ({ error: 'unreachable' }));
  if (!r.ok) throw new ApiError(body, r.status);
  return body as T;
}

export async function status(): Promise<{ engine_ready: boolean; site_open: boolean; visitor_open: boolean }> {
  return json(await fetch('/api/status', { cache: 'no-store' }));
}

export async function startEncode(file: Blob, name: string, mode: ModeKey, message: string, passphrase: string, token?: string): Promise<JobView> {
  const form = new FormData();
  form.set('mode', mode); form.set('message', message); form.set('passphrase', passphrase);
  if (token) form.set('cf-turnstile-response', token);
  form.set('image', file, name);
  return json(await fetch('/api/encode', { method: 'POST', body: form }));
}

export const pollJob = async (id: string): Promise<JobView> => json(await fetch(`/api/jobs/${id}`, { cache: 'no-store' }));
export const cancelJob = async (id: string): Promise<JobView> => json(await fetch(`/api/jobs/${id}/cancel`, { method: 'POST' }));

/** The exact PNG bytes the encoder produced (the server releases them after this fetch). */
export async function fetchResult(id: string, kind: 'marked' | 'difference'): Promise<Blob> {
  const r = await fetch(`/api/jobs/${id}/${kind}.png`, { cache: 'no-store' });
  if (!r.ok) throw new ApiError({ error: 'no_result' }, r.status);
  return r.blob();
}

export type DecodeEvent =
  | { trying: ModeKey } | { nothing: ModeKey }
  | { found: true; mode: ModeKey; profile: string; bytes: number; message: string | null; message_b64: string }
  | { found: false };

/** Streams one event per mode tried; resolves when the server is done. */
export async function decode(file: Blob, name: string, passphrase: string, mode: ModeKey | 'auto', onEvent: (e: DecodeEvent) => void, token?: string) {
  const form = new FormData();
  form.set('passphrase', passphrase); form.set('mode', mode);
  if (token) form.set('cf-turnstile-response', token);
  form.set('image', file, name);
  const r = await fetch('/api/decode', { method: 'POST', body: form });
  if (!r.ok || !r.body) {
    const body = await r.json().catch(() => ({ error: 'unreachable' }));
    throw new ApiError(body, r.status);
  }
  const reader = r.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = '';
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += value;
    let nl;
    while ((nl = buffer.indexOf('\n')) >= 0) {
      const line = buffer.slice(0, nl).trim(); buffer = buffer.slice(nl + 1);
      if (line) onEvent(JSON.parse(line));
    }
  }
}
