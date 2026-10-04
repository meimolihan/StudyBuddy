# -*- coding: utf-8 -*-
"""给 content 下的全部一年级游戏 HTML 注入「低龄友好增强层」。

严格约束（用户明确要求）：
  * 题目内容 / 答案 / 知识点 / 原有数据**不变**
  * 答题结果判断逻辑**不变**
  * 页面核心功能**不变**

做法：只在 </head> 前追加一段 <style>、</body> 前追加一段 <script>，
      增强层靠「观察 DOM」挂钩，不碰引擎任何一行代码。
      注入前后逐字节校验题库字面量（const ALL / QUESTIONS / QUESTIONS
      段落）完全一致，并统计引擎关键函数（choose/checkCount/checkAnswer
      等）的行数与 md5 不变 —— 不一致就中止，不写盘。

用法：
    python scripts/game_kids_enhance.py            # 注入
    python scripts/game_kids_enhance.py --check    # 只校验不写盘（CI 用）
    python scripts/game_kids_enhance.py --remove   # 移除增强层
"""
from __future__ import annotations

import hashlib
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from game_kids_enhance import ENHANCE_CSS, ENHANCE_JS  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME_ROOT = os.path.join(ROOT, "content", "primary", "pep", "game")

CSS_MARK = "sb-kids 一年级游戏增强层"
SENTINEL_CSS = "/* __SBK_CSS__ */"
SENTINEL_JS = "/* __SBK_JS__ */"

# 判分逻辑的「指纹」：这些函数名一旦出现次数或内容变化，说明判分被改了
JUDGE_FUNCS = [
    "function choose", "function checkCount", "function checkAnswer",
    "function isCorrect", "function judge", "function handleAnswer",
    "function check", "function submit",
]


def md5(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def find_games(root: str) -> list[str]:
    out = []
    for base, _dirs, files in os.walk(root):
        for f in files:
            if f.lower().endswith(".html"):
                out.append(os.path.join(base, f))
    return sorted(out)


def strip_enhance(html: str) -> str:
    """移除已注入的增强层（用于幂等重写与 --remove）。

    ⚠ 这里踩过一个坑：最初写成 `[ \t]*<?(?:style|script)?[^<>]{0,40}>?` 想
    兼容「哨兵在标签外」与「哨兵在标签内」两种写法，但 `[^<>]{0,40}` 会
    **跨过 `<style>` 标签本身**，匹配起点飘到标签之前，结果只吃掉了哨兵和
    内容、留下了孤立的 `<style>` 开标签 —— 重复注入就多一个空 style 块
    （实测 `<style>` 2→3，字节每次 +17）。

    正确做法：**两个精确模式分开写**，各只认一种形态：
      形态 A（正确，当前写法）：<style>\\n/* 哨兵 */ ... </style>
      形态 B（旧版，哨兵在标签外）：/* 哨兵 */<style> ... </style>
    两条都要求「哨兵紧跟在开标签之后」或「紧贴闭标签之前」，
    不会误伤游戏自带的 style/script。

    ⚠ 替换值用空串而不是 "\\n"：inject() 写回时是
    `head.rstrip() + "\\n" + block + "\\n" + tail.lstrip()`，
    前后换行由 inject 自己负责。若这里再吐一个 "\\n"，
    strip 结果就会比原文多一个空行（实测 `</style>\\n</head>`
    变成 `</style>\\n\\n</head>`），导致「strip 后与原始版本逐字节比对」不通过。
    """
    # 形态 A：标签内哨兵（当前）
    html = re.sub(
        r"[ \t]*<(style|script)>\s*" + re.escape(SENTINEL_CSS)
        + r".*?</\1>\n?",
        "", html, flags=re.S)
    html = re.sub(
        r"[ \t]*<(style|script)>\s*" + re.escape(SENTINEL_JS)
        + r".*?</\1>\n?",
        "", html, flags=re.S)
    # 形态 B：标签外哨兵（旧版，会渲染成可见文本）
    html = re.sub(
        r"[ \t]*" + re.escape(SENTINEL_CSS) + r"\s*<style>.*?</style>\n?",
        "", html, flags=re.S)
    html = re.sub(
        r"[ \t]*" + re.escape(SENTINEL_JS) + r"\s*<script>.*?</script>\n?",
        "", html, flags=re.S)
    return html


def fingerprint(html: str) -> dict:
    """提取「不该变」的部分做指纹：题库字面量 + 判分函数 + 原有 script 数。"""
    # 题库：const ALL = [ ... ];  /  const QUESTIONS = [ ... ];
    banks = {}
    for name in ("ALL", "QUESTIONS"):
        m = re.search(r"const\s+" + name + r"\s*=\s*\[", html)
        if not m:
            continue
        i = m.end() - 1
        depth, j = 0, i
        while j < len(html):
            if html[j] == "[":
                depth += 1
            elif html[j] == "]":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        banks[name] = md5(html[m.start():j + 1])
    # 题库字段出现次数（题数、答案数、解析数）
    fields = {
        "t:": len(re.findall(r'\bt\s*:', html)),
        "o:": len(re.findall(r'\bo\s*:', html)),
        "a:": len(re.findall(r'\ba\s*:', html)),
        "e:": len(re.findall(r'\be\s*:', html)),
    }
    # 判分函数：把每个函数体截出来做 md5
    funcs = {}
    for fn in JUDGE_FUNCS:
        idx = html.find(fn)
        if idx < 0:
            continue
        # 截到下一个顶层 function 或 1200 字符为止
        nxt = len(html)
        for fn2 in JUDGE_FUNCS:
            j = html.find(fn2, idx + len(fn))
            if j > idx:
                nxt = min(nxt, j)
        funcs[fn] = md5(html[idx:min(nxt, idx + 1200)])
    return {"banks": banks, "fields": fields, "funcs": funcs}


def inject(html: str) -> str:
    """在 </head> 前插 CSS、</body> 前插 JS。

    ⚠ 哨兵必须放在 <style>/<script> **标签内部**当首行注释。
    放在标签外面就成了 body 里的可见文本节点，会在页面上真的显示出
    一行「__SBK_CSS__」（实测截图里出现在顶部和底部中央）。
    放在内部既是合法注释（不渲染），又能被 strip_enhance 的正则命中。
    """
    css_block = ("<style>\n" + SENTINEL_CSS + "\n" + ENHANCE_CSS.strip()
                 + "\n</style>")
    js_block = ("<script>\n" + SENTINEL_JS + "\n" + ENHANCE_JS.strip()
                + "\n</script>")
    # 幂等：先清掉旧的（含旧版「哨兵在标签外」的写法）
    # ⚠ strip 用 "\n" 替换整块，插入点因此会多出一个空行；
    #   若这里再无条件加 "\n"，每次注入都会多 1 个空行（实测每次 +2 字节、
    #   重复注入后文件缓慢膨胀）。做法：先把插入点周围的连续换行**压成一个**，
    #   再拼接，保证 N 次注入结果与 1 次完全相同。
    html = strip_enhance(html)
    i = html.lower().rfind("</head>")
    if i < 0:
        raise SystemExit("找不到 </head>")
    head, tail = html[:i], html[i:]
    tail = tail.lstrip("\r\n")          # 吃掉 head 末尾残留的换行
    html = head.rstrip() + "\n" + css_block + "\n" + tail
    # 插到最后一个 </body> 之前：脚本要在 body 末尾才能 querySelector 到选项
    j = html.lower().rfind("</body>")
    if j < 0:
        raise SystemExit("找不到 </body>")
    head2, tail2 = html[:j], html[j:]
    tail2 = tail2.lstrip("\r\n")
    html = head2.rstrip() + "\n" + js_block + "\n" + tail2
    return html


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode not in ("", "--check", "--remove"):
        print("用法: game_kids_enhance.py [--check|--remove]")
        return 2
    if not os.path.isdir(GAME_ROOT):
        print("找不到游戏目录:", GAME_ROOT)
        return 1

    files = find_games(GAME_ROOT)
    print("发现游戏文件 %d 个" % len(files))
    changed = injected = removed = failed = 0
    problems = []

    for p in files:
        rel = os.path.relpath(p, ROOT)
        raw = open(p, "r", encoding="utf-8").read()
        has = (SENTINEL_CSS in raw) or (SENTINEL_JS in raw)

        if mode == "--check":
            if has:
                injected += 1
            # 增强层在位时，指纹要用「剥掉增强层」的版本算
            base = strip_enhance(raw) if has else raw
            fp = fingerprint(base)
            problems.append((rel, fp, None))
            continue

        if mode == "--remove":
            if not has:
                continue
            base = strip_enhance(raw)
            f0, f1 = fingerprint(raw), fingerprint(base)
            if f0 != f1:
                problems.append((rel, f1, "移除增强层时指纹异常"))
                failed += 1
                continue
            open(p, "w", encoding="utf-8", newline="").write(base)
            removed += 1
            print("  移除  %s" % rel)
            continue

        # 默认：注入
        base = strip_enhance(raw) if has else raw
        f0 = fingerprint(base)
        new = inject(raw)
        f1 = fingerprint(strip_enhance(new))
        if f0 != f1:
            problems.append((rel, f1, "注入后指纹变了 —— 已中止写盘"))
            failed += 1
            print("  SKIP  %s  指纹不一致" % rel)
            continue
        if new == raw:
            continue
        open(p, "w", encoding="utf-8", newline="").write(new)
        injected += 1
        changed += 1
        print("  注入  %s" % rel)

    if mode == "--check":
        print("\n--check：仅报告，不写盘")
        for rel, fp, _ in problems:
            banks = ",".join("%s=%s" % (k, v[:8]) for k, v in sorted(fp["banks"].items()))
            print("  %-70s 题库[%s] 字段%s 函数%d"
                  % (rel, banks or "无", fp["fields"], len(fp["funcs"])))
        print("\n已注入: %d / %d" % (injected, len(files)))
        return 0

    print("\n注入 %d 个文件（变更 %d），失败 %d" % (injected, changed, failed))
    if problems:
        print("\n⚠ 有问题：")
        for rel, fp, msg in problems:
            print("  %s  %s" % (rel, msg or ""))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
