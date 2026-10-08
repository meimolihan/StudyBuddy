# -*- coding: utf-8 -*-
"""自测页「壳模板」—— 一份模板 + 一个 HAS_JUDGE 开关覆盖全部题型。

============================ 为什么要模板化 ============================
盘上 424 个旧自测页（grade1 208 + grade2 216）此前是**各写一遍**的：
每个文件里都塞着一份 1000 多行的 HTML 骨架 + CSS + 引擎 JS。经指纹
核对确认，它们其实只有 **2 种壳**：

    判断题壳 212 个（t 支持 s / m / j）
    选择题壳 212 个（t 只支持 s / m）

逐行 diff 两种壳的结果：

    CSS     差异  0 行   ← 完全相同
    JS      差异 17 行   ← 全部是「是否支持 t==="j"」这一个开关
    MARKUP  差异 11 行   ← title / sub 的「· 判断题」后缀 + 题库总数

所以**不需要两份模板**，一份 + `HAS_JUDGE` 布尔开关即可全覆盖。
新增自测页时只写题库数据，壳由 selftest_gen.py 渲染。

============================ 硬约束（改本文件前必读）========================
1. **零外部依赖**：模板里不能出现 <link href> / <script src>。
   自测页是通过 iframe 以 `/lesson?key=...` 打开的，base URL 不在 content
   目录里，任何相对路径（../../shared/x.css）会解析到磁盘上不存在的位置。
   同时「双击 HTML 就能玩」的离线能力也依赖零外链。

2. **不得出现字面量 `const ALL = [`（含注释里）**：
   textbook.ParseBank 用 strings.Index(html, "const ALL = [") 定位**第一个**
   出现处。写在注释/文档字符串里会被先命中，导致题库解析成 0 题。
   本模块的 docstring 因此刻意写成「const ALL」而不带 `[`。

3. **每题必须独占一行**：scripts/verify_games.py 的 check_bank 按行解析
   题库条目，多行条目会被判为格式错误。

4. **a 字段必须是带引号的字母**：a:["B"] / a:["C", "D"]。
   写成数字或裸标识符会被 ParseBank 的 readArray 丢弃整题（静默 0 题）。

5. **本模板用 LF 换行**，写盘时由 selftest_gen.py 统一转成 CRLF
   （盘上 1908 个源页实测 100% CRLF）。
"""
from __future__ import annotations

# ---------------------------------------------------------------- 开关
# 这三段是两种壳**唯一**的差异，渲染时按题型替换。
# 占位符统一用 {{TOKEN}}，不用 str.format —— 模板里 CSS/JS 有大量花括号，
# format 会把它们当成替换域直接炸掉。

_BADGE_JUDGE = (
    'badge.className="badge "+(item.t==="m"?"m":"s");\n'
    '    badge.textContent=item.t==="j"?"判断题":(item.t==="s"?"单选题":"多选题");'
)
_BADGE_PLAIN = (
    'badge.className="badge "+(item.t==="s"?"s":"m");\n'
    '    badge.textContent=item.t==="s"?"单选题":"多选题";'
)

_SPEAK_JUDGE = (
    '+(item.t==="j"?"这是判断题，请判断正确还是错误。":'
    '(item.t==="s"?"这是单选题，请选一个答案。":"这是多选题，可以选多个答案。"))'
)
_SPEAK_PLAIN = (
    '+(item.t==="s"?"这是单选题，请选一个答案。":"这是多选题，可以选多个答案。")'
)

# 判断题的选项本质是二选一，pick 时必须走「单选」分支（选中新的即取消旧的）
_PICK_JUDGE = 'if(item.t==="s"||item.t==="j"){'
_PICK_PLAIN = 'if(item.t==="s"){'

# 判断题页会显示解析行（e 字段）；选择题页只显示答案
_ANSWER_JUDGE = (
    '"<b>正确答案："+item.a.join("、")+"</b>" + (right?" ✓ 你答对啦！":"（本题你未答对）")\n'
    '      + (item.e?"<br>解析："+item.e:"");'
)
_ANSWER_PLAIN = (
    '"<b>正确答案："+item.a.join("、")+"</b>" + (right?" ✓ 你答对啦！":"（本题你未答对）");'
)

# ---------------------------------------------------------------- CSS
CSS = """
  :root{
    --bg:#eef2f7; --card:#ffffff; --ink:#1f2937; --muted:#5b6b7b;
    --brand:#1565c0; --brand-soft:#e6f0fb; --ok:#2e7d32; --ok-soft:#e9f6ea;
    --bad:#d32f2f; --bad-soft:#fdecec; --line:#e3e8ef; --warn:#e65100;
    --head1:#1565c0; --head2:#7b1fa2; --btn-sec:#78909c;
  }
  @media (prefers-color-scheme: dark){
    :root:not([data-theme="light"]){
      --bg:#0f1620; --card:#1a2533; --ink:#e6edf3; --muted:#9fb0c0;
      --brand:#4ea1ff; --brand-soft:#16273c; --ok:#5fbf6a; --ok-soft:#15301c;
      --bad:#ff6b6b; --bad-soft:#3a1a1a; --line:#2a3a4a; --warn:#ffa040;
      --head1:#1e3a5f; --head2:#3a1f5f; --btn-sec:#54677a;
    }
  }
  [data-theme="dark"]{
    --bg:#0f1620; --card:#1a2533; --ink:#e6edf3; --muted:#9fb0c0;
    --brand:#4ea1ff; --brand-soft:#16273c; --ok:#5fbf6a; --ok-soft:#15301c;
    --bad:#ff6b6b; --bad-soft:#3a1a1a; --line:#2a3a4a; --warn:#ffa040;
    --head1:#1e3a5f; --head2:#3a1f5f; --btn-sec:#54677a;
  }
  *{box-sizing:border-box;}
  body{margin:0;background:var(--bg);color:var(--ink);
    font-family:"Microsoft YaHei","PingFang SC","微软雅黑",sans-serif;line-height:1.6;
    transition:background .25s ease,color .25s ease;}
  .wrap{max-width:760px;margin:0 auto;padding:20px 16px 60px;}
  .head{background:linear-gradient(135deg,var(--head1),var(--head2));color:#fff;
    border-radius:16px;padding:18px 20px;box-shadow:0 6px 18px rgba(0,0,0,.12);}
  .topbar{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;}
  .head h1{margin:0;font-size:21px;color:#fff;letter-spacing:.5px;}
  .themebtn{background:rgba(255,255,255,.18);color:#fff;border:1px solid rgba(255,255,255,.4);
    border-radius:20px;padding:6px 14px;font-size:13px;cursor:pointer;white-space:nowrap;
    transition:.15s ease;}
  .themebtn:hover{background:rgba(255,255,255,.32);}
  .sub{color:rgba(255,255,255,.88);font-size:14px;margin:10px 0 14px;}
  .meta{display:flex;flex-wrap:wrap;gap:10px;font-size:14px;}
  .meta .box{background:rgba(255,255,255,.92);border-radius:8px;padding:6px 12px;color:#0d47a1;}
  .meta .box b{color:#1565c0;}
  .meta #score.done{background:#fff3e0;color:#e65100;}
  .bank{font-size:13px;color:#1f2937;background:rgba(255,255,255,.88);border-radius:8px;
    padding:8px 12px;margin-top:12px;}
  .tip{background:rgba(255,255,255,.92);border-left:4px solid #ffb300;border-radius:8px;
    padding:10px 14px;font-size:13px;color:#5d4037;margin-top:12px;}
  .q{background:var(--card);border:1px solid var(--line);border-radius:14px;
    padding:16px 18px;margin-top:16px;box-shadow:0 1px 6px rgba(0,0,0,.04);transition:.2s;}
  .q.correct{border-color:var(--ok);background:var(--ok-soft);}
  .q.wrong{border-color:var(--bad);background:var(--bad-soft);}
  .qtop{display:flex;align-items:center;gap:8px;margin-bottom:8px;}
  .badge{font-size:12px;font-weight:700;color:#fff;border-radius:6px;padding:2px 8px;}
  .badge.s{background:var(--brand);}
  .badge.m{background:var(--warn);}
  .qno{font-weight:700;}
  .qtop{display:flex;align-items:center;gap:8px;flex-wrap:wrap;}
  .qspk{margin-left:auto;}
  .spk{flex:0 0 auto;display:inline-flex;align-items:center;justify-content:center;
    width:28px;height:28px;border:none;background:var(--brand-soft);color:var(--brand);
    border-radius:50%;cursor:pointer;font-size:14px;line-height:1;transition:.15s;}
  .spk:hover{background:var(--brand);color:#fff;}
  .spk.playing{background:var(--brand);color:#fff;}
  .otext{margin-right:auto;}
  .stem{font-size:16px;margin-bottom:10px;}
  .opt{display:flex;align-items:center;gap:10px;border:1px solid var(--line);
    border-radius:10px;padding:10px 12px;margin:8px 0;cursor:pointer;
    font-size:15px;background:var(--card);transition:border-color .15s,background .15s,box-shadow .15s;user-select:none;}
  .opt:hover{border-color:var(--brand);background:var(--brand-soft);}
  .opt.sel{border-color:var(--brand);background:var(--brand-soft);font-weight:600;}
  .opt .tick{width:22px;height:22px;border:2px solid #90a4ae;border-radius:6px;
    flex:0 0 auto;display:flex;align-items:center;justify-content:center;font-size:15px;color:#fff;}
  .opt.sel .tick{background:var(--brand);border-color:var(--brand);}
  .opt.ok{border-color:var(--ok);background:var(--ok-soft);}
  .opt.ok .tick{background:var(--ok);border-color:var(--ok);}
  .opt.no{border-color:var(--bad);background:var(--bad-soft);}
  .opt.no .tick{background:var(--bad);border-color:var(--bad);}
  .answer{font-size:13px;color:#37474f;margin-top:8px;display:none;}
  .q.done .answer{display:block;}
  .btn{display:block;width:100%;margin:22px 0 0;padding:14px;border:none;border-radius:12px;
    background:var(--brand);color:#fff;font-size:17px;font-weight:700;cursor:pointer;transition:.15s;}
  .btn:hover{background:#0d47a1;}
  .btn.sec{background:#90a4ae;margin-top:10px;}
  .btn.sec:hover{background:#78909c;}
  .result{background:var(--card);border-radius:14px;padding:16px 20px;margin-top:18px;
    border:1px solid var(--line);display:none;text-align:center;}
  .result.show{display:block;}
  .result .big{font-size:40px;font-weight:800;color:var(--brand);}
  .bar{height:10px;border-radius:6px;background:#eeeeee;overflow:hidden;margin:10px 0;}
  .bar > i{display:block;height:100%;background:var(--ok);}
  .foot{color:#9e9e9e;font-size:12px;text-align:center;margin-top:24px;}
"""

# ---------------------------------------------------------------- 引擎 JS
# ⚠ 判分逻辑是既有资产，**逐行照搬**存量壳，不要「顺手优化」。
#   存量 424 页的 grade() 语义已被 e2e_grading.js 端到端验证过
#   （真实 Chromium 点选项 → 页面自身判分 → 结果与题库答案自洽）。
#   改动任何一行都需要重跑那套验证。
ENGINE_JS = """
/* __BANK__ */;
const PER_ROUND = {{PER_ROUND}};
const quiz = document.getElementById("quiz");
let Q = [];
let seen = new Set();
let batch = 0;

const THEMES = ["auto", "light", "dark"];
const THEME_ICON = { auto: "🔄 跟随系统", light: "☀️ 明亮模式", dark: "🌙 暗黑模式" };
function applyTheme(t){
  if(t === "dark") document.documentElement.setAttribute("data-theme", "dark");
  else if(t === "light") document.documentElement.setAttribute("data-theme", "light");
  else document.documentElement.removeAttribute("data-theme");
}
function updateThemeBtn(){
  const t = localStorage.getItem("sci_theme") || "auto";
  const btn = document.getElementById("themeBtn");
  if(btn) btn.textContent = THEME_ICON[t];
}
function toggleTheme(){
  const cur = localStorage.getItem("sci_theme") || "auto";
  const next = THEMES[(THEMES.indexOf(cur) + 1) % 3];
  localStorage.setItem("sci_theme", next);
  applyTheme(next);
  updateThemeBtn();
}

function shuffle(a){
  for(let i=a.length-1;i>0;i--){
    const j=Math.floor(Math.random()*(i+1));
    [a[i],a[j]]=[a[j],a[i]];
  }
  return a;
}
function pickRound(){
  // 优先抽取从未做过的题；整库做完后才重新洗牌，保证“续测不重复刷完”
  let pool = ALL.map((_,i)=>i).filter(i=>!seen.has(i));
  if(pool.length === 0){ seen = new Set(); pool = ALL.map((_,i)=>i); }
  shuffle(pool);
  const n = Math.min(PER_ROUND, pool.length);
  const chosen = pool.slice(0, n);
  chosen.forEach(i=>seen.add(i));
  return chosen.map(i=>{ const o=Object.assign({},ALL[i]); o.pick=[]; return o; });
}
function speak(text, btn){
  if(!('speechSynthesis' in window)){
    alert('当前浏览器不支持朗读，请用 Chrome 或 Edge 打开。'); return;
  }
  try{ window.speechSynthesis.cancel(); }catch(e){}
  document.querySelectorAll('.spk.playing').forEach(function(b){b.classList.remove('playing');});
  const u=new SpeechSynthesisUtterance(String(text));
  u.lang='zh-CN'; u.rate=0.9; u.pitch=1;
  if(btn){
    btn.classList.add('playing');
    u.onend=function(){ btn.classList.remove('playing'); };
    u.onerror=function(){ btn.classList.remove('playing'); };
  }
  window.speechSynthesis.speak(u);
}
function render(){
  quiz.innerHTML="";
  Q.forEach((item,i)=>{
    const wrap=document.createElement("div");
    wrap.className="q"; wrap.id="q"+i;
    const qtop=document.createElement("div"); qtop.className="qtop";
    const badge=document.createElement("span");
    {{BADGE}}
    const qno=document.createElement("span"); qno.className="qno"; qno.textContent="第 "+(i+1)+" 题";
    const qspk=document.createElement("button"); qspk.className="spk qspk"; qspk.type="button";
    qspk.title="读题（朗读题目与选项）"; qspk.textContent="🔊";
    const full=item.q+"。"+item.o.map((o,j)=>"ABCD"[j]+"："+o).join("，")+"。"
      {{SPEAK}};
    qspk.addEventListener("click",function(){ speak(full, qspk); });
    qtop.appendChild(badge); qtop.appendChild(qno); qtop.appendChild(qspk);
    const stem=document.createElement("div"); stem.className="stem"; stem.textContent=item.q;
    wrap.appendChild(qtop); wrap.appendChild(stem);
    item.o.forEach(function(o,j){
      const opt=document.createElement("div"); opt.className="opt"; opt.id="o"+i+"_"+j;
      opt.addEventListener("click",function(){ pick(i,j); });
      const tick=document.createElement("span"); tick.className="tick"; tick.id="tk"+i+"_"+j; tick.textContent="○";
      const otext=document.createElement("span"); otext.className="otext"; otext.textContent="ABCD"[j]+". "+o;
      const spk=document.createElement("button"); spk.className="spk"; spk.type="button";
      spk.title="读出来"; spk.textContent="🔊";
      spk.addEventListener("click",function(e){ e.stopPropagation(); speak(o, spk); });
      opt.appendChild(tick); opt.appendChild(otext); opt.appendChild(spk);
      wrap.appendChild(opt);
    });
    const ans=document.createElement("div"); ans.className="answer"; ans.id="ans"+i;
    wrap.appendChild(ans);
    quiz.appendChild(wrap);
  });
  document.getElementById("batch").textContent = "第 "+batch+" 批";
}
function newRound(){
  if(window.speechSynthesis){ try{ window.speechSynthesis.cancel(); }catch(e){} }
  batch++;
  Q = pickRound();
  render();
  const sc=document.getElementById("score");
  sc.innerHTML='得分：<b>待评定</b>'; sc.classList.remove("done");
  document.getElementById("result").classList.remove("show");
  document.getElementById("reset").style.display="none";
  document.getElementById("continue").style.display="none";
  const sb=document.getElementById("submit"); sb.textContent="✅ 提交自测（自动判分）"; sb.disabled=false;
  window.scrollTo({top:0,behavior:"smooth"});
}
function pick(i,j){
  const item=Q[i];
  const el=document.getElementById("o"+i+"_"+j);
  {{PICK}}
    for(let k=0;k<item.o.length;k++){
      document.getElementById("o"+i+"_"+k).classList.remove("sel");
      document.getElementById("tk"+i+"_"+k).textContent="○";
    }
    el.classList.add("sel"); document.getElementById("tk"+i+"_"+j).textContent="✔";
    item.pick=["ABCD"[j]];
  }else{
    if(el.classList.contains("sel")){
      el.classList.remove("sel"); document.getElementById("tk"+i+"_"+j).textContent="○";
      item.pick=(item.pick||[]).filter(x=>x!=="ABCD"[j]);
    }else{
      el.classList.add("sel"); document.getElementById("tk"+i+"_"+j).textContent="✔";
      item.pick=item.pick||[]; if(!item.pick.includes("ABCD"[j])) item.pick.push("ABCD"[j]);
    }
  }
}
function grade(){
  let score=0; let answered=0;
  Q.forEach((item,i)=>{
    const sel=(item.pick||[]).slice().sort();
    const ans=item.a.slice().sort();
    const right = sel.length===ans.length && sel.every((v,k)=>v===ans[k]);
    const box=document.getElementById("q"+i);
    box.classList.add("done");
    if(sel.length>0) answered++;
    if(right){ score+=10; box.classList.add("correct"); }
    else{
      box.classList.add("wrong");
      item.a.forEach(L=>{const idx="ABCD".indexOf(L);document.getElementById("o"+i+"_"+idx).classList.add("ok");
        document.getElementById("tk"+i+"_"+idx).textContent="✔";});
      (item.pick||[]).forEach(L=>{if(!item.a.includes(L)){const idx="ABCD".indexOf(L);
        document.getElementById("o"+i+"_"+idx).classList.add("no");
        document.getElementById("tk"+i+"_"+idx).textContent="✘";}});
    }
    document.getElementById("ans"+i).innerHTML =
      {{ANSWER}}
  });
  const maxScore = Q.length * 10;
  const sc=document.getElementById("score");
  sc.innerHTML='得分：<b>'+score+'</b> / '+maxScore; sc.classList.add("done");
  document.getElementById("scoreBig").textContent=score;
  document.getElementById("barFill").style.width=(maxScore?score/maxScore*100:0)+"%";
  const msg = score>=80 ? "🎉 通过！可推进到下一节。"
            : score>=60 ? "⚠️ 部分掌握，建议再巩固一下。"
            : "❌ 未通过，需重新学习本节。";
  document.getElementById("resultText").innerHTML =
    (answered<Q.length?"（注意：有 "+(Q.length-answered)+" 题未作答）<br>":"")+msg;
  document.getElementById("result").classList.add("show");
  document.getElementById("reset").style.display="block";
  document.getElementById("continue").style.display="block";
  document.getElementById("submit").textContent="已提交 ✔";
  document.getElementById("submit").disabled=true;
  window.scrollTo({top:document.getElementById("result").offsetTop-20,behavior:"smooth"});
}
function resetAll(){
  if(window.speechSynthesis){ try{ window.speechSynthesis.cancel(); }catch(e){} }
  Q.forEach(it=>it.pick=[]);
  document.querySelectorAll(".opt").forEach(o=>{o.classList.remove("sel","ok","no");
    o.querySelector(".tick").textContent="○";});
  document.querySelectorAll(".q").forEach(q=>q.classList.remove("done","correct","wrong"));
  document.querySelectorAll(".answer").forEach(a=>a.innerHTML="");
  const sc=document.getElementById("score");sc.innerHTML='得分：<b>待评定</b>';sc.classList.remove("done");
  document.getElementById("result").classList.remove("show");
  document.getElementById("reset").style.display="none";
  document.getElementById("continue").style.display="none";
  const sb=document.getElementById("submit");sb.textContent="✅ 提交自测（自动判分）";sb.disabled=false;
  window.scrollTo({top:0,behavior:"smooth"});
}
function continueTest(){ newRound(); }
(function(){
  const d=new Date();
  const pad=n=>String(n).padStart(2,"0");
  document.getElementById("date").textContent=`${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`;
  applyTheme(localStorage.getItem("sci_theme") || "auto");
  updateThemeBtn();
  newRound();
})();
"""

# ---------------------------------------------------------------- HTML 骨架
HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{TITLE}}</title>
<style>
{{CSS}}
</style>
</head>
<body>
<div class="wrap">
  <div class="head">
    <div class="topbar">
      <h1>{{H1}}</h1>
      <button class="themebtn" id="themeBtn" onclick="toggleTheme()" title="切换主题：跟随系统 / 明亮 / 暗黑">🔄 跟随系统</button>
    </div>
    <div class="sub">{{SUB}}</div>
    <div class="meta">
      <div class="box">姓名：<b>{{STUDENT}}</b></div>
      <div class="box">日期：<b id="date">—</b></div>
      <div class="box" id="score">得分：<b>待评定</b></div>
    </div>
    <div class="bank">📚 题库共 <b>{{BANK_COUNT}}</b> 题，每次最多抽取 <b>{{PER_ROUND}}</b> 题 · <span id="batch">第 1 批</span></div>
    <div class="tip" id="broadcast">📣 今日广播：{{BROADCAST}}</div>
  </div>

  <div id="quiz"></div>

  <button class="btn" id="submit" onclick="grade()">✅ 提交自测（自动判分）</button>
  <button class="btn sec" id="reset" onclick="resetAll()" style="display:none;">🔄 重做一遍（同一批）</button>
  <button class="btn sec" id="continue" onclick="continueTest()" style="display:none;">➡️ 继续测试（换一批新题）</button>

  <div class="result" id="result">
    <div>本次自测得分</div>
    <div class="big" id="scoreBig">0</div>
    <div class="bar"><i id="barFill" style="width:0%"></i></div>
    <div id="resultText"></div>
  </div>

  <div class="foot">{{FOOT}}</div>
</div>

<script>
{{ENGINE}}
</script>
</body>
</html>
"""


def engine(has_judge: bool, per_round: int, bank_js: str) -> str:
    """渲染引擎 JS。按 has_judge 切换 4 处题型分支。"""
    js = ENGINE_JS
    js = js.replace("{{BADGE}}", _BADGE_JUDGE if has_judge else _BADGE_PLAIN)
    js = js.replace("{{SPEAK}}", _SPEAK_JUDGE if has_judge else _SPEAK_PLAIN)
    js = js.replace("{{PICK}}", _PICK_JUDGE if has_judge else _PICK_PLAIN)
    js = js.replace("{{ANSWER}}", _ANSWER_JUDGE if has_judge else _ANSWER_PLAIN)
    js = js.replace("{{PER_ROUND}}", str(per_round))
    js = js.replace("/* __BANK__ */;", bank_js, 1)
    # ⚠️ 去掉**首尾**各一个换行（不是只 lstrip）。HTML 骨架是
    #   `<script>\n{{ENGINE}}\n</script>`，两处换行各占一行；
    #   若这里保留 ENGINE_JS 自带的首行换行，<script> 后就会多出一个空行。
    return js.strip("\n")
