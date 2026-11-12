import React from 'react';
import { S } from '../../lib/style';
import type { TryItView } from './view';

export function Stage({ v }: { v: TryItView }) {
  const { infoBd, infoBg, infoDisp, infoFg, infoHide, infoOpenStr, infoShow, infoToggle, wAspect, wCap, wCells, wChanged, wClip, wCols, wDiff, wDiffDisp, wDiffOn, wDivider, wEmbed, wFrameL, wFrameR, wFrameRadius, wHandleDown, wKnobBlur, wKnobFocus, wKnobRing, wMarked, wMarkedDisp, wModel, wOnSplit, wOrig, wOrigDisp, wProfile, wRes, wRows, wSliderHint, wSplit, wSplitPct, wSplitText, wStageAlt, wStageMax, wStageRef, wStageW, wTagL, wTagLDisp, wTagR, wTagRBg } = v;
  return (
<>
      <div style={S({ display: 'flex', flexDirection: 'column', gap: '10px', flex: `1 1 ${wStageW}`, maxWidth: wStageMax, minWidth: '0' })}>
        <div style={S({ background: '#312e2b', borderRadius: wFrameRadius, padding: '10px', display: 'flex', flexDirection: 'column', gap: '8px' })}>
          <div style={S({ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px', font: '500 11px/1.3 \'IBM Plex Mono\',ui-monospace,monospace', color: '#d9d3cc' })}><span>{wFrameL}</span>
            <span style={S({ display: 'flex', alignItems: 'center', gap: '8px' })}>{wFrameR}
              <span onMouseEnter={infoShow} onMouseLeave={infoHide} style={S({ position: 'relative', display: 'inline-flex' })}>
                <button type="button" onClick={infoToggle} onFocus={infoShow} onBlur={infoHide} aria-label="About this file" aria-expanded={infoOpenStr} aria-describedby="gf-info" style={S({ width: '22px', height: '22px', padding: '0', borderRadius: '50%', border: `1.5px solid ${infoBd}`, background: infoBg, color: infoFg, font: '700 11px/1 Inter,sans-serif', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' })}>i</button>
                <div id="gf-info" role="tooltip" style={S({ position: 'absolute', top: 'calc(100% + 10px)', right: '-6px', width: '300px', maxWidth: 'calc(100vw - 48px)', padding: '14px 16px', background: '#fff', color: 'rgba(18,16,14,0.96)', borderRadius: '8px', boxShadow: '0 8px 24px rgba(0,0,0,0.22)', zIndex: '30', display: infoDisp, flexDirection: 'column', gap: '10px' })}>
                  <span aria-hidden="true" style={S({ position: 'absolute', top: '-5px', right: '12px', width: '10px', height: '10px', background: '#fff', transform: 'rotate(45deg)', display: 'block' })}></span>
                  <span style={S({ font: '600 13px/1.2 Inter,sans-serif' })}>About this file</span>
                  <dl style={S({ margin: '0', display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '6px 12px', padding: '0', border: '0', background: 'transparent', font: '400 12px/1.45 \'IBM Plex Mono\',ui-monospace,monospace' })}>
            <dt style={S({ color: '#625c57' })}>max change</dt><dd style={S({ margin: '0', fontWeight: '500' })}>{wCap} / 255 per channel</dd>
            <dt style={S({ color: '#625c57' })}>profile</dt><dd style={S({ margin: '0', overflowWrap: 'anywhere' })}>{wModel} <span style={S({ color: '#625c57' })}>· {wProfile}</span></dd>
            <dt style={S({ color: '#625c57' })}>this file</dt><dd style={S({ margin: '0' })}>{wChanged}</dd>
            <dt style={S({ color: '#625c57' })}>this cover</dt><dd style={S({ margin: '0' })}>{wRes}</dd>
            <dt style={S({ color: '#625c57' })}></dt><dd style={S({ margin: '0', display: 'flex' })}><span style={S({ display: 'inline-flex', alignItems: 'center', gap: '5px', font: '500 10px/1.2 \'IBM Plex Mono\',ui-monospace,monospace', color: '#fff', padding: '3px 7px', borderRadius: '999px', background: '#312e2b' })}><span aria-hidden="true" style={S({ width: '5px', height: '5px', borderRadius: '50%', background: '#fff', display: 'block' })}></span>Measured on this exact file</span></dd>
          </dl>
                </div>
              </span>
            </span></div>
          <div ref={wStageRef} style={S({ position: 'relative', aspectRatio: wAspect, background: '#4a4541', overflow: 'hidden', border: '3px solid #f6f4f1', userSelect: 'none', touchAction: 'pan-y' })}>
            <img src={wOrig} alt={wStageAlt} style={S({ position: 'absolute', inset: '0', width: '100%', height: '100%', objectFit: 'cover', display: wOrigDisp })} />
            <img src={wMarked} alt="" style={S({ position: 'absolute', inset: '0', width: '100%', height: '100%', objectFit: 'cover', display: wMarkedDisp, clipPath: `inset(0 0 0 ${wClip})` })} />
            <img src={wDiff} alt="" style={S({ position: 'absolute', inset: '0', width: '100%', height: '100%', objectFit: 'cover', display: wDiffDisp })} />
            {wEmbed && (<>
              <div role="grid" aria-label="Tiles. Choose one to see how far its embedding turned." style={S({ position: 'absolute', inset: '0', display: 'grid', gridTemplateColumns: `repeat(${wCols},1fr)`, gridTemplateRows: `repeat(${wRows},1fr)` })}>
                {wCells.map((c, i) => (<React.Fragment key={i}>
                  <button type="button" aria-label={c.aria} aria-pressed={c.pressed} onClick={c.onClick} style={S({ padding: '0', margin: '0', minWidth: '0', minHeight: '0', border: '0', borderRight: `1px solid ${c.line}`, borderBottom: `1px solid ${c.line}`, background: c.bg, boxShadow: c.sh, cursor: 'pointer', transition: 'background 200ms' })} className="hover-tile"></button>
                </React.Fragment>))}
              </div>
            </>)}
            {wDivider && (<>
              <div onPointerDown={wHandleDown} aria-hidden="true" style={S({ position: 'absolute', top: '0', bottom: '0', left: wSplitPct, width: '44px', marginLeft: '-22px', cursor: 'ew-resize', touchAction: 'none', zIndex: '2' })}>
                <div style={S({ position: 'absolute', top: '0', bottom: '0', left: '21px', width: '2px', background: '#fff', boxShadow: '0 0 0 1px rgba(18,16,14,0.35)' })}></div>
                <div style={S({ position: 'absolute', top: '50%', left: '2px', width: '40px', height: '40px', marginTop: '-20px', borderRadius: '50%', background: '#fff', boxShadow: '0 1px 4px rgba(0,0,0,0.25)', display: 'flex', alignItems: 'center', justifyContent: 'center', outline: wKnobRing, outlineOffset: '2px' })}>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="rgba(18,16,14,0.96)" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><path d="m9 18-6-6 6-6" /><path d="m15 6 6 6-6 6" /></svg>
                </div>
              </div>
              <input type="range" min="0" max="100" value={wSplit} onChange={wOnSplit} onFocus={wKnobFocus} onBlur={wKnobBlur} aria-label="Divider" aria-valuetext={wSplitText} style={S({ position: 'absolute', left: '0', top: '0', width: '1px', height: '1px', margin: '0', opacity: '0', overflow: 'hidden', pointerEvents: 'none' })} />
            </>)}
            <span style={S({ position: 'absolute', left: '8px', bottom: '8px', font: '500 11.5px/1 \'IBM Plex Mono\',ui-monospace,monospace', background: 'rgba(18,16,14,0.82)', color: '#fff', padding: '6px 8px', borderRadius: '3px', pointerEvents: 'none', zIndex: '3', display: wTagLDisp })}>{wTagL}</span>
            <span style={S({ position: 'absolute', right: '8px', bottom: '8px', font: '500 11.5px/1 \'IBM Plex Mono\',ui-monospace,monospace', background: wTagRBg, color: '#fff', padding: '6px 8px', borderRadius: '3px', pointerEvents: 'none', zIndex: '3' })}>{wTagR}</span>
            {wDiffOn && (<>
              <div aria-hidden="true" style={S({ position: 'absolute', inset: '0', border: '2px dashed #3f648c', pointerEvents: 'none' })}></div>
            </>)}
          </div>
        </div>
        
        {wEmbed && (<>
          <div style={S({ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px', textAlign: 'center' })}>
            <div aria-hidden="true" style={S({ height: '10px', width: '100%', boxSizing: 'border-box', borderRadius: '2px', background: 'linear-gradient(90deg,rgba(63,100,140,0.06),rgba(63,100,140,0.84))', border: '1px solid rgba(24,20,17,0.10)' })}></div>
            <div style={S({ display: 'flex', justifyContent: 'space-between', width: '100%', font: '400 11px/1.3 \'IBM Plex Mono\',ui-monospace,monospace', color: '#625c57' })}><span>barely turned</span><span>turned most</span></div>
            <span style={S({ fontSize: '12px', lineHeight: '1.5', color: '#625c57', textWrap: 'balance' })}>Tiles are clickable on both sides of the divider; the tint shows only on the marked side.</span>
          </div>
        </>)}
        {wSliderHint && (<>
            <span style={S({ fontSize: '12px', lineHeight: '1.5', color: '#625c57', textAlign: 'center' })}>Drag the divider, or Tab to it and use the arrow keys.</span>
          </>)}
      </div>
</>
  );
}
