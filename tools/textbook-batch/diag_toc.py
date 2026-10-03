# -*- coding: utf-8 -*-
"""目录提取诊断：把每册的失败原因量化，避免逐个 case 试错。

用法: python tools/textbook-batch/diag_toc.py --stage primary --stage middle
"""
import argparse
import collections
import json
import os
import re
import sys

import pymupdf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import extract_curric as E


def diag(book, root):
    src = os.path.join(root, book["src"].replace("/", os.sep))
    if not os.path.exists(src):
        return {"key": book["key"], "stage": "源文件缺失"}
    doc = pymupdf.open(src)
    tps = E.find_toc_pages(doc)
    if not tps:
        return {"key": book["key"], "stage": "未找到目录页"}
    n_entries = 0
    n_unit = 0
    n_page = 0
    samples = []
    for pg in tps:
        for t, p, no, is_unit in E.parse_toc_page(doc[pg]):
            n_entries += 1
            n_unit += 1 if is_unit else 0
            n_page += 1 if p > 0 else 0
            if len(samples) < 4:
                samples.append((t[:22], p, no, is_unit))
    raw = []
    for pg in tps:
        for t, p, no, is_unit in E.parse_toc_page(doc[pg]):
            raw.append((t, p, no, is_unit, pg))
    off = E._anchor_offset(doc, raw) if raw else None
    return {
        "key": book["key"], "stage": "OK" if n_page >= 3 else "页码不足",
        "tocPages": [p + 1 for p in tps], "entries": n_entries,
        "units": n_unit, "pages": n_page, "offset": off, "samples": samples,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="data/textbook/manifest.json")
    ap.add_argument("--stage", action="append", default=[])
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--show-ok", action="store_true")
    args = ap.parse_args()

    mf = json.load(open(args.manifest, encoding="utf-8"))
    books = mf["books"]
    if args.stage:
        books = [b for b in books if b["stage"] in args.stage]
    if args.limit:
        books = books[:args.limit]

    groups = collections.defaultdict(list)
    for b in books:
        try:
            r = diag(b, mf["root"])
        except Exception as e:
            r = {"key": b["key"], "stage": "异常:%s" % str(e)[:24]}
        groups[r["stage"]].append(r)

    print("扫描 %d 册\n" % len(books))
    for stage, rs in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        print("[%s] %d 册" % (stage, len(rs)))
        show = rs if (args.show_ok or stage == "OK") else rs[:3]
        for r in show[:4]:
            print("   %-34s toc=%-12s 条目%-4s 单元%-4s 页%-4s off=%s"
                  % (r["key"], r.get("tocPages"), r.get("entries"),
                     r.get("units"), r.get("pages"), r.get("offset")))
            for s in (r.get("samples") or [])[:2]:
                print("        %-24r p=%-5s no=%-4s unit=%s" % s)
        print()


if __name__ == "__main__":
    main()
