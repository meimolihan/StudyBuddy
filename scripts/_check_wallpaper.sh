#!/usr/bin/env bash
# 真机自检：壁纸匹配规则是否符合预期。
#   首页（与学科无关的页面）→ 年级层通用图 …/grade4/wallpaper.webp（上下册共用一张）
#   课程页 / 自测页          → 该册学科图 → 该册通用图 → 该年级通用图 → 全局 default.webp
#
# 做法：用一份临时数据库在 8091 端口起第二个实例，教材 content/ 与壁纸 wallpapers/
# 都用项目里真实的，注册一个「小学四年级上册」学生，然后逐页打印实际命中的壁纸，
# 并顺手截几张图到 verify-screenshots/。跑完自动关掉临时实例、清理临时数据。
#
# 用法：bash scripts/_check_wallpaper.sh（需要先 go build -o dist/studybuddy.exe ./cmd/studybuddy）
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ROOTW="$(cd "$ROOT" && pwd -W 2>/dev/null || echo "$ROOT")"   # 给原生 Python 用的 Windows 路径
cd "$ROOT"
TMP="$(mktemp -d)"   # 临时库放系统临时目录，跑完不清理也不影响项目
PORT=8091
BASE="http://127.0.0.1:$PORT"

STUDYBUDDY_PORT=$PORT STUDYBUDDY_DATA="$TMP/data" STUDYBUDDY_ARCHIVE="$TMP/archive" GIN_MODE=release \
  "./dist/studybuddy.exe" > "$TMP/server.log" 2>&1 &
SRV=$!
trap 'kill $SRV 2>/dev/null' EXIT
for _ in $(seq 1 40); do curl -s -o /dev/null "$BASE/login" && break; sleep 0.3; done

CJ="$TMP/cookies.txt"
curl -s -c "$CJ" -o /dev/null -X POST "$BASE/register" \
  --data-urlencode "username=vr" --data-urlencode "name=验证同学" \
  --data-urlencode "password=vrpass123" --data-urlencode "stage=primary" \
  --data-urlencode "grade=4" --data-urlencode "volume=1" \
  --data-urlencode "class_no=3" --data-urlencode "class=四年级三班" \
  --data-urlencode "gender=male"

enc() { python -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))" "$1"; }
pick() { grep -o 'data-wallpaper="[^"]*"' | head -1 | sed 's/data-wallpaper=//'; }
V=primary/pep/grade4/volume1
G=primary/pep/grade4
CN="$V/chinese/01-自然之美/01-观潮.html"
MATH="$V/math/01-大数的认识/01-亿以内数的认识.html"
EN="$V/english/01-My classroom 我的教室/01-核心词汇.html"

echo "== 学籍：小学四年级上册 =="
printf '  %-16s %s\n' "学习主页" "$(curl -s -b "$CJ" "$BASE/study" | pick)"
printf '  %-16s %s\n' "课程页 · 语文" "$(curl -s -b "$CJ" "$BASE/lesson?key=$(enc "$CN")" | pick)"
printf '  %-16s %s\n' "自测页 · 语文" "$(curl -s -b "$CJ" "$BASE/quiz?key=$(enc "$CN")" | pick)"
printf '  %-16s %s\n' "自测页 · 数学" "$(curl -s -b "$CJ" "$BASE/quiz?key=$(enc "$MATH")" | pick)"
printf '  %-16s %s\n' "自测页 · 英语" "$(curl -s -b "$CJ" "$BASE/quiz?key=$(enc "$EN")" | pick)"

echo "== 壁纸 HTTP 可达性（首页用年级图，学科页用册别图）=="
for f in "$G/wallpaper.webp" "$V/g4-v1-chinese.webp" "$V/g4-v1-math.webp"; do
  printf '  %-46s %s\n' "$f" \
    "$(curl -s -o /dev/null -w '%{http_code} %{content_type} %{size_download}B' "$BASE/wallpapers/$f")"
done

echo "== 设置面板里的壁纸一行（首页 / 语文自测页）=="
# 开关行只显示「背景壁纸已开启 / 已关闭」，命中目录挪进了整行的 title，所以这里读 title。
label() {
  curl -s -b "$CJ" "$BASE$1" | python -c "
import re, sys
h = sys.stdin.read()
t = re.search(r'<span class=\"setrow-t\">背景壁纸([^<]*)</span>', h)
d = re.search(r'<a class=\"setrow\"[^>]*title=\"([^\"]*)\"', h)
print('  背景壁纸%s ｜ 悬停提示：%s' % (t.group(1).strip() if t else '?', d.group(1) if d else '（无）'))
"
}
label "/study"
label "/quiz?key=$(enc "$CN")"

echo "== 背景壁纸开关：关掉 → 再打开（回归：关掉后开关行不能消失）=="
wprow() {
  curl -s -b "$CJ" "$BASE/study" | python -c "
import re, sys
h = sys.stdin.read()
t = re.search(r'背景壁纸([^<]*)</span>', h)
m = re.search(r'href=\"(/wallpaper/toggle[^\"]*)\"', h)
print('  背景壁纸%s ｜ 开关 → %s' % (t.group(1).strip() if t else '?',
      (m.group(1).replace('&amp;', '&') if m else '（没有开关行 → 关掉就回不来了！）')))
"
}
wprow
curl -s -b "$CJ" -o /dev/null "$BASE/wallpaper/toggle?on=0&back=%2Fstudy"; wprow
curl -s -b "$CJ" -o /dev/null "$BASE/wallpaper/toggle?on=1&back=%2Fstudy"; wprow

# 下册学生首页应当与上册共用同一张年级图（下册教材还没导入，只看首页即可）。
# 已有用户后注册要邀请码，所以这里由管理员直接建号，再用新账号登录拿会话。
CJ2="$TMP/cookies2.txt"
curl -s -b "$CJ" -o /dev/null -X POST "$BASE/admin/user/create" \
  --data-urlencode "username=vr2" --data-urlencode "name=下册同学" \
  --data-urlencode "password=vrpass123" --data-urlencode "stage=primary" \
  --data-urlencode "grade=4" --data-urlencode "volume=2" \
  --data-urlencode "class_no=3" --data-urlencode "class=四年级三班" \
  --data-urlencode "gender=female"
curl -s -c "$CJ2" -o /dev/null -X POST "$BASE/login" \
  --data-urlencode "username=vr2" --data-urlencode "password=vrpass123"
echo "== 学籍：小学四年级下册 =="
printf '  %-16s %s\n' "学习主页" "$(curl -s -b "$CJ2" "$BASE/study" | pick)"

echo "== 截图（无头 Edge，Dark 配色）=="
# 把页面另存成本地自包含文件：样式表与壁纸都内联进文档，剩下的站内引用改绝对地址。
# 这样截图完全不依赖临时实例还活着，也不会因为 headless 抓拍的时机差异而漏掉大背景图
# （学科图约 240KB，走「网络 + virtual-time-budget」时偶发截不到）。
EDGE="/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
OUT="$ROOT/verify-screenshots"
mkdir -p "$OUT"
curl -s "$BASE/static/style.css" -o "$TMP/style.css"

save() { # $1=站内路径 $2=输出 html
  curl -s -b "$CJ" "$BASE$1" -o "$2.raw"
  python - "$2.raw" "$2" "$TMP/style.css" "$ROOTW" "$BASE" <<'PY'
import base64, os, re, sys
src, out, css_path, root, base = sys.argv[1:6]
with open(src, encoding="utf-8") as f:
    html = f.read()
with open(css_path, encoding="utf-8") as f:
    css = f.read()

def data_uri(p):
    with open(p, "rb") as f:
        return base64.b64encode(f.read()).decode()

def inline_wp(m):
    p = os.path.join(root, "wallpapers", m.group(1).replace("/", os.sep))
    return 'src="data:image/webp;base64,' + data_uri(p) + '"' if os.path.isfile(p) else m.group(0)

html = re.sub(r'src="/wallpapers/([^"]+)"', inline_wp, html)
# 关键：线上用 decoding="async" 是对的（不挡首屏），但无头截图配合 virtual-time-budget 时
# 大图常常还没解码完就抓拍，截出来背景是空的。截图副本改成同步解码，结果才稳定可复现。
html = html.replace('decoding="async"', 'decoding="sync"')
html = html.replace('<link rel="stylesheet" href="/static/style.css">', "<style>\n" + css + "\n</style>")
logo = os.path.join(root, "internal", "web", "static", "logo.svg")
if os.path.isfile(logo):
    html = html.replace('src="/static/logo.svg"', 'src="data:image/svg+xml;base64,' + data_uri(logo) + '"')
html = html.replace('"/static/', '"' + base + '/static/').replace("'/static/", "'" + base + '/static/')
with open(out, "w", encoding="utf-8") as f:
    f.write(html)
PY
}
shot() {
  "$EDGE" --headless=new --disable-gpu --hide-scrollbars --no-first-run --user-data-dir="$TMP/edge-profile" \
    --window-size=1440,900 --virtual-time-budget=8000 \
    --screenshot="$OUT/$1" "file:///$2" >/dev/null 2>&1
  printf '  %-34s %sB\n' "$1" "$(stat -c %s "$OUT/$1" 2>/dev/null || echo 0)"
}
save "/study" "$TMP/study.html"
save "/quiz?key=$(enc "$CN")" "$TMP/quiz-chinese.html"
save "/quiz?key=$(enc "$MATH")" "$TMP/quiz-math.html"
shot "01-学习主页-年级通用图.png" "$TMP/study.html"
shot "02-语文自测页-学科图.png" "$TMP/quiz-chinese.html"
shot "03-数学自测页-学科图.png" "$TMP/quiz-math.html"

echo "（临时实例已关闭；临时数据在 $TMP，可自行删除）"
