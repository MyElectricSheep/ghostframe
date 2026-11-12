import { useLayoutEffect, useRef, useState } from 'react';
import { S } from '../../lib/style';
import type { ModeKey, PhotoKey } from '../../data';
import { ComparePanel } from './ComparePanel';
import { Controls } from './Controls';
import { DiffPanel } from './DiffPanel';
import { EmbedPanel } from './EmbedPanel';
import { Stage } from './Stage';
import { useTryItView } from './view';
import type { TryItState } from './view';

export function TryIt({ state, set, pick }: {
  state: TryItState; set: (patch: Partial<TryItState>) => void; pick: (photo: PhotoKey, mode: ModeKey) => void;
}) {
  const v = useTryItView(state, set, pick);
  // When the side panel no longer fits beside the stage, it spans the full width and lays its
  // cards out in columns (corrective pass 12). Where it wraps depends on the photo, so measure it.
  const sideRef = useRef<HTMLDivElement>(null);
  const [wrapped, setWrapped] = useState(false);
  useLayoutEffect(() => {
    const row = sideRef.current?.parentElement;
    if (!row) return;
    const check = () => {
      const stage = row.children[1] as HTMLElement, side = sideRef.current!;
      // Measure with the side panel in its side-by-side style first.
      side.dataset.measure = '1';
      const next = side.offsetTop > stage.offsetTop + 10;
      delete side.dataset.measure;
      setWrapped(next);
    };
    check();
    const ro = new ResizeObserver(check);
    ro.observe(row);
    return () => ro.disconnect();
  }, [state.photo, state.view]);
  return (
    <section id="try" data-screen-label="Try it" style={S({ maxWidth: '1240px', margin: '0 auto', padding: 'clamp(32px,4.5vw,52px) clamp(16px,4vw,40px) clamp(18px,2.5vw,26px)', scrollMarginTop: '60px' })}>
  <div style={S({ display: 'flex', flexDirection: 'column', gap: '22px' })}>
    <div style={S({ display: 'flex', flexWrap: 'wrap', alignItems: 'flex-start', justifyContent: 'space-between', gap: '16px 32px' })}>
    <div style={S({ display: 'flex', flexDirection: 'column', gap: '8px', flex: '1 1 420px', minWidth: '0', maxWidth: '46em' })}>
        <span style={S({ font: '500 11.5px/1 \'IBM Plex Mono\',ui-monospace,monospace', color: '#625c57' })}>Try it · no upload needed</span>
        <h2 style={S({ margin: '0', fontSize: 'clamp(28px,3.4vw,40px)', fontWeight: '700', letterSpacing: '-0.02em', lineHeight: '1.1' })}>Can you spot the difference?</h2>
        <p style={S({ margin: '0', fontSize: '16px', lineHeight: '1.55', color: '#625c57', textWrap: 'pretty' })}>Three photos, each with a message already hidden in it in three different ways. Compare each with its original, look at the amplified changes, and see how differently the model now describes each part of the photo.</p>
      </div>
  </div>
    {/* Same 1240 px column as every other section, so all left edges line up; the columns stay
        32 px apart. */}
    <div style={S({ display: 'flex', flexWrap: 'wrap', gap: '24px 32px', alignItems: 'flex-start', justifyContent: 'flex-start' })}>
      <Controls v={v} />
      <Stage v={v} />
      <div ref={sideRef} className={wrapped ? 'gf-side gf-side-wrapped' : 'gf-side'} style={S({ flex: '1 1 300px', maxWidth: '440px', minWidth: '280px', display: 'flex', flexDirection: 'column', gap: '12px' })}>
        {v.wEmbed && <EmbedPanel v={v} />}
        {v.wCompare && <ComparePanel v={v} />}
        {v.wDiffOn && <DiffPanel v={v} />}
      </div>
    </div>
  </div>
    </section>
  );
}
