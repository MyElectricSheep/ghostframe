// Build-time data and assets for the site. Nothing here is typed in by hand:
//   - every number comes from design-handoff/ghostframe-site/data/design-data.json;
//   - every example message, byte count and hash from demo-photos/fixtures/*/fixtures.json;
//   - the fixture PNGs are copied byte for byte and checked against those hashes.
// Writes site/public/demo-photos/ (copies) and site/src/generated/site-data.json.
import { createHash } from 'node:crypto';
import { copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const SITE = join(dirname(fileURLToPath(import.meta.url)), '..');
const ROOT = join(SITE, '..');
const DATA = join(ROOT, 'design-handoff', 'ghostframe-site', 'data', 'design-data.json');
const PHOTOS = join(ROOT, 'demo-photos');
const OUT_PHOTOS = join(SITE, 'public', 'demo-photos');
const OUT_DATA = join(SITE, 'src', 'generated', 'site-data.json');

const COVERS = { antonello: 'antonello-portrait-of-a-man', coffee: 'coffee-beans', milky: 'milky-way' };
const STEMS = { classic: 'classic', subtle: 'subtle', long: 'long' };

const sha256 = (path) => createHash('sha256').update(readFileSync(path)).digest('hex');

function pngSize(path) {
  const b = readFileSync(path);
  if (b.toString('latin1', 1, 4) !== 'PNG') throw new Error(`${path} is not a PNG`);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
}

const design = JSON.parse(readFileSync(DATA, 'utf8'));
const fixtures = {};

for (const [key, dir] of Object.entries(COVERS)) {
  const src = join(PHOTOS, 'fixtures', dir);
  const dst = join(OUT_PHOTOS, 'fixtures', dir);
  mkdirSync(dst, { recursive: true });
  const entries = JSON.parse(readFileSync(join(src, 'fixtures.json'), 'utf8'));
  const modes = {};
  for (const entry of entries) {
    const mode = entry.encoded.replace(/\.png$/, '');
    if (!(mode in STEMS)) throw new Error(`Unexpected fixture ${entry.encoded}`);
    for (const [file, hash] of Object.entries(entry.sha256)) {
      if (sha256(join(src, file)) !== hash) throw new Error(`Hash mismatch: ${dir}/${file}`);
      // Copy only when missing or different, so a running dev server keeps serving the files.
      if (!existsSync(join(dst, file)) || sha256(join(dst, file)) !== hash) copyFileSync(join(src, file), join(dst, file));
      if (sha256(join(dst, file)) !== hash) throw new Error(`Copy changed bytes: ${dir}/${file}`);
    }
    modes[mode] = {
      profile: entry.profile,
      message: entry.recovered_message,
      bytes: entry.payload_bytes,
      changed: entry.changed_channel_fraction,
      maxDelta: entry.max_rgb_delta,
      amp: entry.amplification,
      checks: entry.checks,
      sha256: entry.sha256,
    };
  }
  for (const jpg of [`${dir}.jpg`]) copyFileSync(join(PHOTOS, jpg), join(OUT_PHOTOS, jpg));
  fixtures[key] = { dir, size: pngSize(join(src, 'original.png')), modes };
}

const out = {
  source: 'design-handoff/ghostframe-site/data/design-data.json + demo-photos/fixtures/*/fixtures.json',
  modes: design.modes,
  heat: design.heat,
  raw: design.raw,
  res: design.res,
  stress: design.stress,
  small640: design.small640,
  detect: design.detect,
  fixtures,
};
mkdirSync(dirname(OUT_DATA), { recursive: true });
writeFileSync(OUT_DATA, JSON.stringify(out, null, 1) + '\n');
console.log(`prepared ${Object.keys(fixtures).length} covers, data -> ${OUT_DATA}`);
