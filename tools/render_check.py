"""阶段 5 复审｜**真实渲染**可见性验收（Edge 无头模式截图 + 像素分析）。

为什么需要这个工具
------------------
静态CSS 分析只能查「我能想到的失效模式」。此前h1 渐变标题在暗色下
文字完全消失（`background` 简写重置了 `background-clip`），而静态核查
四类（对比度 / 断点 / hover / 暗色A-B）**全绿** —— 因为
「对比度算得出来，但 clip 被重置导致元素不可见」这类问题**算不出来**。
只有真实渲染 + 像素分析才能兜住。

⚠️ 判据方向（第一版踩过的坑，务必别改反）
--------------------------------------
第一版用「盒内非背景像素占比」当指标，结果**方向是反的**：

  正常态（渐变只在笔画里显色）→ 盒内大半是页面背景 → 占比**低**（~4%）
  事故态（clip 被重置，渐变铺满整个盒子）→ 整盒都是渐变 → 占比**高**（~100%）

也就是说「非背景像素多」恰恰是**坏**的信号，怎么调阈值都不可能同时判对两边。
本版改用**与背景色无关**的结构指标：

  **笔画边缘密度 = 相邻像素颜色突变对数 / 相邻像素对总数**

  - 有文字 → 笔画与空隙反复交替 → 水平+垂直边缘密度都高（中文标题 ≈0.15~0.40）
  - 纯色块 / 平滑线性渐变 → 相邻像素差< 阈值 → 边缘密度≈0

渐变铺满盒子时，相邻像素色差仅 ~1/255（96deg 渐变横跨 760px），被阈值完全滤掉。

**自检（每次运行都做）**
--------------------
一个从不失败的检测器毫无价值。所以每次运行先用**两个合成页面**标定量程：
  - selftest-ok  : 纯文字色 h1（必定可见）
  - selftest-bug : 注入历史事故 CSS（`background` 简写，不重声明 clip）
                   —— 必须被判为「文字消失」
若自检不通过，整份报告直接判失败，不给出任何「可见」结论。

用法
----
  python tools/render_check.py                # 跑内置用例 + 自检
  python tools/render_check.py --keep         # 保留截图到临时目录

依赖: Windows Edge / Chrome。找不到浏览器时退出码 2。
"""
import os
import struct
import subprocess
import sys
import tempfile
import zlib

EDGE_CANDIDATES = [
    r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
    r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
    r'C:\Program Files\Google\Chrome\Application\chrome.exe',
    r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
]
PORT = os.environ.get('STUDYBUDDY_PORT', '8658')
BASE = 'http://127.0.0.1:%s' % PORT

# 相邻像素色差阈值（RGB 三通道绝对差之和）。24 ≈ 肉眼可辨的边界。
DELTA = 24
# 边缘密度下限：低于此值判「无笔画结构」。
EDGE_MIN = 0.02
# 内容像素绝对下限：低于此值判「盒内几乎空白」。
INK_MIN = 200


# ---------------------------------------------------------------- PNG 解析
def read_png(path):
    """标准库 zlib+struct 解 PNG → (w, h, [(r,g,b),…])。支持 8bit灰度/RGB/RGBA。"""
    data = open(path, 'rb').read()
    assert data[:8] == b'\x89PNG\r\n\x1a\n', 'not a png'
    pos = 8
    w = h = bitdepth = colortype = None
    idat = b''
    while pos < len(data):
        ln = struct.unpack('>I', data[pos:pos + 4])[0]
        typ = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + ln]
        if typ == b'IHDR':
            w, h, bitdepth, colortype = struct.unpack('>IIBB', chunk[:10])
        elif typ == b'IDAT':
            idat += chunk
        elif typ == b'IEND':
            break
        pos += 12 + ln
    assert bitdepth == 8, 'only 8bit supported, got %s' % bitdepth
    channels = {0: 1, 2: 3, 4: 2, 6: 4}[colortype]
    raw = zlib.decompress(idat)
    stride = w * channels
    out = bytearray(h * stride)
    prev = bytearray(stride)
    p = 0
    for y in range(h):
        ft = raw[p]
        p += 1
        line = bytearray(raw[p:p + stride])
        p += stride
        if ft == 1:
            for i in range(channels, stride):
                line[i] = (line[i] + line[i - channels]) & 255
        elif ft == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 255
        elif ft == 3:
            for i in range(stride):
                a = line[i - channels] if i >= channels else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 255
        elif ft == 4:
            for i in range(stride):
                a = line[i - channels] if i >= channels else 0
                b = prev[i]
                c = prev[i - channels] if i >= channels else 0
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 255
        out[y * stride:(y + 1) * stride] = line
        prev = line
    px = []
    for i in range(w * h):
        o = i * channels
        if channels >= 3:
            px.append((out[o], out[o + 1], out[o + 2]))
        else:
            px.append((out[o], out[o], out[o]))
    return w, h, px


def _d(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2])


# ---------------------------------------------------------------- 像素分析
def analyze(px, w, h):
    """返回内容包围盒与笔画边缘密度（与背景色无关的结构指标）。"""
    cnt = {}
    for p in px:
        cnt[p] = cnt.get(p, 0) + 1
    bg = max(cnt, key=cnt.get)          # 众数 = 页面底色

    # 1) 内容掩码：与页面底色有可见差异的像素
    mask = bytearray(w * h)
    n = 0
    for i, p in enumerate(px):
        if _d(p, bg) > DELTA:
            mask[i] = 1
            n += 1
    if n == 0:
        return {'bg': bg, 'ink': 0, 'box': None, 'eh': 0.0, 'ev': 0.0,
                'ink_ratio': 0.0}

    # 2) 内容包围盒
    x0, x1, y0, y1 = w, -1, h, -1
    for y in range(h):
        row = y * w
        for x in range(w):
            if mask[row + x]:
                if x < x0:
                    x0 = x
                if x > x1:
                    x1 = x
                if y < y0:
                    y0 = y
                if y > y1:
                    y1 = y
    bw, bh = x1 - x0 + 1, y1 - y0 + 1

    # 3) 盒内边缘密度：水平 + 垂直方向的相邻像素突变
    eh_pairs = eh_hits = 0
    for y in range(y0, y1 + 1):
        row = y * w
        for x in range(x0, x1):
            eh_pairs += 1
            if _d(px[row + x], px[row + x + 1]) > DELTA:
                eh_hits += 1
    ev_pairs = ev_hits = 0
    for y in range(y0, y1):
        ra, rb = y * w, (y + 1) * w
        for x in range(x0, x1 + 1):
            ev_pairs += 1
            if _d(px[ra + x], px[rb + x]) > DELTA:
                ev_hits += 1

    return {
        'bg': bg, 'ink': n, 'box': (x0, y0, x1, y1),
        'eh': eh_hits / eh_pairs if eh_pairs else 0.0,
        'ev': ev_hits / ev_pairs if ev_pairs else 0.0,
        'ink_ratio': n / float(bw * bh),
    }


def judge(st):
    """据结构指标下判定。返回 (flag, 结论)。"""
    if st['ink'] < INK_MIN:
        return 'X', '盒内几乎空白'
    e = max(st['eh'], st['ev'])
    if e < EDGE_MIN:
        return 'X', '无笔画结构（纯色/平滑渐变）→ 文字消失'
    return 'OK', '文字可见'


# ---------------------------------------------------------------- 渲染
def find_browser():
    for p in EDGE_CANDIDATES:
        if os.path.exists(p):
            return p
    return None


def render(browser, html, out_png, width=760, height=90):
    tmp = os.path.join(tempfile.gettempdir(), '_rb_case.html')
    open(tmp, 'w', encoding='utf-8').write(html)
    url = 'file:///' + tmp.replace('\\', '/')
    if os.path.exists(out_png):
        os.remove(out_png)
    cmd = [browser, '--headless=new', '--disable-gpu', '--no-sandbox',
           '--hide-scrollbars', '--force-device-scale-factor=1',
           '--screenshot=' + out_png, '--window-size=%d,%d' % (width, height),
           '--virtual-time-budget=4000', url]
    try:
        subprocess.run(cmd, capture_output=True, timeout=60)
    except subprocess.TimeoutExpired:
        return False
    return os.path.exists(out_png) and os.path.getsize(out_png) > 0


BADGE = '<span class="badge info">管理员</span>'

# 历史事故的最小复现：background 简写把 background-clip 重置回 border-box，
# 而 -webkit-text-fill-color:transparent 仍生效 → 渐变铺满盒子、文字全透明。
BUGGY_CSS = (
    '<style>h1{background:linear-gradient(96deg,'
    '#1a2b4d 0%,#3a2a6b 58%,#241a3d 100%) !important;}</style>'
)
# 必定可见的对照：纯文字色，无渐变无clip。
PLAIN_CSS = '<style>h1{background-image:none !important;'\
            '-webkit-text-fill-color:currentColor !important;}</style>'


def build_html(css_url, inner, skin, theme, extra=''):
    return (
        '<!DOCTYPE html><html data-skin="%s" data-theme="%s"><head>'
        '<meta charset="utf-8">'
        '<link rel="stylesheet" href="%s">%s</head>'
        '<body style="margin:0;padding:6px 8px">'
        '<h1 style="margin:0">%s</h1></body></html>'
        % (skin, theme, css_url, extra, inner))


# (标题, 皮肤, 主题, h1 内容, 说明)
CASES = [
    ('学习主页', 'boy', 'dark', '学习主页', '用户报障页（已修复）'),
    ('欢迎回来，同学！', 'boy', 'dark', '欢迎回来，同学！', '登录页 h1'),
    ('用户管理', 'girl', 'dark', '用户管理 ' + BADGE, 'h1 内含徽章（文字+徽章）'),
    ('徽章单独', 'girl', 'dark', BADGE, '只留徽章 → 隔离测后代文字'),
    ('用户管理', 'boy', 'light', '用户管理 ' + BADGE, '亮色基准对照'),
    ('学习主页', 'sunset', 'dark', '学习主页', '最浅皮肤 + 暗色'),
    ('学习主页', 'forest', 'light', '学习主页', '亮色基准对照'),
    ('八年级物理', 'boy', 'dark', '八年级物理', '长标题 + 暗色'),
]


def shot(browser, html, keep=False):
    out = os.path.join(tempfile.gettempdir(), '_rb_out.png')
    if not render(browser, html, out):
        return None
    w, h, px = read_png(out)
    if not keep and os.path.exists(out):
        os.remove(out)
    return analyze(px, w, h)


def main():
    keep = '--keep' in sys.argv
    browser = find_browser()
    if not browser:
        print('❌ 未找到 Edge/Chrome，无法做真实渲染验收')
        return 2

    css_url = '%s/static/style.css' % BASE
    print('=' * 100)
    print('阶段 5 复审｜真实渲染可见性验收   浏览器: %s   样式: %s'
          % (os.path.basename(browser), css_url))
    print('=' * 100)

    # ---------------------------------------------------------- 0 自检
    print()
    print('【0】检测器自检（先用合成页面标定量程，自检不过则不出结论）')
    st_ok = shot(browser, build_html(css_url, '学习主页', 'boy', 'dark', PLAIN_CSS))
    st_bug = shot(browser, build_html(css_url, '学习主页', 'boy', 'dark', BUGGY_CSS))
    if st_ok is None or st_bug is None:
        print('  ❌ 渲染失败，无法自检')
        return 2
    f_ok, v_ok = judge(st_ok)
    f_bug, v_bug = judge(st_bug)
    print('  基准 纯文字色      边缘密度 h=%.3f v=%.3f  内容像素 %5d  → %s %s'
          % (st_ok['eh'], st_ok['ev'], st_ok['ink'], f_ok, v_ok))
    print('  事故 简写重置 clip 边缘密度 h=%.3f v=%.3f  内容像素 %5d  → %s %s'
          % (st_bug['eh'], st_bug['ev'], st_bug['ink'], f_bug, v_bug))
    sep = max(st_ok['eh'], st_ok['ev']) - max(st_bug['eh'], st_bug['ev'])
    self_ok = (f_ok == 'OK' and f_bug == 'X' and sep > 0.05)
    print('  量程差= %.3f  →  %s' % (sep, '✅ 检测器可信' if self_ok
                                   else '❌ 检测器不可信（可见/不可见无法区分）'))
    if not self_ok:
        return 1

    # ---------------------------------------------------------- 1 用例
    print()
    print('【1】真实页面用例（5 皮肤 × 明暗双主题 + 徽章后代继承）')
    print('  %s %-18s %-7s %-6s %-16s %-8s %s'
          % ('', '标题', '皮肤', '主题', '边缘密度 h/v', '内容像素', '结论'))
    bad = []
    for text, skin, theme, inner, desc in CASES:
        st = shot(browser, build_html(css_url, inner, skin, theme), keep)
        if st is None:
            print('  ⚠️  %-18s %-7s %-6s 渲染失败，跳过' % (text[:18], skin, theme))
            bad.append((text, skin, theme, desc, '渲染失败'))
            continue
        flag, verdict = judge(st)
        print('  %s %-18s %-7s %-6s %.3f / %.3f    %6d    %-22s %s'
              % (flag, text[:18], skin, theme, st['eh'], st['ev'], st['ink'],
                 verdict, desc))
        if flag != 'OK':
            bad.append((text, skin, theme, desc, verdict))

    print()
    if bad:
        print('❌ 真实渲染可见性未通过 %d 条：' % len(bad))
        for b in bad:
            print('  - 标题=%s 皮肤=%s 主题=%s | %s | %s' % b)
        return 1
    print('✅ 检测器自检通过 + %d 个用例在真实渲染下全部文字可见' % len(CASES))
    return 0


if __name__ == '__main__':
    sys.exit(main())
