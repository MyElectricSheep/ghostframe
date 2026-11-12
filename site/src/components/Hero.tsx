import { useEffect, useRef } from 'react';
import { drawHero } from '../canvas/hero';
import { prefersReducedMotion, S } from '../lib/style';

const DURATION = 10000;

/** 10 s looping ghost animation. Pauses off-screen; a static frame under reduced motion. */
function useHeroAnimation() {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const reduced = prefersReducedMotion();
    const img = new Image();
    const t0 = performance.now();
    let raf = 0, visible = true, alive = true;
    const frame = (now: number) => {
      raf = 0;
      if (!alive) return;
      const t = reduced ? 0.95 : ((now - t0) % DURATION) / DURATION;
      drawHero(canvas.getContext('2d')!, img.complete && img.naturalWidth ? img : null, t);
      if (!reduced && visible) raf = requestAnimationFrame(frame);
    };
    const io = new IntersectionObserver((entries) => {
      visible = entries.some((e) => e.isIntersecting);
      if (visible && !raf && !reduced) raf = requestAnimationFrame(frame);
    }, { threshold: 0.05 });
    io.observe(canvas);
    img.onload = () => { if (reduced) frame(performance.now()); };
    img.src = '/demo-photos/coffee-beans.jpg';
    raf = requestAnimationFrame(frame);
    return () => { alive = false; cancelAnimationFrame(raf); io.disconnect(); img.onload = null; };
  }, []);
  return ref;
}

export function Hero() {
  const heroRef = useHeroAnimation();
  return (
<section id="top" data-screen-label="Intro" style={S({ maxWidth: '1240px', margin: '0 auto', padding: 'clamp(28px,4.5vw,56px) clamp(16px,4vw,40px) clamp(20px,3vw,28px)', display: 'flex', flexWrap: 'wrap', gap: '24px 56px', alignItems: 'center' })}>
  <div style={S({ flex: '1 1 460px', minWidth: '0', display: 'flex', flexDirection: 'column', gap: '14px' })}>
    <span style={S({ font: '500 12px/1.4 \'IBM Plex Mono\',ui-monospace,monospace', color: '#625c57' })}>An experiment in embedding-based steganography</span>
    <h1 style={S({ margin: '0', fontSize: 'clamp(36px,4.8vw,56px)', fontWeight: '700', lineHeight: '1.03', letterSpacing: '-0.035em', textWrap: 'balance' })}>A secret message, hidden in plain pixels.</h1>
    <p style={S({ margin: '0', fontSize: 'clamp(16px,1.5vw,18.5px)', lineHeight: '1.5', color: '#625c57', maxWidth: '38em', textWrap: 'pretty' })}>An AI image model turns every part of a photo into a vector embedding, a list of numbers describing what it sees. Ghostframe nudges the pixels, by at most 2 or 8 levels out of 255, until those numbers spell out a short encrypted message. The same frozen model reads it back. The message is private and tamper-evident.</p>
  </div>
  <figure style={S({ flex: '1 1 380px', minWidth: '0', maxWidth: '540px', margin: '0', display: 'flex', flexDirection: 'column', gap: '8px' })}>
    <canvas ref={heroRef} width="1080" height="760" role="img" aria-label="Animation: a pixel ghost breaks into the tiles of a photo, the photo looks unchanged, then a scan reads the tiles and the ghost reassembles." style={S({ width: '100%', height: 'auto', display: 'block', borderRadius: '8px', background: '#312e2b' })} />
  </figure>
</section>

  );
}
