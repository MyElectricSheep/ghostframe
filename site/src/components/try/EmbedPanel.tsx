import React from 'react';
import { S } from '../../lib/style';
import type { TryItView } from './view';

export function EmbedPanel({ v }: { v: TryItView }) {
  const { t4Dots, t4MedLx, t4MedLy, t4MedX, t4MedY, wAlx, wAly, wArc, wAx, wAy, wBlx, wBly, wBx, wBy, wC, wCap, wCos, wDeg, wDegLeft, wDegTop, wDialAria, wDim, wHeadline, wMax, wMed, wModeLabel, wModel, wR } = v;
  return (
<>
          <div style={S({ display: 'flex', flexDirection: 'column', gap: '10px', padding: '14px', border: '1px solid rgba(24,20,17,0.10)', borderRadius: '8px', background: '#fff' })}>
            <div style={S({ display: 'flex', flexDirection: 'column', gap: '2px' })}>
              <span style={S({ font: '500 11.5px/1.3 \'IBM Plex Mono\',ui-monospace,monospace', color: '#625c57' })}>tile r{wR} c{wC}</span>
              <span style={S({ fontSize: '14.5px', fontWeight: '600' })}>{wHeadline}</span>
            </div>
            <div style={S({ position: 'relative', width: '220px', height: '190px' })}>
              <svg width="220" height="190" viewBox="0 0 220 190" role="img" aria-label={wDialAria} style={S({ display: 'block' })}>
                <line x1="20" y1="175" x2="200" y2="175" stroke="rgba(24,20,17,0.12)" strokeWidth="1" />
                <path d={wArc} fill="none" stroke="#3f648c" strokeWidth="1.5" strokeDasharray="3 3" />
                <line x1="20" y1="175" x2={wBx} y2={wBy} stroke="#8a837c" strokeWidth="2.5" strokeLinecap="round" />
                <circle cx={wBx} cy={wBy} r="4" fill="#8a837c" />
                <line x1="20" y1="175" x2={wAx} y2={wAy} stroke="#3f648c" strokeWidth="2.5" strokeLinecap="round" />
                <circle cx={wAx} cy={wAy} r="4" fill="#3f648c" />
                <text x={wBlx} y={wBly} fontFamily="IBM Plex Mono, monospace" fontSize="11" fill="#625c57">before</text>
                <text x={wAlx} y={wAly} fontFamily="IBM Plex Mono, monospace" fontSize="11" fill="#3f648c">after</text>
              </svg>
              <span aria-hidden="true" style={S({ position: 'absolute', left: wDegLeft, top: wDegTop, font: '500 12.5px/1 \'IBM Plex Mono\',ui-monospace,monospace', background: 'rgba(255,255,255,0.85)', padding: '1px 2px' })}>{wDeg}</span>
            </div>
            <dl style={S({ margin: '0', display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '3px 10px', font: '400 12px/1.4 \'IBM Plex Mono\',ui-monospace,monospace' })}>
              <dt style={S({ color: '#625c57' })}>cosine</dt><dd style={S({ margin: '0', fontWeight: '500' })}>{wCos}</dd>
              <dt style={S({ color: '#625c57' })}>turned</dt><dd style={S({ margin: '0' })}>{wDeg}, where 90° is unrelated</dd>
              <dt style={S({ color: '#625c57' })}>pixels</dt><dd style={S({ margin: '0' })}>at most {wCap}/255</dd>
              <dt style={S({ color: '#625c57' })}>all tiles</dt><dd style={S({ margin: '0' })}>median {wMed}°, most {wMax}°</dd>
                  <dt style={S({ color: '#625c57' })}>model</dt><dd style={S({ margin: '0' })}>read by {wModel}</dd>
            </dl>
            <details style={S({ borderTop: '1px solid rgba(24,20,17,0.10)' })}>
              <summary style={S({ listStyle: 'none', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px', padding: '10px 0 2px', fontSize: '13px', fontWeight: '600', cursor: 'pointer' })}>What the angle means<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#625c57" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="m6 9 6 6 6-6" /></svg></summary>
              <div style={S({ display: 'flex', flexDirection: 'column', gap: '6px', paddingTop: '8px' })}>
                <p style={S({ margin: '0', fontSize: '12.5px', lineHeight: '1.55' })}>The model describes each tile with a list of numbers, its embedding: {wDim} for {wModeLabel}, read by {wModel}. Think of those numbers as an arrow: tiles that look alike to the model point in similar directions. The angle is how differently the model now describes the same tile. 0° would mean no change; 90° would mean an unrelated description.</p>
                <p style={S({ margin: '0', fontSize: '12.5px', lineHeight: '1.55' })}>Here the pixels moved by at most {wCap}/255, yet this tile’s arrow turned {wDeg}. The hidden bits are read from the direction the arrow now points.</p>
              </div>
            </details>
          </div>
          <div style={S({ display: 'flex', flexDirection: 'column', gap: '6px', padding: '14px 0 12px', border: '1px solid rgba(24,20,17,0.10)', borderRadius: '8px', background: '#fff', overflow: 'hidden' })}>
            <div style={S({ display: 'flex', flexDirection: 'column', gap: '2px', padding: '0 14px' })}>
              <span style={S({ fontSize: '13.5px', fontWeight: '600' })}>Every tile’s turn</span>
              <span style={S({ fontSize: '12px', lineHeight: '1.45', color: '#625c57' })}>Each dot is one tile. Click a dot to pick it.</span>
            </div>
            <div style={S({ position: 'relative', width: '298px', height: '170px', margin: '0 auto' })}>
            <svg width="300" height="170" viewBox="0 0 300 170" aria-hidden="true" style={S({ position: 'absolute', inset: '0', display: 'block' })}>
              <path d="M 20 160 L 280 160" stroke="rgba(24,20,17,0.15)" strokeWidth="1" />
              <path d="M 160 160 A 140 140 0 0 0 20 20" fill="none" stroke="rgba(24,20,17,0.15)" strokeWidth="1" />
              <path d="M 20 160 L 20 14" stroke="rgba(24,20,17,0.15)" strokeWidth="1" />
              <path d={`M 20 160 L ${t4MedX} ${t4MedY}`} stroke="#8a837c" strokeWidth="1" strokeDasharray="3 3" />
            </svg>
            {t4Dots.map((d, i) => (<React.Fragment key={i}>
              <button type="button" className="hit-44" aria-label={d.aria} onClick={d.onClick} style={S({ position: 'absolute', left: d.x, top: d.y, width: d.s, height: d.s, margin: d.m, padding: '0', border: d.bd, borderRadius: '50%', background: d.bg, cursor: 'pointer', zIndex: d.z })}></button>
            </React.Fragment>))}
            <span style={S({ position: 'absolute', left: '168px', top: '146px', font: '400 10px/1 \'IBM Plex Mono\',ui-monospace,monospace', color: '#625c57', whiteSpace: 'nowrap' })}>0° · unchanged</span>
            <span style={S({ position: 'absolute', left: '26px', top: '8px', font: '400 10px/1 \'IBM Plex Mono\',ui-monospace,monospace', color: '#625c57', whiteSpace: 'nowrap' })}>90° · unrelated</span>
            <span style={S({ position: 'absolute', left: t4MedLx, top: t4MedLy, font: '400 10px/1 \'IBM Plex Mono\',ui-monospace,monospace', color: '#625c57', background: '#fff', padding: '1px 2px', whiteSpace: 'nowrap' })}>median {wMed}°</span>
          </div>
          </div>
</>
  );
}
