#!/usr/bin/env bash
# 注册页「年级 / 班级」滚轮自检。
#
# 做两件事：
#   1) 用合成事件（wheel / keydown / pointer）在真浏览器里逐个验证输入手感：
#      鼠标滚轮一格 = 走一行、连转几格就走几行、方向键逐行、拖拽按距离换行、
#      触摸板按累积像素换行、停稳后是否正好吸在整行上。
#   2) 用无头 Edge 截三张图：亮色 / 暗色 / 窄屏，肉眼确认弹窗排版与选中行居中。
#
# 用法：bash scripts/_check_picker.sh          （默认查本机 :8080 的服务）
#       BASE=http://127.0.0.1:8099 bash scripts/_check_picker.sh
set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
BASE="${BASE:-http://127.0.0.1:8080}"
TMP="$(mktemp -d)"
TMPW="$(cd "$TMP" && pwd -W)"          # Edge 只认 Windows 路径
OUT="$ROOT/verify-screenshots"
EDGE="/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
FLAGS="--headless=new --disable-gpu --hide-scrollbars --no-first-run --force-device-scale-factor=1 --user-data-dir=$TMP/edge-profile"
mkdir -p "$OUT"

if ! curl -s -f -o /dev/null "$BASE/register"; then
  echo "读不到 $BASE/register —— 请先启动服务：./dist/studybuddy.exe"
  exit 1
fi
curl -s "$BASE/register" -o "$TMP/raw.html"
echo "已抓到注册页：$(stat -c %s "$TMP/raw.html") 字节"

# ---- 把页面做成自包含（CSS / logo 内联），再注入探针脚本 ----
python - "$TMP/raw.html" "$TMP" "$ROOT" <<'PY'
import base64, os, sys

raw, tmp, root = sys.argv[1:4]
html = open(raw, encoding="utf-8").read()

css = open(os.path.join(root, "internal/web/static/style.css"), encoding="utf-8").read()
logo = open(os.path.join(root, "internal/web/static/logo.svg"), "rb").read()
logo_uri = "data:image/svg+xml;base64," + base64.b64encode(logo).decode()

html = html.replace('<link rel="stylesheet" href="/static/style.css">', "<style>\n" + css + "\n</style>")
html = html.replace('src="/static/logo.svg"', 'src="' + logo_uri + '"')

PROBE = r"""
<script>
(function () {
  var out = [];
  function wait(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }
  function fv(id) { var el = document.getElementById(id); return el ? el.value : '?'; }
  function wheelEl() { return document.getElementById('pick-wheel'); }
  function ct(id) { var el = document.getElementById(id); return el ? el.textContent : '?'; }
  function exp(label, actual, want) {
    out.push((String(actual) === String(want) ? '[OK] ' : '[!!] ') + label + ' 实测 ' + actual + '（期望 ' + want + '）');
  }
  function notch(dy) {
    var ev = new WheelEvent('wheel', { deltaY: dy, deltaMode: 0, bubbles: true, cancelable: true });
    wheelEl().dispatchEvent(ev);
    return ev.defaultPrevented;
  }
  function tap(k) {
    document.dispatchEvent(new KeyboardEvent('keydown', { key: k, bubbles: true, cancelable: true }));
  }
  // 模拟「真的用鼠标点某一行」：pointerdown → pointerup → click（少一步都跟真实操作不一致）
  function tapRow(i) {
    var w = wheelEl(), el = w.querySelectorAll('.wheel-item')[i];
    var box = el.getBoundingClientRect();
    var x = box.left + box.width / 2, y = box.top + box.height / 2;
    function pe(type) {
      return new PointerEvent(type, { pointerId: 9, pointerType: 'mouse', button: 0, buttons: 1,
        clientX: x, clientY: y, bubbles: true, cancelable: true });
    }
    w.dispatchEvent(pe('pointerdown'));
    w.dispatchEvent(pe('pointerup'));
    el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
  }
  // 按住列表向上拖 px 像素 → 应该等价于往后走 px/44 行
  function dragUp(px) {
    var w = wheelEl(), box = w.getBoundingClientRect();
    var x = box.left + box.width / 2, y = box.top + box.height / 2;
    function ev(type, cy) {
      return new PointerEvent(type, { pointerId: 7, pointerType: 'mouse', button: 0,
        buttons: 1, clientX: x, clientY: cy, bubbles: true, cancelable: true });
    }
    w.dispatchEvent(ev('pointerdown', y));
    w.dispatchEvent(ev('pointermove', y - px / 2));
    w.dispatchEvent(ev('pointermove', y - px));
    var cls = w.className;
    w.dispatchEvent(ev('pointerup', y - px));
    return cls;
  }
  // 选中行是否正好落在正中：偏差 = scrollTop - 选中行序号 × 44（期望 0）
  function skew() {
    var w = wheelEl();
    var its = w.querySelectorAll('.wheel-item');
    var on = w.querySelector('.wheel-item.is-on');
    if (!on) { return 'no-on'; }
    var i = Array.prototype.indexOf.call(its, on);
    return (w.scrollTop - i * 44).toFixed(1);
  }

  (async function () {
    // ================= A. 年级（小学一年级起步，1~6，别撞上限）=================
    document.getElementById('grade-field').click();
    await wait(400);

    // A0 诊断：一次滚轮之后「位置 / 选中值 / 补间标记」的轨迹。
    // 用来盯住最容易出的那个 bug：位置没落地、回读却用旧位置把选中行覆盖回去。
    var w = wheelEl(), traj = [];
    w.addEventListener('scroll', function () { traj.push(Math.round(w.scrollTop)); });
    function snap() {
      return 'v=' + fv('grade-value') + ' top=' + Math.round(w.scrollTop) +
             ' anim=' + (w.classList.contains('is-anim') ? 1 : 0);
    }
    notch(100);
    await wait(100); var s1 = snap();
    await wait(200); var s2 = snap();
    await wait(500); var s3 = snap();
    out.push('A0 轨迹 t100 ' + s1 + ' / t300 ' + s2 + ' / t800 ' + s3 + ' / scroll事件 ' + (traj.join(',') || '无'));
    document.getElementById('pick-cancel').click(); await wait(300);
    document.getElementById('grade-field').click(); await wait(400);

    out.push('--- A 年级滚轮 ---');
    exp('打开时年级', fv('grade-value'), 1);
    exp('打开时吸附偏差', skew(), '0.0');
    var ih = wheelEl().querySelector('.wheel-item').offsetHeight;
    out.push('样式：行高 ' + ih + 'px / 滚轮高 ' + wheelEl().getBoundingClientRect().height +
             'px / user-select ' + getComputedStyle(wheelEl()).userSelect +
             ' / snap ' + getComputedStyle(wheelEl()).scrollSnapType);
    exp('行高与脚本里的 ITEM 一致', ih, 44);

    exp('wheel 被接管（defaultPrevented）', notch(100), true);
    await wait(600);
    exp('转一格滚轮', fv('grade-value'), 2);
    exp('转一格后吸附偏差', skew(), '0.0');

    tap('ArrowDown'); await wait(600);
    exp('方向键↓一次', fv('grade-value'), 3);

    out.push('拖拽中的 class：' + dragUp(44));
    await wait(800);
    exp('向上拖 44px（≈1 行）', fv('grade-value'), 4);
    exp('拖拽后吸附偏差', skew(), '0.0');

    notch(25); notch(25); await wait(600);
    exp('触摸板累积 50px（不足一行）', fv('grade-value'), 4);
    notch(25); await wait(600);
    exp('触摸板累积到 75px', fv('grade-value'), 5);

    document.getElementById('pick-cancel').click(); await wait(300);
    exp('点「取消」回滚年级', fv('grade-value'), 1);
    exp('点「取消」回滚文案', ct('grade-text'), '一年级');

    // ================= B. 班级（0~12，空间足够，测「转几格走几行」）=================
    document.getElementById('class-field').click();
    await wait(400);
    out.push('--- B 班级滚轮 ---');
    exp('打开时班级（空串 = 不填）', fv('class-value'), '');
    exp('打开时吸附偏差', skew(), '0.0');

    notch(100); await wait(600);
    exp('转一格滚轮', fv('class-value'), 1);

    for (var i = 0; i < 3; i++) { notch(100); await wait(130); }
    await wait(800);
    exp('连转三格（一格都不该丢）', fv('class-value'), 4);
    exp('连转三格后吸附偏差', skew(), '0.0');

    tap('ArrowUp'); await wait(600);
    exp('方向键↑一次', fv('class-value'), 3);

    dragUp(88); await wait(800);
    exp('向上拖 88px（≈2 行）', fv('class-value'), 5);
    exp('拖拽后吸附偏差', skew(), '0.0');

    tapRow(0); await wait(600);
    exp('点第 1 行（不填）', fv('class-value'), '');
    tapRow(7); await wait(600);
    exp('点第 8 行', fv('class-value'), 7);
    exp('点行后吸附偏差', skew(), '0.0');

    document.getElementById('pick-ok').click(); await wait(300);
    exp('点「确定」提交班级', fv('class-value'), 7);
    exp('点「确定」提交文案', ct('class-text'), '七班');

    // ================= C. 诊断（只报告，不断言）=================
    document.getElementById('class-field').click(); await wait(400);
    out.push('--- C 诊断 ---');
    var before = w.scrollTop;
    if (w.scrollTo) { w.scrollTo({ top: 0, behavior: 'smooth' }); await wait(700); }
    var moved = Math.abs(w.scrollTop - before);
    out.push('C1 原生 scrollTo({behavior:smooth}) 位移 ' + moved + 'px' +
             (moved < 1 ? ' → 该容器上不可用，位置更新必须自己写补间（当前实现）' : ' → 可用'));
    var evCount = 0;
    w.addEventListener('scroll', function () { evCount++; });
    w.scrollTop = 0; await wait(300);
    out.push('C2 直接写 scrollTop 后：scroll 事件 ' + evCount + ' 次，选中值 ' + fv('class-value') +
             '（无头环境常不发 scroll 事件，所以「回读」类行为以拖拽路径为准，上面已覆盖）');
    document.getElementById('pick-cancel').click(); await wait(200);

    var p = document.createElement('div');
    p.id = '__probe';
    p.setAttribute('data-log', out.join(' ; '));
    document.body.appendChild(p);
  })();
})();
</script>
"""

OPEN_MODAL = r"""
<style>
/* 截图专用：关掉弹窗入场动画。无头浏览器快进虚拟时间时可能抓到动画中间帧
   （半透明、位移），看起来像「弹窗没弹出来」。线上不动这一块。 */
.sheetscrim,.sheet{animation:none !important; opacity:1 !important; transform:none !important}
</style>
<script>
setTimeout(function () { document.getElementById('grade-field').click(); }, 60);
</script>
"""

# 报告 scroll-snap 到底有没有生效（鼠标侧应为 none，触摸侧应为 y mandatory）
SNAP_PROBE = r"""
<script>
setTimeout(function () {
  var w = document.getElementById('pick-wheel');
  var d = document.createElement('div');
  d.id = '__snap';
  d.setAttribute('data-log', 'pointer:coarse=' + (matchMedia('(pointer:coarse)').matches ? 1 : 0) +
    ' hover:none=' + (matchMedia('(hover:none)').matches ? 1 : 0) +
    ' -> scroll-snap-type=' + getComputedStyle(w).scrollSnapType);
  document.body.appendChild(d);
}, 500);
</script>
"""

def write(name, body):
    open(os.path.join(tmp, name), "w", encoding="utf-8").write(body)

# 无头 Edge 的 prefers-color-scheme 是 dark，不钉住主题的话「亮色」那张其实是暗色 ——
# 亮色靠显式 data-theme="light" 关掉暗色块（CSS 里是 html:not([data-theme="light"])）。
light = html.replace('<html lang="zh-CN"', '<html lang="zh-CN" data-theme="light"', 1)
dark = html.replace('<html lang="zh-CN"', '<html lang="zh-CN" data-theme="dark"', 1)
write("probe.html", html.replace("</body>", PROBE + "</body>"))
write("light.html", light.replace("</body>", OPEN_MODAL + "</body>"))
write("dark.html", dark.replace("</body>", OPEN_MODAL + "</body>"))
write("snap.html", light.replace("</body>", OPEN_MODAL + SNAP_PROBE + "</body>"))
PY

echo
echo "== 交互探针（合成 wheel / 方向键 / 拖拽事件，真浏览器执行）=="
"$EDGE" $FLAGS --window-size=1440,900 --virtual-time-budget=40000 \
  --dump-dom "file:///$TMPW/probe.html" 2>/dev/null \
  | grep -o '<div id="__probe"[^>]*>' \
  | python -c "
import re, sys
tag = sys.stdin.read()
m = re.search(r'data-log=\"([^\"]*)\"', tag)
if not m:
    print('  探针没有返回结果（页面可能没跑完，或脚本报错）')
    sys.exit(0)
for part in m.group(1).split(' ; '):
    print('  ' + part.strip())
"

echo
echo "== 截图（无头 Edge）=="
shot() {
  "$EDGE" $FLAGS --window-size="$3" --virtual-time-budget=9000 \
    --screenshot="$OUT/$1" "file:///$TMPW/$2" >/dev/null 2>&1
  printf '  %-32s %sB\n' "$1" "$(stat -c %s "$OUT/$1" 2>/dev/null || echo 0)"
}
shot "07-滚轮弹窗-亮色.png" light.html 1440,900
shot "08-滚轮弹窗-暗色.png" dark.html 1440,900
shot "09-滚轮弹窗-窄屏.png" light.html 520,880

echo
echo "== scroll-snap 两个分支（--blink-settings 可把 hover/pointer 伪装成触摸）=="
snap() {  # $1=标签 $2=可选的 blink-settings
  local out
  out="$("$EDGE" $FLAGS --window-size=1440,900 --virtual-time-budget=7000 ${2:+--blink-settings="$2"} \
    --dump-dom "file:///$TMPW/snap.html" 2>/dev/null | grep -o 'data-log="[^"]*"' | head -1)"
  printf '  %s %s\n' "$1" "${out:-（没取到）}"
}
snap "鼠标 / 触摸板：" ""
snap "触摸屏：        " "primaryPointerType=4,availablePointerTypes=4,primaryHoverType=1,availableHoverTypes=1"

echo
echo "（临时文件在 $TMP，可自行删除）"
