#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验生成的单元游戏 HTML。

这是 gen_games.py 的验收 counterpart：生成器里有断言，但断言只在
**构造题库时**生效；这里从**落盘后的文件**重新解析一遍，确认写出去的东西
真的符合约定 —— 两者都要，因为序列化环节也可能出错（转义、截断、换行）。

检查项：
  1. 结构完整（doctype / head / body / 关键 DOM id）
  2. 每题 4 个选项、无重复
  3. 答案下标落在选项范围内
  4. 解析（e 字段）非空 —— 家长靠它陪孩子复习
  5. 主题变量 --g-* 存在
  6. 换行不混用
  7. 每个游戏 8 道题（一年级游戏的统一规格）

============================ 两类页面，两套口径 ============================
game/grade1 下实际有两种结构完全不同的页面，**不能用同一把尺子量**：

  A. 新引擎页（engine.py 生成，grade1 共 235 个）
     DOM 约定：`const MODE =` / id="stage" / id="opts" / id="fb" / id="done"
     主题变量：`--g-bg`；题数固定 8；每题固定 4 个选项。

  B. 旧自测页（apply_game_grade2_premium 从 choose/judge 树复制，424 个）
     DOM 约定：`const ALL = [` + id="quiz" / id="submit" / .opt / .q
     主题变量：`--brand`（没有 --g-bg）；题数 20~40 不一；判断题只有 2 个选项。

⚠️ 改造前本脚本只按 A 的口径检查，B 类每页都报 7 项「缺少」，
   1459 个问题里绝大多数是这种**假阳性**（例：
   'volume1/chinese/01-我上学了（判断）/01-我上学了.html' 缺 const MODE /
   #stage / #opts / #fb / #done / --g-bg / 题库块未匹配 —— 其实它是一道
   完全正常的判断题页）。

现在按 `const MODE =` 是否存在自动分流，问题数才反映真实缺陷。

============================ 换行判据 ============================
⚠️ 原来写的是 `raw.count(b"\\r\\n") != raw.count(b"\\n")` —— 后者**把 CRLF
   也算进去了**，所以纯 LF 文件（CRLF=0, LF=1405）必然判成「混用」。
   而内容目录里纯 LF 文件是合法的（实测 game/grade1 = 208 CRLF + 33 LF，
   那 33 个是单元级综合游戏，git HEAD 里本来就是 LF）。
   正确判据是数**裸 LF**：`(?<!\\r)\\n`。

用法：python tools/gamegen/verify_games.py [根目录]
"""

import os
import re
import sys

DEFAULT_ROOT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..",
    "content", "primary", "pep", "game", "grade1")

# 早先手工做的两个独立游戏：自带完整交互，不走本生成器，不参与结构校验
LEGACY = ("01-天地人", "01-数学游戏（数一数、比多少）")

WANT_PER_GAME = 8
OPTION_COUNT = 4

# 两类页面的结构约定。按 `const MODE =` 是否存在分流（见模块 docstring）。
ENGINE_TOKENS = ("<!DOCTYPE html>", '<html lang="zh-CN">', "</head>",
                 "</body>", "</html>", "const MODE =",
                 'id="stage"', 'id="opts"', 'id="fb"', 'id="done"',
                 "--g-bg")
SELFTEST_TOKENS = ("<!DOCTYPE html>", '<html lang="zh-CN">', "</head>",
                   "</body>", "</html>", 'id="quiz"', 'id="submit"',
                   "--brand", 'id="score"', 'id="result"')

# 与 textbook.ParseBank 里的 marker 保持一致（那边是硬编码字面量）。
# 单独提成常量是为了让「注释里误写这个字面量」能被自动发现。
MARKER = "const ALL = ["


def scan(root):
    """遍历所有游戏文件，返回 (新引擎文件列表, 问题列表)。"""
    files = []
    for dirpath, _, names in os.walk(root):
        for n in sorted(names):
            if n.endswith(".html"):
                files.append(os.path.join(dirpath, n))
    files.sort()

    fresh, problems = [], []
    for path in files:
        name = os.path.basename(path)
        if any(k in name for k in LEGACY):
            continue
        fresh.append(path)

        raw = open(path, "rb").read()
        text = raw.decode("utf-8")
        rel = os.path.relpath(path, root).replace("\\", "/")

        # ⚠️ 按页面类型选检查项。用新引擎的尺子量旧自测页会刷出一堆假阳性。
        is_engine = "const MODE =" in text
        tokens = ENGINE_TOKENS if is_engine else SELFTEST_TOKENS
        for token in tokens:
            if token not in text:
                problems.append("%s 缺少 %s" % (rel, token))

        # ParseBank 用 strings.Index 取「题库声明」的**第一个**出现处。
        # 若注释里也写了这个字面量，它会匹配到注释，后面的正文解析不出任何题 ——
        # 症状是「游戏能正常玩，但刷题系统读到 0 题」，极难靠肉眼发现。
        first = text.find(MARKER)
        if first < 0:
            problems.append("%s 找不到题库声明（%s）" % (rel, MARKER))
        else:
            after = text[first + len(MARKER):first + len(MARKER) + 12]
            if not after.lstrip().startswith("{"):
                problems.append(
                    "%s 题库声明后不是题对象（实际是 %r）—— 多半是注释里也写了那个字面量，"
                    "ParseBank 匹配到了注释" % (rel, after))

        # ⚠️ 必须数**裸 LF**。原来写的是 count(b"\n")，而它把 CRLF 也算进去，
        #   于是纯 LF 文件（CRLF=0, LF=1405）必然被判成「混用」——
        #   而纯 LF 在本内容目录里是合法的（grade1 有 33 个单元级综合游戏
        #   本来就是 LF，git HEAD 可查）。
        crlf = raw.count(b"\r\n")
        bare_lf = len(re.findall(rb"(?<!\r)\n", raw))
        if crlf and bare_lf:
            problems.append("%s 换行混用（CRLF=%d 裸LF=%d）" % (rel, crlf, bare_lf))

        problems.extend(check_bank(rel, text, is_engine))
    return fresh, problems


def check_bank(rel, text, is_engine=True):
    """解析题库块并逐题校验。

    按行处理：生成器保证每题独占一行，因此不需要处理嵌套结构，
    也不需要写状态机 —— 用正则反而比逐字符扫描更容易读懂。

    ⚠️ 旧自测页的题数（20~40）和选项数（判断题只有 2 个）都与新引擎不同，
       所以期望值只在 is_engine 时才强制。
    """
    problems = []
    want = WANT_PER_GAME if is_engine else None
    want_opt = OPTION_COUNT if is_engine else None
    blk = bank_block(text)
    if blk is None:
        return ["%s 题库块未匹配（注意：必须是 `const ALL = [`，写成 var 会让 ParseBank 读不到）" % rel]

    qs = [ln.strip().rstrip(",") for ln in blk.split("\n")]
    qs = [ln for ln in qs if ln.startswith("{t:")]
    if want and len(qs) != want:
        problems.append("%s 题数 %d（预期 %d）" % (rel, len(qs), want))
    if not qs:
        problems.append("%s 题库为空 —— ParseBank 会读到 0 题" % rel)

    for i, line in enumerate(qs, 1):
        at = "%s 第%d题" % (rel, i)
        lo, hi = line.find("o:["), line.find("],a:")
        opts = re.findall(r'"([^"]*)"', line[lo + 3:hi]) if lo >= 0 and hi > lo else []
        if want_opt and len(opts) != want_opt:
            problems.append("%s 选项 %d 个（预期 %d）" % (at, len(opts), want_opt))
        if len(opts) < 2:
            problems.append("%s 选项不足 2 个：%s" % (at, opts))
        if len(set(opts)) != len(opts):
            problems.append("%s 选项有重复：%s" % (at, opts))

        am = re.search(r'a:\[([^\]]*)\]', line)
        if not am:
            problems.append("%s 缺答案" % at)
        else:
            # 答案必须是带引号的**字母**：ParseBank 的 readArray 只收字符串，
            # 裸字母（a:[B]）既是未定义标识符，也会让 readArray 返回空数组。
            letters = re.findall(r'"([A-Z])"', am.group(1))
            if not letters:
                problems.append("%s 答案不是带引号的字母：%s" % (at, am.group(1).strip()))
            else:
                # ⚠️ 多选题（a:["C","D"]）的每个字母都要查，不能只看第一个 ——
                #   实测存量里存在多选题，只查 letters[0] 会漏掉越界的 D/E。
                for L in letters:
                    if ord(L) - 65 >= len(opts):
                        problems.append("%s 答案 %s 越界（选项 %d 个）" % (at, L, len(opts)))
                if len(set(letters)) != len(letters):
                    problems.append("%s 答案有重复字母：%s" % (at, letters))

        em = re.search(r'e:"([^"]*)"', line)
        if not em or not em.group(1).strip():
            problems.append("%s 解析为空" % at)
    return problems


def bank_block(text):
    """截出题库字面量。**收尾换行可选** —— 旧自测页的题库末条与 `];`
    紧贴（实测 grade2/volume2/math/02-求一个数的几倍是多少.html 原文如此），
    写死 `\\n\\];` 会让这些页面全部报「题库块未匹配」（假阳性）。
    ⚠️ 这里是全脚本唯一的题库正则，scan/check_bank/main 三处共用 ——
    改造前 main() 里另有一份副本，两份口径不一致过。
    """
    m = re.search(re.escape(MARKER) + r"(.*?)(?:\r?\n)?\];", text, re.S)
    return m.group(1) if m else None


def main(argv):
    root = argv[1] if len(argv) > 1 else DEFAULT_ROOT
    if not os.path.isdir(root):
        print("找不到目录：%s" % root)
        return 2

    fresh, problems = scan(root)
    # 顺带统计题目总数与页面类型，方便对照
    total = 0
    n_engine = 0
    for p in fresh:
        text = open(p, encoding="utf-8").read()
        if "const MODE =" in text:
            n_engine += 1
        blk = bank_block(text)
        if blk:
            total += sum(1 for ln in blk.split("\n")
                         if ln.strip().startswith("{t:"))

    print("参与校验 %d 个（新引擎 %d + 旧自测页 %d，另有 %d 个早期独立游戏不参与）"
          % (len(fresh), n_engine, len(fresh) - n_engine, len(LEGACY)))
    print("题目总数 %d，平均 %.1f 题/个" % (total, total / max(1, len(fresh))))
    if problems:
        print("发现 %d 个问题：" % len(problems))
        for x in problems[:40]:
            print("  - " + x)
        return 1
    print("全部通过 ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
