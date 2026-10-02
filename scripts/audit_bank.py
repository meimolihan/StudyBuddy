# -*- coding: utf-8 -*-
"""StudyBuddy 题库全面审查（只读）。
严禁修改/覆盖/删除任何 content/ 下 HTML 文件；本脚本只读文件、输出 reports/audit_data.json。
审查维度：镜像配对 / 命名规范 / 题库结构与格式 / 题量 / 解析字段 / 重复题 / DOM 模板标记 / 结构统计 / 抽样清单。
"""
import json, os, re, sys, hashlib, random
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "content")
OUT = os.path.join(ROOT, "reports", "audit_data.json")

STAGES = ["primary", "middle", "high"]
QTYPES = ["choose", "judge"]
UNIT_RE = re.compile(r"^(\d{2,3})-([^\\/:*?\"<>|]+)$")
FILE_RE = re.compile(r"^(\d{2,3})-([^\\/:*?\"<>|]+)\.html$")
CN_NUM = "一二三四五六七八九十"

issues = defaultdict(list)   # category -> list of {path, ...}
stats = defaultdict(int)

def add(cat, **kw):
    issues[cat].append(kw)

# ---------- 1) 收集文件树 ----------
def collect(qtype):
    """返回 {相对 qtype 根的 rel: fullpath}；树为 content/<stage>/pep/<qtype>/..."""
    tree = {}
    for stage in STAGES:
        base = os.path.join(CONTENT, stage, "pep", qtype)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            for fn in filenames:
                if not fn.lower().endswith(".html"):
                    add("stray_file", path=os.path.relpath(os.path.join(dirpath, fn), CONTENT))
                    continue
                r = os.path.relpath(os.path.join(dirpath, fn), base)
                tree[stage + "/" + r.replace("\\", "/")] = os.path.join(dirpath, fn)
    return tree

trees = {q: collect(q) for q in QTYPES}
for q in QTYPES:
    stats[f"files_{q}"] = len(trees[q])

# ---------- 2) 镜像配对 ----------
choose_set, judge_set = set(trees["choose"]), set(trees["judge"])
for rel in sorted(choose_set - judge_set):
    add("mirror_missing_judge", path=f"choose/{rel}")
for rel in sorted(judge_set - choose_set):
    add("mirror_missing_choose", path=f"judge/{rel}")
stats["mirror_pairs"] = len(choose_set & judge_set)
stats["mirror_unpaired"] = len(choose_set ^ judge_set)

# ---------- 3) 路径解析 + 命名规范 ----------
def parse_rel(rel):
    """stage/grade1/volume1/chinese/01-单元/01-课.html -> dict；review 特例无单元层"""
    parts = rel.split("/")
    if len(parts) == 6:      # stage/grade/vol/subject/unit/file
        stage, grade, vol, subject, unit, fn = parts
        unit_name = unit
    elif len(parts) == 5:    # stage/grade/review/subject/file（高考复习）
        stage, grade, vol, subject, fn = parts
        unit_name = ""
        if vol != "review":
            return None
    else:
        return None
    info = {"stage": stage}
    m = FILE_RE.match(fn)
    if not m:
        return None
    info.update({"grade": grade, "vol": vol, "subject": subject, "unit": unit_name,
                 "file": fn, "no": m.group(1), "name": m.group(2)})
    return info

parsed = {}
for q in QTYPES:
    parsed[q] = {}
    for rel, full in trees[q].items():
        info = parse_rel(rel)
        if info is None:
            add("naming_bad", path=f"{q}/{rel}", detail="路径或文件名不符合 NN-规范")
            continue
        gm = re.match(r"^grade(\d+)$", info["grade"])
        if not gm:
            add("naming_bad", path=f"{q}/{rel}", detail="年级目录名非法")
            continue
        info["gradeN"] = int(gm.group(1))
        if info["vol"] != "review":
            vm = re.match(r"^volume(\d+)$", info["vol"])
            if not vm:
                add("naming_bad", path=f"{q}/{rel}", detail="册目录名非法")
                continue
            info["volN"] = int(vm.group(1))
        if info["unit"]:
            um = UNIT_RE.match(info["unit"])
            if not um:
                add("naming_bad", path=f"{q}/{rel}", detail="单元目录名不符合 NN-名称")
                continue
        parsed[q][rel] = info

# 单元目录与课文序号重复检查（语文=册内连续；其余=单元内）
for q in QTYPES:
    seen_unit = defaultdict(set)    # (stage,grade,vol,subject) -> {unit_no}（按目录去重）
    seen_lesson_chinese = defaultdict(list)  # (stage,grade,vol) -> [(file_no, path)]
    seen_lesson_other = defaultdict(list)    # (grade,vol,subject,unit) -> [(file_no, path)]
    for rel, info in parsed[q].items():
        if info["unit"]:
            key = (info["stage"], info["grade"], info["vol"], info["subject"])
            seen_unit[key].add(info["unit"].split("-")[0])
            lk = key + (info["unit"],)
            seen_lesson_other[lk].append((info["no"], f"{q}/{rel}"))
            if info["subject"] == "chinese":
                seen_lesson_chinese[(info["stage"], info["grade"], info["vol"])].append((info["no"], f"{q}/{rel}"))
    for key, nos_set in seen_unit.items():
        nos = sorted(nos_set)
        dup = sorted({n for n in nos if nos.count(n) > 1})
        if dup:
            add("naming_dup_unit", path=f"{q}/{key[0]}/{key[1]}/{key[2]}", detail=f"单元序号重复: {dup}")
    # 同一单元目录内课名重复（不同序号、相同课名 → 疑似重复生成）
    seen_name = defaultdict(lambda: defaultdict(set))  # (stage,g,v,sub,unit) -> 课名 -> {序号}
    for rel, info in parsed[q].items():
        if info["unit"]:
            seen_name[(info["stage"], info["grade"], info["vol"], info["subject"], info["unit"])][info["name"]].add(info["no"])
    for key, names in seen_name.items():
        for name, nos_set in names.items():
            if len(nos_set) > 1:
                add("dup_lesson_same_unit", path=f"{q}/{key[0]}/{key[1]}/{key[2]}/{key[3]}",
                    detail=f"同课名多份文件: {name} 序号{sorted(nos_set)}")
    for key, lst in seen_lesson_other.items():
        nos = [n for n, _ in lst]
        dup = sorted({n for n in nos if nos.count(n) > 1})
        if dup:
            files = [p for n, p in lst if n in dup]
            add("naming_dup_lesson", path=f"{q}/{key[0]}/{key[1]}/{key[2]}/{key[3]}", detail=f"课序号单元内重复: {dup} -> {files}")
    for key, lst in seen_lesson_chinese.items():
        nos = [n for n, _ in lst]
        dup = sorted({n for n in nos if nos.count(n) > 1})
        if dup:
            files = [p for n, p in lst if n in dup][:12]
            add("naming_dup_lesson", path=f"{q}/{key[0]}/{key[1]}/chinese", detail=f"语文册内课序号重复: {dup} -> {files}")

# ---------- 4) 题库解析（容错） ----------
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

RE_T = re.compile(r'\bt\s*:\s*"([a-z])"')
RE_Q = re.compile(r'\bq\s*:\s*"(..*?)"\s*,\s*o\s*:\s*\[', re.S)
RE_E = re.compile(r',\s*e\s*:\s*"(..*?)"\s*\}\s*$', re.S)
RE_STR = re.compile(r'"(?:[^"\\]|\\.)*"')

def parse_obj(txt):
    """返回 (t,q,o,a,e) 或 None"""
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
        if not o:  # 容错：旧课件未转义引号时按引号-逗号切分
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

bank = {}          # rel -> list of questions (parsed or None-marked)
for q in QTYPES:
    bank[q] = {}
    for rel, info in parsed[q].items():
        full = trees[q][rel]
        try:
            src = open(full, encoding="utf-8").read()
        except Exception as ex:
            add("file_unreadable", path=f"{q}/{rel}", detail=str(ex))
            bank[q][rel] = None
            continue
        stats["questions_total_scanned"] += 0
        objs = extract_objects(src)
        if objs is None:
            add("format_no_all", path=f"{q}/{rel}", detail="缺少 const ALL 题库数组")
            bank[q][rel] = None
            continue
        qs, bad = [], 0
        for idx, ot in enumerate(objs, 1):
            item = parse_obj(ot)
            if item is None:
                bad += 1
                add("format_bad_item", path=f"{q}/{rel}", no=idx, detail="题元组解析失败")
                continue
            item["no"] = idx
            qs.append(item)
        bank[q][rel] = qs
        if bad:
            stats["files_with_parse_errors"] += 1

# ---------- 5) 逐题格式核验 ----------
is_chinese = lambda info: info["subject"] == "chinese"
for q in QTYPES:
    for rel, qs in bank[q].items():
        if qs is None:
            continue
        info = parsed[q][rel]
        n = len(qs)
        if n < 20 or n > 40:
            add("count_out_of_range", path=f"{q}/{rel}", detail=f"题量 {n}（要求 20~40）")
        stems = {}
        for it in qs:
            no = it["no"]
            t, o, a, e = it["t"], it["o"], it["a"], it["e"]
            qq = unesc(it["q"]) or ""
            sk = hashlib.md5(qq.encode("utf-8")).hexdigest()
            if sk in stems:
                add("dup_stem_in_file", path=f"{q}/{rel}", no=no, detail=f"与第 {stems[sk]} 题题干完全重复（选项可不同）")
            else:
                stems[sk] = no
            if not qq.strip():
                add("format_empty_stem", path=f"{q}/{rel}", no=no)
            if len(o) != 4 and q == "choose":
                add("format_opts", path=f"{q}/{rel}", no=no, detail=f"选择题选项数 {len(o)}（应 4）")
            if q == "judge":
                if [x.strip() for x in o] != ["正确", "错误"]:
                    add("judge_opts", path=f"{q}/{rel}", no=no, detail=f"判断题选项异常: {o[:4]}")
                if len(a) != 1:
                    add("judge_answer", path=f"{q}/{rel}", no=no, detail=f"判断题答案数 {len(a)}")
                if not (e or "").strip():
                    add("judge_no_explain", path=f"{q}/{rel}", no=no)
            else:
                if t == "s" and len(a) != 1:
                    add("choose_answer", path=f"{q}/{rel}", no=no, detail=f"单选答案数 {len(a)}")
                if t == "m" and not (2 <= len(a) <= 4):
                    add("choose_answer", path=f"{q}/{rel}", no=no, detail=f"多选答案数 {len(a)}")
                if not (e or "").strip():
                    add("choose_no_explain", path=f"{q}/{rel}", no=no)
            if any((not x.strip()) for x in o):
                add("format_opts", path=f"{q}/{rel}", no=no, detail="存在空选项")
            if len(set(o)) != len(o):
                dups = sorted({x for x in o if o.count(x) > 1})
                add("format_opts", path=f"{q}/{rel}", no=no, detail=f"选项重复: {dups}")
            if a and (max(ord(x) for x in a) - 64) > len(o):
                add("choose_answer", path=f"{q}/{rel}", no=no, detail=f"答案 {a} 超出选项范围")
            key = hashlib.md5((qq + "|" + "|".join(o)).encode("utf-8")).hexdigest()
            stems.setdefault(key, no)
        # 文件内重复题
        seen2 = {}
        for it in qs:
            qq = unesc(it["q"]) or ""
            key = hashlib.md5((qq + "|" + "|".join(it["o"])).encode("utf-8")).hexdigest()
            if key in stems and stems[key] != it["no"] and key not in seen2:
                seen2[key] = True
                add("dup_in_file", path=f"{q}/{rel}", no=it["no"], detail=f"与第 {stems[key]} 题题干+选项完全重复")
        stats[f"questions_{q}"] += n

# ---------- 6) 跨文件重复题干（同学段同学科） ----------
glob = defaultdict(list)
for q in QTYPES:
    for rel, qs in bank[q].items():
        if qs is None:
            continue
        info = parsed[q][rel]
        for it in qs:
            qq = unesc(it["q"]) or ""
            glob[(q, info["stage"], info["grade"], info["vol"], info["subject"], hashlib.md5(qq.encode()).hexdigest())].append((f"{q}/{rel}", it["no"]))
cross_dup = {k: v for k, v in glob.items() if len(v) > 1}
stats["cross_dup_groups"] = len(cross_dup)

# ---------- 7) DOM / 模板标记 ----------
MARKERS = ["const ALL", 'class="wrap"', 'class="head"', "themebtn", "speechSynthesis"]
for q in QTYPES:
    for rel, full in parsed[q].items() if False else ((rel, trees[q][rel]) for rel in parsed[q]):
        src = None
        try:
            src = open(full, encoding="utf-8").read()
        except Exception:
            continue
        miss = [m for m in MARKERS if m not in src]
        if miss:
            add("dom_marker_missing", path=f"{q}/{rel}", detail="缺少: " + ",".join(miss))
        if not src.lstrip().lower().startswith("<!doctype html"):
            add("dom_marker_missing", path=f"{q}/{rel}", detail="缺少 DOCTYPE")
        if "charset" not in src[:400]:
            add("dom_marker_missing", path=f"{q}/{rel}", detail="缺少 charset 声明")
        has_judge_title = "判断题" in src[:src.find("</title>")] if "</title>" in src else False
        if q == "judge" and not has_judge_title:
            add("dom_marker_missing", path=f"{q}/{rel}", detail="judge 页标题缺「判断题」标识")
        if q == "choose" and has_judge_title:
            add("dom_marker_missing", path=f"{q}/{rel}", detail="choose 页标题含「判断题」字样")

# ---------- 8) 结构统计与完整性 ----------
structure = {}
for q in QTYPES:
    s = defaultdict(dict)   # stage -> grade -> vol -> {"units": {(subject,unit): n}, "review_files": int}
    for rel, info in parsed[q].items():
        st, g, v = info["stage"], info["grade"], info["vol"]
        cell = s[st].setdefault(g, {}).setdefault(v, {"units": {}, "review_files": 0})
        if info["unit"]:
            key = (info["subject"], info["unit"])
            cell["units"][key] = cell["units"].get(key, 0) + 1
        else:
            cell["review_files"] += 1
    structure[q] = {st: {g: {v: {"units": {f"{k0}/{k1}": n for (k0, k1), n in d["units"].items()},
                                  "review_files": d["review_files"]} for v, d in vv.items()} for g, vv in gv.items()}
                    for st, gv in s.items()}

# 单元缺课文/课文极少的启发式检查
for q in QTYPES:
    per_unit = defaultdict(int)
    for rel, info in parsed[q].items():
        if info["unit"]:
            per_unit[(info["stage"], info["grade"], info["vol"], info["subject"], info["unit"])] += 1
    unit_counts = defaultdict(int)
    for (st, g, v, sub, u), n in per_unit.items():
        unit_counts[(st, g, v, sub)] += 1
        if n == 1:
            add("unit_thin", path=f"{q}/{st}/{g}/{v}/{sub}/{u}", detail="该单元仅 1 篇课文")

# ---------- 9) 抽样清单（内容精审用，确定性） ----------
random.seed(20261002)
sample = []
stage_grades = {"primary": list(range(1, 7)), "middle": list(range(1, 4)), "high": list(range(1, 3))}
for stage in ["primary", "middle", "high"]:
    grades = stage_grades[stage]
    pool = defaultdict(list)   # (grade,subject) -> rel(choose)
    for rel, info in parsed["choose"].items():
        if not rel.startswith(stage + "/"):
            continue
        if info["gradeN"] in grades and info["vol"] != "review" and rel in judge_set:
            pool[(info["gradeN"], info["subject"])].append(rel)
    keys = sorted(pool)
    random.shuffle(keys)
    picked = 0
    for k in keys:
        if picked >= 8:
            break
        rel = random.choice(pool[k])
        sample.append({"stage": stage, "choose": f"choose/{rel}", "judge": f"judge/{rel}"})
        picked += 1
    # 高中额外抽 2 个高考复习专题
    if stage == "high":
        rev = [rel for rel in parsed["choose"] if rel.startswith("high/") and "/review/" in rel and rel in judge_set]
        for rel in random.sample(rev, min(2, len(rev))):
            sample.append({"stage": stage, "choose": f"choose/{rel}", "judge": f"judge/{rel}"})

# ---------- 输出 ----------
data = {
    "stats": dict(stats),
    "issues": {k: v for k, v in issues.items()},
    "issue_counts": {k: len(v) for k, v in issues.items()},
    "cross_dup_total_groups": len(cross_dup),
    "cross_dup_total_questions": sum(len(v) for v in cross_dup.values()),
    "cross_dup_by_size": {str(n): sum(1 for v in cross_dup.values() if len(v) == n)
                          for n in sorted({len(v) for v in cross_dup.values()})},
    "cross_dup_groups": [
        {"key": f"{k[0]} {k[1]} grade{k[2]} {k[3]} {k[4]}", "where": v[:6]} for k, v in list(cross_dup.items())[:200]
    ],
    "structure": structure,
    "sample": sample,
}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=1)

print("=== 统计 ===")
for k, v in sorted(stats.items()):
    print(f"  {k}: {v}")
print("=== 问题分类计数 ===")
for k, v in sorted(issues.items()):
    print(f"  {k}: {len(v)}")
print(f"跨文件重复题干组: {len(cross_dup)}")
print(f"抽样对数: {len(sample)}")
print("OK ->", OUT)
