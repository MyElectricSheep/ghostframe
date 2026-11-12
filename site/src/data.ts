// All numbers come from the generated site-data.json (design-data.json + fixtures.json, see
// scripts/prepare-assets.mjs). Strings here are the page copy.
import raw from './generated/site-data.json';

export type ModeKey = 'classic' | 'subtle' | 'long';
export type PhotoKey = 'antonello' | 'coffee' | 'milky';

export const ORDER: ModeKey[] = ['classic', 'subtle', 'long'];
export const PORDER: PhotoKey[] = ['antonello', 'coffee', 'milky'];
export const PASS_FIXTURE = 'ghostframe public benchmark fixture';

export const BLUE = '#3f648c', INK = 'rgba(18,16,14,0.96)', GRAY = '#625c57', RED = '#9f3b3b';

interface DataMode {
  profile: string; backbone: string; dim: number; cap: number; amp: number; grid: [number, number];
  bytes: number; ev: string; evUnit: string; psnr: string; ssim: string;
}
interface FixtureMode { profile: string; message: string; bytes: number; changed: number; checks: Record<string, string> }
interface Res { read_back: number; frames: number; max_wrong_bytes: number; min_ssim: number; max_encode_s: number }
interface SiteData {
  modes: Record<ModeKey, DataMode>;
  heat: Record<PhotoKey, Record<ModeKey, number[][]>>;
  raw: Record<PhotoKey, Record<'u10' | 'u6' | ModeKey, number[]>>;
  res: Record<PhotoKey, Record<'subtle' | 'long', Res>>;
  stress: Record<'subtle' | 'long', { encoded: number; of: number }>;
  small640: Partial<Record<'subtle' | 'long', { read_back: number; of: number }>>;
  detect: Partial<Record<'subtle' | 'long', { auc: number; pairs: number }>>;
  fixtures: Record<PhotoKey, { dir: string; size: { w: number; h: number }; modes: Record<ModeKey, FixtureMode>; served: Record<string, string> }>;
}
const D = raw as unknown as SiteData;

const UI: Record<ModeKey, { label: string; blurb: string; tip: string }> = {
  classic: { label: 'Short', blurb: 'A short phrase. Larger tiles.', tip: 'Holds a short phrase. Pixels change by up to 8 levels out of 255, and the model reads a coarser grid of larger tiles.' },
  subtle: { label: 'Subtle', blurb: 'Smallest changes, a sentence or two.', tip: 'The gentlest change to the picture: at most 2 levels out of 255. Holds a sentence or two.' },
  long: { label: 'Long', blurb: 'A long paragraph. More visible change.', tip: 'Holds a long paragraph, about 80 words. Pixels change by up to 8 levels out of 255, so the picture changes more than with Subtle.' },
};

export interface Mode extends DataMode { key: ModeKey; label: string; blurb: string; tip: string; cols: number; rows: number }
export const MODES = Object.fromEntries(ORDER.map((k) => {
  const m = D.modes[k];
  return [k, { ...m, key: k, ...UI[k], cols: m.grid[0], rows: m.grid[1] }];
})) as Record<ModeKey, Mode>;

const PHOTO_UI: Record<PhotoKey, { label: string; pos: string }> = {
  antonello: { label: 'Portrait', pos: '50% 25%' },
  coffee: { label: 'Coffee beans', pos: '50% 50%' },
  milky: { label: 'Milky Way', pos: '50% 50%' },
};
export interface Photo { key: PhotoKey; label: string; pos: string; dir: string; w: number; h: number; jpg: string; thumb: string; aspect: string }
export const PHOTOS = Object.fromEntries(PORDER.map((k) => {
  const f = D.fixtures[k];
  return [k, { key: k, ...PHOTO_UI[k], dir: f.dir, w: f.size.w, h: f.size.h, jpg: `/demo-photos/${f.dir}.jpg`, thumb: `/thumbs/${k}.jpg`, aspect: `${f.size.w} / ${f.size.h}` }];
})) as Record<PhotoKey, Photo>;

/** URL of a fixture under its visitor-facing name (e.g. classic.png → portrait-short.png), a byte-identical copy. */
export const servedName = (p: PhotoKey, file: string) => D.fixtures[p].served[file] ?? file;
export const fixturePath = (p: PhotoKey, file: string) => `/demo-photos/fixtures/${PHOTOS[p].dir}/${servedName(p, file)}`;
export const fixture = (p: PhotoKey, m: ModeKey) => D.fixtures[p].modes[m];
export const heat = (p: PhotoKey, m: ModeKey) => D.heat[p][m];
export const rawNumbers = (p: PhotoKey) => D.raw[p];

/** "Recorded result" line for a cover and mode, in the design's format. */
export function resultLine(p: PhotoKey, m: ModeKey): string {
  if (m === 'classic') {
    const ok = Object.entries(fixture(p, m).checks).filter(([k]) => k.startsWith('decode_')).every(([, v]) => v.startsWith('exit 0'));
    return ok ? '1 / 1 read back' : '0 / 1 read back';
  }
  const r = D.res[p][m];
  return `${r.read_back} / ${r.frames} read back · ${r.max_wrong_bytes} wrong bytes · SSIM ≥ ${r.min_ssim.toFixed(3)} · encode ≤ ${r.max_encode_s} s`;
}

export const STRESS = D.stress;
export const SMALL640 = D.small640;
export const DETECT = D.detect;

export const ABBR: Record<'PSNR' | 'SSIM' | 'AES' | 'scrypt', [string, string]> = {
  PSNR: ['PSNR · peak signal-to-noise ratio', 'How close the marked photo is to the original, measured in decibels. Higher means closer; at around 40 dB and above, differences are usually very hard to see.'],
  SSIM: ['SSIM · structural similarity', 'Compares local patterns of brightness, contrast and texture between two images. 1 means identical.'],
  AES: ['AES-256-GCM', 'A widely used encryption standard. It keeps the message secret, and any change to the hidden data is detected instead of producing a wrong message.'],
  scrypt: ['scrypt', 'A deliberately slow way of turning a passphrase into an encryption key, so trying many passphrases takes a very long time.'],
};
export type AbbrKey = keyof typeof ABBR;

export const bytesOf = (s: string) => new TextEncoder().encode(s || '').length;
