import React from 'react';
import { S } from '../../lib/style';
import type { TryItView } from './view';

export function DiffPanel({ v }: { v: TryItView }) {
  const { t5Amp, t5DiffSrc, t5Lx, t5Ly, t5Move, t5Patch, t5Sw, t5SwN, t5ZoomLabel } = v;
  return (
<>
            <div style={S({ display: 'flex', flexDirection: 'column', gap: '12px', padding: '16px', border: '1px solid rgba(24,20,17,0.10)', borderRadius: '8px', background: '#fff' })}>
        <div style={S({ display: 'flex', flexDirection: 'column', gap: '4px' })}>
          <span style={S({ fontSize: '14px', fontWeight: '600' })}>What changed, made visible</span>
          <span style={S({ fontSize: '12.5px', lineHeight: '1.5', color: '#625c57' })}>The changes are too small to see, so each one is multiplied by ×{t5Amp} and drawn around mid-grey. This picture is a map of the changes, not the photo.</span>
        </div>
        <div style={S({ display: 'flex', flexDirection: 'column', gap: '6px' })}>
          <div style={S({ display: 'grid', gridTemplateColumns: `repeat(${t5SwN},1fr)`, gap: '4px' })}>
            {t5Sw.map((w, i) => (<React.Fragment key={i}>
              <div style={S({ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' })}>
                <span aria-hidden="true" style={S({ width: '100%', height: '28px', borderRadius: '3px', background: w.bg, border: '1px solid rgba(24,20,17,0.12)', display: 'block' })}></span>
                <span style={S({ font: '500 11px/1 \'IBM Plex Mono\',ui-monospace,monospace' })}>{w.d}</span>
              </div>
            </React.Fragment>))}
          </div>
          <div style={S({ display: 'flex', justifyContent: 'space-between', fontSize: '11.5px', color: '#625c57' })}><span>darker = value lowered</span><span>lighter = raised</span></div>
        </div>
        <div style={S({ display: 'flex', flexDirection: 'column', gap: '6px' })}>
          <span style={S({ fontSize: '12.5px', fontWeight: '600' })}>Zoomed in: {t5ZoomLabel}</span>
          <div onPointerDown={t5Move} onPointerMove={t5Move} style={S({ display: 'flex', gap: '10px', alignItems: 'flex-start' })}>
            <div style={S({ position: 'relative', lineHeight: '0', borderRadius: '4px', overflow: 'hidden', cursor: 'crosshair', width: '110px', flex: 'none', touchAction: 'none' })}>
              <img src={t5DiffSrc} alt="Amplified difference. Point to zoom." style={S({ width: '100%', display: 'block' })} />
              <span aria-hidden="true" style={S({ position: 'absolute', left: t5Lx, top: t5Ly, width: '10px', height: '10px', margin: '-5px 0 0 -5px', border: '1.5px solid #fff', boxShadow: '0 0 0 1px rgba(18,16,14,0.7)', pointerEvents: 'none' })}></span>
            </div>
            <div role="img" aria-label="Green-channel change for a 7 by 7 patch" style={S({ display: 'grid', gridTemplateColumns: 'repeat(7,22px)', gridAutoRows: '22px', gap: '1px', background: 'rgba(24,20,17,0.12)', padding: '1px' })}>
              {t5Patch.map((c, i) => (<React.Fragment key={i}>
                <span style={S({ background: c.bg, color: c.fg, font: '500 9px/22px \'IBM Plex Mono\',ui-monospace,monospace', textAlign: 'center' })}>{c.v}</span>
              </React.Fragment>))}
            </div>
          </div>
          <span style={S({ fontSize: '11.5px', lineHeight: '1.45', color: '#625c57' })}>Numbers are the real change in the green channel at each pixel.</span>
        </div>
            </div>
</>
  );
}
