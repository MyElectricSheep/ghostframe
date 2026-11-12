import { BLUE, GRAY, INK, RED } from '../../data';
import type { FileInfo, IssueKey } from '../../lib/image';
import { prefersReducedMotion } from '../../lib/style';

// Input-rule messages, word for word from the design (ISSUE).
export const ISSUE: Record<IssueKey, (f: FileInfo, modeLabel?: string) => string> = {
  type: () => 'This file isn’t a PNG or JPEG. Ghostframe accepts PNG or JPEG photos.',
  big: (f) => 'This photo is ' + f.mp + ' megapixels. The limit is 4 MP, for example 2448 × 1632. Scale it down and try again.',
  small: (f, m) => 'This photo is ' + f.dims + '. ' + m + ' needs at least 160 × 128.',
  alpha: () => 'This image has transparent pixels. Place it on a solid background, save it again and retry.',
  deep: () => '16-bit and HDR images aren’t supported. Export an 8-bit PNG or JPEG and try again.',
  cmyk: () => 'CMYK and Lab images aren’t supported. Convert the photo to RGB and try again.',
  jpegRead: () => 'This is a JPEG, and a JPEG can never contain a readable Ghostframe message. Ghostframe only writes PNG files, and saving one as JPEG destroys the message. Use the exact PNG you were sent.',
};

export function check(issue: IssueKey | null, f: FileInfo | null) {
  if (!f) return { fg: '', glyph: '', radius: '', text: '' };
  if (issue) return { fg: RED, glyph: '!', radius: '2px', text: issue === 'jpegRead' ? 'Can’t be read' : 'Can’t be used' };
  return { fg: BLUE, glyph: '✓', radius: '50%', text: 'Meets the input rules' };
}

export function dropZone(drag: boolean, issue: IssueKey | null, has: boolean) {
  if (drag) return { bs: 'dashed', bd: BLUE, bg: '#eaf1f7' };
  if (issue) return { bs: 'solid', bd: RED, bg: '#fff8f8' };
  if (has) return { bs: 'solid', bd: 'rgba(24,20,17,0.18)', bg: '#f6f4f1' };
  return { bs: 'dashed', bd: 'rgba(24,20,17,0.25)', bg: '#f6f4f1' };
}

export function segments(opts: [string, string][], cur: string, set: (k: string) => void) {
  return opts.map(([k, label]) => { const on = k === cur; return { label, pressed: on, bg: on ? '#fff' : 'transparent', fg: on ? INK : GRAY, sh: on ? '0 1px 2px rgba(0,0,0,0.08), 0 0 0 1px rgba(24,20,17,0.08)' : 'none', onClick: () => set(k) }; });
}

export function scrollToId(id: string) {
  setTimeout(() => {
    const el = document.getElementById(id);
    if (!el) return;
    const r = el.getBoundingClientRect();
    if (r.top > window.innerHeight - 120 || r.top < 60) window.scrollTo({ top: r.top + window.scrollY - 80, behavior: prefersReducedMotion() ? 'auto' : 'smooth' });
  }, 60);
}
