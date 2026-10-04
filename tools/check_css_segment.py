"""校验本次新增 CSS 段：括号平衡 + 动画时长是否走令牌。
用法: python check_css_segment.py <before.css> <after.css>
"""
import sys

before = open(sys.argv[1], encoding='utf-8').read()
after = open(sys.argv[2], encoding='utf-8').read()

for lab, f in (('花括号', '{}'), ('圆括号', '()')):
    b = before.count(f[0]) - before.count(f[1])
    a = after.count(f[0]) - after.count(f[1])
    print('%s: 前=%d 后=%d 我引入=%d %s' % (lab, b, a, a - b, '平衡' if a == b else '⚠️不平衡'))

# 只看新增段（可能前面空白不同，用内容差集判断）
tail = after[len(before):] if after.startswith(before) else after
print('新增段行数:', len(tail.split('\n')))

# 动画时长必须走令牌，禁止裸写 .2s/.25s/0.3s
import re
bad = []
for i, line in enumerate(tail.split('\n'), 1):
    s = line.strip()
    if s.startswith('*') or s.startswith('/*'):
        continue
    if 'transition' in s or 'animation' in s:
        # 允许 var(--dur*) / var(--ease) / 复用既有 keyframes 名
        if ('var(--dur' in s or 'var(--ease' in s
                or re.search(r'animation:\s*[A-Za-z][\w-]*', s)
                or re.search(r'transition:\s*none', s)):
            continue
        bad.append((i, s))
print('新增段裸时长声明:', len(bad))
for i, s in bad:
    print('   L%d %s' % (i, s[:92]))

# 死规则自检：新增段里选择器用到的类是否在文件其他地方出现过
newsel = set(re.findall(r'\.([a-zA-Z][\w-]*)', tail))
body = after
dead = [c for c in sorted(newsel)
        if len(re.findall(r'\.' + re.escape(c) + r'(?![\w-])', body)) <= 1]
print('疑似死类（全文仅出现在新增段）:', dead if dead else '无')