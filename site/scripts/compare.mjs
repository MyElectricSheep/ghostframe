// Side-by-side screenshots: design prototype (left) vs this site (right), per section and width.
//   node scripts/compare.mjs <sectionId|selector> [widths] [outDir]
// Needs the prototype served on :5190 (design-handoff/ghostframe-site) and the site on :5178.
import { chromium } from 'playwright';
import { mkdirSync } from 'node:fs';

const [target = 'top', widthsArg = '1280,768,375', out = 'compare-out', clicks = '', tag = ''] = process.argv.slice(2);
// clicks: '|'-separated Playwright selectors clicked in order before the shot (e.g. 'text=Long|text=What the model sees').
const sel = target.startsWith('#') || target.includes(' ') || target.includes('.') ? target : `#${target}`;
const PROTO = process.env.PROTO_URL || 'http://127.0.0.1:5190/Ghostframe%20v3.dc.html';
const SITE = process.env.SITE_URL || 'http://127.0.0.1:5178/';
mkdirSync(out, { recursive: true });

const browser = await chromium.launch();
for (const width of widthsArg.split(',').map(Number)) {
  const shots = [];
  for (const [name, url] of [['proto', PROTO], ['site', SITE]]) {
    const page = await browser.newPage({ viewport: { width, height: 900 }, reducedMotion: 'reduce' });
    await page.goto(url, { waitUntil: 'networkidle' });
    await page.waitForSelector(sel, { timeout: 30000 });
    await page.evaluate(() => document.fonts.ready);
    if (sel !== 'body header') await page.addStyleTag({ content: 'header{position:static!important}' });
    await page.waitForTimeout(1200);
    for (const c of clicks.split('|').filter(Boolean)) { await page.locator(sel).locator(c).first().click(); await page.waitForTimeout(400); }
    if (clicks) await page.waitForTimeout(2500);
    const el = page.locator(sel).first();
    await el.scrollIntoViewIfNeeded();
    await page.waitForTimeout(300);
    const path = `${out}/${target.replace(/[^\w-]/g, '_')}${tag}-${width}-${name}.png`;
    await el.screenshot({ path, animations: 'disabled' });
    shots.push(path);
    await page.close();
  }
  console.log(shots.join('  '));
}
await browser.close();
