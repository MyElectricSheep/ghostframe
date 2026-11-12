// Daily encode counter: when it fetches, what it shows, and when it hides.
//   node tests/counter.mjs [siteUrl]     (site and API running; the API's real /api/quota is used first)
import { chromium } from 'playwright';

const SITE = process.argv[2] || 'http://127.0.0.1:5178/';
const ok = (cond, what) => { if (!cond) throw new Error('FAILED: ' + what); console.log('ok  ' + what); };
const browser = await chromium.launch();
const counter = (p) => p.locator('#tool [role=status]').filter({ hasText: 'encodes left today' });

// Real API: no fetch until the section is in view, then the server's own limit.
let page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
let calls = 0; page.on('request', (r) => { if (r.url().endsWith('/api/quota')) calls++; });
await page.goto(SITE, { waitUntil: 'networkidle' }); await page.waitForTimeout(500);
ok(calls === 0, 'no quota request before the section scrolls into view');
await page.locator('#tool').scrollIntoViewIfNeeded(); await page.waitForTimeout(800);
ok(calls === 1, 'one request when it scrolls into view');
const real = await (await page.request.get(new URL('/api/quota', SITE).href)).json();
ok((await counter(page).innerText()).startsWith(`${real.left} / ${real.limit} encodes left today`), `shows the server's count (${real.left} / ${real.limit})`);
ok(await counter(page).getAttribute('aria-live') === 'polite', 'polite live region');
await page.evaluate(() => { Object.defineProperty(document, 'visibilityState', { value: 'visible', configurable: true }); document.dispatchEvent(new Event('visibilitychange')); });
await page.waitForTimeout(500);
ok(calls === 2, 'refetches when the tab becomes visible again');
await page.close();

// Encoder replies: accepted → refetch; "site limit reached" → 0 at once.
page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
let left = 12, slow = false; calls = 0;
await page.route('**/api/quota', async (r) => { calls++; if (slow) await new Promise((s) => setTimeout(s, 1500)); r.fulfill({ json: { left, limit: 20, resets_at: '2026-11-13T00:00:00Z' } }); });
let reply = { status: 202, json: { id: 'j1', mode: 'subtle', state: 'queued', position: 0, progress: 0, elapsed_s: 0, slow: false, colour_conversion: null } };
await page.route('**/api/encode', (r) => r.fulfill(reply));
await page.route('**/api/jobs/**', (r) => r.fulfill({ json: { ...reply.json, state: 'queued' } }));
await page.goto(SITE, { waitUntil: 'networkidle' });
const tool = page.locator('#tool');
await tool.scrollIntoViewIfNeeded(); await page.waitForTimeout(600);
ok((await counter(page).innerText()).startsWith('12 / 20'), 'uses the limit the server sends, not 50');
await tool.getByRole('button', { name: 'Use a sample photo' }).click();
await tool.getByText('Meets the input rules').first().waitFor();
await tool.locator('#gf-hmsg').fill('Test'); await tool.locator('#gf-hp1').fill('harbour lantern orbit'); await tool.locator('#gf-hp2').fill('harbour lantern orbit');
const before = calls; left = 11;
await tool.getByRole('button', { name: /Encode/ }).click(); await page.waitForTimeout(800);
ok(calls > before && (await counter(page).innerText()).startsWith('11 / 20'), 'refetches after an encode is accepted');
await tool.getByRole('button', { name: 'Cancel' }).click(); await page.waitForTimeout(600);
reply = { status: 429, json: { error: 'site_limit' } }; slow = true;
await tool.getByRole('button', { name: /Encode/ }).click(); await page.waitForTimeout(300);
ok((await counter(page).innerText()).startsWith('0 / 20'), '"site limit reached" shows 0 at once, before the refetch answers');
ok((await counter(page).innerText()).includes('Closed until midnight UTC'), 'closed note');
ok(await tool.getByText('Encoding is closed for today', { exact: true }).count() === 1, 'only the existing banner, no new message');
await page.close();

// A failed quota request hides the counter.
page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
await page.route('**/api/quota', (r) => r.fulfill({ status: 503, json: { error: 'unreachable' } }));
await page.goto(SITE, { waitUntil: 'networkidle' });
await page.locator('#tool').scrollIntoViewIfNeeded(); await page.waitForTimeout(600);
ok(await counter(page).count() === 0, 'hidden when the quota request fails');
await browser.close();
