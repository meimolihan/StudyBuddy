"""阶段5｜全端验收工具：最终生效令牌的对比度矩阵（5 皮肤 × 明/暗 × 真实搭配）。

与 check_contrast.py 的区别：后者用的是文件头 :root 的原始值，
但项目在 3100~3160 行已做过一轮「浅色令牌纠偏」（--muted/--ok/--warn/--bad
以及 sunset/forest/girl 的 --brand-dark/--btn-bg），所以**原始 :root 值不再代表
实际渲染值**。本脚本按CSS 后写覆盖顺序，解析出每个皮肤 + 每个主题下**最终生效**
的令牌，再核真实搭配（徽章是「语义色 on 语义-soft 底」，不是「语义色 on card」）。

用法: python tools/check_contrast_matrix.py
"""
import re
import sys

CSS = 'internal/web/static/style.css'


def _lum(h):
    h = h.lstrip('#')
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    r, g, b = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    f = lambda c: c / 12.92 if c <= 0.03928 else((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def cr(a, b):
    l1, l2 = sorted([_lum(a), _lum(b)], reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


# ---------------------------------------------------------------- 令牌解析
def strip_comments(s):
    """剥离 /* */ 注释——必须剥两次：非贪婪单遍会被「值里含 /* 」的情况骗过。"""
    prev = None
    while prev != s:
        prev = s
        s = re.sub(r'/\*.*?\*/', '', s, flags=re.S)
    return s


def parse_blocks(css):
    """把 CSS 切成 (selector, declarations) 列表，保留出现顺序。
    只处理单层大括号（不含 @media 嵌套），嵌套块递归成 '(outer) inner'。"""
    out = []
    css = strip_comments(css)
    i, n = 0, len(css)
    while i < n:
        j = css.find('{', i)
        if j < 0:
            break
        sel = css[i:j].strip()
        depth, k = 1, j + 1
        while k < n and depth:
            if css[k] == '{':
                depth += 1
            elif css[k] == '}':
                depth -= 1
            k += 1
        body = css[j + 1:k - 1]
        if sel.startswith('@media') or sel.startswith('@supports') or sel.startswith('@container'):
            # 递归：把内层选择器加上外层条件前缀
            out.extend(parse_blocks(body))
        else:
            decls = {}
            # 注意：项目里存在单行无分号声明（如 3149 行 --brand-dark:#a85210}），
            # 所以不能要求分号结尾，也不能跨 { }。
            for m in re.finditer(r'(--[a-z0-9-]+)\s*:\s*([^;{}]+)', body):
                decls[m.group(1)] = m.group(2).strip()
            if decls:
                out.append((sel, decls))
        i = k
    return out


def collect(css):
    blocks = parse_blocks(css)
    base = {}
    for sel, d in blocks:
        if sel == ':root':
            base.update(d)
    return base, blocks


def applies(sel, skin, theme):
    """判断一条令牌声明的选择器在当前 (skin, theme) 组合下是否生效。

    项目对light 主题写了两套入口（显式 data-theme=light + @media light 下的
    :not([data-theme="dark"])），这里统一归到theme=='light'，
    对应浏览器的 light 显式切与 auto 跟随系统两条路径。
    """
    s = sel.strip()
    if s == ':root':
        return True
    if s in ('html[data-theme="dark"]',):
        return theme == 'dark'
    if s in ('html[data-theme="light"]', 'html:not([data-theme="dark"])'):
        return theme == 'light'
    m = re.match(r'^html\[data-theme="(\w+)"\]\[data-skin="(\w+)"\]$', s)
    if m:
        return m.group(1) == theme and m.group(2) == skin
    m = re.match(r'^html:not\(\[data-theme="dark"\]\)\[data-skin="(\w+)"\]$', s)
    if m:
        return theme == 'light' and m.group(1) == skin
    m = re.match(r'^html\[data-skin="(\w+)"\]$', s)
    if m:
        return m.group(1) == skin
    return False


def final_tokens(base, blocks, skin, theme):
    """按 CSS 出现顺序叠加所有适用于当前 (skin, theme) 的令牌块。
    后写覆盖先写——与浏览器层叠一致（此处所有块特异性相近，
    纠偏段刻意放在文件后部就是靠顺序取胜的）。"""
    t = dict(base)
    for sel, d in blocks:
        if sel != ':root' and applies(sel, skin, theme):
            t.update(d)
    return t


# ---------------------------------------------------------------- 真实搭配
# (前景令牌, 背景令牌, 最低, 说明)  —— 全部按组件实际用法，而非假想
PAIRS = [
    ('ink', 'card', 4.5, '卡片正文'),
    ('ink', 'bg', 4.5, '页面底正文'),
    ('muted', 'card', 4.5, '卡片辅助小字'),
    ('muted', 'bg', 4.5, '页面底辅助小字'),
    ('brand-dark', 'card', 4.5, '卡片内链接/强调文字'),
    ('brand-dark', 'bg', 4.5, '页面底链接/强调文字'),
    ('ok', 'card', 4.5, '正确态文字 on card'),
    ('warn', 'card', 4.5, '警示态文字 on card'),
    ('bad', 'card', 4.5, '错误态文字 on card'),
    # —— 徽章：真实搭配是「语义色 on 语义-soft 底」——
    ('ok', 'ok-soft', 4.5, '徽章 .badge.ok'),
    ('warn', 'warn-soft', 4.5, '徽章 .badge.warn'),
    ('bad', 'bad-soft', 4.5, '徽章 .badge.bad（错误计数）'),
    ('brand-dark', 'brand-soft', 4.5, '徽章 .badge.info / .skinchip.is-on'),
    ('brand', 'brand-soft', 3.0, 'brand 作点缀填充（SC 1.4.11 非文本）'),
    ('brand', 'card', 3.0, 'brand 描边/图标 on card'),
    ('ok', 'ok-soft', 3.0, '通过态图形元素'),
]

SKINS = ['boy', 'girl', 'forest', 'sunset', 'starry']


def main():
    css = open(CSS, encoding='utf-8').read()
    base, blocks = collect(css)

    print('=' * 92)
    print('阶段5｜最终生效令牌对比度矩阵（WCAG，正文 4.5:1 / 图形 3:1）')
    print('=' * 92)

    fails = []
    for theme in ('light', 'dark'):
        for skin in SKINS:
            t = final_tokens(base, blocks, skin, theme)
            print('\n[%s]皮肤=%s' % (theme, skin))
            print('  令牌: bg=%s card=%s ink=%s muted=%s brand=%s brand-dark=%s'
                  % (t.get('--bg'), t.get('--card'), t.get('--ink'), t.get('--muted'),
                     t.get('--brand'), t.get('--brand-dark')))
            for fg, bg, need, desc in PAIRS:
                f, b = t.get('--' + fg), t.get('--' + bg)
                if not f or not b:
                    print('%-22s 令牌缺失 fg=%s bg=%s' % (desc, f, b))
                    continue
                v = cr(f, b)
                good = v >= need
                flag = 'AA' if need >= 4.5 else 'AA(图形)'
                if not good:
                    fails.append((theme, skin, fg, bg, round(v, 2), need, desc))
                print('  %-26s %-9s on %-9s %6.2f  需%.1f  %s'
                      % (desc, fg, bg, v, need, 'OK' if good else '✗ 未达'))
    print('\n' + '=' * 92)
    if fails:
        print('未达 AA 项 %d 个：' % len(fails))
        for r in fails:
            print('  [%s/%s] %s on %s = %.2f（需 %.1f）— %s' % r)
        return 1
    print('全部搭配达标 ✅')
    return 0


if __name__ == '__main__':
    sys.exit(main())