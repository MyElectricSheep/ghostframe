// How it works on phones (mobile pass 8h): five swipe cards in a scroll-snap row, with numbered
// dots. Only the card in view mounts the canvas and plays its step; the others wait.
import { useEffect, useRef } from 'react';
import type { RefObject } from 'react';
import { HOW_DUR, HOW_LABELS } from '../canvas/how';
import { BLUE } from '../data';
import { prefersReducedMotion, S } from '../lib/style';

interface Step { who: string; t: string; d: string; n: string }
const CARD_W = 'min(340px, calc(100vw - 56px))', GAP = 12, PAD = 16;

export function StepCards({ steps, step, start, howRef, howBarRef, howTime, howReplay, howAria }: {
  steps: Step[]; step: number; start: (i: number) => void; howRef: RefObject<HTMLCanvasElement>; howBarRef: RefObject<HTMLDivElement>;
  howTime: string; howReplay: () => void; howAria: string;
}) {
  const row = useRef<HTMLDivElement>(null);
  const target = useRef<number | null>(null), settle = useRef(0), stepRef = useRef(step);
  stepRef.current = step;

  // The card whose left edge is nearest the snap line is the active step. While a dot's smooth
  // scroll is under way, ignore the cards it passes on the way.
  const onScroll = () => {
    const el = row.current, first = el?.firstElementChild as HTMLElement | null;
    if (!el || !first) return;
    const pitch = first.offsetWidth + GAP, end = el.scrollLeft >= el.scrollWidth - el.clientWidth - 2;
    const i = end && target.current == null ? steps.length - 1 : Math.max(0, Math.min(steps.length - 1, Math.round(el.scrollLeft / pitch)));
    if (target.current != null) { if (i !== target.current) return; target.current = null; }
    if (i !== stepRef.current) start(i);
  };
  const go = (i: number) => {
    const el = row.current, first = el?.firstElementChild as HTMLElement | null;
    if (el && first) {
      target.current = i;
      el.scrollTo({ left: i * (first.offsetWidth + GAP), behavior: prefersReducedMotion() ? 'auto' : 'smooth' });
      window.clearTimeout(settle.current);
      settle.current = window.setTimeout(() => { target.current = null; }, 900);
    }
    start(i);
  };
  useEffect(() => () => window.clearTimeout(settle.current), []);

  return (
    <div style={S({ display: 'flex', flexDirection: 'column', gap: '12px', margin: '0 calc(-1 * clamp(16px,4vw,40px))' })}>
      <div ref={row} onScroll={onScroll} role="group" aria-label="Steps" className="gf-cards" style={S({ display: 'flex', gap: GAP + 'px', overflowX: 'auto', scrollSnapType: 'x mandatory', padding: `0 ${PAD}px`, scrollPadding: `0 ${PAD}px`, overscrollBehaviorX: 'contain' })}>
        {steps.map((f, i) => {
          const on = i === step;
          return (
            <div key={f.n} role="group" aria-label={'Step ' + f.n + ' of 05'} style={S({ flex: 'none', width: CARD_W, scrollSnapAlign: 'start', scrollSnapStop: 'always', display: 'flex', flexDirection: 'column', gap: '12px', background: '#fff', border: `1px solid ${on ? 'rgba(63,100,140,0.5)' : 'rgba(24,20,17,0.12)'}`, borderRadius: '10px', padding: '8px 8px 16px', boxSizing: 'border-box' })}>
              <div style={S({ background: '#312e2b', borderRadius: '6px', padding: '6px', display: 'flex', flexDirection: 'column', gap: '6px' })}>
                <div style={S({ display: 'flex', gap: '8px', justifyContent: 'space-between', font: '500 10.5px/1.3 \'IBM Plex Mono\',ui-monospace,monospace', color: '#d9d3cc', padding: '2px 2px 0' })}><span style={S({ minWidth: '0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' })}>{HOW_LABELS[i]}</span><span style={S({ whiteSpace: 'nowrap' })}>{on ? howTime : '0 / ' + HOW_DUR[i] / 1000 + ' s'}</span></div>
                {/* 4:5, the phone composition of each step (text stays legible), not the desktop 4:3 drawing. */}
                <div style={S({ position: 'relative', border: '3px solid #f6f4f1', lineHeight: '0', background: '#f6f4f1', aspectRatio: '4 / 5' })}>
                  {on ? (<>
                    <canvas ref={howRef} width="560" height="700" role="img" aria-label={howAria} style={S({ width: '100%', height: '100%', display: 'block' })} />
                    <button type="button" onClick={howReplay} aria-label="Replay this step" style={S({ position: 'absolute', top: '8px', right: '8px', display: 'flex', alignItems: 'center', gap: '6px', padding: '7px 11px 7px 9px', minHeight: '36px', border: '0', borderRadius: '999px', background: 'rgba(18,16,14,0.82)', color: '#fff', font: '600 12.5px/1 Inter,sans-serif', cursor: 'pointer' })} className="hover-pill hit-44">
                      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M3 12a9 9 0 1 0 3-6.7" /><path d="M3 3v6h6" /></svg>Replay
                    </button>
                    <div aria-hidden="true" style={S({ position: 'absolute', left: '0', right: '0', bottom: '0', height: '4px', background: 'rgba(18,16,14,0.10)' })}><div ref={howBarRef} style={S({ height: '100%', width: '0%', background: '#3f648c' })}></div></div>
                  </>) : (
                    <div style={S({ position: 'absolute', inset: '0', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '10px', lineHeight: '1.3' })}>
                      <span style={S({ font: '500 36px/1 \'IBM Plex Mono\',ui-monospace,monospace', color: '#a39b93' })}>{f.n}</span>
                      <span style={S({ fontSize: '12.5px', color: '#625c57' })}>Plays when this card is in view</span>
                    </div>
                  )}
                </div>
              </div>
              <div style={S({ padding: '0 8px', display: 'flex', flexDirection: 'column', gap: '6px' })}>
                <span style={S({ font: '500 11px/1 \'IBM Plex Mono\',ui-monospace,monospace', color: '#625c57' })}>{f.who} · {f.n} / 05</span>
                <span style={S({ fontSize: '16.5px', fontWeight: '700', lineHeight: '1.3' })}>{f.t}</span>
                <span style={S({ fontSize: '14px', lineHeight: '1.5', color: '#625c57', textWrap: 'pretty' })}>{f.d}</span>
              </div>
            </div>
          );
        })}
        {/* Room after the last card so that card 05 can snap to the start like the others. */}
        <div aria-hidden="true" style={S({ flex: 'none', width: `calc(100% - ${CARD_W} - ${GAP}px + ${PAD}px)` })}></div>
      </div>
      <div style={S({ display: 'flex', justifyContent: 'center', gap: '6px' })}>
        {steps.map((f, i) => {
          const on = i === step;
          return <button key={f.n} type="button" onClick={() => go(i)} aria-label={'Step ' + f.n} aria-current={on ? 'step' : undefined} style={S({ width: '44px', height: '44px', border: '0', borderRadius: '50%', background: on ? BLUE : 'rgba(24,20,17,0.07)', color: on ? '#fff' : '#625c57', font: '500 11px/1 \'IBM Plex Mono\',ui-monospace,monospace', cursor: 'pointer' })}>{f.n}</button>;
        })}
      </div>
      <span style={S({ padding: `0 ${PAD}px`, fontSize: '12px', lineHeight: '1.5', color: '#625c57', textWrap: 'pretty' })}>Swipe for the next step. Illustration. The message, grid sizes and pixel cap are real; the numbers inside the model are simplified.</span>
    </div>
  );
}
