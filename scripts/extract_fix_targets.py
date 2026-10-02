# -*- coding: utf-8 -*-
"""提取全部待修题目原文（只读，不修改任何 content/ 文件）。
输入：reports/audit_data.json + content/ 题库原文
输出：reports/fix_targets.json（机器可读，供修复脚本定位题号）
      reports/fix_targets.md （人读原文清单）
"""
import json, os, re, glob
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "content")

# ---------- 解析函数（复制自 audit_bank.py，保持口径一致） ----------
RE_T = re.compile(r'\bt\s*:\s*"([a-z])"')
RE_Q = re.compile(r'\bq\s*:\s*"(..*?)"\s*,\s*o\s*:\s*\[', re.S)
RE_E = re.compile(r',\s*e\s*:\s*"(..*?)"\s*\}\s*$', re.S)
RE_STR = re.compile(r'"(?:[^"\\]|\\.)*"')

def extract_objects(src):
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
    """解析单个题库文件 -> 题目列表（1-based 下标访问）"""
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

def to_fs(rel):
    """audit rel（choose/primary/...）-> 文件系统相对 content 路径（primary/pep/choose/...）"""
    parts = rel.split("/")
    return "/".join([parts[1], "pep", parts[0]] + parts[2:])

def find_one(pattern):
    """content 下 glob，返回文件系统相对路径（stage/pep/qtype/...，用 / 分隔）"""
    hits = glob.glob(os.path.join(CONTENT, pattern))
    if not hits:
        return None
    return os.path.relpath(sorted(hits)[0], CONTENT).replace("\\", "/")

def mirror(rel):
    """文件系统形式路径的 choose<->judge 镜像"""
    return rel.replace("/choose/", "/judge/", 1)

# ---------- 定位表 ----------
# (tag, choose 相对 content 的 glob, choose 题号, judge 题号, 问题描述)
TARGETS = [
    # P0 判分争议
    ("P0", "primary/pep/choose/grade5/volume2/math/04-*/16-约分.html", [25], [],
     "单选 A/C/D 三项均为正确说法，答案不唯一"),
    ("P0", "primary/pep/choose/grade6/volume1/math/03-*/08-倒数的认识.html", [23], [],
     "单选 B/D 双正确（D 与本文件第 16 题答案自证），且与第 16 题矛盾"),
    ("P0", "high/pep/choose/grade2/volume1/biology/02-*/04-神经系统的分级调节.html", [4, 6, 22], [6, 7],
     "「与其大小无关」指代不明，应为「与躯体各部分的实际大小无关」"),
    # B 类表述/知识性瑕疵
    ("B", "middle/pep/choose/grade3/volume2/history/*/10-列宁与十月革命.html", [2], [3],
     "《和平法令》《土地法令》被表述为「巩固时期」颁布，教材为「十月革命胜利后及时颁布」"),
    ("B", "middle/pep/choose/grade1/volume1/biology/*/17-绿色植物是生物圈中有机物的制造者.html", [8], [15],
     "「光合作用的条件」给光和叶绿体——光是条件、叶绿体是场所，与本库场所题冲突"),
    ("B", None, [], [23], "「无限循环小数」的含义是是有理数——模板叠字病句"),  # 实数 judge
    ("B", None, [], [33], "judge 病句「0有，是 0倒数。」——模板拼接错误"),
    ("B", "primary/pep/choose/grade3/volume2/math/05-*/15-数据的收集与整理.html", [18], [],
     "题干设两空但选项只对应后一空，且「16 人占几分之几」超三年级范围"),
    ("B", "primary/pep/choose/grade4/volume1/english/*/02-句型.html", [39], [],
     "一般现在时三单（likes）非 PEP 四上句型（三个 02-句型.html 都取，人工确认）"),
    ("B", "high/pep/choose/grade2/volume2/english/*/04-Unit 4*.html", [2, 13], [2, 3, 34, 35],
     "Tired and hungry 为形容词短语，被归为「过去分词作原因状语」误导归类"),
    ("B", "high/pep/choose/grade1/volume1/chinese/*/09-念奴娇·赤壁怀古*.html", [4, 24], [],
     "《虞美人》《鹊桥仙》非第 9 课课文（属古诗词诵读板块），范围偏移"),
    ("B", "high/pep/choose/grade3/review/chinese/03-文言文阅读.html", [6], [],
     "直译解释为「逐字对应」，通行表述为「字字落实」"),
    ("B", "middle/pep/choose/grade3/volume1/morallaw/*/06-建设美丽中国.html", [4, 17], [7, 17],
     "「保护环境基本国策」配「绿水青山就是金山银山」——并列表述非包含关系"),
]

# 实数 judge / 倒数 judge 的准确路径
SPECIAL_JUDGE = {
    "实数": ("middle/pep/judge/grade1/volume2/math/02-实数/03-实数.html", [23]),
    "倒数judge": ("primary/pep/judge/grade6/volume1/math/03-*/08-倒数的认识.html", [33]),
}

# ---------- 1) 提取 P0 + B 类原文 ----------
extracted = []   # [{tag, note, qtype, rel, no, q...}]
md = []
md.append("# 待修题目原文提取（fix_targets）\n")
md.append("> 生成方式：只读提取脚本，未修改任何题库文件。供 #164/#165 修复定位。\n")

def emit(tag, note, qtype, rel, no, bank):
    if no > len(bank):
        extracted.append({"tag": tag, "note": note, "qtype": qtype, "rel": rel, "no": no, "error": "题号越界"})
        md.append(f"\n## [{tag}] {rel} 第 {no} 题\n\n**⚠ 题号越界（该文件共 {len(bank)} 题）**\n")
        return
    q = bank[no - 1]
    rec = {"tag": tag, "note": note, "qtype": qtype, "rel": rel, "no": no,
           "t": q["t"], "q": q["q"], "o": q["o"], "a": q["a"], "e": q["e"]}
    extracted.append(rec)
    md.append(f"\n## [{tag}] {rel} ｜ 第 {no} 题 ｜ type={q['t']} 答案={''.join(q['a'])}\n")
    md.append(f"- **问题**：{note}\n- **题干**：{q['q']}\n- **选项**：{json.dumps(q['o'], ensure_ascii=False)}\n")
    if q["e"]:
        md.append(f"- **解析**：{q['e']}\n")

print("=== 1) P0 + B 类定位提取 ===")
for tag, pat, cnos, jnos, note in TARGETS:
    if tag == "B" and pat is None:
        continue  # 特殊处理在下方
    if pat is None:
        continue
    rel = find_one(pat)
    if rel is None:
        print(f"  !! 未找到: {pat}")
        md.append(f"\n**⚠ 未找到文件：{pat}**\n")
        continue
    bank_c = load_bank(os.path.join(CONTENT, rel))
    for no in cnos:
        emit(tag, note, "choose", rel, no, bank_c)
    # 附带参照题：P0 打印同文件相邻题自证
    if tag == "P0" and "约分" in rel:
        for no in (14, 22):
            emit("REF", "P0 参照（同文件自证）", "choose", rel, no, bank_c)
    if tag == "P0" and "倒数的认识" in rel and "choose" in rel:
        for no in (16,):
            emit("REF", "P0 参照（同文件第 16 题自证 D 正确）", "choose", rel, no, bank_c)
    if jnos:
        jrel = mirror(rel)
        if os.path.exists(os.path.join(CONTENT, jrel)):
            bank_j = load_bank(os.path.join(CONTENT, jrel))
            for no in jnos:
                emit(tag, note, "judge", jrel, no, bank_j)
        else:
            print(f"  !! 镜像缺失: {jrel}")

# 特殊：实数 judge #23、倒数 judge #33
for key, (pat, nos) in SPECIAL_JUDGE.items():
    rel = find_one(pat)
    if rel is None:
        print(f"  !! 未找到: {pat}")
        continue
    bank = load_bank(os.path.join(CONTENT, rel))
    note = SPECIAL_NOTES = {
        "实数": "「无限循环小数」的含义是是有理数——模板叠字病句",
        "倒数judge": "judge 病句「0有，是 0倒数。」——模板拼接错误",
    }[key]
    for no in nos:
        emit("B", note, "judge", rel, no, bank)

# ---------- 2) format_opts 59 题原文 ----------
print("=== 2) format_opts 选项重复 59 题 ===")
audit = json.load(open(os.path.join(ROOT, "reports", "audit_data.json"), encoding="utf-8"))
md.append("\n---\n\n# format_opts 选项重复（59 题 / 10 文件）\n")
fmt_recs = []
by_file = defaultdict(list)
for it in audit["issues"]["format_opts"]:
    by_file[to_fs(it["path"])].append(it["no"])
for rel, nos in sorted(by_file.items()):
    full = os.path.join(CONTENT, rel)
    if not os.path.exists(full):
        print(f"  !! 文件缺失: {rel}")
        continue
    bank = load_bank(full)
    md.append(f"\n## {rel}\n")
    for no in sorted(nos):
        if no > len(bank):
            md.append(f"- 第 {no} 题：⚠ 越界\n")
            continue
        q = bank[no - 1]
        rec = {"tag": "format_opts", "qtype": "choose", "rel": rel, "no": no,
               "t": q["t"], "q": q["q"], "o": q["o"], "a": q["a"], "e": q["e"]}
        fmt_recs.append(rec)
        md.append(f"- **第 {no} 题** 答案={''.join(q['a'])}｜{q['q']}\n  - 选项：{json.dumps(q['o'], ensure_ascii=False)}\n")
extracted.extend(fmt_recs)

# ---------- 3) dup_stem_in_file 11 处（打印两题原文对） ----------
print("=== 3) 课内题干重复 11 处 ===")
md.append("\n---\n\n# 课内题干重复（11 处，含被重复题原文）\n")
dup_recs = []
for it in audit["issues"]["dup_stem_in_file"]:
    rel, no = to_fs(it["path"]), it["no"]
    m = re.search(r"与第 (\d+) 题", it["detail"])
    with_no = int(m.group(1)) if m else None
    full = os.path.join(CONTENT, rel)
    if not os.path.exists(full):
        print(f"  !! 文件缺失: {rel}")
        continue
    bank = load_bank(full)
    qa = bank[no - 1] if no <= len(bank) else None
    qb = bank[with_no - 1] if with_no and with_no <= len(bank) else None
    md.append(f"\n## {rel}\n- 第 {no} 题 与 第 {with_no} 题题干重复\n")
    for label, q in (("重复题", qa), ("被重复题", qb)):
        if q is None:
            md.append(f"- {label}：⚠ 越界\n")
            continue
        rec = {"tag": "dup_stem", "role": label, "qtype": "choose", "rel": rel,
               "no": no, "with_no": with_no, "t": q["t"], "q": q["q"], "o": q["o"], "a": q["a"], "e": q["e"]}
        dup_recs.append(rec)
        md.append(f"- **{label}（第 {dup_recs[-1]['no'] if label=='重复题' else with_no} 题）** 答案={''.join(q['a'])}｜{q['q']}\n  - 选项：{json.dumps(q['o'], ensure_ascii=False)}\n")
extracted.extend(dup_recs)

# ---------- 4) count_out_of_range 18 文件 + 删除候选分析 ----------
print("=== 4) 题量超标 18 文件（删除候选分析） ===")
md.append("\n---\n\n# 题量 43→40 裁剪分析（18 文件）\n")
oor = []
# 建立同学科同册（primary grade4 volume1 english）全部文件的题干集合，用于跨文件重复判定
eng_dir = os.path.join(CONTENT, "primary/pep/choose/grade4/volume1/english")
cross_map = defaultdict(set)   # stem_md5 -> set(rel)
file_banks = {}
for dirpath, _, files in os.walk(eng_dir):
    for fn in sorted(files):
        if not fn.endswith(".html"):
            continue
        full = os.path.join(dirpath, fn)
        rel = os.path.relpath(full, CONTENT).replace("\\", "/")
        bank = load_bank(full)
        file_banks[rel] = bank
        for i, q in enumerate(bank, 1):
            key = (q["q"] or "").strip()
            if key:
                cross_map[key].add(rel)
# 课内重复题号（audit 已知）
in_file_dup = defaultdict(list)
for it in audit["issues"]["dup_stem_in_file"]:
    in_file_dup[to_fs(it["path"])].append(it["no"])
for it in audit["issues"]["count_out_of_range"]:
    rel = to_fs(it["path"])
    bank = file_banks.get(rel) or (load_bank(os.path.join(CONTENT, rel)) if os.path.exists(os.path.join(CONTENT, rel)) else [])
    if not bank:
        print(f"  !! 文件缺失: {rel}")
        continue
    dups_in = sorted(in_file_dup.get(rel, []))
    cross = []
    for i, q in enumerate(bank, 1):
        key = (q["q"] or "").strip()
        if key and len(cross_map[key] - {rel}) > 0:
            cross.append(i)
    # 删除候选顺序：课内重复 -> 跨文件重复 -> 末尾题
    candidates = dups_in + [n for n in cross if n not in dups_in]
    tail = list(range(len(bank), 0, -1))
    for n in tail:
        if len(candidates) >= len(bank) - 40:
            break
        if n not in candidates:
            candidates.append(n)
    candidates = candidates[: len(bank) - 40]
    oor.append({"rel": rel, "count": len(bank), "in_file_dups": dups_in,
                "cross_dups": cross, "delete_plan": sorted(candidates)})
    md.append(f"\n## {rel}（{len(bank)} 题，删 {len(bank)-40} 题）\n")
    md.append(f"- 课内重复题号：{dups_in or '无'}\n- 跨文件重复题号：{cross or '无'}\n- **建议删除（共 {len(candidates)} 题）**：{sorted(candidates)}\n")

# ---------- 5) dup_lesson_same_unit 46 项：完整文件对清单 ----------
print("=== 5) 重复文件 46 项分组清单 ===")
md.append("\n---\n\n# 重复生成文件（grade3/volume1/math 五单元，choose+judge）\n")
dup_files = []
g3 = os.path.join(CONTENT, "primary/pep")
for qtype in ("choose", "judge"):
    base = os.path.join(g3, qtype, "grade3/volume1/math")
    if not os.path.isdir(base):
        continue
    md.append(f"\n## {qtype}\n")
    for dirpath, _, files in os.walk(base):
        htmls = sorted(fn for fn in files if fn.endswith(".html"))
        groups = defaultdict(list)
        for fn in htmls:
            m = re.match(r"^\d{2,3}-(.+)\.html$", fn)
            if m:
                groups[m.group(1)].append(fn)
        unit_rel = os.path.relpath(dirpath, CONTENT).replace("\\", "/")
        for name, fns in sorted(groups.items()):
            if len(fns) < 2:
                continue
            fns_sorted = sorted(fns)  # 字典序 = 批次 A(低序号)在前
            keep = fns_sorted[1:]     # 保留批次 B（高序号）
            drop = fns_sorted[:1]     # 删除批次 A（低序号）
            rec = {"qtype": qtype, "unit": unit_rel, "lesson": name,
                   "files": fns_sorted, "drop_batchA": [os.path.join(unit_rel, f).replace("\\", "/") for f in drop],
                   "keep_batchB": [os.path.join(unit_rel, f).replace("\\", "/") for f in keep]}
            dup_files.append(rec)
            md.append(f"- **{name}**：{' / '.join(fns_sorted)} ｜ 删批次A：{drop} ｜ 留批次B：{keep}\n")

# ---------- 6) 「的含义是」模板统计 ----------
print("=== 6) 「含义是」模板全库统计 ===")
md.append("\n---\n\n# 「含义是」模板统计（全库题干级）\n")
hany = {
    "choose_bracket": defaultdict(int),   # choose 题干含「的含义是（」
    "choose_plain": defaultdict(int),     # choose 含「的含义是」但无括号
    "judge_bracket": defaultdict(int),    # judge 拼接句却带括号
    "judge_plain": defaultdict(int),      # judge 拼接句（无括号）
    "quote_nested": defaultdict(int),     # 题干含「““」引号嵌套
}
samples = defaultdict(list)
SUBJ_KEYS = ["chinese", "math", "english", "morallaw", "science", "history", "geography",
             "biology", "physics", "chemistry", "politics", "information"]
def stage_subject(rel):
    parts = rel.split("/")
    stage = parts[1] if parts[0] in ("choose", "judge") else parts[0]
    subj = next((p for p in parts if p in SUBJ_KEYS), "?")
    return stage, subj

for qtype in ("choose", "judge"):
    base = os.path.join(CONTENT, "primary/pep", qtype), os.path.join(CONTENT, "middle/pep", qtype), os.path.join(CONTENT, "high/pep", qtype)
    for root in base:
        if not os.path.isdir(root):
            continue
        for dirpath, _, files in os.walk(root):
            for fn in files:
                if not fn.endswith(".html"):
                    continue
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, CONTENT).replace("\\", "/")
                st, subj = stage_subject(rel)
                src = open(full, encoding="utf-8").read()
                objs = extract_objects(src)
                if not objs:
                    continue
                for txt in objs:
                    mq = RE_Q.search(txt)
                    if not mq:
                        continue
                    q = unesc(mq.group(1))
                    if "““" in q or "””" in q:
                        hany["quote_nested"][f"{qtype}/{st}/{subj}"] += 1
                        if len(samples["quote_nested"]) < 6:
                            samples["quote_nested"].append(f"{rel} ｜ {q[:60]}")
                    if "的含义是" not in q:
                        continue
                    if "的含义是（" in q:
                        hany[f"{qtype}_bracket"][f"{qtype}/{st}/{subj}"] += 1
                        if len(samples[f"{qtype}_bracket"]) < 8:
                            samples[f"{qtype}_bracket"].append(f"{rel} ｜ {q[:70]}")
                    else:
                        hany[f"{qtype}_plain"][f"{qtype}/{st}/{subj}"] += 1
                        if len(samples[f"{qtype}_plain"]) < 8:
                            samples[f"{qtype}_plain"].append(f"{rel} ｜ {q[:70]}")

md.append("\n## choose 带括号「的含义是（　）」\n")
tot = 0
for k, v in sorted(hany["choose_bracket"].items()):
    md.append(f"- {k}: {v}\n"); tot += v
md.append(f"- **合计 {tot}**\n")
md.append("\n## judge 拼接句「“X”的含义是…」（无括号）\n")
tot2 = 0
for k, v in sorted(hany["judge_plain"].items()):
    md.append(f"- {k}: {v}\n"); tot2 += v
md.append(f"- **合计 {tot2}**\n")
md.append("\n## choose 无括号变体 / judge 带括号（异常形态）\n")
md.append(f"- choose_plain: {dict(hany['choose_plain']) or '无'}\n- judge_bracket: {dict(hany['judge_bracket']) or '无'}\n")
md.append("\n## 题干引号嵌套「““」\n")
tot3 = 0
for k, v in sorted(hany["quote_nested"].items()):
    md.append(f"- {k}: {v}\n"); tot3 += v
md.append(f"- **合计 {tot3}**\n")
md.append("\n## 样例\n")
for cat, ss in samples.items():
    md.append(f"\n### {cat}\n")
    for s in ss:
        md.append(f"- {s}\n")

# ---------- 落盘 ----------
out = {
    "targets": extracted,
    "format_opts": fmt_recs,
    "dup_stem": dup_recs,
    "out_of_range": oor,
    "dup_files": dup_files,
    "hanyishi": {k: dict(v) for k, v in hany.items()},
}
with open(os.path.join(ROOT, "reports", "fix_targets.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
with open(os.path.join(ROOT, "reports", "fix_targets.md"), "w", encoding="utf-8") as f:
    f.writelines(md)

print(f"\ntargets(含参照): {len(extracted)} 条")
print(f"format_opts: {len(fmt_recs)} 题")
print(f"dup_stem 原文对: {len(dup_recs)} 条")
print(f"out_of_range: {len(oor)} 文件")
print(f"dup_files 组: {len(dup_files)} 组")
print(f"含义是: choose_bracket={sum(hany['choose_bracket'].values())} judge_plain={sum(hany['judge_plain'].values())} 引号嵌套={sum(hany['quote_nested'].values())}")
print("OK -> reports/fix_targets.json + reports/fix_targets.md")
