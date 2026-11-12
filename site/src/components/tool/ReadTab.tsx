import React, { useRef, useState } from 'react';
import { BLUE, fixturePath, GRAY, INK, MODES, ORDER, PASS_FIXTURE } from '../../data';
import type { ModeKey } from '../../data';
import { ApiError, decode } from '../../lib/api';
import { inspect, issueOf, withDims } from '../../lib/image';
import type { FileInfo } from '../../lib/image';
import { prefersReducedMotion, S } from '../../lib/style';
import { check, dropZone, ISSUE, scrollToId } from './shared';
import { Turnstile } from './Turnstile';

type RState = 'idle' | 'running' | 'found' | 'none' | 'failed';
interface Found { message: string; bytes: number; mode: ModeKey; profile: string }

export function ReadTab() {
  const [rFile, setRFile] = useState<FileInfo | null>(null);
  const [rPass, setRPassState] = useState(''), [rShow, setRShow] = useState(false), [rMode, setRModeState] = useState<ModeKey | 'auto'>('auto');
  const [rState, setRState] = useState<RState>('idle'), [rStep, setRStep] = useState(0), [found, setFound] = useState<Found | null>(null);
  const [copied, setCopied] = useState(false), [rDrag, setRDrag] = useState(false), [ranMode, setRanMode] = useState<ModeKey | 'auto'>('auto');
  const [token, setToken] = useState<string | null>(null), [tsReset, setTsReset] = useState(0);
  const rFileRef = useRef<HTMLInputElement>(null);

  const setFile = (f: FileInfo | null) => { setRFile(withDims(f)); setRState('idle'); setCopied(false); };
  const readFile = async (file?: File) => { if (file) setFile(await inspect(file, file.name)); };
  const useSample = async () => {
    const blob = await (await fetch(fixturePath('antonello', 'classic.png'))).blob();
    setFile(await inspect(new File([blob], 'classic.png', { type: 'image/png' }), 'classic.png', true));
  };

  const list: ModeKey[] = rMode === 'auto' ? ORDER : [rMode];
  const run = async () => {
    if (!rFile?.blob) return;
    setRState('running'); setRStep(0); setCopied(false); setFound(null); setRanMode(rMode);
    scrollToId('gf-rresult');
    try {
      let hit = false;
      await decode(rFile.blob, rFile.name, rPass, rMode, (e) => {
        if ('nothing' in e) setRStep((s) => s + 1);
        if ('found' in e && e.found) {
          hit = true;
          const text = e.message ?? new TextDecoder('utf-8', { fatal: false }).decode(Uint8Array.from(atob(e.message_b64), (c) => c.charCodeAt(0)));
          setFound({ message: text, bytes: e.bytes, mode: e.mode, profile: e.profile }); setRState('found');
        }
        if ('found' in e && !e.found) setRState('none');
      }, token || undefined);
      if (!hit) setRState((s) => (s === 'running' ? 'none' : s));
    } catch (e) {
      setRState(e instanceof ApiError && e.body.error === 'issue' ? 'idle' : 'failed');
    } finally {
      setTsReset((n) => n + 1);
    }
  };

  // ---- values, named as in the design reference's renderVals()
  const rIss = issueOf(rFile, true), rf = rFile;
  const rBlock: string[] = []; if (!rf) rBlock.push('add a PNG'); else if (rIss) rBlock.push('use the original PNG'); if (!rPass) rBlock.push('enter the passphrase');
  const rDisabled = rBlock.length > 0 || rState === 'running';
  const hit = found ? MODES[found.mode] : null;
  const rDragOver = (e: React.DragEvent) => { e.preventDefault(); if (!rDrag) setRDrag(true); }, rDragLeave = () => setRDrag(false);
  const rDrop = (e: React.DragEvent) => { e.preventDefault(); setRDrag(false); readFile(e.dataTransfer.files[0]); };
  const rFileInput = (e: React.ChangeEvent<HTMLInputElement>) => { readFile(e.target.files?.[0]); e.target.value = ''; };
  const rPick = () => rFileRef.current && rFileRef.current.click(), rUseSample = useSample, rClear = () => setFile(null);
  const rDz = dropZone(rDrag, rIss, !!rf), rDzTitle = rDrag ? 'Drop to use this file' : 'Drop a PNG here';
  const rEmpty = !rf, rHasFile = !!rf, rCheck = check(rIss, rf), rIssue = !!rIss, rIssueText = rIss ? ISSUE[rIss](rf!) : '';
  const rIsSample = !!(rf && rf.sample), rFillSample = () => setRPassState(PASS_FIXTURE);
  const onRPass = (e: React.ChangeEvent<HTMLInputElement>) => setRPassState(e.target.value);
  const rPassType = rShow ? 'text' : 'password', rShowStr = rShow, rShowLabel = rShow ? 'Hide' : 'Show', toggleRPass = () => setRShow(!rShow);
  const onRMode = (e: React.ChangeEvent<HTMLSelectElement>) => { setRModeState(e.target.value as ModeKey | 'auto'); setRState('idle'); };
  const rRun = run, rBtn = { bg: rDisabled ? 'rgba(0,0,0,0.06)' : BLUE, fg: rDisabled ? '#7a736d' : '#fff', cursor: rDisabled ? 'not-allowed' : 'pointer' };
  const rBtnLabel = rState === 'running' ? 'Reading…' : 'Read the message', rBlocker = rBlock.length ? 'To continue, ' + rBlock.join(', ') + '.' : '';
  const rRunning = rState === 'running', rFound = rState === 'found' && !!found, rNone = rState === 'none';
  const reduced = prefersReducedMotion();
  const rSteps = list.map((k, i) => ({ label: 'Trying ' + MODES[k].label, status: i < rStep ? 'nothing' : i === rStep ? 'now' : '', fg: i <= rStep ? INK : GRAY, bd: i <= rStep ? BLUE : '#c9c2ba', fill: i < rStep ? '#c9c2ba' : 'transparent', anim: i === rStep && !reduced ? 'gfpulse 1s ease-in-out infinite' : 'none' }));
  const rMessage = found?.message ?? '', rFoundMeta = found && hit ? found.bytes + ' bytes · ' + hit.label + ' · ' + found.profile : '';
  const rCopy = () => { try { navigator.clipboard.writeText(rMessage); } catch { /* clipboard unavailable */ } setCopied(true); };
  const rCopyLabel = copied ? 'Copied' : 'Copy';
  const rNoneModeNote = ranMode === 'auto' ? '' : ' (you chose ' + MODES[ranMode].label + ' only)';
  const rFailed = rState === 'failed';

  return (
<>
      <div style={S({ display: 'flex', flexWrap: 'wrap', gap: '32px', alignItems: 'flex-start' })}>
        <div style={S({ flex: '1 1 380px', minWidth: '0', display: 'flex', flexDirection: 'column', gap: '8px' })}>
          <span style={S({ fontSize: '14px', fontWeight: '600' })}><span style={S({ font: '500 11.5px \'IBM Plex Mono\',ui-monospace,monospace', color: '#3f648c', marginRight: '8px' })}>01</span>Upload a PNG</span>
          <div onDragOver={rDragOver} onDragLeave={rDragLeave} onDrop={rDrop} style={S({ minHeight: '200px', borderRadius: '8px', border: `1.5px ${rDz.bs} ${rDz.bd}`, background: rDz.bg, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '10px', padding: '18px', textAlign: 'center', boxSizing: 'border-box' })}>
            <input ref={rFileRef} type="file" accept="image/png,image/jpeg" onChange={rFileInput} aria-label="Choose a PNG" style={S({ position: 'absolute', width: '1px', height: '1px', opacity: '0', pointerEvents: 'none' })} />
            {rEmpty && (<>
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#625c57" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><path d="m17 8-5-5-5 5" /><path d="M12 3v12" /></svg>
              <span style={S({ fontSize: '15px', fontWeight: '600' })}>{rDzTitle}</span>
              <span style={S({ fontSize: '13px', lineHeight: '1.5', color: '#625c57' })}>The exact PNG file you received. Screenshots and re-saved copies won’t work.</span>
              <div style={S({ display: 'flex', flexWrap: 'wrap', gap: '6px', justifyContent: 'center' })}>
                <button type="button" onClick={rPick} style={S({ fontSize: '14px', fontWeight: '600', padding: '9px 14px', minHeight: '40px', border: '1px solid rgba(63,100,140,0.22)', borderRadius: '4px', background: '#fff', color: '#355574', cursor: 'pointer' })}>Choose PNG</button>
                <button type="button" onClick={rUseSample} style={S({ fontSize: '14px', fontWeight: '600', padding: '9px 12px', minHeight: '40px', border: '0', borderRadius: '4px', background: 'transparent', color: 'rgba(18,16,14,0.96)', cursor: 'pointer', textDecoration: 'underline', textUnderlineOffset: '3px' })}>Use the portrait sample</button>
              </div>
            </>)}
            {rHasFile && (<>
              <div style={S({ display: 'flex', gap: '14px', alignItems: 'center', width: '100%', textAlign: 'left' })}>
                <img src={rFile.url} alt="Selected file" style={S({ width: '80px', height: '96px', objectFit: 'cover', borderRadius: '4px', border: '1px solid rgba(24,20,17,0.10)', display: 'block', flex: 'none' })} />
                <div style={S({ display: 'flex', flexDirection: 'column', gap: '4px', minWidth: '0', flex: '1' })}>
                  <span style={S({ fontSize: '14.5px', fontWeight: '600', wordBreak: 'break-all' })}>{rFile.name}</span>
                  <span style={S({ font: '400 12px/1.35 \'IBM Plex Mono\',ui-monospace,monospace', color: '#625c57' })}>{rFile.type} · {rFile.dims}</span>
                  <span style={S({ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', fontWeight: '600', color: rCheck.fg })}><span aria-hidden="true" style={S({ width: '14px', height: '14px', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: rCheck.radius, background: rCheck.fg, color: '#fff', fontSize: '10px', fontWeight: '700', flex: 'none' })}>{rCheck.glyph}</span>{rCheck.text}</span>
                </div>
              </div>
              {rIssue && (<>
                <p role="alert" style={S({ margin: '0', fontSize: '13.5px', lineHeight: '1.5', textAlign: 'left', width: '100%' })}>{rIssueText}</p>
              </>)}
              <div style={S({ display: 'flex', gap: '6px', alignSelf: 'flex-start' })}><button type="button" onClick={rPick} style={S({ fontSize: '13.5px', fontWeight: '600', padding: '8px 12px', minHeight: '36px', border: '0', borderRadius: '4px', background: 'rgba(0,0,0,0.05)', color: 'rgba(18,16,14,0.96)', cursor: 'pointer' })}>Replace</button><button type="button" onClick={rClear} style={S({ fontSize: '13.5px', fontWeight: '600', padding: '8px 12px', minHeight: '36px', border: '0', borderRadius: '4px', background: 'transparent', color: 'rgba(18,16,14,0.96)', cursor: 'pointer' })}>Remove</button></div>
            </>)}
          </div>
        </div>

        <div style={S({ flex: '1 1 380px', minWidth: '0', display: 'flex', flexDirection: 'column', gap: '20px' })}>
          <div style={S({ display: 'flex', flexDirection: 'column', gap: '6px' })}>
            <label htmlFor="gf-rpass" style={S({ fontSize: '14px', fontWeight: '600' })}><span style={S({ font: '500 11.5px \'IBM Plex Mono\',ui-monospace,monospace', color: '#3f648c', marginRight: '8px' })}>02</span>Enter the passphrase</label>
            <div style={S({ display: 'flex', gap: '6px' })}>
              <input id="gf-rpass" type={rPassType} value={rPass} onChange={onRPass} autoComplete="current-password" style={S({ flex: '1', minWidth: '0', fontSize: '15px', padding: '10px 12px', minHeight: '44px', boxSizing: 'border-box', border: '1px solid #dddddd', borderRadius: '4px', background: '#fff', color: 'rgba(18,16,14,0.9)' })} />
              <button type="button" onClick={toggleRPass} aria-pressed={rShowStr} style={S({ fontSize: '14px', fontWeight: '600', padding: '0 12px', minHeight: '44px', border: '0', borderRadius: '4px', background: 'rgba(0,0,0,0.05)', color: 'rgba(18,16,14,0.96)', cursor: 'pointer' })}>{rShowLabel}</button>
            </div>
            {rIsSample && (<>
              <span style={S({ fontSize: '12.5px', lineHeight: '1.5', color: '#625c57' })}>The sample uses the public passphrase <span style={S({ fontFamily: '\'IBM Plex Mono\',ui-monospace,monospace' })}>ghostframe public benchmark fixture</span>. <button type="button" onClick={rFillSample} style={S({ font: 'inherit', fontWeight: '600', color: '#3f648c', background: 'none', border: '0', padding: '0', cursor: 'pointer', textDecoration: 'underline', textUnderlineOffset: '3px' })}>Fill it in</button></span>
            </>)}
          </div>
          <div style={S({ display: 'flex', flexDirection: 'column', gap: '6px' })}>
            <label htmlFor="gf-rmode" style={S({ fontSize: '14px', fontWeight: '600' })}><span style={S({ font: '500 11.5px \'IBM Plex Mono\',ui-monospace,monospace', color: '#3f648c', marginRight: '8px' })}>03</span>Mode</label>
            <select id="gf-rmode" value={rMode} onChange={onRMode} style={S({ fontSize: '15px', padding: '10px 12px', minHeight: '44px', border: '1px solid #dddddd', borderRadius: '4px', background: '#fff', color: 'rgba(18,16,14,0.9)' })}>
              <option value="auto">Try all modes (about 6–12 s)</option>
              <option value="classic">Short · SqueezeNet 1.1 · legacy-v1</option>
              <option value="subtle">Subtle · MobileNetV3-Small · bb-mobilenet_v3_small-l2-b16p48</option>
              <option value="long">Long · MobileNetV3-Small · bb-mobilenet_v3_small-l8-b64p112</option>
            </select>
            <span style={S({ fontSize: '12.5px', color: '#625c57' })}>Choosing the mode the sender used is faster.</span>
          </div>
          <div style={S({ display: 'flex', flexDirection: 'column', gap: '10px' })}>
            <Turnstile onToken={setToken} resetKey={tsReset} />
            <div style={S({ display: 'flex', flexWrap: 'wrap', gap: '10px 14px', alignItems: 'center' })}>
              <button type="button" onClick={rRun} disabled={rDisabled} style={S({ fontSize: '15px', fontWeight: '600', padding: '12px 20px', minHeight: '44px', border: '0', borderRadius: '4px', background: rBtn.bg, color: rBtn.fg, cursor: rBtn.cursor })}>{rBtnLabel}</button>
              <span style={S({ fontSize: '13px', color: '#625c57' })}>{rBlocker}</span>
            </div>
          </div>

          <div id="gf-rresult" role="status" aria-live="polite" style={S({ scrollMarginTop: '72px' })}>
            {rRunning && (<>
              <ol style={S({ margin: '0', padding: '14px 16px', listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '10px', border: '1px solid rgba(24,20,17,0.12)', borderRadius: '8px', background: '#f6f4f1' })}>
                {rSteps.map((st, i) => (<React.Fragment key={i}>
                  <li style={S({ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '14px', color: st.fg })}>
                    <span aria-hidden="true" style={S({ width: '14px', height: '14px', borderRadius: '50%', border: `1.5px solid ${st.bd}`, background: st.fill, display: 'block', flex: 'none', animation: st.anim })}></span>
                    <span>{st.label}</span><span style={S({ font: '400 11.5px/1 \'IBM Plex Mono\',ui-monospace,monospace', color: '#625c57', marginLeft: 'auto' })}>{st.status}</span>
                  </li>
                </React.Fragment>))}
              </ol>
            </>)}
            {rFound && (<>
              <div style={S({ display: 'flex', flexDirection: 'column', gap: '12px', padding: '16px', borderRadius: '8px', background: '#f5f8fb', border: '1.5px solid #3f648c' })}>
                <span style={S({ display: 'flex', gap: '10px', alignItems: 'center', fontSize: '17px', fontWeight: '700' })}><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#3f648c" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10" /><path d="m8 12 3 3 5-6" /></svg>Message found and unlocked</span>
                <div style={S({ display: 'flex', gap: '8px', alignItems: 'stretch' })}>
                  <p style={S({ margin: '0', flex: '1', fontSize: '18px', fontWeight: '600', lineHeight: '1.4', padding: '10px 12px', background: '#fff', border: '1px solid rgba(63,100,140,0.14)', borderRadius: '4px', whiteSpace: 'pre-wrap', wordBreak: 'break-word' })}>{rMessage}</p>
                  <button type="button" onClick={rCopy} style={S({ fontSize: '14px', fontWeight: '600', padding: '0 14px', minHeight: '44px', border: '1px solid rgba(63,100,140,0.22)', borderRadius: '4px', background: '#fff', color: '#355574', cursor: 'pointer' })}>{rCopyLabel}</button>
                </div>
                <span style={S({ font: '400 12px/1.4 \'IBM Plex Mono\',ui-monospace,monospace', color: '#625c57' })}>{rFoundMeta}</span>
              </div>
            </>)}
            {rNone && (<>
              <div style={S({ display: 'flex', flexDirection: 'column', gap: '10px', padding: '16px', borderRadius: '8px', background: '#f1eee9', border: '1.5px solid rgba(18,16,14,0.55)' })}>
                <span style={S({ display: 'flex', gap: '10px', alignItems: 'center', fontSize: '17px', fontWeight: '700' })}><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="rgba(18,16,14,0.96)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10" /><path d="m4.9 4.9 14.2 14.2" /></svg>No message found.</span>
                <p style={S({ margin: '0', fontSize: '14px', lineHeight: '1.5' })}>Any of these give the same result, and the reader can’t tell which one applies:</p>
                <ul style={S({ margin: '0', paddingLeft: '18px', display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '14px', lineHeight: '1.5' })}>
                  <li>a different passphrase</li>
                  <li>a different mode{rNoneModeNote}</li>
                  <li>the file was re-saved, compressed, resized or cropped on the way</li>
                  <li>the photo never carried a message</li>
                </ul>
              </div>
            </>)}
            {rFailed && (
              // COPY NOT IN THE DESIGN: proposed wording for a server error, pending approval.
              <div style={S({ display: 'flex', flexDirection: 'column', gap: '10px', padding: '16px', borderRadius: '8px', background: '#f1eee9', border: '1.5px solid rgba(18,16,14,0.55)' })}>
                <span style={S({ fontSize: '17px', fontWeight: '700' })}>Something went wrong</span>
                <p style={S({ margin: '0', fontSize: '14px', lineHeight: '1.5' })}>The reader couldn’t finish. Try again in a minute.</p>
              </div>
            )}
          </div>
        </div>
      </div>
</>
  );
}
