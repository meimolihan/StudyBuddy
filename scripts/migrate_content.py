#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
教材内容目录规范化导入工具。

用途：把「旧命名」的课程 HTML 批量整理成 StudyBuddy 的标准内容目录树，
以后新增教材只要按标准结构放文件即可，系统自动识别，无需改代码。

标准结构（路径本身即元数据，不再在文件名里重复）：

    content/<stage>/<publisher>/grade<N>/volume<N>/<subject>/<NN-单元名>/<NN-课名>.html
    content/primary/pep/grade4/volume1/chinese/01-自然之美/01-观潮.html

  stage     学段：primary / middle / high
  publisher 出版社：pep 等
  grade<N>  年级：grade1 ~ grade6 / grade7 ~ grade9 / grade10 ~ grade12
  volume<N> 册别：volume1 上册 / volume2 下册
  subject   科目：chinese / math / english / morallaw / science
  NN-单元名 单元目录（两位序号，保证排序）
  NN-课名   课程文件（两位序号）

用法：
    python scripts/migrate_content.py --dry-run      # 预览，不落盘
    python scripts/migrate_content.py                # 执行移动
"""

import argparse
import os
import re
import shutil
import sys

SUBJECTS = ("chinese", "math", "english", "morallaw", "science")

RE_GRADE = re.compile(r"grade(\d+)")
RE_VOLUME = re.compile(r"volume(\d+)")
RE_UNIT = re.compile(r"第([^单]*)单元")
RE_LESSON = re.compile(r"第([0-9]+)课")

# Windows 文件名非法字符
BAD_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

CN_DIGITS = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
             "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


def cn_num(s: str) -> int:
    """中文数字（一 ~ 九十九）转阿拉伯数字；无法识别返回 0。"""
    total, num = 0, 0
    for ch in s:
        if ch in CN_DIGITS:
            num = CN_DIGITS[ch]
            continue
        if ch == "十":
            total += (num or 1) * 10
            num = 0
        elif ch == "百":
            total += (num or 1) * 100
            num = 0
    return total + num


def safe(name: str) -> str:
    """清洗为合法的文件/目录名。"""
    name = BAD_CHARS.sub("_", name).strip().strip(".")
    return name or "未命名"


def parse_legacy(base: str):
    """
    解析旧文件名：「四年级语文上册 · 第一单元 自然之美 · 第1课 观潮」
    返回 (unit_no, unit_name, lesson_no, lesson_name)。
    """
    parts = [p.strip() for p in base.split("·")]
    if len(parts) >= 3:
        unit_raw, lesson_raw = parts[-2], parts[-1]
    elif len(parts) == 2:
        unit_raw, lesson_raw = parts[0], parts[1]
    else:
        return 0, "", 0, base

    unit_no, unit_name = 0, unit_raw
    m = RE_UNIT.search(unit_raw)
    if m:
        unit_no = cn_num(m.group(1))
        unit_name = unit_raw[m.end():].strip()

    lesson_no, lesson_name = 0, lesson_raw
    m = RE_LESSON.search(lesson_raw)
    if m:
        lesson_no = int(m.group(1))
        lesson_name = lesson_raw[m.end():].strip()
    else:
        m2 = re.search(r"第([^课]*)课", lesson_raw)
        if m2:
            lesson_no = cn_num(m2.group(1))
            lesson_name = lesson_raw[m2.end():].strip()

    return unit_no, unit_name, lesson_no, lesson_name


def detect_meta(rel_parts):
    """从旧路径中识别 学段 / 出版社 / 年级 / 册别 / 科目。"""
    stage, publisher, grade, volume, subject = "primary", "pep", 0, 1, ""
    for p in rel_parts[:-1]:
        low = p.lower()
        if "school" in low:
            stage = {"primary-school": "primary", "middle-school": "middle",
                     "high-school": "high"}.get(low, low.replace("-school", ""))
        m = RE_GRADE.search(low)
        if m:
            grade = int(m.group(1))
        m = RE_VOLUME.search(low)
        if m:
            volume = int(m.group(1))
        for s in SUBJECTS:
            if low.endswith("-" + s):
                subject = s
    return stage, publisher, grade, volume, subject


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="primary-school", help="旧教材根目录")
    ap.add_argument("--dst", default="content", help="标准内容根目录")
    ap.add_argument("--dry-run", action="store_true", help="仅预览")
    args = ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = os.path.join(root, args.src)
    dst = os.path.join(root, args.dst)

    if not os.path.isdir(src):
        print("源目录不存在：%s（可能已迁移过）" % src)
        return 0

    plan, skipped = [], []
    for dirpath, _dirs, files in os.walk(src):
        for fn in sorted(files):
            if not fn.lower().endswith(".html"):
                continue
            old = os.path.join(dirpath, fn)
            rel = os.path.relpath(old, src)
            parts = rel.replace("\\", "/").split("/")
            stage, publisher, grade, volume, subject = detect_meta(parts)
            if grade == 0 or not subject:
                skipped.append(rel + "  （路径不符合规范）")
                continue
            base = os.path.splitext(fn)[0]
            # 已规范化的文件名（NN-课名）直接沿用，不再二次解析
            if re.match(r"^\d{2,}-", base):
                unit_no, unit_name = 0, ""
                lesson_no = int(re.match(r"^(\d+)-", base).group(1))
                lesson_name = base.split("-", 1)[1]
            else:
                unit_no, unit_name, lesson_no, lesson_name = parse_legacy(base)

            unit_dir = "%02d-%s" % (unit_no, safe(unit_name)) if unit_name else "00-未分单元"
            new_name = "%02d-%s.html" % (lesson_no, safe(lesson_name))
            new_rel = "/".join([stage, publisher, "grade%d" % grade,
                                "volume%d" % volume, subject, unit_dir, new_name])
            plan.append((old, os.path.join(dst, *new_rel.split("/")), new_rel))

    print("待迁移 %d 个课程文件，跳过 %d 个" % (len(plan), len(skipped)))
    for s in skipped[:10]:
        print("   跳过:", s)

    if args.dry_run:
        print("\n--- 预览（前 12 条）---")
        for _old, _new, rel in plan[:12]:
            print("   ", rel)
        print("   ...")
        return 0

    moved = 0
    for old, new, rel in plan:
        os.makedirs(os.path.dirname(new), exist_ok=True)
        shutil.move(old, new)
        moved += 1
    print("\n已迁移 %d 个文件到 %s/" % (moved, args.dst))

    # 迁移后清理空的旧目录（仅删空目录，非空则保留）
    removed = 0
    for dirpath, _dirs, _files in os.walk(src, topdown=False):
        try:
            if not os.listdir(dirpath):
                os.rmdir(dirpath)
                removed += 1
        except OSError:
            pass
    print("已清理 %d 个空目录" % removed)
    if os.path.isdir(src) and not os.listdir(src):
        try:
            os.rmdir(src)
            print("旧根目录 %s/ 已为空并移除" % args.src)
        except OSError as e:
            print("旧根目录保留（%s）" % e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
