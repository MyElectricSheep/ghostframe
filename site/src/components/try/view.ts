// View model for "Try it". Names mirror the design reference (wVals / t4Vals / t5Vals in
// Ghostframe v3.dc.html) so each value can be traced back to the prototype:
// w* = the image stage, t4* = the dot strip, t5* = the pixel inspector.
import { useEffect, useRef, useState } from 'react';
import type React from 'react';
import { useNarrow } from '../../hooks/useNarrow';
import { BLUE, fixture, fixturePath, heat, INK, MODES, ORDER, PHOTOS, PORDER, resultLine } from '../../data';
import type { ModeKey, PhotoKey } from '../../data';

export type View = 'compare' | 'diff' | 'embed';
export const VIEWS: [View, string][] = [['compare', 'Original vs encoded'], ['diff', 'Amplified difference'], ['embed', 'What the model sees']];

const tint = (cos: number) => { const t = Math.max(0, Math.min(1, (0.95 - cos) / 0.80)); return 'rgba(63,100,140,' + (0.06 + 0.8 * t).toFixed(3) + ')'; };

export interface TryItState {
  photo: PhotoKey; mode: ModeKey; view: View;
  split: number; sel: number | null; tip: ModeKey | null; info: boolean; infoPinned: boolean; knob: boolean;
  pt: { fx: number; fy: number };
}
export const initialTryIt = (): Omit<TryItState, 'photo' | 'mode'> => ({
  view: 'compare', split: 50, sel: null, tip: null, info: false, infoPinned: false, knob: false, pt: { fx: 0.5, fy: 0.42 },
});

type Pixels = { o: ImageData; m: ImageData } | null;

/** Decoded pixels of original.png and <mode>.png, for the colour-value inspector. */
function usePixels(photo: PhotoKey, mode: ModeKey): Pixels {
  const cache = useRef(new Map<string, Pixels | 'loading'>());
  const [, bump] = useState(0);
  const key = photo + '|' + mode;
  useEffect(() => {
    if (cache.current.has(key)) return;
    cache.current.set(key, 'loading');
    const load = (f: string) => new Promise<HTMLImageElement>((res, rej) => { const im = new Image(); im.onload = () => res(im); im.onerror = rej; im.src = fixturePath(photo, f); });
    const read = (im: HTMLImageElement) => {
      const c = document.createElement('canvas'); c.width = im.naturalWidth; c.height = im.naturalHeight;
      const x = c.getContext('2d', { willReadFrequently: true })!; x.drawImage(im, 0, 0);
      return x.getImageData(0, 0, c.width, c.height);
    };
    Promise.all([load('original.png'), load(mode + '.png')])
      .then(([o, m]) => { cache.current.set(key, { o: read(o), m: read(m) }); bump((n) => n + 1); })
      .catch(() => cache.current.delete(key));
  }, [key, photo, mode]);
  const v = cache.current.get(key);
  return v && v !== 'loading' ? v : null;
}

export function useTryItView(s: TryItState, set: (patch: Partial<TryItState>) => void, pick: (photo: PhotoKey, mode: ModeKey) => void) {
  const narrow = useNarrow();
  const stageRef = useRef<HTMLDivElement>(null);
  const D = usePixels(s.photo, s.mode);
  const P = PHOTOS[s.photo], M = MODES[s.mode];
  const fl = ([] as number[]).concat(...heat(s.photo, s.mode)), cols = M.cols, rows = M.rows, cap = M.cap, amp = M.amp;
  let mi = 0; fl.forEach((v, i) => { if (v < fl[mi]) mi = i; });
  const sel = s.sel != null && s.sel < fl.length ? s.sel : mi;

  // ---- stage (wVals)
  const wHandleDown = (e: React.PointerEvent) => {
    e.preventDefault();
    const el = stageRef.current; if (!el) return;
    const to = (x: number) => { const r = el.getBoundingClientRect(); set({ split: Math.round(Math.max(0, Math.min(100, (x - r.left) / r.width * 100))) }); };
    const move = (ev: PointerEvent) => to(ev.clientX);
    const up = () => { window.removeEventListener('pointermove', move); window.removeEventListener('pointerup', up); };
    window.addEventListener('pointermove', move); window.addEventListener('pointerup', up);
  };
  const th = Math.acos(fl[sel]), b0 = 12 * Math.PI / 180;
  const pt = (a: number, r: number) => [20 + r * Math.cos(a), 175 - r * Math.sin(a)];
  const [bx, by] = pt(b0, 150), [ax, ay] = pt(b0 + th, 150), [x1, y1] = pt(b0, 46), [x2, y2] = pt(b0 + th, 46), [tx, ty] = pt(b0 + th / 2, 62);
  const degs = fl.map((v) => Math.acos(v) * 180 / Math.PI).sort((a, b) => a - b), dg = Math.round(th * 180 / Math.PI), med = Math.round(degs[Math.floor(degs.length / 2)]);
  const FX = fixture(s.photo, s.mode), embed = s.view === 'embed', diff = s.view === 'diff', cmp = s.view === 'compare';
  // Every view has the divider: original on the left; marked, tinted or amplified difference on the right.
  const slider = cmp || embed || diff;
  const mLabel = M.label;
  const dir = (f: string) => fixturePath(s.photo, f);

  // ---- dot strip (t4Vals)
  const ang = fl.map((v) => Math.acos(v) * 180 / Math.PI);
  const sorted = [...ang].sort((a, b) => a - b), t4med = sorted[Math.floor(sorted.length / 2)];
  const lab = (i: number) => 'Tile row ' + (Math.floor(i / cols) + 1) + ', column ' + (i % cols + 1) + ', ' + Math.round(ang[i]) + ' degrees';
  const Pd = (deg: number, r: number) => { const a = deg * Math.PI / 180; return [20 + r * Math.cos(a), 160 - r * Math.sin(a)]; };
  const [mdx, mdy] = Pd(t4med, 150), [mlx, mly] = Pd(t4med, 162);
  const jit = (i: number) => ((i * 37) % 11) / 11;

  // ---- pixel inspector (t5Vals)
  const p5 = s.pt;
  let O: (number | string)[] = ['…', '…', '…'], Mk: (number | string)[] = ['…', '…', '…'], Dl = ['', '', ''], line = 'Loading the two files…';
  const patch: { v: string; bg: string; fg: string }[] = [];
  if (D) {
    const W = D.o.width, H = D.o.height, x = Math.min(W - 1, Math.floor(p5.fx * W)), y = Math.min(H - 1, Math.floor(p5.fy * H)), i = (y * W + x) * 4;
    const o = [0, 1, 2].map((c) => D.o.data[i + c]), m = [0, 1, 2].map((c) => D.m.data[i + c]);
    O = o; Mk = m;
    const dd = [0, 1, 2].map((c) => m[c] - o[c]); Dl = dd.map((d) => (d > 0 ? '+' : d < 0 ? '−' : '±') + Math.abs(d));
    const n = dd.filter((d) => d !== 0).length;
    line = 'Pixel ' + x + ', ' + y + ': ' + (n ? n + ' of 3 colour values changed, by at most ' + Math.max(...dd.map(Math.abs)) + ' of 255.' : 'unchanged here.') + ' Cap for this mode: ' + cap + '.';
    for (let yy = -3; yy <= 3; yy++) for (let xx = -3; xx <= 3; xx++) {
      const X = Math.max(0, Math.min(W - 1, x + xx)), Y = Math.max(0, Math.min(H - 1, y + yy)), j = (Y * W + X) * 4 + 1, d = D.m.data[j] - D.o.data[j];
      const g = Math.max(0, Math.min(255, 128 + d * amp));
      patch.push({ v: d === 0 ? '0' : (d > 0 ? '+' : '−') + Math.abs(d), bg: 'rgb(' + g + ',' + g + ',' + g + ')', fg: g > 150 ? 'rgba(18,16,14,0.9)' : '#fff' });
    }
  } else for (let k = 0; k < 49; k++) patch.push({ v: '', bg: '#ddd', fg: '#000' });
  const sw: { d: string; bg: string }[] = [];
  for (let d = -cap; d <= cap; d += cap > 4 ? 2 : 1) { const g = Math.max(0, Math.min(255, 128 + d * amp)); sw.push({ d: (d > 0 ? '+' : d < 0 ? '−' : '') + Math.abs(d), bg: 'rgb(' + g + ',' + g + ',' + g + ')' }); }
  // Pixel inspector: follows the mouse, and a finger or pen held down and dragged across the picture
  // (the pointer is captured, so the drag keeps tracking even past the picture's edge).
  const t5Move = (e: React.PointerEvent<HTMLElement> | React.MouseEvent<HTMLElement>) => {
    if ('pointerType' in e && e.pointerType !== 'mouse' && e.type === 'pointerdown') e.currentTarget.setPointerCapture(e.pointerId);
    const r = e.currentTarget.querySelector('img')!.getBoundingClientRect();
    set({ pt: { fx: Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)), fy: Math.max(0, Math.min(1, (e.clientY - r.top) / r.height)) } });
  };

  // Arrow keys move between tiles (the tiles are buttons; Tab reaches them).
  const wTileKeys = (e: React.KeyboardEvent<HTMLElement>) => {
    const from = Number((e.target as HTMLElement).dataset.index);
    if (Number.isNaN(from)) return;
    const step = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -cols, ArrowDown: cols }[e.key];
    if (step === undefined) return;
    const to = from + step;
    if (to < 0 || to >= fl.length || (Math.abs(step) === 1 && Math.floor(to / cols) !== Math.floor(from / cols))) return;
    e.preventDefault();
    set({ sel: to });
    (e.currentTarget.querySelector(`[data-index="${to}"]`) as HTMLElement | null)?.focus();
  };

  return {
    wTileKeys,
    // controls
    wCovers: PORDER.map((k) => { const p = PHOTOS[k], on = k === s.photo; return { label: p.label, src: p.thumb, pos: p.pos, pressed: on, bd: on ? BLUE : 'rgba(24,20,17,0.12)', bg: on ? '#f5f8fb' : '#fff', onClick: () => pick(k, s.mode) }; }),
    wModeList: ORDER.map((k) => { const m = MODES[k], on = k === s.mode; return { label: m.label, cap: m.cap, pressed: on, bd: on ? BLUE : 'rgba(24,20,17,0.12)', bg: on ? '#f5f8fb' : '#fff', onClick: () => { pick(s.photo, k); set({ tip: k }); },
      tipId: 'tip-' + k, tip: m.tip, max: m.bytes, grid: m.cols + ' × ' + m.rows, status: '', tipDisp: s.tip === k ? 'flex' : 'none', onEnter: () => set({ tip: k }), onLeave: () => { if (s.tip === k) set({ tip: null }); } }; }),
    // Tooltips open on hover, focus or tap; a tap outside or Esc closes them (Controls).
    wTip: s.tip, wTipClose: () => set({ tip: null }),
    wViewList: VIEWS.map(([k, l]) => { const on = k === s.view; return { label: l, pressed: on, bg: on ? '#f5f8fb' : 'transparent', dot: on ? BLUE : '#fff', dotBd: on ? BLUE : '#a39b93', weight: on ? 600 : 500, onClick: () => set({ view: k }) }; }),
    // stage
    wStageRef: stageRef, wHandleDown, wFrameRadius: '6px',
    wStageW: s.photo === 'antonello' ? '420px' : '560px', wStageMax: s.photo === 'antonello' ? '600px' : '900px', wAspect: P.aspect,
    wCompare: cmp, wEmbed: embed, wNotEmbed: !embed, wDiffOn: diff, wDivider: slider, wSliderHint: cmp || diff,
    wOrig: dir('original.png'), wMarked: dir(s.mode + '.png'), wDiff: dir(s.mode + '-difference.png'),
    wOrigDisp: 'block', wMarkedDisp: cmp || embed ? 'block' : 'none', wDiffDisp: diff ? 'block' : 'none', wClip: slider ? s.split + '%' : '0%',
    wStageAlt: P.label + ' · ' + mLabel,
    wFrameL: 'original', wFrameR: embed ? 'embedding change · ' + mLabel.toLowerCase() : diff ? (narrow ? '×' + amp + ' · not the photo' : 'amplified ×' + amp + ' · real maximum ' + cap + '/255 · not the photo') : mLabel.toLowerCase() + ' · marked',
    wTagL: 'Original', wTagLDisp: slider ? 'block' : 'none',
    wTagR: diff ? 'Amplified difference ×' + amp : embed ? 'Marked · embedding change' : 'Encoded', wTagRBg: diff || embed ? BLUE : 'rgba(18,16,14,0.82)',
    wSplit: s.split, wSplitPct: s.split + '%', wSplitText: s.split + '% original', wOnSplit: (e: React.ChangeEvent<HTMLInputElement>) => set({ split: +e.target.value }),
    wKnobFocus: () => set({ knob: true }), wKnobBlur: () => set({ knob: false }), wKnobRing: s.knob ? '2px solid #3f648c' : 'none',
    wCols: cols, wRows: rows,
    wCells: fl.map((v, i) => { const right = ((i % cols) + 0.5) / cols * 100 > s.split, on = i === sel; return { aria: 'Tile row ' + (Math.floor(i / cols) + 1) + ', column ' + (i % cols + 1) + ', turned ' + Math.round(Math.acos(v) * 180 / Math.PI) + ' degrees', pressed: on, bg: right ? tint(v) : 'transparent', line: right ? 'rgba(255,255,255,0.35)' : 'rgba(255,255,255,0.12)', sh: on ? 'inset 0 0 0 2px #fff, inset 0 0 0 4px #3f648c' : 'none', onClick: () => set({ sel: i }) }; }),
    wR: Math.floor(sel / cols) + 1, wC: sel % cols + 1, wCos: fl[sel].toFixed(2), wDeg: dg + '°', wMed: med, wMax: Math.round(degs[degs.length - 1]),
    wHeadline: sel === mi ? 'The tile that turned most' : dg >= med ? 'Turned more than the median tile' : 'Turned less than the median tile',
    wBx: bx.toFixed(1), wBy: by.toFixed(1), wAx: ax.toFixed(1), wAy: ay.toFixed(1), wBlx: (bx - 40).toFixed(1), wBly: (by + 22).toFixed(1), wAlx: (ax + 7).toFixed(1), wAly: Math.max(12, ay + 4).toFixed(1),
    wArc: 'M ' + x1.toFixed(1) + ' ' + y1.toFixed(1) + ' A 46 46 0 0 0 ' + x2.toFixed(1) + ' ' + y2.toFixed(1),
    wDegLeft: ((tx + 6) / 220 * 100).toFixed(2) + '%', wDegTop: ((ty - 6) / 190 * 100).toFixed(2) + '%', wDialAria: 'Before and after arrows ' + dg + ' degrees apart',
    wCap: cap, wProfile: M.profile, wChanged: Math.round(FX.changed * 1000) / 10 + '% of colour values changed', wRes: resultLine(s.photo, s.mode),
    infoShow: () => { if (!s.info) set({ info: true }); }, infoHide: () => { if (s.info && !s.infoPinned) set({ info: false }); },
    infoToggle: () => set({ info: !(s.info && s.infoPinned), infoPinned: !(s.info && s.infoPinned) }),
    infoDisp: s.info ? 'flex' : 'none', infoOpenStr: s.info, infoBg: s.info ? '#f6f4f1' : 'transparent', infoFg: s.info ? INK : '#f6f4f1', infoBd: s.info ? '#f6f4f1' : 'rgba(246,244,241,0.6)',
    wDim: M.dim, wModel: M.backbone, wModeLabel: M.label,
    // dot strip
    t4MedX: mdx.toFixed(1), t4MedY: mdy.toFixed(1), t4MedLx: (mlx + 4).toFixed(0) + 'px', t4MedLy: (mly - 12).toFixed(0) + 'px',
    t4Dots: fl.map((_, i) => { const r = 70 + jit(i) * 66, [x, y] = Pd(ang[i], r), on = i === sel, sz = on ? 12 : 8; return { x: x.toFixed(1) + 'px', y: y.toFixed(1) + 'px', s: sz + 'px', m: (-sz / 2) + 'px 0 0 ' + (-sz / 2) + 'px', bg: on ? BLUE : 'rgba(63,100,140,0.35)', bd: on ? '2px solid #fff' : '0', z: on ? 2 : 1, aria: lab(i), onClick: () => set({ sel: i }) }; }),
    // pixel inspector
    t5Move, t5Marked: dir(s.mode + '.png'), t5DiffSrc: dir(s.mode + '-difference.png'), t5ThumbW: s.photo === 'antonello' ? '180px' : '300px',
    t5Lx: (p5.fx * 100) + '%', t5Ly: (p5.fy * 100) + '%',
    t5O0: O[0], t5O1: O[1], t5O2: O[2], t5M0: Mk[0], t5M1: Mk[1], t5M2: Mk[2], t5D0: Dl[0], t5D1: Dl[1], t5D2: Dl[2],
    t5OSw: D ? 'rgb(' + O.join(',') + ')' : '#ddd', t5MSw: D ? 'rgb(' + Mk.join(',') + ')' : '#ddd', t5Line: line,
    t5Amp: amp, t5Sw: sw, t5SwN: sw.length, t5Patch: patch, t5ZoomLabel: '7 × 7 pixels around the marker',
  };
}

export type TryItView = ReturnType<typeof useTryItView>;
