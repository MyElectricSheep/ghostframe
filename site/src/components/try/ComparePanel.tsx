import { S } from '../../lib/style';
import type { TryItView } from './view';

export function ComparePanel({ v }: { v: TryItView }) {
  const { t5D0, t5D1, t5D2, t5Line, t5Lx, t5Ly, t5M0, t5M1, t5M2, t5MSw, t5Marked, t5Move, t5O0, t5O1, t5O2, t5OSw, t5ThumbW } = v;
  return (
<>
            <div style={S({ display: 'flex', flexDirection: 'column', gap: '12px', padding: '16px', border: '1px solid rgba(24,20,17,0.10)', borderRadius: '8px', background: '#fff' })}>
        <div style={S({ display: 'flex', flexDirection: 'column', gap: '4px' })}>
          <span style={S({ fontSize: '14px', fontWeight: '600' })}>Same photo, two files</span>
          <span style={S({ fontSize: '12.5px', lineHeight: '1.5', color: '#625c57' })}>The divider shows the untouched original on the left and the marked file on the right. Point at any spot to compare the exact colour values.</span>
        </div>
        <div onPointerDown={t5Move} onPointerMove={t5Move} style={S({ position: 'relative', lineHeight: '0', borderRadius: '4px', overflow: 'hidden', cursor: 'crosshair', alignSelf: 'center', width: t5ThumbW, touchAction: 'none' })}>
          <img src={t5Marked} alt="Marked photo. Point to inspect a pixel." style={S({ width: '100%', display: 'block' })} />
          <span aria-hidden="true" style={S({ position: 'absolute', left: t5Lx, top: t5Ly, width: '14px', height: '14px', margin: '-7px 0 0 -7px', border: '2px solid #fff', boxShadow: '0 0 0 1px rgba(18,16,14,0.7)', borderRadius: '50%', pointerEvents: 'none' })}></span>
        </div>
        <div role="table" aria-label="Colour values at the chosen pixel" style={S({ display: 'grid', gridTemplateColumns: 'auto 1fr 1fr 1fr', gap: '6px 10px', alignItems: 'center', font: '400 12px/1.2 \'IBM Plex Mono\',ui-monospace,monospace' })}>
          <span></span><span style={S({ color: '#625c57', textAlign: 'right' })}>R</span><span style={S({ color: '#625c57', textAlign: 'right' })}>G</span><span style={S({ color: '#625c57', textAlign: 'right' })}>B</span>
          <span style={S({ display: 'flex', alignItems: 'center', gap: '6px', color: '#625c57' })}><span aria-hidden="true" style={S({ width: '12px', height: '12px', borderRadius: '2px', background: t5OSw, display: 'block' })}></span>original</span><span style={S({ textAlign: 'right' })}>{t5O0}</span><span style={S({ textAlign: 'right' })}>{t5O1}</span><span style={S({ textAlign: 'right' })}>{t5O2}</span>
          <span style={S({ display: 'flex', alignItems: 'center', gap: '6px', color: '#3f648c' })}><span aria-hidden="true" style={S({ width: '12px', height: '12px', borderRadius: '2px', background: t5MSw, display: 'block' })}></span>marked</span><span style={S({ textAlign: 'right', color: '#3f648c' })}>{t5M0}</span><span style={S({ textAlign: 'right', color: '#3f648c' })}>{t5M1}</span><span style={S({ textAlign: 'right', color: '#3f648c' })}>{t5M2}</span>
          <span style={S({ color: '#625c57' })}>change</span><span style={S({ textAlign: 'right', fontWeight: '500' })}>{t5D0}</span><span style={S({ textAlign: 'right', fontWeight: '500' })}>{t5D1}</span><span style={S({ textAlign: 'right', fontWeight: '500' })}>{t5D2}</span>
        </div>
        <span style={S({ fontSize: '12px', lineHeight: '1.5', color: '#625c57' })}>{t5Line}</span>
            </div>
</>
  );
}
