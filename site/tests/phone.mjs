// Phone layout (mobile pass, below 760 px): menu, Try it sheet and view switch, How it works cards.
//   node tests/phone.mjs [siteUrl]
import { chromium } from 'playwright';

const SITE = process.argv[2] || 'http://127.0.0.1:5178/';
const ok = (cond, what) => { if (!cond) throw new Error('FAILED: ' + what); console.log('ok  ' + what); };
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 375, height: 812 }, hasTouch: true, isMobile: true });
await page.goto(SITE, { waitUntil: 'networkidle' });
const overflow = () => page.evaluate(() => document.body.style.overflow);
const active = (sel) => page.evaluate((s) => !!document.activeElement?.closest(s), sel);
const noSideScroll = async (what) => ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), what + ': no horizontal overflow');

// ---- Menu
const burger = page.getByRole('button', { name: 'Open menu' });
ok(await page.locator('header nav:not(#gf-menu nav)').count() === 0, 'nav row replaced by the burger');
ok((await burger.boundingBox()).height >= 44, 'burger is 44 px');
await burger.click(); await page.waitForTimeout(300);
const close = page.getByRole('button', { name: 'Close menu' });
ok(await close.getAttribute('aria-expanded') === 'true', 'aria-expanded is true while open');
ok(await active('#gf-menu'), 'focus moves into the menu');
ok(await overflow() === 'hidden', 'page scroll is locked');
await noSideScroll('menu open');
for (let i = 0; i < 8; i++) await page.keyboard.press('Tab');
ok(await active('#gf-menu') || await page.evaluate(() => document.activeElement?.getAttribute('aria-controls') === 'gf-menu'), 'Tab stays in the menu');
await page.keyboard.press('Escape'); await page.waitForTimeout(300);
ok(await burger.getAttribute('aria-expanded') === 'false', 'Escape closes the menu');
ok(await page.evaluate(() => document.activeElement?.getAttribute('aria-label') === 'Open menu'), 'focus returns to the burger');
ok(await overflow() === '', 'page scroll is unlocked');
await burger.click(); await page.waitForTimeout(300);
await page.locator('#gf-menu a', { hasText: 'Read a message' }).click(); await page.waitForTimeout(900);
ok(await burger.getAttribute('aria-expanded') === 'false', 'a menu link closes the menu');
ok(await page.getByRole('tab', { name: 'Read a message' }).getAttribute('aria-selected') === 'true', '“Read a message” opens the Read tab');
ok(await page.evaluate(() => Math.abs(document.querySelector('#tool').getBoundingClientRect().top) < 120), 'and scrolls to the tool');
await burger.click(); await page.waitForTimeout(300);
await page.setViewportSize({ width: 800, height: 812 }); await page.waitForTimeout(300);
ok(await page.locator('#gf-menu').count() === 0 && await overflow() === '', 'menu closes and scroll unlocks above 760 px');
await page.setViewportSize({ width: 375, height: 812 }); await page.waitForTimeout(300);

// ---- Try it: summary, sheet, view switch
const summary = page.locator('#try button[aria-haspopup=dialog]');
ok(await page.locator('#try [aria-label=Cover]').count() === 0, 'control column replaced on phones');
ok((await summary.innerText()).includes('Portrait · Subtle'), 'summary shows photo and mode');
await summary.click(); await page.waitForTimeout(400);
const sheet = page.getByRole('dialog', { name: 'Photo and mode' });
ok(await sheet.isVisible(), 'summary opens the sheet');
ok(await active('[role=dialog]'), 'focus moves into the sheet');
ok(await overflow() === 'hidden', 'page scroll is locked behind the sheet');
await noSideScroll('sheet open');
await sheet.getByRole('button', { name: 'Coffee beans' }).click();
await sheet.getByRole('radio', { name: /^Long/ }).click(); await page.waitForTimeout(300);
ok((await summary.innerText()).includes('Coffee beans · Long'), 'choices update at once');
ok((await page.locator('#try img[alt="Coffee beans · Long"]').count()) === 1, 'stage shows the chosen photo and mode');
await page.keyboard.press('Escape'); await page.waitForTimeout(400);
ok(!(await sheet.isVisible()), 'Escape closes the sheet');
ok(await page.evaluate(() => document.activeElement?.getAttribute('aria-haspopup') === 'dialog'), 'focus returns to the summary');
ok(await overflow() === '', 'scroll unlocked after the sheet');
await summary.click(); await page.waitForTimeout(400);
await page.mouse.click(180, 40); await page.waitForTimeout(400);
ok(!(await sheet.isVisible()), 'tapping the scrim closes the sheet');
await summary.click(); await page.waitForTimeout(400);
await sheet.getByRole('button', { name: 'Show this photo' }).click(); await page.waitForTimeout(400);
ok(!(await sheet.isVisible()), '“Show this photo” closes the sheet');
const views = page.locator('#try [role=radiogroup][aria-label=View] [role=radio]');
ok(await views.count() === 3, 'Compare · Difference · Model switch');
await page.getByRole('radio', { name: 'What the model sees' }).click(); await page.waitForTimeout(400);
ok(await page.getByRole('radio', { name: 'What the model sees' }).getAttribute('aria-checked') === 'true', 'switch names are the full labels and select the view');
for (const v of await views.all()) ok((await v.boundingBox()).height >= 44, 'switch option ≥ 44 px');

// ---- Pixel inspector: a finger held down and dragged moves the marker (Compare and Difference)
const cdp = await page.context().newCDPSession(page);
const drag = async (box) => {
  const y = box.y + box.height * 0.5, pts = [0.15, 0.4, 0.65, 0.85].map((f) => ({ x: box.x + box.width * f, y }));
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [pts[0]] });
  for (const p of pts.slice(1)) { await cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [p] }); await page.waitForTimeout(60); }
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
};
for (const [view, alt] of [['Original vs encoded', 'Marked photo. Point to inspect a pixel.'], ['Amplified difference', 'Amplified difference. Point to zoom.']]) {
  await page.getByRole('radio', { name: view }).click(); await page.waitForTimeout(400);
  const pic = page.locator(`#try img[alt="${alt}"]`);
  await pic.scrollIntoViewIfNeeded(); await page.waitForTimeout(300);
  const marker = pic.locator('xpath=following-sibling::span[1]');
  await drag(await pic.boundingBox());
  const left = await marker.evaluate((m) => parseFloat(m.style.left));
  ok(left > 80 && left < 90, `${view}: a finger drag moves the marker across the picture (now at ${left.toFixed(0)}%)`);
}
await page.getByRole('radio', { name: 'What the model sees' }).click(); await page.waitForTimeout(300);

// ---- How it works cards
const how = page.locator('#how');
await how.scrollIntoViewIfNeeded(); await page.waitForTimeout(600);
ok(await how.locator('canvas').count() === 1, 'only the active card has an animation');
await how.getByRole('button', { name: 'Step 05' }).click(); await page.waitForTimeout(1200);
ok(await how.getByRole('button', { name: 'Step 05' }).getAttribute('aria-current') === 'step', 'dot 05 makes card 05 active');
ok(await how.locator('[aria-label="Step 05 of 05"] canvas').count() === 1, 'and card 05 plays');
ok(await how.locator('details').evaluate((d) => getComputedStyle(d).marginLeft) === '0px', 'Technical detail has no indent');
await noSideScroll('How it works');
await browser.close();
