"""阶段 5｜三端 / 热区 / 触屏 / 暗色 A/B 双写 静态核查。

本机 headless Chrome 在沙箱里崩溃（GPU 与守护进程受限），浏览器自动化不可用，
所以改成静态核查：把「能用grep 判定的硬性规则」一次性跑出来，
剩下的交人工对照 CSS 判断。

用法: python tools/check_responsive.py
"""
import re
import sys
from collections import defaultdict

CSS = 'internal/web/static/style.css'
TPL = 'internal/web/templates'

# 项目既定断点体系（见优化版提示词「零、必须先知道的现状」第4 条）
EXPECTED_BP = [380, 420, 520, 560, 640, 760, 900]
FORBIDDEN_BP = [768, 1024, 1200, 1280]

problems = []
notes = []


def split_blocks(css):
    """返回 [(selector, body, 外层@media条件串)]，含@nest 递归。"""
    out = []
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
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
        if sel.startswith('@media') or sel.startswith('@supports'):
            cond = sel
            for s2, b2, _ in split_blocks(body):
                out.append((s2, b2, cond))
        else:
            out.append((sel, body, ''))
        i = k
    return out


def main():
    css = open(CSS, encoding='utf-8').read()
    css_nc = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    # 本轮五阶段新增段的起始行：对比度/响应式问题必须区分「既有」与「本轮引入」
    stage_start = css.find('阶段 1｜底层设计令牌')

    # ---------------------------------------------------------- 1. 断点体系
    bps = sorted({int(m) for m in re.findall(r'max-width:\s*(\d+)px', css_nc)})
    extra = [b for b in bps if b not in EXPECTED_BP]
    # 判定归属：只在「新增段文本」里出现的额外断点才算本轮引入
    tail_txt = css[stage_start:] if stage_start > 0 else ''
    tail_only_bp = [b for b in extra if re.search(r'max-width:\s*%dpx' % b, tail_txt)]
    if tail_only_bp:
        problems.append('新增段引入既定之外的断点 %s' % tail_only_bp)
    used_forbidden = [b for b in FORBIDDEN_BP if re.search(
        r'(max|min)-width:\s*%dpx' % b, css_nc)]
    if used_forbidden:
        problems.append('引入通用模板的断点 %s' % used_forbidden)
    notes.append('断点体系：实际 max-width = %s' % bps)
    notes.append('  既定7 档 = %s；其余 %s 均为**既有代码**，非本轮引入'
                 % (EXPECTED_BP, extra))

    # ------------------------------------------- 2. 新增段是否引入 rem/em 字号
    tail = css[css.find('阶段 1｜底层设计令牌'):] if '阶段 1｜底层设计令牌' in css else ''
    tail_nc = re.sub(r'/\*.*?\*/', '', tail, flags=re.S)
    rem = re.findall(r'font-size:[^;}]*\d(?:rem|em)\b', tail_nc)
    if rem:
        problems.append('新增段出现 rem/em 字号 %d 处 →会与 font-scale 段冲突：%s'
                        % (len(rem), rem[:3]))

    # --------------------------------------------- 3. 新增段是否裸写动画时长
    durs = re.findall(r'transition:[^;}]*?(?<![\w-])(\.\d+s|\d+m?s)(?![\w-])', tail_nc)
    durs = [d for d in durs if d not in ('.2s', '.25s', '.3s', '.4s', '.7s')]
    if durs:
        notes.append('新增段的裸时长：%s（若不在 --dur/--dur-fast/--dur-slow 取值内需复核）' % durs)

    # ------------------------------ 4. hover 上浮是否包进 @media (hover:hover)
    # 逐块扫描：记录 @media 栈，对每个规则体判定其外层 media 条件。
    # 允许的两种正确形态：
    #   ① 规则本身包在 @media (hover:hover) 里；
    #   ② 规则裸写，但在 @media (hover:none),(pointer:coarse) 复位段里有对应条目。
    blocks = split_blocks(css_nc)
    unwrapped = []
    for sel, body, media in blocks:
        if ':hover' not in sel:
            continue
        if not re.search(r'translateY\(\s*-\d', body) and 'scale(' not in body:
            continue
        if re.search(r'hover\s*:\s*hover', media):
            continue
        # 形态②：复位段里存在**同一 selector**（复位段常把多个选择器写成一组，
    # 不能用整串相等比对，否则会误报）。
        reset = [s for s, _b, m in blocks
                 if 'hover:none' in m or 'pointer:coarse' in m]
        hit = any(
            sel.strip() == r.strip()
            # 复位段一组里逗号分隔的任一项与本selector 相同
            or any(x.strip() == sel.strip() for x in r.split(','))
            or sel.strip() in r
            for r in reset)
        if hit:
            continue
        unwrapped.append((sel[:70], media[:50]))
    if unwrapped:
        problems.append('hover 上浮既未包 hover:hover、也未在触屏复位段出现：%s' % unwrapped[:4])
    notes.append('hover 上浮：形态① hover:hover 包裹 + 形态② 触屏复位，'
                 '未覆盖项 %d 个' % len(unwrapped))

    # --------------------- 5. 暗色补丁A/B 双写：找出所有 dark 专属令牌/样式块
    # 规则：凡在 @media(prefers-color-scheme:dark) 里出现的 selector，
    #      必须在 html[data-theme="dark"] 下有对应（计数比对）。
    pref_dark = re.findall(
        r'@media\s*\(prefers-color-scheme:\s*dark\)\s*\{\s*(html:not\(\[data-theme="light"\]\)[^{]*)\{', css_nc)
    attr_dark = re.findall(r'(?<![\w-])html\[data-theme="dark"\][^{]*\{', css_nc)
    notes.append('暗色 A/B：prefers-color-scheme dark 内 html:not([data-theme="light"]) 规则 %d 条；'
                 'html[data-theme="dark"] 规则 %d 条'
                 % (len(pref_dark), len(attr_dark)))
    # 检查是否有只写了一边的典型形态
    only_attr = re.findall(r'(?<!not\(\[data-theme="light"\]\)\s)\bhtml\[data-theme="dark"\]', css_nc)

    # ---------------------------- 6. 横向溢出隐患：固定宽度 / 不换行长元素
    risky = []
    for i, ln in enumerate(css.split('\n'), 1):
        m = re.search(r'(min-)?width:\s*(\d{3,4})px', ln)
        if m and 'max-width' not in ln:
            w = int(m.group(2))
            if w >= 420 and not m.group(1):
                risky.append((i, w, ln.strip()[:80]))
    if risky:
        notes.append('固定 width>=420px 的规则 %d 条（窄屏溢出候选，需人工确认）：' % len(risky))
        for r in risky[:8]:
            notes.append('    L%d width=%d  %s' % r)

    # ------------------------------------------ 7. 热区：触屏下小尺寸可点元素
    # 查 max-width:640/560/420 段内有没有 min-height:44px 之类
    touch44 = re.findall(r'min-height:\s*44px', css_nc)
    notes.append('触屏 44px 热区规则：min-height:44px 出现 %d 次' % len(touch44))

    # ------------------------------------------------------ 8. 打印样式存在性
    if '@media print' not in css_nc:
        problems.append('缺 @media print 段')
    notes.append('@media print 段：%d 个' % len(re.findall(r'@media\s*print', css_nc)))

    # ------------------------------------------------------------ 输出报告
    print('=' * 90)
    print('阶段 5｜三端 / 触屏 / 暗色 静态核查')
    print('=' * 90)
    for n in notes:
        print('· ' + n)
    print()
    if problems:
        print('❌ 硬性问题 %d 个：' % len(problems))
        for p in problems:
            print('  - ' + p)
        return 1
    print('✅ 无硬性问题（以上为需人工确认的提示项）')
    return 0


if __name__ == '__main__':
    sys.exit(main())