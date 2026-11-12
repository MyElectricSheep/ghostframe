import { Fragment, useEffect, useRef, useState } from 'react';
import { fixture, MODES, PHOTOS, rawNumbers } from '../data';
import type { ModeKey, PhotoKey } from '../data';
import { useNarrow } from '../hooks/useNarrow';
import { prefersReducedMotion, S } from '../lib/style';

type Run = { st: 'idle' } | { st: 'running' | 'done'; n: number };

/**
 * "Hidden in this photo": a recorded result. It replays the fixture's verified message with
 * embedding-like digits resolving into the text; no decode runs (keep it that way: see the
 * handoff README, "What is real, recorded or simulated"). Remount it (key) to reset.
 */
export function Reveal({ photo, mode }: { photo: PhotoKey; mode: ModeKey }) {
  const narrow = useNarrow();
  const [rv, setRv] = useState<Run>({ st: 'idle' });
  const [all, setAll] = useState(false);
  const timer = useRef<number>();
  useEffect(() => () => window.clearInterval(timer.current), []);

  const FX = fixture(photo, mode), msg = FX.message, P = PHOTOS[photo], M = MODES[mode];
  const RW = rawNumbers(photo);
  const DIG = [...(mode === 'classic' ? RW.classic : RW[mode]), ...(mode === 'classic' ? RW.u6 : RW.u10)].map((v) => Math.abs(v).toFixed(4).slice(2)).join('');
  const scr = (n: number) => msg.split('').map((ch, i) => i < n ? ch : (ch === ' ' ? ' ' : DIG[(i * 7 + n * 3) % DIG.length])).join('');

  const rvClick = () => {
    window.clearInterval(timer.current);
    if (rv.st === 'done') { setRv({ st: 'idle' }); return; }
    if (prefersReducedMotion()) { setRv({ st: 'done', n: msg.length }); return; }
    let n = 0; setRv({ st: 'running', n: 0 });
    timer.current = window.setInterval(() => {
      n++;
      if (n >= msg.length) { window.clearInterval(timer.current); setRv({ st: 'done', n: msg.length }); } else setRv({ st: 'running', n });
    }, Math.max(14, 1500 / msg.length));
  };
  const rvCtx = P.label + ' · ' + M.label;
  const rvSize = mode === 'classic' ? '26px' : mode === 'subtle' ? '19px' : '15px';
  // Before the reveal each word is a solid rounded bar of the word's width (corrective pass 24:
  // drawn, not █ glyphs, which rendered with coloured fringes).
  const rvText = rv.st === 'idle'
    ? msg.split(' ').map((w, i) => (<Fragment key={i}>{i > 0 && ' '}<span aria-hidden="true" style={S({ display: 'inline-block', width: `calc(${[...w].length} * (1ch + 0.02em) - 0.02em)`, height: '0.82em', verticalAlign: '-0.08em', background: 'rgba(18,16,14,0.96)', borderRadius: '2px' })} /></Fragment>))
    : scr(rv.n);
  const rvMaxH = (narrow && mode === 'long' && !all) ? '13em' : 'none';
  const rvCanExpand = narrow && mode === 'long' && rv.st === 'done';
  const rvExpand = () => setAll(!all), rvExpandLabel = all ? 'Show less' : 'Show all';
  const rvLabel = rv.st === 'done' ? 'Hide the message' : 'Reveal the hidden message', rvBusy = rv.st === 'running', rvDone = rv.st === 'done';
  const rvMeta = rv.st === 'done'
    ? FX.bytes + ' bytes · ' + M.profile + ' · passphrase “ghostframe public benchmark fixture” · exact match'
    : FX.bytes + ' bytes hidden · pick a cover and mode above';
  return (
<section id="reveal" data-screen-label="Reveal" style={S({ maxWidth: '1240px', margin: '0 auto', padding: '0 clamp(16px,4vw,40px) clamp(40px,6vw,64px)', scrollMarginTop: '60px' })}>
  <div style={S({ display: 'flex', flexDirection: 'column', gap: '14px', padding: 'clamp(18px,3vw,28px)', background: '#fff', border: '1px solid rgba(24,20,17,0.10)', borderRadius: '10px' })}>
    <div style={S({ display: 'flex', flexWrap: 'wrap', alignItems: 'baseline', justifyContent: 'space-between', gap: '8px 16px' })}>
      <h3 style={S({ margin: '0', fontSize: 'clamp(20px,2vw,24px)', fontWeight: '700', letterSpacing: '-0.01em', lineHeight: '1.2' })}>Hidden in this photo</h3>
      <span style={S({ font: '500 12px/1 \'IBM Plex Mono\',ui-monospace,monospace', color: '#625c57' })}>{rvCtx}</span>
    </div>
    <div role="status" aria-live="polite" style={S({ padding: '16px 18px', background: '#f6f4f1', border: '1px solid rgba(24,20,17,0.12)', borderRadius: '6px', minHeight: '28px', maxHeight: rvMaxH, overflow: 'hidden' })}>
      <span style={S({ font: `600 ${rvSize}/1.45 'IBM Plex Mono',ui-monospace,monospace`, color: 'rgba(18,16,14,0.96)', letterSpacing: '0.02em', wordBreak: 'break-word' })}>{rvText}</span>
    </div>
    <div style={S({ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '12px 16px' })}>
      <button type="button" onClick={rvClick} disabled={rvBusy} style={S({ display: 'inline-flex', alignItems: 'center', gap: '8px', fontSize: '15px', fontWeight: '600', padding: '12px 18px', minHeight: '44px', border: '0', borderRadius: '4px', background: '#3f648c', color: '#fff', cursor: 'pointer', flex: 'none' })} className="hover-primary"><svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z" /><circle cx="12" cy="12" r="3" /></svg><span>{rvLabel}</span></button>
      {rvCanExpand && (<><button type="button" onClick={rvExpand} style={S({ fontSize: '14px', fontWeight: '600', padding: '10px 4px', minHeight: '44px', background: 'none', border: '0', color: '#3f648c', cursor: 'pointer' })}>{rvExpandLabel}</button></>)}
      <span style={S({ font: '400 11.5px/1.45 \'IBM Plex Mono\',ui-monospace,monospace', color: '#625c57' })}>{rvMeta}</span>
      {rvDone && (<>
        <span style={S({ display: 'inline-flex', alignItems: 'center', gap: '5px', font: '500 10.5px/1.2 \'IBM Plex Mono\',ui-monospace,monospace', color: '#fff', padding: '3px 8px', borderRadius: '999px', background: '#312e2b', marginLeft: 'auto' })}>Recorded result</span>
      </>)}
    </div>
  </div>
</section>

  );
}
