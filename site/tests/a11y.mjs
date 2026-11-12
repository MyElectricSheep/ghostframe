// Keyboard paths: divider slider, tiles, tooltips, tabs, touch targets.
//   node tests/a11y.mjs [siteUrl]
import { chromium } from 'playwright';

const SITE = process.argv[2] || 'http://127.0.0.1:5178/';
const ok = (cond, what) => { if (!cond) throw new Error('FAILED: ' + what); console.log('ok  ' + what); };
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 900 }, reducedMotion: 'reduce' });
await page.goto(SITE, { waitUntil: 'networkidle' });

// Divider: a keyboard range input with a visible focus ring on the knob.
const divider = page.getByRole('slider', { name: 'Divider' });
await divider.focus();
await page.keyboard.press('ArrowRight');
ok((await divider.getAttribute('aria-valuetext')) === '51% original', 'divider moves with the arrow keys');

// Tiles: buttons with labels; arrows move the selection and the focus.
await page.locator('#try').getByRole('radio', { name: 'What the model sees' }).click();
const tiles = page.locator('#try [data-index]');
ok((await tiles.count()) === 80, '80 focusable tiles for Subtle');
await tiles.nth(0).focus();
await page.keyboard.press('ArrowRight');
ok(await tiles.nth(1).evaluate((el) => el === document.activeElement), 'ArrowRight focuses the next tile');
ok((await tiles.nth(1).getAttribute('aria-pressed')) === 'true', 'and selects it');
await page.keyboard.press('ArrowDown');
ok(await tiles.nth(11).evaluate((el) => el === document.activeElement), 'ArrowDown moves one row down');
ok(/^Tile row 2, column 2, turned \d+ degrees$/.test(await tiles.nth(11).getAttribute('aria-label')), 'tile labels name row, column and angle');

// Acronym tooltip: opens on click, closes on Esc.
const psnr = page.locator('#limits [data-abbr]').first();
await psnr.scrollIntoViewIfNeeded();
await psnr.click();
ok(await page.locator('#gf-abbr').isVisible(), 'PSNR tooltip opens on click');
await page.keyboard.press('Escape');
ok(!(await page.locator('#gf-abbr').isVisible()), 'and closes on Esc');

// Tabs: arrow keys switch between Hide and Read.
await page.getByRole('tab', { name: 'Hide a message' }).focus();
await page.keyboard.press('ArrowRight');
ok((await page.getByRole('tab', { name: 'Read a message' }).getAttribute('aria-selected')) === 'true', 'tabs switch with the arrow keys');

// Status regions announce results.
ok((await page.locator('[role="status"][aria-live="polite"]').count()) >= 3, 'reveal, encode and read results are live regions');

await browser.close();
