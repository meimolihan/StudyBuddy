# -*- coding: utf-8 -*-
"""StudyBuddy 题库全面审查（只读）。
严禁修改/覆盖/删除任何被扫描目录下的 HTML 文件；本脚本只读文件、输出 JSON 报告。

用法：
    python scripts/audit_bank.py                      # 扫 content/，写 reports/audit_data.json
    python scripts/audit_bank.py <content根> <输出json>  # 自测用：指定扫描根与报告落点

审查维度：镜像配对 / 命名规范 / 题库结构与格式 / 题量 / 解析字段 / 重复题 / DOM 模板标记 / 结构统计 / 抽样清单。
检测器的正确性由 scripts/audit_selftest.py 用注入式用例保证（防假阴性）。
"""
import json, os, re, sys, hashlib, random
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(ROOT, "content")
OUT = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else os.path.join(ROOT, "reports", "audit_data.json")

STAGES = ["primary", "middle", "high"]
QTYPES = ["choose", "judge"]
UNIT_RE = re.compile(r"^(\d{2,3})-([^\\/:*?\"<>|]+)$")
FILE_RE = re.compile(r"^(\d{2,3})-([^\\/:*?\"<>|]+)\.html$")
CN_NUM = "一二三四五六七八九十"

issues = defaultdict(list)   # category -> list of {path, ...}：需要修的缺陷
todos = defaultdict(list)    # category -> list of {path, ...}：不致错、可整理项
stats = defaultdict(int)

def add(cat, **kw):
    issues[cat].append(kw)

def add_todo(cat, **kw):
    todos[cat].append(kw)

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

# 单元目录与课文序号重复检查（课序号唯一性范围 = 单元目录内，与运行时排序键一致）
for q in QTYPES:
    # 单元序号 -> 该序号出现过的单元目录名集合。同一 (学段,年级,册,学科) 下
    # 一个序号只能对应一个单元目录；出现两个不同目录名即为序号重复。
    seen_unit = defaultdict(lambda: defaultdict(set))   # (stage,grade,vol,subject) -> {unit_no: {unit_name}}
    seen_lesson_other = defaultdict(list)    # (stage,grade,vol,subject,unit) -> [(file_no, path)]
    for rel, info in parsed[q].items():
        if info["unit"]:
            key = (info["stage"], info["grade"], info["vol"], info["subject"])
            unit_no, unit_name = info["unit"].split("-", 1)
            seen_unit[key][unit_no].add(unit_name)
            lk = key + (info["unit"],)
            seen_lesson_other[lk].append((info["no"], f"{q}/{rel}"))
    for key, by_no in seen_unit.items():
        dup = sorted(no for no, names in by_no.items() if len(names) > 1)
        if dup:
            # 同序号不同名是合法的目录现状：运行时 textbook.Subject.buildUnits 已按
            # 「序号 + 目录名」复合键聚合，两者并列展示、标题与课文一致（见
            # internal/textbook/textbook.go 与 tools/unitcheck）。故只登记为待整理
            # 清单，不计入问题——否则会与 unitcheck 的结论自相矛盾。
            stats["unit_no_shared_dirs"] += 1
            for no in dup:
                add_todo("shared_unit_no_dirs",
                         path=f"{q}/{key[0]}/{key[1]}/{key[2]}",
                         detail="同序号多个目录名（运行时并列展示，建议整理编号）: "
                                "%s -> %s" % (no, sorted(by_no[no])))
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
            add("naming_dup_lesson", path=f"{q}/{key[0]}/{key[1]}/{key[2]}/{key[3]}/{key[4]}",
                detail=f"课序号单元内重复: {dup} -> {files}")

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
        objs = extract_objects(src)
        if objs is None:
            add("format_no_all", path=f"{q}/{rel}", detail="缺少 const ALL 题库数组")
            bank[q][rel] = None
            continue
        # 扫描态题量：凡是从 const ALL 里取出的题元组都计入，与解析成功的 questions_* 一起
        # 构成「扫描数 vs 解析成功数」的可核对比值（解析失败的题元组会被 format_bad_item 记录）。
        stats["questions_total_scanned"] += len(objs)
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
        # 两类重复用两套独立的键空间，避免 md5(题干) 与 md5(题干+选项) 混在同一张表里
        stem_only = {}    # md5(题干) -> 首次出现的题号
        stem_opts = {}    # md5(题干+选项) -> 首次出现的题号
        for it in qs:
            no = it["no"]
            t, o, a, e = it["t"], it["o"], it["a"], it["e"]
            qq = unesc(it["q"]) or ""
            sk = hashlib.md5(qq.encode("utf-8")).hexdigest()
            if sk in stem_only:
                add("dup_stem_in_file", path=f"{q}/{rel}", no=no, detail=f"与第 {stem_only[sk]} 题题干完全重复（选项可不同）")
            else:
                stem_only[sk] = no
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
            stem_opts.setdefault(key, no)
        # 文件内重复题：与首次出现位置比对，每组只报一次
        seen2 = set()
        for it in qs:
            qq = unesc(it["q"]) or ""
            key = hashlib.md5((qq + "|" + "|".join(it["o"])).encode("utf-8")).hexdigest()
            first = stem_opts.get(key)
            if first is not None and first != it["no"] and key not in seen2:
                seen2.add(key)
                add("dup_in_file", path=f"{q}/{rel}", no=it["no"], detail=f"与第 {first} 题题干+选项完全重复")
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
    "todos": {k: v for k, v in todos.items()},
    "todo_counts": {k: len(v) for k, v in todos.items()},
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
print("=== 问题分类计数（需要修） ===")
for k, v in sorted(issues.items()):
    print(f"  {k}: {len(v)}")
print("=== 待整理项（不致错） ===")
for k, v in sorted(todos.items()):
    print(f"  {k}: {len(v)}")
print(f"跨文件重复题干组: {len(cross_dup)}")
print(f"抽样对数: {len(sample)}")
print("OK ->", OUT)
