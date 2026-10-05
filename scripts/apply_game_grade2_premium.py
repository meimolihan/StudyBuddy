# -*- coding: utf-8 -*-
"""二年级互动习题页 · Premium 视觉增强层注入器。

用法::

    python scripts/apply_game_grade2_premium.py            # 注入
    python scripts/apply_game_grade2_premium.py --check    # 只体检（不写盘）
    python scripts/apply_game_grade2_premium.py --remove   # 剥离
    python scripts/apply_game_grade2_premium.py --build    # 从题库生成二年级游戏页

三条铁律（都是踩过坑换来的，改之前先读）
------------------------------------------------
1. **哨兵注释必须在 <style>/<script> 标签内部**。放外面会变成 body 的可见
   文本节点，页面上真的会显示 ``__SBK2_CSS__`` 这串字符。
2. **剥离正则不能跨过开标签**。用 ``[^<>]{0,40}`` 之类的宽松匹配会飘到标签之前，
   留下孤立开标签，每次注入多一个空块。两个精确形态分开写。
3. **剥离的替换值必须是空串**（不是 ``"\\n"``）。inject() 自己负责前后换行，
   多吐一个会让「剥离后与原始版本逐字节比对」不通过。

指纹校验
------------------------------------------------
注入前扫描题库数组与判分函数体取 md5。**指纹不一致就中止，绝不写盘** ——
这是「题目内容、答案、答题业务逻辑完全保留不变」这条硬约束的技术保证。
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from game_grade2_premium import ENHANCE_CSS, ENHANCE_JS  # noqa: E402

SENTINEL_CSS = "__SBK2_CSS__"
SENTINEL_JS = "__SBK2_JS__"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 二年级游戏页输出根
GAME_ROOT = os.path.join(ROOT, "content", "primary", "pep", "game", "grade2")
# 题库来源：choose（选择）与 judge（判断）两棵树的 grade2
# (题库根, 题型键)。**顺序与题型都要显式写出**：两棵树单元名完全相同，
# 靠目录名区分题型（见 unit_dir）。
BANK_ROOTS = [
    (os.path.join(ROOT, "content", "primary", "pep", "choose", "grade2"), "choose"),
    (os.path.join(ROOT, "content", "primary", "pep", "judge", "grade2"), "judge"),
]
VOL_LABEL = {"volume1": "上册", "volume2": "下册"}
SUBJ_LABEL = {"chinese": "语文", "math": "数学"}


# ---------------------------------------------------------------- 增强层自检
def selfcheck() -> int:
    """写盘前自检：JS 语法 + 结构完整性。**任何一项不过就不许注入。**

    ⚠️⚠️ 这道闸门是血泪换来的：增强层 JS 里我写过
    ``function ICON_SND_ON = "\\uD83D\\DD0A";``（把变量声明写成函数声明），
    结果 **216 个页面全部静默失效** —— 哨兵都在、位置都对、指纹也一致，
    但浏览器报 ``Uncaught SyntaxError``，``boot()`` 根本没跑，
    背景层和音频坞都没建。

    **为什么指纹校验发现不了**：指纹只覆盖题库数组与判分函数，
    增强层是**纯新增**代码，改它不影响指纹。所以「指纹一致」≠「页面能跑」。

    → 因此除了指纹，还必须验「增强层自己能不能被 JS 引擎解析」。
    这里直接借 Node 的 ``--check``（只解析不执行，零副作用）；
    没有 node 就退化为最基本的标签配对检查。
    """
    # 1) 标签完整性
    for name, body, tag in (("ENHANCE_CSS", ENHANCE_CSS, "style"),
                            ("ENHANCE_JS", ENHANCE_JS, "script")):
        if not body.strip().startswith("<%s " % tag):
            print("!! %s 必须以 <%s ...> 开头（常量自带完整标签，注入器不再二次包装）"
                  % (name, tag))
            return 1
        if ("</%s>" % tag) not in body:
            print("!! %s 缺少 </%s> 闭合标签" % (name, tag))
            return 1
        if body.count("<%s " % tag) != 1:
            print("!! %s 内出现多个 <%s> 开标签" % (name, tag))
            return 1

    # 2) JS 语法（借 node --check；无 node 则跳过，只警告）
    js_lines = ENHANCE_JS.strip("\n").split("\n")
    js_body = "\n".join(js_lines[1:-1])          # 去掉首行的 <script> 与末行 </script>
    tmp = os.path.join(tempfile.gettempdir(), "sbk2_selfcheck.js")
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        fh.write(js_body)
    node = None
    for cand in ("node", "nodejs"):
        node = shutil.which(cand)
        if node:
            break
    if not node:
        managed = os.path.join(
            os.path.expanduser("~"), ".workbuddy", "binaries", "node")
        for root, dirs, names in os.walk(managed):
            if "node.exe" in names:
                node = os.path.join(root, "node.exe")
                break
    if node:
        r = subprocess.run([node, "--check", tmp], capture_output=True, text=True)
        if r.returncode != 0:
            print("!! 增强层 JS 语法错误，注入已中止：")
            print(r.stderr.strip()[:1200])
            print("   （这类错误会让 216 个页面全部静默失效，且指纹校验查不出来）")
            return 1
        print("  自检  JS 语法 node --check 通过")
    else:
        print("  自检  跳过 JS 语法检查（未找到 node）")
    print("  自检  标签完整性通过")
    return 0


# ---------------------------------------------------------------- 指纹
def bank_fingerprint(html: str) -> dict:
    """提取题库与判分函数指纹。

    题库：从 ``const ALL = [`` 到匹配的 ``];``（括号配对扫描，字符串内忽略）。
    判分函数：grade / pick / render / newRound 四个函数体分别取 md5。
    """
    m = re.search(r"(?:const|var|let)\s+ALL\s*=\s*\[", html)
    bank = ""
    if m:
        i = m.end() - 1
        depth = 0
        instr = None
        while i < len(html):
            c = html[i]
            if instr:
                if c == "\\":
                    i += 2
                    continue
                if c == instr:
                    instr = None
            elif c in "\"'":
                instr = c
            elif c == "[":
                depth += 1
            elif c == "]":
                depth -= 1
                if depth == 0:
                    bank = html[m.start():i + 1]
                    break
            i += 1
    funcs = {}
    for name in ("grade", "pick", "render", "newRound", "resetAll", "continueTest"):
        mm = re.search(r"function\s+" + name + r"\s*\(", html)
        if not mm:
            continue
        j, depth, instr = mm.start(), 0, None
        while j < len(html):
            c = html[j]
            if instr:
                if c == "\\":
                    j += 2
                    continue
                if c == instr:
                    instr = None
            elif c in "\"'":
                instr = c
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    funcs[name] = html[mm.start():j + 1]
                    break
            j += 1
    fields = {}
    for k in ("t:", "o:", "a:", "e:"):
        fields[k] = bank.count('"%s"' % k) + bank.count("'%s'" % k) + bank.count(k + '"')
    return {
        "bank": hashlib.md5(bank.encode("utf-8")).hexdigest() if bank else "",
        "bank_len": len(bank),
        "funcs": {k: hashlib.md5(v.encode("utf-8")).hexdigest()[:8] for k, v in funcs.items()},
        "nfuncs": len(funcs),
        "fields": fields,
    }


# ---------------------------------------------------------------- 换行风格
def detect_nl(raw: str) -> str:
    """探测原文件换行风格（CRLF 优先，纯 LF 次之）。

    ⚠️⚠️ 题库源是 **CRLF**（实测 339 处），而 Python 读文件默认会做通用换行
    转换（``open(..., encoding="utf-8")`` 不带 ``newline=""`` 时会把 ``\\r\\n``
    变成 ``\\n``），写回时又按 LF 落盘 → **剥离后与原始版本逐字节比对全不一致**
    （实测 0/216，差异就是全篇的换行符）。

    → 铁律：**读题库文件一律 ``newline=""``（原样读），探测换行风格后按同样的
    风格拼注入块、写盘。** 判定按「首行结束符」，不要全文计数（避免末尾空行干扰）。
    """
    i = raw.find("\n")
    if i > 0 and raw[i - 1] == "\r":
        return "\r\n"
    return "\n"


def _nl(s: str, nl: str) -> str:
    """把纯 LF 文本转成目标换行风格。"""
    if nl == "\n":
        return s
    return s.replace("\n", nl)


# ---------------------------------------------------------------- 注入/剥离
def already(html: str) -> bool:
    return SENTINEL_CSS in html or SENTINEL_JS in html


def inject_simple(html: str, nl: str = "\n") -> str:
    """顺序注入：CSS 进 head 末尾，JS 进 body 末尾。**严格可逆**。

    可逆性设计（这是「剥离后与原始版本逐字节比对」能通过的关键）：
      - 注入时 **完全不动原文本**，只在 ``</head>`` / ``</body>`` **之前**插入
        ``<块> + nl``；**绝不 rstrip 前缀**（那会吃掉原有的换行，剥离后还原不回来）。
      - 块内换行统一走 ``nl``，与原文件风格一致。
      - 剥离正则把 ``<块>`` 连同其**后面那一个换行**一起删掉 → 字节级还原。

    ⚠️⚠️ **ENHANCE_CSS / ENHANCE_JS 常量自身已包含完整标签**
    （``\\n<style id="__SBK2_CSS__">\\n...\\n</style>\\n``）。这里**直接用常量本体**，
    绝不能再套一层 ``'<style id=...>%s</style>'`` —— 那会产生
    ``<style id="__SBK2_CSS__"><style id="__SBK2_CSS__">`` 的**嵌套**：
    浏览器把内层当文本、``strip_enhance`` 的非贪婪 ``.*?</\\1>`` 只吃掉内层，
    残留一个孤立的 ``</style>``，剥离后与原文逐字节比对 **216/216 全不一致**。

    踩过的坑（两个连环）：
      1. 先前版本写的是 ``out[:i].rstrip() + "\\n" + block + "\\n" + out[i:]``，
         rstrip 吞掉原文 ``</head>`` 前的换行 → 剥离后少一个换行。
      2. 修完换行仍全不一致，追查发现是上面这个**二次包装导致的嵌套**。
    """
    out = html
    # 常量自带首尾换行与标签，只把内部换行风格换掉
    css_block = _nl(ENHANCE_CSS.strip("\n"), nl)
    js_block = _nl(ENHANCE_JS.strip("\n"), nl)
    i = out.rfind("</head>")
    if i >= 0:
        out = out[:i] + css_block + nl + out[i:]
    else:
        out = out + css_block + nl
    j = out.rfind("</body>")
    if j >= 0:
        out = out[:j] + js_block + nl + out[j:]
    else:
        out = out + js_block + nl
    return out


def strip_enhance(html: str) -> str:
    """剥离增强层。**替换值必须是空串**（见模块 docstring 铁律 3）。

    每条正则都带尾随 ``\\r?\\n?``：注入时块后面紧跟的那一个换行必须一起吃掉，
    否则剥离后会残留一个空行，与原始版本逐字节不一致。
    """
    # 形态 A：标签内哨兵（当前版本）
    html = re.sub(r"[ \t]*<(style|script)\s+id=\"" + SENTINEL_CSS + r"\"[^>]*>.*?</\1>\r?\n?",
                  "", html, flags=re.S)
    html = re.sub(r"[ \t]*<(style|script)\s+id=\"" + SENTINEL_JS + r"\"[^>]*>.*?</\1>\r?\n?",
                  "", html, flags=re.S)
    # 形态 B：无 id 属性（早期版本）
    html = re.sub(r"[ \t]*<(style|script)>\s*" + re.escape(SENTINEL_CSS) + r".*?</\1>\r?\n?",
                  "", html, flags=re.S)
    html = re.sub(r"[ \t]*<(style|script)>\s*" + re.escape(SENTINEL_JS) + r".*?</\1>\r?\n?",
                  "", html, flags=re.S)
    # 形态 C：标签外哨兵（旧版，会渲染成可见文本）
    html = re.sub(r"[ \t]*" + re.escape(SENTINEL_CSS) + r"\s*<style[^>]*>.*?</style>\r?\n?",
                  "", html, flags=re.S)
    html = re.sub(r"[ \t]*" + re.escape(SENTINEL_JS) + r"\s*<script[^>]*>.*?</script>\r?\n?",
                  "", html, flags=re.S)
    return html


# ---------------------------------------------------------------- 生成
def unit_dir(qtype: str, unit: str) -> str:
    """单元目录名。**必须带题型后缀，否则两棵树会互相覆盖。**

    choose 与 judge 的单元名完全相同（如两边都有 ``01-阅读``），而 gameRaw
    的路径第 3 段固定是 ``game``，无法在那一层区分题型。直接沿用原单元名时，
    judge 会覆盖 choose 的同名文件 —— 实测因此只生成 108 个（应 216 个），
    且标题被换成「· 判断题」。

    目录名是给人看的，用中文：``01-阅读（选择）`` / ``01-阅读（判断）``。
    """
    label = "选择" if qtype == "choose" else "判断"
    return "%s（%s）" % (unit, label)


def build_grade2() -> int:
    """从 choose / judge 题库生成 game/grade2 页面。

    只做「复制 + 注入」，**不改题库内容、不改判分逻辑**。
    """
    n = 0
    for bank_root, qtype in BANK_ROOTS:
        if not os.path.isdir(bank_root):
            continue
        for vol in sorted(os.listdir(bank_root)):
            vpath = os.path.join(bank_root, vol)
            if not os.path.isdir(vpath) or vol not in VOL_LABEL:
                continue
            for subj in sorted(os.listdir(vpath)):
                spath = os.path.join(vpath, subj)
                if not os.path.isdir(spath) or subj not in SUBJ_LABEL:
                    continue
                for unit in sorted(os.listdir(spath)):
                    upath = os.path.join(spath, unit)
                    if not os.path.isdir(upath):
                        continue
                    for fname in sorted(os.listdir(upath)):
                        if not fname.endswith(".html"):
                            continue
                        src = os.path.join(upath, fname)
                        dst_dir = os.path.join(GAME_ROOT, vol, subj,
                                               unit_dir(qtype, unit))
                        os.makedirs(dst_dir, exist_ok=True)
                        dst = os.path.join(dst_dir, fname)
                        shutil.copyfile(src, dst)
                        n += 1
    return n


def iter_targets():
    return sorted(glob.glob(os.path.join(GAME_ROOT, "**", "*.html"), recursive=True))


# ---------------------------------------------------------------- 主流程
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只体检不写盘")
    ap.add_argument("--remove", action="store_true", help="剥离增强层")
    ap.add_argument("--build", action="store_true", help="先从题库生成二年级游戏页")
    ap.add_argument("--selfcheck-only", action="store_true", help="只跑增强层自检")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    # ⚠️ 自检在最前：增强层自身语法错 → 216 个页面全部静默失效，
    # 而指纹校验（只覆盖题库与判分函数）查不出来。见 selfcheck 文档字符串。
    # --remove 不需要（那是回退操作，不写入新代码）。
    if not args.remove:
        rc = selfcheck()
        if rc:
            return rc
    if args.selfcheck_only:
        return 0

    if args.build:
        n = build_grade2()
        print("已生成二年级游戏页 %d 个 -> %s" % (n, GAME_ROOT))

    files = iter_targets()
    if not files:
        print("未找到二年级游戏页，先跑 --build")
        return 1

    if args.remove:
        done = 0
        for f in files:
            s = open(f, encoding="utf-8", newline="").read()
            if not already(s):
                continue
            open(f, "w", encoding="utf-8", newline="").write(strip_enhance(s))
            done += 1
        print("已剥离 %d / %d" % (done, len(files)))
        return 0

    if args.check:
        ok = css_n = js_n = 0
        for f in files:
            s = open(f, encoding="utf-8", newline="").read()
            if SENTINEL_CSS in s:
                css_n += 1
            if SENTINEL_JS in s:
                js_n += 1
            fp = bank_fingerprint(s)
            if not args.quiet:
                print("  %s 题库[%s]=%s 字段%s 函数%d"
                      % (os.path.relpath(f, ROOT), SENTINEL_CSS[:6],
                         (fp["bank"] or "-")[:8], fp["fields"], fp["nfuncs"]))
            ok += 1
        print("\n已注入: CSS %d / JS %d，共 %d 文件" % (css_n, js_n, ok))
        return 0

    # 默认：注入（先剥离再注入，保证幂等）
    # ⚠️ 一律 newline="" 原样读写：题库源是 CRLF，默认读写会把它转成 LF，
    # 剥离后逐字节比对就全不一致（见 detect_nl 文档字符串）。
    done = fail = 0
    for f in files:
        orig = open(f, encoding="utf-8", newline="").read()
        nl = detect_nl(orig)
        base = strip_enhance(orig) if already(orig) else orig
        fp_before = bank_fingerprint(base)
        merged = inject_simple(base, nl)
        fp_after = bank_fingerprint(merged)
        # 指纹必须完全一致，否则中止（业务代码被改动了！）
        if fp_before != fp_after:
            fail += 1
            print("  !! 指纹变化，已中止：%s" % f)
            print("     before=%s" % fp_before)
            print("     after =%s" % fp_after)
            continue
        if merged != orig:
            with open(f, "w", encoding="utf-8", newline="") as fh:
                fh.write(merged)
            done += 1
        if not args.quiet:
            print("  注入  %s" % os.path.relpath(f, ROOT))
    print("\n注入 %d 个文件（变更 %d），失败 %d" % (len(files), done, fail))
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
