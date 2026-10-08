# -*- coding: utf-8 -*-
"""自测页生成器 —— 以后新增自测页**只写题库**，不再手写 1000 多行壳。

============================ 它解决什么 ============================
改造前：新增一个自测页，要手写 HTML 骨架 + 5.3 KB CSS + 8.9 KB 引擎 JS，
        合计 1000 多行，且 424 个存量页各写了一遍（内容完全相同）。
改造后：本文件提供题库 DSL，`build()` 负责渲染壳 + 注入增强层 + 写盘。

============================ 目录约定（实测 424 个存量页的规律）========================
    content/primary/pep/choose/grade<N>/volume<V>/<subject>/NN-单元/NN-课名.html
        ↑ 选择题源页（纯净壳 + 题库）—— **生成器写这里**
    content/primary/pep/judge/grade<N>/volume<V>/<subject>/NN-单元/NN-课名.html
        ↑ 判断题源页 —— 同上

    单元目录**不需要**题型后缀：choose 与 judge 是两个平行的顶层目录，
    `choose/grade1/.../01-阅读/` 与 `judge/grade1/.../01-阅读/` 天然不冲突。
    （游戏模块存在时曾需要 `（选择）`/`（判断）` 后缀，因为 gameRaw 的路径
      第 3 段固定是 `game`，两种题型挤在同一层会互相覆盖；
      该模块已于 2026-10-08 整体移除，此约束随之作废。）

============================ 换行 ============================
⚠️ 必须逐文件探测，不能全局写死。内容目录里 CRLF / LF **混存**。
   但 choose/ + judge/ 的 1908 个**源页实测 100% 是 CRLF**，
   所以新建源页默认 CRLF（与既有源页保持一致），并允许按目标目录探测覆盖。

   读写必须对称：读用 `newline=""`、写也用 `newline=""`。
   用通用换行模式读（`open(p).read()` 会把 \\r\\n 翻译成 \\n）再原样写回，
   整份 CRLF 文件会被静默改写成 LF（实测 204 个文件中招）。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import selftest_shell as shell  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PEP = os.path.join(ROOT, "content", "primary", "pep")

VOL_LABEL = {"volume1": "上册", "volume2": "下册"}
SUBJ_LABEL = {"chinese": "语文", "math": "数学"}
QTYPE_LABEL = {"choose": "选择", "judge": "判断"}
GRADES = (1, 2, 3, 4, 5, 6)
LETTERS = "ABCD"

# 盘上既有源页的默认学生名。新增页沿用同一字段（家长可直接改）。
DEFAULT_STUDENT = "郭奕凡"


# ---------------------------------------------------------------- 题库 DSL
def q(stem, options, answer, explain, t="s"):
    """构造一道题。**生成期就断言**，写盘前拦住所有低级错。

    :param stem:    题干
    :param options: 选项列表，2~4 个
    :param answer:  "B" 或 ["C", "D"]（自动归一成 list）
    :param explain: 解析文本，会显示在判分后的答案行
    :param t:       "s" 单选 / "m" 多选 / "j" 判断

    ⚠️ 为什么必须有断言：ParseBank 遇到格式不对的条目是**静默丢弃整题**，
      页面上表现为「题库共 N 题」但实际少一题，verify_games 要到很后面
      才报出来。这里提前拦。
    """
    assert t in ("s", "m", "j"), "t 只能是 s/m/j，收到 %r" % (t,)
    opts = list(options)
    assert 2 <= len(opts) <= 4, "选项数必须 2~4，收到 %d：%r" % (len(opts), opts)
    assert len(set(opts)) == len(opts), "选项重复：%r" % (opts,)
    for o in opts:
        assert isinstance(o, str) and o.strip(), "选项必须是非空字符串：%r" % (o,)

    ans = [answer] if isinstance(answer, str) else list(answer)
    assert ans, "答案不能为空"
    for a in ans:
        # ⚠️ 必须是单个字母，且落在选项范围内。写成数字或裸标识符
        #   会被 ParseBank 的 readArray 整题丢弃（静默 0 题）。
        assert isinstance(a, str) and len(a) == 1 and a in LETTERS, \
            "答案必须写成带引号的字母（A~D），收到 %r" % (a,)
        assert LETTERS.index(a) < len(opts), \
            "答案 %s 超出选项范围（共 %d 个选项）" % (a, len(opts))
    assert len(set(ans)) == len(ans), "答案里有重复字母：%r" % (ans,)

    if t == "s":
        assert len(ans) == 1, "单选题只能有 1 个答案，收到 %r" % (ans,)
    elif t == "m":
        assert len(ans) >= 2, "多选题至少 2 个答案，收到 %r" % (ans,)
    else:  # j
        assert len(opts) == 2 and len(ans) == 1, \
            "判断题必须是 2 个选项 + 1 个答案，收到 %d 选项 %r" % (len(opts), ans)
        assert set(opts) == {"正确", "错误"}, \
            "判断题选项固定为 ['正确', '错误']，收到 %r" % (opts,)

    assert isinstance(stem, str) and stem.strip(), "题干不能为空"
    assert isinstance(explain, str) and explain.strip(), "解析不能为空"
    # 这些字符会破坏 JS 字面量或题库解析
    for name, val in (("题干", stem), ("解析", explain)):
        for bad, why in (("\n", "换行"), ("\r", "回车"),
                         ('"', '双引号'), ("\\", "反斜杠")):
            assert bad not in val, "%s里不能有%s（%r）" % (name, why, bad)
    for o in opts:
        for bad, why in (("\n", "换行"), ("\r", "回车"),
                         ('"', '双引号'), ("\\", "反斜杠")):
            assert bad not in o, "选项 %r 里不能有%s" % (o, why)

    return {"t": t, "q": stem.strip(), "o": opts, "a": ans, "e": explain.strip()}


def judge(stem, is_true, explain):
    """判断题糖：`is_true` 为真 → 答案 A（正确）。"""
    return q(stem, ["正确", "错误"], "A" if is_true else "B", explain, t="j")


# ---------------------------------------------------------------- 题库序列化
def js_str(s: str) -> str:
    """Python 字符串 → JS 字符串字面量（含双引号）。

    ⚠️ 刻意手工转义而不是 json.dumps：json.dumps 默认输出 **ASCII 转义**
      （中文变成 \\uXXXX），题库会变成一整页难以阅读和维护的乱码。
    """
    out = []
    for ch in s:
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        else:
            out.append(ch)
    return '"' + "".join(out) + '"'


def bank_js(items) -> str:
    """题库 → JS 字面量。**每题独占一行**（verify_games.check_bank 按行解析）。

    ⚠️ 头部是 `const ALL = [ {...},\n {...}]` 的形式，首行左括号后紧跟
      第一题，末题后 `];` 收尾 —— 与存量 1908 个源页的写法完全一致。

    ⚠️ 逗号后有一个空格：o:["正确", "错误"]。这是存量源页的既有约定
      （反推-重渲染-逐字节比对时差这一个空格就会全量漂移）。
      注意分隔符是在**加引号之后**拼的：若写成 `", ".join('"x"')` 之类的
      交叉形式，引号会被写进引号内部，变成 o:["\\"正确\\""...]。
    """
    lines = []
    for it in items:
        ans = ", ".join(js_str(a) for a in it["a"])
        opts = ", ".join(js_str(o) for o in it["o"])
        lines.append('{t:%s,q:%s,o:[%s],a:[%s],e:%s}' % (
            js_str(it["t"]), js_str(it["q"]), opts, ans, js_str(it["e"])))
    return "const ALL = [ " + ",\n ".join(lines) + "];", len(items)


# ---------------------------------------------------------------- 路径
def bank_path(grade: int, volume: str, subject: str, qtype: str,
              unit: str, filename: str) -> str:
    """源页绝对路径（生成器的写入目标）。"""
    if grade not in GRADES:
        raise ValueError("grade 必须在 %s 内，收到 %r" % (str(list(GRADES)), grade))
    if volume not in VOL_LABEL:
        raise ValueError("volume 必须是 volume1/volume2，收到 %r" % (volume,))
    if subject not in SUBJ_LABEL:
        raise ValueError("subject 必须是 chinese/math，收到 %r" % (subject,))
    if qtype not in QTYPE_LABEL:
        raise ValueError("qtype 必须是 choose/judge，收到 %r" % (qtype,))
    return os.path.join(PEP, qtype, "grade%d" % grade, volume, subject, unit, filename)


# ---------------------------------------------------------------- 换行
def detect_eol(text: str) -> str:
    """探测文本的换行风格。内容目录 CRLF/LF 混存，必须逐文件判断。"""
    return "\r\n" if "\r\n" in text else "\n"


def to_crlf(text: str) -> str:
    """统一转成 CRLF（新建源页的约定，与既有 1908 个源页一致）。"""
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r\n")


# ---------------------------------------------------------------- 渲染
def render(items, *, grade, volume, subject, unit, lesson, broadcast,
           student=DEFAULT_STUDENT, per_round=10, qtype="choose") -> str:
    """渲染完整 HTML 文本（LF 换行，未写盘）。"""
    if not items:
        raise ValueError("题库为空")
    if len(items) < per_round:
        raise ValueError("题库只有 %d 题，少于每批抽取数 %d —— 页面会抽不满"
                         % (len(items), per_round))

    types = set(it["t"] for it in items)
    has_judge = "j" in types
    # 判断题页（judge 树）必须带 j；选择题页（choose 树）绝不能带 j
    if qtype == "judge" and not has_judge:
        raise ValueError("qtype=judge 但题库里没有 t='j' 的题")
    if qtype == "choose" and has_judge:
        raise ValueError("qtype=choose 的题库不能含 t='j'（判断题请放 judge 树）")

    bank, count = bank_js(items)
    gname = {1: "一", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六"}[grade]
    sname = SUBJ_LABEL[subject]
    vname = VOL_LABEL[volume]
    # ⚠️ 有「级」字：一年级语文上册。漏掉会与存量 1908 个源页的
    #   <title> / <h1> / <div class="foot"> 三处全部不一致。
    subject_line = "%s年级%s%s" % (gname, sname, vname)
    full_title = "%s 自测 · %s · %s" % (subject_line, unit, lesson)
    if has_judge:
        full_title += " · 判断题"
    sub_line = "%s · %s%s" % (unit, lesson, " · 判断题" if has_judge else "")

    html = shell.HTML
    html = html.replace("{{TITLE}}", full_title)
    html = html.replace("{{H1}}", "%s · 自测卷（人教版）" % subject_line)
    html = html.replace("{{SUB}}", sub_line)
    html = html.replace("{{STUDENT}}", student)
    html = html.replace("{{BANK_COUNT}}", str(count))
    html = html.replace("{{PER_ROUND}}", str(per_round))
    html = html.replace("{{BROADCAST}}", broadcast)
    html = html.replace("{{FOOT}}", "人教版%s · 每题 10 分，满分 = 本批题数 × 10" % subject_line)
    # ⚠️ CSS 只能去首尾**换行**，不能 strip()：shell.CSS 里每行都带两格
    #   缩进（与存量源页一致），strip 会把第一行的缩进也吃掉。
    html = html.replace("{{CSS}}", shell.CSS.strip("\n"))
    # ⚠️ 题库只渲染一次。engine() 里的 `/* __BANK__ */;` 是占位，
    #   已经在 engine() 内部替换掉了；这里**绝不能**再替换 {{BANK}}，
    #   否则题库出现两遍 —— 页面声明 20 题而实际有 40 个条目。
    html = html.replace("{{ENGINE}}", shell.engine(has_judge, per_round, bank))

    # 断言一个占位符都没漏
    left = re.findall(r"\{\{[A-Z_]+\}\}", html)
    assert not left, "模板占位符未替换：%r" % (left,)
    return html


# ---------------------------------------------------------------- 写盘
def write(path: str, html: str, eol: str = "\r\n") -> int:
    """写盘。**newline="" 让换行原样写出**（读写必须对称，见模块 docstring）。"""
    data = to_crlf(html) if eol == "\r\n" else html.replace("\r\n", "\n")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # ⚠️ 必须用二进制写：文本模式在 Windows 上可能再加一层 \r
    with open(path, "wb") as fh:
        fh.write(data.encode("utf-8"))
    return len(data)


def build(grade, volume, subject, unit, filename, items, *,
          broadcast, lesson=None, qtype=None, per_round=10,
          student=DEFAULT_STUDENT, dry_run=False):
    """一步生成源页。返回 (源页路径, 字节数)。

    :param unit:     单元目录名，**不带**题型后缀（生成器自己拼）
    :param filename: 页内文件名，如 `01-天地人.html`
    :param qtype:    choose / judge；不传则按题库里有没有 t='j' 自动判断
    """
    if qtype is None:
        qtype = "judge" if any(it["t"] == "j" for it in items) else "choose"
    lesson = lesson or os.path.splitext(filename)[0]
    html = render(items, grade=grade, volume=volume, subject=subject,
                  unit=unit, lesson=lesson, broadcast=broadcast,
                  student=student, per_round=per_round, qtype=qtype)
    path = bank_path(grade, volume, subject, qtype, unit, filename)
    if dry_run:
        return path, len(html.encode("utf-8"))
    return path, write(path, html)


# ---------------------------------------------------------------- 自检
def selfcheck(html: str) -> list:
    """对生成好的 HTML 做体检。返回问题列表（空 = 通过）。"""
    probs = []

    # 1. 零外链（页面经 /quiz iframe 加载，base URL 不在 content 目录里，
    #    任何相对路径（../../shared/x.css）会解析到磁盘上不存在的位置）
    for pat, why in ((r'<link[^>]+href=', "外链 CSS"),
                     (r'<script[^>]+src=', "外链 JS"),
                     (r'url\(\s*[\'"]?(?!data:)', "CSS 里的相对 url()")):
        if re.search(pat, html, re.I):
            probs.append("存在%s —— 会破坏 iframe 加载与离线双击能力" % why)

    # 2. 题库标记有且只有一个（ParseBank 取第一个出现处）
    n = html.count("const ALL = [")
    if n != 1:
        probs.append("题库标记出现 %d 次（应为 1）" % n)

    # 3. 题库条目数与页面声明一致
    m = re.search(r'题库共 <b>(\d+)</b> 题', html)
    real = len(re.findall(r'\{t:"', html))
    if not m:
        probs.append("找不到「题库共 N 题」声明")
    elif int(m.group(1)) != real:
        probs.append("声明题数 %s 与实际条目 %d 不一致" % (m.group(1), real))

    # 4. 答案字母必须带引号且在范围内
    for it in re.finditer(r'\{t:"(\w)",q:.*?,o:\[(.*?)\],a:\[(.*?)\]', html):
        opts = it.group(2).count('",') + 1
        for a in re.findall(r'"(\w)"', it.group(3)):
            if a not in LETTERS[:opts]:
                probs.append("答案 %s 超出选项范围（%d 个选项）" % (a, opts))

    # 5. 每题独占一行
    body = html[html.index("const ALL = ["):]
    body = body[:body.index("];")]
    for i, ln in enumerate(body.split("\n")[1:], 1):
        s = ln.strip().rstrip(",")
        if not (s.startswith("{t:") and s.endswith("}")):
            probs.append("题库第 %d 行不是完整条目（独占一行约定被破坏）" % i)
            break

    # 6. 换行不混用
    if "\r\n" in html:
        bare = len(re.findall(r"(?<!\r)\n", html))
        if bare:
            probs.append("存在 %d 处裸 LF（换行混用）" % bare)

    # 7. 标签配对
    for tag in ("style", "script", "head", "body", "html"):
        o = len(re.findall(r"<%s[\s>]" % tag, html))
        c = html.count("</%s>" % tag)
        if o != c:
            probs.append("<%s> 开 %d 闭 %d 不配对" % (tag, o, c))

    # 8. 引擎函数齐全
    for fn in ("pickRound", "render", "pick", "grade", "resetAll",
               "continueTest", "toggleTheme", "speak"):
        if ("function %s(" % fn) not in html:
            probs.append("缺引擎函数 %s()" % fn)
    return probs


# ---------------------------------------------------------------- CLI
def main() -> int:
    ap = argparse.ArgumentParser(
        description="从 JSON 题库生成自测页（只写源页，不动 game 侧存量）")
    ap.add_argument("--spec", required=True, help="JSON 题库描述文件")
    ap.add_argument("--dry-run", action="store_true", help="只渲染+体检，不写盘")
    ap.add_argument("--no-check", action="store_true", help="跳过体检（不建议）")
    args = ap.parse_args()

    with open(args.spec, encoding="utf-8") as fh:
        spec = json.load(fh)

    items = []
    for raw in spec["items"]:
        items.append(q(raw["q"], raw["o"], raw["a"], raw["e"],
                       t=raw.get("t", "s")))

    html = render(items,
                  grade=spec["grade"], volume=spec["volume"],
                  subject=spec["subject"], unit=spec["unit"],
                  lesson=spec["lesson"], broadcast=spec["broadcast"],
                  per_round=spec.get("per_round", 10),
                  student=spec.get("student", DEFAULT_STUDENT),
                  qtype=spec.get("qtype"))

    probs = [] if args.no_check else selfcheck(html)
    for p in probs:
        print("  [体检] " + p)

    path = bank_path(spec["grade"], spec["volume"], spec["subject"],
                     spec.get("qtype") or ("judge" if any(
                         it["t"] == "j" for it in items) else "choose"),
                     spec["unit"], spec["filename"])
    nbytes = len(to_crlf(html).encode("utf-8"))
    print("题库 %d 题 · 渲染 %d 字节（CRLF）" % (len(items), nbytes))
    print("目标 %s" % os.path.relpath(path, ROOT).replace(os.sep, "/"))

    if probs:
        print("体检未通过，不写盘")
        return 1
    if args.dry_run:
        print("（dry-run，未写盘）")
        return 0
    write(path, html)
    print("已写入")
    return 0


if __name__ == "__main__":
    sys.exit(main())
