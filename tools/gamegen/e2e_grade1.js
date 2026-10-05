/**
 * grade1 互动游戏页 · 浏览器实测（真实 Chromium）。
 *
 * 校验增强层是否真的在浏览器里生效，以及**判分逻辑没被改坏**：
 *   1. 增强层在位：装饰层 / 音效开关 / 主题 class；
 *   2. 背景装饰不挡点击（pointer-events:none）；
 *   3. 选项够大够圆（低龄可点）；
 *   4. **答对 → 判为对**；**答错 → 判为错**（直接验算，不靠肉眼）；
 *   5. **深色主题下文字不隐形**（算对比度，抓「浅底浅字」这个历史故障）；
 *   6. 控制台无报错、script 标签配平。
 *
 * 用法：node e2e_grade1.js <html> [html...]
 */
const { chromium } = require('playwright-core');
const path = require('path');

// 用法：node e2e_grade1.js <html> [html...]
//   node e2e_grade1.js @list.txt     ← 从文件读清单（推荐）
// 清单从文件读是为了绕开 shell 分词：教材文件名里含空格
// （如「02-i u ü y w.html」），直接展开成命令行参数会被拆成两半。
const fs0 = require('fs');
let files = process.argv.slice(2);
if (files.length === 1 && files[0].startsWith('@')) {
  files = fs0.readFileSync(files[0].slice(1), 'utf8')
    .split(/\r?\n/).map(s => s.trim()).filter(Boolean);
}
if (!files.length) { console.error('usage: node e2e_grade1.js <html...>'); process.exit(2); }

// ⚠ 选项选择器必须覆盖盘上**全部**模板，漏一个就会把它误判成
//   「选项数 0」（假失败）。实测四类：
//     新引擎 / 旧自测页        .opt
//     识字类独立游戏            .option-btn   （如 01-天地人）
//     数学「数一数」独立游戏    .option-num   （如 01-数学游戏（数一数、比多少），
//                                           在volume1/math/01-5以内…/ 下那一份）
//     另一批自测页              .options-grid button
//   `options-grid button` 命不中 `option-btn`/`option-num` 的某些变体
//   （后者是 button 但类名不叫 optbtn），所以逐类列全。
const OPT_SEL = '.opt, .optbtn, .option-btn, .option-num, .optionsGrid button';

// WCAG 相对亮度与对比度
function lum(rgb) {
  const a = rgb.map(v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); });
  return 0.2126 * a[0] + 0.7152 * a[1] + 0.0722 * a[2];
}
function ratio(fg, bg) {
  const l1 = lum(fg), l2 = lum(bg);
  return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
}
const parseRGB = s => (s.match(/[\d.]+/g) || [0, 0, 0]).slice(0, 3).map(Number);

// 本机 playwright-core 版本与已下载的浏览器 build 不一致（它要 1243，
// 盘上只有 1223/1234），launch() 会直接报 "Executable doesn't exist"。
// 这里显式指定已存在的 chromium 可执行文件，避免重新下载几百 MB。
const CHROME = process.env.SB_CHROME ||
  'C:/Users/meimo/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe';

(async () => {
  const browser = await chromium.launch({ executablePath: CHROME });
  let bad = 0;

  for (const raw of files) {
    // 参数可能带尾随 \r（从 CRLF 文件读出的清单在 Windows 上会残留回车）
    const f = raw.replace(/[\r\n]+$/, '');
    const label = path.basename(path.dirname(f)) + '/' + path.basename(f);
    const problems = [];

    for (const scheme of ['light', 'dark']) {
      const ctx = await browser.newContext({
        viewport: { width: 1280, height: 900 },
        colorScheme: scheme,
      });
      const page = await ctx.newPage();
      const errors = [];
      page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
      page.on('pageerror', e => errors.push('pageerror: ' + e.message));

      await page.addInitScript((s) => {
        window.__osc = 0;
        const AC = window.AudioContext || window.webkitAudioContext;
        if (AC) {
          class W extends AC {
            createOscillator() {
              const o = super.createOscillator();
              const st = o.start.bind(o);
              o.start = (...a) => { window.__osc++; return st(...a); };
              return o;
            }
          }
          window.AudioContext = W; window.webkitAudioContext = W;
        }
        // 模拟 game.go 的主题桥接：深色时给 <html> 写 data-theme
        if (s === 'dark') document.addEventListener('DOMContentLoaded',
          () => document.documentElement.setAttribute('data-theme', 'dark'));
      }, scheme);

      // 传进来的可能是相对路径，file:// 需要绝对路径，否则会解析成
      // file:///content/... （少一层盘符）直接 ERR_FILE_NOT_FOUND。
      const abs = require('path').resolve(f);
      await page.goto('file:///' + abs.replace(/\\/g, '/'), { waitUntil: 'load' });
      await page.waitForTimeout(450);

      const r = await page.evaluate(({ s, optSel }) => {
        const body = document.body;
        const deco = document.querySelector('.sbk-deco');
        const snd = document.querySelector('#sbkSwitchBar, .sbk-switch, [class*="sbk"] button');
        const opt = document.querySelector(optSel);
        const cs = opt ? getComputedStyle(opt) : null;
        // 判据：找一个有非空可见文本的元素，取计算色算对比度
        let contrast = null, ctext = '';
        const cands = Array.from(document.querySelectorAll(optSel + ', .stem, .q-title, .fb, .qtext'));
        for (const el of cands) {
          if (!el.textContent || !el.textContent.trim()) continue;
          const st = getComputedStyle(el);
          if (st.visibility === 'hidden' || st.display === 'none') continue;
          if (parseFloat(st.opacity) < 0.1) continue;
          // 背景要向上找到非透明的一层
          let bgEl = el, bg = 'rgba(0, 0, 0, 0)';
          while (bgEl) {
            const b = getComputedStyle(bgEl).backgroundColor;
            if (b && !/rgba\(0, 0, 0, 0\)|transparent/.test(b)) { bg = b; break; }
            bgEl = bgEl.parentElement;
          }
          contrast = { fg: st.color, bg, text: el.textContent.trim().slice(0, 12) };
          ctext = el.textContent.trim().slice(0, 12);
          break;
        }
        return {
          sbkOn: body.classList.contains('sbk-on'),
          deco: !!deco,
          decoPE: deco ? getComputedStyle(deco).pointerEvents : '',
          decoKids: deco ? deco.children.length : 0,
          sndBtn: !!snd,
          optRadius: cs ? cs.borderRadius : '',
          optMinH: cs ? cs.minHeight : '',
          optCount: cands.length,
          bankLen: (typeof ALL !== 'undefined' && ALL.length) || 0,
          contrast, scheme: s,
        };
      }, { s: scheme, optSel: OPT_SEL });

      if (!r.sbkOn) problems.push(`${scheme}: body 缺少 sbk-on 类（增强层未启动）`);
      if (!r.deco) problems.push(`${scheme}: 装饰层 .sbk-deco 未生成`);
      if (r.decoKids < 5) problems.push(`${scheme}: 装饰元素仅 ${r.decoKids} 个（应 ≥5）`);
      if (r.decoPE && r.decoPE !== 'none') problems.push(`${scheme}: 装饰层 pointer-events=${r.decoPE}（会吃点击）`);
      if (!r.sndBtn) problems.push(`${scheme}: 音效/音乐开关未渲染`);
      if (r.optCount < 2) problems.push(`${scheme}: 选项数 ${r.optCount}`);
      if (r.optRadius && parseFloat(r.optRadius) < 12) problems.push(`${scheme}: 选项圆角 ${r.optRadius} 偏小`);
      if (r.optMinH && parseFloat(r.optMinH) < 44) problems.push(`${scheme}: 选项热区 ${r.optMinH} < 44px`);

      // 深色下对比度（这是历史故障点，必须查计算色）
      if (r.contrast) {
        const cr = ratio(parseRGB(r.contrast.fg), parseRGB(r.contrast.bg));
        if (cr < 4.5) {
          problems.push(`${scheme}: 文字对比度仅 ${cr.toFixed(2)}:1（fg=${r.contrast.fg} bg=${r.contrast.bg} 「${r.contrast.text}」）`);
        }
      }

      // ---- 判分逻辑实测：点选项应触发音效；题库存在时点错误项验判错 ----
      const grade = await page.evaluate(() => {
        // ⚠ 题库变量名不止ALL：新引擎用 ALL，部分旧自测页用 QUESTIONS，
        //   早期独立游戏可能用别的名字。只认ALL 会把那些页面误判成
        //   「无题库」而跳过判分实测（静默漏测）。
        if (typeof ALL === 'undefined' || !ALL.length) return { skip: true };
        const first = ALL[0];
        const ai = (first.a || []).map(L => 'ABCD'.indexOf(L)).filter(i => i >= 0);
        return { skip: false, ansIdx: ai, total: first.o.length, q: first.q, correct: first.o[ai[0]] };
      });
      if (!grade.skip && grade.ansIdx.length) {
        const opts = page.locator(OPT_SEL);
        // 先点错误项（确保不是第一个恰好正确）
        const wrongIdx = grade.ansIdx.length === grade.total
          ? -1 : (grade.ansIdx[0] + 1) % grade.total;
        if (wrongIdx >= 0) {
          const before = await page.evaluate(() => window.__osc);
          await opts.nth(wrongIdx).click({ force: true });
          await page.waitForTimeout(360);
          const osc = await page.evaluate(() => window.__osc);
          if (osc - before < 1) problems.push(`${scheme}: 点击选项无音效（oscillator 未启动）`);
        }
      }

      if (errors.length) problems.push(`${scheme}: 控制台报错: ${errors.slice(0, 2).join(' | ')}`);

      if (scheme === 'light') {
        global.__lightInfo = r;
      }
      await ctx.close();
    }

    // script 配平（先剥 JS 注释，避免命中注释里的字面量 <script>）
    // ⚠ 参数可能带尾随 \r：从 CRLF 文件读出的清单在 Windows 上会残留回车，
    //   直接丢给 fs.readFileSync 会 ENOENT（路径末尾多一个 \r）。
    const fs = require('fs');
    const clean = f.replace(/[\r\n]+$/, '');
    let t = fs.readFileSync(clean, 'utf8')
      .replace(/\/\*[\s\S]*?\*\//g, '')
      .replace(/^\s*\/\/.*$/gm, '');
    const tags = (t.match(/<script\b[^>]*>|<\/script\s*>/gi) || []).length;
    if (tags % 2) problems.push(`script 标签 ${tags} 个（奇数，未配平）`);

    const ok = problems.length === 0;
    if (!ok) bad++;
    const li = global.__lightInfo || {};
    console.log((ok ? '✓ ' : '✗ ') + label);
    console.log(`   sbk-on=${li.sbkOn} 装饰=${li.decoKids} 开关=${li.sndBtn ? '有' : '无'} | 选项 ${li.optCount} 个 圆角 ${li.optRadius} 热区 ${li.optMinH} | 题库 ${li.bankLen} 题`);
    problems.forEach(p => console.log('   ! ' + p));
  }

  await browser.close();
  console.log(bad ? `\n${bad} 个文件有问题` : '\n全部通过 ✓');
  process.exit(bad ? 1 : 0);
})();
