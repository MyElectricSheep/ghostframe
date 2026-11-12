import React from 'react';
import { BLUE, DETECT, MODES, ORDER, SMALL640, STRESS } from '../data';
import { S } from '../lib/style';
import { useMedia } from '../hooks/useNarrow';
import { useAbbr } from './Abbr';

// Every number here comes from design-data.json (stress, small640, detect, modes).
const stressNote = `hard images: Subtle ${STRESS.subtle.encoded}/${STRESS.subtle.of}, Long ${STRESS.long.encoded}/${STRESS.long.of}`;
const small = (k: 'subtle' | 'long') => SMALL640[k] ? `${SMALL640[k]!.read_back}/${SMALL640[k]!.of}` : '';
const smallNote = SMALL640.subtle && SMALL640.long ? ` · 640 px photos: Subtle ${small('subtle')}, Long ${small('long')}` : '';
const sameSmall = SMALL640.subtle && SMALL640.long && SMALL640.subtle.read_back === SMALL640.long.read_back && SMALL640.subtle.of === SMALL640.long.of;
const smallSentence = !SMALL640.subtle || !SMALL640.long ? ''
  : sameSmall ? `At 640 px wide, ordinary photos did well: Subtle and Long each read back ${SMALL640.subtle.read_back} of ${SMALL640.subtle.of}.`
  : `At 640 px wide, ordinary photos did well: Subtle read back ${SMALL640.subtle.read_back} of ${SMALL640.subtle.of}, Long ${SMALL640.long.read_back} of ${SMALL640.long.of}.`;
const aucs = [DETECT.subtle?.auc, DETECT.long?.auc].filter((v): v is number => v != null);
const detectNote = aucs.length ? `a detection test separated marked from clean photos ${Math.round(Math.min(...aucs) * 100)}% of the time` : '';

const limits = [
  { t: 'Exact PNG copies only.', d: 'Recompressing, resizing, cropping, screenshots and most chat apps destroy the message. Email attachments, file links, AirDrop and USB keep it.', n: '' },
  { t: 'Steganography, not a watermark.', d: 'The message is meant to stay hidden, not to survive edits. A watermark is built to withstand compression and resizing; Ghostframe deliberately is not.', n: '' },
  { t: 'Not invisible to software.', d: 'Anyone with the public reader can tell a photo carries a message. They can’t read or forge it.', n: detectNote },
  { t: 'Not every photo works.', d: 'Flat, synthetic and small images can be refused. When that happens, no file is produced.', n: stressNote + smallNote },
  { t: 'Short messages only.', d: 'Limits are in UTF-8 bytes, not characters.', n: `${MODES.classic.bytes}, ${MODES.subtle.bytes} or ${MODES.long.bytes} bytes` },
];
const modeRows = ORDER.map((k) => ({ ...MODES[k], statusSfx: '' }));
const hardRows = ([['Subtle', STRESS.subtle], ['Long', STRESS.long]] as const).map(([label, s]) => ({ label, n: s.encoded, cells: Array.from({ length: s.of }, (_, i) => (i < s.encoded ? BLUE : '#e0dad3')) }));
const REPO = 'https://github.com/MyElectricSheep/ghostframe';
const links = [
  { t: 'Source code', d: 'Engine, CLI and this site', ph: 'github.com/MyElectricSheep/ghostframe', href: REPO },
  { t: 'Benchmark', d: 'Held-out trials, image quality, speed', ph: 'docs/BENCHMARK.md', href: `${REPO}/blob/main/docs/BENCHMARK.md` },
  { t: 'Method notes', d: 'How the experiments were run', ph: 'docs/AUDIT_REPORT.md', href: `${REPO}/blob/main/docs/AUDIT_REPORT.md` },
];

export function Limits() {
  const phone = useMedia('(max-width: 559.98px)');
  const { abOpen, abExp } = useAbbr();
  return (
<section id="limits" data-screen-label="Limits and evidence" style={S({ background: '#fff', borderTop: '1px dashed rgba(24,20,17,0.22)', borderBottom: '1px dashed rgba(24,20,17,0.22)', scrollMarginTop: '56px' })}>
  <div style={S({ maxWidth: '1240px', margin: '0 auto', padding: 'clamp(40px,6vw,80px) clamp(16px,4vw,40px)', display: 'flex', flexDirection: 'column', gap: '28px' })}>
    <div style={S({ display: 'flex', flexDirection: 'column', gap: '8px', maxWidth: '46em' })}>
      <h2 style={S({ margin: '0', fontSize: 'clamp(28px,3.4vw,40px)', fontWeight: '700', letterSpacing: '-0.02em', lineHeight: '1.1' })}>Limits and evidence</h2>
      <p style={S({ margin: '0', fontSize: '16px', lineHeight: '1.55', color: '#625c57', textWrap: 'pretty' })}>Numbers from our own experiments and benchmarks. Held-out trials used 41 photographs the system had never seen, all 1280 px wide, with three messages per photo, read back by a separate program given only the file and the passphrase.</p>
    </div>
    <div style={S({ display: 'flex', flexWrap: 'wrap', gap: '32px', alignItems: 'flex-start' })}>
      <ul style={S({ flex: '1 1 380px', minWidth: '0', margin: '0', padding: '0', listStyle: 'none', display: 'flex', flexDirection: 'column', borderTop: '1px solid rgba(24,20,17,0.10)' })}>
        {limits.map((l, i) => (<React.Fragment key={i}>
          <li style={S({ display: 'flex', flexDirection: 'column', gap: '4px', padding: '14px 0', borderBottom: '1px solid rgba(24,20,17,0.10)' })}>
            <span style={S({ fontSize: '16px', fontWeight: '700' })}>{l.t}</span>
            <span style={S({ fontSize: '14.5px', lineHeight: '1.55', textWrap: 'pretty' })}>{l.d}</span>
            <span style={S({ font: '500 12px/1.4 \'IBM Plex Mono\',ui-monospace,monospace', color: '#355574' })}>{l.n}</span>
          </li>
        </React.Fragment>))}
      </ul>
      <div style={S({ flex: '1.4 1 480px', minWidth: '0', display: 'flex', flexDirection: 'column', gap: '20px' })}>
        <div style={S({ overflowX: 'auto', border: '1px solid rgba(24,20,17,0.10)', borderRadius: '8px' })}>
          <div style={S({ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '8px', padding: '12px 16px', borderBottom: '1px solid rgba(24,20,17,0.10)' })}>
            <span style={S({ display: 'inline-flex', alignItems: 'center', gap: '6px', font: '500 11px/1.2 \'IBM Plex Mono\',ui-monospace,monospace', color: '#fff', padding: '4px 9px', borderRadius: '999px', background: '#312e2b' })}><span aria-hidden="true" style={S({ width: '7px', height: '7px', borderRadius: '50%', background: '#fff', display: 'block' })}></span>Measured</span>
            <span id="gf-modes-cap" style={S({ fontSize: '13px', color: '#625c57' })}>Modes, held-out evidence and median image quality</span>
          </div>
          {phone ? (
          // Below 560 px each mode is a card with labelled rows, so nothing is cut off (corrective pass 3).
          <ul aria-labelledby="gf-modes-cap" style={S({ listStyle: 'none', margin: '0', padding: '0' })}>
            {modeRows.map((r, i) => (<React.Fragment key={i}>
              <li style={S({ display: 'flex', flexDirection: 'column', gap: '10px', padding: '14px 16px', borderBottom: '1px solid rgba(24,20,17,0.07)' })}>
                <span style={S({ display: 'flex', flexDirection: 'column', gap: '3px' })}><span style={S({ fontSize: '14.5px', fontWeight: '600' })}>{r.label}</span><span style={S({ font: '400 11px/1.3 \'IBM Plex Mono\',ui-monospace,monospace', color: '#625c57', overflowWrap: 'anywhere' })}><span style={S({ color: 'rgba(18,16,14,0.96)' })}>{r.backbone}</span> · {r.profile}{r.statusSfx}</span></span>
                <dl style={S({ margin: '0', display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '8px 14px', alignItems: 'baseline' })}>
                  <dt style={S({ fontSize: '12.5px', color: '#625c57' })}>Max message</dt><dd style={S({ margin: '0', font: '500 13px/1.3 \'IBM Plex Mono\',ui-monospace,monospace' })}>{r.bytes} B</dd>
                  <dt style={S({ fontSize: '12.5px', color: '#625c57' })}>Max change</dt><dd style={S({ margin: '0', font: '500 13px/1.3 \'IBM Plex Mono\',ui-monospace,monospace' })}>{r.cap} / 255</dd>
                  <dt style={S({ fontSize: '12.5px', color: '#625c57' })}>Read back</dt><dd style={S({ margin: '0', display: 'flex', flexDirection: 'column', gap: '5px' })}><span style={S({ font: '500 13px/1.3 \'IBM Plex Mono\',ui-monospace,monospace' })}>{r.ev}</span><span aria-hidden="true" style={S({ height: '6px', width: '120px', background: '#3f648c', borderRadius: '1px', display: 'block' })}></span><span style={S({ fontSize: '11.5px', color: '#625c57' })}>{r.evUnit}</span></dd>
                  <dt style={S({ fontSize: '12.5px', color: '#625c57' })}><button type="button" data-abbr="1" onClick={abOpen.PSNR} aria-expanded={abExp.PSNR} aria-controls="gf-abbr" style={S({ font: 'inherit', color: 'inherit', background: 'none', border: '0', padding: '0', margin: '0', borderBottom: '1px dashed currentColor', cursor: 'help', lineHeight: 'inherit' })}>PSNR</button> · <button type="button" data-abbr="1" onClick={abOpen.SSIM} aria-expanded={abExp.SSIM} aria-controls="gf-abbr" style={S({ font: 'inherit', color: 'inherit', background: 'none', border: '0', padding: '0', margin: '0', borderBottom: '1px dashed currentColor', cursor: 'help', lineHeight: 'inherit' })}>SSIM</button></dt><dd style={S({ margin: '0', font: '500 13px/1.3 \'IBM Plex Mono\',ui-monospace,monospace' })}>{r.psnr} · {r.ssim}</dd>
                </dl>
              </li>
            </React.Fragment>))}
          </ul>
          ) : (
          <table aria-labelledby="gf-modes-cap" style={S({ width: '100%', borderCollapse: 'collapse', minWidth: '560px' })}>
            <thead>
              <tr>
                <th scope="col" style={S({ textAlign: 'left', padding: '10px 14px', fontSize: '12.5px', fontWeight: '600', color: '#625c57', borderBottom: '1px solid rgba(24,20,17,0.10)' })}>Mode</th>
                <th scope="col" style={S({ textAlign: 'right', padding: '10px 14px', fontSize: '12.5px', fontWeight: '600', color: '#625c57', borderBottom: '1px solid rgba(24,20,17,0.10)' })}>Max message</th>
                <th scope="col" style={S({ textAlign: 'right', padding: '10px 14px', fontSize: '12.5px', fontWeight: '600', color: '#625c57', borderBottom: '1px solid rgba(24,20,17,0.10)' })}>Max change</th>
                <th scope="col" style={S({ textAlign: 'left', padding: '10px 14px', fontSize: '12.5px', fontWeight: '600', color: '#625c57', borderBottom: '1px solid rgba(24,20,17,0.10)' })}>Read back</th>
                <th scope="col" style={S({ textAlign: 'right', padding: '10px 14px', fontSize: '12.5px', fontWeight: '600', color: '#625c57', borderBottom: '1px solid rgba(24,20,17,0.10)' })}><button type="button" data-abbr="1" onClick={abOpen.PSNR} aria-expanded={abExp.PSNR} aria-controls="gf-abbr" style={S({ font: 'inherit', color: 'inherit', background: 'none', border: '0', padding: '0', margin: '0', borderBottom: '1px dashed currentColor', cursor: 'help', lineHeight: 'inherit' })}>PSNR</button> · <button type="button" data-abbr="1" onClick={abOpen.SSIM} aria-expanded={abExp.SSIM} aria-controls="gf-abbr" style={S({ font: 'inherit', color: 'inherit', background: 'none', border: '0', padding: '0', margin: '0', borderBottom: '1px dashed currentColor', cursor: 'help', lineHeight: 'inherit' })}>SSIM</button></th>
              </tr>
            </thead>
            <tbody>
              {modeRows.map((r, i) => (<React.Fragment key={i}>
                <tr>
                  <th scope="row" style={S({ textAlign: 'left', padding: '12px 14px', borderBottom: '1px solid rgba(24,20,17,0.07)', verticalAlign: 'top' })}>
                    <span style={S({ display: 'flex', flexDirection: 'column', gap: '3px' })}><span style={S({ fontSize: '14.5px', fontWeight: '600' })}>{r.label}</span><span style={S({ font: '400 11px/1.3 \'IBM Plex Mono\',ui-monospace,monospace', color: '#625c57' })}><span style={S({ color: 'rgba(18,16,14,0.96)' })}>{r.backbone}</span> · {r.profile}{r.statusSfx}</span></span>
                  </th>
                  <td style={S({ textAlign: 'right', padding: '12px 14px', borderBottom: '1px solid rgba(24,20,17,0.07)', font: '500 13px/1.3 \'IBM Plex Mono\',ui-monospace,monospace', verticalAlign: 'top', whiteSpace: 'nowrap' })}>{r.bytes} B</td>
                  <td style={S({ textAlign: 'right', padding: '12px 14px', borderBottom: '1px solid rgba(24,20,17,0.07)', font: '500 13px/1.3 \'IBM Plex Mono\',ui-monospace,monospace', verticalAlign: 'top', whiteSpace: 'nowrap' })}>{r.cap} / 255</td>
                  <td style={S({ padding: '12px 14px', borderBottom: '1px solid rgba(24,20,17,0.07)', verticalAlign: 'top' })}>
                    <span style={S({ display: 'flex', flexDirection: 'column', gap: '5px' })}><span style={S({ font: '500 13px/1.3 \'IBM Plex Mono\',ui-monospace,monospace' })}>{r.ev}</span><span aria-hidden="true" style={S({ height: '6px', width: '120px', background: '#3f648c', borderRadius: '1px', display: 'block' })}></span><span style={S({ fontSize: '11.5px', color: '#625c57' })}>{r.evUnit}</span></span>
                  </td>
                  <td style={S({ textAlign: 'right', padding: '12px 14px', borderBottom: '1px solid rgba(24,20,17,0.07)', font: '500 13px/1.3 \'IBM Plex Mono\',ui-monospace,monospace', verticalAlign: 'top', whiteSpace: 'nowrap' })}>{r.psnr} · {r.ssim}</td>
                </tr>
              </React.Fragment>))}
            </tbody>
          </table>
          )}
          <p style={S({ margin: '0', padding: '10px 14px', fontSize: '12.5px', lineHeight: '1.5', color: '#625c57' })}>Higher <button type="button" data-abbr="1" onClick={abOpen.PSNR} aria-expanded={abExp.PSNR} aria-controls="gf-abbr" style={S({ font: 'inherit', color: 'inherit', background: 'none', border: '0', padding: '0', margin: '0', borderBottom: '1px dashed currentColor', cursor: 'help', lineHeight: 'inherit' })}>PSNR</button> and <button type="button" data-abbr="1" onClick={abOpen.SSIM} aria-expanded={abExp.SSIM} aria-controls="gf-abbr" style={S({ font: 'inherit', color: 'inherit', background: 'none', border: '0', padding: '0', margin: '0', borderBottom: '1px dashed currentColor', cursor: 'help', lineHeight: 'inherit' })}>SSIM</button> mean closer to the original. Long changes the image visibly more than Subtle.</p>
          <p style={S({ margin: '0', padding: '0 14px 14px', fontSize: '12.5px', lineHeight: '1.5', color: '#625c57', textWrap: 'pretty' })}>Subtle and Long moved from SqueezeNet 1.1 to MobileNetV3-Small after a preregistered comparison of five image models. Same held-out reliability, {MODES.long.bytes} B instead of 302 B in Long, and about 1.6× faster encodes.</p>
        </div>

        <div style={S({ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(220px,1fr))', gap: '12px' })}>
          <div style={S({ display: 'flex', flexDirection: 'column', gap: '8px', padding: '16px', border: '1px solid rgba(24,20,17,0.10)', borderRadius: '8px', background: '#f6f4f1' })}>
            <span style={S({ fontSize: '13px', fontWeight: '600' })}>How long it takes</span>
            <dl style={S({ margin: '0', display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '5px 12px', font: '400 12.5px/1.45 \'IBM Plex Mono\',ui-monospace,monospace' })}>
              <dt style={S({ color: '#625c57' })}>encode</dt><dd style={S({ margin: '0' })}>usually under 2 minutes; stopped after 5 min</dd>
              <dt style={S({ color: '#625c57' })}>queue</dt><dd style={S({ margin: '0' })}>one encode at a time, with a daily cap</dd>
              <dt style={S({ color: '#625c57' })}>decode</dt><dd style={S({ margin: '0' })}>a few seconds</dd>
            </dl>
            <span style={S({ fontSize: '11.5px', lineHeight: '1.45', color: '#625c57' })}>Times vary with the photo and with how busy the demo server is.</span>
          </div>
          <div style={S({ display: 'flex', flexDirection: 'column', gap: '8px', padding: '16px', border: '1px solid rgba(24,20,17,0.10)', borderRadius: '8px', background: '#f6f4f1' })}>
            <div style={S({ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '6px' })}>
              <span style={S({ fontSize: '13px', fontWeight: '600' })}>Flat, synthetic or tiny images</span>
              <span style={S({ display: 'inline-flex', alignItems: 'center', gap: '5px', font: '500 10.5px/1.2 \'IBM Plex Mono\',ui-monospace,monospace', color: '#9f3b3b', padding: '3px 8px', border: '1px solid rgba(159,59,59,0.45)', borderRadius: '999px', background: '#fff' })}><span aria-hidden="true" style={S({ fontWeight: '700' })}>!</span>Known limitation</span>
            </div>
            <div style={S({ display: 'flex', flexDirection: 'column', gap: '8px' })}>
              {hardRows.map((h, i) => (<React.Fragment key={i}>
                <div style={S({ display: 'flex', flexDirection: 'column', gap: '4px' })}>
                  <span style={S({ display: 'flex', justifyContent: 'space-between', font: '500 12.5px/1.2 \'IBM Plex Mono\',ui-monospace,monospace' })}><span>{h.label}</span><span>{h.n}/{h.cells.length} encoded</span></span>
                  <span aria-hidden="true" style={S({ display: 'grid', gridTemplateColumns: `repeat(${h.cells.length},1fr)`, gap: '2px' })}>
                    {h.cells.map((c, i) => (<React.Fragment key={i}><span style={S({ height: '10px', background: c, borderRadius: '1px', display: 'block' })}></span></React.Fragment>))}
                  </span>
                </div>
              </React.Fragment>))}
            </div>
            <span style={S({ fontSize: '12px', lineHeight: '1.45', color: '#625c57' })}>Blank backgrounds, solid colours, colour bars, line art and near-minimum sizes. {smallSentence}</span>
          </div>
        </div>

        <div style={S({ display: 'flex', flexDirection: 'column', gap: '0', borderTop: '1px solid rgba(24,20,17,0.10)' })}>
          {links.map((l, i) => (<React.Fragment key={i}>
            <div style={S({ display: 'flex', flexWrap: 'wrap', gap: '4px 16px', justifyContent: 'space-between', alignItems: 'baseline', padding: '12px 0', borderBottom: '1px solid rgba(24,20,17,0.10)' })}>
              <span style={S({ display: 'flex', flexDirection: 'column', gap: '2px' })}><span style={S({ fontSize: '15px', fontWeight: '600' })}>{l.t}</span><span style={S({ fontSize: '13px', color: '#625c57' })}>{l.d}</span></span>
              <a href={l.href} target="_blank" rel="noopener" style={S({ font: '500 12px/1.3 \'IBM Plex Mono\',ui-monospace,monospace', color: '#355574', background: '#f1eee9', padding: '4px 8px', borderRadius: '3px', overflowWrap: 'anywhere' })}>{l.ph}</a>
            </div>
          </React.Fragment>))}
        </div>
      </div>
    </div>
  </div>
</section>

  );
}
