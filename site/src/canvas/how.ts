// "How it works" step animations (drawHow, 1120 × 840). Below 560 px the
// page draws drawHowNarrow instead: a 560 × 700 (4:5) composition with the visual on top and the
// labels below, drawn at the canvas's real size so no text is under 11 CSS px.
type Ctx = CanvasRenderingContext2D;
type Img = HTMLImageElement | null;
interface TextOpts { weight?: number; mono?: boolean; align?: CanvasTextAlign; base?: CanvasTextBaseline; alpha?: number }
interface Cell { bg?: string; bd?: string; fg?: string }

export const HOW_DUR = [8000, 7000, 7000, 9000, 9000];
export const HOW_LABELS = ['01 · the passphrase locks the message', '02 · error-correction bytes are added', '03 · the photo is split into tiles', '04 · tiles are nudged until the model reads the bits', '05 · reading back with the same model'];
const hClamp = (v: number) => Math.max(0, Math.min(1, v));
const hSeg = (t: number, a: number, b: number) => hClamp((t - a) / (b - a));
const hEase = (x: number) => x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
const HINK = 'rgba(18,16,14,0.96)', HGRAY = '#625c57', HBLUE = '#3f648c', HPAPER = '#f6f4f1', HRED = '#9f3b3b';
const HMSG = 'Trust no one.', HHEX = ['9f', '3a', 'c7', '1e', '58', 'b2', '04', 'e9', '7d', 'a1', '6c', 'f0', '2b'];
const HBITS = [1, 0, 1, 1, 0, 0, 1, 0, 0, 1, 1, 0, 1, 0, 0, 1], HSTART = [0, 1, 1, 0, 0, 1, 0, 0, 1, 1, 0, 1, 1, 0, 1, 1];
function hRound(x: Ctx, X: number, Y: number, W: number, H: number, r: number) { x.beginPath(); x.moveTo(X + r, Y); x.arcTo(X + W, Y, X + W, Y + H, r); x.arcTo(X + W, Y + H, X, Y + H, r); x.arcTo(X, Y + H, X, Y, r); x.arcTo(X, Y, X + W, Y, r); x.closePath(); }
function hText(x: Ctx, s: string, X: number, Y: number, size: number, color: string, opts?: TextOpts) { opts = opts || {}; x.font = (opts.weight || 500) + ' ' + size + 'px ' + (opts.mono ? '"IBM Plex Mono", ui-monospace, monospace' : 'Inter, system-ui, sans-serif'); x.fillStyle = color; x.textAlign = opts.align || 'left'; x.textBaseline = opts.base || 'alphabetic'; x.globalAlpha = opts.alpha == null ? 1 : opts.alpha; x.fillText(s, X, Y); x.globalAlpha = 1; }
function hLock(x: Ctx, cx: number, cy: number, s: number, closed: number, color: string) {
  x.save(); x.strokeStyle = color; x.fillStyle = color; x.lineWidth = s * 0.12;
  const top = cy - s * 0.1, lift = (1 - closed) * s * 0.35, arcY = top - s * 0.05 - lift, r = s * 0.3;
  hRound(x, cx - s / 2, top, s, s * 0.75, s * 0.1); x.fill();
  // Right leg stays in the body; the left leg reaches it only as the shackle closes.
  x.beginPath(); x.moveTo(cx - r, arcY + (top - arcY) * closed); x.lineTo(cx - r, arcY); x.arc(cx, arcY, r, Math.PI, 0); x.lineTo(cx + r, top + s * 0.05); x.stroke();
  x.restore();
}
/** Fills text wrapped to maxW, one line per lineH, starting at baseline Y. */
function hWrap(x: Ctx, s: string, X: number, Y: number, maxW: number, size: number, lineH: number, color: string, opts?: TextOpts) {
  opts = opts || {};
  x.font = (opts.weight || 500) + ' ' + size + 'px ' + (opts.mono ? '"IBM Plex Mono", ui-monospace, monospace' : 'Inter, system-ui, sans-serif');
  const lines: string[] = []; let line = '';
  for (const w of s.split(' ')) { const t = line ? line + ' ' + w : w; if (line && x.measureText(t).width > maxW) { lines.push(line); line = w; } else line = t; }
  lines.push(line);
  lines.forEach((l, i) => hText(x, l, X, Y + i * lineH, size, color, opts));
}
function hPhoto(x: Ctx, img: Img, X: number, Y: number, W: number, H: number) { if (!img) { x.fillStyle = '#d9d3cc'; x.fillRect(X, Y, W, H); return; } const r = Math.max(W / img.naturalWidth, H / img.naturalHeight), dw = img.naturalWidth * r, dh = img.naturalHeight * r; x.save(); x.beginPath(); x.rect(X, Y, W, H); x.clip(); x.drawImage(img, X + (W - dw) / 2, Y + (H - dh) / 2, dw, dh); x.restore(); }
function hBitRow(x: Ctx, bits: (number | null)[], X: number, Y: number, cell: number, colorFn?: (i: number, b: number | null) => Cell | null, size?: number) { bits.forEach((b, i) => { const c = colorFn ? colorFn(i, b) : null; hRound(x, X + i * (cell + 6), Y, cell, cell, 5); x.fillStyle = c && c.bg || '#fff'; x.fill(); x.strokeStyle = c && c.bd || 'rgba(24,20,17,0.2)'; x.lineWidth = 2; x.stroke(); if (b != null) hText(x, String(b), X + i * (cell + 6) + cell / 2, Y + cell / 2 + 1, size || cell * 0.5, c && c.fg || HINK, { mono:true, align:'center', base:'middle' }); }); }
export function drawHow(x: Ctx, img: Img, step: number, t: number) {
  const W = 1120, H = 840; x.clearRect(0, 0, W, H); x.fillStyle = HPAPER; x.fillRect(0, 0, W, H);
  if (step === 0) {
    const a = hSeg(t, 0.04, 0.3), n = Math.round(a * HMSG.length);
    hText(x, 'message', 160, 150, 26, HGRAY, { mono:true });
    hRound(x, 160, 170, 800, 110, 14); x.fillStyle = '#fff'; x.fill(); x.strokeStyle = 'rgba(24,20,17,0.15)'; x.lineWidth = 2; x.stroke();
    const enc = hSeg(t, 0.48, 0.78), nEnc = Math.floor(enc * HMSG.length);
    for (let i = 0; i < HMSG.length; i++) { const isHex = i < nEnc; const s = isHex ? HHEX[i] : (i < n ? HMSG[i] : ''); hText(x, s, 200 + i * 58, 240, isHex ? 30 : 44, isHex ? HBLUE : HINK, { mono:true, weight:isHex ? 500 : 600 }); }
    const p = hSeg(t, 0.25, 0.42);
    hText(x, 'passphrase', 160, 380, 26, HGRAY, { mono:true, alpha:p });
    hRound(x, 160, 400, 380, 84, 14); x.globalAlpha = p; x.fillStyle = '#fff'; x.fill(); x.strokeStyle = 'rgba(24,20,17,0.15)'; x.stroke(); x.globalAlpha = 1;
    for (let i = 0; i < Math.round(p * 9); i++) { x.beginPath(); x.arc(200 + i * 34, 442, 9, 0, Math.PI * 2); x.fillStyle = HINK; x.fill(); }
    const k = hSeg(t, 0.38, 0.5);
    if (k > 0) { x.globalAlpha = k; x.strokeStyle = HGRAY; x.lineWidth = 3; x.setLineDash([8, 8]); x.beginPath(); x.moveTo(560, 442); x.lineTo(660, 442); x.stroke(); x.setLineDash([]);
      hRound(x, 680, 400, 280, 84, 14); x.fillStyle = '#eaf1f7'; x.fill(); x.strokeStyle = HBLUE; x.lineWidth = 2; x.stroke();
      hText(x, 'key (scrypt)', 820, 452, 28, HBLUE, { mono:true, align:'center' }); x.globalAlpha = 1;
      x.strokeStyle = HBLUE; x.lineWidth = 3; x.beginPath(); x.moveTo(820, 400); x.lineTo(820, 300); x.stroke(); x.beginPath(); x.moveTo(808, 314); x.lineTo(820, 296); x.lineTo(832, 314); x.stroke(); }
    if (enc > 0) hText(x, 'encrypted bytes', 960, 150, 26, HBLUE, { mono:true, align:'right', alpha:enc });
    const lk = hSeg(t, 0.8, 0.92);
    if (lk > 0) { x.globalAlpha = lk; hLock(x, 1010, 220, 60, hEase(lk), HBLUE); x.globalAlpha = 1; }
    hWrap(x, 'Without the passphrase, the message can’t be read, as long as the passphrase is hard to guess.', 560, 610, 900, 32, 42, HINK, { align:'center', weight:600, alpha:hSeg(t, 0.85, 0.97) });
    hText(x, 'AES-256-GCM: tampering is detected, not just hidden.', 560, 710, 24, HGRAY, { align:'center', alpha:hSeg(t, 0.88, 1) });
  } else if (step === 1) {
    const cell = 46, gap = 6, n = 13, ecc = 6, X0 = 560 - ((n + ecc) * (cell + gap) - gap) / 2, Y0 = 330;
    const a = hSeg(t, 0.02, 0.3);
    hText(x, 'encrypted message', X0, Y0 - 30, 24, HGRAY, { mono:true, alpha:a });
    for (let i = 0; i < n; i++) { const p = hSeg(a, i / n * 0.6, i / n * 0.6 + 0.4); x.globalAlpha = p; const bad = i === 5 && t > 0.62 && t < 0.86; hRound(x, X0 + i * (cell + gap), Y0 + (1 - p) * 30, cell, cell, 8); x.fillStyle = bad ? '#fbecec' : '#fff'; x.fill(); x.strokeStyle = bad ? HRED : 'rgba(24,20,17,0.2)'; x.lineWidth = 2; x.stroke(); hText(x, bad ? '??' : HHEX[i], X0 + i * (cell + gap) + cell / 2, Y0 + cell / 2 + 8 + (1 - p) * 30, 20, bad ? HRED : HINK, { mono:true, align:'center' }); x.globalAlpha = 1; }
    const b = hSeg(t, 0.32, 0.55);
    if (b > 0) hText(x, 'repair bytes', X0 + n * (cell + gap), Y0 - 30, 24, HBLUE, { mono:true, alpha:b });
    for (let i = 0; i < ecc; i++) { const p = hSeg(b, i / ecc * 0.6, i / ecc * 0.6 + 0.4); if (p <= 0) continue; x.globalAlpha = p; const X = X0 + (n + i) * (cell + gap); hRound(x, X, Y0 - (1 - p) * 40, cell, cell, 8); x.fillStyle = '#eaf1f7'; x.fill(); x.strokeStyle = HBLUE; x.lineWidth = 2; x.stroke(); hText(x, '+', X + cell / 2, Y0 + cell / 2 + 12 - (1 - p) * 40, 34, HBLUE, { mono:true, align:'center' }); x.globalAlpha = 1; }
    const dmg = hSeg(t, 0.6, 0.68), fix = hSeg(t, 0.82, 0.9);
    if (dmg > 0 && fix < 1) { hText(x, 'a byte gets damaged on the way', 560, 520, 30, HRED, { align:'center', weight:600, alpha:dmg * (1 - fix) }); }
    if (fix > 0) { hText(x, 'the repair bytes fix it', 560, 520, 30, HBLUE, { align:'center', weight:600, alpha:fix }); const X = X0 + 5 * (cell + gap) + cell / 2; x.globalAlpha = fix; x.strokeStyle = HBLUE; x.lineWidth = 4; x.beginPath(); x.moveTo(X - 14, Y0 + cell + 30); x.lineTo(X - 4, Y0 + cell + 40); x.lineTo(X + 16, Y0 + cell + 18); x.stroke(); x.globalAlpha = 1; }
    hText(x, 'Only a few wrong bits can be repaired. Too many, and nothing is shown.', 560, 640, 24, HGRAY, { align:'center', alpha:hSeg(t, 0.9, 1) });
  } else if (step === 2 || step === 4) {
    const PW = 400, PH2 = Math.round(PW * 1782 / 1280), PX = step === 2 ? 360 : 120, PY = (H - PH2) / 2;
    hPhoto(x, img, PX, PY, PW, PH2);
    const cols = 10, rows = 8, tw = PW / cols, th = PH2 / rows;
    if (step === 2) {
      const gv = hEase(hSeg(t, 0.06, 0.4)), gh = hEase(hSeg(t, 0.3, 0.62));
      x.strokeStyle = 'rgba(255,255,255,0.85)'; x.lineWidth = 2;
      for (let c = 1; c < cols; c++) { x.beginPath(); x.moveTo(PX + c * tw, PY); x.lineTo(PX + c * tw, PY + PH2 * gv); x.stroke(); }
      for (let r = 1; r < rows; r++) { x.beginPath(); x.moveTo(PX, PY + r * th); x.lineTo(PX + PW * gh, PY + r * th); x.stroke(); }
      const wave = hSeg(t, 0.62, 0.82);
      if (wave > 0 && wave < 1) for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) { const d = (r + c) / (rows + cols - 2), a = Math.max(0, 1 - Math.abs(wave * 1.3 - d) * 6); if (a > 0) { x.fillStyle = 'rgba(63,100,140,' + (0.45 * a) + ')'; x.fillRect(PX + c * tw, PY + r * th, tw, th); } }
      const hl = hSeg(t, 0.82, 0.92);
      if (hl > 0) { x.globalAlpha = hl; x.strokeStyle = '#fff'; x.lineWidth = 4; x.strokeRect(PX + 4 * tw, PY + 3 * th, tw, th); x.strokeStyle = HBLUE; x.lineWidth = 3; x.strokeRect(PX + 4 * tw - 3, PY + 3 * th - 3, tw + 6, th + 6); x.globalAlpha = 1; }
      hText(x, '10 × 8 = 80 tiles', PX + PW + 40, PY + 90, 34, HINK, { weight:600, alpha:hSeg(t, 0.62, 0.74) });
      hText(x, 'for Subtle and Long', PX + PW + 40, PY + 130, 24, HGRAY, { alpha:hSeg(t, 0.64, 0.76) });
      hText(x, '6 × 5 = 30 tiles', PX + PW + 40, PY + 200, 30, HINK, { weight:600, alpha:hSeg(t, 0.72, 0.84) });
      hText(x, 'for Short', PX + PW + 40, PY + 236, 24, HGRAY, { alpha:hSeg(t, 0.74, 0.86) });
      hText(x, 'Each tile is read', PX + PW + 40, PY + 330, 26, HBLUE, { weight:600, alpha:hSeg(t, 0.86, 0.96) });
      hText(x, 'on its own.', PX + PW + 40, PY + 364, 26, HBLUE, { weight:600, alpha:hSeg(t, 0.86, 0.96) });
    } else {
      x.strokeStyle = 'rgba(255,255,255,0.6)'; x.lineWidth = 1.5;
      for (let c = 1; c < cols; c++) { x.beginPath(); x.moveTo(PX + c * tw, PY); x.lineTo(PX + c * tw, PY + PH2); x.stroke(); }
      for (let r = 1; r < rows; r++) { x.beginPath(); x.moveTo(PX, PY + r * th); x.lineTo(PX + PW, PY + r * th); x.stroke(); }
      const scan = hSeg(t, 0.04, 0.56), total = cols * rows, k = Math.floor(scan * total);
      for (let i = 0; i < Math.min(k, total); i++) { const r = Math.floor(i / cols), c = i % cols; x.fillStyle = 'rgba(63,100,140,0.22)'; x.fillRect(PX + c * tw, PY + r * th, tw, th); }
      if (k < total && scan > 0) { const r = Math.floor(k / cols), c = k % cols; x.strokeStyle = '#fff'; x.lineWidth = 4; x.strokeRect(PX + c * tw, PY + r * th, tw, th); }
      const RX = 600;
      hText(x, 'same frozen model', RX, 170, 24, HGRAY, { mono:true });
      hText(x, 'reads each tile', RX, 210, 34, HINK, { weight:600 });
      const nb = Math.floor(scan * 32);
      for (let i = 0; i < 32; i++) { const r = Math.floor(i / 8), c = i % 8, X = RX + c * 52, Y = 250 + r * 52; hRound(x, X, Y, 44, 44, 6); x.fillStyle = i < nb ? '#eaf1f7' : '#fff'; x.fill(); x.strokeStyle = i < nb ? HBLUE : 'rgba(24,20,17,0.15)'; x.lineWidth = 2; x.stroke(); if (i < nb) hText(x, String((HBITS[i % 16] + (i >> 4)) % 2), X + 22, Y + 31, 24, HBLUE, { mono:true, align:'center' }); }
      const rep = hSeg(t, 0.58, 0.68), un = hSeg(t, 0.7, 0.82), msg = hSeg(t, 0.82, 0.94);
      hText(x, '✓ repaired', RX, 500, 28, HBLUE, { weight:600, alpha:rep });
      if (un > 0) { x.globalAlpha = un; hLock(x, RX + 30, 570, 50, 1 - hEase(un), HBLUE); x.globalAlpha = 1; hText(x, 'unlocked with the passphrase', RX + 80, 584, 26, HINK, { alpha:un }); }
      if (msg > 0) { x.globalAlpha = msg; hRound(x, RX, 630, 420, 90, 12); x.fillStyle = '#fff'; x.fill(); x.strokeStyle = HBLUE; x.lineWidth = 2.5; x.stroke(); x.globalAlpha = 1; hText(x, HMSG.slice(0, Math.ceil(msg * HMSG.length)), RX + 24, 690, 40, HINK, { mono:true, weight:600 }); }
      hWrap(x, 'Wrong passphrase or altered file → “No message found.”', RX, 762, 480, 22, 30, HGRAY, { alpha:hSeg(t, 0.92, 1) });
    }
  } else if (step === 3) {
    const tsH = 520, TY = 140;
    const ratio = img ? (img.naturalHeight / 8) / (img.naturalWidth / 10) : 1.74, TS = Math.round(tsH / ratio), TX = 90 + Math.round((400 - TS) / 2);
    if (img) { const sw = img.naturalWidth / 10, sh = img.naturalHeight / 8; x.drawImage(img, 4 * sw, 3 * sh, sw, sh, TX, TY, TS, tsH); }
    const nudge = hSeg(t, 0.15, 0.8);
    if (nudge > 0 && nudge < 1) { const rnd = (i: number) => ((Math.sin(i * 12.9898 + Math.floor(t * 40) * 78.233) * 43758.5453) % 1 + 1) % 1; for (let i = 0; i < 260; i++) { const px = TX + rnd(i) * TS, py = TY + rnd(i + 999) * tsH; x.fillStyle = rnd(i + 3) > 0.5 ? 'rgba(255,255,255,0.35)' : 'rgba(0,0,0,0.25)'; x.fillRect(px, py, 6, 6); } }
    x.strokeStyle = '#fff'; x.lineWidth = 4; x.strokeRect(TX, TY, TS, tsH);
    hText(x, 'one tile, zoomed', 90, TY - 24, 24, HGRAY, { mono:true });
    hText(x, 'pixels change by at most 2/255', 90, TY + tsH + 50, 26, HINK, { weight:600, alpha:hSeg(t, 0.1, 0.25) });
    const OX = 600, OY = 470, L2 = 230, base = 0.25;
    const target = 0.25 + 0.95, ang = base + (target - base) * hEase(nudge);
    hText(x, 'embedding of this tile', OX, 130, 24, HGRAY, { mono:true });
    x.strokeStyle = 'rgba(24,20,17,0.15)'; x.lineWidth = 2; x.beginPath(); x.moveTo(OX, OY); x.lineTo(OX + 420, OY); x.stroke();
    x.strokeStyle = '#a39b93'; x.lineWidth = 6; x.lineCap = 'round'; x.beginPath(); x.moveTo(OX, OY); x.lineTo(OX + L2 * Math.cos(base), OY - L2 * Math.sin(base)); x.stroke();
    x.strokeStyle = HBLUE; x.beginPath(); x.moveTo(OX, OY); x.lineTo(OX + L2 * Math.cos(ang), OY - L2 * Math.sin(ang)); x.stroke(); x.lineCap = 'butt';
    x.setLineDash([6, 6]); x.strokeStyle = HBLUE; x.lineWidth = 2; x.beginPath(); x.arc(OX, OY, 90, -ang, -base); x.stroke(); x.setLineDash([]);
    hText(x, 'before', OX + L2 * Math.cos(base) + 14, OY - L2 * Math.sin(base) + 8, 24, HGRAY, { mono:true });
    hText(x, 'after', OX + L2 * Math.cos(ang) + 14, Math.max(190, OY - L2 * Math.sin(ang)), 24, HBLUE, { mono:true, alpha:hSeg(t, 0.2, 0.3) });
    const flipped = Math.floor(nudge * 16);
    hText(x, 'bits it reads', OX, 540, 24, HGRAY, { mono:true });
    hBitRow(x, HSTART.map((b, i) => i < flipped ? HBITS[i] : b), OX, 560, 26, (i: number) => i < flipped ? { bg:'#eaf1f7', bd:HBLUE, fg:HBLUE } : null);
    hText(x, 'target', OX, 640, 24, HGRAY, { mono:true });
    hBitRow(x, HBITS, OX, 660, 26, () => ({ bg:'#fff', bd:'rgba(63,100,140,0.35)', fg:HGRAY }));
    hText(x, '✓ saved as PNG, reopened, read back', OX, 760, 26, HBLUE, { weight:600, alpha:hSeg(t, 0.85, 0.96) });
  }
}

export const HOW_NARROW_W = 560, HOW_NARROW_H = 700;

/** Phone composition of the same five steps: 560 × 700 logical units, text at least 18 units
 *  (11 CSS px at the smallest phone width). The caller scales the context to the canvas size. */
export function drawHowNarrow(x: Ctx, img: Img, step: number, t: number) {
  const W = HOW_NARROW_W, H = HOW_NARROW_H, TOP = 64, L = 28, R = W - 28, CW = R - L, MID = W / 2;
  x.clearRect(0, 0, W, H); x.fillStyle = HPAPER; x.fillRect(0, 0, W, H);
  // The Replay button sits over the top right corner, so the drawing starts below it.
  x.translate(0, TOP);
  if (step === 0) {
    const a = hSeg(t, 0.04, 0.3), n = Math.round(a * HMSG.length), enc = hSeg(t, 0.48, 0.78), nEnc = Math.floor(enc * HMSG.length);
    hText(x, 'message', L, 70, 20, HGRAY, { mono:true });
    if (enc > 0) hText(x, 'encrypted bytes', R - 48, 70, 20, HBLUE, { mono:true, align:'right', alpha:enc });
    const lk = hSeg(t, 0.8, 0.92);
    if (lk > 0) { x.globalAlpha = lk; hLock(x, R - 16, 58, 26, hEase(lk), HBLUE); x.globalAlpha = 1; }
    hRound(x, L, 86, CW, 84, 12); x.fillStyle = '#fff'; x.fill(); x.strokeStyle = 'rgba(24,20,17,0.15)'; x.lineWidth = 2; x.stroke();
    for (let i = 0; i < HMSG.length; i++) { const isHex = i < nEnc; const ch = isHex ? HHEX[i] : (i < n ? HMSG[i] : ''); hText(x, ch, L + 18 + i * 37, 140, isHex ? 22 : 32, isHex ? HBLUE : HINK, { mono:true, weight:isHex ? 500 : 600 }); }
    const p = hSeg(t, 0.25, 0.42);
    hText(x, 'passphrase', L, 262, 20, HGRAY, { mono:true, alpha:p });
    hRound(x, L, 276, 228, 66, 12); x.globalAlpha = p; x.fillStyle = '#fff'; x.fill(); x.strokeStyle = 'rgba(24,20,17,0.15)'; x.stroke(); x.globalAlpha = 1;
    for (let i = 0; i < Math.round(p * 9); i++) { x.beginPath(); x.arc(L + 26 + i * 22, 309, 7, 0, Math.PI * 2); x.fillStyle = HINK; x.fill(); }
    const k = hSeg(t, 0.38, 0.5);
    if (k > 0) { x.globalAlpha = k; x.strokeStyle = HGRAY; x.lineWidth = 3; x.setLineDash([6, 6]); x.beginPath(); x.moveTo(L + 236, 309); x.lineTo(L + 270, 309); x.stroke(); x.setLineDash([]);
      hRound(x, L + 278, 276, CW - 278, 66, 12); x.fillStyle = '#eaf1f7'; x.fill(); x.strokeStyle = HBLUE; x.lineWidth = 2; x.stroke();
      const kx = L + 278 + (CW - 278) / 2;
      hText(x, 'key (scrypt)', kx, 316, 20, HBLUE, { mono:true, align:'center' }); x.globalAlpha = 1;
      x.strokeStyle = HBLUE; x.lineWidth = 3; x.beginPath(); x.moveTo(kx, 276); x.lineTo(kx, 178); x.stroke(); x.beginPath(); x.moveTo(kx - 10, 190); x.lineTo(kx, 176); x.lineTo(kx + 10, 190); x.stroke(); }
    hWrap(x, 'Without the passphrase, the message can’t be read, as long as the passphrase is hard to guess.', MID, 430, CW, 28, 36, HINK, { align:'center', weight:600, alpha:hSeg(t, 0.85, 0.97) });
    hWrap(x, 'AES-256-GCM: tampering is detected, not just hidden.', MID, 566, CW, 21, 30, HGRAY, { align:'center', alpha:hSeg(t, 0.88, 1) });
  } else if (step === 1) {
    const n = 13, ecc = 6, cell = 34, gap = 4, X0 = MID - (n * (cell + gap) - gap) / 2, Y0 = 130, Y1 = 250;
    const a = hSeg(t, 0.02, 0.3);
    hText(x, 'encrypted message', X0, Y0 - 18, 20, HGRAY, { mono:true, alpha:a });
    for (let i = 0; i < n; i++) { const p = hSeg(a, i / n * 0.6, i / n * 0.6 + 0.4); x.globalAlpha = p; const bad = i === 5 && t > 0.62 && t < 0.86; hRound(x, X0 + i * (cell + gap), Y0 + (1 - p) * 24, cell, cell, 6); x.fillStyle = bad ? '#fbecec' : '#fff'; x.fill(); x.strokeStyle = bad ? HRED : 'rgba(24,20,17,0.2)'; x.lineWidth = 2; x.stroke(); hText(x, bad ? '??' : HHEX[i], X0 + i * (cell + gap) + cell / 2, Y0 + cell / 2 + 1 + (1 - p) * 24, 20, bad ? HRED : HINK, { mono:true, align:'center', base:'middle' }); x.globalAlpha = 1; }
    const b = hSeg(t, 0.32, 0.55);
    if (b > 0) hText(x, 'repair bytes', X0, Y1 - 18, 20, HBLUE, { mono:true, alpha:b });
    for (let i = 0; i < ecc; i++) { const p = hSeg(b, i / ecc * 0.6, i / ecc * 0.6 + 0.4); if (p <= 0) continue; x.globalAlpha = p; const X = X0 + i * (cell + gap); hRound(x, X, Y1 - (1 - p) * 30, cell, cell, 6); x.fillStyle = '#eaf1f7'; x.fill(); x.strokeStyle = HBLUE; x.lineWidth = 2; x.stroke(); hText(x, '+', X + cell / 2, Y1 + cell / 2 + 1 - (1 - p) * 30, 26, HBLUE, { mono:true, align:'center', base:'middle' }); x.globalAlpha = 1; }
    const dmg = hSeg(t, 0.6, 0.68), fix = hSeg(t, 0.82, 0.9);
    if (dmg > 0 && fix < 1) hWrap(x, 'a byte gets damaged on the way', MID, 384, CW, 26, 34, HRED, { align:'center', weight:600, alpha:dmg * (1 - fix) });
    if (fix > 0) { hWrap(x, 'the repair bytes fix it', MID, 384, CW, 26, 34, HBLUE, { align:'center', weight:600, alpha:fix }); const X = X0 + 5 * (cell + gap) + cell / 2; x.globalAlpha = fix; x.strokeStyle = HBLUE; x.lineWidth = 3.5; x.beginPath(); x.moveTo(X - 11, Y0 + cell + 22); x.lineTo(X - 3, Y0 + cell + 30); x.lineTo(X + 12, Y0 + cell + 12); x.stroke(); x.globalAlpha = 1; }
    hWrap(x, 'Only a few wrong bits can be repaired. Too many, and nothing is shown.', MID, 500, CW, 21, 30, HGRAY, { align:'center', alpha:hSeg(t, 0.9, 1) });
  } else if (step === 2) {
    const PH2 = 400, PW = Math.round(PH2 * 1280 / 1782), PX = MID - PW / 2, PY = 28, cols = 10, rows = 8, tw = PW / cols, th = PH2 / rows;
    hPhoto(x, img, PX, PY, PW, PH2);
    const gv = hEase(hSeg(t, 0.06, 0.4)), gh = hEase(hSeg(t, 0.3, 0.62));
    x.strokeStyle = 'rgba(255,255,255,0.85)'; x.lineWidth = 1.5;
    for (let c = 1; c < cols; c++) { x.beginPath(); x.moveTo(PX + c * tw, PY); x.lineTo(PX + c * tw, PY + PH2 * gv); x.stroke(); }
    for (let r = 1; r < rows; r++) { x.beginPath(); x.moveTo(PX, PY + r * th); x.lineTo(PX + PW * gh, PY + r * th); x.stroke(); }
    const wave = hSeg(t, 0.62, 0.82);
    if (wave > 0 && wave < 1) for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) { const d = (r + c) / (rows + cols - 2), al = Math.max(0, 1 - Math.abs(wave * 1.3 - d) * 6); if (al > 0) { x.fillStyle = 'rgba(63,100,140,' + (0.45 * al) + ')'; x.fillRect(PX + c * tw, PY + r * th, tw, th); } }
    const hl = hSeg(t, 0.82, 0.92);
    if (hl > 0) { x.globalAlpha = hl; x.strokeStyle = '#fff'; x.lineWidth = 3; x.strokeRect(PX + 4 * tw, PY + 3 * th, tw, th); x.strokeStyle = HBLUE; x.lineWidth = 2.5; x.strokeRect(PX + 4 * tw - 3, PY + 3 * th - 3, tw + 6, th + 6); x.globalAlpha = 1; }
    hText(x, '10 × 8 = 80 tiles', L, 488, 25, HINK, { weight:600, alpha:hSeg(t, 0.62, 0.74) });
    hText(x, 'for Subtle and Long', L, 518, 20, HGRAY, { alpha:hSeg(t, 0.64, 0.76) });
    hText(x, '6 × 5 = 30 tiles', MID + 20, 488, 25, HINK, { weight:600, alpha:hSeg(t, 0.72, 0.84) });
    hText(x, 'for Short', MID + 20, 518, 20, HGRAY, { alpha:hSeg(t, 0.74, 0.86) });
    hText(x, 'Each tile is read on its own.', MID, 600, 24, HBLUE, { weight:600, align:'center', alpha:hSeg(t, 0.86, 0.96) });
  } else if (step === 3) {
    const TS = 130, tsH = Math.round(TS * (img ? (img.naturalHeight / 8) / (img.naturalWidth / 10) : 1.74)), TX = L, TY = 56;
    if (img) { const sw = img.naturalWidth / 10, sh = img.naturalHeight / 8; x.drawImage(img, 4 * sw, 3 * sh, sw, sh, TX, TY, TS, tsH); }
    const nudge = hSeg(t, 0.15, 0.8);
    if (nudge > 0 && nudge < 1) { const rnd = (i: number) => ((Math.sin(i * 12.9898 + Math.floor(t * 40) * 78.233) * 43758.5453) % 1 + 1) % 1; for (let i = 0; i < 120; i++) { const px = TX + rnd(i) * TS, py = TY + rnd(i + 999) * tsH; x.fillStyle = rnd(i + 3) > 0.5 ? 'rgba(255,255,255,0.35)' : 'rgba(0,0,0,0.25)'; x.fillRect(px, py, 4, 4); } }
    x.strokeStyle = '#fff'; x.lineWidth = 3; x.strokeRect(TX, TY, TS, tsH);
    hText(x, 'one tile, zoomed', L, TY - 16, 20, HGRAY, { mono:true });
    const OX = L + TS + 40, OY = TY + tsH - 20, L2 = Math.min(R - OX - 50, OY - TY - 12), base = 0.25, ang = base + 0.95 * hEase(nudge);
    hText(x, 'embedding of this tile', R, TY - 16, 20, HGRAY, { mono:true, align:'right' });
    x.strokeStyle = 'rgba(24,20,17,0.15)'; x.lineWidth = 2; x.beginPath(); x.moveTo(OX, OY); x.lineTo(R, OY); x.stroke();
    x.strokeStyle = '#a39b93'; x.lineWidth = 5; x.lineCap = 'round'; x.beginPath(); x.moveTo(OX, OY); x.lineTo(OX + L2 * Math.cos(base), OY - L2 * Math.sin(base)); x.stroke();
    x.strokeStyle = HBLUE; x.beginPath(); x.moveTo(OX, OY); x.lineTo(OX + L2 * Math.cos(ang), OY - L2 * Math.sin(ang)); x.stroke(); x.lineCap = 'butt';
    x.setLineDash([5, 5]); x.strokeStyle = HBLUE; x.lineWidth = 2; x.beginPath(); x.arc(OX, OY, 60, -ang, -base); x.stroke(); x.setLineDash([]);
    hText(x, 'before', Math.min(R - 60, OX + L2 * Math.cos(base) - 40), OY - L2 * Math.sin(base) - 14, 20, HGRAY, { mono:true });
    hText(x, 'after', OX + L2 * Math.cos(ang) + 12, Math.max(TY + 16, OY - L2 * Math.sin(ang)), 20, HBLUE, { mono:true, alpha:hSeg(t, 0.2, 0.3) });
    hText(x, 'pixels change by at most 2/255', L, TY + tsH + 44, 22, HINK, { weight:600, alpha:hSeg(t, 0.1, 0.25) });
    const flipped = Math.floor(nudge * 16), BY = TY + tsH + 96;
    hText(x, 'bits it reads', L, BY, 20, HGRAY, { mono:true });
    hBitRow(x, HSTART.map((b, i) => i < flipped ? HBITS[i] : b), L, BY + 12, 25, (i: number) => i < flipped ? { bg:'#eaf1f7', bd:HBLUE, fg:HBLUE } : null, 20);
    hText(x, 'target', L, BY + 74, 20, HGRAY, { mono:true });
    hBitRow(x, HBITS, L, BY + 86, 25, () => ({ bg:'#fff', bd:'rgba(63,100,140,0.35)', fg:HGRAY }), 20);
    hWrap(x, '✓ saved as PNG, reopened, read back', L, BY + 160, CW, 22, 30, HBLUE, { weight:600, alpha:hSeg(t, 0.85, 0.96) });
  } else if (step === 4) {
    const PW = 190, PH2 = Math.round(PW * 1782 / 1280), PX = L, PY = 28, cols = 10, rows = 8, tw = PW / cols, th = PH2 / rows;
    hPhoto(x, img, PX, PY, PW, PH2);
    x.strokeStyle = 'rgba(255,255,255,0.6)'; x.lineWidth = 1;
    for (let c = 1; c < cols; c++) { x.beginPath(); x.moveTo(PX + c * tw, PY); x.lineTo(PX + c * tw, PY + PH2); x.stroke(); }
    for (let r = 1; r < rows; r++) { x.beginPath(); x.moveTo(PX, PY + r * th); x.lineTo(PX + PW, PY + r * th); x.stroke(); }
    const scan = hSeg(t, 0.04, 0.56), total = cols * rows, k = Math.floor(scan * total);
    for (let i = 0; i < Math.min(k, total); i++) { const r = Math.floor(i / cols), c = i % cols; x.fillStyle = 'rgba(63,100,140,0.22)'; x.fillRect(PX + c * tw, PY + r * th, tw, th); }
    if (k < total && scan > 0) { const r = Math.floor(k / cols), c = k % cols; x.strokeStyle = '#fff'; x.lineWidth = 2.5; x.strokeRect(PX + c * tw, PY + r * th, tw, th); }
    const RX = PX + PW + 26, cell = 30, cg = 4;
    hText(x, 'same frozen model', RX, 52, 20, HGRAY, { mono:true });
    hText(x, 'reads each tile', RX, 84, 25, HINK, { weight:600 });
    const nb = Math.floor(scan * 32);
    for (let i = 0; i < 32; i++) { const r = Math.floor(i / 8), c = i % 8, X = RX + c * (cell + cg), Y = 104 + r * (cell + cg); hRound(x, X, Y, cell, cell, 5); x.fillStyle = i < nb ? '#eaf1f7' : '#fff'; x.fill(); x.strokeStyle = i < nb ? HBLUE : 'rgba(24,20,17,0.15)'; x.lineWidth = 2; x.stroke(); if (i < nb) hText(x, String((HBITS[i % 16] + (i >> 4)) % 2), X + cell / 2, Y + cell / 2 + 1, 20, HBLUE, { mono:true, align:'center', base:'middle' }); }
    const rep = hSeg(t, 0.58, 0.68), un = hSeg(t, 0.7, 0.82), msg = hSeg(t, 0.82, 0.94), Y2 = PY + PH2 + 44;
    hText(x, '✓ repaired', RX, 274, 22, HBLUE, { weight:600, alpha:rep });
    if (un > 0) { x.globalAlpha = un; hLock(x, L + 16, Y2 - 6, 28, 1 - hEase(un), HBLUE); x.globalAlpha = 1; hText(x, 'unlocked with the passphrase', L + 48, Y2 + 2, 21, HINK, { alpha:un }); }
    if (msg > 0) { x.globalAlpha = msg; hRound(x, L, Y2 + 24, CW, 74, 12); x.fillStyle = '#fff'; x.fill(); x.strokeStyle = HBLUE; x.lineWidth = 2.5; x.stroke(); x.globalAlpha = 1; hText(x, HMSG.slice(0, Math.ceil(msg * HMSG.length)), L + 20, Y2 + 72, 32, HINK, { mono:true, weight:600 }); }
    hWrap(x, 'Wrong passphrase or altered file → “No message found.”', L, Y2 + 140, CW, 20, 28, HGRAY, { alpha:hSeg(t, 0.92, 1) });
  }
}
