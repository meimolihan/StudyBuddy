# -*- coding: utf-8 -*-
"""一年级互动游戏题的「增强层」代码（CSS + JS）。

设计原则（严格遵守用户约束）：
  * **不改题目数据**：不碰 const ALL / QUESTIONS / t/q/o/a/e 任何一个字段。
  * **不改判分逻辑**：不碰 choose() / checkCount() / checkAnswer() 等判分函数，
    也不改它们返回的 true/false。用「观察」的方式挂钩：
        - 选项点击  → 在捕获阶段监听 click，只做音效与按压动效，不阻止冒泡。
        - 正误反馈  → MutationObserver 盯 #fb / .fb / #feedbackBar 的 class，
                       识别出 ok / no 状态后播对应音效 + 播奖励/提示动画。
    这样即使将来引擎重写，增强层依然工作（它只认 DOM 约定）。
  * **音效全部用 Web Audio 现场合成**，不引入任何音频文件：
    游戏是离线静态 HTML（可直接双击打开），引外部 mp3 在 file:// 下会被
    CORS 拦掉，且要额外分发几十个文件。合成音零依赖、零体积、可调。

增强层是「幂等」的：脚本重复跑不会重复注入（靠下面的哨兵标记）。
"""
from __future__ import annotations

# ---------------------------------------------------------------- CSS
# 全部颜色走 var(--g-*, fallback)：游戏本体已经有 --g-* 变量体系，
# 而 game.go 的 gameThemeBridgeCSS 会按主题注入 light/dark 两套值。
# 我们只在没有 --g-* 时给 fallback（游戏被双击直接打开、不经站点时生效），
# 绝不在这里覆盖 --g-*，否则会把宿主页注入的主题覆盖掉。
ENHANCE_CSS = r"""
/* ============================================================
   sb-kids 一年级游戏增强层（背景 / 卡片 / 按钮 / 动画）
   ------------------------------------------------------------
   颜色策略：**只用 --g-* 变量的 fallback，不覆盖变量本身**。
   --g-* 由 game.go 的 gameThemeBridgeCSS 按主题注入（light/dark/auto），
   在这里写死颜色会把暗色主题顶掉。fallback 只在「双击 HTML 直开、
   没有任何主题桥」时生效，那时本来就没有暗色概念。
   ============================================================ */
.sbk{
  --sbk-blue:#4aa3ff;   --sbk-blue-s:#dbeeff;
  --sbk-yellow:#ffd23f; --sbk-yellow-s:#fff6d9;
  --sbk-orange:#ff9f45; --sbk-orange-s:#ffeedb;
  --sbk-green:#5ec26a;  --sbk-green-s:#e2f6e4;
  --sbk-pink:#ff8fb1;   --sbk-pink-s:#ffe6ee;
  --sbk-purple:#a98bff; --sbk-purple-s:#eee8ff;
  --sbk-ink:var(--g-ink,#1f2937);
  --sbk-line:var(--g-line,#e3e9f1);
  --sbk-card:var(--g-card,#fff);
  --sbk-brand:var(--g-brand,#2f6fd0);
  --sbk-ok:var(--g-ok,#2e9e5b);
  --sbk-bad:var(--g-bad,#d64545);
  /* 柔和但明亮：避免高饱和纯色大面积铺满（刺眼），
     用「白 + 低饱和彩色」的组合，色相集中在蓝/黄/橙/绿/粉五色。 */
  --sbk-sky-1:#eaf4ff; --sbk-sky-2:#fff8ec; --sbk-sky-3:#f2fbf3;
}

body.sbk-on{
  background:
    radial-gradient(1100px 460px at 8% -8%,  var(--sbk-blue-s) 0%, transparent 62%),
    radial-gradient(900px 420px at 96% 4%,   var(--sbk-yellow-s) 0%, transparent 60%),
    radial-gradient(820px 500px at 50% 108%, var(--sbk-pink-s) 0%, transparent 64%),
    linear-gradient(180deg, var(--sbk-sky-1) 0%, var(--sbk-sky-2) 46%, var(--sbk-sky-3) 100%) !important;
  background-attachment: fixed !important;
}

/* ---------- 卡通装饰层（云朵 / 星星 / 彩虹 / 气球 / 校园） ----------
   纯 CSS 绘制，零图片依赖（离线双击也能看）。
   全部 pointer-events:none，绝不挡住孩子的点击。 */
.sbk-deco{position:fixed; inset:0; pointer-events:none; z-index:0; overflow:hidden}
.sbk-deco i{position:absolute; display:block; font-style:normal; line-height:1;
  will-change:transform; user-select:none}

/* 云朵：三个圆球拼一朵，缓慢横移 */
.sbk-cl{width:0; height:0}
.sbk-cl::before,.sbk-cl::after{content:""; position:absolute; border-radius:50%;
  background:#fff; opacity:.82}
.sbk-cl::before{width:56px; height:56px; left:0; top:12px}
.sbk-cl::after{width:40px; height:40px; left:34px; top:2px;
  box-shadow:30px 22px 0 -2px #fff}
.sbk-cl i{position:absolute; left:52px; top:26px; width:46px; height:26px;
  border-radius:0 22px 22px 0; background:#fff; opacity:.82}

/* 星星：柔和闪烁，不刺眼（用饱和度较低的黄 + 半透明） */
.sbk-st{color:var(--sbk-yellow); font-size:22px; opacity:.75;
  text-shadow:0 0 10px rgba(255,210,63,.55)}
.sbk-st.s2{color:var(--sbk-orange); font-size:16px; opacity:.6}
.sbk-st.s3{color:var(--sbk-pink); font-size:18px; opacity:.55}

/* 气球：轻微上下浮动，线是伪元素 */
.sbk-ba{font-size:34px; animation:sbk-float 7s ease-in-out infinite}
.sbk-ba::after{content:""; position:absolute; left:50%; top:100%; width:1px;
  height:26px; background:rgba(120,130,150,.32); transform:translateX(-50%)}

/* 彩虹：七色弧，用 conic-gradient 的一环 */
.sbk-rb{width:190px; height:95px; overflow:hidden; border-radius:190px 190px 0 0;
  background:
    conic-gradient(from 270deg at 50% 100%,
      #ff8fb1 0 12deg, #ffd23f 12deg 24deg, #5ec26a 24deg 36deg,
      #4aa3ff 36deg 48deg, #a98bff 48deg 60deg, #ff9f45 60deg 72deg,
      transparent 72deg 360deg);
  opacity:.3}

/* 小动物 / 校园剪影：emoji，蹲在底部不抢视觉 */
.sbk-an{font-size:28px; opacity:.5; animation:sbk-bob 4.2s ease-in-out infinite}

/* 飘浮动画：三个元素用不同周期，避免整齐划一的机械感 */
@keyframes sbk-drift{from{transform:translateX(-14vw)}to{transform:translateX(114vw)}}
@keyframes sbk-drift-r{from{transform:translateX(114vw)}to{transform:translateX(-14vw)}}
@keyframes sbk-float{0%,100%{transform:translateY(0)}50%{transform:translateY(-13px)}}
@keyframes sbk-bob{0%,100%{transform:translateY(0) rotate(-2deg)}50%{transform:translateY(-7px) rotate(2deg)}}
@keyframes sbk-tw{0%,100%{opacity:.35; transform:scale(.9)}50%{opacity:.85; transform:scale(1.1)}}

/* ---------- 主体内容浮到装饰层之上 ---------- */
.sbk-on .wrap,.sbk-on .hud,.sbk-on .q,.sbk-on .fb,.sbk-on .opts,.sbk-on .stage,
.sbk-on .done,.sbk-on #gameContainer,.sbk-on .gb,.sbk-on [class*="bar"],
.sbk-on [class*="card"],.sbk-on [class*="panel"]{
  position:relative; z-index:1;
}
.sbk-on #gameContainer{max-width:820px; margin:0 auto}

/* ---------- 大卡片：更圆、更软、有厚度感（不用重投影，避免糊） ---------- */
.sbk-on .q, .sbk-on #gameContainer, .sbk-on .fb{
  border-radius:24px !important;
  border:2px solid var(--sbk-line) !important;
  box-shadow:0 6px 0 rgba(0,0,0,.05), 0 10px 26px rgba(80,110,160,.13) !important;
  background-color:var(--sbk-card) !important;
}

/* ---------- 大字号：题干与选项是低龄阅读的主体，必须够大 ---------- */
.sbk-on .q-title, .sbk-on #promptText{
  font-size:22px !important; line-height:1.65 !important; font-weight:800 !important;
  letter-spacing:.01em;
}
.sbk-on .q-sub, .sbk-on #scoreText, .sbk-on #levelBadge{font-size:15px !important}
.sbk-on .stage{min-height:126px}
.sbk-on .stage .big{font-size:76px}
.sbk-on .stage .py{font-size:40px}
.sbk-on .stage .shape{font-size:64px}
.sbk-on .fb{font-size:17px !important; font-weight:700 !important;
  border-radius:18px !important; padding:12px 16px !important}

/* ---------- 圆润大按钮 + 五色循环 ---------- */
/* 每个选项给一个色相（nth-child 轮转），孩子靠颜色也能定位选项，
   这对一年级认字不多的学生是很实在的辅助。 */
.sbk-on .opt, .sbk-on .optionsGrid button, .sbk-on .optbtn{
  min-height:62px !important;           /* 触屏热区：远高于 44px 下限 */
  border-radius:20px !important;
  border:3px solid transparent !important;
  font-size:19px !important; font-weight:800 !important;
  box-shadow:0 5px 0 var(--sbk-shadow,rgba(0,0,0,.10)) !important;
  transition:transform .14s cubic-bezier(.34,1.56,.64,1),
             box-shadow .14s, filter .2s !important;
  position:relative; overflow:hidden;
}
.sbk-on .opt:nth-child(5n+1),.sbk-on .optionsGrid button:nth-child(5n+1){
  background-color:var(--sbk-blue-s)!important; border-color:var(--sbk-blue)!important;
  --sbk-shadow:rgba(74,163,255,.34)}
.sbk-on .opt:nth-child(5n+2),.sbk-on .optionsGrid button:nth-child(5n+2){
  background-color:var(--sbk-yellow-s)!important; border-color:var(--sbk-yellow)!important;
  --sbk-shadow:rgba(255,210,63,.42)}
.sbk-on .opt:nth-child(5n+3),.sbk-on .optionsGrid button:nth-child(5n+3){
  background-color:var(--sbk-green-s)!important; border-color:var(--sbk-green)!important;
  --sbk-shadow:rgba(94,194,106,.34)}
.sbk-on .opt:nth-child(5n+4),.sbk-on .optionsGrid button:nth-child(5n+4){
  background-color:var(--sbk-orange-s)!important; border-color:var(--sbk-orange)!important;
  --sbk-shadow:rgba(255,159,69,.36)}
.sbk-on .opt:nth-child(5n+5),.sbk-on .optionsGrid button:nth-child(5n+5){
  background-color:var(--sbk-pink-s)!important; border-color:var(--sbk-pink)!important;
  --sbk-shadow:rgba(255,143,177,.36)}

/* 按下：往下压 + 影子缩短（物理直觉：按下去了） */
.sbk-on .opt.sbk-press, .sbk-on .optionsGrid button.sbk-press{
  transform:translateY(4px) scale(.96) !important;
  box-shadow:0 1px 0 var(--sbk-shadow,rgba(0,0,0,.10)) !important;
  filter:saturate(1.15) brightness(1.03);
}
/* 选项生成的气泡：click 时的扩散圆环 */
.sbk-bubble{
  position:absolute; border-radius:50%; pointer-events:none;
  width:14px; height:14px; margin:-7px 0 0 -7px;
  background:radial-gradient(circle,rgba(255,255,255,.95) 0%,rgba(255,255,255,.35) 55%,transparent 72%);
  animation:sbk-bub .52s ease-out forwards;
}
@keyframes sbk-bub{from{transform:scale(.4); opacity:.95} to{transform:scale(9); opacity:0}}

/* 正误态：只增强观感，不改类名（类名是判分信号，绝不能动） */
.sbk-on .opt.right, .sbk-on .opt.wrong{animation:none !important}   /* 让下面的 keyframes 接管 */
.sbk-on .opt.right, .sbk-on .opt.ok{
  background-color:var(--sbk-green-s)!important; border-color:var(--sbk-ok)!important;
  color:var(--sbk-ok)!important;
}
.sbk-on .opt.wrong, .sbk-on .opt.no{
  background-color:var(--sbk-orange-s)!important; border-color:var(--sbk-bad)!important;
  color:var(--sbk-bad)!important;
}
.sbk-on .fb.ok, .sbk-on #feedbackBar.ok{
  background-color:var(--sbk-green-s)!important; border-color:var(--sbk-ok)!important;
  color:var(--sbk-ok)!important}
.sbk-on .fb.no, .sbk-on #feedbackBar.no{
  background-color:var(--sbk-yellow-s)!important; border-color:var(--sbk-warn,#e08b00)!important;
  color:var(--sbk-warn,#e08b00)!important}
/* 答对：弹跳 + 发光（只作用在正确项上，用 sbk-right 标记，不改原类名） */
.sbk-on .sbk-right{animation:sbk-pop .62s cubic-bezier(.34,1.56,.64,1) 2}
@keyframes sbk-pop{
  0%{transform:scale(1)} 22%{transform:scale(1.13)}
  44%{transform:scale(.97)} 66%{transform:scale(1.05)} 100%{transform:scale(1)}
}
.sbk-on .sbk-right::after{
  content:""; position:absolute; inset:-4px; border-radius:inherit; pointer-events:none;
  box-shadow:0 0 0 3px var(--sbk-ok), 0 0 26px 6px rgba(94,194,106,.55);
  animation:sbk-glow 1.1s ease-in-out 2;
}
@keyframes sbk-glow{0%,100%{opacity:.28}50%{opacity:1}}

/* 答错：温和横向抖动（幅度小、次数少，不吓到孩子） */
.sbk-on .sbk-wrong{animation:sbk-shake .5s cubic-bezier(.36,.07,.19,.97) 1}
@keyframes sbk-shake{
  0%,100%{transform:translateX(0)}
  18%{transform:translateX(-6px)} 38%{transform:translateX(6px)}
  58%{transform:translateX(-4px)} 78%{transform:translateX(3px)}
}

/* ---------- 题目进入动画：弹跳淡入 ---------- */
.sbk-in{animation:sbk-in .52s cubic-bezier(.34,1.4,.64,1) both}
@keyframes sbk-in{
  from{opacity:0; transform:translateY(26px) scale(.94)}
  to{opacity:1; transform:none}
}
.sbk-in-opt{animation:sbk-in-opt .44s cubic-bezier(.34,1.5,.64,1) both}
@keyframes sbk-in-opt{
  from{opacity:0; transform:translateY(16px) scale(.9)}
  to{opacity:1; transform:none}
}

/* ---------- 答对奖励：星星 + 彩带 + 笑脸 + 点赞 ---------- */
.sbk-fx{position:fixed; inset:0; pointer-events:none; z-index:60; overflow:hidden}
.sbk-star{position:absolute; font-size:30px; line-height:1;
  animation:sbk-star .95s cubic-bezier(.3,.7,.4,1) forwards}
@keyframes sbk-star{
  0%{opacity:0; transform:translate(0,0) scale(.3) rotate(0)}
  18%{opacity:1; transform:translate(0,-16px) scale(1.25) rotate(18deg)}
  100%{opacity:0; transform:translate(var(--dx,40px),var(--dy,-150px)) scale(.55) rotate(220deg)}
}
.sbk-ribbon{position:absolute; width:11px; height:20px; border-radius:3px;
  animation:sbk-rib 1.05s ease-in forwards}
@keyframes sbk-rib{
  0%{opacity:0; transform:translate(0,0) rotate(0)}
  12%{opacity:1}
  100%{opacity:0; transform:translate(var(--dx,0),var(--dy,300px)) rotate(var(--rot,540deg))}
}
.sbk-cheer{position:fixed; left:50%; top:38%; z-index:61; pointer-events:none;
  transform:translate(-50%,-50%);
  animation:sbk-cheer 1.15s cubic-bezier(.34,1.5,.64,1) forwards}
.sbk-cheer .sbk-face{font-size:78px; line-height:1; animation:sbk-nod 1.15s ease-in-out}
.sbk-cheer .sbk-word{margin-top:4px; font-size:22px; font-weight:900; color:var(--sbk-ok);
  text-shadow:0 2px 0 #fff, 0 0 16px rgba(94,194,106,.5); text-align:center}
@keyframes sbk-cheer{
  0%{opacity:0; transform:translate(-50%,-50%) scale(.3) rotate(-16deg)}
  30%{opacity:1; transform:translate(-50%,-50%) scale(1.1) rotate(6deg)}
  45%{transform:translate(-50%,-50%) scale(1) rotate(-3deg)}
  100%{opacity:0; transform:translate(-50%,-62%) scale(.96)}
}
@keyframes sbk-nod{0%,100%{transform:rotate(0)}30%{transform:rotate(-9deg) scale(1.06)}
  60%{transform:rotate(7deg) scale(1.03)}}
/* 答错：温和的提示气泡（从选项旁冒出来，不遮挡题目） */
.sbk-hint{position:fixed; z-index:61; pointer-events:none; transform:translate(-50%,-100%);
  background:var(--sbk-yellow-s); color:var(--sbk-warn,#a86a00);
  border:2px solid var(--sbk-yellow); border-radius:16px;
  padding:8px 14px; font-size:16px; font-weight:800; white-space:nowrap;
  box-shadow:0 5px 0 rgba(0,0,0,.07);
  animation:sbk-hint 1.5s cubic-bezier(.34,1.4,.64,1) forwards}
@keyframes sbk-hint{
  0%{opacity:0; transform:translate(-50%,-84%) scale(.6)}
  16%{opacity:1; transform:translate(-50%,-100%) scale(1.06)}
  26%{transform:translate(-50%,-100%) scale(1)}
  80%{opacity:1; transform:translate(-50%,-100%) scale(1)}
  100%{opacity:0; transform:translate(-50%,-128%) scale(.9)}
}

/* ---------- 音效与音乐开关 ---------- */
.sbk-bar{position:fixed; right:10px; bottom:10px; z-index:70;
  display:flex; gap:8px; align-items:center}
.sbk-ico{
  width:52px; height:52px; border-radius:50%; border:2px solid var(--sbk-line);
  background:var(--sbk-card); color:var(--sbk-ink); cursor:pointer;
  font-size:23px; line-height:1; display:flex; align-items:center; justify-content:center;
  box-shadow:0 4px 0 rgba(0,0,0,.08); padding:0;
  transition:transform .14s cubic-bezier(.34,1.56,.64,1);
}
.sbk-ico:active{transform:translateY(3px) scale(.94)}
.sbk-ico:focus-visible{outline:3px solid var(--sbk-blue); outline-offset:2px}
.sbk-ico[aria-pressed="true"]{background:var(--sbk-blue-s); border-color:var(--sbk-blue)}
.sbk-ico.sbk-sound{position:relative}
.sbk-ico.sbk-off{opacity:.5; filter:grayscale(1)}

/* ---------- 结算页也放大 ---------- */
.sbk-on .done h2{font-size:30px !important}
.sbk-on .done .medal{font-size:84px !important;
  animation:sbk-bob 2.6s ease-in-out infinite; display:inline-block}
.sbk-on .btn, .sbk-on .resetBtn, .sbk-on #resetBtn{
  min-height:58px !important; border-radius:999px !important; font-size:20px !important;
  font-weight:900 !important; padding:14px 40px !important;
  background:var(--sbk-brand) !important; color:#fff !important;
  box-shadow:0 5px 0 rgba(0,0,0,.14) !important;
  transition:transform .14s cubic-bezier(.34,1.56,.64,1) !important;
}
.sbk-on .btn:active,.sbk-on #resetBtn:active{transform:translateY(4px) scale(.97) !important}

/* ---------- 三端适配：平板 / 手机 ---------- */
@media (max-width:760px){
  .sbk-on .q-title,.sbk-on #promptText{font-size:20px !important}
  .sbk-on .opt,.sbk-on .optionsGrid button{font-size:18px !important; min-height:60px !important}
  .sbk-on .stage .big{font-size:64px}
  .sbk-deco{opacity:.75}                 /* 小屏少一点装饰，避免抢注意力 */
}
@media (max-width:420px){
  .sbk-on .q-title,.sbk-on #promptText{font-size:19px !important}
  .sbk-on .opt,.sbk-on .optionsGrid button{
    min-height:60px !important; font-size:17px !important; border-radius:18px !important}
  .sbk-on .stage .big{font-size:54px}
  .sbk-on .stage .py{font-size:32px}
  .sbk-ico{width:48px; height:48px; font-size:21px}
  .sbk-bar{right:8px; bottom:8px}
}
/* 触屏：hover 会「粘住」，用 hover:hover 门控 */
@media (hover:none){
  .sbk-on .opt:active,.sbk-on .optionsGrid button:active{
    transform:translateY(4px) scale(.96) !important}
}
/* 无障碍：用户开了「减少动态效果」就全部关掉（游戏本体已有同类兜底） */
@media (prefers-reduced-motion:reduce){
  .sbk-deco{display:none !important}
  .sbk-in,.sbk-in-opt,.sbk-right,.sbk-wrong,.sbk-star,.sbk-ribbon,
  .sbk-cheer,.sbk-hint,.sbk-ba,.sbk-an,.sbk-st{animation:none !important}
  .sbk-in,.sbk-in-opt{opacity:1 !important; transform:none !important}
}
@media print{ .sbk-deco,.sbk-bar{display:none !important} }
"""

# ---------------------------------------------------------------- JS
ENHANCE_JS = r"""
/* ============================================================
   sb-kids 一年级游戏增强层（音效 / 动效 / 背景装饰）
   ------------------------------------------------------------
   ⚠ 本段**不修改任何判分逻辑**，只「观察」：
     · 选项点击：捕获阶段监听 click，只播音效 + 加按压类，**不 preventDefault、
       不 stopPropagation**，引擎的 choose() 照常执行。
     · 正误判定：MutationObserver 盯 #fb / .fb / #feedbackBar 的 class，
       识别出 ok / no 后播对应音效与奖励 / 提示动画。
     · 题目切换：盯 #title / #stage / #opts 的 childList 变化，播进入动画 + 提示音。
   引擎将来重写也不影响本层（它只认 DOM 约定）。
   ============================================================ */
(function () {
  "use strict";
  if (document.documentElement.getAttribute("data-sbk") === "1") { return; }  // 幂等
  document.documentElement.setAttribute("data-sbk", "1");

  var reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------------------------------------------------------
     1. Web Audio：全部音效现场合成，零文件依赖
     --------------------------------------------------------- */
  var AC = window.AudioContext || window.webkitAudioContext;
  var ac = null, master = null;
  var sndOn = true, bgmOn = false;      /* 音效默认开；BGM 默认关（有声环境下不擅自播） */
  var BGM_KEY = "sbk_sound";

  function audio() {
    if (!AC) { return null; }
    if (!ac) {
      try {
        ac = new AC();
        master = ac.createGain();
        master.gain.value = 0.5;
        master.connect(ac.destination);
      } catch (e) { ac = null; }
    }
    /* 浏览器自动播放策略：首次交互前 resume，合成音才响 */
    if (ac && ac.state === "suspended") { try { ac.resume(); } catch (e) {} }
    return ac;
  }
  function env(node, t0, a, d, peak) {
    var g = ac.createGain();
    g.gain.setValueAtTime(0.0001, t0);
    g.gain.exponentialRampToValueAtTime(peak, t0 + a);
    g.gain.exponentialRampToValueAtTime(0.0001, t0 + a + d);
    node.connect(g); g.connect(master);
    return g;
  }
  function tone(freq, t0, dur, type, peak) {
    var o = ac.createOscillator();
    o.type = type || "sine";
    o.frequency.setValueAtTime(freq, t0);
    env(o, t0, Math.min(0.02, dur * 0.25), dur, peak == null ? 0.3 : peak);
    o.start(t0); o.stop(t0 + dur + 0.06);
    return o;
  }
  /* 频率滑音（滑音本身就有"跳起来"的听感，比纯 beep 更活泼） */
  function slide(f0, f1, t0, dur, type, peak) {
    var o = ac.createOscillator();
    o.type = type || "triangle";
    o.frequency.setValueAtTime(f0, t0);
    o.frequency.exponentialRampToValueAtTime(f1, t0 + dur);
    env(o, t0, 0.012, dur, peak == null ? 0.26 : peak);
    o.start(t0); o.stop(t0 + dur + 0.06);
  }

  /* —— 五种音效 —— */
  var SFX = {
    /* 点击：短促清脆的「叮」，音高偏高（一年级对高频更敏感） */
    click: function (t) { tone(1180, t, 0.055, "sine", 0.16); tone(1760, t + 0.012, 0.05, "sine", 0.09); },
    /* 答对：C-E-G-C 上行大跳 + 高音，标准"答对"感 */
    right: function (t) {
      tone(523.25, t, 0.12, "triangle", 0.26);
      tone(659.25, t + 0.09, 0.12, "triangle", 0.26);
      tone(783.99, t + 0.18, 0.12, "triangle", 0.26);
      tone(1046.5, t + 0.27, 0.34, "sine", 0.3);
    },
    /* 答错：柔和的下行小三度，绝不用刺耳的蜂鸣（吓到孩子） */
    wrong: function (t) {
      tone(392, t, 0.14, "sine", 0.2);
      tone(311.13, t + 0.11, 0.24, "sine", 0.18);
    },
    /* 题目开始：两声上行邀请音 */
    start: function (t) { tone(659.25, t, 0.1, "sine", 0.2); tone(880, t + 0.1, 0.16, "sine", 0.22); },
    /* 结算：一串小乐句 */
    finish: function (t) {
      var f = [523.25, 659.25, 783.99, 1046.5];
      for (var i = 0; i < f.length; i++) { tone(f[i], t + i * 0.13, 0.2, "triangle", 0.26); }
    }
  };
  function play(name) {
    if (!sndOn || !SFX[name]) { return; }
    var a = audio(); if (!a) { return; }
    try { SFX[name](a.currentTime + 0.01); } catch (e) {}
  }

  /* —— 轻快背景音乐：16 步循环，音量压到 0.1 当背景 ——
     用 setInterval 调度（不用 AudioBufferSource，好处是能随时开关/变速）。 */
  var bgmTimer = null, bgmStep = 0;
  var BGM_SEQ = [
    /* C 大调五声音阶拨弦，节奏轻快不吵 */
    [523.25, 659.25, 783.99, 1046.5, 783.99, 659.25, 587.33, 0],
    [523.25, 659.25, 783.99, 1046.5, 880, 783.99, 659.25, 0]
  ];
  function bgmTick() {
    if (!bgmOn || !sndOn) { return; }
    var a = audio(); if (!a) { return; }
    try {
      var row = BGM_SEQ[bgmStep % BGM_SEQ.length];
      for (var i = 0; i < row.length; i++) {
        if (!row[i]) { continue; }
        var t = a.currentTime + i * 0.19;
        var o = a.createOscillator();
        o.type = "triangle";
        o.frequency.setValueAtTime(row[i], t);
        env(o, t, 0.02, 0.17, 0.075);      /* 音量刻意压低，确保人声/解析优先 */
        o.start(t); o.stop(t + 0.24);
      }
    } catch (e) {}
    bgmStep++;
  }
  function bgmStart() {
    if (bgmTimer) { return; }
    bgmTick();
    bgmTimer = setInterval(bgmTick, 1520);   /* 8 步 × 0.19s */
  }
  function bgmStop() { if (bgmTimer) { clearInterval(bgmTimer); bgmTimer = null; } }

  function loadPref() {
    try { var o = JSON.parse(localStorage.getItem(BGM_KEY) || "{}");
      if (typeof o.snd === "boolean") { sndOn = o.snd; }
      if (typeof o.bgm === "boolean") { bgmOn = o.bgm; }
    } catch (e) {}
  }
  function savePref() {
    try { localStorage.setItem(BGM_KEY, JSON.stringify({ snd: sndOn, bgm: bgmOn })); } catch (e) {}
  }

  /* ---------------------------------------------------------
     2. 卡通背景装饰层
     --------------------------------------------------------- */
  function deco() {
    document.body.classList.add("sbk-on", "sbk");
    var box = document.createElement("div");
    box.className = "sbk-deco";
    box.setAttribute("aria-hidden", "true");
    var html = [];
    /* 云朵 3 朵（左→右慢速） */
    for (var i = 0; i < 3; i++) {
      var top = 6 + i * 21, dur = 62 + i * 22, size = 0.8 + i * 0.28;
      html.push('<span class="sbk-cl" style="top:' + top + 'vh;width:0;height:0;'
        + 'animation:sbk-drift ' + dur + 's linear infinite;animation-delay:-' + (i * 17) + 's;'
        + 'transform:scale(' + size + ')"><i></i></span>');
    }
    /* 反向云 */
    html.push('<span class="sbk-cl" style="top:52vh;width:0;height:0;'
      + 'animation:sbk-drift-r 88s linear infinite;animation-delay:-31s;transform:scale(.7)"><i></i></span>');
    /* 星星：闪烁（各不同周期） */
    var stars = ["✨", "⭐", "🌟", "✨", "⭐", "🌟", "✨", "⭐"];
    for (var s = 0; s < stars.length; s++) {
      var L = 5 + (s * 13) % 88, T = 5 + (s * 19) % 78;
      html.push('<span class="sbk-st ' + (s % 3 === 0 ? "" : "s" + (s % 3 === 0 ? 2 : s % 3)) + '"'
        + ' style="left:' + L + '%;top:' + T + 'vh;'
        + 'animation:sbk-tw ' + (2.4 + s * 0.42) + 's ease-in-out infinite;'
        + 'animation-delay:-' + (s * 0.63) + 's">' + stars[s] + "</span>");
    }
    /* 彩虹：右上角静态，弱化不抢 */
    html.push('<span class="sbk-rb" style="position:absolute;top:8px;right:2%"></span>');
    /* 气球：底部两侧，上下浮动 */
    var bal = ["🎈", "🎈", "🎈", "🎈"];
    for (var bI = 0; bI < bal.length; bI++) {
      var bl = 4 + bI * 27, bd = 6.4 + bI * 1.3;
      html.push('<span class="sbk-ba" style="left:' + bl + '%;bottom:6vh;'
        + 'animation:sbk-float ' + bd + 's ease-in-out infinite;animation-delay:-' + (bI * 1.4) + 's">'
        + bal[bI] + "</span>");
    }
    /* 小动物 / 校园剪影：蹲底部，弱化 */
    var an = ["🐰", "🐻", "🐱", "🏫", "🌳", "🐥"];
    for (var aI = 0; aI < an.length; aI++) {
      var al = 2 + aI * 16.5;
      html.push('<span class="sbk-an" style="left:' + al + '%;bottom:1.5vh;'
        + 'animation:sbk-bob ' + (3.6 + aI * 0.5) + 's ease-in-out infinite;'
        + 'animation-delay:-' + (aI * 0.8) + 's">' + an[aI] + "</span>");
    }
    box.innerHTML = html.join("");
    document.body.appendChild(box);
  }

  /* ---------------------------------------------------------
     3. 特效：星星 / 彩带 / 笑脸 / 温和提示气泡
     --------------------------------------------------------- */
  function fx() {
    if (reduced) { return null; }
    var b = document.createElement("div");
    b.className = "sbk-fx";
    b.setAttribute("aria-hidden", "true");
    document.body.appendChild(b);
    return b;
  }
  function burstRight(host) {
    var box = fx();
    /* 彩带：从正确项位置向上撒五色纸片 */
    var R = host ? host.getBoundingClientRect() : { left: innerWidth / 2, top: innerHeight / 2, width: 0, height: 0 };
    if (box) {
      var cols = ["#ff8fb1", "#ffd23f", "#5ec26a", "#4aa3ff", "#a98bff", "#ff9f45"];
      for (var i = 0; i < 22; i++) {
        var rb = document.createElement("span");
        rb.className = "sbk-ribbon";
        rb.style.left = (R.left + R.width / 2) + "px";
        rb.style.top = (R.top + R.height / 2) + "px";
        rb.style.background = cols[i % cols.length];
        rb.style.setProperty("--dx", (Math.random() * 260 - 130) + "px");
        rb.style.setProperty("--dy", (180 + Math.random() * 200) + "px");
        rb.style.setProperty("--rot", (Math.random() * 900 - 450) + "deg");
        rb.style.animationDelay = (Math.random() * 0.16) + "s";
        box.appendChild(rb);
      }
      /* 星星：分两批从中心迸开 */
      for (var k = 0; k < 14; k++) {
        var st = document.createElement("span");
        st.className = "sbk-star";
        st.textContent = k % 3 === 0 ? "🌟" : (k % 3 === 1 ? "⭐" : "✨");
        st.style.left = (R.left + R.width / 2) + "px";
        st.style.top = (R.top + R.height / 2) + "px";
        st.style.setProperty("--dx", (Math.random() * 320 - 160) + "px");
        st.style.setProperty("--dy", -(90 + Math.random() * 200) + "px");
        st.style.animationDelay = (Math.random() * 0.22) + "s";
        st.style.fontSize = (20 + Math.random() * 16) + "px";
        box.appendChild(st);
      }
      setTimeout(function () { if (box.parentNode) { box.parentNode.removeChild(box); } }, 1900);
    }
    /* 笑脸 + 点赞：屏幕中央的独立层（不吃掉上面的事件） */
    var c = document.createElement("div");
    c.className = "sbk-cheer";
    c.setAttribute("aria-hidden", "true");
    var faces = ["😄", "🎉", "👏", "😃", "🌟"];
    var words = ["答对啦！", "太棒了！", "真厉害！", "好样的！", "满分哦！"];
    var idx = Math.floor(Math.random() * faces.length);
    c.innerHTML = '<div class="sbk-face">' + faces[idx] + "</div>"
                + '<div class="sbk-word">' + words[idx] + "</div>";
    document.body.appendChild(c);
    setTimeout(function () { if (c.parentNode) { c.parentNode.removeChild(c); } }, 1300);
  }
  function hintWrong(host) {
    if (reduced || !host) { return; }
    var r = host.getBoundingClientRect();
    var h = document.createElement("div");
    h.className = "sbk-hint";
    h.setAttribute("aria-hidden", "true");
    h.textContent = ["再想一想～", "差一点点！", "看看题目哦", "不着急，再试试"][Math.floor(Math.random() * 4)];
    h.style.left = Math.max(80, Math.min(innerWidth - 80, r.left + r.width / 2)) + "px";
    h.style.top = Math.max(70, r.top - 6) + "px";
    document.body.appendChild(h);
    setTimeout(function () { if (h.parentNode) { h.parentNode.removeChild(h); } }, 1650);
  }

  /* ---------------------------------------------------------
     4. 题目进入动画 + 开始提示音
     --------------------------------------------------------- */
  var seenQ = "";                 /* 记住当前题干，避免同一题反复播提示音 */
  function animIn(node, cls, delay) {
    if (!node || reduced) { return; }
    node.classList.remove(cls);
    /* 强制 reflow 让动画能重放（同 class 连续加不会重新触发动画） */
    void node.offsetWidth;
    node.style.animationDelay = (delay || 0) + "s";
    node.classList.add(cls);
  }
  function questionIn() {
    var q = document.getElementById("q") || document.getElementById("gameContainer")
         || document.querySelector(".q") || document.querySelector(".wrap");
    animIn(q, "sbk-in", 0);
    var opts = document.querySelectorAll("#opts .opt, .optionsGrid button, .opt");
    for (var i = 0; i < opts.length; i++) { animIn(opts[i], "sbk-in-opt", 0.06 + i * 0.07); }
  }
  function maybeStartTone() {
    var t = document.getElementById("title") || document.getElementById("promptText");
    var key = t ? (t.textContent || "").trim() : "";
    if (!key) { return; }
    if (key !== seenQ) { seenQ = key; play("start"); }
  }

  /* ---------------------------------------------------------
     5. 挂钩：全部在「观察」，不干预判分
     --------------------------------------------------------- */
  function isOpt(b) {
    if (!b || b.nodeType !== 1) { return false; }
    if (b.classList && (b.classList.contains("opt") || b.classList.contains("optbtn"))) { return true; }
    var p = b.closest ? b.closest(".opt,.optbtn") : null;
    if (p) { return true; }
    /* optionsGrid 这类异类结构：按钮且在选项容器里 */
    var og = b.closest ? b.closest("#optionsGrid,.optionsGrid,.opts") : null;
    return !!(og && og.tagName !== "BODY" && b.tagName === "BUTTON");
  }
  function bubble(b) {
    if (reduced || !b) { return; }
    var r = b.getBoundingClientRect();
    var e = document.createElement("span");
    e.className = "sbk-bubble";
    e.style.left = (r.left + r.width / 2) + "px";
    e.style.top = (r.top + r.height / 2) + "px";
    document.body.appendChild(e);
    setTimeout(function () { if (e.parentNode) { e.parentNode.removeChild(e); } }, 560);
  }

  /* 5a. 选项点击：捕获阶段，只加动效与音效，不阻断引擎 */
  document.addEventListener("click", function (ev) {
    var t = ev.target;
    /* 音效/音乐开关自己不播点击音（否则会自我循环） */
    if (t && t.closest && t.closest(".sbk-bar")) { return; }
    if (!isOpt(t)) { return; }
    var b = t.closest ? (t.closest(".opt,.optbtn") || t) : t;
    play("click");
    bubble(b);
    b.classList.add("sbk-press");
    setTimeout(function () { b.classList.remove("sbk-press"); }, 180);
  }, true);
  /* pointerdown 也要有按压感：click 在触摸端有 300ms 延迟，
     立刻按压更跟手。仍然只改 class，不阻止任何事。 */
  document.addEventListener("pointerdown", function (ev) {
    if (reduced || !isOpt(ev.target)) { return; }
    var b = ev.target.closest ? (ev.target.closest(".opt,.optbtn") || ev.target) : ev.target;
    if (b && b.classList) { b.classList.add("sbk-press"); }
  }, true);

  /* 5b. 正误反馈：盯 class 变化，识别 ok / no */
  var lastFb = "";
  function feedback() {
    var fb = document.getElementById("fb") || document.querySelector(".fb")
          || document.getElementById("feedbackBar") || document.querySelector("#feedbackBar,.feedback");
    if (!fb) { return; }
    var cl = fb.className || "";
    var ok = /(^|\s)(ok|right|correct)(\s|$)/.test(cl);
    var no = /(^|\s)(no|wrong|bad)(\s|$)/.test(cl);
    var st = ok ? "ok" : (no ? "no" : "");
    if (!st || st === lastFb) { return; }
    lastFb = st;
    if (st === "ok") {
      play("right");
      var good = document.querySelector(".opt.right,.opt.ok,#optionsGrid .right,#optionsGrid .ok")
              || document.querySelector(".opt:not(.dim)");
      if (good) {
        good.classList.remove("sbk-right");
        void good.offsetWidth;
        good.classList.add("sbk-right");
        setTimeout(function () { good.classList.remove("sbk-right"); }, 1500);
      }
      burstRight(good);
    } else {
      play("wrong");
      var bad = document.querySelector(".opt.wrong,.opt.no,#optionsGrid .wrong,#optionsGrid .no");
      if (bad) {
        bad.classList.remove("sbk-wrong");
        void bad.offsetWidth;
        bad.classList.add("sbk-wrong");
        setTimeout(function () { bad.classList.remove("sbk-wrong"); }, 700);
        hintWrong(bad);
      }
    }
  }

  /* 5c. 题目切换：选项容器内容变化 = 换题了 */
  function watchQuestion() {
    var opts = document.getElementById("opts") || document.querySelector(".opts")
            || document.getElementById("optionsGrid") || document.querySelector(".optionsGrid");
    if (opts && window.MutationObserver) {
      new MutationObserver(function () {
        /* 延一帧：等 innerHTML 全部替换完 */
        setTimeout(function () { questionIn(); maybeStartTone(); }, 30);
      }).observe(opts, { childList: true, subtree: true });
    }
    var t = document.getElementById("title") || document.getElementById("promptText");
    if (t && window.MutationObserver) {
      new MutationObserver(function () { setTimeout(questionIn, 20); })
        .observe(t, { childList: true, characterData: true, subtree: true });
    }
    if (document.body && window.MutationObserver) {
      new MutationObserver(function () { setTimeout(feedback, 20); })
        .observe(document.body, { subtree: true, attributes: true, attributeFilter: ["class"] });
    }
  }

  /* ---------------------------------------------------------
     6. 音效 / 音乐开关（浮动两个圆钮）
     --------------------------------------------------------- */
  function switchBar() {
    var bar = document.createElement("div");
    bar.className = "sbk-bar";
    var snd = document.createElement("button");
    snd.type = "button"; snd.className = "sbk-ico sbk-sound";
    snd.title = "音效开关";
    snd.setAttribute("aria-label", "音效开关");
    snd.setAttribute("aria-pressed", sndOn ? "true" : "false");
    var bgm = document.createElement("button");
    bgm.type = "button"; bgm.className = "sbk-ico";
    bgm.title = "背景音乐开关";
    bgm.setAttribute("aria-label", "背景音乐开关");
    bgm.setAttribute("aria-pressed", bgmOn ? "true" : "false");
    function paint() {
      snd.textContent = sndOn ? "🔊" : "🔇";
      snd.classList.toggle("sbk-off", !sndOn);
      snd.setAttribute("aria-pressed", sndOn ? "true" : "false");
      bgm.textContent = bgmOn ? "🎵" : "🎶";
      bgm.classList.toggle("sbk-off", !bgmOn);
      bgm.setAttribute("aria-pressed", bgmOn ? "true" : "false");
    }
    snd.addEventListener("click", function (e) {
      e.stopPropagation();
      sndOn = !sndOn;
      if (!sndOn) { bgmStop(); }         /* 关音效必然连带停 BGM，否则静音播放更怪 */
      else { var a = audio(); if (a) { try { SFX.click(a.currentTime + 0.01); } catch (er) {} } }
      savePref(); paint();
    });
    bgm.addEventListener("click", function (e) {
      e.stopPropagation();
      bgmOn = !bgmOn;
      if (bgmOn) { bgmStart(); var a = audio();
        if (a) { try { SFX.start(a.currentTime + 0.01); } catch (er) {} } }
      else { bgmStop(); }
      savePref(); paint();
    });
    bar.appendChild(snd); bar.appendChild(bgm);
    document.body.appendChild(bar);
    paint();
  }

  /* ---------------------------------------------------------
     7. 启动
     --------------------------------------------------------- */
  function boot() {
    loadPref();
    deco();
    switchBar();
    watchQuestion();
    questionIn();
    setTimeout(maybeStartTone, 260);
    /* 首次任意点击 = 解锁音频上下文（浏览器自动播放策略） */
    var once = function () {
      var a = audio();
      if (a) { try { a.resume(); } catch (e) {} }
      if (bgmOn) { bgmStart(); }
      document.removeEventListener("pointerdown", once);
      document.removeEventListener("click", once);
    };
    document.addEventListener("pointerdown", once);
    document.addEventListener("click", once);
    /* 结算页：把「再玩一次 / 重来」换成本层配色（它们的类名各游戏不同，
       用语义类兜底，见 CSS 里的 .btn / .resetBtn / #resetBtn） */
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else { boot(); }
})();
"""
