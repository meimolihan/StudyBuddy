"""StudyBuddy 亮/暗主题 WCAG 对比度核算（静态解析 CSS 里的真实令牌值）。
用法: python check_contrast.py
"""
def _lum(h):
    h = h.lstrip('#')
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    r, g, b = [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def cr(a, b):
    l1, l2 = sorted([_lum(a), _lum(b)], reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


THEMES = {
    '亮色': {
        'bg': '#f4f7fb', 'card': '#ffffff', 'ink': '#1f2937', 'muted': '#6b7a8d',
        'brand': '#2f6fd0', 'line': '#e3e9f1',
        'ok': '#2e9e5b', 'warn': '#e08b00', 'bad': '#d64545',
    },
    '暗色': {
        'bg': '#0e1621', 'card': '#182231', 'ink': '#e6edf5', 'muted': '#9fb0c4',
        'brand': '#5aa2ff', 'line': '#263449',
        'ok': '#5fbf6a', 'warn': '#ffb454', 'bad': '#ff7b7b',
    },
}

# (前景令牌, 背景令牌, 最低要求, 说明)
PAIRS = [
    ('ink', 'card', 4.5, '卡片内正文'),
    ('ink', 'bg', 4.5, '页面底色上正文'),
    ('muted', 'card', 4.5, '卡片内辅助小字'),
    ('muted', 'bg', 4.5, '页面底色上辅助小字'),
    ('brand', 'card', 4.5, '卡片内品牌链接'),
    ('brand', 'bg', 4.5, '页面底色上品牌链接'),
    ('ok', 'card', 4.5, '正确态文字'),
    ('warn', 'card', 4.5, '警示态文字'),
    ('bad', 'card', 4.5, '错误态文字'),
    ('line', 'card', 1.0, '分割线（装饰性，无硬性门槛）'),
]

if __name__ == '__main__':
    print('%-6s %-10s %-10s %8s  %-22s %s' % ('主题', '前景', '背景', '对比度', '用途', '判定'))
    print('-' * 78)
    fails = 0
    for tn, c in THEMES.items():
        for fg, bg, need, desc in PAIRS:
            v = cr(c[fg], c[bg])
            ok = v >= need
            if not ok and need > 1.0:
                fails += 1
            print('%-6s %-10s %-10s %8.2f  %-22s %s'
                  % (tn, fg, bg, v, desc, 'AA 通过' if ok else '⚠️ 未达 AA'))
        print()
    print('合计未达AA 项：%d' % fails)