# -*- coding: utf-8 -*-
"""清理后结构校验：花括号配平、孤立选择器、注释未闭合、保留项完好。"""
import io
import re
import os

PATH = os.path.join("internal", "web", "static", "style.css")
text = io.open(PATH, "r", encoding="utf-8", newline="").read()

# 1. 花括号配平
depth = 0
minv = 0
for ch in text:
    if ch == "{":
        depth += 1
    elif ch == "}":
        depth -= 1
        minv = min(minv, depth)
print("花括号配平: 结束 depth=%d (应为 0), 最低=%d (应 >=0)" % (depth, minv))

# 2. 注释配平
print("注释配平: /* = %d, */ = %d" % (text.count("/*"), text.count("*/")))

# 3. 孤立选择器：连续两个 } 之间不该有裸选择器尾巴（结尾的 } 后面只有空白/注释）
bad = 0
for m in re.finditer(r"\}", text):
    tail = text[m.end():m.end() + 3]
    if re.match(r"^[^\s@/*)\];{}]+", tail):
        bad += 1
        if bad <= 5:
            print("  孤立尾巴 @%d: %r" % (m.end(), text[m.end():m.end() + 40]))
print("孤立选择器尾巴: %d" % bad)

# 4. 每个 { 前必须有对应选择器
empty_sel = 0
for m in re.finditer(r"\{", text):
    pre = text[:m.start()].rstrip()
    if not pre or pre[-1] in "{};":
        empty_sel += 1
        if empty_sel <= 5:
            print("  空选择器 @%d: %r" % (m.start(), text[m.start() - 30:m.start() + 10]))
print("空选择器块: %d" % empty_sel)

# 5. 保留项完整性：study.html 真正用到的类都要还在
must = [".qtype-entry", ".qtype-entry-grid", ".qtype-entry-foot",
        ".qtype-card", ".qtype-card-ico", ".qtype-card-body",
        ".qtype-card-name", ".qtype-card-desc", ".qtype-card-go",
        ".qtype-card.is-on", ".qtype-card:hover", ".qtype-card:focus-visible"]
miss = [c for c in must if c not in text]
print("保留项缺失: %s" % (miss if miss else "无（%d 项全在）" % len(must)))

# 6. 换行一致性
crlf = text.count("\r\n")
bare = len(re.findall(r"(?<!\r)\n", text))
print("换行: CRLF=%d 裸LF=%d" % (crlf, bare))

# 7. 「游戏内容」那 1 处是什么
m = re.search(r".{80}游戏内容.{80}", text, re.S)
print("\n「游戏内容」上下文:\n  %r" % (m.group(0) if m else None))