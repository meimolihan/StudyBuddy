# -*- coding: utf-8 -*-
"""二年级互动习题页 · Premium 视觉增强层（本体）。

设计目标（用户 2026-10-05 明确要求）
----------------------------------------
1. 画风：**轻 3D 软拟物 + 柔和渐变**，莫兰迪明亮色系，低饱和、干净通透、不刺眼。
   几何圆角卡片 + 精致微妙阴影 + 柔光层，**摒弃廉价卡通贴纸**（无云朵/彩虹/小动物/气球）。
2. 背景：动态简约场景。缓慢漂浮的几何图形 + 淡淡粒子流光 + 浅景深。
   全部**低对比、低饱和、慢速**，不抢题目焦点、不遮挡题干与选项。
3. 排版：层次分明。题干字号大而清晰；选项为精致圆角卡片，
   带微妙渐变与柔和外发光，**明暗双模式**。

动效规范
----------------------------------------
- 卡片入场：淡入 + 轻微上浮，0.25s ease。
- 选项交互：hover 轻微抬升 + 阴影放大；点击细腻压缩回弹（**不做夸张弹跳**）。
- 答对：优雅粒子星芒迸发 + 柔和金色流光扩散 + 勾选标记放大；**总时长 0.8s 自动淡出**，
  不阻塞答题。
- 答错：小幅弹性抖动（**阻尼感，不剧烈震动**）+ 柔和红色光晕，**无惊吓效果**。
- 页面切换：题目间平滑淡入淡出；背景粒子持续轻柔运动。

音频规范
----------------------------------------
- Web Audio **高质量干净合成音色**，无嘈杂刺耳声：
  点击 = 轻脆提示音；答对 = 明亮通透奖励音；答错 = 低沉温和提示音。
- 可选轻柔环境 BGM（轻音乐/钢琴感），**BGM 开关按钮**，音量可控、默认适中。

架构约束（与项目既有约定一致）
----------------------------------------
- **纯外挂式**：只在 </head> 前插 <style>、</body> 前插 <script>，**业务代码一行不改**。
- 点击用**捕获阶段**监听，只加 class 与播音效，**不 preventDefault / 不 stopPropagation**。
- 正误判定靠 `MutationObserver` 观察 `.q` 的 `correct` / `wrong` class（判分信号，绝不篡改）。
- 颜色：**硬编码浅/深底的元素，文字色必须同源硬编码**，绝不引用随主题翻转的
  `--g-*`（这正是 2026-10-05 早前「文字在暗色下隐形 1:1」事故的根因，见记忆 MEMORY.md）。
- 动效**绝不以 opacity 为唯一可见性载体**：keyframes 里不碰 opacity，纯 transform + filter。
"""
from __future__ import annotations

# ============================================================== CSS
ENHANCE_CSS = r"""
<style id="__SBK2_CSS__">
/* ============================================================
   sbk2 · 二年级 Premium 视觉增强层
   ------------------------------------------------------------
   色彩策略：全部走自有令牌 --p-*，不覆盖宿主的 --g-* / --ink 等。
   两套令牌用 A/B 双写：明色 + 暗色（@media prefers-color-scheme 与
   [data-theme="dark"] 各一份），保证明暗双模式都精致。

   ⚠️ 铁律：凡是**硬编码底色**的元素（选项卡、徽章、提示条），
   文字色必须**同源硬编码**（--p-*-ink），绝不引用随主题翻转的
   --g-ink / var(--ink)。否则暗色下浅字配浅底 = 对比度 1:1 隐形。
   ============================================================ */
.sbk2{
  /* ---- 莫兰迪色板：低饱和、明亮、干净 ---- */
  --p-blue:#8fa9c4;    --p-blue-d:#6d87a4;    --p-blue-s:#e4ebf2;   --p-blue-ink:#33465c;
  --p-rose:#c9a3a8;    --p-rose-d:#ab858b;    --p-rose-s:#f3e7e9;   --p-rose-ink:#5c3f44;
  --p-sage:#9fb8a4;    --p-sage-d:#7e9885;    --p-sage-s:#e6eee8;   --p-sage-ink:#3a4d41;
  --p-sand:#cdb999;    --p-sand-d:#ab9778;    --p-sand-s:#f2ebdd;   --p-sand-ink:#544733;
  --p-lilac:#a9a3c4;   --p-lilac-d:#8b85a8;   --p-lilac-s:#eae7f3;  --p-lilac-ink:#423d5c;
  --p-clay:#c4a68f;    --p-clay-d:#a48872;    --p-clay-s:#f0e7de;   --p-clay-ink:#584134;

  --p-ok:#7aa88a;       --p-ok-ink:#2c4a38;    --p-ok-s:#e2efe6;
  --p-bad:#c48b8b;     --p-bad-ink:#5c3232;   --p-bad-s:#f4e4e4;
  --p-gold:#d4b483;    --p-gold-ink:#5f4a22;  --p-gold-s:#f5ecd9;

  /* 背景层（低饱和、极浅，绝不抢焦点） */
  --p-bg-1:#eef1f5;  --p-bg-2:#f2eef2;  --p-bg-3:#eaf0ef;
  /* 不透明基底：见 .sbk2-bg 注释，必须先于渐变铺底 */
  --p-base:#f4f6f9;
  --p-shape:rgba(143,169,196,.13);
  --p-shape-2:rgba(201,163,168,.11);
  --p-shape-3:rgba(159,184,164,.11);
  --p-spark:rgba(212,180,131,.30);

  /* 表面与阴影：软拟物的关键 */
  --p-card:#ffffff;
  --p-card-2:#fbfcfd;
  --p-line:rgba(120,140,160,.16);
  --p-shadow-s:0 1px 2px rgba(70,90,110,.05), 0 2px 8px rgba(70,90,110,.05);
  --p-shadow-m:0 2px 4px rgba(70,90,110,.05), 0 6px 18px rgba(70,90,110,.08);
  --p-shadow-l:0 4px 8px rgba(70,90,110,.06), 0 14px 38px rgba(70,90,110,.12);
  --p-glow:0 0 0 1px rgba(255,255,255,.7) inset, 0 0 22px rgba(143,169,196,.16);
  --p-txt:#2f3e4c;  --p-txt-2:#5c6b7a;  --p-txt-3:#8494a3;

  /* 动效参数：统一时长曲线，避免节奏杂乱 */
  --p-e-out:cubic-bezier(.22,.68,.32,1);
  --p-e-soft:cubic-bezier(.34,.9,.36,1);
  --p-e-back:cubic-bezier(.34,1.3,.5,1);
  --p-d:.25s;  --p-d-s:.18s;  --p-d-l:.5s;
}
/* ⚠️⚠️⚠️ 选择器必须写成 `html.sbk2[...]`（同一个元素），**不能**写
   `html[...] .sbk2`（后代）。`sbk2` 这个 class 是加在 <html> 上的，
   写成后代选择器就要求 .sbk2 是 html 的**子元素** —— 永不命中，
   于是暗色令牌整套失效、页面永远只显示亮色那一套。
   这个 bug 让明暗两个主题截图几乎一模一样，靠读代码完全看不出来，
   是靠「双主题截图肉眼比对」抓到的。 */
@media (prefers-color-scheme: dark){
  html.sbk2:not([data-theme="light"]){
    --p-blue-s:#24313d;   --p-blue-ink:#d3e0ee;  --p-blue-d:#8aa4c0;
    --p-rose-s:#332a2c;   --p-rose-ink:#e7d4d7;  --p-rose-d:#c4a0a6;
    --p-sage-s:#26302a;   --p-sage-ink:#d5e3d9;  --p-sage-d:#93ac9a;
    --p-sand-s:#332e26;   --p-sand-ink:#e6d9c0;  --p-sand-d:#c3ae8c;
    --p-lilac-s:#2a2733;  --p-lilac-ink:#dcd7ea; --p-lilac-d:#a29bbf;
    --p-clay-s:#302823;   --p-clay-ink:#e3d2c2;  --p-clay-d:#bfa48a;
    --p-ok-s:#24312a;     --p-ok-ink:#cfe3d6;    --p-bad-s:#332526;    --p-bad-ink:#eccfcf;
    --p-gold-s:#332d20;   --p-gold-ink:#ecd9b3;
    --p-bg-1:#151b22;  --p-bg-2:#1a1a22;  --p-bg-3:#151f1e;
    --p-base:#121820;
    --p-shape:rgba(143,169,196,.10);
    --p-shape-2:rgba(201,163,168,.085);
    --p-shape-3:rgba(159,184,164,.085);
    --p-spark:rgba(212,180,131,.24);
    --p-card:#1c242e;  --p-card-2:#202833;
    --p-line:rgba(150,170,190,.16);
    --p-shadow-s:0 1px 2px rgba(0,0,0,.22), 0 2px 8px rgba(0,0,0,.18);
    --p-shadow-m:0 2px 4px rgba(0,0,0,.24), 0 6px 18px rgba(0,0,0,.24);
    --p-shadow-l:0 4px 8px rgba(0,0,0,.26), 0 14px 38px rgba(0,0,0,.32);
    --p-glow:0 0 0 1px rgba(255,255,255,.05) inset, 0 0 26px rgba(143,169,196,.14);
    --p-txt:#e4ebf2;  --p-txt-2:#a9b8c6;  --p-txt-3:#7b8b9a;
  }
}
html.sbk2[data-theme="dark"]{
  --p-blue-s:#24313d;   --p-blue-ink:#d3e0ee;  --p-blue-d:#8aa4c0;
  --p-rose-s:#332a2c;   --p-rose-ink:#e7d4d7;  --p-rose-d:#c4a0a6;
  --p-sage-s:#26302a;   --p-sage-ink:#d5e3d9;  --p-sage-d:#93ac9a;
  --p-sand-s:#332e26;   --p-sand-ink:#e6d9c0;  --p-sand-d:#c3ae8c;
  --p-lilac-s:#2a2733;  --p-lilac-ink:#dcd7ea; --p-lilac-d:#a29bbf;
  --p-clay-s:#302823;   --p-clay-ink:#e3d2c2;  --p-clay-d:#bfa48a;
  --p-ok-s:#24312a;     --p-ok-ink:#cfe3d6;    --p-bad-s:#332526;    --p-bad-ink:#eccfcf;
  --p-gold-s:#332d20;   --p-gold-ink:#ecd9b3;
  --p-bg-1:#151b22;  --p-bg-2:#1a1a22;  --p-bg-3:#151f1e;
  --p-base:#121820;
  --p-shape:rgba(143,169,196,.10);
  --p-shape-2:rgba(201,163,168,.085);
  --p-shape-3:rgba(159,184,164,.085);
  --p-spark:rgba(212,180,131,.24);
  --p-card:#1c242e;  --p-card-2:#202833;
  --p-line:rgba(150,170,190,.16);
  --p-shadow-s:0 1px 2px rgba(0,0,0,.22), 0 2px 8px rgba(0,0,0,.18);
  --p-shadow-m:0 2px 4px rgba(0,0,0,.24), 0 6px 18px rgba(0,0,0,.24);
  --p-shadow-l:0 4px 8px rgba(0,0,0,.26), 0 14px 38px rgba(0,0,0,.32);
  --p-glow:0 0 0 1px rgba(255,255,255,.05) inset, 0 0 26px rgba(143,169,196,.14);
  --p-txt:#e4ebf2;  --p-txt-2:#a9b8c6;  --p-txt-3:#7b8b9a;
}

/* ---------- 背景：柔和渐变 + 几何漂浮 + 粒子流光 ---------- */
/* ⚠️ 渐变各色标都以 transparent 收尾，会**透出 body 自身的底色**。
   题库自带 `body{background:var(--bg)}`，而 --bg 只在题库的
   `@media (prefers-color-scheme:dark)` 里被重定义 —— 一旦用户切到亮色、
   系统又是深色（或反之），body 就会露出与主题不符的底色，
   表现为「亮色主题下背景一片深黑」。所以这里必须先铺一层不透明基底。 */
.sbk2-bg{position:fixed; inset:0; z-index:0; pointer-events:none; overflow:hidden;
  background:
    radial-gradient(1200px 620px at 12% -10%, var(--p-bg-1) 0%, transparent 62%),
    radial-gradient(1000px 560px at 92% 6%, var(--p-bg-2) 0%, transparent 60%),
    radial-gradient(900px 620px at 52% 112%, var(--p-bg-3) 0%, transparent 64%),
    var(--p-base);
}
.sbk2-bg::after{content:""; position:absolute; inset:0;
  background:radial-gradient(ellipse at 50% 42%, transparent 38%, rgba(80,95,110,.05) 100%);}
/* 几何图形：低饱和、大尺寸、慢速漂移。blur 制造浅景深 */
.sbk2-sh{position:absolute; border-radius:50%; filter:blur(14px);
  will-change:transform; animation:sbk2-drift 34s var(--p-e-soft) infinite alternate;}
.sbk2-sh.r1{width:210px;height:210px;background:var(--p-shape);
  left:-40px;top:6vh;animation-duration:38s}
.sbk2-sh.r2{width:150px;height:150px;background:var(--p-shape-2);
  right:6vw;top:14vh;border-radius:44% 56% 62% 38%/48% 38% 62% 52%;animation-duration:44s}
.sbk2-sh.r3{width:250px;height:250px;background:var(--p-shape-3);
  right:14vw;bottom:-60px;border-radius:58% 42% 34% 66%/44% 56% 44% 56%;animation-duration:52s}
.sbk2-sh.r4{width:120px;height:120px;background:var(--p-shape);
  left:16vw;bottom:8vh;border-radius:40% 60% 52% 48%/56% 40% 60% 44%;animation-duration:41s}
.sbk2-sh.r5{width:170px;height:170px;background:var(--p-shape-2);
  left:52vw;top:-30px;filter:blur(20px);animation-duration:47s}
@keyframes sbk2-drift{
  0%{transform:translate3d(0,0,0) rotate(0deg) scale(1)}
  50%{transform:translate3d(18px,-26px,0) rotate(14deg) scale(1.06)}
  100%{transform:translate3d(-14px,18px,0) rotate(-10deg) scale(.97)}
}
/* 粒子流光：小点 + 缓慢上浮 + 呼吸式明灭 */
.sbk2-sp{position:absolute; width:4px;height:4px;border-radius:50%;
  background:var(--p-spark); will-change:transform,opacity;
  animation:sbk2-rise linear infinite;}
@keyframes sbk2-rise{
  0%{transform:translate3d(0,0,0) scale(.6); opacity:0}
  12%{opacity:.85}
  78%{opacity:.5}
  100%{transform:translate3d(14px,-118vh,0) scale(1.15); opacity:0}
}

/* ---------- 主体内容浮到背景之上 ---------- */
.sbk2 .wrap{position:relative; z-index:1;}

/* ---------- 顶部标题区：轻 3D 软拟物 ---------- */
.sbk2 .head{
  background:linear-gradient(145deg, var(--p-card) 0%, var(--p-card-2) 100%) !important;
  border:1px solid var(--p-line) !important;
  border-radius:22px !important;
  box-shadow:var(--p-shadow-m) !important;
  padding:22px 24px !important;
  color:var(--p-txt) !important;
  position:relative; overflow:hidden;
  transition:box-shadow var(--p-d) var(--p-e-soft), transform var(--p-d) var(--p-e-out);
}
.sbk2 .head::before{content:""; position:absolute; inset:0 0 auto; height:52%;
  background:linear-gradient(180deg, rgba(255,255,255,.5), transparent);
  pointer-events:none;}
@media (prefers-color-scheme: dark){
  html.sbk2:not([data-theme="light"]) .head::before{background:linear-gradient(180deg, rgba(255,255,255,.045), transparent)}
}
html.sbk2[data-theme="dark"] .head::before{background:linear-gradient(180deg, rgba(255,255,255,.045), transparent)}
.sbk2 .head h1{
  color:var(--p-txt) !important; font-size:23px !important; font-weight:800 !important;
  letter-spacing:.2px; text-shadow:none !important;}
.sbk2 .head .sub{color:var(--p-txt-2) !important; font-size:14.5px !important}

/* 元信息小卡：柔和描边 + 内发光 */
.sbk2 .head .meta .box{
  background:var(--p-card) !important; color:var(--p-txt-2) !important;
  border:1px solid var(--p-line) !important;
  border-radius:12px !important; padding:7px 14px !important;
  box-shadow:var(--p-shadow-s) !important;
}
.sbk2 .head .meta .box b{color:var(--p-txt) !important; font-weight:800}
.sbk2 .head .bank{background:transparent !important; color:var(--p-txt-3) !important;
  border:0 !important; padding:10px 2px 0 !important; font-size:13px !important}
.sbk2 .head .tip{
  background:var(--p-sand-s) !important; color:var(--p-sand-ink) !important;
  border-left:3px solid var(--p-sand) !important;
  border-radius:12px !important; padding:11px 15px !important;
  box-shadow:var(--p-shadow-s) !important; font-size:13.5px !important}

/* ---------- 题目卡片：入场淡入 + 轻微上浮 ---------- */
.sbk2 .q{
  background:linear-gradient(150deg, var(--p-card) 0%, var(--p-card-2) 100%) !important;
  border:1px solid var(--p-line) !important;
  border-radius:20px !important;
  box-shadow:var(--p-shadow-s) !important;
  padding:22px 24px !important; margin-top:18px !important;
  color:var(--p-txt) !important;
  transition:box-shadow var(--p-d) var(--p-e-soft),
             border-color var(--p-d) var(--p-e-soft),
             transform var(--p-d) var(--p-e-out);
  will-change:transform,opacity;
}
.sbk2 .q:hover{box-shadow:var(--p-shadow-m) !important}
/* 入场：淡入 + 上浮 0.25s ease。keyframes 不碰 opacity 的问题——
   本层 opacity 由元素自身承载，动画只动 transform/filter，
   即使动画被系统禁用或时钟卡死，内容也永远可见。 */
.sbk2 .q.sbk2-in{animation:sbk2-qin .25s ease-out backwards}
@keyframes sbk2-qin{
  from{transform:translateY(10px) scale(.994)}
  to{transform:none}
}

/* 题型徽章 */
.sbk2 .badge{
  background:var(--p-blue-s) !important; color:var(--p-blue-ink) !important;
  border-radius:9px !important; padding:3px 11px !important;
  font-size:12px !important; font-weight:800 !important; letter-spacing:.2px;
}
.sbk2 .badge.m{background:var(--p-lilac-s) !important; color:var(--p-lilac-ink) !important}
.sbk2 .qno{color:var(--p-txt-2) !important; font-weight:700 !important; font-size:13.5px !important}
/* 题干：字号大而清晰 —— 二年级重点 */
.sbk2 .stem{
  color:var(--p-txt) !important; font-size:18.5px !important; font-weight:700 !important;
  line-height:1.72 !important; margin:10px 0 16px !important; letter-spacing:.2px;
}

/* ---------- 选项：精致圆角交互卡片 ---------- */
.sbk2 .opt{
  background:linear-gradient(150deg, var(--p-card) 0%, var(--p-card-2) 100%) !important;
  border:1px solid var(--p-line) !important;
  border-radius:16px !important;
  padding:13px 16px !important; margin:10px 0 !important;
  box-shadow:var(--p-shadow-s) !important;
  color:var(--p-txt) !important; font-size:16px !important; font-weight:700 !important;
  /* 触屏热区 ≥44px（规范要求）：min-height 锁死，padding 配合 */
  min-height:52px !important;
  position:relative; overflow:hidden; isolation:isolate;
  transition:transform var(--p-d-s) var(--p-e-out),
             box-shadow var(--p-d-s) var(--p-e-soft),
             border-color var(--p-d-s) var(--p-e-soft),
             background-color var(--p-d-s) var(--p-e-soft);
  will-change:transform;
}
/* 顶部柔光层：软拟物的「受光面」 */
.sbk2 .opt::before{content:""; position:absolute; inset:0 0 auto; height:52%;
  background:linear-gradient(180deg, rgba(255,255,255,.42), transparent);
  pointer-events:none; z-index:-1;}
@media (prefers-color-scheme: dark){
  html.sbk2:not([data-theme="light"]) .opt::before{background:linear-gradient(180deg, rgba(255,255,255,.035), transparent)}
}
html.sbk2[data-theme="dark"] .opt::before{background:linear-gradient(180deg, rgba(255,255,255,.035), transparent)}
/* 悬浮：轻微抬升 + 阴影放大（克制，不夸张） */
.sbk2 .opt:hover{
  transform:translateY(-2px);
  box-shadow:var(--p-shadow-m) !important;
  border-color:var(--p-blue) !important;
}
/* 选中态 */
.sbk2 .opt.sel{
  background:linear-gradient(150deg, var(--p-blue-s), var(--p-card-2)) !important;
  border-color:var(--p-blue-d) !important;
  box-shadow:var(--p-shadow-m), 0 0 0 3px rgba(143,169,196,.20) !important;
  transform:translateY(-1px);
}
/* 按下：细腻压缩回弹（弹簧曲线，不用夸张弹跳） */
.sbk2 .opt.sbk2-press{
  transform:translateY(1px) scale(.978);
  box-shadow:var(--p-shadow-s) !important;
  transition-duration:.08s;
}
/* 选项文字：浅底 → 深字，同源硬编码（暗色下也不会隐形） */
.sbk2 .opt .otext{color:inherit !important; font-weight:700}
.sbk2 .opt .tick{
  border-color:var(--p-txt-3) !important; color:#fff !important;
  border-radius:8px !important; width:24px !important; height:24px !important;
  transition:background-color var(--p-d-s), border-color var(--p-d-s), transform var(--p-d-s) var(--p-e-back);
}
.sbk2 .opt.sel .tick{background:var(--p-blue-d) !important; border-color:var(--p-blue-d) !important}
.sbk2 .opt.sel .tick{transform:scale(1.08)}

/* ---------- 答对：金色流光 + 勾选放大 ---------- */
.sbk2 .q.correct{
  background:linear-gradient(150deg, var(--p-ok-s), var(--p-card-2)) !important;
  border-color:var(--p-ok) !important; box-shadow:var(--p-shadow-m) !important;
}
.sbk2 .opt.ok{
  background:linear-gradient(150deg, var(--p-ok-s), var(--p-card-2)) !important;
  border-color:var(--p-ok) !important; color:var(--p-ok-ink) !important;
  animation:sbk2-okpulse .8s var(--p-e-soft) 1 both;
}
.sbk2 .opt.ok .tick{background:var(--p-ok) !important; border-color:var(--p-ok) !important;
  animation:sbk2-tickpop .5s var(--p-e-back) 1}
@keyframes sbk2-okpulse{
  0%{box-shadow:var(--p-shadow-s), 0 0 0 0 rgba(212,180,131,.55)}
  28%{box-shadow:var(--p-shadow-m), 0 0 26px 5px rgba(212,180,131,.34)}
  100%{box-shadow:var(--p-shadow-s), 0 0 0 0 rgba(212,180,131,0)}
}
@keyframes sbk2-tickpop{
  0%{transform:scale(1)}
  42%{transform:scale(1.26)}
  100%{transform:scale(1)}
}
/* 星芒粒子：由 JS 注入，0.8s 内迸发并自动淡出，不阻塞答题 */
.sbk2-spark{position:fixed; z-index:64; pointer-events:none;
  width:8px;height:8px;border-radius:50%;
  background:radial-gradient(circle, var(--p-gold) 0%, rgba(212,180,131,.5) 46%, transparent 72%);
  animation:sbk2-burst .8s var(--p-e-out) forwards;}
@keyframes sbk2-burst{
  0%{transform:translate3d(0,0,0) scale(.3); opacity:0}
  16%{opacity:1}
  100%{transform:translate3d(var(--dx,0), var(--dy,-58px), 0) scale(.15); opacity:0}
}
/* 柔和金色扩散光晕 */
.sbk2-halo{position:fixed; z-index:63; pointer-events:none;
  width:74px;height:74px;margin:-37px 0 0 -37px;border-radius:50%;
  background:radial-gradient(circle, rgba(212,180,131,.42) 0%, rgba(212,180,131,.12) 45%, transparent 70%);
  animation:sbk2-halo .8s var(--p-e-out) forwards;}
@keyframes sbk2-halo{
  0%{transform:scale(.25); opacity:0}
  22%{opacity:.9}
  100%{transform:scale(2.5); opacity:0}
}

/* ---------- 答错：小幅阻尼抖动 + 柔和红晕（不惊吓） ---------- */
.sbk2 .q.wrong{
  background:linear-gradient(150deg, var(--p-bad-s), var(--p-card-2)) !important;
  border-color:var(--p-bad) !important;
}
.sbk2 .opt.no{
  background:linear-gradient(150deg, var(--p-bad-s), var(--p-card-2)) !important;
  border-color:var(--p-bad) !important; color:var(--p-bad-ink) !important;
  animation:sbk2-damp .5s var(--p-e-soft) 1;
}
.sbk2 .opt.no .tick{background:var(--p-bad) !important; border-color:var(--p-bad) !important}
/* 阻尼：幅度 3~5px 递减，不剧烈震动 */
@keyframes sbk2-damp{
  0%{transform:translateX(0)}
  18%{transform:translateX(-4px)}
  38%{transform:translateX(3.5px)}
  58%{transform:translateX(-2.5px)}
  76%{transform:translateX(1.6px)}
  90%{transform:translateX(-.8px)}
  100%{transform:translateX(0)}
}

/* ---------- 反馈条与答案解析 ---------- */
.sbk2 .fb{
  background:var(--p-card) !important; border:1px solid var(--p-line) !important;
  border-radius:14px !important; color:var(--p-txt-2) !important;
  box-shadow:var(--p-shadow-s) !important;
}
.sbk2 .fb.ok{background:var(--p-ok-s) !important; border-color:var(--p-ok) !important;
  color:var(--p-ok-ink) !important}
.sbk2 .fb.no{background:var(--p-bad-s) !important; border-color:var(--p-bad) !important;
  color:var(--p-bad-ink) !important}
.sbk2 .answer{
  background:var(--p-sage-s) !important; color:var(--p-sage-ink) !important;
  border-radius:12px !important; padding:11px 15px !important;
  border-left:3px solid var(--p-sage) !important;
  font-size:13.8px !important; line-height:1.7 !important;
}

/* ---------- 按钮 ---------- */
.sbk2 .btn{
  background:linear-gradient(145deg, var(--p-blue), var(--p-blue-d)) !important;
  color:#fff !important; border:0 !important;
  border-radius:15px !important; padding:15px !important;
  font-size:17px !important; font-weight:800 !important;
  box-shadow:0 3px 0 var(--p-blue-d), var(--p-shadow-s) !important;
  transition:transform var(--p-d-s) var(--p-e-out), box-shadow var(--p-d-s) var(--p-e-soft);
  min-height:52px !important;
}
.sbk2 .btn:hover{transform:translateY(-1px);
  box-shadow:0 5px 0 var(--p-blue-d), var(--p-shadow-m) !important}
.sbk2 .btn:active{transform:translateY(2px);
  box-shadow:0 1px 0 var(--p-blue-d), var(--p-shadow-s) !important}
.sbk2 .btn.sec{background:linear-gradient(145deg, var(--p-sand), var(--p-sand-d)) !important;
  box-shadow:0 3px 0 var(--p-sand-d), var(--p-shadow-s) !important}
.sbk2 .btn.sec:hover{box-shadow:0 5px 0 var(--p-sand-d), var(--p-shadow-m) !important}
.sbk2 .btn:disabled{opacity:.62; filter:saturate(.7); transform:none !important}
/* 结果卡 */
.sbk2 .result{
  background:linear-gradient(150deg, var(--p-card), var(--p-card-2)) !important;
  border:1px solid var(--p-line) !important; border-radius:20px !important;
  box-shadow:var(--p-shadow-m) !important; color:var(--p-txt-2) !important;
}
.sbk2 .result .big{
  background:linear-gradient(145deg, var(--p-blue), var(--p-lilac));
  -webkit-background-clip:text; background-clip:text;
  -webkit-text-fill-color:transparent; color:transparent;
  font-size:44px !important; font-weight:800 !important;
}
.sbk2 .result .bar{background:var(--p-line) !important; border-radius:99px !important; height:11px !important}
.sbk2 .result .bar > i{
  background:linear-gradient(90deg, var(--p-blue), var(--p-sage)) !important;
  border-radius:99px !important; transition:width .6s var(--p-e-soft) !important;
}
.sbk2 .foot{color:var(--p-txt-3) !important}
/* 主题按钮与朗读按钮 */
.sbk2 .themebtn{
  background:var(--p-card) !important; color:var(--p-txt-2) !important;
  border:1px solid var(--p-line) !important; border-radius:20px !important;
  box-shadow:var(--p-shadow-s) !important;
  transition:transform var(--p-d-s) var(--p-e-out), box-shadow var(--p-d-s) var(--p-e-soft);
  min-height:36px;
}
.sbk2 .themebtn:hover{transform:translateY(-1px); box-shadow:var(--p-shadow-m) !important}
.sbk2 .spk{
  background:var(--p-blue-s) !important; color:var(--p-blue-ink) !important;
  border:0 !important; border-radius:50% !important;
  box-shadow:var(--p-shadow-s) !important;
  /* 触屏热区 >=44px（规范要求）。原先写的是 30px，是我自己定的规范自己
     没遵守 —— 无头实测每个页面 16~26 个朗读按钮只有 30x30。 */
  min-width:44px !important; min-height:44px !important;
  display:inline-flex !important; align-items:center; justify-content:center;
  transition:transform var(--p-d-s) var(--p-e-back), background-color var(--p-d-s);
}
.sbk2 .spk:hover{background:var(--p-blue) !important; color:#fff !important; transform:scale(1.06)}
.sbk2 .spk.playing{background:var(--p-blue-d) !important; color:#fff !important}

/* ---------- 音频控制坞 ---------- */
.sbk2-dock{
  position:fixed; right:16px; bottom:16px; z-index:70;
  display:flex; align-items:center; gap:9px;
  padding:10px 12px; border-radius:999px;
  background:var(--p-card) !important;
  border:1px solid var(--p-line) !important;
  box-shadow:var(--p-shadow-l) !important;
}
.sbk2-ib{
  /* 触屏热区 >=44px（规范要求）。窄屏媒体查询里也**不许**缩小 ——
     移动端正是最需要大热区的时候。 */
  width:44px; height:44px; min-width:44px; min-height:44px; border-radius:50%;
  border:1px solid var(--p-line); background:var(--p-card-2);
  color:var(--p-txt-2); font-size:18px; line-height:1; cursor:pointer;
  display:flex; align-items:center; justify-content:center;
  box-shadow:var(--p-shadow-s);
  transition:transform var(--p-d-s) var(--p-e-back),
             background-color var(--p-d-s), color var(--p-d-s);
}
.sbk2-ib:hover{transform:scale(1.07); background:var(--p-blue-s); color:var(--p-blue-ink)}
.sbk2-ib:active{transform:scale(.96)}
.sbk2-ib:focus-visible{outline:3px solid var(--p-blue); outline-offset:2px}
.sbk2-ib[aria-pressed="true"]{background:var(--p-blue-s); color:var(--p-blue-ink)}
.sbk2-ib.sbk2-off{opacity:.5; filter:grayscale(1)}
.sbk2-vol{width:82px; accent-color:var(--p-blue-d); cursor:pointer; background:transparent}

/* ---------- 响应式：平板 / 移动 ---------- */
@media (max-width:720px){
  .sbk2 .wrap{padding:16px 13px 96px !important}
  .sbk2 .head{padding:18px 17px !important; border-radius:18px !important}
  .sbk2 .head h1{font-size:20px !important}
  .sbk2 .q{padding:18px 16px !important; border-radius:17px !important}
  .sbk2 .stem{font-size:17.5px !important; line-height:1.7 !important}
  .sbk2 .opt{font-size:16px !important; padding:13px 14px !important;
    min-height:52px !important; border-radius:15px !important}
  .sbk2 .result .big{font-size:38px !important}
  .sbk2-dock{right:12px; bottom:12px; padding:8px 10px; gap:7px}
  /* 窄屏仍保持 44px 热区（只缩图标，不缩按钮） */
  .sbk2-ib{font-size:17px}
  .sbk2-vol{width:64px}
  /* 装饰在窄屏上更收敛，避免干扰阅读 */
  .sbk2-sh{opacity:.5; filter:blur(18px)}
  .sbk2-sh.r5{display:none}
}
@media (max-width:420px){
  .sbk2-vol{display:none}
  .sbk2-dock{gap:6px; padding:7px 9px}
}

/* ---------- 性能与无障碍：低端设备不卡顿 ---------- */
@media (prefers-reduced-motion: reduce){
  .sbk2-bg, .sbk2-sh, .sbk2-sp{display:none !important}
  .sbk2 .head::before, .sbk2 .opt::before{display:none !important}
  .sbk2 .q, .sbk2 .opt, .sbk2 .btn, .sbk2 .themebtn, .sbk2 .spk, .sbk2-ib,
  .sbk2 .opt.ok, .sbk2 .opt.no, .sbk2 .opt.ok .tick, .sbk2 .opt.sel .tick,
  .sbk2 .result .bar > i, .sbk2 .q.sbk2-in{
    animation:none !important; transition:none !important;
  }
  .sbk2 .opt:hover{transform:none !important}
}
</style>
"""


# ============================================================== JS
ENHANCE_JS = r"""
<script id="__SBK2_JS__">
(function(){
  "use strict";
  var doc = document;
  var root = doc.documentElement;

  /* ---------- 动效强度与音频偏好 ---------- */
  var reduced = false;
  try { reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch(e){}
  var lowPower = false;
  try { lowPower = (navigator.hardwareConcurrency || 8) <= 4; } catch(e){}

  var P_SFX = "sbk2_sound";
  var P_BGM = "sbk2_bgm";
  var P_VOL = "sbk2_vol";
  function readLS(k, d){ try { var v = localStorage.getItem(k); return (v === null || v === "") ? d : v; } catch(e){ return d; } }
  function writeLS(k, v){ try { localStorage.setItem(k, v); } catch(e){} }

  /* ==========================================================
     1. 音频：高保真合成音色
     ----------------------------------------------------------
     浏览器自动播放策略：用户产生真实手势（pointerdown/click/keydown）
     之前**绝对不能 new AudioContext()**，否则控制台会按每个音一条
     刷 "The AudioContext was not allowed to start" 警告，声音也不响。
     所以用 unlocked 闸门：未解锁时 audio() 直接返回 null，
     所有发声自然空转且不报错。
     ========================================================== */
  var AC = window.AudioContext || window.webkitAudioContext;
  var ac = null, master = null, comp = null;
  var unlocked = false;
  var sfxOn = readLS(P_SFX, "1") === "1";
  var bgmOn = readLS(P_BGM, "0") === "1";
  var vol = (function(){ var v = parseFloat(readLS(P_VOL, "0.5")); return (isNaN(v) ? 0.5 : Math.max(0, Math.min(1, v))); })();

  function audio(){
    if (!AC || !unlocked) { return null; }
    if (!ac) {
      try {
        ac = new AC();
        comp = ac.createDynamicsCompressor();
        /* 温和压缩：避免多音叠加时刺耳，同时保留奖励音的通透感 */
        comp.threshold.value = -18; comp.knee.value = 22;
        comp.ratio.value = 4; comp.attack.value = .004; comp.release.value = .18;
        master = ac.createGain();
        master.gain.value = vol;
        master.connect(comp); comp.connect(ac.destination);
      } catch(e){ ac = null; }
    }
    if (ac && ac.state === "suspended") { try { ac.resume(); } catch(e){} }
    return ac;
  }
  function unlockAudio(){
    if (unlocked) { return; }
    unlocked = true;
    var a = audio();
    if (a) { try { a.resume(); } catch(e){} }
    if (bgmOn) { bgmStart(); }
  }

  /* --- 音色库：全部为正弦/三角波 + 指数包络，干净无噪 --- */
  function env(g, t, a, d, peak){
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(peak, t + a);
    g.gain.exponentialRampToValueAtTime(0.0001, t + a + d);
  }
  function tone(o){
    var a = audio(); if (!a || !sfxOn) { return; }
    var t = o.at || a.currentTime + 0.005;
    var osc = a.createOscillator(), g = a.createGain();
    osc.type = o.type || "sine";
    osc.frequency.setValueAtTime(o.f, t);
    if (o.f2) { osc.frequency.exponentialRampToValueAtTime(o.f2, t + (o.slide || .12)); }
    env(g, t, o.a || .008, o.d || .18, o.p == null ? .3 : o.p);
    var node = osc;
    if (o.filt) {
      var lp = a.createBiquadFilter();
      lp.type = "lowpass"; lp.frequency.value = o.filt; lp.Q.value = .7;
      osc.connect(lp); node = lp;
    }
    node.connect(g); g.connect(master);
    osc.start(t); osc.stop(t + (o.a || .008) + (o.d || .18) + .04);
  }
  var SFX = {
    /* 点击：轻脆短促的高音，2 个泛音微叠加 → 干净不刺耳 */
    click: function(){
      tone({f:1180, f2:1560, type:"sine", a:.004, d:.07, p:.20, filt:5200});
      tone({f:2360, type:"sine", a:.003, d:.045, p:.055, filt:6400});
    },
    /* 答对：明亮通透的三音上行奖励音（纯律叠置，泛音自然） */
    good: function(){
      var a = audio(); if (!a || !sfxOn) { return; }
      var t0 = a.currentTime + 0.005;
      tone({at:t0,         f:659.25, type:"sine", a:.01, d:.30, p:.24});  /* E5 */
      tone({at:t0+.075,    f:830.61, type:"sine", a:.01, d:.30, p:.21});  /* G#5 */
      tone({at:t0+.150,    f:987.77, type:"sine", a:.01, d:.52, p:.19});  /* B5 */
      tone({at:t0+.150,    f:1318.5, type:"sine", a:.012, d:.46, p:.075}); /* E6 泛音 */
    },
    /* 答错：低沉温和的两音下行，圆润无冲击 */
    bad: function(){
      var a = audio(); if (!a || !sfxOn) { return; }
      var t0 = a.currentTime + 0.005;
      tone({at:t0,      f:392.00, f2:349.23, type:"sine", a:.02, d:.20, p:.19, slide:.14});
      tone({at:t0+.10,  f:293.66, f2:261.63, type:"sine", a:.02, d:.26, p:.13, slide:.16, filt:1200});
    },
    /* 切题：极轻的气流感，引导注意但不打扰 */
    turn: function(){ tone({f:880, f2:1046.5, type:"sine", a:.006, d:.10, p:.10, filt:4800}); }
  };
  function play(k){ try { if (SFX[k]) { SFX[k](); } } catch(e){} }

  /* --- BGM：轻柔环境音（正弦琶音 + 慢速包络），非循环采样文件 --- */
  var bgmTimer = null, bgmStep = 0;
  var BGM_CHORD = [
    [261.63, 329.63, 392.00],   /* C 大调 */
    [220.00, 261.63, 329.63],   /* Am */
    [174.61, 220.00, 261.63],   /* F */
    [196.00, 246.94, 293.66]    /* G */
  ];
  function bgmTick(){
    var a = audio(); if (!a || !bgmOn) { return; }
    var ch = BGM_CHORD[bgmStep % BGM_CHORD.length];
    var t = a.currentTime + 0.02;
    for (var i = 0; i < ch.length; i++) {
      var osc = a.createOscillator(), g = a.createGain(), lp = a.createBiquadFilter();
      osc.type = "sine";
      osc.frequency.value = ch[i] * (i === 2 ? 2 : 1);   /* 高八度更清透 */
      lp.type = "lowpass"; lp.frequency.value = 1500; lp.Q.value = .4;
      /* 极缓的起落 + 低音量 = 环境音而非背景音乐 */
      g.gain.setValueAtTime(0.0001, t);
      g.gain.exponentialRampToValueAtTime(0.032, t + .8);
      g.gain.exponentialRampToValueAtTime(0.0001, t + 2.6);
      osc.connect(lp); lp.connect(g); g.connect(master);
      osc.start(t); osc.stop(t + 2.8);
    }
    bgmStep++;
  }
  function bgmStart(){
    if (bgmTimer) { return; }
    if (!unlocked) { return; }   /* 闸门未开不排程，免占定时器 */
    bgmTick();
    bgmTimer = setInterval(bgmTick, 2600);
  }
  function bgmStop(){ if (bgmTimer) { clearInterval(bgmTimer); bgmTimer = null; } }

  /* ==========================================================
     2. 背景：几何漂浮 + 粒子流光
     ----------------------------------------------------------
     性能：粒子数量按设备能力自适应（低端机减半）；
     全部用 transform/opacity，**不触发重排**；低端机直接不生成粒子。
     ========================================================== */
  function buildBackdrop(){
    if (reduced) { return; }
    var bg = doc.createElement("div");
    bg.className = "sbk2-bg";
    var shapes = ["r1","r2","r3","r4","r5"];
    for (var i = 0; i < shapes.length; i++) {
      var s = doc.createElement("span");
      s.className = "sbk2-sh " + shapes[i];
      bg.appendChild(s);
    }
    doc.body.appendChild(bg);

    var n = lowPower ? 8 : 18;
    for (var j = 0; j < n; j++) {
      var p = doc.createElement("span");
      p.className = "sbk2-sp";
      p.style.left = (Math.random() * 100).toFixed(2) + "%";
      p.style.bottom = (-Math.random() * 30).toFixed(2) + "%";
      var size = 2 + Math.random() * 3.2;
      p.style.width = size.toFixed(1) + "px";
      p.style.height = size.toFixed(1) + "px";
      p.style.animationDuration = (22 + Math.random() * 26).toFixed(1) + "s";
      p.style.animationDelay = (-Math.random() * 30).toFixed(1) + "s";
      bg.appendChild(p);
    }
  }

  /* ==========================================================
     3. 星芒粒子：答对时 0.8s 迸发并自动移除
     ========================================================== */
  function burst(el){
    if (!el || reduced || lowPower) { return; }
    var r = el.getBoundingClientRect();
    if (!r.width) { return; }
    var cx = r.left + r.width / 2, cy = r.top + r.height / 2;
    var host = doc.body;
    /* 光晕 */
    var halo = doc.createElement("span");
    halo.className = "sbk2-halo";
    halo.style.left = cx + "px"; halo.style.top = cy + "px";
    host.appendChild(halo);
    /* 8 颗星芒，扇形略向上展开 */
    var count = 8;
    for (var i = 0; i < count; i++) {
      var s = doc.createElement("span");
      s.className = "sbk2-spark";
      var ang = (-Math.PI * .86) + (i / (count - 1)) * Math.PI * .72;
      var dist = 26 + Math.random() * 30;
      s.style.left = cx + "px"; s.style.top = cy + "px";
      s.style.setProperty("--dx", (Math.cos(ang) * dist).toFixed(1) + "px");
      s.style.setProperty("--dy", (Math.sin(ang) * dist).toFixed(1) + "px");
      s.style.animationDelay = (Math.random() * .09).toFixed(3) + "s";
      host.appendChild(s);
      (function(node){ setTimeout(function(){ if (node.parentNode) { node.parentNode.removeChild(node); } }, 1100); })(s);
    }
    setTimeout(function(){ if (halo.parentNode) { halo.parentNode.removeChild(halo); } }, 1000);
  }

  /* ==========================================================
     4. 入场编排：题目卡片淡入 + 轻微上浮
     ----------------------------------------------------------
     ⚠️ keyframes 只动 transform，不碰 opacity —— 保证无论动画是否
     执行，内容可见性都不受影响（见 MEMORY.md 的教训记录）。
     ========================================================== */
  function qIn(node, delay){
    if (!node || reduced) { return; }
    node.classList.remove("sbk2-in");
    void node.offsetWidth;              /* 强制 reflow 以便重放 */
    node.style.animationDelay = (delay || 0) + "s";
    node.classList.add("sbk2-in");
    /* ⚠️⚠️ 必须 animationend 后摘掉 class。`fill-mode:backwards` 会让动画
       在结束后**依然驻留在 getAnimations() 里**（playState 仍为 running/finished
       但对象不回收）。无头实测：20 道题各挂 3 个常驻动画 = 60 个永不释放，
       全文页 536 个动画对象。低性能设备上这是实打实的内存与合成开销。
       入场动画是一次性的，播完就该彻底释放。 */
    var cleaned = false;
    function cleanup(){
      if (cleaned) { return; }
      cleaned = true;
      node.classList.remove("sbk2-in");
      node.style.animationDelay = "";
    }
    node.addEventListener("animationend", cleanup, {once:true});
    /* 保险丝：动画时钟若未推进（标签页节流等），2s 后摘掉 class 回自然位 */
    setTimeout(function(){
      var list = node.getAnimations ? node.getAnimations() : [];
      for (var i = 0; i < list.length; i++) {
        if ((list[i].currentTime || 0) > 0) { return; }
      }
      cleanup();
    }, 2000);
  }
  function runIn(){
    var qs = doc.querySelectorAll(".q");
    for (var i = 0; i < qs.length; i++) {
      qIn(qs[i], Math.min(i * 0.045, 0.5));
    }
  }

  /* ==========================================================
     5. 判分结果观察：只看 class，绝不改判分逻辑
     ----------------------------------------------------------
     引擎 grade() 会给 .q 加 correct/wrong，给 .opt 加 ok/no。
     我们据此触发动效与音效，**不参与判定**。
     ========================================================== */
  var seenState = new WeakSet();
  function handleQ(q){
    if (!q || seenState.has(q)) { return; }
    var ok = q.classList.contains("correct");
    var no = q.classList.contains("wrong");
    if (!ok && !no) { return; }
    seenState.add(q);
    if (ok) {
      play("good");
      var opts = q.querySelectorAll(".opt.ok");
      for (var i = 0; i < opts.length; i++) { burst(opts[i]); }
    } else {
      play("bad");
    }
  }
  function watch(){
    if (window.MutationObserver && doc.body) {
      var mo = new MutationObserver(function(){
        var qs = doc.querySelectorAll(".q.correct, .q.wrong");
        for (var i = 0; i < qs.length; i++) { handleQ(qs[i]); }
      });
      mo.observe(doc.body, {subtree:true, childList:true, attributes:true, attributeFilter:["class"]});
    }
  }

  /* ==========================================================
     6. 交互：悬浮 / 按下
     ----------------------------------------------------------
     捕获阶段监听，**只加 class 与播音效，绝不 preventDefault /
     stopPropagation**，引擎的答题逻辑完全不受影响。
     ⚠️ 必须在本监听开头就 unlockAudio()：本监听是捕获阶段，
     比挂在冒泡阶段的解锁先跑，不在这里解锁则首次点击无声。
     ========================================================== */
  function bind(){
    doc.addEventListener("click", function(ev){
      unlockAudio();
      var t = ev.target;
      if (!t || !t.closest) { return; }
      if (t.closest(".sbk2-dock")) { return; }
      var o = t.closest(".opt");
      if (!o) { return; }
      play("click");
      o.classList.add("sbk2-press");
      setTimeout(function(){ o.classList.remove("sbk2-press"); }, 170);
    }, true);
    doc.addEventListener("pointerdown", function(ev){
      unlockAudio();
      if (reduced) { return; }
      var t = ev.target;
      if (!t || !t.closest) { return; }
      var o = t.closest(".opt");
      if (o) { o.classList.add("sbk2-press"); }
    }, true);
  }

  /* ==========================================================
     7. 音频控制坞：BGM 开关 + 音量 + 音效开关
     ========================================================== */
  /* 线性 SVG 图标（stroke=currentColor，跟随主题）。
     ⚠️ 绝不用 emoji（🔊🎵）：emoji 本身就是「廉价卡通贴纸」观感的来源，
     与用户「摒弃简陋廉价卡通贴纸、整体精致高级」的要求直接冲突。 */
  function svg(inner){
    return '<svg viewBox="0 0 24 24" width="19" height="19" fill="none" ' +
      'stroke="currentColor" stroke-width="1.7" stroke-linecap="round" ' +
      'stroke-linejoin="round" aria-hidden="true">' + inner + '</svg>';
  }
  var ICON_SND_ON  = svg('<path d="M4 9.5h3.2L12 5.4v13.2L7.2 14.5H4z"/>' +
    '<path d="M15.6 9.2a4 4 0 0 1 0 5.6"/><path d="M18.2 6.6a7.6 7.6 0 0 1 0 10.8"/>');
  var ICON_SND_OFF = svg('<path d="M4 9.5h3.2L12 5.4v13.2L7.2 14.5H4z"/>' +
    '<path d="M16.2 9.8l4.4 4.4M20.6 9.8l-4.4 4.4"/>');
  var ICON_BGM_ON  = svg('<path d="M9 18V6.4l10-2v11.2"/>' +
    '<circle cx="6.6" cy="18" r="2.4"/><circle cx="16.6" cy="15.6" r="2.4"/>');
  var ICON_BGM_OFF = svg('<path d="M9 18V6.4l10-2v7.4"/>' +
    '<circle cx="6.6" cy="18" r="2.4"/><path d="M16.8 13.2l4.6 4.6M21.4 13.2l-4.6 4.6"/>');
  function buildDock(){
    if (doc.querySelector(".sbk2-dock")) { return; }
    var d = doc.createElement("div");
    d.className = "sbk2-dock";

    var snd = doc.createElement("button");
    snd.type = "button"; snd.className = "sbk2-ib";
    snd.title = "音效开关";
    var bgm = doc.createElement("button");
    bgm.type = "button"; bgm.className = "sbk2-ib";
    bgm.title = "背景音乐开关";
    var volEl = doc.createElement("input");
    volEl.type = "range"; volEl.className = "sbk2-vol";
    volEl.min = "0"; volEl.max = "100"; volEl.step = "5";
    volEl.value = String(Math.round(vol * 100));
    volEl.title = "音量";

    d.appendChild(snd); d.appendChild(bgm); d.appendChild(volEl);
    doc.body.appendChild(d);

    function paint(){
      snd.innerHTML = sfxOn ? ICON_SND_ON : ICON_SND_OFF;
      snd.setAttribute("aria-pressed", sfxOn ? "true" : "false");
      snd.classList.toggle("sbk2-off", !sfxOn);
      snd.title = sfxOn ? "音效：开" : "音效：关";
      bgm.innerHTML = bgmOn ? ICON_BGM_ON : ICON_BGM_OFF;
      bgm.setAttribute("aria-pressed", bgmOn ? "true" : "false");
      bgm.classList.toggle("sbk2-off", !bgmOn);
      bgm.title = bgmOn ? "背景音乐：开" : "背景音乐：关";
    }
    paint();

    snd.addEventListener("click", function(e){
      e.stopPropagation(); unlockAudio();
      sfxOn = !sfxOn; writeLS(P_SFX, sfxOn ? "1" : "0");
      if (sfxOn) { play("click"); } else { bgmStop(); }
      paint();
    });
    bgm.addEventListener("click", function(e){
      e.stopPropagation(); unlockAudio();
      bgmOn = !bgmOn; writeLS(P_BGM, bgmOn ? "1" : "0");
      if (bgmOn) { bgmStart(); play("click"); } else { bgmStop(); }
      paint();
    });
    volEl.addEventListener("input", function(){
      vol = Math.max(0, Math.min(1, (parseFloat(volEl.value) || 0) / 100));
      writeLS(P_VOL, String(vol));
      if (master) { try { master.gain.value = vol; } catch(e){} }
    });
    volEl.addEventListener("click", function(e){ e.stopPropagation(); });
  }

  /* ==========================================================
     8. 切题音：观察题库变化，播极轻的引导音
     ========================================================== */
  function watchTurn(){
    if (window.MutationObserver && doc.getElementById("quiz")) {
      var host = doc.getElementById("quiz");
      var mo = new MutationObserver(function(){ if (unlocked) { play("turn"); } });
      mo.observe(host, {childList:true});
    }
  }

  /* ---------- 启动 ---------- */
  function boot(){
    root.classList.add("sbk2");
    buildBackdrop();
    buildDock();
    bind();
    watch();
    watchTurn();
    runIn();
    /* 音频解锁闸门：挂在真实用户手势上。keydown/touchstart 一并挂上，
       兼顾键盘操作与旧触屏。 */
    ["pointerdown","click","keydown","touchstart"].forEach(function(ev){
      doc.addEventListener(ev, unlockAudio, {passive:true});
    });
    /* 切题时重新播放入场动画 */
    if (window.MutationObserver && doc.getElementById("quiz")) {
      var host2 = doc.getElementById("quiz");
      var mo2 = new MutationObserver(function(){ seenState = new WeakSet(); setTimeout(runIn, 60); });
      mo2.observe(host2, {childList:true});
    }
  }
  if (doc.readyState === "loading") {
    doc.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
</script>
"""
