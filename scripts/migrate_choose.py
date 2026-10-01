# -*- coding: utf-8 -*-
"""把原有选择题库迁移到 choose 目录，并按新学段命名重建目录树。

原结构：
    content/primary/pep/gradeN/...          小学（N=1~6）
    content/middle/pep/gradeN/...           初中（N=1~3，即七/八/九年级）
    content/high/pep/gradeN/...             高中（N=1~3，含 grade3/review 高考复习专题）

新结构：
    content/primary/pep/choose/gradeN/...   小学
    content/junior/pep/choose/gradeN/...    初中（N=7~9）
    content/senior/pep/choose/gradeN/...    高中（N=1~3）

只做「目录移动 / 改名」，不复制、不改动任何 HTML 文件内容；
禁止交叉覆盖：目标已存在时直接报错中止。
"""
import os
import shutil
import sys

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "content")

# (原学段, 原出版社, 新学段, 年级偏移)
PLAN = [
    ("primary", "pep", "primary", 0),
    ("middle", "pep", "junior", 6),   # grade1/2/3 → grade7/8/9
    ("high", "pep", "senior", 0),
]


def move_dir(src, dst):
    if os.path.exists(dst):
        raise SystemExit("目标已存在，拒绝覆盖：%s" % dst)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.move(src, dst)
    return dst


def main():
    moved = 0
    for old_stage, pub, new_stage, off in PLAN:
        src_pub = os.path.join(ROOT, old_stage, pub)
        if not os.path.isdir(src_pub):
            print("跳过（不存在）：%s" % src_pub)
            continue
        for name in sorted(os.listdir(src_pub)):
            src = os.path.join(src_pub, name)
            if not os.path.isdir(src) or not name.startswith("grade"):
                continue
            try:
                n = int(name[len("grade"):])
            except ValueError:
                continue
            dst = os.path.join(ROOT, new_stage, pub, "choose", "grade%d" % (n + off))
            move_dir(src, dst)
            moved += 1
            print("迁移 %s  →  %s" % (os.path.relpath(src, ROOT), os.path.relpath(dst, ROOT)))
        # 清掉空的旧学段目录（publisher 层及其父层）
        if not os.listdir(src_pub):
            os.rmdir(src_pub)
            old_stage_dir = os.path.join(ROOT, old_stage)
            if not os.listdir(old_stage_dir):
                os.rmdir(old_stage_dir)
                print("清理空目录：%s" % old_stage)
    print("完成：共迁移 %d 个年级目录" % moved)


if __name__ == "__main__":
    if "--yes" not in sys.argv:
        print("这是一次目录改名迁移（不复制、不覆盖）。确认执行请加 --yes 参数。")
        raise SystemExit(1)
    main()
