#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成「全局字体档位」CSS 覆盖段（append-only 用）。

背景：全站样式是 px 写的，直接改 html 的 font-size 对那些显式 px 无效。
这里扫一遍 style.css，把所有 `font-size:<N>px` 抽出来，按原来的选择器
重新生成一份 `html[data-font] <选择器>{font-size:calc(<N>px * var(--sb-fz,1))}`，
追加到文件末尾。原规则一行不动，档位开关只靠 --sb-fz 一个变量生效。

用法：python scripts/gen_font_scale_css.py            # 打印到标准输出
      python scripts/gen_font_scale_css.py --append   # 追加到 style.css 末尾
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSS = ROOT / "internal" / "web" / "static" / "style.css"

SKIP_AT = ("@keyframes", "@font-face", "@-webkit-keyframes", "@page", "@supports")


def strip_comments(s: str) -> str:
    out, i, n = [], 0, len(s)
    while i < n:
        if s.startswith("/*", i):
            j = s.find("*/", i + 2)
            if j < 0:
                break
            i = j + 2
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


def split_media(body: str):
    """把 @media 的 condition 与内层内容分开，返回 (cond, inner)。"""
    i = body.index("{")
    return body[:i].strip(), body[i + 1:]


def collect(css: str, media: str = ""):
    """递归收集 (media条件, 选择器串, px字号) 三元组。"""
    items = []
    i, n = 0, len(css)
    buf = ""
    while i < n:
        c = css[i]
        if c == "{":
            # 找匹配的右括号
            depth, j = 1, i + 1
            while j < n and depth:
                if css[j] == "{":
                    depth += 1
                elif css[j] == "}":
                    depth -= 1
                j += 1
            inner = css[i + 1: j - 1]
            head = buf.strip()
            buf = ""
            if head.startswith("@"):
                if not head.lower().startswith(SKIP_AT):
                    if head.lower().startswith("@media"):
                        # 条件在 head 上（@media (max-width:640px)），inner 是块内内容。
                        # 早期版本拿 inner 去 split_media，会把块内第一条规则的
                        # 选择器当成 media 条件，产出 `@media .auth-wrap{...}` 这种废规则。
                        cond = head[len("@media"):].strip()
                        # 嵌套 media：条件用 and 叠加
                        merged = ("%s and %s" % (media, cond)) if media else cond
                        items += collect(inner, merged)
                    else:
                        items += collect(inner, media)
            else:
                # 普通规则：抽 font-size
                m = re.search(r"(?:^|;)\s*font-size\s*:\s*(\d+(?:\.\d+)?)px\s*(?:;|$)", inner)
                if m and head:
                    items.append((media, head, m.group(1)))
            i = j
            continue
        buf += c
        i += 1
    return items


def prefix_selector(sel: str) -> str:
    """给选择器串里每一个逗号分隔的片段都加上 html[data-font] 前缀。

    只给第一项加会让 .a,.b 里的 .b 拿不到更高特异度 —— 这正是「加了前缀
    却只有一半元素变大」的典型原因。
    """
    parts = [p.strip() for p in sel.split(",") if p.strip()]
    return ", ".join("html[data-font] " + p for p in parts)


def main():
    raw = CSS.read_text(encoding="utf-8")
    items = collect(strip_comments(raw))
    out = []
    out.append("")
    out.append("/* ============================================================")
    out.append("   全局字体档位（小 / 默认 / 大）")
    out.append("   全站字号都是 px 写死的，改 html 的 font-size 对它们无效，")
    out.append("   所以这里按原选择器重新声明一遍 font-size，乘上 --sb-fz：")
    out.append("     默认 = 不写 data-font（--sb-fz 取兜底值 1）")
    out.append("     小   = 0.88 倍，大 = 1.15 倍")
    out.append("   规则由 scripts/gen_font_scale_css.py 扫描本文件自动生成，")
    out.append("   改字号请改原规则后重新生成，不要手改这一段。")
    out.append("   ============================================================ */")
    out.append("html[data-font=\"sm\"]{--sb-fz:.88}")
    out.append("html[data-font=\"lg\"]{--sb-fz:1.15}")
    # body 本身也在扫描结果里（原文件写了 15px），这里不再重复声明

    plain = [(s, v) for (m, s, v) in items if not m]
    media = [(m, s, v) for (m, s, v) in items if m]
    for sel, v in plain:
        out.append("%s{font-size:calc(%spx * var(--sb-fz,1))}" % (prefix_selector(sel), v))

    # 媒体查询内的规则：按 media 条件分组，整段包起来，保持原有断点语义
    groups = {}
    for m, sel, v in media:
        groups.setdefault(m, []).append((sel, v))
    for m, lst in groups.items():
        out.append("@media %s{" % m)
        for sel, v in lst:
            out.append("  %s{font-size:calc(%spx * var(--sb-fz,1))}" % (prefix_selector(sel), v))
        out.append("}")

    text = "\n".join(out) + "\n"
    if "--append" in sys.argv:
        with CSS.open("a", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print("appended %d rules (%d in media)" % (len(items), len(media)))
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
