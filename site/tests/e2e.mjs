// End-to-end against the real engine: Hide -> download the exact PNG -> Read it back.
//   node tests/e2e.mjs [siteUrl] [mode] [message]    (site and API must be running; see site/README.md)
// Against the live site the Turnstile check must pass in the headless browser.
import { chromium } from 'playwright';
import { createHash } from 'node:crypto';
import { mkdtempSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const SITE = process.argv[2] || 'http://127.0.0.1:5178/';
const MODE = process.argv[3] || 'Subtle';
const MESSAGE = process.argv[4] || 'Meet at dawn. The north gate stays open until six.';
const PASS = 'harbour lantern orbit';
const out = mkdtempSync(join(tmpdir(), 'gf-e2e-'));
const ok = (cond, what) => { if (!cond) throw new Error('FAILED: ' + what); console.log('ok  ' + what); };

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 900 }, acceptDownloads: true });
await page.goto(SITE, { waitUntil: 'networkidle' });
const tool = page.locator('#tool');

// ---- Hide
await tool.getByRole('button', { name: 'Use a sample photo' }).click();
await tool.getByText('Meets the input rules').first().waitFor();
await tool.getByRole('button', { name: new RegExp('^' + MODE) }).click();
await tool.locator('#gf-hmsg').fill(MESSAGE);
await tool.locator('#gf-hp1').fill(PASS);
await tool.locator('#gf-hp2').fill(PASS);
const t0 = Date.now();
await tool.getByRole('button', { name: /Encode/ }).click();
await tool.getByText(/Encoding your photo|ahead of you|next in line|Starting the engine/).first().waitFor({ timeout: 20000 });
await page.locator('#gf-hresult').screenshot({ path: join(out, 'hide-running.png') });
await tool.getByText('Done. Your message is hidden.').waitFor({ timeout: 330000 });
console.log(`    encode took ${((Date.now() - t0) / 1000).toFixed(1)} s`);
await page.locator('#gf-hresult').screenshot({ path: join(out, 'hide-done.png') });
const [download] = await Promise.all([page.waitForEvent('download'), tool.getByRole('link', { name: 'Download PNG' }).click()]);
const saved = join(out, 'marked.png');
await download.saveAs(saved);
const bytes = readFileSync(saved);
ok(bytes.subarray(1, 4).toString() === 'PNG', 'download is a PNG');
console.log('    sha256 ' + createHash('sha256').update(bytes).digest('hex'));

// ---- Read it back (try all modes)
await tool.getByRole('tab', { name: 'Read a message' }).click();
await tool.locator('input[aria-label="Choose a PNG"]').setInputFiles(saved);
await tool.locator('#gf-rpass').fill(PASS);
await tool.getByRole('button', { name: 'Read the message' }).click();
await tool.getByText('Message found and unlocked').waitFor({ timeout: 60000 });
ok((await tool.locator('#gf-rresult p').first().innerText()) === MESSAGE, 'downloaded PNG reads back the exact message');
await page.locator('#gf-rresult').screenshot({ path: join(out, 'read-found.png') });

// ---- Wrong passphrase gives the neutral "No message found."
await tool.locator('#gf-rpass').fill('wrong passphrase');
await tool.getByRole('button', { name: 'Read the message' }).click();
await tool.getByText('No message found.').waitFor({ timeout: 60000 });
ok(true, 'wrong passphrase shows "No message found."');

// ---- Portrait sample with the public passphrase (Short)
await tool.getByRole('button', { name: 'Remove' }).last().click();
await tool.getByRole('button', { name: 'Use the portrait sample' }).click();
await tool.getByRole('button', { name: 'Fill it in' }).click();
await tool.getByRole('button', { name: 'Read the message' }).click();
await tool.getByText('Message found and unlocked').waitFor({ timeout: 60000 });
ok((await tool.locator('#gf-rresult p').first().innerText()) === 'Trust no one.', 'portrait sample reads "Trust no one."');

// ---- A JPEG is refused on Read with the design's explanation
await tool.getByRole('button', { name: 'Remove' }).last().click();
await tool.locator('input[aria-label="Choose a PNG"]').setInputFiles(join(process.cwd(), 'public', 'assets', 'station-wellington.jpg'));
await tool.getByText('a JPEG can never contain a readable Ghostframe message', { exact: false }).waitFor();
ok(true, 'JPEG on Read shows the jpegRead explanation');

console.log('screenshots in ' + out);
await browser.close();
