// Hero animation, carried over unchanged from the design reference (drawHero).
const HG_MAP = ['..XXX..', '.XXXXX.', 'XXXXXXX', 'XX.X*XX', 'XXXXXXX', 'XXXXXXX', 'XXXXXXX', 'X.X.X.X'];
const HG_PIX: { r: number; c: number; eye: boolean; tile: number; delay: number }[] = []; HG_MAP.forEach((row, r) => [...row].forEach((ch, c) => { if (ch !== '.') HG_PIX.push({ r, c, eye:ch === '*', tile:0, delay:0 }); }));
(function () { let seed = 7; const rnd = () => { seed = (seed * 9301 + 49297) % 233280; return seed / 233280; }; const used = new Set<number>(); HG_PIX.forEach(p => { let k; do { k = Math.floor(rnd() * 80); } while (used.has(k)); used.add(k); p.tile = k; p.delay = rnd(); }); })();
export function drawHero(x: CanvasRenderingContext2D, img: HTMLImageElement | null, t: number) {
  const W = 1080, H = 760; x.fillStyle = '#312e2b'; x.fillRect(0, 0, W, H);
  const PX = 380, PY = 150, PW = 640, PH = 480, cols = 10, rows = 8, tw = PW / cols, th = PH / rows;
  x.fillStyle = '#f6f4f1'; x.fillRect(PX - 8, PY - 8, PW + 16, PH + 16);
  if (img) { const r = Math.max(PW / img.naturalWidth, PH / img.naturalHeight), dw = img.naturalWidth * r, dh = img.naturalHeight * r; x.save(); x.beginPath(); x.rect(PX, PY, PW, PH); x.clip(); x.drawImage(img, PX + (PW - dw) / 2, PY + (PH - dh) / 2, dw, dh); x.restore(); } else { x.fillStyle = '#6b625a'; x.fillRect(PX, PY, PW, PH); }
  const ease = (v: number) => v < 0.5 ? 4 * v * v * v : 1 - Math.pow(-2 * v + 2, 3) / 2, cl = (v: number) => Math.max(0, Math.min(1, v)), seg = (a: number, b: number) => cl((t - a) / (b - a));
  const bob = Math.sin(t * Math.PI * 6) * 6, S = 26, GX = 70, GY = 220 + bob;
  const hide = seg(0.12, 0.44), read = seg(0.6, 0.86);
  const scanX = PX + PW * seg(0.58, 0.84);
  const gridA = Math.max(seg(0.1, 0.16) * (1 - seg(0.44, 0.52)), seg(0.56, 0.6) * (1 - seg(0.86, 0.94)));
  if (gridA > 0) { x.strokeStyle = 'rgba(255,255,255,' + (0.5 * gridA) + ')'; x.lineWidth = 1.5; for (let c = 1; c < cols; c++) { x.beginPath(); x.moveTo(PX + c * tw, PY); x.lineTo(PX + c * tw, PY + PH); x.stroke(); } for (let r = 1; r < rows; r++) { x.beginPath(); x.moveTo(PX, PY + r * th); x.lineTo(PX + PW, PY + r * th); x.stroke(); } }
  if (t > 0.58 && t < 0.86) { x.fillStyle = 'rgba(143,179,217,0.18)'; x.fillRect(PX, PY, scanX - PX, PH); x.fillStyle = '#8fb3d9'; x.fillRect(scanX - 2, PY - 10, 4, PH + 20); }
  HG_PIX.forEach(p => {
    const gx = GX + p.c * S, gy = GY + p.r * S, tc = p.tile % cols, tr = Math.floor(p.tile / cols), tx = PX + tc * tw + tw / 2 - S / 2, ty = PY + tr * th + th / 2 - S / 2;
    const ph = cl((hide - p.delay * 0.55) / 0.45), tileRead = (PX + tc * tw + tw / 2) < scanX, pr = t < 0.6 ? 0 : tileRead ? cl((read - (tc / cols) * 0.75) / 0.3) : 0;
    let px, py, a = 1, col = p.eye ? '#8fb3d9' : '#f6f4f1', sz = S - 2;
    if (t < 0.6) { const e = ease(ph); px = gx + (tx - gx) * e; py = gy + (ty - gy) * e - Math.sin(e * Math.PI) * 80; if (ph >= 1) { a = 1 - cl((t - 0.44) / 0.06 + (1 - p.delay) * 0.2); sz = S - 2; } }
    else { const e = ease(pr); px = tx + (gx - tx) * e; py = ty + (gy - ty) * e - Math.sin(e * Math.PI) * 80; a = pr > 0 ? 1 : 0; }
    if (t >= 0.86) { px = gx; py = gy; a = 1; }
    if (a <= 0) return;
    x.globalAlpha = a; x.fillStyle = col; x.fillRect(px + 1, py + 1, sz, sz); x.globalAlpha = 1;
  });
  if (t < 0.14 || t >= 0.86) { HG_MAP.forEach((row, r) => [...row].forEach((ch, c) => { if (ch === '.' && r === 3) { x.fillStyle = '#312e2b'; x.fillRect(GX + c * S + 1, GY + r * S + 1, S - 2, S - 2); } })); }
  const label = (s: string, X: number, on: boolean) => { x.font = '500 22px "IBM Plex Mono", ui-monospace, monospace'; x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillStyle = on ? '#f6f4f1' : 'rgba(246,244,241,0.38)'; x.fillText(s, X, 700); x.textBaseline = 'alphabetic'; };
  const phase = t < 0.12 ? 0 : t < 0.52 ? 1 : t < 0.58 ? 2 : t < 0.88 ? 3 : 4;
  const LX = [135, 405, 675, 945];
  label('message', LX[0], phase === 0 || phase === 4); label('hidden in the tiles', LX[1], phase === 1); label('looks the same', LX[2], phase === 2); label('read back', LX[3], phase === 3);
  x.font = '500 22px "IBM Plex Mono", ui-monospace, monospace';
  const LW = ['message', 'hidden in the tiles', 'looks the same', 'read back'].map(s => x.measureText(s).width);
  for (let i = 0; i < 3; i++) { const end = LX[i] + LW[i] / 2, start = LX[i + 1] - LW[i + 1] / 2; label('→', (end + start) / 2, false); }
  x.font = '500 20px "IBM Plex Mono", ui-monospace, monospace'; x.fillStyle = 'rgba(246,244,241,0.55)'; x.textAlign = 'left'; x.fillText('marked photo · ≤ 2/255 per pixel', PX, PY - 26);
}
