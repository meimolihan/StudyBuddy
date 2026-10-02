# -*- coding: utf-8 -*-
"""修复 A2（v2，纯 raw 域）：修复「“X指的是（　）”缺闭引号」形态。
规则：题干 raw 中 “ 计数 != ” 计数 且以 “ 开头且含「指的是」→ 在第一个「指的是」前插 ”。
默认 dry-run，--apply 执行。
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _banklib import extract_objects

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "content")
APPLY = "--apply" in sys.argv

total_files = 0
total_fixed = 0
unfixed = []
for qtype in ("choose", "judge"):
    for stage in ("primary", "middle", "high"):
        base = os.path.join(CONTENT, stage, "pep", qtype)
        for dp, _, fns in os.walk(base):
            for fn in sorted(fns):
                if not fn.endswith(".html"):
                    continue
                full = os.path.join(dp, fn)
                src = open(full, encoding="utf-8", newline="").read()
                objs = extract_objects(src)
                if not objs:
                    continue
                new_src_parts = []
                last = 0
                n_fix_file = 0
                for txt in objs:
                    start = src.find(txt, last)
                    if start < 0:
                        continue
                    end = start + len(txt)
                    new_src_parts.append(src[last:start])
                    qi = txt.find('q:"')
                    if qi >= 0:
                        content_start = qi + 3
                        rest_i = txt.find('",o:[', qi)
                        if rest_i >= 0:
                            q_raw = txt[content_start:rest_i]
                            if (q_raw.count("“") != q_raw.count("”")
                                    and q_raw.startswith("“") and "指的是" in q_raw):
                                pos = q_raw.find("指的是")
                                if pos > 0 and q_raw[pos - 1] != "”":
                                    q_new = q_raw[:pos] + "”" + q_raw[pos:]
                                    if q_new.count("“") == q_new.count("”"):
                                        new_src_parts.append(txt[:content_start] + q_new + txt[rest_i:])
                                        n_fix_file += 1
                                        last = end
                                        continue
                                unfixed.append([os.path.relpath(full, CONTENT).replace("\\", "/"), q_raw[:44]])
                    new_src_parts.append(txt)
                    last = end
                new_src_parts.append(src[last:])
                if n_fix_file:
                    total_files += 1
                    total_fixed += n_fix_file
                    if APPLY:
                        for attempt in range(5):
                            try:
                                open(full, "w", encoding="utf-8", newline="").write("".join(new_src_parts))
                                break
                            except PermissionError:
                                import time
                                if attempt == 4:
                                    raise
                                time.sleep(0.6 * (attempt + 1))

print(f"APPLY={APPLY} ｜ 修复文件: {total_files} ｜ 修复题数: {total_fixed} ｜ 未修复: {len(unfixed)}")
for x in unfixed[:10]:
    print("  UNFIXED:", x)
