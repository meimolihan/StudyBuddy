"""阶段 5 复审｜**元素可见性**静态核查（补首轮验收的最大盲区）。

背景：首轮阶段 5 验收只覆盖「对比度 / 断点 / hover 隔离 / 暗色 A-B」四类
**静态可算**项，据此报告「无硬性问题 ✅」，结果用户一用就发现
**暗色下13 个页面的 h1 渐变标题文字完全消失**（有背景色、无文字）。
根因是 CSS 简写属性把 background-clip 打回默认值 —— 这类问题
**对比度算不出来、断点查不出来、grep 也查不出来**，因为每一条规则
单独看都没错，错在「层叠顺序 × 简写重置」的组合。

本脚本按 CSS 真实层叠顺序模拟计算，专门抓四类「元素可能看不见」的隐患：

  ① 简写属性重置 longhand
     background / border / font / flex / grid / transition / animation /
     mask / list-style / outline / text-decoration 等 shorthand 会把子属性
     打回初始值。若某选择器先设了 longhand（同一条规则内或更早的同特异度规则），
     后面又出现 shorthand，就会被重置。
     重点场景：依赖 background-clip:text / animation-* / transition-*
     等 longhand 才有效果的属性。

  ② 透明填充色无背景可显形
     color:transparent / -webkit-text-fill-color:transparent / opacity 极低
     却没有配套背景（渐变 / clip:text）→ 元素彻底不可见。
     这是「文字消失」类事故的通用形态。

  ③ 透明文字的后代继承
     -webkit-text-fill-color / color 是**继承属性**。父级设transparent 后，
     子元素（徽章、链接、span）会一起变透明，除非显式恢复 currentColor。

  ④ 降级路径自身失效
     @supports 降级分支里如果又用了 shorthand，等于降级失败（不支持的浏览器
     反而坏得更快）。

用法: python tools/check_visibility.py
"""
import re
import sys
from collections import defaultdict

CSS = 'internal/web/static/style.css'

# ---- 各类 shorthand 会重置哪些 longhand（只列本项目实际可能用到的）----
SHORTHAND_RESET = {
    'background': ['background-image', 'background-color', 'background-clip',
                   'background-origin', 'background-position', 'background-size',
                   'background-repeat', 'background-attachment', 'background-origin'],
    'border': ['border-width', 'border-style', 'border-color',
               'border-top-width', 'border-top-style', 'border-top-color',
               'border-right-width', 'border-right-style', 'border-right-color',
               'border-bottom-width', 'border-bottom-style', 'border-bottom-color',
               'border-left-width', 'border-left-style', 'border-left-color',
               'border-image', 'border-image-source', 'border-image-slice'],
    'font': ['font-size', 'font-family', 'font-weight', 'font-style',
             'font-variant', 'font-stretch', 'line-height'],
    'flex': ['flex-grow', 'flex-shrink', 'flex-basis', 'flex-direction',
             'flex-wrap', 'flex-flow', 'order'],
    'grid': ['grid-template', 'grid-template-areas', 'grid-template-rows',
             'grid-template-columns', 'grid-auto-rows', 'grid-auto-columns',
             'grid-auto-flow', 'grid-area'],
    'transition': ['transition-property', 'transition-duration',
                   'transition-timing-function', 'transition-delay'],
    'animation': ['animation-name', 'animation-duration', 'animation-timing-function',
                  'animation-delay', 'animation-iteration-count',
                  'animation-direction', 'animation-fill-mode',
                  'animation-play-state'],
    'mask': ['mask-image', 'mask-mode', 'mask-repeat', 'mask-position',
             'mask-clip', 'mask-origin', 'mask-size', 'mask-composite'],
    'list-style': ['list-style-type', 'list-style-image', 'list-style-position'],
    'outline': ['outline-width', 'outline-style', 'outline-color'],
    'text-decoration': ['text-decoration-color', 'text-decoration-style',
                        'text-decoration-thickness'],
    'overflow': ['overflow-x', 'overflow-y'],
    'gap': ['row-gap', 'column-gap'],
}

# 透明填充色属性 → 判定「不可见」的关键属性
# ⚠️ 这两类必须分开，不能一视同仁（v2 修的误报）：
#   · -webkit-text-fill-color:transparent —— 渐变字 technique 的必要条件。
#     单独用它 → 文字必须靠 background-clip:text 显形，没有 clip 就是隐形。
#   · color:transparent —— 常见于**故意的替换内容**写法：
#       .btn.is-loading{color:transparent}  +  ::after 画转圈 spinner
#     文字确实被藏起来，但由 ::after 提供可见内容，**不是 bug**。
#     只有「color 透明 + 同选择器既无背景、又无 ::after/::before 替代内容」
#     才可能真的看不见。
TRANSPARENT_FILL = ['-webkit-text-fill-color', 'color']
# 真正「必须配套 clip/渐变」的属性（用于条件 C 与维度 ②③④⑤）
FILL_NEEDS_BG = ['-webkit-text-fill-color']

# 这些 longhand 一旦被 shorthand 重置，元素外观就会显著改变（高危）
CRITICAL_LONGS = {
    'background-clip',    # text 渐变字必需
    'animation-name', 'animation-duration', 'transition-property',
    'transition-duration', 'flex-grow', 'flex-basis', 'grid-template-areas',
    'line-height', 'font-size', 'border-color', 'border-width', 'list-style-type',
}

# ================================================================
# ⚠️ 误报控制（本脚本第一版误报 50+ 条，绝大多数是正常用法）
# ================================================================
# 简写重置 longhand 本身**不是 bug** —— 绝大多数情况是有意为之：
#   transition:all .2s;transition-property:transform;  ← 合法覆盖，顺序正确
# 只有当「被重置的 longhand 是另一个选择器设置的、且该longhand
# 是元素可见/可显形的关键依赖」时，才是事故。
#
# 事故的三个必要条件（缺一不算）：
#   A. 被重置的 longhand 属于 CRITICAL_LONGS
#   B. 设置该 longhand 的选择器 **与** 用简写的选择器 **不同**
#      （同规则内先 longhand 后 shorthand，是作者本意，不算）
#   C. 该元素同时存在「透明填充色」或「依赖 clip 显形」的配套声明
#      —— 只有这时 clip 被重置才会导致「看不见」
# 换句话说：单纯 border-color 被 border 简写重置不算问题，
# 因为 border 简写里的color 本来就是新的期望值。
CRITICAL_DEPENDENT = {'background-clip'}   # B+C 联合判定才报


def strip_comments(css):
    prev = None
    s = css
    while prev != s:
        prev = s
        s = re.sub(r'/\*.*?\*/', '', s, flags=re.S)
    return s


def parse(css):
    """返回 [(selector, [(prop, value, 顺序号, media条件串)])]，递归 @media/@supports。"""
    out = []
    css = strip_comments(css)
    order = [0]

    def walk(src, media):
        i, n = 0, len(src)
        while i < n:
            j = src.find('{', i)
            if j < 0:
                break
            sel = src[i:j].strip()
            d, k = 1, j + 1
            while k < n and d:
                if src[k] == '{':
                    d += 1
                elif src[k] == '}':
                    d -= 1
                k += 1
            body = src[j + 1:k - 1]
            if sel.startswith('@media') or sel.startswith('@supports'):
                walk(body, sel)
            elif sel.startswith('@'):
                pass
            else:
                decls = []
                for part in body.split(';'):
                    part = part.strip()
                    if not part or ':' not in part:
                        continue
                    p, v = part.split(':', 1)
                    # ⚠️ 必须剥掉 !important / !important 前的空格，
                    #   否则值是 'currentColor !important'，下游按值精确
                    #   匹配（transparent / currentColor）会全部落空 ——
                    #   v1 第⑤维就因此把已有的 @media print 兜底误报成「没有」。
                    v = re.sub(r'\s*!\s*important\s*$', '', v.strip(),
                               flags=re.I).strip()
                    order[0] += 1
                    decls.append((p.strip().lower(), v, order[0], media))
                if decls:
                    for one in sel.split(','):
                        out.append((re.sub(r'\s+', ' ', one).strip(), decls, media))
            i = k

    walk(css, '')
    return out


def specificity(sel):
    """粗略特异度：(id, class/attr/pseudo-class, 元素/伪元素)"""
    s = sel
    ids = len(re.findall(r'#[A-Za-z0-9_-]+', s))
    cls = len(re.findall(r'\.[A-Za-z0-9_-]+', s)) + \
        len(re.findall(r'\[[^\]]*\]', s)) + \
        len(re.findall(r':(?!:)[a-z-]+', s))
    els = len(re.findall(r'(?:^|[\s>+~])([a-z][a-z0-9]*)', s))
    return (ids, cls, els)


def key_of(sel):
    return specificity(sel), sel


def main():
    raw = open(CSS, encoding='utf-8').read()
    blocks = parse(raw)
    print('=' * 94)
    print('阶段 5 复审｜元素可见性静态核查（简写重置 / 透明填充 / 后代继承 / 降级失效 / 降级媒体）')
    print('=' * 94)
    print('解析规则组：%d 条' % len(blocks))

    problems = []

    # =========================================================
    # ① 简写重置 longhand：同选择器内，或更早的同/更高特异性规则
    # =========================================================
    print('\n--- ① 简写属性重置 longhand（按层叠顺序模拟，已按三条件收窄）---')

    # 先收集：哪些选择器设置了「透明填充色」或「依赖 clip 显形」
    # （条件 C）——只有这些选择器上发生的 clip 重置才会导致看不见
    #
    # ⚠️ v2 误报修复：.btn.is-loading{color:transparent !important} 曾被收进来，
    #   但它配了 ::after 转圈 spinner，是**故意的替换内容**写法。
    #   故 color:transparent 只有在「同选择器也用了 clip/渐变」时才纳入风险集；
    #   纯 -webkit-text-fill-color:transparent 则必须配套 clip，永远纳入。
    sel_has_clip = set()
    sel_has_grad = set()
    for sel, decls, media in blocks:
        for prop, val, order, m in decls:
            if prop in ('-webkit-background-clip', 'background-clip') and \
                    'text' in val:
                sel_has_clip.add(sel)
            if prop == 'background-image' and 'gradient' in val:
                sel_has_grad.add(sel)
    # 同选择器是否用 ::after/::before 提供了替代可见内容
    sel_has_pseudo = set()
    for sel, decls, media in blocks:
        if '::after' in sel or '::before' in sel:
            base = sel.split('::')[0].strip()
            if any(p == 'content' for p, _v, _o, _m in decls):
                sel_has_pseudo.add(base)
    clip_users = set(sel_has_clip)          # ① 设了 background-clip:text
    for sel, decls, media in blocks:
        for prop, val, order, m in decls:
            if val.strip().lower() != 'transparent':
                continue
            if prop in FILL_NEEDS_BG:
                clip_users.add(sel)          # ② 必须配套 clip，必然纳入
            elif prop == 'color':
                # ③ color 透明：仅当同选择器有 clip/渐变（渐变字）时才是风险；
                #    有 ::after/::before 替代内容的（如 loading spinner）排除。
                if sel in sel_has_clip or sel in sel_has_grad:
                    clip_users.add(sel)
    # 记录被排除的 color:transparent（说明理由，避免下轮再误判）
    excluded_color = []
    for sel, decls, media in blocks:
        for prop, val, order, m in decls:
            if prop == 'color' and val.strip().lower() == 'transparent' \
                    and sel not in clip_users:
                why = ('配了 ::after/::before 替代内容' if sel in sel_has_pseudo
                       else '无 clip/渐变但由其他机制显形')
                excluded_color.append((sel, why))
    # 记录「只有渐变、没有文字」的纯装饰层（不构成可见性风险，仅留痕）
    deco = sorted(s for s in sel_has_grad if s not in clip_users)
    print('  依赖 clip 显形 / 使用透明填充色的选择器（条件 C 集合）：%d 个'
          % len(clip_users))
    for s in sorted(clip_users)[:8]:
        print('      · %s' % s[:60])
    for sel, why in excluded_color:
        print('      · [已排除] %s（color:transparent，%s）' % (sel[:44], why))
    for s in deco[:6]:
        print('      · [非风险] %s（纯装饰渐变层，无文字依赖）' % s[:52])

    # 逐个选择器模拟其自身的声明序列（条件 A+B）
    hits = []
    for sel, decls, media in blocks:
        if sel not in clip_users:
            continue                      # 只审「会因 clip 重置而不可见」的选择器
        seen_long = {}
        for prop, val, order, m in decls:
            if prop in SHORTHAND_RESET:
                for rp in SHORTHAND_RESET[prop]:
                    if rp in CRITICAL_DEPENDENT and rp in seen_long:
                        hits.append((sel, rp, seen_long[rp][1], prop, val))
                for rp in SHORTHAND_RESET[prop]:
                    seen_long.pop(rp, None)
                seen_long[prop] = (order, val)
            else:
                seen_long[prop] = (order, val)

    # 跨规则：更早的同特异性规则设了 clip:text，被当前规则的 background 简写重置
    # （这正是事故形态：h1{} 设clip，html[data-theme="dark"] h1{} 用 background 简写）
    by_key = defaultdict(list)
    for sel, decls, media in blocks:
        by_key[key_of(sel)].append((sel, decls))
    for sel, decls, media in blocks:
        if sel not in clip_users:
            continue
        cur_spec = specificity(sel)
        for prop, val, order, m in decls:
            if prop != 'background':
                continue
            for (spec, ssel), lst in by_key.items():
                if ssel == sel or spec != cur_spec:
                    continue
                for s2, d2 in lst:
                    for p2, v2, o2, _m2 in d2:
                        if p2 in ('-webkit-background-clip', 'background-clip') \
                                and 'text' in v2 and o2 < order:
                            hits.append((sel, p2, v2, prop, val))

    if hits:
        seen = set()
        for sel, rp, oldv, prop, val in hits:
            key = (sel, rp, prop)
            if key in seen:
                continue
            seen.add(key)
            problems.append('简写重置可见性关键 longhand：%s 的 %s 被 %s 重置'
                            % (sel, rp, prop))
            print('  ❌ %-40s %s 被 %s 重置（原值 %s）'
                  % (sel[:40], rp, prop, oldv[:24]))
    else:
        print('  ✅ 依赖 clip 显形的元素上，未发现简写重置 background-clip')

    # =========================================================
    # ② 透明填充色 vs 背景可显形
    # =========================================================
    print('\n--- ② 透明填充色是否有配套背景（文字可见性）---')
    # ⚠️ 只审 clip_users（条件 C 同一集合），不要重新按 TRANSPARENT_FILL 全量收，
    #   否则会把「color:transparent + ::after 替代内容」的正常写法误报进来。
    #   has_grad/has_clip 已在 ① 算好，这里只补 media 维度。
    transparent = defaultdict(set)
    for sel, decls, media in blocks:
        if sel not in clip_users:
            continue
        for prop, val, order, m in decls:
            if prop in FILL_NEEDS_BG and val.strip().lower() == 'transparent':
                transparent[sel].add(m or '无条件')
    for sel, medias in sorted(transparent.items()):
        ok = sel_has_clip or sel_has_grad
        for media in medias:
            cond = media if media != '无条件' else '（无 media 限定）'
            if not ok:
                problems.append('透明填充色但无渐变/clip 背景：%s @ %s' % (sel, cond))
                print('  ❌ %-38s text-fill-color:transparent @ %s' % (sel[:38], cond))
            else:
                print('  ✅ %-38s transparent @ %s（有 clip/渐变配套）'
                      % (sel[:38], cond))

    # =========================================================
    # ③ 透明文字的后代继承
    # =========================================================
    print('\n--- ③ 透明填充色的后代继承（h1 内的徽章/链接）---')
    # 关键：-webkit-text-fill-color 沿**元素树**继承，与选择器特异性无关。
    # 只要存在一条**无条件**的后代恢复规则（如 `h1 *{…currentColor}`），
    # 任何主题下都会生效 —— 不需要按主题各写一份。
    # （本项目 v1 曾误报「暗色选择器未各自恢复」，实际是无条件规则已覆盖。）
    restore = [sel for sel, _d, _m in blocks
               if sel.endswith(' *') and any(
                   p == '-webkit-text-fill-color'
                   and v.strip().lower() == 'currentcolor'
                   for p, v, _o, _m2 in _d)]
    # 该主题选择器的「去掉前缀后的裸选择器」（如 html[data-theme="dark"] h1 → h1）
    def bare(s):
        # html[data-theme="dark"] h1 → h1
        # html:not([data-theme="light"]) h1 → h1（注意 :not(...) 收尾是 ) 不是 ]）
        m = re.search(r'(?:\]|\))\s+(h1)$', s)
        return m.group(1) if m else s

    for sel in transparent:
        need = bare(sel)
        # 找是否存在 `<need> *` 形式的后代恢复（可带任意祖先前缀）
        has_restore = any(
            r == need + ' *' or r.endswith(' ' + need + ' *')
            for r in restore)
        if has_restore:
            print('  ✅ %-40s 后代已由 %s 恢复' % (sel[:40],
                  [r for r in restore if r.endswith(need + ' *')][0]))
        else:
            print('  ❌ %-40s 未给后代恢复 currentColor' % sel[:40])
            problems.append('%s 设了透明填充色但未给后代恢复 currentColor'
                            '（模板里该选择器下若含徽章/链接，文字会消失）' % sel)

    # =========================================================
    # ④ 降级路径自身失效
    # =========================================================
    print('\n--- ④ @supports 降级分支里是否又用了简写---')
    sup_blocks = []
    css_nc = strip_comments(raw)
    for m in re.finditer(r'@supports[^{]*\{', css_nc):
        st = m.end()
        d, k = 1, st
        while k < len(css_nc) and d:
            if css_nc[k] == '{':
                d += 1
            elif css_nc[k] == '}':
                d -= 1
            k += 1
        sup_blocks.append(css_nc[st:k - 1])
    print('  @supports 分支数：%d' % len(sup_blocks))
    bad_sup = 0
    for bi, b in enumerate(sup_blocks, 1):
        for sel, decls, media in parse(b):
            # ⚠️ 误报控制（v1 曾误报 9 条）：降级分支里的简写绝大多数正常，
            #   -::-webkit-scrollbar-*  本来就要靠简写重置 border/background；
            #   .sb-modal-mask / .sheetscrim 这类纯色遮罩本来就不需要 clip:text。
            #   只有「该选择器同时依赖 clip 显形 / 使用透明填充色」时才算隐患。
            if sel not in clip_users:
                continue
            for prop, val, order, m in decls:
                if prop in SHORTHAND_RESET:
                    for rp in SHORTHAND_RESET[prop]:
                        if rp in CRITICAL_DEPENDENT:
                            problems.append(
                                '@supports 分支 #%d 的 %s 用了简写 %s（会重置 %s）'
                                % (bi, sel, prop, rp))
                            print('  ❌ 分支#%d %-34s %s → 重置 %s'
                                  % (bi, sel[:34], prop, rp))
                            bad_sup += 1
    total_sup_short = 0
    for b in sup_blocks:
        for sel, decls, media in parse(b):
            total_sup_short += sum(1 for p, _v, _o, _m in decls if p in SHORTHAND_RESET)
    if not bad_sup:
        print('  ✅ 降级分支中，无「依赖 clip 显形的选择器」使用简写')
        print('     （另有 %d 处简写均在::-webkit-scrollbar-* 与纯色遮罩上，'
              '属正常用法）' % total_sup_short)

    # =========================================================
    # ⑤ 降级媒体（print / forced-colors）覆盖
    # =========================================================
    print('\n--- ⑤ 降级媒体下透明填充色元素是否仍可见（print / forced-colors）---')
    # 背景：这两个模式下浏览器会**剥离背景图**
    #   · @media print → 默认 print-color-adjust:economy，不打印背景
    #   · forced-colors: active → UA 强制系统色，background-image 被移除
    # 而 -webkit-text-fill-color:transparent 不受这两个模式影响 → 文字消失。
    # 实测（tools/render_check.py 模拟剥离背景图）：
    #   剥离前内容像素 1337（可见）→ 剥离后 0（整块空白）
    # 故凡是设了透明填充色的选择器，都必须在这两个媒体里恢复实色。
    DEGRADE_MEDIA = ('print', 'forced-colors')
    # 每个降级媒体下，哪些选择器被恢复了 text-fill-color
    restored = defaultdict(set)
    for sel, decls, media in blocks:
        if not media:
            continue
        for want in DEGRADE_MEDIA:
            if want in media:
                for prop, val, order, m in decls:
                    if prop == '-webkit-text-fill-color' and \
                            val.strip().lower() in ('currentcolor', 'initial'):
                        restored[want].add(sel)
    for want in DEGRADE_MEDIA:
        n = len(restored[want])
        print('  @media %-14s 恢复规则 %d 条：%s'
              % (want, n, ', '.join(sorted(s[:34] for s in restored[want])[:4])
                 or '（无）'))
    # 对每个透明填充色选择器，检查是否有**任意**降级媒体下的恢复规则命中
    # （取裸选择器比对，允许带祖先前缀，如 h1 ← html[data-theme="dark"] h1）
    for sel in sorted(transparent):
        need = bare(sel)
        hit = []
        for want in DEGRADE_MEDIA:
            for r in restored[want]:
                if r == need or r.endswith(' ' + need):
                    hit.append(want)
                    break
        if hit:
            print('  ✅ %-40s 已在 @media %s 恢复实色'
                  % (sel[:40], '/'.join(hit)))
        else:
            problems.append(
                '%s 设了透明填充色，但 @media print 与 @media (forced-colors: active) '
                '下均未恢复实色（背景图会被剥离 → 文字完全消失）' % sel)
            print('  ❌ %-40s 两个降级媒体下都没有恢复规则' % sel[:40])

    # =========================================================
    print('\n' + '=' * 94)
    if problems:
        print('❌ 发现可见性隐患 %d 项：' % len(problems))
        for p in problems:
            print('  - ' + p)
        return 1
    print('✅ 未发现「元素不可见」类隐患')
    return 0


if __name__ == '__main__':
    sys.exit(main())