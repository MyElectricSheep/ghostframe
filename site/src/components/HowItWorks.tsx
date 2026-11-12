import React, { useCallback, useEffect, useRef, useState } from 'react';
import { drawHow, drawHowNarrow, HOW_DUR, HOW_LABELS, HOW_NARROW_H, HOW_NARROW_W } from '../canvas/how';
import { BLUE, GRAY } from '../data';
import { prefersReducedMotion, S } from '../lib/style';
import { useNarrow } from '../hooks/useNarrow';
import { useAbbr } from './Abbr';
import { StepCards } from './HowCards';

const STEPS = [
  { who: 'sender', t: 'The passphrase locks the message.', d: 'The message is encrypted with a key made from the passphrase. Without it, the message can’t be read, as long as the passphrase is hard to guess.' },
  { who: 'sender', t: 'Error-correction bytes are added.', d: 'A few extra bytes let the reader repair a small number of wrong bits later.' },
  { who: 'sender', t: 'The photo is split into a grid of tiles.', d: '10 × 8 tiles for Subtle and Long, 6 × 5 for Short.' },
  { who: 'sender', t: 'Each tile is nudged until the model reads specific bits.', d: 'Pixels change by at most 2 or 8 levels out of 255. The encoder then saves the PNG, reopens it and checks it reads back.' },
  { who: 'recipient', t: 'Reading back runs the same model on each tile.', d: 'It repairs a few wrong bits, then unlocks with the passphrase. A wrong passphrase or altered message gives “No message found.”' },
];

// Below 760 px the steps are swipe cards and each animation is the phone composition.
const PHONE = '(max-width: 759.98px)';

/** Draws one frame. On phones (the card layout) the canvas is sized to its real pixels and gets the 4:5 composition;
 *  otherwise the design's 1120 × 840 drawing, scaled by CSS. */
function paint(cv: HTMLCanvasElement, img: HTMLImageElement | null, step: number, t: number) {
  const x = cv.getContext('2d')!;
  if (window.matchMedia(PHONE).matches) {
    const dpr = window.devicePixelRatio || 1, w = Math.round((cv.clientWidth || HOW_NARROW_W) * dpr), h = Math.round(w * HOW_NARROW_H / HOW_NARROW_W);
    if (cv.width !== w || cv.height !== h) { cv.width = w; cv.height = h; }
    x.setTransform(w / HOW_NARROW_W, 0, 0, h / HOW_NARROW_H, 0, 0);
    drawHowNarrow(x, img, step, t);
  } else {
    if (cv.width !== 1120 || cv.height !== 840) { cv.width = 1120; cv.height = 840; }
    x.setTransform(1, 0, 0, 1, 0, 0);
    drawHow(x, img, step, t);
  }
}

/** Five 7–9 s step animations. Autoplays once when scrolled into view; static frames under reduced motion. */
function useHowAnimation() {
  const narrow = useNarrow();
  const howRef = useRef<HTMLCanvasElement>(null), howBarRef = useRef<HTMLDivElement>(null), sectionRef = useRef<HTMLElement>(null);
  const img = useRef<HTMLImageElement | null>(null), raf = useRef(0), playing = useRef(false), secShown = useRef(-1), last = useRef({ s: 0, t: 1 });
  const [step, setStep] = useState(0), [done, setDone] = useState(false), [sec, setSec] = useState(0);
  const stepRef = useRef(0);
  const start = useCallback((s: number) => {
    cancelAnimationFrame(raf.current);
    const reduced = prefersReducedMotion(), dur = HOW_DUR[s], t0 = performance.now();
    playing.current = true;
    const frame = (now: number) => {
      const cv = howRef.current; if (!cv) { raf.current = requestAnimationFrame(frame); return; }
      const t = reduced ? 1 : Math.min(1, (now - t0) / dur);
      last.current = { s, t };
      paint(cv, img.current && img.current.complete ? img.current : null, s, t);
      if (howBarRef.current) howBarRef.current.style.width = (t * 100) + '%';
      const n = Math.round(t * dur / 1000); if (n !== secShown.current) { secShown.current = n; setSec(n); }
      if (t < 1) raf.current = requestAnimationFrame(frame); else { playing.current = false; setDone(true); }
    };
    stepRef.current = s; setStep(s); setDone(false);
    raf.current = requestAnimationFrame(frame);
  }, []);
  useEffect(() => {
    const im = new Image(); img.current = im;
    im.onload = () => { if (!playing.current && howRef.current) paint(howRef.current, im, last.current.s, last.current.t); };
    im.src = '/demo-photos/antonello-portrait-of-a-man.jpg';
    let seen = false;
    const io = new IntersectionObserver((en) => { if (en.some((e) => e.isIntersecting) && !seen) { seen = true; start(stepRef.current); } }, { threshold: 0.35 });
    if (sectionRef.current) io.observe(sectionRef.current);
    const first = window.setTimeout(() => { const cv = howRef.current; if (cv && !seen) paint(cv, null, 0, 1); }, 50);
    // Redraw the current frame when the canvas changes size or crosses the phone breakpoint.
    return () => { io.disconnect(); cancelAnimationFrame(raf.current); window.clearTimeout(first); };
  }, [start]);
  // Redraw the current frame when the canvas changes size. On phones the canvas element changes with
  // the active card, so observe whichever one is mounted.
  useEffect(() => {
    const cv = howRef.current;
    if (!cv) return;
    const ro = new ResizeObserver(() => { if (!playing.current) paint(cv, img.current && img.current.complete ? img.current : null, last.current.s, last.current.t); });
    ro.observe(cv);
    return () => ro.disconnect();
  }, [step, narrow]);
  return { howRef, howBarRef, sectionRef, step, done, sec, start };
}

export function HowItWorks() {
  const { abOpen, abExp } = useAbbr();
  const { howRef, howBarRef, sectionRef, step, done, sec, start } = useHowAnimation();
  const howLabel = HOW_LABELS[step], howTime = sec + ' / ' + (HOW_DUR[step] / 1000) + ' s', howReplay = () => start(step), howAria = 'Animation: ' + HOW_LABELS[step];
  const steps = STEPS.map((f, i, a) => {
    const on = step === i;
    return { ...f, n: '0' + (i + 1), pressed: on, cardBg: on ? '#fff' : 'transparent', cardBd: on ? '#3f648c' : 'transparent', playing: on ? (done ? 'played' : 'playing') : 'play',
      onClick: () => start(i), bd: on ? BLUE : 'rgba(24,20,17,0.2)', bg: on ? BLUE : '#fff', numFg: on ? '#fff' : GRAY, line: i < a.length - 1 ? 'block' : 'none' };
  });
  const narrow = useNarrow();
  const technical = (indent: string) => (
<details style={S({ borderTop: '1px solid rgba(24,20,17,0.10)', paddingTop: '14px', marginLeft: indent })}>
            <summary style={S({ fontSize: '15px', fontWeight: '600', color: '#355574' })}>Technical detail</summary>
            <ul style={S({ margin: '12px 0 0', paddingLeft: '18px', display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '14px', lineHeight: '1.55' })}>
              <li><strong>Models:</strong> MobileNetV3-Small for Subtle and Long (<a href="https://arxiv.org/abs/1905.02244" target="_blank" rel="noopener">Howard et al., <em>Searching for MobileNetV3</em>, ICCV 2019</a>), torchvision checkpoint (sha256 <span style={S({ fontFamily: '\'IBM Plex Mono\',ui-monospace,monospace' })}>047dcff4…</span>), and <a href="https://github.com/forresti/SqueezeNet/tree/master/SqueezeNet_v1.1" target="_blank" rel="noopener">SqueezeNet 1.1</a> for Short (<a href="https://arxiv.org/abs/1602.07360" target="_blank" rel="noopener">original paper</a>), checkpoint (sha256 <span style={S({ fontFamily: '\'IBM Plex Mono\',ui-monospace,monospace' })}>b8a52dc0…</span>). Each has its own pinned calibration file. PyTorch 2.7.1 CPU, torchvision 0.22.1.</li>
              <li>Encryption: <button type="button" data-abbr="1" onClick={abOpen.AES} aria-expanded={abExp.AES} aria-controls="gf-abbr" style={S({ font: 'inherit', color: 'inherit', background: 'none', border: '0', padding: '0', margin: '0', borderBottom: '1px dashed currentColor', cursor: 'help', lineHeight: 'inherit' })}>AES-256-GCM</button>. The key is derived from the passphrase with <button type="button" data-abbr="1" onClick={abOpen.scrypt} aria-expanded={abExp.scrypt} aria-controls="gf-abbr" style={S({ font: 'inherit', color: 'inherit', background: 'none', border: '0', padding: '0', margin: '0', borderBottom: '1px dashed currentColor', cursor: 'help', lineHeight: 'inherit' })}>scrypt</button>, which makes guessing deliberately slow.</li>
              <li>Tamper evidence: if the hidden message is altered, authentication fails and the reader returns “No message found.” instead of a wrong message.</li>
              <li>The encoder is a standard optimiser. The model only reads; it never writes anything.</li>
              <li><strong>Related work.</strong> Ghostframe builds on an established idea: hide data by optimising an image so a frozen network reads it out. See <a href="https://doi.org/10.1109/wifs.2018.8630768" target="_blank" rel="noopener">Vukotić et al. (WIFS 2018)</a>, a zero-bit watermark, and <a href="https://arxiv.org/abs/1912.01487" target="_blank" rel="noopener">Ghamizi et al. (2019)</a>, who hid messages in pretrained classifiers’ outputs with adversarial attacks. <a href="https://arxiv.org/abs/2112.09581" target="_blank" rel="noopener">Fernandez et al. (ICASSP 2022)</a> used secret random “carrier” directions in a self-supervised (DINO) feature space and read bits from projection signs, which is close to what we do with public carriers. <a href="https://openreview.net/forum?id=hcMvApxGSzZ" target="_blank" rel="noopener">Kishore et al. (ICLR 2022)</a> developed it for steganography (FNNS), and <a href="https://arxiv.org/abs/2309.09700" target="_blank" rel="noopener">Luo et al., “Securing Fixed Neural Network Steganography” (ACM MM 2023)</a> added a key. What’s ours is the engineering and the testing, not the method.
                <span style={S({ display: 'flex', flexWrap: 'wrap', gap: '4px 14px', marginTop: '6px', font: '400 12px/1.5 \'IBM Plex Mono\',ui-monospace,monospace', color: '#625c57' })}><span>Also:</span><a href="https://github.com/varshakishore/FNNS" target="_blank" rel="noopener">FNNS code</a><a href="https://patents.google.com/patent/US12033233B2/en" target="_blank" rel="noopener">US patent 12,033,233 (Cornell University), “Image steganography utilizing adversarial perturbations”</a><a href="https://arxiv.org/abs/2407.11405" target="_blank" rel="noopener">Cs-FNNS follow-up (ACM MM 2024)</a></span>
              </li>
              <li>Encoding and decoding run on a server. Browser decoding hasn’t been validated.</li>
            </ul>
          </details>
  );
  return (
<section ref={sectionRef} id="how" data-screen-label="How it works" style={S({ scrollMarginTop: '56px' })}>
  <div style={S({ maxWidth: '1240px', margin: '0 auto', padding: 'clamp(40px,6vw,80px) clamp(16px,4vw,40px)', display: 'flex', flexDirection: 'column', gap: '28px' })}>
    <div style={S({ display: 'flex', flexDirection: 'column', gap: '8px', maxWidth: '46em' })}>
      <h2 style={S({ margin: '0', fontSize: 'clamp(28px,3.4vw,40px)', fontWeight: '700', letterSpacing: '-0.02em', lineHeight: '1.1' })}>How it works</h2>
      <p style={S({ margin: '0', fontSize: '16px', lineHeight: '1.55', color: '#625c57', textWrap: 'pretty' })}>A frozen, public image model, <a href="https://arxiv.org/abs/1905.02244" target="_blank" rel="noopener">MobileNetV3-Small</a> (or, <a href="https://github.com/forresti/SqueezeNet/tree/master/SqueezeNet_v1.1" target="_blank" rel="noopener">SqueezeNet 1.1</a> for Short mode) looks at the photo one tile at a time. For each tile it produces an embedding: the list of numbers the model uses to describe that tile. The encoder nudges pixels until those numbers spell out the encrypted message. The model’s weights never change. Only the pixels do.</p>
    </div>
    {narrow ? (<>
      <StepCards steps={steps} step={step} start={start} howRef={howRef} howBarRef={howBarRef} howTime={howTime} howReplay={howReplay} howAria={howAria} />
      {technical('0')}
    </>) : (
    <div style={S({ display: 'flex', flexWrap: 'wrap', gap: '32px', alignItems: 'flex-start' })}>
      <figure className="gf-how-figure" style={S({ flex: '1 1 440px', minWidth: '0', maxWidth: '600px', margin: '0', display: 'flex', flexDirection: 'column', gap: '10px' })}>
        <div style={S({ background: '#312e2b', borderRadius: '8px', padding: '10px', display: 'flex', flexDirection: 'column', gap: '8px' })}>
          <div style={S({ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px', font: '500 11px/1.3 \'IBM Plex Mono\',ui-monospace,monospace', color: '#d9d3cc' })}>
            <span style={S({ minWidth: '0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' })}>{howLabel}</span><span style={S({ flex: 'none', whiteSpace: 'nowrap' })}>{howTime}</span>
          </div>
          <div style={S({ position: 'relative', border: '3px solid #f6f4f1', lineHeight: '0', background: '#f6f4f1' })}>
            <canvas ref={howRef} width="1120" height="840" role="img" aria-label={howAria} style={S({ width: '100%', height: 'auto', display: 'block' })} />
            <button type="button" onClick={howReplay} aria-label="Replay this step" style={S({ position: 'absolute', top: '10px', right: '10px', display: 'flex', alignItems: 'center', gap: '6px', padding: '7px 11px 7px 9px', border: '0', borderRadius: '999px', background: 'rgba(18,16,14,0.82)', color: '#fff', font: '600 12.5px/1 Inter,sans-serif', cursor: 'pointer' })} className="hover-pill">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M3 12a9 9 0 1 0 3-6.7" /><path d="M3 3v6h6" /></svg>Replay
            </button>
            <div aria-hidden="true" style={S({ position: 'absolute', left: '0', right: '0', bottom: '0', height: '4px', background: 'rgba(18,16,14,0.10)' })}><div ref={howBarRef} style={S({ height: '100%', width: '0%', background: '#3f648c' })}></div></div>
          </div>
        </div>
        <figcaption style={S({ fontSize: '12px', lineHeight: '1.5', color: '#625c57', textWrap: 'pretty' })}>Illustration. The message, grid sizes and pixel cap are real; the numbers inside the model are simplified.</figcaption>
      </figure>
      <ol aria-label="Steps" style={S({ flex: '1 1 420px', minWidth: '0', margin: '0', padding: '0', listStyle: 'none', display: 'flex', flexDirection: 'column' })}>
        {steps.map((f, i) => (<React.Fragment key={i}>
          <li style={S({ display: 'grid', gridTemplateColumns: '32px 1fr', gap: '14px', cursor: 'pointer' })} onClick={f.onClick}>
            <div style={S({ display: 'flex', flexDirection: 'column', alignItems: 'center' })}>
              <span style={S({ width: '30px', height: '30px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', font: '500 12px/1 \'IBM Plex Mono\',ui-monospace,monospace', border: `1.5px solid ${f.bd}`, background: f.bg, color: f.numFg, flex: 'none' })}>{f.n}</span>
              <span aria-hidden="true" style={S({ flex: '1', width: '1.5px', background: 'rgba(24,20,17,0.15)', display: f.line, minHeight: '16px' })}></span>
            </div>
            <div style={S({ padding: '0 0 14px' })}>
              <button type="button" aria-pressed={f.pressed} onClick={f.onClick} style={S({ width: '100%', display: 'flex', flexDirection: 'column', gap: '4px', padding: '10px 12px', margin: '-6px 0 0 -12px', border: `1.5px solid ${f.cardBd}`, borderRadius: '8px', background: f.cardBg, cursor: 'pointer', textAlign: 'left', color: 'rgba(18,16,14,0.96)', font: 'inherit', transition: 'background 160ms,border-color 160ms' })} className="hover-card">
                <span style={S({ display: 'flex', justifyContent: 'space-between', gap: '8px', font: '500 11px/1 \'IBM Plex Mono\',ui-monospace,monospace', color: '#625c57' })}><span>{f.who}</span><span style={S({ color: '#3f648c' })}>{f.playing}</span></span>
                <span style={S({ fontSize: '17px', fontWeight: '600', lineHeight: '1.3' })}>{f.t}</span>
                <span style={S({ fontSize: '14.5px', lineHeight: '1.55', color: '#625c57', textWrap: 'pretty' })}>{f.d}</span>
              </button>
            </div>
          </li>
        </React.Fragment>))}
        <li>
          {technical('46px')}
        </li>
      </ol>
    </div>
    )}
  </div>
</section>

  );
}
