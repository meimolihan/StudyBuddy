# -*- coding: utf-8 -*-
"""
删除 unit_dir() / game_path() 之后的回归验证：
拿存量源页反推参数 → render() 重渲染 → 与磁盘逐字节比对。

零漂移是模板正确性的硬判据。删了游戏侧的两个函数之后，
生成器必须仍能一字不差地复现 424 个存量源页。
"""
import io
import os
import re
import sys

sys.path.insert(0, os.path.join("tools", "gamegen"))
import selftest_gen as G
import selftest_shell as shell

PEP = "content/primary/pep"
MARKER = "const ALL = ["


def bank_block(text):
    m = re.search(re.escape(MARKER) + r"(.*?)(?:\r?\n)?\];", text, re.S)
    return m.group(1) if m else None


def parse_source(path):
    """从存量源页反推 (items, meta)，供 render() 重渲染。"""
    text = io.open(path, "r", encoding="utf-8", newline="").read()

    # <h1>一年级语文上册 · 自测卷（人教版）</h1>
    h1 = re.search(r"<h1[^>]*>([^<]+)</h1>", text).group(1).strip()
    m = re.match(r"^([一二三四五六])年级(语文|数学)(上|下)册", h1)
    if not m:
        raise ValueError("h1 不匹配: %r" % h1[:40])
    gname, sname, vname = m.group(1), m.group(2), m.group(3)

    blk = bank_block(text)
    items = []
    for line in blk.splitlines():
        line = line.strip().rstrip(",")
        if not line.startswith("{t:"):
            continue
        # ⚠️ 必须按引号抠，不能按逗号裸切（会带出引号）
        f = re.search(r'\{t:"(.)".*\}$', line)
        t = f.group(1)
        q = re.search(r'q:"((?:[^"\\]|\\.)*)"', line).group(1)
        opts = re.findall(r'"((?:[^"\\]|\\.)*)"', re.search(r"o:\[(.*?)\]", line).group(1))
        ans = re.findall(r'"((?:[^"\\]|\\.)*)"', re.search(r"a:\[(.*?)\]", line).group(1))
        exp = re.search(r'e:"((?:[^"\\]|\\.)*)"', line).group(1)
        items.append({"t": t, "q": q, "o": opts, "a": ans, "e": exp})

    # 元信息
    subject = "chinese" if sname == "语文" else "math"
    grade = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6}[gname]
    volume = "volume1" if vname == "上" else "volume2"
    qtype = "judge" if 't==="j"' in text else "choose"
    per = int(re.search(r"题库共 <b>(\d+)</b> 题", text).group(1))
    per_round = int(re.search(r"最多抽取 <b>(\d+)</b> 题", text).group(1))
    bc = re.search(r'id="broadcast">📣 今日广播：(.*?)</div>', text, re.S)
    broadcast = bc.group(1).strip() if bc else ""

    # ⚠️ unit / lesson 是**显示名**，与磁盘目录名/文件名不是一回事：
    #    目录 `01-我上学了/01-我上学了.html` -> unit="我上学了" lesson="第1课 我上学了"
    #    从 <title>「<学科> 自测 · <unit> · <lesson>[ · 判断题]」反推。
    #    判断题壳在 title 末尾**多一段**「· 判断题」（就是那个 HAS_JUDGE 开关）。
    title = re.search(r"<title>([^<]+)</title>", text).group(1)
    parts = [x.strip() for x in title.split("·")]
    if parts and parts[-1] == "判断题":
        parts = parts[:-1]
    if len(parts) != 3:
        raise ValueError("title 段数不对: %r" % title)
    unit, lesson = parts[1], parts[2]
    return items, dict(subject=subject, grade=grade, volume=volume,
                        qtype=qtype, unit=unit, lesson=lesson,
                        broadcast=broadcast, per_round=per_round), per


def main():
    total = drift = missing = skipped = 0
    shown = 0
    for qtype in ("choose", "judge"):
        root = os.path.join(PEP, qtype)
        for dirpath, _, files in os.walk(root):
            for fn in files:
                if not fn.endswith(".html"):
                    continue
                # 只验生成器覆盖的 grade1/2 语文数学（其余是别的构建脚本产的）
                rel = os.path.relpath(dirpath, root).replace("\\", "/")
                if not re.match(r"^grade[12]/volume[12]/(chinese|math)/", rel):
                    continue
                path = os.path.join(dirpath, fn)
                # 跳过已注入增强层（SBK / SBK2）的页面 —— 它们比「纯壳」多几段
                # style/脚本，生成器重渲染的是纯壳，比了必然漂移
                raw = io.open(path, "r", encoding="utf-8", newline="").read()
                if "__SBK" in raw:
                    skipped += 1
                    continue
                try:
                    items, meta, per = parse_source(path)
                except Exception as e:
                    missing += 1
                    if missing <= 3:
                        print("  解析失败 %s: %s" % (rel + "/" + fn, e))
                    continue
                out = G.render(items, **meta)
                disk = io.open(path, "r", encoding="utf-8", newline="").read()
                total += 1
                if out.replace("\n", "\r\n") != disk:
                    drift += 1
                    if drift <= 2:
                        shown += 1
                        a = out.replace("\n", "\r\n").split("\r\n")
                        b = disk.split("\r\n")
                        print("\n=== 漂移 %s ===" % (rel + "/" + fn))
                        for i, (x, y) in enumerate(zip(a, b)):
                            if x != y:
                                print("  行%d\n    渲染 %r\n    磁盘 %r" % (i + 1, x[:150], y[:150]))
                                break
                        if len(a) != len(b):
                            print("  行数 渲染%d / 磁盘%d" % (len(a), len(b)))
    print("\n校验 %d 个源页：零漂移 %d，漂移 %d，解析失败 %d，已注入增强层跳过 %d"
          % (total, total - drift - missing, drift, missing, skipped))
    return 1 if (drift or missing) else 0


if __name__ == "__main__":
    sys.exit(main())