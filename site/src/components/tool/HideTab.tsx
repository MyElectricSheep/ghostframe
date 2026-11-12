import React, { useCallback, useEffect, useRef, useState } from 'react';
import { BLUE, bytesOf, GRAY, INK, MODES, ORDER, RED } from '../../data';
import type { ModeKey } from '../../data';
import { ApiError, cancelJob, fetchResult, pollJob, startEncode, status } from '../../lib/api';
import type { JobView } from '../../lib/api';
import { inspect, issueOf, withDims } from '../../lib/image';
import type { FileInfo } from '../../lib/image';
import { prefersReducedMotion, S } from '../../lib/style';
import { check, dropZone, ISSUE, scrollToId, segments } from './shared';
import { Turnstile } from './Turnstile';

type Final = 'done' | 'refused' | 'timeout' | 'cancelled' | 'vlimit' | 'slimit' | 'failed' | 'botcheck';
type Phase = 'idle' | 'run' | Final;
interface Result { marked: string; diff: string; bytes: number }

export function HideTab({ navRead }: { navRead: () => void }) {
  const [hFile, setHFile] = useState<FileInfo | null>(null);
  const [hMode, setHMode] = useState<ModeKey>('subtle');
  const [hMsg, setHMsgState] = useState(''), [hPass, setHPassState] = useState(''), [hPass2, setHPass2State] = useState('');
  const [hShow, setHShow] = useState(false), [hDrag, setHDrag] = useState(false), [hView, setHView] = useState<'enc' | 'orig'>('enc');
  const [phase, setPhase] = useState<Phase>('idle');
  const [job, setJob] = useState<JobView | null>(null), [cold, setCold] = useState(false), [t0, setT0] = useState(0), [now, setNow] = useState(0);
  const [result, setResult] = useState<Result | null>(null), [sentBytes, setSentBytes] = useState(0);
  const [siteClosed, setSiteClosed] = useState(false);
  const [token, setToken] = useState<string | null>(null), [tsReset, setTsReset] = useState(0);
  const hFileRef = useRef<HTMLInputElement>(null);
  const jobId = useRef<string | null>(null);

  useEffect(() => { status().then((s) => setSiteClosed(!s.site_open)).catch(() => {}); }, []);
  useEffect(() => () => { if (result) { URL.revokeObjectURL(result.marked); URL.revokeObjectURL(result.diff); } }, [result]);

  // Poll the job once a second while it runs; the server drops a queued job whose page stops polling.
  useEffect(() => {
    if (phase !== 'run' || !job) return;
    let stop = false;
    const tick = window.setInterval(() => setNow(Date.now()), 200);
    const loop = async () => {
      while (!stop) {
        await new Promise((r) => setTimeout(r, 1000));
        if (stop || !jobId.current) return;
        let view: JobView;
        try { view = await pollJob(jobId.current); } catch { if (!stop) setPhase('failed'); return; }
        if (stop) return;
        if (view.state === 'starting') setCold(true);
        setJob(view);
        if (view.state === 'done') {
          try {
            const [m, d] = await Promise.all([fetchResult(view.id, 'marked'), fetchResult(view.id, 'difference')]);
            setResult({ marked: URL.createObjectURL(m), diff: URL.createObjectURL(d), bytes: m.size });
            setHView('enc'); setPhase('done');
          } catch { setPhase('failed'); }
          return;
        }
        const final: Partial<Record<JobView['state'], Final>> = { refused: 'refused', timed_out: 'timeout', cancelled: 'cancelled', failed: 'failed' };
        if (final[view.state]) { setPhase(final[view.state]!); return; }
      }
    };
    loop();
    return () => { stop = true; window.clearInterval(tick); };
  }, [phase, job?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const resetJob = () => { if (phase !== 'run') { setPhase('idle'); setResult(null); } };
  const setMode = (k: ModeKey) => { setHMode(k); resetJob(); };
  const setFile = (f: FileInfo | null) => { setHFile(withDims(f)); setPhase('idle'); setResult(null); };
  const readFile = async (file?: File) => { if (file) setFile(await inspect(file, file.name)); };
  const useSample = async () => {
    const blob = await (await fetch('/assets/station-wellington.jpg')).blob();
    setFile({ ...(await inspect(new File([blob], 'station-platform.jpg', { type: 'image/jpeg' }), 'station-platform.jpg', true)) });
  };

  const encode = async () => {
    if (!hFile?.blob) return;
    setResult(null); setCold(false);
    const start = Date.now(); setT0(start); setNow(start);
    setSentBytes(bytesOf(hMsg));
    scrollToId('gf-hresult');
    try {
      const view = await startEncode(hFile.blob, hFile.name, hMode, hMsg, hPass, token || undefined);
      jobId.current = view.id; setJob(view); setPhase('run');
      if (view.state === 'starting') setCold(true);
    } catch (e) {
      const code = e instanceof ApiError ? e.body.error : 'unreachable';
      setPhase(code === 'site_limit' ? 'slimit' : code === 'visitor_limit' ? 'vlimit' : code === 'bot_check' ? 'botcheck' : 'failed');
      if (code === 'site_limit') setSiteClosed(true);
    } finally {
      setTsReset((n) => n + 1);
    }
  };

  // ---- values, named as in the design reference's renderVals()
  const HM = MODES[hMode];
  const hIss = issueOf(hFile, false), hf = hFile;
  const n = bytesOf(hMsg), over = n > HM.bytes, near = !over && n >= HM.bytes * 0.85;
  const words = hPass.trim().split(/\s+/).filter(Boolean).length, len = hPass.length;
  const lvl = !len ? 0 : (words >= 3 && len >= 15) || len >= 24 ? 3 : (words >= 2 && len >= 10) || len >= 14 ? 2 : 1;
  const strText = ['Use three or more random words.', 'Weak. Easy to guess, even with slow key derivation.', 'Fair. Three or more random words is better.', 'Good. Several random words.'][lvl];
  const mismatch = hPass2.length > 0 && hPass !== hPass2;
  const blockers: string[] = [];
  if (!hf) blockers.push('add a photo'); else if (hIss) blockers.push('use a different photo');
  if (!n) blockers.push('type a message'); else if (over) blockers.push('shorten the message');
  if (!hPass) blockers.push('set a passphrase'); else if (hPass !== hPass2) blockers.push('repeat the passphrase exactly');
  const jobBusy = phase === 'run';
  const hDisabled = blockers.length > 0 || jobBusy || siteClosed;
  const hNotes: string[] = [];
  if (hf && !hIss && hf.p3) hNotes.push('This photo uses a wide-gamut colour profile (Display P3). It will be converted to standard sRGB first, so colours may shift very slightly.');
  if (hf && !hIss && Math.max(hf.w, hf.h) < 1000) hNotes.push('Small photos take longer and are more likely to be refused. Bigger, busier photos work best.');

  const stage = job && jobBusy ? job.state : null;
  const stDefs: [string, string][] = [['queued', 'Waiting in line'], ...(cold ? [['starting', 'Starting the engine'] as [string, string]] : []), ['encoding', 'Encoding and checking the saved file'], ['done', 'Ready to download']];
  const stageIdx = stDefs.findIndex((d) => d[0] === stage);
  // Done: a check. Now: a ring with a pulsing centre. Upcoming: an outline (corrective pass 14).
  const hStages = stDefs.map((d, i) => ({ label: d[1], status: i < stageIdx ? 'done' : i === stageIdx ? 'now' : '', fg: i <= stageIdx ? INK : GRAY, weight: i === stageIdx ? 600 : 400,
    kind: i < stageIdx ? 'done' : i === stageIdx ? 'now' : 'next', anim: i === stageIdx && !prefersReducedMotion() ? 'gfpulse 1s ease-in-out infinite' : 'none' }));
  const pos = job?.position ?? 0, slow = !!job?.slow;
  const hHead = stage === 'queued' ? (pos === 0 ? 'You’re next in line' : pos + (pos === 1 ? ' person' : ' people') + ' ahead of you') : stage === 'starting' ? 'Starting the engine…' : slow ? 'This photo is a tough one. Still working…' : 'Encoding your photo';
  const hSub = stage === 'queued' ? 'Only one photo is encoded at a time. Your place is kept while this tab stays open.' : stage === 'starting' ? 'The engine sleeps when nobody has used it for a while. Waking it adds 10–20 seconds.' : slow ? 'Some photos need much longer. If it can’t finish within 5 minutes, it stops and no file is produced. You can cancel at any time.' : 'This usually takes under 2 minutes. You can keep this tab open.';
  const prog = Math.round(Math.min(1, job?.progress || 0) * 100);
  const elapsed = Math.max(0, (now - t0) / 1000);
  const hFileClick = () => hFileRef.current && hFileRef.current.click();
  const toExamples = () => { const el = document.getElementById('try'); if (el) window.scrollTo({ top: el.getBoundingClientRect().top + window.scrollY - 60, behavior: prefersReducedMotion() ? 'auto' : 'smooth' }); };
  const toLong = () => { setHMode('long'); setPhase('idle'); };
  const STOP = ({
    refused: { t: 'This picture can’t carry the message', b: 'This picture doesn’t have enough texture to carry the message. Try a busier photo, a shorter message, or Long mode.', m: 'No file was produced. The encoder never returns a file that fails to read back.', a: [['Choose another photo', hFileClick], ['Switch to Long', toLong]] },
    timeout: { t: 'This photo took too long', b: 'This photo took too long to encode. Try a larger or more detailed photo, or a shorter message.', m: 'Stopped at 5:00 · no file produced', a: [['Choose another photo', hFileClick], ['Switch to Long', toLong]] },
    cancelled: { t: 'Encoding cancelled', b: 'Nothing was kept. Change the photo, mode or message and encode again when you’re ready.', m: 'cancelled · no file produced', a: [] },
    vlimit: { t: 'You’ve used today’s encodes', b: 'You’ve used today’s encodes. You can still decode any image, or try the ready-made examples.', m: 'visitor limit reached · resets tomorrow (UTC)', a: [['Try the ready-made examples', toExamples], ['Read a message', navRead]] },
    slimit: { t: 'Encoding is closed for today', b: 'The demo has hit today’s limit. Encoding comes back tomorrow (UTC). Decoding still works.', m: 'site limit reached', a: [['Try the ready-made examples', toExamples], ['Read a message', navRead]] },
    // Not in the design: wording for server errors and a failed bot check, approved 2026-11-12.
    failed: { t: 'Something went wrong', b: 'The encoder stopped unexpectedly and no file was produced. Try again in a minute.', m: 'server error · no file produced', a: [] },
    botcheck: { t: 'The bot check didn’t pass', b: 'Complete the check next to the Encode button and try again.', m: 'bot check failed · no file produced', a: [] },
  } as Record<string, { t: string; b: string; m: string; a: [string, () => void][] }>)[phase];

  const bc = { n, limit: HM.bytes, fg: over ? RED : near ? '#355574' : GRAY, bd: over ? RED : '#dddddd', bar: over ? RED : BLUE, pct: Math.min(100, n / HM.bytes * 100) + '%', helpFg: over ? RED : GRAY,
    help: over ? 'Too long by ' + (n - HM.bytes) + ' byte' + (n - HM.bytes === 1 ? '' : 's') + ' for ' + HM.label + '.' + (hMode !== 'long' && n <= MODES.long.bytes ? ' Long fits up to ' + MODES.long.bytes + ' bytes.' : '') : 'Counted in UTF-8 bytes. Plain letters are 1 byte, accented letters 2, most emoji 4.' };
  const str = { text: strText, c1: lvl >= 1 ? (lvl === 1 ? '#8a837c' : BLUE) : '#e6e1da', c2: lvl >= 2 ? BLUE : '#e6e1da', c3: lvl >= 3 ? BLUE : '#e6e1da' };

  const hDragOver = (e: React.DragEvent) => { e.preventDefault(); if (!hDrag) setHDrag(true); }, hDragLeave = () => setHDrag(false);
  const hDrop = (e: React.DragEvent) => { e.preventDefault(); setHDrag(false); readFile(e.dataTransfer.files[0]); };
  const hFileInput = (e: React.ChangeEvent<HTMLInputElement>) => { readFile(e.target.files?.[0]); e.target.value = ''; };
  const hPick = hFileClick, hUseSample = useSample, hClear = () => setFile(null);
  const hDz = dropZone(hDrag, hIss, !!hf), hDzTitle = hDrag ? 'Drop to use this photo' : 'Drop a photo here';
  const hEmpty = !hf, hHasFile = !!hf, hCheck = check(hIss, hf), hIssue = !!hIss, hIssueText = hIss ? ISSUE[hIss](hf!, HM.label) : '';
  const hModes = ORDER.map((k) => { const M = MODES[k], on = k === hMode; return { label: M.label, bytes: M.bytes, cap: M.cap, status: '', tagBs: 'solid', tagDisp: 'none', blurb: M.blurb, pressed: on, bd: on ? BLUE : 'rgba(24,20,17,0.12)', bg: on ? '#f5f8fb' : '#fff', onClick: () => setMode(k) }; });
  const onHMsg = (e: React.ChangeEvent<HTMLTextAreaElement>) => setHMsgState(e.target.value);
  const onHPass = (e: React.ChangeEvent<HTMLInputElement>) => setHPassState(e.target.value), onHPass2 = (e: React.ChangeEvent<HTMLInputElement>) => setHPass2State(e.target.value);
  const hPassType = hShow ? 'text' : 'password', hShowStr = hShow, hShowLabel = hShow ? 'Hide' : 'Show', toggleHPass = () => setHShow(!hShow);
  const hMatchBd = mismatch ? RED : '#dddddd', hMatchFg = mismatch ? RED : GRAY;
  const hMatchText = mismatch ? 'The two entries don’t match.' : 'Share it with the recipient separately. It is never stored and never goes in a link.';
  const hEncode = encode, hSiteClosed = siteClosed;
  const hBtn = { bg: hDisabled ? 'rgba(0,0,0,0.06)' : BLUE, fg: hDisabled ? '#7a736d' : '#fff', cursor: hDisabled ? 'not-allowed' : 'pointer' };
  const hBlocker = jobBusy ? 'Encoding in progress.' : blockers.length ? 'To continue, ' + blockers.join(', ') + '.' : siteClosed ? 'Encoding is closed for today.' : 'Usually under 2 minutes.';
  const hJobActive = jobBusy, hElapsed = Math.floor(elapsed / 60) + ':' + String(Math.floor(elapsed % 60)).padStart(2, '0');
  const hShowProg = stage === 'encoding', hProgN = prog, hProgPct = prog + '%';
  const hCardBd = slow ? 'rgba(18,16,14,0.55)' : 'rgba(24,20,17,0.12)', hCancelBd = slow ? '#3f648c' : 'rgba(24,20,17,0.18)';
  const hCancel = useCallback(() => { if (jobId.current) cancelJob(jobId.current).catch(() => {}); setPhase('cancelled'); }, []);
  const hStop = !!STOP && !(phase === 'slimit' && siteClosed), hStopTitle = STOP ? STOP.t : '', hStopBody = STOP ? STOP.b : '', hStopMeta = STOP ? STOP.m : '', hStopActions = STOP ? STOP.a.map(([label, onClick]) => ({ label, onClick })) : [];
  const hDone = phase === 'done' && !!result, hAmp = HM.amp, hCap = HM.cap, hModeLabel = HM.label, hModel = HM.backbone, hProfile = HM.profile;
  const hStageLabel = hView === 'orig' ? 'Your photo · original' : 'Marked PNG · ' + HM.label;
  const hStageSrc = hView === 'orig' ? hf?.url : result?.marked, hDiffSrc = result?.diff;
  const hDownloadUrl = result?.marked, hDownloadName = (hf?.name || 'photo').replace(/\.[^.]+$/, '') + '-ghostframe.png';
  const hViewSeg = segments([['enc', 'Marked'], ['orig', 'Original']], hView, (v) => setHView(v as 'enc' | 'orig'));

  return (
<>
      {hSiteClosed && (<>
        <div role="status" style={S({ display: 'flex', flexWrap: 'wrap', gap: '12px 20px', alignItems: 'center', justifyContent: 'space-between', padding: '16px 18px', marginBottom: '24px', borderRadius: '8px', background: '#f1eee9', border: '1.5px solid rgba(18,16,14,0.55)' })}>
          <div style={S({ display: 'flex', flexDirection: 'column', gap: '4px', flex: '1 1 320px', minWidth: '0' })}>
            <span style={S({ fontSize: '16px', fontWeight: '700' })}>Encoding is closed for today</span>
            <span style={S({ fontSize: '14px', lineHeight: '1.5' })}>The demo has hit today’s limit. Encoding comes back tomorrow (UTC). Decoding still works.</span>
          </div>
          <div style={S({ display: 'flex', flexWrap: 'wrap', gap: '8px' })}>
            <a href="#try" className="gf-touch-44" style={S({ fontSize: '14px', fontWeight: '600', padding: '9px 14px', minHeight: '40px', boxSizing: 'border-box', display: 'inline-flex', alignItems: 'center', border: '1px solid rgba(63,100,140,0.22)', borderRadius: '4px', background: '#fff', color: '#355574', textDecoration: 'none' })}>Try the ready-made examples</a>
            <button type="button" onClick={navRead} style={S({ fontSize: '14px', fontWeight: '600', padding: '9px 14px', minHeight: '40px', border: '1px solid rgba(63,100,140,0.22)', borderRadius: '4px', background: '#fff', color: '#355574', cursor: 'pointer' })}>Read a message</button>
          </div>
        </div>
      </>)}
      <div style={S({ display: 'flex', flexWrap: 'wrap', gap: '32px', alignItems: 'flex-start' })}>
        <div style={S({ flex: '1 1 380px', minWidth: '0', display: 'flex', flexDirection: 'column', gap: '22px' })}>
          <div style={S({ display: 'flex', flexDirection: 'column', gap: '8px' })}>
            <span style={S({ fontSize: '14px', fontWeight: '600' })}><span style={S({ font: '500 11.5px \'IBM Plex Mono\',ui-monospace,monospace', color: '#3f648c', marginRight: '8px' })}>01</span>Upload a photo</span>
            <div onDragOver={hDragOver} onDragLeave={hDragLeave} onDrop={hDrop} style={S({ minHeight: '200px', borderRadius: '8px', border: `1.5px ${hDz.bs} ${hDz.bd}`, background: hDz.bg, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '10px', padding: '18px', textAlign: 'center', boxSizing: 'border-box' })}>
              <input ref={hFileRef} type="file" accept="image/png,image/jpeg" onChange={hFileInput} aria-label="Choose a photo" style={S({ position: 'absolute', width: '1px', height: '1px', opacity: '0', pointerEvents: 'none' })} />
              {hEmpty && (<>
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#625c57" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><path d="m17 8-5-5-5 5" /><path d="M12 3v12" /></svg>
                <span style={S({ fontSize: '15px', fontWeight: '600' })}>{hDzTitle}</span>
                <span style={S({ fontSize: '13px', lineHeight: '1.5', color: '#625c57' })}>PNG or JPEG, up to 4 megapixels. At least 1000 px on the long side works best.</span>
                <div style={S({ display: 'flex', flexWrap: 'wrap', gap: '6px', justifyContent: 'center' })}>
                  <button type="button" onClick={hPick} style={S({ fontSize: '14px', fontWeight: '600', padding: '9px 14px', minHeight: '40px', border: '1px solid rgba(63,100,140,0.22)', borderRadius: '4px', background: '#fff', color: '#355574', cursor: 'pointer' })}>Choose photo</button>
                  <button type="button" onClick={hUseSample} style={S({ fontSize: '14px', fontWeight: '600', padding: '9px 12px', minHeight: '40px', border: '0', borderRadius: '4px', background: 'transparent', color: 'rgba(18,16,14,0.96)', cursor: 'pointer', textDecoration: 'underline', textUnderlineOffset: '3px' })}>Use a sample photo</button>
                </div>
              </>)}
              {hHasFile && (<>
                <div style={S({ display: 'flex', gap: '14px', alignItems: 'center', width: '100%', textAlign: 'left' })}>
                  <img src={hFile.url} alt="Selected photo" style={S({ width: '96px', height: '96px', objectFit: 'cover', borderRadius: '4px', border: '1px solid rgba(24,20,17,0.10)', display: 'block', flex: 'none' })} />
                  <div style={S({ display: 'flex', flexDirection: 'column', gap: '4px', minWidth: '0', flex: '1' })}>
                    <span style={S({ fontSize: '14.5px', fontWeight: '600', wordBreak: 'break-all' })}>{hFile.name}</span>
                    <span style={S({ font: '400 12px/1.35 \'IBM Plex Mono\',ui-monospace,monospace', color: '#625c57' })}>{hFile.type} · {hFile.dims} · {hFile.mp} MP</span>
                    <span style={S({ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', fontWeight: '600', color: hCheck.fg })}><span aria-hidden="true" style={S({ width: '14px', height: '14px', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: hCheck.radius, background: hCheck.fg, color: '#fff', fontSize: '10px', fontWeight: '700', flex: 'none' })}>{hCheck.glyph}</span>{hCheck.text}</span>
                  </div>
                </div>
                {hIssue && (<>
                  <p role="alert" style={S({ margin: '0', fontSize: '13.5px', lineHeight: '1.5', textAlign: 'left', width: '100%', color: 'rgba(18,16,14,0.96)' })}>{hIssueText}</p>
                </>)}
                {hNotes.map((n, i) => (<React.Fragment key={i}>
                  <p style={S({ margin: '0', fontSize: '13px', lineHeight: '1.5', textAlign: 'left', width: '100%', color: '#355574', background: '#eaf1f7', padding: '8px 10px', borderRadius: '4px', boxSizing: 'border-box' })}>{n}</p>
                </React.Fragment>))}
                <div style={S({ display: 'flex', gap: '6px', alignSelf: 'flex-start' })}><button type="button" onClick={hPick} style={S({ fontSize: '13.5px', fontWeight: '600', padding: '8px 12px', minHeight: '36px', border: '0', borderRadius: '4px', background: 'rgba(0,0,0,0.05)', color: 'rgba(18,16,14,0.96)', cursor: 'pointer' })}>Replace</button><button type="button" onClick={hClear} style={S({ fontSize: '13.5px', fontWeight: '600', padding: '8px 12px', minHeight: '36px', border: '0', borderRadius: '4px', background: 'transparent', color: 'rgba(18,16,14,0.96)', cursor: 'pointer' })}>Remove</button></div>
              </>)}
            </div>
          </div>

          <p style={S({ margin: '-14px 0 0', fontSize: '12.5px', lineHeight: '1.5', color: '#625c57', textWrap: 'pretty' })}><span style={S({ fontWeight: '600', color: 'rgba(18,16,14,0.96)' })}>Tip:</span> busy, detailed photos work best, such as food, textures, crowds or foliage. Flat skies, plain walls, logos and screenshots are often refused.</p>

          <div role="group" aria-label="Mode" style={S({ display: 'flex', flexDirection: 'column', gap: '8px' })}>
            <span style={S({ fontSize: '14px', fontWeight: '600' })}><span style={S({ font: '500 11.5px \'IBM Plex Mono\',ui-monospace,monospace', color: '#3f648c', marginRight: '8px' })}>02</span>Choose a mode</span>
            <div className="gf-hmodes" style={S({ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(150px,1fr))', gap: '8px' })}>
              {hModes.map((m, i) => (<React.Fragment key={i}>
                <button type="button" aria-pressed={m.pressed} onClick={m.onClick} style={S({ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: '6px', padding: '12px', borderRadius: '6px', border: `1.5px solid ${m.bd}`, background: m.bg, cursor: 'pointer', textAlign: 'left', color: 'rgba(18,16,14,0.96)' })}>
                  <span style={S({ display: 'flex', alignItems: 'center', gap: '8px', width: '100%' })}><span style={S({ fontSize: '15px', fontWeight: '600' })}>{m.label}</span><span style={S({ marginLeft: 'auto', font: '500 10.5px/1 \'IBM Plex Mono\',ui-monospace,monospace', padding: '3px 6px', borderRadius: '999px', border: `1px ${m.tagBs} #8a837c`, color: '#625c57', display: m.tagDisp })}>{m.status}</span></span>
                  <span style={S({ font: '400 11.5px/1.45 \'IBM Plex Mono\',ui-monospace,monospace', color: '#625c57' })}>up to {m.bytes} bytes<br />change ≤ {m.cap}/255</span>
                  <span style={S({ fontSize: '12.5px', lineHeight: '1.4', color: '#625c57' })}>{m.blurb}</span>
                </button>
              </React.Fragment>))}
            </div>
          </div>
        </div>

        <div style={S({ flex: '1 1 380px', minWidth: '0', display: 'flex', flexDirection: 'column', gap: '22px' })}>
          <div style={S({ display: 'flex', flexDirection: 'column', gap: '6px' })}>
            <div style={S({ display: 'flex', justifyContent: 'space-between', gap: '12px', alignItems: 'baseline' })}>
              <label htmlFor="gf-hmsg" style={S({ fontSize: '14px', fontWeight: '600' })}><span style={S({ font: '500 11.5px \'IBM Plex Mono\',ui-monospace,monospace', color: '#3f648c', marginRight: '8px' })}>03</span>Type the message</label>
              <span id="gf-hcount" aria-live="polite" style={S({ font: '500 12.5px/1 \'IBM Plex Mono\',ui-monospace,monospace', color: bc.fg })}>{bc.n} / {bc.limit} bytes</span>
            </div>
            <textarea id="gf-hmsg" rows={3} value={hMsg} onChange={onHMsg} aria-describedby="gf-hcount gf-hhelp" placeholder="Meet at dawn." style={S({ fontSize: '15px', lineHeight: '1.45', padding: '10px 12px', border: `1px solid ${bc.bd}`, borderRadius: '4px', resize: 'vertical', minHeight: '72px', color: 'rgba(18,16,14,0.9)', background: '#fff' })}></textarea>
            <div aria-hidden="true" style={S({ height: '4px', background: '#e6e1da', borderRadius: '2px', overflow: 'hidden' })}><div style={S({ height: '100%', width: bc.pct, background: bc.bar, transition: 'width 160ms cubic-bezier(0.22,0.61,0.36,1)' })}></div></div>
            <span id="gf-hhelp" style={S({ fontSize: '12.5px', lineHeight: '1.5', color: bc.helpFg })}>{bc.help}</span>
          </div>

          <div style={S({ display: 'flex', flexDirection: 'column', gap: '8px' })}>
            <span style={S({ fontSize: '14px', fontWeight: '600' })}><span style={S({ font: '500 11.5px \'IBM Plex Mono\',ui-monospace,monospace', color: '#3f648c', marginRight: '8px' })}>04</span>Set a passphrase</span>
            <div className="gf-hpass" style={S({ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) minmax(0,1fr) auto', gap: '8px', alignItems: 'end' })}>
              <div style={S({ display: 'flex', flexDirection: 'column', gap: '4px' })}><label htmlFor="gf-hp1" style={S({ fontSize: '12.5px', color: '#625c57' })}>Passphrase</label><input id="gf-hp1" type={hPassType} value={hPass} onChange={onHPass} autoComplete="new-password" aria-describedby="gf-hstrength" style={S({ fontSize: '15px', padding: '10px 12px', minHeight: '44px', boxSizing: 'border-box', border: '1px solid #dddddd', borderRadius: '4px', background: '#fff', color: 'rgba(18,16,14,0.9)', width: '100%' })} /></div>
              <div style={S({ display: 'flex', flexDirection: 'column', gap: '4px' })}><label htmlFor="gf-hp2" style={S({ fontSize: '12.5px', color: '#625c57' })}>Repeat passphrase</label><input id="gf-hp2" type={hPassType} value={hPass2} onChange={onHPass2} autoComplete="new-password" aria-describedby="gf-hmatch" style={S({ fontSize: '15px', padding: '10px 12px', minHeight: '44px', boxSizing: 'border-box', border: `1px solid ${hMatchBd}`, borderRadius: '4px', background: '#fff', color: 'rgba(18,16,14,0.9)', width: '100%' })} /></div>
              <button type="button" className="gf-hshow" onClick={toggleHPass} aria-pressed={hShowStr} style={S({ fontSize: '13.5px', fontWeight: '600', padding: '0 12px', minHeight: '44px', border: '0', borderRadius: '4px', background: 'rgba(0,0,0,0.05)', color: 'rgba(18,16,14,0.96)', cursor: 'pointer' })}>{hShowLabel}</button>
            </div>
            <div style={S({ display: 'flex', flexWrap: 'wrap', gap: '8px 14px', alignItems: 'center', justifyContent: 'space-between' })}>
              <span id="gf-hstrength" style={S({ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12.5px', color: '#625c57' })}>
                <span aria-hidden="true" style={S({ display: 'flex', gap: '2px' })}><span style={S({ width: '18px', height: '4px', borderRadius: '1px', background: str.c1, display: 'block' })}></span><span style={S({ width: '18px', height: '4px', borderRadius: '1px', background: str.c2, display: 'block' })}></span><span style={S({ width: '18px', height: '4px', borderRadius: '1px', background: str.c3, display: 'block' })}></span></span>{str.text}
              </span>
              
            </div>
            <span id="gf-hmatch" style={S({ fontSize: '12.5px', lineHeight: '1.5', color: hMatchFg })}>{hMatchText}</span>
          </div>

          <div style={S({ display: 'flex', flexDirection: 'column', gap: '10px' })}>
            <div style={S({ display: 'flex', flexWrap: 'wrap', gap: '10px 14px', alignItems: 'center' })}>
              <button type="button" onClick={hEncode} disabled={hDisabled} style={S({ fontSize: '15px', fontWeight: '600', padding: '12px 20px', minHeight: '44px', border: '0', borderRadius: '4px', background: hBtn.bg, color: hBtn.fg, cursor: hBtn.cursor })}><span style={S({ font: '500 11.5px \'IBM Plex Mono\',ui-monospace,monospace', marginRight: '8px', opacity: '0.8' })}>05</span>Encode</button>
              <Turnstile onToken={setToken} resetKey={tsReset} />
            </div>
            <div>
              <span style={S({ fontSize: '13px', lineHeight: '1.45', color: '#625c57' })}>{hBlocker}</span>
            </div>
          </div>

        </div>
      </div>

      <div id="gf-hresult" role="status" aria-live="polite" style={S({ marginTop: '24px', scrollMarginTop: '72px' })}>
        {hJobActive && (<>
          <div style={S({ display: 'flex', flexDirection: 'column', gap: '14px', padding: '20px', border: `1px solid ${hCardBd}`, borderRadius: '8px', background: '#f6f4f1' })}>
            <div style={S({ display: 'flex', flexWrap: 'wrap', gap: '8px 16px', alignItems: 'baseline', justifyContent: 'space-between' })}>
              <span style={S({ fontSize: '18px', fontWeight: '700', lineHeight: '1.3' })}>{hHead}</span>
              <span style={S({ font: '500 12.5px/1 \'IBM Plex Mono\',ui-monospace,monospace', color: '#625c57' })}>elapsed {hElapsed}</span>
            </div>
            <p style={S({ margin: '0', fontSize: '14.5px', lineHeight: '1.55', textWrap: 'pretty' })}>{hSub}</p>
            {hShowProg && (<>
              <div style={S({ display: 'flex', flexDirection: 'column', gap: '6px' })}>
                <div role="progressbar" aria-label="Encoding progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={hProgN} style={S({ height: '8px', background: '#e6e1da', borderRadius: '2px', overflow: 'hidden' })}><div style={S({ height: '100%', width: hProgPct, background: '#3f648c', transition: 'width 200ms linear' })}></div></div>
                <span style={S({ font: '500 12px/1.3 \'IBM Plex Mono\',ui-monospace,monospace', color: '#625c57' })}>{hProgPct} · reported by the encoder</span>
              </div>
            </>)}
            <ol style={S({ margin: '0', padding: '0', listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '10px' })}>
              {hStages.map((st, i) => (<React.Fragment key={i}>
                <li style={S({ display: 'flex', alignItems: 'flex-start', gap: '10px', fontSize: '14.5px', lineHeight: '20px', color: st.fg })}>
                  <span aria-hidden="true" style={S({ width: '16px', height: '16px', marginTop: '2px', borderRadius: '50%', boxSizing: 'border-box', border: `1.5px solid ${st.kind === 'next' ? '#c9c2ba' : BLUE}`, background: st.kind === 'done' ? BLUE : 'transparent', display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 'none' })}>
                    {st.kind === 'done' && <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round"><path d="m5 12 5 5L20 7" /></svg>}
                    {st.kind === 'now' && <span style={S({ width: '7px', height: '7px', borderRadius: '50%', background: BLUE, display: 'block', animation: st.anim })} />}
                  </span>
                  <span style={S({ fontWeight: st.weight, minWidth: '0' })}>{st.label}</span><span style={S({ font: '400 11.5px/20px \'IBM Plex Mono\',ui-monospace,monospace', color: '#625c57', marginLeft: 'auto', flex: 'none' })}>{st.status}</span>
                </li>
              </React.Fragment>))}
            </ol>
            <div style={S({ display: 'flex', flexWrap: 'wrap', gap: '8px 14px', alignItems: 'center' })}>
              <button type="button" onClick={hCancel} style={S({ fontSize: '14px', fontWeight: '600', padding: '9px 14px', minHeight: '40px', border: `1px solid ${hCancelBd}`, borderRadius: '4px', background: '#fff', color: 'rgba(18,16,14,0.96)', cursor: 'pointer' })}>Cancel</button>
              <span style={S({ fontSize: '12.5px', lineHeight: '1.45', color: '#625c57' })}>Stops after 5 minutes if it can’t finish.</span>
            </div>
          </div>
        </>)}

        {hStop && (<>
          <div style={S({ display: 'flex', flexDirection: 'column', gap: '12px', padding: '20px', borderRadius: '8px', background: '#f1eee9', border: '1.5px solid rgba(18,16,14,0.55)' })}>
            <span style={S({ display: 'flex', gap: '10px', alignItems: 'center', fontSize: '17px', fontWeight: '700' })}><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="rgba(18,16,14,0.96)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={S({ flex: 'none' })}><path d="M12 2 2 20h20Z" /><path d="M12 9v5" /><path d="M12 17.5h.01" /></svg>{hStopTitle}</span>
            <p style={S({ margin: '0', fontSize: '15px', lineHeight: '1.55', textWrap: 'pretty' })}>{hStopBody}</p>
            <span style={S({ font: '400 12px/1.4 \'IBM Plex Mono\',ui-monospace,monospace', color: '#625c57' })}>{hStopMeta}</span>
            <div style={S({ display: 'flex', flexWrap: 'wrap', gap: '8px' })}>
              {hStopActions.map((a, i) => (<React.Fragment key={i}>
                <button type="button" onClick={a.onClick} style={S({ fontSize: '14px', fontWeight: '600', padding: '9px 14px', minHeight: '40px', border: '1px solid rgba(63,100,140,0.22)', borderRadius: '4px', background: '#fff', color: '#355574', cursor: 'pointer' })}>{a.label}</button>
              </React.Fragment>))}
            </div>
          </div>
        </>)}

        {hDone && (<>
          <div style={S({ display: 'flex', flexWrap: 'wrap', gap: '28px', alignItems: 'flex-start', padding: '20px', borderRadius: '8px', border: '1.5px solid #3f648c', background: '#f5f8fb' })}>
            <figure style={S({ flex: '1.4 1 460px', minWidth: '0', maxWidth: '780px', margin: '0', display: 'flex', flexDirection: 'column', gap: '8px' })}>
              <div style={S({ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(200px,1fr))', gap: '10px', background: '#312e2b', borderRadius: '6px', padding: '10px' })}>
                <div style={S({ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: '0' })}>
                  <span style={S({ font: '500 11px/1.3 \'IBM Plex Mono\',ui-monospace,monospace', color: '#d9d3cc' })}>{hStageLabel}</span>
                  <div style={S({ border: '3px solid #f6f4f1', lineHeight: '0' })}><img src={hStageSrc} alt={hStageLabel} style={S({ width: '100%', height: 'auto', display: 'block' })} /></div>
                </div>
                <div style={S({ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: '0' })}>
                  <span style={S({ font: '500 11px/1.3 \'IBM Plex Mono\',ui-monospace,monospace', color: '#d9d3cc' })}>Amplified difference ×{hAmp} · not the photo</span>
                  <div style={S({ position: 'relative', border: '3px solid #f6f4f1', lineHeight: '0' })}><img src={hDiffSrc} alt="Amplified difference" style={S({ width: '100%', height: 'auto', display: 'block' })} /><div aria-hidden="true" style={S({ position: 'absolute', inset: '0', border: '2px dashed #3f648c', pointerEvents: 'none' })}></div></div>
                </div>
              </div>
              <div style={S({ display: 'flex', flexWrap: 'wrap', gap: '8px 14px', alignItems: 'center', justifyContent: 'space-between' })}>
                <span style={S({ display: 'flex', alignItems: 'center', gap: '8px' })}><span id="gf-hleft" style={S({ fontSize: '13px', fontWeight: '600', color: '#625c57' })}>Left image</span>
                <div role="group" aria-labelledby="gf-hleft" style={S({ display: 'flex', gap: '2px', background: 'rgba(0,0,0,0.05)', padding: '3px', borderRadius: '6px' })}>
                  {hViewSeg.map((o, i) => (<React.Fragment key={i}>
                    <button type="button" aria-pressed={o.pressed} onClick={o.onClick} style={S({ fontSize: '13.5px', fontWeight: '600', padding: '8px 11px', minHeight: '38px', border: '0', borderRadius: '4px', background: o.bg, color: o.fg, boxShadow: o.sh, cursor: 'pointer' })}>{o.label}</button>
                  </React.Fragment>))}
                </div></span>
                <span style={S({ font: '500 12px/1.3 \'IBM Plex Mono\',ui-monospace,monospace', color: '#355574' })}>differences ×{hAmp}, real maximum {hCap}/255</span>
              </div>
            </figure>
            <div style={S({ flex: '1 1 320px', minWidth: '0', display: 'flex', flexDirection: 'column', gap: '16px' })}>
              <span style={S({ display: 'flex', gap: '10px', alignItems: 'center', fontSize: '19px', fontWeight: '700' })}><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#3f648c" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10" /><path d="m8 12 3 3 5-6" /></svg>Done. Your message is hidden.</span>
              <dl style={S({ margin: '0', display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '4px 14px', font: '400 12.5px/1.4 \'IBM Plex Mono\',ui-monospace,monospace' })}>
                <dt style={S({ color: '#625c57' })}>mode</dt><dd style={S({ margin: '0', overflowWrap: 'anywhere' })}>{hModeLabel} · {hModel} <span style={S({ color: '#625c57' })}>· {hProfile}</span></dd>
                <dt style={S({ color: '#625c57' })}>message</dt><dd style={S({ margin: '0' })}>{sentBytes} bytes, encrypted</dd>
                <dt style={S({ color: '#625c57' })}>checked</dt><dd style={S({ margin: '0' })}>saved file reopened and read back</dd>
                <dt style={S({ color: '#625c57' })}>output</dt><dd style={S({ margin: '0' })}>PNG, no metadata</dd>
              </dl>
              <div style={S({ display: 'flex', flexWrap: 'wrap', gap: '8px', alignItems: 'center' })}>
                <a href={hDownloadUrl} download={hDownloadName} style={S({ display: 'inline-flex', alignItems: 'center', boxSizing: 'border-box', fontSize: '15px', fontWeight: '600', padding: '12px 18px', minHeight: '44px', border: '0', borderRadius: '4px', background: '#3f648c', color: '#fff', textDecoration: 'none', cursor: 'pointer' })} className="hover-primary-link">Download PNG</a>
              </div>
              <div style={S({ display: 'flex', flexDirection: 'column', gap: '8px', padding: '14px 16px', background: '#fff', border: '1px solid rgba(24,20,17,0.12)', borderRadius: '6px' })}>
                <span style={S({ fontSize: '14.5px', fontWeight: '700' })}>Keep the PNG file exact</span>
                <p style={S({ margin: '0', fontSize: '13.5px', lineHeight: '1.5' })}>The message survives only an exact copy of this file.</p>
                <div style={S({ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(150px,1fr))', gap: '10px', fontSize: '13px', lineHeight: '1.45' })}>
                  <div style={S({ display: 'flex', flexDirection: 'column', gap: '4px' })}><span style={S({ fontWeight: '600', display: 'flex', gap: '6px', alignItems: 'center' })}><span aria-hidden="true" style={S({ fontWeight: '700', color: '#3f648c' })}>✓</span>Keeps it</span><span>Email attachment, file-sharing link, AirDrop, USB</span></div>
                  <div style={S({ display: 'flex', flexDirection: 'column', gap: '4px' })}><span style={S({ fontWeight: '600', display: 'flex', gap: '6px', alignItems: 'center' })}><span aria-hidden="true" style={S({ fontWeight: '700' })}>✕</span>Destroys it</span><span>WhatsApp, Instagram, Messenger and most chat apps, screenshots, saving as JPEG, resizing, cropping, filters, some “optimise” tools</span></div>
                </div>
              </div>
              <p style={S({ margin: '0', fontSize: '13.5px', lineHeight: '1.5', color: '#625c57', textWrap: 'pretty' })}>The photo still looks like a photo, but anyone with the public reader can tell it carries a message. Your photo and the result are deleted from the server shortly after the job finishes.</p>
            </div>
          </div>
        </>)}
      </div>
</>
  );
}
