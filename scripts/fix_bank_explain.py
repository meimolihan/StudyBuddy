# -*- coding: utf-8 -*-
"""修复 #169：choose 全库补解析（自验证生成）。
模板分层：
  1) 计算题验算：仅处理可 100% 验证的形态（计算：A op B=；把 A/B 化成最简分数），且计算结果必须与正确选项一致，否则退兜底；
  2) 读音题：「“X”的正确读音是（　）」→ 复述读音；
  3) 「指的是」题：「“X”指的是（　）」→ 复述定义；
  4) 兜底：「本题正确答案为 <L>：<opt>。」（多选列举）。
安全性：
  - q/o 保持 raw 原文回填（零 round-trip 风险），仅新增 e 字段；
  - e 内容基于 raw 域文本拼接，解析永不与答案矛盾（验算型必须通过比对才写入）。
默认 dry-run（输出模板命中统计+抽样），--apply 写回。
"""
import json, os, re, sys
from math import gcd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _banklib import extract_objects, parse_obj

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "content")
APPLY = "--apply" in sys.argv

RE_CALC = re.compile(r"计算[：:]\s*(\d+)\s*([+\-×x*÷/])\s*(\d+)\s*=")
RE_SIMP = re.compile(r"把 (\d+)/(\d+) 化成最简分数是")
RE_YIN = re.compile(r"[「“']([^」”'）(]{1,12})[」”']的(?:正确)?读音是")
RE_ZHIDE = re.compile(r"^“(.+)”指的是")

def opt_of(q, a):
    """正确选项原文（raw 域）；多选取第一个供验算"""
    if not a:
        return None
    i = ord(a[0]) - 65
    return q["o"][i] if 0 <= i < len(q["o"]) else None

def gen_explain(p):
    """返回 (模板名, e_raw) 或 (None, None)"""
    q = p["q"] or ""
    o, a, t = p["o"], p["a"], p["t"]
    if not o or not a:
        return None, None
    correct = opt_of(p, a)
    if correct is None:
        return None, None
    letters = "".join(a)
    # 1) 计算题
    m = RE_CALC.search(q)
    if m and t == "s":
        x, op, y = int(m.group(1)), m.group(2), int(m.group(3))
        r = {"+": x + y, "-": x - y, "×": x * y, "x": x * y, "*": x * y}.get(op)
        if r is None and op in "÷/" and y != 0 and x % y == 0:
            r = x // y
        if r is not None and str(r) == correct.strip():
            return "calc", f"解析：{x} {op} {y} = {r}，所以选「{correct}」。"
    m = RE_SIMP.search(q)
    if m and t == "s":
        x, y = int(m.group(1)), int(m.group(2))
        g = gcd(x, y)
        c, d = x // g, y // g
        expected = f"{c}/{d}" if d != 1 else str(c)
        if expected == correct.strip():
            return "simp", f"解析：{x} 和 {y} 的最大公因数是 {g}，分子分母同除以 {g}，得 {expected}，所以选「{correct}」。"
    # 2) 读音题
    m = RE_YIN.search(q)
    if m and t == "s":
        return "yin", f"解析：「{m.group(1)}」的正确读音是 {correct}。"
    # 3) 指的是
    m = RE_ZHIDE.match(q)
    if m and t == "s":
        return "zhide", f"解析：“{m.group(1)}”指的是：{correct}。"
    # 4) 兜底
    if t == "m":
        names = "、".join(letters)
        body = "；".join(p["o"][ord(L) - 65] for L in a if 0 <= ord(L) - 65 < len(p["o"]))
        return "multi", f"解析：本题正确答案为 {names}：{body}。"
    return "base", f"解析：本题正确答案为 {letters}：{correct}。"

def build_obj(t, q_raw, o_raws, a_list, e_raw):
    return ('{t:"%s",q:"%s",o:[%s],a:[%s],e:"%s"}' % (
        t, q_raw, ", ".join('"%s"' % v for v in o_raws), ", ".join('"%s"' % v for v in a_list), e_raw))

# ---------- 主循环 ----------
files = []
for stage in ("primary", "middle", "high"):
    base = os.path.join(CONTENT, stage, "pep", "choose")
    for dp, _, fns in os.walk(base):
        for fn in fns:
            if fn.endswith(".html"):
                files.append(os.path.join(dp, fn))
files.sort()
print(f"choose 文件数: {len(files)} ｜ APPLY={APPLY}")

from collections import Counter
tmpl_stat = Counter()
samples = {}
written = 0
skipped = []
for full in files:
    rel = os.path.relpath(full, CONTENT).replace("\\", "/")
    src = open(full, encoding="utf-8", newline="").read()
    objs = extract_objects(src)
    if not objs:
        skipped.append([rel, "no objects"])
        continue
    raws = [o.strip() for o in objs]
    parsed = [parse_obj(r) for r in raws]
    if any(p is None for p in parsed):
        skipped.append([rel, "parse fail"])
        continue
    new_raws = []
    dirty = False
    for idx, (r, p) in enumerate(zip(raws, parsed)):
        if p["e"]:
            new_raws.append(r)   # 已有解析（不应出现）保持原样
            continue
        name, e_raw = gen_explain(p)
        if e_raw is None:
            skipped.append([rel, f"#{idx+1} 无法生成"])
            new_raws.append(r)
            continue
        tmpl_stat[name] += 1
        samples.setdefault(name, [])
        if len(samples[name]) < 3:
            samples[name].append(f"{rel} #{idx+1} ｜ {p['q'][:36]} → {e_raw[:70]}")
        new_raws.append(build_obj(p["t"], p["q"], p["o"], p["a"], e_raw))
        dirty = True
    if dirty:
        i = src.find("const ALL")
        lb = src.find("[", i)
        depth = in_str = esc = 0
        end = -1
        for k in range(lb, len(src)):
            c = src[k]
            if in_str:
                if esc:
                    esc = 0
                elif c == "\\":
                    esc = 1
                elif c == '"':
                    in_str = 0
                continue
            if c == '"':
                in_str = 1
            elif c == "[":
                depth += 1
            elif c == "]":
                depth -= 1
                if depth == 0:
                    end = k
                    break
        new_body = " " + (",\r\n ").join(new_raws)
        new_src = src[:lb + 1] + new_body + src[end:]
        if APPLY:
            for attempt in range(5):
                try:
                    open(full, "w", encoding="utf-8", newline="").write(new_src)
                    break
                except PermissionError:
                    import time
                    if attempt == 4:
                        raise
                    time.sleep(0.6 * (attempt + 1))
        written += 1

print(f"写回文件: {written} ｜ 模板命中: {dict(tmpl_stat)} ｜ 跳过: {len(skipped)}")
for s in skipped[:10]:
    print("  SKIP:", s)
for name in samples:
    print(f"--- 样例 [{name}] ---")
    for s in samples[name]:
        print("  ", s)
