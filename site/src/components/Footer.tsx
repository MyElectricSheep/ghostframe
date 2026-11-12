import React, { useEffect } from 'react';
import { S } from '../lib/style';

/** Opens the privacy notice (a <details>) and scrolls to it; used by every "Privacy" link. */
export function openPrivacy(e?: React.MouseEvent) {
  const d = document.getElementById('privacy') as HTMLDetailsElement | null;
  if (!d) return;
  e?.preventDefault();
  d.open = true;
  d.scrollIntoView({ block: 'start' });
  history.replaceState(null, '', '#privacy');
}

const H = { margin: '0', fontSize: '12.5px', fontWeight: '600', color: 'rgba(18,16,14,0.96)' };
const P = { margin: '0' };

export function Footer() {
  useEffect(() => {
    const check = () => { if (location.hash === '#privacy') openPrivacy(); };
    check();
    window.addEventListener('hashchange', check);
    return () => window.removeEventListener('hashchange', check);
  }, []);
  return (
<footer style={S({ background: '#f6f4f1' })}>
  <div style={S({ maxWidth: '1240px', margin: '0 auto', padding: '24px clamp(16px,4vw,40px) 40px', display: 'flex', flexDirection: 'column', gap: '16px', fontSize: '12.5px', lineHeight: '1.55', color: '#625c57' })}>
    <div style={S({ display: 'flex', flexWrap: 'wrap', gap: '10px 32px', justifyContent: 'space-between' })}>
      <span style={S({ maxWidth: '36em', display: 'flex', flexDirection: 'column', gap: '4px' })}><span>Ghostframe is an engineering experiment by <a href="https://electricsheep.id" target="_blank" rel="noopener">Ben Paget</a>.</span><span>No accounts. Nothing is kept after your job. <a href="#privacy" onClick={openPrivacy}>Privacy</a></span><span>A research demo: the marks are easy to detect and the server sees what you send, so don’t use it for anything that matters.</span></span>
      <span style={S({ maxWidth: '40em' })}>Antonello da Messina, Portrait of a Man (about 1475), National Gallery, London; public-domain painting, reproduction via Wikimedia Commons. “Roasted coffee beans” by MarkSweep, public domain. “Milky Way Night Sky” by Guillaume (Unsplash), CC0. Upload sample “Wellington Railway Station, NSW Platform” by Abesty, CC0. All via Wikimedia Commons.</span>
    </div>
    <details id="privacy" style={S({ borderTop: '1px solid rgba(24,20,17,0.10)', paddingTop: '12px', maxWidth: '46em', scrollMarginTop: '56px' })}>
      <summary style={S({ fontSize: '13px', fontWeight: '600', color: '#355574', cursor: 'pointer' })}>Privacy</summary>
      <div style={S({ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '10px' })}>
        <p style={S(H)}>Who runs it</p>
        <p style={S(P)}>This demo is run by Ben Paget, an individual in the EU. Contact: <a href="mailto:ben@electricsheep.id">ben@electricsheep.id</a>.</p>
        <p style={S(H)}>What is processed, and why</p>
        <p style={S(P)}>To hide or read a message, the photo, message and passphrase you send are processed for the duration of the job. Your IP address is used for rate limits, daily caps and the bot check. The purpose is to provide the demo and protect it from abuse; the legal basis is legitimate interest (GDPR Art. 6(1)(f)).</p>
        <p style={S(H)}>How long it is kept</p>
        <p style={S(P)}>Photos, messages and passphrases stay in memory until the job ends and are never written to disk. The marked PNG and the difference image are deleted as soon as your browser fetches them; an unfetched result is deleted after 15 minutes at most. Per-visitor counts use a hash of your IP address (IPv6 by /64) with a key that changes daily and is never stored; they last until midnight UTC. The only stored records are today’s site-wide counts of encodes and reads. Cloudflare’s per-request logs are switched off; the engine’s own log lines (errors and count updates; no photos, messages or passphrases) are kept by Cloudflare for up to 7 days.</p>
        <p style={S(H)}>Who else sees it</p>
        <p style={S(P)}>Cloudflare hosts the site and the engine and runs Turnstile, the bot check, which processes your IP address and browser signals. See <a href="https://www.cloudflare.com/privacypolicy/" target="_blank" rel="noopener">Cloudflare’s privacy policy</a>. Nothing is shared with anyone else.</p>
        <p style={S(H)}>Cookies</p>
        <p style={S(P)}>The site sets no cookies and stores nothing in your browser. Turnstile may use its own, under Cloudflare’s policy.</p>
        <p style={S(H)}>Your rights</p>
        <p style={S(P)}>You can ask for access to or erasure of your data, or object to its processing, by writing to the address above, and you can complain to a data protection supervisory authority. Beyond what is listed here nothing is kept, so there is usually nothing to give back.</p>
      </div>
    </details>
  </div>
</footer>

  );
}
