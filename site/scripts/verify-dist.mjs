// After `vite build`: every fixture PNG in dist/ must be byte-identical to its fixtures.json hash.
import { createHash } from 'node:crypto';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const SITE = join(dirname(fileURLToPath(import.meta.url)), '..');
const data = JSON.parse(readFileSync(join(SITE, 'src', 'generated', 'site-data.json'), 'utf8'));
let checked = 0;
for (const { dir, modes, served } of Object.values(data.fixtures)) {
  for (const { sha256 } of Object.values(modes)) {
    for (const [file, hash] of Object.entries(sha256)) for (const name of [file, served[file]]) {
      const path = join(SITE, 'dist', 'demo-photos', 'fixtures', dir, name);
      if (!existsSync(path)) throw new Error(`Missing from dist: ${dir}/${name}`);
      if (createHash('sha256').update(readFileSync(path)).digest('hex') !== hash) {
        throw new Error(`dist changed bytes: ${dir}/${name}`);
      }
      checked++;
    }
  }
}
console.log(`dist: ${checked} fixture files (originals and visitor-named copies) byte-identical to fixtures.json`);
