import React from 'react';
import { S } from '../../lib/style';
import type { TryItView } from './view';

export function Controls({ v }: { v: TryItView }) {
  const { wCovers, wModeList, wViewList } = v;
  return (
<>
              <div style={S({ display: 'flex', flexDirection: 'column', gap: '18px', width: '164px', flex: 'none' })}>
          <div role="group" aria-label="Cover" style={S({ display: 'flex', flexDirection: 'column', gap: '6px' })}>
            <span style={S({ font: '500 10.5px/1 \'IBM Plex Mono\',ui-monospace,monospace', color: '#625c57' })}>01 · cover</span>
            {wCovers.map((c, i) => (<React.Fragment key={i}>
              <button type="button" aria-pressed={c.pressed} onClick={c.onClick} style={S({ display: 'flex', alignItems: 'center', gap: '8px', padding: '3px 8px 3px 3px', borderRadius: '4px', border: `1.5px solid ${c.bd}`, background: c.bg, cursor: 'pointer', color: 'rgba(18,16,14,0.96)' })}>
                <img src={c.src} alt="" style={S({ width: '36px', height: '30px', objectFit: 'cover', objectPosition: c.pos, borderRadius: '2px', display: 'block', flex: 'none' })} />
                <span style={S({ fontSize: '12.5px', fontWeight: '600' })}>{c.label}</span>
              </button>
            </React.Fragment>))}
          </div>
          <div role="radiogroup" aria-label="Mode" style={S({ display: 'flex', flexDirection: 'column', gap: '6px' })}>
            <span style={S({ font: '500 10.5px/1 \'IBM Plex Mono\',ui-monospace,monospace', color: '#625c57' })}>02 · mode</span>
            <span style={S({ fontSize: '11px', lineHeight: '1.4', color: '#625c57' })}>How much data the message can hold, and how much the pixels may change.</span>
            {wModeList.map((m, i) => (<React.Fragment key={i}>
              <div onMouseEnter={m.onEnter} onMouseLeave={m.onLeave} style={S({ position: 'relative' })}>
                <button type="button" role="radio" aria-checked={m.pressed} aria-describedby={m.tipId} onClick={m.onClick} onFocus={m.onEnter} onBlur={m.onLeave} style={S({ width: '100%', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '6px', padding: '8px', borderRadius: '4px', border: `1.5px solid ${m.bd}`, background: m.bg, cursor: 'pointer', color: 'rgba(18,16,14,0.96)' })}>
                  <span style={S({ display: 'flex', alignItems: 'center', gap: '6px' })}><span style={S({ fontSize: '13px', fontWeight: '600' })}>{m.label}</span><span aria-hidden="true" style={S({ width: '14px', height: '14px', borderRadius: '50%', border: '1.25px solid #8a837c', color: '#625c57', font: '600 9px/12px Inter,sans-serif', textAlign: 'center', boxSizing: 'border-box', display: 'block' })}>i</span></span>
                  <span style={S({ font: '400 10px/1 \'IBM Plex Mono\',ui-monospace,monospace', color: '#625c57' })}>{m.bytes} B · ≤{m.cap}</span>
                </button>
                <div id={m.tipId} role="tooltip" style={S({ position: 'absolute', left: 'calc(100% + 10px)', top: '50%', transform: 'translateY(-50%)', width: '230px', padding: '10px 12px', background: '#312e2b', color: '#f6f4f1', borderRadius: '6px', boxShadow: '0 4px 14px rgba(0,0,0,0.18)', zIndex: '20', display: m.tipDisp, flexDirection: 'column', gap: '6px', pointerEvents: 'none' })}>
                  <span aria-hidden="true" style={S({ position: 'absolute', left: '-5px', top: '50%', marginTop: '-5px', width: '10px', height: '10px', background: '#312e2b', transform: 'rotate(45deg)', display: 'block' })}></span>
                  <span style={S({ fontSize: '13px', fontWeight: '700' })}>{m.label}</span>
                  <span style={S({ fontSize: '12px', lineHeight: '1.5', textWrap: 'pretty' })}>{m.tip}</span>
                  <span style={S({ font: '400 10.5px/1.4 \'IBM Plex Mono\',ui-monospace,monospace', color: '#d9d3cc' })}>up to {m.max} bytes · ≤{m.cap}/255 · {m.grid} tiles{m.status}</span>
                </div>
              </div>
            </React.Fragment>))}
          </div>
          <div role="radiogroup" aria-label="View" style={S({ display: 'flex', flexDirection: 'column', gap: '4px' })}>
            <span style={S({ font: '500 10.5px/1 \'IBM Plex Mono\',ui-monospace,monospace', color: '#625c57' })}>03 · view</span>
            {wViewList.map((vv, i) => (<React.Fragment key={i}>
              <button type="button" role="radio" aria-checked={vv.pressed} onClick={vv.onClick} style={S({ display: 'flex', alignItems: 'center', gap: '8px', padding: '7px 8px', borderRadius: '4px', border: '0', background: vv.bg, cursor: 'pointer', color: 'rgba(18,16,14,0.96)', textAlign: 'left' })}>
                <span style={S({ width: '12px', height: '12px', borderRadius: '50%', border: `2px solid ${vv.dotBd}`, background: vv.dot, boxSizing: 'border-box', display: 'block', flex: 'none' })}></span>
                <span style={S({ fontSize: '12.5px', fontWeight: vv.weight })}>{vv.label}</span>
              </button>
            </React.Fragment>))}
          </div>
        </div>
</>
  );
}
