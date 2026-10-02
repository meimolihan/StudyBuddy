# -*- coding: utf-8 -*-
"""修复 #166：清理 grade3/volume1/math 的 46 份重复生成文件（v2，按单元聚合重编号）。
步骤：
  1) 每组重复文件先比对「题干+选项」签名集合完全一致（不一致则保留并报告，不删除）；
  2) 一致 → 删除批次 A（低序号）文件（内容已在 backup/content_backup_2026-10-02 全量备份）；
  3) 按「单元」聚合所有保留文件（批次 B + 该单元内无重复的普通课），按原序号升序重排为 01~N
     （旧批次 B 序号 08~30 > 新序号上限，且保留课的原序号唯一，直接 rename 无撞名风险）。
默认 dry-run，--apply 执行。
"""
import json, os, sys, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _banklib import load_bank

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "content")
APPLY = "--apply" in sys.argv

audit = json.load(open(os.path.join(ROOT, "reports", "fix_targets.json"), encoding="utf-8"))
groups = audit["dup_files"]   # 46 组

def fs(rel):
    return os.path.join(CONTENT, rel.replace("/", os.sep))

def sig(full):
    qs = load_bank(full)
    return {hashlib.md5((q["q"] + "|" + "|".join(sorted(q["o"]))).encode()).hexdigest() for q in qs}

deleted, renamed, kept_unequal, errors = 0, 0, [], []
# unit_dir -> set(保留文件的 fs rel)
unit_keeps = {}
for g in groups:
    drop = g["drop_batchA"][0]
    keeps = g["keep_batchB"]
    drop_full = fs(drop)
    try:
        s_drop = sig(drop_full)
    except Exception as ex:
        errors.append([drop, f"读取失败 {ex}"])
        continue
    equal_all = True
    for k in keeps:
        try:
            if sig(fs(k)) != s_drop:
                equal_all = False
                kept_unequal.append([drop, k])
                break
        except Exception as ex:
            errors.append([k, f"读取失败 {ex}"])
            equal_all = False
            break
    if not equal_all:
        continue
    if APPLY:
        os.remove(drop_full)
    deleted += 1
    for k in keeps:
        unit_keeps.setdefault(os.path.dirname(fs(k)), set()).add(k)

# 按单元聚合重编号：单元内全部现存 html（保留课 + 未涉及重复的普通课）按序号升序 → 01~N
renames = []   # (old_full, new_full)
# 每单元将被删除的批次 A 文件名（dry-run 时未真删，校验需排除）
unit_drops = {}
for g in groups:
    drop_rel = g["drop_batchA"][0]
    unit_drops.setdefault(os.path.dirname(fs(drop_rel)), set()).add(os.path.basename(drop_rel))
for unit_dir, keeps in unit_keeps.items():
    drops_here = unit_drops.get(unit_dir, set())
    all_html = sorted(fn for fn in os.listdir(unit_dir) if fn.endswith(".html") and fn not in drops_here)
    # 校验：单元内文件序号（删除批次A后）应唯一
    from collections import Counter
    nums = [fn.split("-", 1)[0] for fn in all_html]
    dup_nums = [n for n, c in Counter(nums).items() if c > 1]
    if dup_nums:
        errors.append([unit_dir, f"删除后仍有撞号: {dup_nums}"])
        continue
    for idx, fn in enumerate(sorted(all_html, key=lambda f: f.split("-", 1)[0]), 1):
        new_name = f"{idx:02d}-{fn.split('-', 1)[1]}"
        if new_name != fn:
            renames.append((os.path.join(unit_dir, fn), os.path.join(unit_dir, new_name)))

renamed = len(renames)
if APPLY:
    # 旧序号 08~30 → 新 01~N 降序映射，无撞名；仍按目标名排序执行保险
    for old_full, new_full in sorted(renames, key=lambda x: x[1]):
        os.rename(old_full, new_full)

print(f"APPLY={APPLY}")
print(f"比对一致并删除: {deleted} ｜ 重命名: {renamed}")
print(f"内容不一致保留: {len(kept_unequal)} ｜ 错误: {len(errors)}")
for x in kept_unequal:
    print("  UNEQUAL:", x)
for x in errors:
    print("  ERROR:", x)
