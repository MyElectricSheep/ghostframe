// Try it on phones: a summary line above the photo opens a bottom sheet for photo
// and mode, and a Compare · Difference · Model switch sits under the photo. Visibility turns on at
// once when opening (so focus can move in) and off only after the slide when closing.
import { useRef, useState } from 'react';
import { useOverlay } from '../../hooks/useOverlay';
import { BLUE } from '../../data';
import { S } from '../../lib/style';
import type { TryItView } from './view';

const SHORT: Record<string, string> = { 'Original vs encoded': 'Compare', 'Amplified difference': 'Difference', 'What the model sees': 'Model' };
const capText = (m: { max: number; cap: number }) => 'up to ' + m.max + ' B · ≤ ' + m.cap + '/255';

export function usePhoneControls(v: TryItView) {
  const [open, setOpen] = useState(false);
  const summary = useRef<HTMLButtonElement>(null), sheet = useRef<HTMLDivElement>(null);
  const close = () => setOpen(false);
  useOverlay(open, close, sheet, summary);
  const P = v.wCovers.find((c) => c.pressed) ?? v.wCovers[0], M = v.wModeList.find((m) => m.pressed) ?? v.wModeList[0];

  const summaryButton = (
    <button ref={summary} type="button" onClick={() => setOpen(true)} aria-haspopup="dialog" aria-expanded={open} style={S({ display: 'flex', alignItems: 'center', gap: '10px', padding: '8px 10px 8px 8px', minHeight: '56px', border: '1px solid rgba(24,20,17,0.14)', borderRadius: '8px', background: '#fff', textAlign: 'left', color: 'rgba(18,16,14,0.96)', cursor: 'pointer' })}>
      <img src={P.src} alt="" style={S({ width: '40px', height: '40px', objectFit: 'cover', objectPosition: P.pos, borderRadius: '4px', display: 'block', flex: 'none' })} />
      <span style={S({ display: 'flex', flexDirection: 'column', gap: '3px', flex: '1', minWidth: '0' })}><span style={S({ fontSize: '14.5px', fontWeight: '600' })}>{P.label} · {M.label}</span><span style={S({ font: '500 11px/1.3 \'IBM Plex Mono\',ui-monospace,monospace', color: '#625c57' })}>{capText(M)}</span></span>
      <span style={S({ fontSize: '14px', fontWeight: '600', color: '#3f648c' })}>Change</span>
    </button>
  );

  const viewSwitch = (
    <div role="radiogroup" aria-label="View" style={S({ display: 'grid', gridTemplateColumns: 'repeat(3,minmax(0,1fr))', gap: '3px', background: 'rgba(24,20,17,0.07)', borderRadius: '8px', padding: '3px' })}>
      {v.wViewList.map((x) => (
        <button key={x.label} type="button" role="radio" aria-checked={x.pressed} aria-label={x.label} onClick={x.onClick} style={S({ minHeight: '44px', border: '0', borderRadius: '6px', background: x.pressed ? '#fff' : 'transparent', boxShadow: x.pressed ? '0 1px 2px rgba(18,16,14,0.16)' : 'none', color: x.pressed ? 'rgba(18,16,14,0.96)' : '#625c57', fontSize: '13.5px', fontWeight: '600', cursor: 'pointer' })}>{SHORT[x.label] ?? x.label}</button>
      ))}
    </div>
  );

  const bottomSheet = (
    <>
      <div onClick={close} aria-hidden="true" style={S({ position: 'fixed', inset: '0', zIndex: '40', background: 'rgba(18,16,14,0.38)', transition: 'opacity 240ms ease', opacity: open ? '1' : '0', pointerEvents: open ? 'auto' : 'none' })}></div>
      <div ref={sheet} role="dialog" aria-modal="true" aria-label="Photo and mode" aria-hidden={!open} style={S({ position: 'fixed', left: '0', right: '0', bottom: '0', zIndex: '41', maxHeight: '88vh', overflowY: 'auto', overscrollBehavior: 'contain', background: '#f6f4f1', borderRadius: '18px 18px 0 0', padding: '10px 16px 20px', display: 'flex', flexDirection: 'column', gap: '12px', boxShadow: '0 -10px 30px rgba(18,16,14,0.16)', transition: `transform 280ms cubic-bezier(0.22,0.61,0.36,1), visibility 0s linear ${open ? '0s' : '280ms'}`, transform: open ? 'translateY(0)' : 'translateY(105%)', visibility: open ? 'visible' : 'hidden', boxSizing: 'border-box' })}>
        <span aria-hidden="true" style={S({ alignSelf: 'center', width: '40px', height: '4px', borderRadius: '2px', background: 'rgba(24,20,17,0.20)', flex: 'none' })}></span>
        <span style={S({ font: '500 11px/1 \'IBM Plex Mono\',ui-monospace,monospace', color: '#625c57' })}>01 · photo</span>
        <div role="group" aria-label="Photo" style={S({ display: 'grid', gridTemplateColumns: 'repeat(3,minmax(0,1fr))', gap: '8px' })}>
          {v.wCovers.map((c) => (
            <button key={c.label} type="button" aria-pressed={c.pressed} data-autofocus={c.pressed ? '' : undefined} onClick={c.onClick} style={S({ display: 'flex', flexDirection: 'column', gap: '6px', padding: '4px 4px 8px', minWidth: '0', border: `1.5px solid ${c.bd}`, background: c.bg, borderRadius: '7px', color: 'rgba(18,16,14,0.96)', cursor: 'pointer' })}><img src={c.src} alt="" style={S({ width: '100%', height: '54px', objectFit: 'cover', objectPosition: c.pos, borderRadius: '4px', display: 'block' })} /><span style={S({ fontSize: '12.5px', fontWeight: '600' })}>{c.label}</span></button>
          ))}
        </div>
        <span style={S({ font: '500 11px/1.4 \'IBM Plex Mono\',ui-monospace,monospace', color: '#625c57', marginTop: '4px' })}>02 · mode · how much the message can hold, and how much the pixels may change</span>
        <div role="radiogroup" aria-label="Mode" style={S({ display: 'flex', flexDirection: 'column', border: '1px solid rgba(24,20,17,0.12)', borderRadius: '8px', overflow: 'hidden', background: '#fff' })}>
          {v.wModeList.map((m) => (
            <button key={m.label} type="button" role="radio" aria-checked={m.pressed} onClick={m.onClick} style={S({ display: 'flex', alignItems: 'flex-start', gap: '12px', padding: '12px 14px', border: '0', borderBottom: '1px solid rgba(24,20,17,0.08)', background: m.pressed ? '#f5f8fb' : '#fff', textAlign: 'left', color: 'rgba(18,16,14,0.96)', cursor: 'pointer' })}>
              <span aria-hidden="true" style={S({ flex: 'none', width: '16px', height: '16px', marginTop: '2px', borderRadius: '50%', border: m.pressed ? `5px solid ${BLUE}` : '1.5px solid #a39b93', boxSizing: 'border-box', background: '#fff' })}></span>
              <span style={S({ display: 'flex', flexDirection: 'column', gap: '3px', flex: '1', minWidth: '0' })}><span style={S({ display: 'flex', justifyContent: 'space-between', gap: '8px' })}><span style={S({ fontSize: '14.5px', fontWeight: '600' })}>{m.label}</span><span style={S({ font: '500 11px/1.4 \'IBM Plex Mono\',ui-monospace,monospace', color: '#625c57', whiteSpace: 'nowrap' })}>{capText(m)}</span></span><span style={S({ fontSize: '13px', lineHeight: '1.45', color: '#625c57' })}>{m.tip}</span></span>
            </button>
          ))}
        </div>
        <button type="button" onClick={close} style={S({ minHeight: '48px', flex: 'none', border: '0', borderRadius: '6px', background: '#3f648c', color: '#fff', fontSize: '15px', fontWeight: '600', cursor: 'pointer' })}>Show this photo</button>
      </div>
    </>
  );

  return { summaryButton, viewSwitch, bottomSheet };
}
