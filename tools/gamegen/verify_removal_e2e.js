/**
 * 游戏模块删除 · 端到端验收
 *
 * 跑在**隔离实例**（STUDYBUDDY_DATA=data_test，端口 8099）上，
 * 不碰生产库（里面是 admin / anan / yifan 三个真实用户）。
 * 隔离库 users 表已清空，第一个注册者自动成为管理员，免邀请码。
 *
 * 断言两块：
 *   1. 游戏痕迹彻底清零（文案 / 选择器 / ID / 弹窗）
 *   2. 保留能力完好（两张入口卡能点、.is-on 高亮唯一、样式没塌）
 */
const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');

const CHROME = process.env.SB_CHROME ||
  'C:/Users/meimo/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe';
const BASE = process.env.SB_BASE || 'http://127.0.0.1:8099';
const OUT = 'tools/gamegen/shots';
fs.mkdirSync(OUT, { recursive: true });

// 页面里必须彻底消失的东西
const BAN_TEXT = ['游戏题', '资源制作中', '火速开发中', '敬请期待', '/games', '/game/'];
const BAN_SEL = ['sb-game-wip', 'gm-frame', 'gm-bar', 'gm-card', 'wip-modal', 'is-wip', '🎮'];

(async () => {
  const b = await chromium.launch({ executablePath: CHROME });
  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 }, colorScheme: 'light' });
  const p = await ctx.newPage();
  const pageErrs = [];
  p.on('pageerror', e => pageErrs.push(String(e)));
  const fails = [];

  // ---------- 注册（隔离库首个用户 -> 管理员）----------
  await p.goto(BASE + '/register', { waitUntil: 'load' });
  await p.fill('input[name="name"]', '验收员');
  await p.fill('input[name="username"]', 'e2e_check');
  await p.fill('input[name="password"]', 'e2e123456');
  // gender 是必填 radio，但原生 input 被自定义样式隐藏了，要点它外层的 label
  await p.evaluate(() => {
    const el = document.querySelector('input[name="gender"][value="male"]');
    el.checked = true;
    el.dispatchEvent(new Event('change', { bubbles: true }));
  });
  // ⚠️ grade / class_no 是**隐藏 input**，由「点按钮 → 弹窗滚轮」驱动，不是 select。
  //    注册页自带默认值（grade=1、class_no 空），滚轮只是改值，所以不必驱动 UI。
  const hidden = await p.evaluate(() => {
    const o = {};
    for (const f of ['grade', 'class_no', 'volume']) {
      const el = document.querySelector('input[name="' + f + '"]');
      o[f] = el ? el.value : '(无此字段)';
    }
    return o;
  });
  console.log('隐藏字段默认值:', JSON.stringify(hidden));
  await Promise.all([
    p.waitForNavigation({ waitUntil: 'load' }).catch(() => {}),
    p.click('button[type="submit"]'),
  ]);
  console.log('注册后落地:', p.url());

  if (p.url().includes('/register')) {
    // 表单校验没过 —— 把服务端渲染回来的报错段落抓出来，便于定位
    const err = await p.evaluate(() => {
      const t = document.body.innerText;
      const hit = t.split('\n').find(l => /错误|失败|请选择|必填|至少|已被注册|无效|请填写/.test(l));
      return hit ? hit.trim() : '(页面无可见报错文本)';
    });
    fails.push('注册未通过: ' + err);
    console.log('注册报错:', err);
    console.log('可见字段:', await p.evaluate(() =>
      [...document.querySelectorAll('input,select')].map(x => x.name || x.id || x.type).join(', ')));
    await b.close();
    process.exit(1);
  }

  // ---------- /study ----------
  await p.goto(BASE + '/study?qt=choose', { waitUntil: 'load' });
  await p.waitForTimeout(700);

  const bodyText = await p.evaluate(() => document.body.innerText);
  const html = await p.content();
  for (const t of BAN_TEXT) {
    if (bodyText.includes(t)) fails.push(`页面文案仍含「${t}」`);
    if (html.includes(t)) fails.push(`HTML 源码仍含「${t}」`);
  }
  for (const s of BAN_SEL) {
    if (html.includes(s)) fails.push(`HTML 源码仍含「${s}」`);
  }
  // 已删的弹窗不应存在于 DOM
  if (await p.$('.wip-modal')) fails.push('DOM 里仍有 .wip-modal 弹窗');

  // ---------- 入口卡 ----------
  const cards = await p.$$eval('.qtype-card', els => els.map(e => ({
    tag: e.tagName,
    href: e.getAttribute('href') || '',
    name: ((e.querySelector('.qtype-card-name') || {}).textContent || '').trim(),
    desc: ((e.querySelector('.qtype-card-desc') || {}).textContent || '').trim(),
  })));
  console.log('\n入口卡 ' + cards.length + ' 张:');
  cards.forEach(c => console.log('  <' + c.tag + '> ' + c.name + ' | ' + c.desc + ' | ' + c.href));
  if (cards.length !== 2) fails.push(`入口卡应恰好 2 张，实到 ${cards.length}`);
  const hrefs = cards.map(c => c.href).sort().join('|');
  if (hrefs !== '/study?qt=choose|/study?qt=judge') fails.push('入口卡链接不对: ' + hrefs);

  const box = await p.$eval('.qtype-card', e => {
    const r = e.getBoundingClientRect(); const cs = getComputedStyle(e);
    return { w: Math.round(r.width), h: Math.round(r.height), display: cs.display };
  });
  console.log('首卡盒模型:', JSON.stringify(box));
  if (box.display === 'none') fails.push('入口卡被隐藏');
  if (box.w < 100 || box.h < 50) fails.push('入口卡塌了: ' + box.w + 'x' + box.h);

  // ---------- 截图（明/暗）----------
  for (const scheme of ['light', 'dark']) {
    await p.emulateMedia({ colorScheme: scheme });
    await p.waitForTimeout(300);
    const out = path.join(OUT, 'study_after_game_removal_' + scheme + '.png');
    await p.screenshot({ path: out, fullPage: false });
    console.log('截图:', out);
  }
  await p.emulateMedia({ colorScheme: 'light' });

  // ---------- 两个题型页各自检查 .is-on ----------
  for (const qt of ['choose', 'judge']) {
    await p.goto(BASE + '/study?qt=' + qt, { waitUntil: 'load' });
    await p.waitForTimeout(500);
    const on = await p.$$eval('.qtype-card.is-on', e => e.map(x =>
      ((x.querySelector('.qtype-card-name') || {}).textContent || '').trim()));
    console.log(qt + ': .is-on = ' + JSON.stringify(on));
    if (on.length !== 1) fails.push(qt + ' 页 .is-on 应恰好 1 张，实到 ' + on.length);
  }

  // ---------- 游戏路由必须 404 ----------
  for (const u of ['/games', '/game', '/game/raw?key=x']) {
    const r = await p.goto(BASE + u, { waitUntil: 'load' }).catch(() => null);
    const code = r ? r.status() : 0;
    console.log(u + ' -> HTTP ' + code);
    if (code !== 404) fails.push(u + ' 应 404，实到 ' + code);
  }

  // ---------- style.css 里也不能再有游戏 token ----------
  const css = await (await ctx.request.get(BASE + '/static/style.css')).text();
  for (const t of ['gm-', 'is-wip', 'sb-game-wip', 'wip-modal']) {
    if (css.includes(t)) fails.push('服务出去的 style.css 仍含「' + t + '」');
  }
  console.log('style.css 线上长度:', css.length);

  // ---------- 判分链路：选择题点一个选项 ----------
  await p.goto(BASE + '/study?qt=choose', { waitUntil: 'load' });
  await p.waitForTimeout(600);
  const qtype = await p.evaluate(() => document.querySelector('.qtype-card.is-on .qtype-card-name').textContent.trim());
  console.log('当前题型:', qtype);
  const optSel = await p.evaluate(() => {
    for (const s of ['.opt', '.options button', '#opts button', '.option']) {
      const n = document.querySelectorAll(s);
      if (n.length) return { sel: s, n: n.length };
    }
    return null;
  });
  console.log('选项容器:', JSON.stringify(optSel));
  if (optSel && optSel.n > 0) {
    await p.click(optSel.sel);
    await p.waitForTimeout(400);
    console.log('点选后已判定（无 JS 报错即通过）');
  }

  if (pageErrs.length) fails.push('页面 JS 报错: ' + pageErrs.join('; '));

  await b.close();

  console.log('\n===== 验收结论 =====');
  if (fails.length === 0) console.log('全部通过 ✓');
  else { console.log('失败 ' + fails.length + ' 项:'); fails.forEach(f => console.log('  ✗ ' + f)); process.exit(1); }
})().catch(e => { console.error('脚本异常:', e); process.exit(2); });