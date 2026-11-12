// Client-side look at an upload, for immediate feedback. The server re-checks everything.
export interface FileInfo {
  name: string; type: string; w: number; h: number; url: string; blob: Blob | null;
  alpha: boolean; p3: boolean; err: 'type' | 'deep' | 'cmyk' | null; sample: boolean;
  dims?: string; mp?: string;
}

const ascii = (b: Uint8Array, s: string) => [...s].every((ch, i) => b[i] === ch.charCodeAt(0));

function find(bytes: Uint8Array, needle: string, utf16 = false) {
  const n = utf16 ? [...needle].flatMap((c) => [0, c.charCodeAt(0)]) : [...needle].map((c) => c.charCodeAt(0));
  outer: for (let i = 0; i <= bytes.length - n.length; i++) {
    for (let j = 0; j < n.length; j++) if (bytes[i + j] !== n[j]) continue outer;
    return true;
  }
  return false;
}

/** 16-bit PNGs, CMYK JPEGs and a Display P3 colour profile, from the file header. */
function header(bytes: Uint8Array, isPng: boolean): { deep: boolean; cmyk: boolean; p3: boolean } {
  let deep = false, cmyk = false;
  if (isPng && ascii(bytes.subarray(12, 16), 'IHDR')) deep = bytes[24] === 16;
  if (!isPng) {
    for (let i = 2; i + 9 < bytes.length;) {
      if (bytes[i] !== 0xff) break;
      const marker = bytes[i + 1], len = (bytes[i + 2] << 8) | bytes[i + 3];
      if (marker >= 0xc0 && marker <= 0xcf && marker !== 0xc4 && marker !== 0xc8 && marker !== 0xcc) { cmyk = bytes[i + 9] === 4; break; }
      i += 2 + len;
    }
  }
  const p3 = find(bytes, 'Display P3') || find(bytes, 'Display P3', true);
  return { deep, cmyk, p3 };
}

function pixels(img: HTMLImageElement, maxSide: number) {
  const s = Math.min(1, maxSide / Math.max(img.naturalWidth, img.naturalHeight));
  const w = Math.max(1, Math.round(img.naturalWidth * s)), h = Math.max(1, Math.round(img.naturalHeight * s));
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  const x = c.getContext('2d', { willReadFrequently: true })!; x.drawImage(img, 0, 0, w, h);
  return x.getImageData(0, 0, w, h);
}

export async function inspect(file: Blob, name: string, sample = false): Promise<FileInfo> {
  const isPng = file.type === 'image/png', isJpg = file.type === 'image/jpeg';
  const base = { name, w: 0, h: 0, url: '', blob: file, alpha: false, p3: false, sample };
  if (!isPng && !isJpg) return { ...base, type: (name.split('.').pop() || 'file').toUpperCase(), err: 'type' };
  const head = header(new Uint8Array(await file.slice(0, 512 * 1024).arrayBuffer()), isPng);
  const url = URL.createObjectURL(file);
  const img = await new Promise<HTMLImageElement | null>((res) => { const im = new Image(); im.onload = () => res(im); im.onerror = () => res(null); im.src = url; });
  if (!img) return { ...base, type: '?', err: 'type' };
  let alpha = false;
  if (isPng) { const d = pixels(img, 800).data; for (let i = 3; i < d.length; i += 4) if (d[i] < 255) { alpha = true; break; } }
  const err = head.deep ? 'deep' : head.cmyk ? 'cmyk' : null;
  return { ...base, type: isPng ? 'PNG' : 'JPEG', w: img.naturalWidth, h: img.naturalHeight, url, alpha, p3: head.p3, err };
}

export function withDims(f: FileInfo | null): FileInfo | null {
  if (!f) return f;
  return { ...f, dims: f.w + ' × ' + f.h, mp: (f.w * f.h / 1e6).toFixed(1) };
}

export type IssueKey = 'type' | 'big' | 'small' | 'alpha' | 'deep' | 'cmyk' | 'jpegRead';

export function issueOf(f: FileInfo | null, forRead: boolean): IssueKey | null {
  if (!f) return null;
  if (f.err) return f.err;
  if (forRead && f.type !== 'PNG') return 'jpegRead';
  if (f.w * f.h > 4e6) return 'big';
  if (!forRead && (f.w < 160 || f.h < 128)) return 'small';
  if (f.alpha) return 'alpha';
  return null;
}
