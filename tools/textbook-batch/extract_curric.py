# -*- coding: utf-8 -*-
"""从教材 PDF 提取「教材介绍」与结构化「目录」。

为什么要单独一个工具
--------------------
283 册教材里只有语文一年级上册是手写目录（internal/web/textbookres.go 的
``tbCurric``），其余全空。本工具从源 PDF 自动补全，输出
``data/textbook/curric.json``，由 Go 侧读取。

难点与对策
----------
1. **PDF 内置书签基本为 0**（实测 283 册绝大多数为空），只能读目录页文本。
2. **三种排版都要认**：
   - 点线式（语文）：``1 观潮……2``
   - 分行式（低年级识字表、独立数字行）
   - 坐标分离式（数学/英语）：课名在左、页码在右，且**双栏**，
     文本抽取顺序 ≠ 阅读顺序 → 必须用 ``get_text('blocks')`` 拿坐标，
     按 ``(y 行, x 列)`` 排序还原。
3. **页码偏移**：目录里印的是「教材标注页码」，与 PDF 页码差一个常数
   （封面、版权、目录页占前几页）。逐册实测求出，不硬编码。
4. **置信度**：解析不可靠的册不能污染数据，输出 ``confidence`` 字段，
   低的交人工复核。

用法
----
    python tools/textbook-batch/extract_curric.py                    # 全量
    python tools/textbook-batch/extract_curric.py --only primary-math-g4-v1
    python tools/textbook-batch/extract_curric.py --out data/textbook/curric.json
"""

import argparse
import collections
import json
import os
import re
import sys
import time

import pymupdf

# ---------------------------------------------------------------- 通用工具

RE_DOTS = re.compile(r"\.{3,}\s*(\d{1,3})\s*$")          # 点线结尾 + 页码
# 行尾页码：容许任意长度的中文标题（数学册「三位数乘两位数」有 7 字，
# 早期用 [^\d]{0,12} 量词上限会整条匹配失败）
RE_TAIL_NUM = re.compile(r"^(.+?)\s*(\d{1,3})\s*$")
RE_ONLY_NUM = re.compile(r"^\s*(\d{1,3})\s*$")          # 整行只有页码
RE_UNIT = re.compile(r"^\s*(第[一二三四五六七八九十百]+单元|"
                     r"Unit\s*\d+|第[一二三四五六七八九十]+章|"
                     r"第[一二三四五六七八九十]+部分|"
                     r"Revision\s*\d*|附录[一二三四五六七八九十]+.*|"
                     r"目\s*录|Contents)\s*$", re.I)
RE_NOISE = re.compile(r"[\s　]+")

# 明显不是课名的噪声行
RE_NOISE_LINE = re.compile(
    r"^(目\s*录|Contents|页码|本书|印刷|责任编辑|美术编辑|编写人员|"
    r"总\s*主\s*编|主编|出\s*版|新华书店|定价|ISBN|社\s*址|邮编|"
    r"版权所有|教育部组织编写|全国优秀教材|特等奖)") 

# 版权页字段
RE_PUB = re.compile(r"出\s*版\s*社[）)]?\s*[:：]?\s*([^\n，。]{2,20}出版社)")
RE_PUB2 = re.compile(r"^([^\n，。]{2,20}出版社)\s*$", re.M)
# 主编名。版权页里主编常连排（「王晶郑长龙」「温儒敏总主编：…」），
# 固定长度切不准。做法：按标签字（总/小学/本册/副/执行/编写/责任编辑…）切段，
# 取最前一段，再校验它像不像中文人名。
RE_ED_LABEL = re.compile(
    r"(总\s*主\s*编|小学\s*主\s*编|本册\s*主\s*编|副\s*主\s*编|执行|"
    r"主\s*编|编\s*写\s*人\s*员|责\s*任\s*编\s*辑|美\s*术\s*编\s*辑)")
RE_EDU = re.compile(r"(教育部组织编写|教育部审定|国家教育委员会编写)")
RE_VER = re.compile(r"(第\s?\d\s?版|新版修订|20\d\d\s?年\s?\d*月?第?\d*版?)")
RE_AWARD = re.compile(r"(全国优秀教材[特一等]+奖|国家优秀教材)")


def _pick_editor(blob):
    """从版权页文本里取主编姓名。取不到返回空串。

    版权页形态实测：
      - 语文：``总主编温儒敏总主编：温儒敏小学主编：陈先云（执行）…``
      - 高中数学：``主编：章建跃李增沪副主编：李勇李海东…``（多人连排、无分隔）
      - 小学数学：版权页只有「小学数学教材编委会」，**根本没写人名** → 返回空，
        不硬编。取不到就留空，比填错好。
    """
    # 常见姓氏，用于在连排人名里找断点
    surnames = ("王李张刘陈杨黄赵周吴徐孙马朱胡林郭何高罗郑梁谢宋唐许韩冯邓曹彭曾"
                "肖田董袁潘于蒋蔡余杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦付方")
    for m in RE_ED_LABEL.finditer(blob):
        seg = blob[m.end():]
        nxt = RE_ED_LABEL.search(seg)
        if nxt and nxt.start() <= 8:
            seg = seg[:nxt.start()]
        seg = re.split(r"[^一-鿿·]", seg)[0].strip("·")
        if not (2 <= len(seg) <= 4):
            continue
        return seg
    # 多人连排：在姓氏处找第一个断点，最多取 3 字
    for m in RE_ED_LABEL.finditer(blob):
        seg = re.split(r"[^一-鿿·]", blob[m.end():])[0]
        for i in range(3, 1, -1):
            if i < len(seg) and seg[i] in surnames:
                return seg[:i]
        if 2 <= len(seg) <= 4:
            return seg
    return ""

# 课名开头粘连的课序号：1观潮 / 3*现代诗二首 / 2* Wiedermachen
RE_LESSON_NO = re.compile(r"^(\d{1,2})(\s*\*?)\s*(.+)$")


def clean(s):
    """压掉全角空格与零宽字符，PDF 里注音排版会塞进大量不可见字符。"""
    s = RE_NOISE.sub("", s or "")
    return s.strip()


def is_unit_text(s):
    """只压掉「全角空格 + 零宽字符」，**保留半角空格**。

    目录页的 ``Unit 1 Sports and Games`` 被 clean() 去掉空格后会变成
    ``Unit1SportsandGames``，整串锚定的单元正则就再也匹配不上（实测英语册
    12 个单元全被当普通课名、页码全被吞）。所以判单元用这个宽松版。
    """
    return re.sub(r"[　\s﻿]+", " ", s or "").strip()


# ---------------------------------------------------------------- 目录页定位

def _toc_score(page_text):
    """这一页像不像目录页：点线条数 / 独立数字行数。"""
    dots = len(RE_DOTS.findall(page_text))
    standalone = len(re.findall(r"^\s*\d{1,3}\s*$", page_text, re.M))
    return dots, standalone


def find_toc_pages(doc, limit=16):
    """返回疑似目录页的 PDF 页序号（0 基），只返回**连续**的一段。

    不能只看「点线多 / 独立数字行多」——正文页里也有大量独立数字（页码、
    习题号、表格数字），会把正文误判成目录并把偏移算飞。曾实测数学四上
    命中 [5,6,8,10]，其中 8、10 明显是正文。
    办法：命中后取**最大连续区间**作为目录页，并要求首命中页不超过 12。
    """
    hits = []
    for i in range(min(limit, len(doc))):
        txt = doc[i].get_text()
        if not txt.strip():
            continue
        dots, standalone = _toc_score(txt)
        has_toc_word = "目" in txt and "录" in txt and len(txt) < 3000
        if has_toc_word:
            hits.append((i, 100 + dots * 3 + standalone))
        elif dots >= 4:
            hits.append((i, dots))
        elif standalone >= 5:
            hits.append((i, standalone * 2))
    if not hits:
        return []

    idx = sorted(i for i, _ in hits)
    # 找最长连续段（目录偶尔有跨页空白，允许间隔 1 页）
    best = [idx[0]]
    run = [idx[0]]
    for a, b in zip(idx, idx[1:]):
        if b - a <= 2:
            run.append(b)
        else:
            if len(run) > len(best):
                best = run
            run = [b]
    if len(run) > len(best):
        best = run
    # 目录一般在书的前 12 页内
    if best[0] > 12:
        best = [best[0]]

    # 硬性上限：目录不会超过 6 页，超了说明把正文吃进来了，只保留含
    # 「目录」二字的那几页（数学册第 5 页有「目 录」标题，正文页没有）
    if len(best) > 6:
        titled = [i for i in best
                  if "目" in doc[i].get_text() and "录" in doc[i].get_text()]
        best = titled if titled else best[:3]
    return best


# ---------------------------------------------------------------- 目录解析

def _lines_by_coord(page):
    """按阅读顺序返回 [(x, y, 紧凑文本, 宽松文本)]。

    「紧凑文本」去掉了所有空格（适合取页码），「宽松文本」保留半角空格
    （适合判断 ``Unit 1`` 这类单元名）。两个都要，因为 clean() 抹掉空格后
    单元正则会失效。

    目录页有两种「双栏」，处理方式完全不同，必须区分：

    A. **内容双栏**（语文）：左栏是第一/二单元，右栏是第三/四单元，
       文字本身是完整的条目行（``1 观潮……2``）。→ 先分栏，栏内按 y 排。
    B. **课名/页码分列**（数学、英语）：页码单独成列且**块很窄、纯数字**。
       → 必须**跨列按 y 配对**，否则「1 大数的认识」匹配不到页码。

    判据不能只看「x 是否过半」：英语册标题块 x=210~423，中点 317 已过中线
    261，会被误判成页码列（实测把 12 个单元吃剩 4 个）。改用**窄块 + 纯数字**
    判定页码列 —— 页码列的块宽通常 < 页宽 8%，标题块则宽得多。
    """
    blocks = [b for b in page.get_text("blocks") if b[4].strip()]
    if not blocks:
        return []

    def is_page_num(b):
        """这个块是不是「纯数字页码块」：窄、且每行都是数字。"""
        lines = [clean(x) for x in b[4].split("\n")]
        lines = [x for x in lines if x]
        if not lines:
            return False
        if not all(re.fullmatch(r"\d{1,3}", x) for x in lines):
            return False
        return (b[2] - b[0]) < page.rect.width * 0.10

    # ---- 形态 0：单栏 + 块内多行（低年级识字表最常见） ----
    # 块内形如 ``1 \n 天地人 \n 6``：课名与页码在同一块的换行里，
    # 不做合并就会被当成三行独立文本，课名永远匹配不到页码。
    only_wide = [b for b in blocks if (b[2] - b[0]) >= page.rect.width * 0.10]
    # 允许少量窄块存在（低年级目录里「识字」这种单元标签就是窄块），
    # 门槛取「窄块不足两成」，否则一个单元标签就会让整个形态 0 失效
    # （实测语文一年级上册 21 块里有 1 个窄块，卡掉了整册）。
    if len(only_wide) >= 3 and len(only_wide) >= len(blocks) * 0.8:
        merged_out = []
        for b in sorted(blocks, key=lambda b: b[1]):
            parts = [clean(x) for x in b[4].split("\n")]
            parts = [x for x in parts if x]
            if not parts:
                continue
            if (b[2] - b[0]) < page.rect.width * 0.10:
                # 窄块（如「识字」单元标签）原样保留
                for idx, one in enumerate(parts):
                    merged_out.append((b[0], b[1] + idx, one, is_unit_text(one)))
                continue
            # 尾部连续的数字行 = 页码
            k = len(parts)
            while k > 0 and re.fullmatch(r"\d{1,3}", parts[k - 1]):
                k -= 1
            tail_nums = parts[k:]
            body = parts[:k]
            loose_src = " ".join(body)
            if tail_nums and body:
                merged_out.append((b[0], b[1],
                                   " ".join(body + tail_nums), is_unit_text(loose_src)))
            else:
                for idx, one in enumerate(parts):
                    merged_out.append((b[0], b[1] + idx, one, is_unit_text(one)))
        if merged_out:
            return merged_out

    num_blocks = [b for b in blocks if is_page_num(b)]
    txt_blocks = [b for b in blocks if not is_page_num(b)]

    # ---- B 型：存在独立页码列 → 跨列配对 ----
    if num_blocks and txt_blocks:
        # 页码列取「最靠右」的那批。容差要按实测放宽：数学册页码块 x0
        # 在 376~386 之间抖动（列宽 10~19），用 6 会只选中 1 个块导致全废。
        maxx = max(b[0] for b in num_blocks)
        tol = page.rect.width * 0.05
        right_nums = sorted([b for b in num_blocks if b[0] >= maxx - tol],
                            key=lambda b: b[1])
        left_txts = [b for b in txt_blocks if b[0] < maxx - tol]
        # 展开成 (y, x, 文本) 行，行内保持原有顺序
        rlines = []
        for b in right_nums:
            for ln in b[4].split("\n"):
                t = clean(ln)
                if t:
                    rlines.append((b[1], t))
        llines = []
        for b in sorted(left_txts, key=lambda b: b[1]):
            for ln in b[4].split("\n"):
                t = clean(ln)
                if t:
                    llines.append((b[0], b[1], t, is_unit_text(ln)))

        if rlines and llines:
            # 标题行里「目录 / Contents」是页眉，不吃页码，先摘出去。
            # 判单元必须用**宽松文本**（保留半角空格），否则
            # ``Unit 1 Sports and Games`` 去掉空格后匹配不上单元正则。
            head_lines = [it for it in llines if _is_unit_head(it[3])]
            body_lines = [it for it in llines if not _is_unit_head(it[3])]

            if rlines and len(rlines) == len(body_lines):
                # 英语册形态：标题数与页码数相等 → 按序配对最准
                out = list(head_lines)
                out += [(lx, ly, "%s%s" % (title, num), loose)
                        for (lx, ly, title, loose), (_ry, num)
                        in zip(body_lines, rlines)]
                out.sort(key=lambda t: t[1])
                return out
            if rlines and body_lines:
                # 数学册形态：页码列与标题按 y 就近配对。必须**一对一**（用过即弃），
                # 否则同一行多个页码（``三位数乘两位数 / 4 / 47``）会全贴到同一标题。
                pool = list(rlines)
                out = list(head_lines)
                for lx, ly, title, loose in body_lines:
                    best_i, bestdy = -1, 999
                    for i, (ry, num) in enumerate(pool):
                        dy = abs(ry - ly)
                        if dy < bestdy:
                            best_i, bestdy = i, dy
                    if best_i >= 0 and bestdy <= 26:
                        num = pool.pop(best_i)[1]
                        out.append((lx, ly, "%s%s" % (title, num), loose))
                    else:
                        out.append((lx, ly, title, loose))
                out.sort(key=lambda t: t[1])
                return out
            if head_lines:
                out = list(head_lines) + list(body_lines)
                out.sort(key=lambda t: t[1])
                return out

    # ---- A 型：无独立页码列 → 可能是内容双栏 ----
    mid = page.rect.width / 2.0
    left = [b for b in blocks if b[0] < mid]
    right = [b for b in blocks if b[0] >= mid]
    if left and right and min(b[0] for b in right) > page.rect.width * 0.45:
        cols = [left, right]
    else:
        cols = [blocks]
    # 只有一栏时再按 x 起点聚类（安全兜底）
    if len(cols) == 1 and len(blocks) > 2:
        groups = []
        for b in sorted(blocks, key=lambda b: b[0]):
            for g in groups:
                if abs(g[0][0] - b[0]) < page.rect.width * 0.18:
                    g.append(b)
                    break
            else:
                groups.append([b])
        if len(groups) > 1:
            cols = groups

    out = []
    for col in cols:
        col.sort(key=lambda b: (round(b[1] / 8), b[0]))
        for b in col:
            for raw in b[4].split("\n"):
                t = clean(raw)
                if t:
                    out.append((b[0], b[1], t, is_unit_text(raw)))
    return out


def _merge_tail_nums(items):
    """数学/英语那种「课名」「页码」分成相邻两块的形态，按 y 就近配对。"""
    merged = []
    i = 0
    while i < len(items):
        x, y, t = items[i]
        m = RE_ONLY_NUM.match(t)
        if m and merged and not RE_ONLY_NUM.match(merged[-1][2]):
            px, py, pt = merged[-1]
            # y 差在 14pt 内视为同一行 → 页码并入课名
            if abs(y - py) <= 14:
                merged[-1] = (px, py, "%s%s" % (pt, m.group(1)))
                i += 1
                continue
        merged.append((x, y, t))
        i += 1
    return merged


def _is_unit_head(loose):
    u, _p = _unit_head_with_page(loose)
    return u


def _unit_head_with_page(loose):
    """判断单元头，返回 (单元名, 起始标注页码)。

    入参用**宽松文本**（保留半角空格）：``Unit 1 Sports and Games`` 去掉空格
    会变成 ``Unit1SportsandGames``，整串锚定的正则就废了。
    形如 ``Unit 1 Sports and Games2`` 的行既是单元头又带起始页码，
    单元名要保留英文原文，不要把结尾的 2 当页码剥掉。
    """
    head = RE_DOTS.sub("", loose).strip()
    for cand in (head, re.sub(r"(\d{1,3})\s*$", "", head).strip()):
        if not cand:
            continue
        if (RE_UNIT.match(cand)
                or re.match(r"^第[一二三四五六七八九十]+单元", cand)
                or re.match(r"^Unit\s*\d", cand, re.I)):
            page = 0
            m = re.search(r"(\d{1,3})\s*$", head)
            if m and cand != head:
                page = int(m.group(1))
            return cand, page
    return None, 0


def parse_toc_page(page):
    """从一页里解析出条目列表 [(标题, 教材页码, 课序号, 是否单元头)]。"""
    items = _lines_by_coord(page)
    entries = []
    for _x, _y, t, loose in items:
        if RE_NOISE_LINE.match(loose) or RE_NOISE_LINE.match(t):
            continue

        # 1) 单元头（可能带页码：Unit 1 Sports and Games2 → 头 + 起始页）
        unit, unit_page = _unit_head_with_page(loose)
        if unit:
            entries.append((unit, unit_page, "", True))
            continue

        # 2) 点线式：观潮……2
        m = RE_DOTS.search(t)
        if m:
            title = RE_DOTS.sub("", t).strip()
        else:
            # 3) 行尾页码：1 观潮 2 / 角的度量 3
            m = RE_TAIL_NUM.match(t)
            if not m:
                continue
            title = m.group(1)
            # 标题太短说明尾数字是编号的一部分而非页码
            if len(title) < 2 or title.isdigit():
                continue
            t = "%s%s" % (title, m.group(2))
            m = re.search(r"(\d{1,3})\s*$", t)

        page_no = int(m.group(1))
        title = re.sub(r"[◎◇◆\s]+$", "", title).strip()
        no = ""
        mm = RE_LESSON_NO.match(title)
        if mm:                       # 1 观潮 / 3* 现代诗二首 → 序号与课名拆开
            no, title = mm.group(1), mm.group(3).strip()
        if len(title) >= 2:
            entries.append((title, page_no, no, False))
    return entries


def _plausible(entries):
    """合理性校验：条目数、页码递增性、页码范围。决定这册能不能信。"""
    if len(entries) < 4:
        return 0.0, "条目过少"
    pages = [p for _t, p, _u in entries if p > 0]
    if len(pages) < 3:
        return 0.0, "页码样本不足"
    uniq = len(set(pages))
    inc = sum(1 for a, b in zip(pages, pages[1:]) if b >= a)
    inc_ratio = inc / max(1, len(pages) - 1)
    uniq_ratio = uniq / len(pages)
    if inc_ratio < 0.55:
        return 0.0, "页码非递增(%.2f)，多栏还原失败" % inc_ratio
    score = 0.45 + 0.35 * inc_ratio + 0.2 * uniq_ratio
    note = "条目%d 页码递增%.2f 去重%.2f" % (len(entries), inc_ratio, uniq_ratio)
    return score, note


def verify_units(doc, units, sample=12):
    """抽查目录页码是否真的指向对应内容，返回 (命中率, 说明)。

    这是上线的**最后一道闸**：目录的价值全在「点哪条就翻到哪页」，
    页码错了比没有目录更糟。所以不靠 confidence 猜，直接拿目录里的课名
    去目标页正文里找 —— 命中才算数。
    """
    items = [(l["title"], l["page"])
             for u in units for l in (u.get("lessons") or []) if l.get("page")]
    if not items:
        return 0.0, "无条目"
    # 均匀抽样，避免只验开头几页
    step = max(1, len(items) // sample)
    picked = items[::step][:sample]
    ok = 0
    for title, page in picked:
        key = re.split(r"[/／《》（(]", title)[0]
        key = re.sub(r"[^\w一-鿿]", "", key)[:6]
        if len(key) < 2 or page < 1 or page > len(doc):
            continue
        txt = clean(doc[page - 1].get_text())[:300]
        if key in txt:
            ok += 1
    rate = ok / len(picked)
    return rate, "抽查 %d 条命中 %d" % (len(picked), ok)


def _anchor_offset(doc, entries, max_page_scan=140):
    """用「课名 → 正文真实页码」锚点法求偏移，比统计众数可靠得多。

    做法：抽几本目录里有代表性、且名字足够独特的课，去正文页里找它第一次
    出现的位置，offset = 真实 PDF 页 - 目录标注页。取多个锚点的中位数。
    锚点找不到就返回 None（宁可判定这册不可信，也别让偏移错到把目录指乱）。
    """
    cands = [e for e in entries if not e[3] and e[1] > 0 and 2 <= len(e[0]) <= 12]
    if len(cands) < 3:
        return None
    # 挑几个分布靠前、中、后的条目，避免只锚到开头
    picked = [cands[0], cands[len(cands) // 3], cands[2 * len(cands) // 3],
              cands[-1]]
    found = []
    for title, printed, _no, _u, pg in picked:
        # 目录里的课名常带副标题：「沁园春·长沙/毛泽东」「加快转型/作者名」，
        # 直接拿整串去正文匹配必然失败（正文只有课文名，没有作者）。
        # 取斜杠、书名号、括号前的部分作为锚点。
        key = re.split(r"[/／《》（(]", title)[0]
        key = re.sub(r"[^\w一-鿿]", "", key)
        if len(key) < 2:
            continue
        # 正文起点：必须在目录页之后，否则会匹配到目录页自身
        for p in range(pg + 1, min(max_page_scan, len(doc))):
            txt = clean(doc[p].get_text())
            if key and key in txt:
                found.append((p + 1) - printed)
                break
        if len(found) >= 3:
            break
    if len(found) < 2:
        return None
    found.sort()
    return found[len(found) // 2]


def extract_units(doc, toc_pages, max_printed):
    """把若干目录页的条目合并成单元结构，并算出「标注页码→PDF 页码」偏移。"""
    raw = []
    for i in toc_pages:
        for t, p, no, is_unit in parse_toc_page(doc[i]):
            raw.append((t, p, no, is_unit, i))

    if not raw:
        return [], 0, 0.0, "目录页无有效条目"

    # 偏移优先用锚点法；锚点不可用时退回众数法
    offset = _anchor_offset(doc, raw)
    how = "anchor"
    if offset is None:
        counter = collections.Counter()
        for t, p, no, is_unit, pg in raw:
            if p > 0:
                counter[p - (pg + 1)] += 1
        if not counter:
            return [], 0, 0.0, "无有效页码"
        offset, hit = counter.most_common(1)[0]
        how = "mode"
        # 众数占比门槛不能太严：目录页的页码分布往往分散（单元头不带页码、
        # 跨栏重复、附录页码另算），实测占比常在 0.2~0.3 之间。
        # 只要众数明显高于次众数就采信，最终页码正确性由锚点/抽样核对兜底。
        top2 = counter.most_common(2)
        ratio = hit / max(1, sum(counter.values()))
        runner = top2[1][1] if len(top2) > 1 else 0
        if ratio < 0.15 or hit <= runner:
            return [], offset, 0.0, "偏移众数不可靠(%.2f)" % ratio
    if offset < 0 or offset > 40:
        return [], offset, 0.0, "偏移异常(%d)" % offset

    # 合并成单元
    units = []
    cur = None
    for t, p, no, is_unit, _pg in raw:
        if is_unit:
            if cur and (cur["lessons"] or cur["start"]):
                units.append(cur)
            cur = {"name": t, "start": (p + offset) if p > 0 else 0,
                   "lessons": []}
            continue
        pdf_page = p + offset
        if pdf_page < 1 or pdf_page > max_printed + 2:
            continue
        if cur is None:
            cur = {"name": "目录", "start": pdf_page, "lessons": []}
        if any(l["page"] == pdf_page for l in cur["lessons"]):
            continue
        if not cur["start"]:
            cur["start"] = pdf_page
        cur["lessons"].append({"no": no, "title": t, "page": pdf_page})
    if cur and (cur["lessons"] or cur["start"]):
        units.append(cur)
    return units, offset, 1.0, "ok(%s)" % how


# ---------------------------------------------------------------- 介绍文案

SUBJECT_INTRO = {
    "chinese": "本册围绕识字与写字、阅读与表达、综合运用与语文实践三条主线编排，"
               "选文兼顾主题思想与语言风格，分单元组织并设置口语交际、习作与单元习作练习，"
               "课后附写字表、词语表与阅读材料，便于自主学习与查阅。",
    "math": "本册围绕数与代数、图形与几何、统计与概率、综合与实践四大领域编排，"
            "每个单元由问题情境引入，配套例题、练习与思考题，"
            "并在部分单元后安排整理与复习，帮助学生建立数学模型与运算能力。",
    "english": "本册以话题（Topic）为主线组织语言材料，每单元设置 Starting Point、"
               "Let's talk、Let's learn、Let's spell 等板块，"
               "在听说读写的基础上逐步培养语音语感与初步的读写能力。",
    "physics": "本册围绕力、热、光、电等物理现象组织内容，"
               "通过实验、探究与实例分析，引导学生理解物理规律并学会运用所学解释生活现象。",
    "chemistry": "本册从物质组成与结构出发，依次介绍化学反应、溶液与酸碱盐等主题，"
                 "注重实验探究与定量分析相结合，培养学生的化学思维与实验技能。",
    "biology": "本册围绕生物体的结构、功能与生命活动规律展开，"
               "结合显微镜观察与实验活动，使学生理解生物与环境的关系并掌握基础研究方法。",
    "politics": "本册以社会主义核心价值观为主线，分单元组织经济、社会、法治与文化等内容，"
                "采用情境化、议题式呈现，引导学生联系生活理解道理并学会明辨是非。",
    "history": "本册按时间顺序组织中外历史重要事件与人物，"
               "以时间轴、地图与史料相互印证，帮助学生形成时空观念并理解历史发展脉络。",
    "geography": "本册以区域地理与人类活动的关系为主线，"
                 "结合地图判读与实地观察案例，训练学生的读图能力与综合分析素养。",
    "morallaw": "本册围绕品德与法治的核心议题组织内容，"
                "通过案例分析、情境讨论与实践活动，引导学生形成规则意识与责任意识。",
    "science": "本册从身边的科学现象出发，分单元组织观察、实验与探究活动，"
               "强调用证据说话，逐步培养学生的科学思维与动手能力。",
    "art": "本册围绕造型、色彩、构图与欣赏等基本要素展开，"
           "通过欣赏与实践相结合的方式，培养学生的审美能力与艺术表现力。",
    "music": "本册以唱歌、器乐欣赏与音乐实践为主线组织内容，"
             "注重审美感知与艺术表现的综合培养，帮助学生感受音乐之美。",
}


def extract_meta_text(doc):
    """从版权页（通常是第 2~4 页）抓出版社、主编、编写方式。"""
    blob = ""
    for i in range(min(6, len(doc))):
        blob += "\n" + doc[i].get_text()
    blob = clean(blob)
    pub = ""
    m = RE_PUB.search(blob) or RE_PUB2.search(blob)
    if m:
        pub = clean(m.group(1))
    ed = _pick_editor(blob)
    parts = []
    m_edu = RE_EDU.search(blob)
    if m_edu:
        parts.append(m_edu.group(1))
    if ed:
        parts.append(ed)
    editor = " · ".join(parts)
    ver = ""
    m = RE_VER.search(blob)
    if m:
        ver = clean(m.group(1))
    return pub, editor, ver


def build_intro(book, pub, editor, ver, unit_count, lesson_count):
    """拼介绍文案：优先用版权页信息，学科描述按学科模板补。"""
    subject = book.get("subject", "")
    tmpl = SUBJECT_INTRO.get(subject,
                             "本册依据课程标准编排，注重夯实基础、发展能力，"
                             "在系统的学习内容中培养学生的学科核心素养。")
    head = "《%s》" % book.get("title", "")
    if book.get("subTitle"):
        head += "（%s）" % book["subTitle"]
    bits = [head]
    if pub:
        bits.append("%s出版" % pub)
    if book.get("version"):
        bits.append("版本 %s" % book["version"])
    if ver:
        bits.append(ver)
    if editor:
        bits.append(editor)
    tail = tmpl
    if unit_count:
        tail += "全书共 %d 个单元、%d 个条目，已按单元整理目录，可直接点击跳转到对应页面。" % (
            unit_count, lesson_count)
    else:
        tail += "目录已按章节顺序整理，可直接点击跳转到对应页面。"
    return "，".join(bits) + "。" + tail


# ---------------------------------------------------------------- 主流程

def process_book(book, root):
    key = book["key"]
    src = os.path.join(root, book["src"].replace("/", os.sep))
    if not os.path.exists(src):
        return {"key": key, "ok": False, "reason": "源文件缺失"}
    try:
        doc = pymupdf.open(src)
    except Exception as e:
        return {"key": key, "ok": False, "reason": "PDF 打开失败: %s" % e}

    n_pages = len(doc)
    toc_pages = find_toc_pages(doc)
    units, offset, _c, note = extract_units(doc, toc_pages, n_pages)

    # 目录页整体合理性（多页合并后再评一次分）
    conf = 0.0
    entries = [(u["name"], l["title"], l["page"]) for u in units for l in u["lessons"]]
    if entries:
        pages = [e[2] for e in entries]
        inc = sum(1 for a, b in zip(pages, pages[1:]) if b >= a)
        inc_ratio = inc / max(1, len(pages) - 1)
        conf = 0.4 + 0.4 * inc_ratio + 0.2 * min(1.0, len(pages) / 30.0)
        note = "条目%d 页码递增%.2f 偏移%d %s" % (len(entries), inc_ratio, offset,
                                                ("目录页%s" % (toc_pages[:3],)))

    pub, editor, ver = extract_meta_text(doc)
    if not pub:
        pub = book.get("publisher") or "人民教育出版社"
    if not book.get("version"):
        book["version"] = book.get("version", "")

    lesson_count = sum(len(u["lessons"]) for u in units)

    # 上线闸门：目录页码必须真的指向对应内容。
    # 统计置信度（页码递增性、去重率）只能说明「像目录」，说明不了「页码对」——
    # 教师用书这类册的目录页码与 PDF 页码偏移不统一，统计看着漂亮、实际全错。
    hit_rate, hit_note = (0.0, "无目录")
    if units:
        hit_rate, hit_note = verify_units(doc, units)
    verified = bool(units) and hit_rate >= 0.6
    if units and not verified:
        note = "%s；页码抽查未达标(%.0f%%) %s" % (note, hit_rate * 100, hit_note)

    intro = build_intro(book, pub, editor, ver, len(units), lesson_count)

    return {
        "key": key,
        "ok": verified,
        "reason": note,
        "confidence": round(conf, 3),
        "hitRate": round(hit_rate, 3),
        "tocPages": [p + 1 for p in toc_pages],
        "pageOffset": offset,
        "publisher": pub,
        "editor": editor,
        "intro": intro,
        # 未通过校验的册不输出目录，只保留介绍
        "units": units if verified else [],
    }


def main():
    ap = argparse.ArgumentParser(description="从教材 PDF 提取介绍与目录")
    ap.add_argument("--manifest", default="data/textbook/manifest.json")
    ap.add_argument("--out", default="data/textbook/curric.json")
    ap.add_argument("--only", default="", help="只处理指定 key，逗号分隔")
    ap.add_argument("--stage", default="", help="只处理该学段：primary/middle/high")
    ap.add_argument("--limit", type=int, default=0, help="只处理前 N 册（调试用）")
    args = ap.parse_args()

    mf = json.load(open(args.manifest, encoding="utf-8"))
    root = mf["root"]
    books = mf["books"]
    if args.only:
        want = {x for x in args.only.split(",") if x}
        books = [b for b in books if b["key"] in want]
    if args.stage:
        books = [b for b in books if b["stage"] == args.stage]
    if args.limit:
        books = books[:args.limit]

    print("待处理 %d 册" % len(books), flush=True)
    t0 = time.time()
    results = []
    ok = low = bad = 0
    for i, b in enumerate(books, 1):
        r = process_book(b, root)
        results.append(r)
        if r.get("ok"):
            ok += 1
        elif r.get("confidence", 0) > 0:
            low += 1
        else:
            bad += 1
        if i % 10 == 0 or i == len(books):
            print("  %d/%d 册 · 成功 %d · 待复核 %d · 失败 %d · 用时 %.0f 秒"
                  % (i, len(books), ok, low, bad, time.time() - t0), flush=True)

    # 输出结构与 Go 侧 tbCurricFile 对齐：books 是 map[key]record，
    # 不是 list —— Go 读取时按 key 直接索引，不用遍历。
    payload = {
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "root": root,
        "books": {r["key"]: {
            "publisher": r.get("publisher", ""),
            "editor": r.get("editor", ""),
            "intro": r.get("intro", ""),
            "confidence": r.get("confidence", 0),
            "hitRate": r.get("hitRate", 0),
            "units": r.get("units", []),
            "_reason": r.get("reason", ""),
        } for r in results},
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print()
    print("输出 %s" % args.out)
    print("共 %d 册：成功 %d · 待复核 %d · 失败 %d"
          % (len(results), ok, low, bad))
    # 列出待复核的册，便于人工确认
    if low or bad:
        print()
        print("需人工复核的册：")
        for r in results:
            if not r.get("ok"):
                print("   %-34s conf=%-6s %s"
                      % (r["key"], r.get("confidence", 0), r.get("reason", "")[:44]))


if __name__ == "__main__":
    main()
