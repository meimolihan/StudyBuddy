#!/usr/bin/env bash
# 顶栏自检：把「设置」面板在 亮色 / 暗色 / 窄屏 三种情况下截图，并量出关键几何与颜色；
# 另外多截一组「背景壁纸已关闭」的，用来核对关掉后开关行还在、并且指向「开启」。
#
# 做法：用临时数据库在 8092 端口起第二个实例（教材与壁纸都用真实的），注册一个
# 「小学四年级上册」学生，把 /study 另存为自包含 HTML（CSS、logo、壁纸全部内联），
# 再手工把 <details class="setpick"> 标成 open —— 无头浏览器没法点，只能免点击展开。
# 这样截图不依赖服务存活，也不受抓拍时机影响。
#
# 用法：bash scripts/_shot_topbar.sh
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ROOTW="$(cd "$ROOT" && pwd -W 2>/dev/null || echo "$ROOT")"
cd "$ROOT"
TMP="$(mktemp -d)"
PORT=8092
BASE="http://127.0.0.1:$PORT"

STUDYBUDDY_PORT=$PORT STUDYBUDDY_DATA="$TMP/data" STUDYBUDDY_ARCHIVE="$TMP/archive" GIN_MODE=release \
  "./dist/studybuddy.exe" > "$TMP/server.log" 2>&1 &
SRV=$!
trap 'kill $SRV 2>/dev/null' EXIT
for _ in $(seq 1 40); do curl -s -o /dev/null "$BASE/login" && break; sleep 0.3; done

CJ="$TMP/cookies.txt"
curl -s -c "$CJ" -o /dev/null -X POST "$BASE/register" \
  --data-urlencode "username=vtop" --data-urlencode "name=郭奕凡" \
  --data-urlencode "password=vtoppass123" --data-urlencode "stage=primary" \
  --data-urlencode "grade=4" --data-urlencode "volume=1" \
  --data-urlencode "class_no=3" --data-urlencode "class=四年级三班" \
  --data-urlencode "gender=male"

# 另存两份页面：壁纸开着（默认）与壁纸已关闭。
# 后者是回归用例：当年关掉后整行被换成「未匹配」，开关就再也点不回来了。
curl -s -b "$CJ" "$BASE/study" -o "$TMP/study.raw"
curl -s -b "$CJ" -o /dev/null "$BASE/wallpaper/toggle?on=0&back=%2Fstudy"
curl -s -b "$CJ" "$BASE/study" -o "$TMP/study-off.raw"
curl -s -b "$CJ" -o /dev/null "$BASE/wallpaper/toggle?on=1&back=%2Fstudy"
curl -s "$BASE/static/style.css" -o "$TMP/style.css"
python - "$TMP" "$ROOTW" <<'PY'
import base64, os, re, sys
tmp, root = sys.argv[1:3]
css = open(os.path.join(tmp, "style.css"), encoding="utf-8").read()

PROBE = """
<div id="__probe"></div>
<script>
(function () {
  var p = document.getElementById('__probe');
  var pick = document.querySelector('.setpick > summary');
  var panel = document.querySelector('.setpanel');
  var pr = pick.getBoundingClientRect(), ar = panel.getBoundingClientRect();
  function g(sel, prop) {
    var n = document.querySelector(sel);
    return n ? getComputedStyle(n)[prop] : 'n/a';
  }
  var wp = document.querySelector('.setrow');
  var wpT = document.querySelector('.setrow-t');
  p.setAttribute('data-wp', [wp ? (wp.getAttribute('href') || '（静态行，没有链接）') : '（没有这一行）',
                             wpT ? wpT.textContent : 'n/a',
                             wp && wp.querySelector('.sw') ? wp.querySelector('.sw').className : 'n/a',
                             wp ? (wp.querySelector('.setrow-d') ? '有副标题' : '无副标题') : 'n/a',
                             wp ? (wp.getAttribute('title') || '（无悬停提示）') : 'n/a'].join('|'));
  p.setAttribute('data-pick', [pr.left, pr.top, pr.right, pr.bottom].map(Math.round).join(','));
  p.setAttribute('data-panel', [ar.left, ar.top, ar.right, ar.bottom].map(Math.round).join(','));
  p.setAttribute('data-vw', window.innerWidth);
  p.setAttribute('data-vh', window.innerHeight);
  p.setAttribute('data-panel-css', [getComputedStyle(panel).position, getComputedStyle(panel).zIndex,
                                    getComputedStyle(panel).backgroundColor, getComputedStyle(panel).overflowY].join('|'));
  p.setAttribute('data-pick-css', [getComputedStyle(pick).backgroundColor, getComputedStyle(pick).color,
                                   getComputedStyle(pick).overflow, getComputedStyle(pick, '::before').content].join('|'));
  p.setAttribute('data-ink', [g('.skinlb', 'color'), g('.setrow-t', 'color'), g('.setrow-d', 'color'),
                              g('.setsec-h', 'color'), g('.setpanel-t', 'color')].join('|'));
  p.setAttribute('data-nav', [g('.tnav.is-on', 'backgroundColor'), g('.tnav.is-on', 'fontWeight'),
                              g('.avatar', 'color')].join('|'));
  p.setAttribute('data-bar', [getComputedStyle(document.querySelector('.topbar'), '::before').backgroundImage.length,
                              getComputedStyle(document.querySelector('.topbar'), '::after').height].join('|'));
  p.setAttribute('data-count', [document.querySelectorAll('.skinchip').length,
                                document.querySelectorAll('.skinchip.is-on').length,
                                document.querySelectorAll('.setrow').length].join('|'));
  p.setAttribute('data-scroll', panel.scrollHeight + '|' + panel.clientHeight);
})();
</script>
"""

def data_uri(p):
    return base64.b64encode(open(p, "rb").read()).decode()

def inline_wp(m):
    p = os.path.join(root, "wallpapers", m.group(1).replace("/", os.sep))
    return 'src="data:image/webp;base64,' + data_uri(p) + '"' if os.path.isfile(p) else m.group(0)

def prep(src_name, out_prefix):
    html = open(os.path.join(tmp, src_name), encoding="utf-8").read()
    html = re.sub(r'src="/wallpapers/([^"]+)"', inline_wp, html)
    html = html.replace('decoding="async"', 'decoding="sync"')  # 见 _check_wallpaper.sh 的说明
    html = html.replace('<link rel="stylesheet" href="/static/style.css">', "<style>\n" + css + "\n</style>")
    logo = os.path.join(root, "internal", "web", "static", "logo.svg")
    if os.path.isfile(logo):
        html = html.replace('src="/static/logo.svg"', 'src="data:image/svg+xml;base64,' + data_uri(logo) + '"')
    html = html.replace("</body>", PROBE + "</body>")
    # 无头浏览器点不了，直接展开：把首个 details 标成 open。
    html = html.replace('<details class="setpick"', '<details class="setpick" open', 1)
    # 明暗必须显式钉住：无头 Edge 的 prefers-color-scheme 跟着系统走（这里实测是 dark），
    # 不写死的话「亮色」那张也会是暗色页面。data-theme 由 CSS 的 B 段接管，优先级高于媒体查询。
    light = html.replace('<html lang="zh-CN"', '<html lang="zh-CN" data-theme="light"', 1)
    open(os.path.join(tmp, out_prefix + "-light.html"), "w", encoding="utf-8").write(light)
    dark = html.replace('<html lang="zh-CN"', '<html lang="zh-CN" data-theme="dark"', 1)
    open(os.path.join(tmp, out_prefix + "-dark.html"), "w", encoding="utf-8").write(dark)

prep("study.raw", "on")
prep("study-off.raw", "off")
PY

EDGE="/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
OUT="$ROOT/verify-screenshots"
mkdir -p "$OUT"
# 两个踩过的坑：
# 1) Windows 的窗口有最小宽度（实测 ~516px），--window-size=430 会被抬到 516，
#    而 --screenshot 出来的图仍是 430 宽 —— 等于把 516 宽的排版裁掉右边一截，
#    看着像「面板溢出屏幕了」。所以窄屏一律用 ≥ 520 的宽度，并靠探针读 innerWidth 核对。
# 2) 布局视口 ≈ 窗口尺寸 − 24（左右边框）− 92（标题栏等），不是等于。
# --force-device-scale-factor=1 把 DPR 钉成 1，免得高分屏上比例又变一套。
# --user-data-dir 指向临时目录，否则 Edge 会把 verify-scratch/ 落在项目根目录。
FLAGS="--headless=new --disable-gpu --hide-scrollbars --no-first-run --force-device-scale-factor=1 --user-data-dir=$TMP/edge-profile"
shot() { # $1=输出名 $2=html 文件名 $3=窗口尺寸
  "$EDGE" $FLAGS --window-size="$3" --virtual-time-budget=8000 \
    --screenshot="$OUT/$1" "file:///$TMP/$2" >/dev/null 2>&1
  printf '  %-30s %sB\n' "$1" "$(stat -c %s "$OUT/$1" 2>/dev/null || echo 0)"
}
shot "04-顶栏设置面板-亮色.png" on-light.html 1440,760
shot "05-顶栏设置面板-暗色.png" on-dark.html 1440,760
shot "06-顶栏设置面板-窄屏.png" on-light.html 520,880
shot "10-设置面板-壁纸已关闭-亮色.png" off-light.html 1440,760
shot "11-设置面板-壁纸已关闭-暗色.png" off-dark.html 1440,760

probe() { # $1=html 文件名 $2=标签 $3=窗口尺寸
  echo "== 几何与颜色探针（$2，$3）=="
  "$EDGE" $FLAGS --window-size="$3" --virtual-time-budget=8000 \
    --dump-dom "file:///$TMP/$1" 2>/dev/null \
    | grep -o '<div id="__probe"[^>]*>' \
    | python -c "
import re, sys
tag = sys.stdin.read()
d = dict(re.findall(r'data-([a-z-]+)=\"([^\"]*)\"', tag))
vw, vh = int(d.get('vw', 0)), int(d.get('vh', 0))
pick = [int(x) for x in d.get('pick', '0,0,0,0').split(',')]
panel = [int(x) for x in d.get('panel', '0,0,0,0').split(',')]
print('  视口            %d × %d' % (vw, vh))
print('  设置按钮        left=%d top=%d right=%d bottom=%d' % tuple(pick))
print('  面板            left=%d top=%d right=%d bottom=%d' % tuple(panel))
print('  完全在视口内    %s' % ('是' if panel[0] >= 0 and panel[2] <= vw and panel[3] <= vh else '否 ← 有问题'))
print('  挂在按钮正下方  %s（面板顶 %d ≥ 按钮底 %d）' % ('是' if panel[1] >= pick[3] else '否', panel[1], pick[3]))
print('  面板 CSS        position|z-index|底色|overflowY = %s' % d.get('panel-css'))
print('  按钮 CSS        底色|文字色|overflow|::before = %s' % d.get('pick-css'))
print('  背景壁纸行      href=%s ｜ 文案=%s ｜ 开关 class=%s ｜ %s ｜ title=%s'
      % tuple((d.get('wp', '') + '||||').split('|')[:5]))
print('  文字色          skinlb|setrow-t|setrow-d|setsec-h|setpanel-t = %s' % d.get('ink'))
print('  当前分区高亮    底色|字重 = %s  头像文字色 = %s' % (d.get('nav', '').rsplit('|', 1)[0], d.get('nav', '').rsplit('|', 1)[-1]))
print('  顶栏装饰层      ::before 背景层数(字符数) = %s  ::after 高度 = %s' % tuple(d.get('bar', '|').split('|')))
print('  元素计数        色卡数|选中数|功能行数 = %s' % d.get('count'))
sh, ch = (int(x) for x in d.get('scroll', '0|0').split('|'))
print('  内容/可视高度   %d / %d → %s' % (sh, ch, '不需要滚动' if sh <= ch + 1 else '面板内滚动 %dpx' % (sh - ch)))
"
}
probe on-light.html 亮色 1440,760
probe on-dark.html 暗色 1440,760
probe on-light.html 窄屏 520,880
# 回归重点：关掉壁纸后，这一行仍要存在、文案为「已关闭」、href 指向开启（on=1）、开关是关状态。
probe off-light.html 壁纸已关闭 1440,760
echo "（临时实例已关闭；临时数据在 $TMP，可自行删除）"
