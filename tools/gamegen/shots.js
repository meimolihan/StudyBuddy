/** 抓增强层截图（明/暗 + 桌面/平板/手机），用于人工确认视觉效果。 */
const { chromium } = require('playwright-core');
const path = require('path');
const CHROME = process.env.SB_CHROME ||
  'C:/Users/meimo/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe';
const OUT = 'tools/gamegen/shots';
require('fs').mkdirSync(OUT, { recursive: true });
const targets = process.argv.slice(2);
(async () => {
  const b = await chromium.launch({ executablePath: CHROME });
  const VP = { desktop: { width: 1440, height: 900 }, tablet: { width: 834, height: 1112 }, phone: { width: 390, height: 844 } };
  for (const f of targets) {
    const name = path.basename(path.dirname(f)).replace(/[\\/:*?"<>|（）()]/g, '_');
    for (const [dev, vp] of Object.entries(VP)) {
      for (const scheme of ['light', 'dark']) {
        if (dev !== 'desktop' && scheme === 'dark') continue; // 手机/平板只抓亮色，节省时间
        const c = await b.newContext({ viewport: vp, colorScheme: scheme, deviceScaleFactor: 1 });
        const p = await c.newPage();
        await p.goto('file:///' + path.resolve(f).replace(/\\/g, '/'), { waitUntil: 'load' });
        await p.waitForTimeout(700);
        const out = path.join(OUT, `${name}_${dev}_${scheme}.png`);
        await p.screenshot({ path: out });
        console.log(out);
        await c.close();
      }
    }
  }
  await b.close();
})();
