# -*- coding: utf-8 -*-
"""题库解析公共库（无副作用，可安全 import）。
从 audit_bank.py / extract_fix_targets.py 抽取的容错解析函数。
"""
import re

RE_T = re.compile(r'\bt\s*:\s*"([a-z])"')
RE_Q = re.compile(r'\bq\s*:\s*"(..*?)"\s*,\s*o\s*:\s*\[', re.S)
RE_E = re.compile(r',\s*e\s*:\s*"(..*?)"\s*\}\s*$', re.S)
RE_STR = re.compile(r'"(?:[^"\\]|\\.)*"')

def extract_objects(src):
    """从 const ALL = [ ... ]; 按引号感知的花括号配对切出对象文本"""
    i = src.find("const ALL")
    if i < 0:
        return None
    lb = src.find("[", i)
    if lb < 0:
        return None
    objs, depth, in_str, esc, cur = [], 0, False, False, None
    for k in range(lb, len(src)):
        c = src[k]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == "{":
            if depth == 0:
                cur = k
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0 and cur is not None:
                objs.append(src[cur:k + 1])
                cur = None
        elif c == "]" and depth == 0:
            break
    return objs

def parse_obj(txt):
    """返回 (t,q,o,a,e) 或 None；q/o/a/e 均保持原始转义域（除 q 在 load_bank 中 unesc）"""
    mt = RE_T.search(txt)
    if not mt:
        return None
    t = mt.group(1)
    q = None
    mq = RE_Q.search(txt)
    if mq:
        q = mq.group(1)
    o = []
    io = txt.find("o:[")
    if io >= 0:
        seg_end = txt.find("],a:[", io)
        if seg_end < 0:
            seg_end = txt.find("]", io)
        seg = txt[io + 3:seg_end if seg_end > 0 else len(txt)]
        o = [m[1:-1] for m in RE_STR.findall(seg)]
        if not o:
            seg2 = seg.strip().strip(",")
            o = [p.strip().strip('"') for p in seg2.split('", "')]
    a = []
    ia = txt.find("a:[")
    if ia >= 0:
        seg_end = txt.find("]", ia)
        seg = txt[ia + 3:seg_end]
        a = re.findall(r'[A-D]', seg)
    e = None
    me = RE_E.search(txt)
    if me:
        e = me.group(1)
    return {"t": t, "q": q, "o": o, "a": a, "e": e}

def unesc(s):
    return s.replace('\\"', '"').replace("\\n", "\n").replace("\\\\", "\\") if s else s

def load_bank(full):
    """解析单个题库文件 -> 题目列表（题干已 unesc 便于阅读）"""
    src = open(full, encoding="utf-8").read()
    objs = extract_objects(src)
    if objs is None:
        return []
    out = []
    for txt in objs:
        p = parse_obj(txt)
        if p:
            p["q"] = unesc(p["q"])
            if p["e"]:
                p["e"] = unesc(p["e"])
            out.append(p)
    return out
