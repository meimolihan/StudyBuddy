/**
 * grade1 判分逻辑实测：点选项 → 页面自己判的对错，必须与题库答案一致。
 *
 * 这是「不改变答题结果判断逻辑」最硬的证据：
 * 增强层在页面上 Enhanced，判定结果仍由原引擎给出，且与数据自洽。
 * 对旧自测页（点选 + 提交判分）与新引擎（点一下即判）分别处理。
 */
const { chromium } = require('playwright-core');
const path = require('path');
const CHROME = process.env.SB_CHROME ||
  'C:/Users/meimo/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe';

let files = process.argv.slice(2);
const fs0 = require('fs');
if (files.length === 1 && files[0].startsWith('@')) {
  files = fs0.readFileSync(files[0].slice(1), 'utf8')
    .split(/\r?\n/).map(s => s.replace(/[\r\n]+$/, '').trim()).filter(Boolean);
}

// ⚠ 选项选择器要覆盖盘上全部四类模板，漏一个就把该页判成「第一题选项数 0」：
//   新引擎 / 旧自测页 .opt ；早期独立游戏 .option-btn ；另一批 .optionsGrid button
const OPT_SEL = '.opt, .optbtn, .option-btn, .optionsGrid button';

(async () => {
  const browser = await chromium.launch({ executablePath: CHROME });
  let bad = 0;

  for (const f of files) {
    const label = path.basename(path.dirname(f)) + '/' + path.basename(f);
    const problems = [];
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    const page = await ctx.newPage();
    const errs = [];
    page.on('pageerror', e => errs.push(e.message));
    await page.goto('file:///' + path.resolve(f).replace(/\\/g, '/'), { waitUntil: 'load' });
    await page.waitForTimeout(400);

    const info = await page.evaluate((optSel) => {
      // 题库变量名有两种：新引擎用 ALL，早期独立游戏用 QUESTIONS。
      // 都要认，否则那6 个 legacy 页面会被当成「无题库」而测不到。
      let bank = null, bankName = '';
      if (typeof ALL !== 'undefined' && ALL && ALL.length) { bank = ALL; bankName = 'ALL'; }
      else if (typeof QUESTIONS !== 'undefined' && QUESTIONS && QUESTIONS.length) { bank = QUESTIONS; bankName = 'QUESTIONS'; }
      if (!bank) return { skip: true };
      const A = 'ABCD';

      // ⚠ 「数一数」这类独立玩法：题库条目形如
      //   {target:{emoji,name,unit}, targetCount:N, distractors:[...]}
      //   —— 没有 o / a / q 字段，页面也没有 .q 和文字选项，
      //   答案是「点数字 N」（.option-num）。要在下面崩掉之前先识别出来。
      const first0 = bank[0];
      const isCountGame = !!(first0 && typeof first0.targetCount === 'number' && !first0.o);
      if (isCountGame) {
        return {
          skip: false, isCountGame: true, n: bank.length, bankName,
          wantCount: first0.targetCount,
          targetName: (first0.target || {}).name || '',
          hasSubmit: false,
        };
      }

      // ⚠⚠ 不能直接用 bank[0]！
      //   旧自测页的 pickRound() 会 shuffle 整库 + 用 localStorage 里的
      //   `seen` 去重，**随机抽 PER_ROUND 道题**，页面第一屏很可能是 ALL[3]
      //   而不是 ALL[0]（实测「我上学了（选择）」页 ALL[0] 答案「开开心心」，
      //   页面首题却是 ALL[1]「见到老师时…」）。拿 ALL[0] 去页面上找选项
      //   必然找不到，会把 88 个正常页面全判成「判分异常」—— 假失败。
      //   正解：**按页面实际渲染出来的首题，反查它对应题库里哪一条**。
      const q0 = document.querySelector('.q');
      const opts = q0 ? Array.from(q0.querySelectorAll(optSel)) : [];
      // ⚠ 归一化必须连「A. 」这类序号前缀一起剥掉。
      //   旧自测页按钮文本是「○A. 大米🔊」，只删图标和空白会留下「A.大米」，
      //   与题库里的「大米」既不等值也不互相 include → 后面找不到正确项。
      const strip = s => (s || '').replace(/[○✔✘🔊\s]/g, '').replace(/^[A-D][.、．)）]\s*/, '');
      const pageOptTexts = opts.map(o => strip(o.textContent));
      const stemEl = q0 && q0.querySelector('.stem, .q-title, .qt, .qh, .title');
      const stem = strip(stemEl ? stemEl.textContent : '');

      // ⚠⚠ 定位顺序：**先按题干，再按选项集合**。
      //   判断题整页 40 道题的选项全是「正确/错误」，选项集合完全相同 ——
      //   只按选项反查会永远撞在 bank[0] 上，于是拿第0 题的答案去点
      //   页面上的别的题，判成 wrong → 把几十个正常页面全判成异常。
      //   （实测「01-识字（一）（判断）/01-天地人.html」：页面首题是
      //     ALL[34]，按选项查却拿到 ALL[0]。）
      let hit = -1;
      if (stem) {
        for (let i = 0; i < bank.length; i++) {
          if (bank[i] && strip(bank[i].q) === stem) { hit = i; break; }
        }
      }
      let how = 'stem';
      if (hit < 0) {
        how = 'opts';
        const set = new Set(pageOptTexts);
        for (let i = 0; i < bank.length; i++) {
          const o = bank[i] && bank[i].o;
          if (!o || o.length !== pageOptTexts.length) continue;
          if (o.every(x => set.has(strip(x))) && new Set(o.map(strip)).size === set.size) { hit = i; break; }
        }
      }
      if (hit < 0) return { skip: false, noHit: true, n: bank.length, bankName,
        pageOptTexts, stem, hasSubmit: !!document.querySelector('#submit, .btn.sec, button[id*=submit]') };

      const item = bank[hit];
      const ansIdx = (item.a || []).map(L => A.indexOf(L)).filter(i => i >= 0 && i < item.o.length);
      // ⚠⚠ 必须支持**多选**：`a:["C","D"]` 是合法题库数据。
      //   实测「01-识字（一）（选择）/03-口耳目.html」里
      //   {t:"m", q:"下面用「目」做的事有（　）。", a:["C","D"]}。
      //   只取 ansIdx[0] 点一个，页面当然判wrong —— 那是测试不支持多选，
      //   不是页面判分错。所以要把**全部**正确项的下标带出去。
      const correctTexts = ansIdx.map(i => item.o[i]);
      return {
        skip: false, n: bank.length, ansIdx, nOpt: item.o.length,
        correctText: correctTexts[0], correctTexts,
        multi: correctTexts.length > 1,
        isMultiType: item.t === 'm',
        bankName, hit, how,
        firstQ: item.q,
        hasSubmit: !!document.querySelector('#submit, .btn.sec, button[id*=submit]'),
      };
    }, OPT_SEL);

    if (info.skip) { console.log('- ' + label + '（无题库，跳过）'); await ctx.close(); continue; }

    // ⚠ 「数一数」这类**独立玩法游戏**不走选择题：题库条目是
    //   {target:{emoji,name,unit}, targetCount:N, distractors:[...] }，
    //   页面没有 .q、没有文字选项，答案是「点数字 N」。
    //   handleAnswer() 里 `n === q.targetCount` 才加 .correct。
    //   拿选择题那套断言去测它，必然报「找不到 .q / 选项为空」—— 假失败。
    //   这里单独走数字按钮的口径。
    if (info.isCountGame) {
      const n0 = await page.locator('.option-num').count();
      if (n0 < 2) {
        problems.push('数字选项数 ' + n0);
      } else {
        const want = info.wantCount;
        const before = await page.evaluate(() => (document.querySelector('#score') || {}).textContent || '');
        await page.locator('.option-num', { hasText: new RegExp('^\\s*' + want + '\\s*$') }).first()
          .click({ force: true });
        await page.waitForTimeout(450);
        const r = await page.evaluate(() => ({
          ok: !!document.querySelector('.option-num.correct'),
          score: (document.querySelector('#score') || {}).textContent || '',
          fb: (document.querySelector('.feedback-bar') || {}).textContent || '',
        }));
        if (!r.ok) problems.push(`点正确数字「${want}」后未出现 .option-num.correct（判分异常）`);
        if (before && r.score === before) problems.push('点正确数字后得分未变化（判分异常）');
        const cOk = !problems.length;
        console.log((cOk ? '✓ ' : '✗ ') + label);
        console.log(`   数一数玩法 | 首题答案 ${want} 个 | correct=${r.ok} 得分「${r.score}」`);
        problems.forEach(p => console.log('   ! ' + p));
        await ctx.close();
        if (!cOk) bad++;
        continue;
      }
    }

    if (info.noHit) {
      problems.push('页面首题的选项在题库里找不到对应条目（页面选项：' +
        (info.pageOptTexts || []).join(' / ') + '）');
    }
    if (!info.ansIdx || !info.ansIdx.length) { problems.push('题库答案下标全部越界'); }

    // 找到第一题对应的选项容器
    const scope = await page.evaluate(() => {
      const q = document.querySelector('.q');
      if (q) return { sel: '.q', idx: 0 };
      return { sel: null, idx: -1 };
    });

    let graded = null;
    if (scope.sel) {
      const q0 = page.locator('.q').first();
      const opts = q0.locator(OPT_SEL);
      const n = await opts.count();
      if (n < 2) problems.push('第一题选项数 ' + n);
      else {
        // ⚠ 必须按**文本**定位，不能按下标：
        //   新引擎默认 SHUFFLE=true，每次进入选项顺序都不同；旧自测页按钮
        //   文本还带「○A. 」前缀和 🔊 图标，既不能全等匹配也不能按下标。
        const texts = await opts.allTextContents();
        // 与上面 info 里的 strip 保持同一套归一化（序号前缀也要剥）
        const norm = t => String(t).replace(/[○✔✘🔊\s]/g, '').replace(/^[A-D][.、．)）]\s*/, '');
        const findIdx = t => {
          const target = norm(String(t));
          const hit = texts.findIndex(x => norm(x) === target);
          if (hit >= 0) return hit;
          const cands = texts.map((x, i) => ({ i, s: norm(x) })).filter(o => o.s.includes(target) || target.includes(o.s));
          return cands.length === 1 ? cands[0].i : -1;
        };
        // 多选题要逐个定位（不能只取第一个）
        const rightIdxs = (info.correctTexts || [info.correctText])
          .map(t => findIdx(t));
        const missing = rightIdxs.filter(i => i < 0);
        if (missing.length) {
          problems.push(`页面上找不到正确选项「${(info.correctTexts || []).join('、')}」，实际选项：${texts.map(t => t.trim()).join(' / ')}`);
        }
        const rightSet = new Set(rightIdxs.filter(i => i >= 0));
        const others = texts.map((_t, i) => i).filter(i => !rightSet.has(i));
        // ⚠ 点 .otext（选项正文），不要点整个 .opt：
        //   旧自测页的 .opt 里嵌着一个 🔊 朗读按钮，它自己带
        //   stopPropagation，点它等于没选答案 → 提交后判成 wrong，
        //   会误报成「增强层把判分改坏了」。新引擎没有这层，兜底点自身。
        const clickOpt = async (i) => {
          const o = opts.nth(i);
          const t = o.locator('.otext');
          if (await t.count()) await t.first().click({ force: true });
          else await o.click({ force: true });
        };
        // ⚠ 多选题**不能**先点错项：多选是累加语义，先点错会把它留在
        //   选中集合里，提交必然判 wrong。多选只点全部正确项。
        //   单选题才可以「先点错再点对」——后一次点击会取消前一次。
        if (!info.multi && others.length) {
          await clickOpt(others[0]);
          await page.waitForTimeout(250);
        }
        for (const ri of rightSet) {
          await clickOpt(ri);
          await page.waitForTimeout(220);
        }
        await page.waitForTimeout(200);
        // 旧页需提交才判分
        if (info.hasSubmit) {
          const sb = page.locator('#submit, .btn.sec').first();
          if (await sb.count() && await sb.isEnabled()) {
            await sb.click({ force: true });
            await page.waitForTimeout(500);
          }
        }
        graded = await page.evaluate(() => {
          const q = document.querySelector('.q');
          const ok = q ? q.classList.contains('correct') : null;
          const no = q ? q.classList.contains('wrong') : null;
          const fb = document.querySelector('.fb, #fb');
          return {
            ok, no,
            fbClass: fb ? fb.className : '',
            fbText: fb ? fb.textContent.trim().slice(0, 40) : '',
            // ⚠ 旧自测页的 grade() 是**一次性给全部题**打 .ok/.no 标记
            //   （一屏渲染 20+ 题），所以计数天然是十几，不能当成
            //   「只有一题被标记」。判据应该是「首题那个 .q 里有没有 .ok」。
            markedOk: q ? q.querySelectorAll('.opt.ok, .opt.right').length : 0,
            markedNo: q ? q.querySelectorAll('.opt.no, .opt.wrong').length : 0,
            score: (document.querySelector('#scoreBig, .big') || {}).textContent || '',
          };
        });
        // 新引擎：点对即判，不会有 .q.correct（旧页才有），改看选项与反馈条
        const isNewEngine = await page.evaluate(() => typeof MODE !== 'undefined');
        if (isNewEngine) {
          // ⚠ 不能断言 markedNo===0：为了验证「答错有反馈」，本测试**故意**先点过
          // 一个错误项，页面上会留下那个 .opt.wrong（引擎 620ms 后才移除，
          // 紧接着点正确项就进入下一题了）。这里要验的是**正确项被标对**。
          if (graded.markedOk < 1) problems.push('新引擎：点正确答案后未出现 .opt.right');
          if (!/太棒|答对|真聪明|完全正确|厉害|棒/.test(graded.fbText || '')) {
            problems.push('新引擎：答对反馈文案不对 → ' + JSON.stringify(graded.fbText));
          }
        } else {
          // 旧自测页 grade() 的语义（读源码确认）：
          //   答对 → 只给 .q 加 .correct（**不给** .opt 加 .ok）
          //   答错 → 给 .q 加 .wrong，并把正确项标 .ok、错选标 .no
          // 所以判「答对」的证据是 `.q.correct`，不是 `.opt.ok`。
          // 之前这里断言 markedOk>=1，等于要求「答对时也要标 .ok」——
          // 那是把答错的分支当成答对的分支，88 个页面全被误判。
          if (graded.ok !== true) {
            problems.push('旧自测页：首题未被判为 .correct（判分结果与题库答案不自洽，' +
              '正确项=' + info.correctText + '）');
          }
        }
      }
    } else problems.push('找不到题目容器 .q');

    if (errs.length) problems.push('页面异常: ' + errs.slice(0, 2).join(' | '));

    const ok = problems.length === 0;
    if (!ok) bad++;
    console.log((ok ? '✓ ' : '✗ ') + label);
    console.log(`   题库[${info.bankName}] ${info.n} 题 | 首题答案「${info.correctText}」| 提交按钮=${info.hasSubmit}` +
      (graded ? ` | 判为对=${graded.ok} 判为错=${graded.no} 正确标记=${graded.markedOk} 错误标记=${graded.markedNo} 得分=${graded.score}` : ''));
    if (graded && graded.fbText) console.log(`   反馈：「${graded.fbText}」`);
    problems.forEach(p => console.log('   ! ' + p));
    await ctx.close();
  }

  await browser.close();
  console.log(bad ? `\n${bad} 个文件判分异常` : '\n判分逻辑全部正常 ✓');
  process.exit(bad ? 1 : 0);
})();
