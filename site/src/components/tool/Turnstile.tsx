import { useEffect, useRef } from 'react';

// Cloudflare Turnstile, rendered only when VITE_TURNSTILE_SITEKEY is set at build time. The
// Worker verifies the token (GF_TURNSTILE_SECRET), including its action ('encode' or 'decode'),
// before the upload reaches the engine. Without a site key nothing renders (local development,
// where the engine runs without the Worker and has no bot check).
const SITE_KEY = import.meta.env.VITE_TURNSTILE_SITEKEY as string | undefined;
export const turnstileEnabled = !!SITE_KEY;

interface TurnstileApi {
  render: (el: HTMLElement, opts: Record<string, unknown>) => string;
  reset: (id: string) => void;
  remove: (id: string) => void;
}
declare global { interface Window { turnstile?: TurnstileApi } }

let script: Promise<void> | null = null;
function loadScript() {
  script ??= new Promise((resolve, reject) => {
    const s = document.createElement('script');
    s.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';
    s.async = true; s.onload = () => resolve(); s.onerror = reject;
    document.head.appendChild(s);
  });
  return script;
}

/** Tokens are single-use: change `resetKey` after each request to get a fresh one. */
export function Turnstile({ onToken, action, resetKey = 0 }: { onToken: (token: string | null) => void; action: 'encode' | 'decode'; resetKey?: number }) {
  const el = useRef<HTMLDivElement>(null), id = useRef<string | null>(null);
  useEffect(() => {
    if (!SITE_KEY) return;
    let gone = false;
    loadScript().then(() => {
      if (gone || !el.current || !window.turnstile) return;
      id.current = window.turnstile.render(el.current, {
        sitekey: SITE_KEY, action, size: 'flexible', appearance: 'always',
        callback: (t: string) => onToken(t), 'expired-callback': () => onToken(null), 'error-callback': () => onToken(null),
      });
    }).catch(() => onToken(null));
    return () => { gone = true; if (id.current && window.turnstile) window.turnstile.remove(id.current); id.current = null; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => { if (resetKey && id.current && window.turnstile) { onToken(null); window.turnstile.reset(id.current); } }, [resetKey, onToken]);
  if (!SITE_KEY) return null;
  return <div ref={el} style={{ minHeight: 65, minWidth: 0 }} />;
}
