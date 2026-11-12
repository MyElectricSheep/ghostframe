import { chromium } from 'playwright';
const b = await chromium.launch();
const ctx = await b.newContext({ viewport: { width: 375, height: 800 }, hasTouch: true, isMobile: true, reducedMotion: 'reduce' });
const p = await ctx.newPage();
await p.goto('http://127.0.0.1:5178/', { waitUntil: 'networkidle' });
const small = await p.evaluate(() => [...document.querySelectorAll('button, select, a[href]')].filter((el) => {
  const r = el.getBoundingClientRect(), cs = getComputedStyle(el);
  if (!r.width || cs.visibility === 'hidden' || el.closest('[hidden]')) return false;
  if (el.matches('.tile, [data-abbr]') || el.closest('p, li, footer, details li')) return false;
  const after = getComputedStyle(el, '::after');
  const hit = el.matches('.hit-44') ? Math.max(r.height, parseFloat(after.height) || 0) : r.height;
  return hit < 44;
}).map((el) => (el.textContent || el.getAttribute('aria-label') || el.tagName).trim().slice(0, 30) + ' ' + Math.round(el.getBoundingClientRect().height)));
console.log(small.length ? 'under 44px: ' + small.join(' | ') : 'all controls >= 44px');
await p.screenshot({ path: process.argv[2], fullPage: false });
await b.close();
