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
  6. 纯 CRLF 换行（与项目内容目录约定一致）
  7. 每个游戏 8 道题（一年级游戏的统一规格）

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

        for token in ("<!DOCTYPE html>", '<html lang="zh-CN">', "</head>",
                      "</body>", "</html>", "const MODE =",
                      'id="stage"', 'id="opts"', 'id="fb"', 'id="done"',
                      "--g-bg"):
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

        crlf, lf = raw.count(b"\r\n"), raw.count(b"\n")
        if crlf != lf:
            problems.append("%s 换行混用（CRLF=%d LF=%d）" % (rel, crlf, lf))

        problems.extend(check_bank(rel, text))
    return fresh, problems


def check_bank(rel, text):
    """解析 var ALL 块并逐题校验。

    按行处理：生成器保证每题独占一行，因此不需要处理嵌套结构，
    也不需要写状态机 —— 用正则反而比逐字符扫描更容易读懂。
    """
    problems = []
    m = re.search(re.escape(MARKER) + r"(.*?)\n\];", text, re.S)
    if not m:
        return ["%s 题库块未匹配（注意：必须是 `const ALL = [`，写成 var 会让 ParseBank 读不到）" % rel]

    qs = [ln.strip().rstrip(",") for ln in m.group(1).split("\n")]
    qs = [ln for ln in qs if ln.startswith("{t:")]
    if len(qs) != WANT_PER_GAME:
        problems.append("%s 题数 %d（预期 %d）" % (rel, len(qs), WANT_PER_GAME))

    for i, line in enumerate(qs, 1):
        at = "%s 第%d题" % (rel, i)
        lo, hi = line.find("o:["), line.find("],a:")
        opts = re.findall(r'"([^"]*)"', line[lo + 3:hi]) if lo >= 0 and hi > lo else []
        if len(opts) != OPTION_COUNT:
            problems.append("%s 选项 %d 个（预期 %d）" % (at, len(opts), OPTION_COUNT))
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
            elif not letters[0].isalpha() or ord(letters[0]) - 65 >= len(opts):
                problems.append("%s 答案 %s 越界（选项 %d 个）" % (at, letters[0], len(opts)))

        em = re.search(r'e:"([^"]*)"', line)
        if not em or not em.group(1).strip():
            problems.append("%s 解析为空" % at)
    return problems


def main(argv):
    root = argv[1] if len(argv) > 1 else DEFAULT_ROOT
    if not os.path.isdir(root):
        print("找不到目录：%s" % root)
        return 2

    fresh, problems = scan(root)
    # 顺带统计题目总数，方便对照
    total = 0
    for p in fresh:
        text = open(p, encoding="utf-8").read()
        m = re.search(re.escape(MARKER) + r"(.*?)\n\];", text, re.S)
        if m:
            total += sum(1 for ln in m.group(1).split("\n") if ln.strip().startswith("{t:"))

    print("新引擎游戏 %d 个（另有 %d 个早期独立游戏不参与校验）"
          % (len(fresh), len(LEGACY)))
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
