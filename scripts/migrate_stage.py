# -*- coding: utf-8 -*-
"""学段目录改名（第二步）：把初中 / 高中目录换成规范命名，并改用绝对年级号。

    content/middle/pep/choose/grade1  →  content/junior/pep/choose/grade7   （七年级）
    content/middle/pep/choose/grade2  →  content/junior/pep/choose/grade8   （八年级）
    content/middle/pep/choose/grade3  →  content/junior/pep/choose/grade9   （九年级）
    content/high/pep/choose/gradeN    →  content/senior/pep/choose/gradeN   （高一~高三，N 不变）

小学 primary 保持不动。judge 目录若已存在会一并改名。
只做目录移动 / 改名，不动任何 HTML 内容；目标已存在则拒绝覆盖。
"""
import os
import shutil
import sys

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "content")

# (旧学段, 新学段, 年级偏移)
PLAN = [("middle", "junior", 6), ("high", "senior", 0)]


def main():
    moved = 0
    for old, new, off in PLAN:
        src_stage = os.path.join(ROOT, old)
        if not os.path.isdir(src_stage):
            print("跳过（不存在）：%s" % src_stage)
            continue
        for pub in sorted(os.listdir(src_stage)):
            src_pub = os.path.join(src_stage, pub)
            if not os.path.isdir(src_pub):
                continue
            for qtype in sorted(os.listdir(src_pub)):
                src_qt = os.path.join(src_pub, qtype)
                if not os.path.isdir(src_qt):
                    continue
                for name in sorted(os.listdir(src_qt)):
                    if not name.startswith("grade"):
                        continue
                    try:
                        n = int(name[len("grade"):])
                    except ValueError:
                        continue
                    src = os.path.join(src_qt, name)
                    dst = os.path.join(ROOT, new, pub, qtype, "grade%d" % (n + off))
                    if os.path.exists(dst):
                        raise SystemExit("目标已存在，拒绝覆盖：%s" % dst)
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.move(src, dst)
                    moved += 1
                    print("改名 %s  →  %s" % (os.path.relpath(src, ROOT), os.path.relpath(dst, ROOT)))
        # 清理空的旧学段目录
        for pub in sorted(os.listdir(src_stage)):
            p = os.path.join(src_stage, pub)
            if os.path.isdir(p) and not os.listdir(p):
                os.rmdir(p)
        if not os.listdir(src_stage):
            os.rmdir(src_stage)
            print("清理空目录：%s" % old)
    print("完成：共改名 %d 个年级目录" % moved)


if __name__ == "__main__":
    if "--yes" not in sys.argv:
        print("学段改名（middle→junior、high→senior）。确认执行请加 --yes 参数。")
        raise SystemExit(1)
    main()
