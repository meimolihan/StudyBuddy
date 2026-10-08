# -*- coding: utf-8 -*-
"""
一次性清理 style.css 里的游戏模块专属样式。

三类残留：
  1) 整块删除：选择器里全部条目都命中游戏 token（.gm-* / .is-wip / #sb-game-wip）
  2) 摘条目：一条规则的选择器列表里只有部分命中（reduced-motion 的 transition:none 清单）
  3) 删注释段 + 改一处分节标题里的「/ 游戏卡」字样

必须保留：.qtype-entry* / .qtype-card*（选择题与判断题入口卡仍在用）
"""
import io
import os
import re
import sys

PATH = os.path.join("internal", "web", "static", "style.css")

# 只匹配选择器里真正属于游戏模块的 token
#   注意不能带 "qtype-card"，因为 .qtype-card 是保留项
GAME_TOKENS = ("gm-", "is-wip", "sb-game-wip")

# 宿主换行符，在 main() 里按文件实际内容覆写
EOL = "\r\n"


def build_mask(text):
    """把注释替换成等长空格，避免注释里的花括号/关键字干扰扫描。返回 (masked, spans)。"""
    masked = list(text)
    spans = []
    i = 0
    n = len(text)
    while i < n - 1:
        if text[i] == "/" and text[i + 1] == "*":
            j = text.find("*/", i + 2)
            if j < 0:
                break
            j += 2
            spans.append((i, j))
            for k in range(i, j):
                if masked[k] != "\r" and masked[k] != "\n":
                    masked[k] = " "
            i = j
        else:
            i += 1
    return "".join(masked), spans


def match_block(masked, lb):
    """给定左花括号位置，返回其配对右花括号位置（含）。"""
    depth = 0
    i = lb
    n = len(masked)
    while i < n:
        c = masked[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return -1


def has_inner_block(masked, lb, rb):
    """判断块内是否还有嵌套的 {（即是否为 @media/@supports 容器）。

    ⚠️ 不能用「depth 归零就 return False」的写法：那样 @media 容器的
    内层规则一闭合 depth 就归零了，容器会被误判成普通规则，整块删 0 条。
    正确判据：depth 一旦到 2 就说明有嵌套。
    """
    depth = 0
    for i in range(lb, rb):
        c = masked[i]
        if c == "{":
            depth += 1
            if depth >= 2:
                return True
        elif c == "}":
            depth -= 1
    return False


def selector_of(masked, sel_start, lb, spans):
    """取选择器文本，并把注释挖成空格（保持长度）。"""
    seg = masked[sel_start:lb]
    out = []
    for idx, ch in enumerate(seg):
        pos = sel_start + idx
        inside = any(s <= pos < e for s, e in spans)
        out.append(" " if inside else ch)
    return "".join(out).strip()


def strip_at(sel):
    """剥掉 @media/@supports 前缀，只留真正参与匹配的选择器层。"""
    return re.sub(r"@(media|supports)[^{]*$", "", sel).strip()


def split_items(sel):
    """按逗号切分选择器列表（顶层逗号）。"""
    items = []
    depth = 0
    buf = []
    for ch in sel:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            items.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    tail = "".join(buf).strip()
    if tail:
        items.append(tail)
    return [x for x in items if x]


def sel_start_of(masked, lb, spans):
    """从左花括号向前回溯到选择器起点。"""
    p = lb - 1
    while p >= 0:
        if masked[p] in ";}{\n":
            break
        if masked[p] == "/" and p >= 1 and masked[p - 1] == "*":
            return p + 1
        p -= 1
    return p + 1


def collect(masked, lo, hi, spans, kills, stats):
    """在 [lo, hi) 内收集可删规则。kills: (start, end, kind, replacement)"""
    i = lo
    while i < hi:
        c = masked[i]
        if c == "{":
            rb = match_block(masked, i)
            if rb < 0:
                return
            inner = has_inner_block(masked, i, rb)
            if inner:
                # @media/@supports 容器：递归进去逐条判，不整块删
                collect(masked, i + 1, rb - 1, spans, kills, stats)
                i = rb
                continue
            ss = sel_start_of(masked, i, spans)
            sel = strip_at(selector_of(masked, ss, i, spans))
            items = split_items(sel)
            hits = [k for k, it in enumerate(items) if any(t in it for t in GAME_TOKENS)]
            if len(hits) == len(items) and items:
                kills.append((ss, rb, "block", ""))
                stats["block"] += 1
            elif hits:
                # ⚠️ 只替换选择器段 [ss, i)，保留后面的 {...}。
                #   若连 { 一起替换就必须补回 }，否则整份 CSS 花括号不配平。
                keep = [it for k, it in enumerate(items) if k not in hits]
                # ⚠️ 必须用宿主换行符拼接。写死 "\n" 会往 CRLF 文件里
                #    注入裸 LF（工作区 style.css 是 100% CRLF）
                joined = ("," + EOL + "  ").join(keep)
                kills.append((ss, i, "item", "  " + joined))
                stats["item"] += 1
            i = rb
        else:
            i += 1


def strip_game_comments(text):
    """先删游戏专属注释段（必须赶在规则删除之前跑）。

    ⚠️ 顺序很关键：如果先删规则，@media 容器会被掏空成
    `@media (max-width:640px){\n\n\n}`，段内就不再含 ".gm-"，
    后面那条「段内必须含 .gm- 才删」的判据就永远匹配不上了。
    """
    note_kills = 0

    # ① iframe 撑满高度那段注释（专讲游戏 iframe），连它下面的 @media 头一起删
    m = re.search(r"/\* iframe 撑满剩余高度[^\n]*\n(?:[^\n]*\n)*?"
                  r"@media \(max-width:640px\)\{[^\n]*\n(?:[^\n]*\n)*?\}\r?\n", text)
    if m and ".gm-" in m.group(0):
        text = text[:m.start()] + text[m.end():]
        note_kills += 1

    # ② 3.1 节整段（从「3.1 学习主页 · 游戏卡」注释起点，到下一节 3.2 之前）
    m = re.search(r"/\*[ \t]*-{2,}[ \t]*3\.1[^\n]*\n", text)
    if m:
        nxt = re.search(r"/\*[ \t]*-{2,}[ \t]*3\.2", text[m.end():])
        end = m.end() + (nxt.start() if nxt else 0)
        seg = text[m.start():end]
        if "sb-game-wip" in seg or "is-wip" in seg:
            text = text[:m.start()] + text[end:]
            note_kills += 1

    # ③ 「⑦ 「火速开发中」弹窗」分节标题
    m = re.search(r"/\*[ \t]*-{2,}[ \t]*⑦[^\n]*\*/\r?\n", text)
    if m:
        text = text[:m.start()] + text[m.end():]
        note_kills += 1

    # ④ 「学习主页入口卡 / 游戏卡」→ 去掉游戏卡字样
    text = text.replace("/* 学习主页入口卡 / 游戏卡 */", "/* 学习主页入口卡 */")

    return text, note_kills


def main():
    with io.open(PATH, "r", encoding="utf-8", newline="") as f:
        original = f.read()
    eol = "\r\n" if "\r\n" in original else "\n"
    global EOL
    EOL = eol

    # 先清注释，再算规则偏移 —— 顺序不能反
    out, note_kills = strip_game_comments(original)

    masked, spans = build_mask(out)
    kills = []
    stats = {"block": 0, "item": 0}
    collect(masked, 0, len(masked), spans, kills, stats)

    # 从后往前删，避免偏移错乱
    for ss, en, kind, rep in sorted(kills, key=lambda x: -x[0]):
        out = out[:ss] + rep + out[en:]

    # 清理删除后遗留的连续空行（最多压到 2 个）与空 @media 壳
    out = re.sub(r"@media[^{]*\{\s*\}\r?\n", "", out)
    out = re.sub(r"\r?\n\r?\n\r?\n+", eol * 2, out)

    with io.open(PATH, "wb") as f:
        f.write(out.encode("utf-8"))

    print("整块删 %d 条 / 摘条目 %d 处 / 注释段 %d 处" % (
        stats["block"], stats["item"], note_kills))
    print("字节 %d -> %d (-%d)" % (len(original.encode("utf-8")),
                                     len(out.encode("utf-8")),
                                     len(original.encode("utf-8")) - len(out.encode("utf-8"))))

    print("\n=== 残留检查 ===")
    for tok in ("gm-", "is-wip", "sb-game-wip", "wip-modal", "游戏卡", "游戏内容"):
        print("  %-12s %d" % (tok, out.count(tok)))
    print("  --- 保留项 ---")
    for tok in ("qtype-card", "qtype-entry"):
        print("  %-12s %d" % (tok, out.count(tok)))


if __name__ == "__main__":
    main()