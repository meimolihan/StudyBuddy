# -*- coding: utf-8 -*-
"""题库内容修复 A（#164/#165/#167/#168）：
  R1~R13 P0/B 精准修复；R14 59 题选项去重；R15+R16 课内重复与超量题删除；
  R17「的含义是→指的是」全局替换；R18 引号嵌套修复。
设计要点：
  - 全部文本替换在「原始转义域（raw）」进行，不做 unesc/esc round-trip，规避 60 题反斜杠/21 题转义引号风险；
  - 未被修改的题保持原 raw 文本原样，只有修改题重建对象文本；
  - 文件为 CRLF，读写统一 newline=''；
  - 默认 dry-run，--apply 才写回；先自动备份 content/。
用法：python fix_bank_a.py [--apply]
"""
import json, os, re, sys, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_fix_targets import CONTENT, ROOT, extract_objects, parse_obj, unesc

APPLY = "--apply" in sys.argv
BACKUP = os.path.join(ROOT, "backup", "content_backup_2026-10-02")
LOG_PATH = os.path.join(ROOT, "reports", "fix_a_log.json")

CRLF = "\r\n"
log = {"rules_hit": [], "warnings": [], "files_written": 0, "total_changed": 0, "total_deleted": 0}

# ---------------- 规则表 ----------------
REL_YUEFEN = "primary/pep/choose/grade5/volume2/math/04-分数的意义和性质/16-约分.html"
REL_DAOSHU_C = "primary/pep/choose/grade6/volume1/math/03-分数除法/08-倒数的认识.html"
REL_DAOSHU_J = "primary/pep/judge/grade6/volume1/math/03-分数除法/08-倒数的认识.html"
REL_SHENJING_C = "high/pep/choose/grade2/volume1/biology/02-第二章 神经调节/04-神经系统的分级调节.html"
REL_SHENJING_J = "high/pep/judge/grade2/volume1/biology/02-第二章 神经调节/04-神经系统的分级调节.html"
REL_SHIYUE_C = "middle/pep/choose/grade3/volume2/history/03-第一次世界大战和战后初期的世界/10-列宁与十月革命.html"
REL_SHIYUE_J = "middle/pep/judge/grade3/volume2/history/03-第一次世界大战和战后初期的世界/10-列宁与十月革命.html"
REL_GUANGHE_C = "middle/pep/choose/grade1/volume1/biology/03-生物圈中的绿色植物/17-绿色植物是生物圈中有机物的制造者.html"
REL_GUANGHE_J = "middle/pep/judge/grade1/volume1/biology/03-生物圈中的绿色植物/17-绿色植物是生物圈中有机物的制造者.html"
REL_SHUJU = "primary/pep/choose/grade3/volume2/math/05-数据的收集与整理/15-数据的收集与整理.html"
REL_SAN_DAN = "primary/pep/choose/grade4/volume1/english/03-My friends 我的朋友/02-句型.html"
REL_UNIT4_C = "high/pep/choose/grade2/volume2/english/04-Unit 4 Journey Across a Vast Land/04-Unit 4 Journey Across a Vast Land.html"
REL_UNIT4_J = "high/pep/judge/grade2/volume2/english/04-Unit 4 Journey Across a Vast Land/04-Unit 4 Journey Across a Vast Land.html"
REL_NIAN_C = "high/pep/choose/grade1/volume1/chinese/03-生命的诗意/09-念奴娇·赤壁怀古永遇乐·京口北固亭怀古声声慢.html"
REL_WENYAN_C = "high/pep/choose/grade3/review/chinese/03-文言文阅读.html"
REL_WENYAN_J = "high/pep/judge/grade3/review/chinese/03-文言文阅读.html"
REL_DAOfa_C = "middle/pep/choose/grade3/volume1/morallaw/03-文明与家园/06-建设美丽中国.html"
REL_DAOfa_J = "middle/pep/judge/grade3/volume1/morallaw/03-文明与家园/06-建设美丽中国.html"
REL_SHISHU_J = "middle/pep/judge/grade1/volume2/math/02-实数/03-实数.html"

# (rel, no_or_None, kind, payload)
RULES = [
    # R1 约分#25：C/D 改为错误说法，保留唯一正确 A
    (REL_YUEFEN, 25, "subst", [("通常要约成最简分数", "约分后分数单位不变"),
                               ("约分不改变分数大小", "约分改变了分数的大小")]),
    # R2 倒数#23：A/D 改为错误说法，保留唯一正确 B
    (REL_DAOSHU_C, 23, "subst", [("求倒数就是交换分子分母的位置", "假分数的倒数都大于 1"),
                                 ("1 的倒数还是 1", "0 的倒数还是 0")]),
    # R3 神经调节：指代不明修复（两文件全部题）
    (REL_SHENJING_C, None, "subst", [("与其大小无关", "与躯体各部分的实际大小无关")]),
    (REL_SHENJING_J, None, "subst", [("与其大小无关", "与躯体各部分的实际大小无关")]),
    # R4 十月革命：巩固时期→建立后及时
    (REL_SHIYUE_C, None, "subst", [("苏维埃政权巩固时期颁布的法令", "苏维埃政权建立后及时颁布的法令")]),
    (REL_SHIYUE_J, None, "subst", [("苏维埃政权巩固时期颁布的法令", "苏维埃政权建立后及时颁布的法令")]),
    # R5 光合作用：条件与场所分开表述
    (REL_GUANGHE_C, 8, "set_full", {
        "q": "“光合作用的条件与场所”指的是（　）。",
        "o": ["绿色植物通过光能，把二氧化碳和水转变成储存能量的有机物，并释放氧气",
              "有机物（如淀粉）和氧气", "光是条件，叶绿体是场所", "检验淀粉是否存在的方法"],
        "a": ["C"]}),
    (REL_GUANGHE_J, 15, "set_qe", (
        "光是光合作用的条件，叶绿体是光合作用的场所。",
        "解析：本句说法正确。光是光合作用的条件，叶绿体是光合作用的场所，二者缺一不可。")),
    # R6 数据收集#18：改为单空可作答
    (REL_SHUJU, 18, "set_q", ("这个问题要用到", "要比较喜欢不同颜色的人数的多少，需要对收集的数据进行（　）。")),
    # R7 英语三单#39：换为四上 Unit3 has 句型
    (REL_SAN_DAN, 39, "set_full", {
        "q": "He（　）short hair.（他留着短发。）",
        "o": ["has", "have", "is", "are"], "a": ["A"]}),
    # R8 Unit4：形容词短语例句→过去分词真实例句
    (REL_UNIT4_C, None, "subst", [("Tired and hungry, he went straight to bed",
                                   "Born in a poor family, he knew the value of money")]),
    (REL_UNIT4_J, None, "subst", [("Tired and hungry, he went straight to bed",
                                   "Born in a poor family, he knew the value of money")]),
    # R9 念奴娇 #4/#24：替换为课文范围内题目
    (REL_NIAN_C, 4, "set_full", {
        "q": "“廉颇老矣，尚能饭否？”出自（　）。",
        "o": ["《永遇乐·京口北固亭怀古》", "《念奴娇·赤壁怀古》", "《声声慢》", "《虞美人》"],
        "a": ["A"]}),
    (REL_NIAN_C, 24, "set_full", {
        "q": "下列词句出自《声声慢》的是（　）。",
        "o": ["寻寻觅觅，冷冷清清，凄凄惨惨戚戚", "大江东去，浪淘尽，千古风流人物",
              "千古江山，英雄无觅，孙仲谋处", "人生如梦，一尊还酹江月"],
        "a": ["A"]}),
    # R10 文言文：逐字对应→字字落实
    (REL_WENYAN_C, None, "subst", [("逐字对应", "字字落实")]),
    (REL_WENYAN_J, None, "subst", [("逐字对应", "字字落实")]),
    # R11 道法：国策与理念混淆修复
    (REL_DAOfa_C, 4, "set_q", ("保护环境基本国策", "“绿水青山就是金山银山”理念强调的是（　）。")),
    (REL_DAOfa_J, 7, "set_q", ("保护环境基本国策", "“绿水青山就是金山银山”理念强调坚持生态优先、绿色发展。")),
    # R12 实数 judge#23：叠字病句
    (REL_SHISHU_J, 23, "set_qe", (
        "无限循环小数是有理数，可化为分数，如 0.3̇ = 1/3。",
        "解析：本句说法正确。无限循环小数都能化为分数，所以是有理数，如 0.3̇ = 1/3。")),
    # R13 倒数 judge#33：解析病句修复 + 题干排版
    (REL_DAOSHU_J, 33, "set_qe", (
        "0 没有倒数。",
        "解析：本句说法正确。因为 0 乘任何数都不等于 1，所以 0 没有倒数；1 的倒数是 1。")),
]

# R14 语文 4 题手工选项
CN_OPT_FIX = {
    ("primary/pep/choose/grade4/volume1/chinese/04-神话故事/13-精卫填海.html", 16):
        (["yuē", "yuè", "rì", "rì"], ["yuē", "yuè", "rì", "gān"]),
    ("primary/pep/choose/grade4/volume1/chinese/06-童年回忆/20-陀螺.html", 8):
        (["dǐng", "dīng", "dìng", "dīng"], ["dǐng", "dīng", "dìng", "tìng"]),
    ("primary/pep/choose/grade4/volume1/chinese/07-家国情怀/22-为中华之崛起而读书.html", 11):
        (["chū", "chù", "chǔ", "chù"], ["chū", "chù", "chǔ", "cù"]),
    ("primary/pep/choose/grade4/volume1/chinese/08-历史传说故事/25-王戎不取道旁李.html", 19):
        (["品尝", "品尝", "品长", "品常"], ["品尝", "品偿", "品长", "品常"]),
}
POOL = list("mkwypbhfgjqsvncld")

def dedup_opts(o):
    o = list(o)
    for _ in range(8):
        seen = {}
        dup_i = -1
        for i, v in enumerate(o):
            if v in seen:
                dup_i = i
                break
            seen[v] = i
        if dup_i < 0:
            return o
        v = o[dup_i]
        pool = [c.upper() if v.isupper() else c for c in POOL]
        for c in pool:
            if c not in o:
                o[dup_i] = c
                break
    return o

# ---------------- 加载审计数据 ----------------
audit = json.load(open(os.path.join(ROOT, "reports", "fix_targets.json"), encoding="utf-8"))

# R14 英语 dedup 题号（按文件）
eng_dedup = {}
for rec in audit["format_opts"]:
    eng_dedup.setdefault(rec["rel"], set()).add(rec["no"])

# R15+R16 删除集
DEL = {}   # rel -> set(no)
for rec in audit["dup_stem"]:
    DEL.setdefault(rec["rel"], set()).add(rec["no"])
for item in audit["out_of_range"]:
    n = item["count"] - 40
    plan = item["delete_plan"]
    assert len(plan) == n, f"delete_plan 长度异常 {item['rel']}: {len(plan)} != {n}"
    DEL.setdefault(item["rel"], set()).update(plan)

# 按文件聚合规则
rules_by_file = {}
for rel, no, kind, payload in RULES:
    rules_by_file.setdefault(rel, []).append((no, kind, payload))
for (rel, no), (old_o, new_o) in CN_OPT_FIX.items():
    rules_by_file.setdefault(rel, []).append((no, "set_opts_cmp", (old_o, new_o)))
for rel, nos in eng_dedup.items():
    rules_by_file.setdefault(rel, []).append((sorted(nos), "dedup_opts", None))
for rel, nos in DEL.items():
    rules_by_file.setdefault(rel, []).append((sorted(nos), "del", None))

# ---------------- 序列化 ----------------
def build_obj(t, q_raw, o_raws, a_list, e_raw=None):
    s = '{t:"%s",q:"%s",o:[%s],a:[%s]' % (
        t, q_raw, ", ".join('"%s"' % v for v in o_raws), ", ".join('"%s"' % v for v in a_list))
    if e_raw is not None:
        s += ',e:"%s"' % e_raw
    return s + "}"

def serialize(objs_raw):
    return " " + ("," + CRLF + " ").join(objs_raw)

# ---------------- 主循环 ----------------
if APPLY and not os.path.isdir(BACKUP):
    os.makedirs(os.path.dirname(BACKUP), exist_ok=True)
    shutil.copytree(CONTENT, BACKUP)
    print(f"已备份 content/ -> {BACKUP}")

# 收集全部 choose/judge 文件（R17/R18 需全量扫描）
all_files = []
for qtype in ("choose", "judge"):
    for stage in ("primary", "middle", "high"):
        base = os.path.join(CONTENT, stage, "pep", qtype)
        for dp, _, fns in os.walk(base):
            for fn in fns:
                if fn.endswith(".html"):
                    all_files.append(os.path.join(dp, fn))
all_files.sort()
print(f"扫描文件数: {len(all_files)} ｜ APPLY={APPLY}")

warn = log["warnings"]
for full in all_files:
    rel = os.path.relpath(full, CONTENT).replace("\\", "/")
    src = open(full, encoding="utf-8", newline="").read()
    i = src.find("const ALL")
    if i < 0:
        warn.append([rel, "no const ALL"])
        continue
    lb = src.find("[", i)
    # 引号感知找数组结束
    depth = in_str = esc = 0
    end = -1
    for k in range(lb, len(src)):
        c = src[k]
        if in_str:
            if esc:
                esc = 0
            elif c == "\\":
                esc = 1
            elif c == '"':
                in_str = 0
            continue
        if c == '"':
            in_str = 1
        elif c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                end = k
                break
    if end < 0:
        warn.append([rel, "no array end"])
        continue
    body = src[lb + 1:end]
    raws = [p.strip() for p in body.split("," + CRLF + " ")] if "," + CRLF + " " in body else [body.strip()]
    # 更稳的切分：直接按 extract_objects
    objs = extract_objects(src)
    if objs is None or len(objs) == 0:
        warn.append([rel, "no objects"])
        continue
    raws = [o.strip() for o in objs]
    parsed = [parse_obj(r) for r in raws]
    if any(p is None for p in parsed):
        warn.append([rel, "parse fail"])
        continue
    frules = rules_by_file.get(rel, [])
    changed = 0
    deleted = []
    detail = []

    # --- R1~R16 题级规则 ---
    for no, kind, payload in frules:
        if kind == "del":
            for n in no:
                if 1 <= n <= len(raws) and n not in deleted:
                    deleted.append(n)
                    detail.append(["del", n, ""])
            continue
        if kind == "dedup_opts":
            for n in no:
                if n > len(raws) or parsed[n - 1] is None:
                    warn.append([rel, f"dedup 题号异常 {n}"])
                    continue
                p = parsed[n - 1]
                new_o = dedup_opts(p["o"])
                if new_o != p["o"]:
                    raws[n - 1] = build_obj(p["t"], p["q"], new_o, p["a"], p["e"])
                    parsed[n - 1] = parse_obj(raws[n - 1])
                    changed += 1
                    detail.append(["dedup", n, ",".join(new_o)])
            continue
        if no is not None and no > len(raws):
            warn.append([rel, f"题号越界 {no}"])
            continue
        if kind == "subst":
            if no is None:
                # 文件级：扫描全部题，凡含锚点即替换；全文件零命中才告警
                hits = 0
                for idx in range(len(raws)):
                    p = parsed[idx]
                    if not p:
                        continue
                    for old, new in payload:
                        if old in p["q"] or any(old in o for o in p["o"]) or (p["e"] and old in p["e"]):
                            nq = raws[idx].replace(old, new)
                            p2 = parse_obj(nq)
                            if p2 is None:
                                warn.append([rel, f"subst 后解析失败 #{idx+1}"])
                                continue
                            raws[idx] = nq
                            parsed[idx] = p2
                            hits += 1
                            changed += 1
                            detail.append(["subst", idx + 1, f"{old[:20]}->"])
                if hits == 0:
                    warn.append([rel, f"文件级 subst 零命中: {[o[0][:24] for o in payload]}"])
            else:
                p = parsed[no - 1]
                for old, new in payload:
                    if old in p["q"] or any(old in o for o in p["o"]) or (p["e"] and old in p["e"]):
                        nq = raws[no - 1].replace(old, new)
                        p2 = parse_obj(nq)
                        if p2 is None:
                            warn.append([rel, f"subst 后解析失败 #{no}"])
                            continue
                        raws[no - 1] = nq
                        parsed[no - 1] = p2
                        changed += 1
                        detail.append(["subst", no, f"{old[:20]}->"])
                    else:
                        warn.append([rel, f"subst 锚点未命中 #{no}: {old[:24]}"])
            continue
        if no is None:
            warn.append([rel, f"{kind} 缺少题号"])
            continue
        p = parsed[no - 1]
        if kind == "set_q":
            anchor, new_q = payload
            if anchor and anchor not in p["q"]:
                warn.append([rel, f"set_q 锚点未命中 #{no}: {anchor[:24]}"])
                continue
            raws[no - 1] = build_obj(p["t"], new_q, p["o"], p["a"], p["e"])
            parsed[no - 1] = parse_obj(raws[no - 1])
            changed += 1
            detail.append(["set_q", no, new_q[:30]])
        elif kind == "set_qe":
            new_q, new_e = payload
            raws[no - 1] = build_obj(p["t"], new_q, p["o"], p["a"], new_e)
            parsed[no - 1] = parse_obj(raws[no - 1])
            changed += 1
            detail.append(["set_qe", no, new_q[:30]])
        elif kind == "set_opts_cmp":
            old_o, new_o = payload
            if p["o"] != old_o:
                warn.append([rel, f"set_opts 旧选项不匹配 #{no}: {p['o']}"])
                continue
            raws[no - 1] = build_obj(p["t"], p["q"], new_o, p["a"], p["e"])
            parsed[no - 1] = parse_obj(raws[no - 1])
            changed += 1
            detail.append(["set_opts", no, ",".join(new_o)])
        elif kind == "set_full":
            raws[no - 1] = build_obj(p["t"], payload["q"], payload["o"], payload["a"], p["e"])
            parsed[no - 1] = parse_obj(raws[no - 1])
            changed += 1
            detail.append(["set_full", no, payload["q"][:30]])

    # --- R17 含义是→指的是（题干 raw 域） ---
    for idx in range(len(raws)):
        p = parsed[idx]
        if not p or not p["q"]:
            continue
        if "的含义是" in p["q"]:
            nq = p["q"].replace("的含义是（　）", "指的是（　）").replace("的含义是", "指的是")
            raws[idx] = build_obj(p["t"], nq, p["o"], p["a"], p["e"])
            p2 = parse_obj(raws[idx])
            if p2:
                parsed[idx] = p2
                changed += 1
                if idx + 1 not in deleted:
                    detail.append(["hanyishi", idx + 1, ""])

    # --- R18 引号嵌套修复（题干 raw 域） ---
    for idx in range(len(raws)):
        p = parsed[idx]
        if not p or not p["q"] or not p["q"].startswith("““"):
            continue
        q = p["q"]
        pos = q.find("指的是")
        if pos > 2 and q[pos - 1] == "”":
            if q[pos - 2:pos] == "””":
                nq = q[1:pos - 2] + q[pos:]
            else:
                nq = q[1:pos - 1] + q[pos:]
            raws[idx] = build_obj(p["t"], nq, p["o"], p["a"], p["e"])
            p2 = parse_obj(raws[idx])
            if p2:
                parsed[idx] = p2
                changed += 1
                if idx + 1 not in deleted:
                    detail.append(["quote_fix", idx + 1, ""])

    # --- 删除（原题号倒序删） ---
    if deleted:
        keep = [(r, pp) for k, (r, pp) in enumerate(zip(raws, parsed)) if (k + 1) not in deleted]
        raws = [r for r, _ in keep]
        parsed = [pp for _, pp in keep]
        changed += len(deleted)

    if changed:
        log["files_written"] += 1
        log["total_changed"] += changed
        log["total_deleted"] += len(deleted)
        log["rules_hit"].append({"rel": rel, "changed": changed, "deleted": sorted(deleted), "detail": detail[:400]})
        if APPLY:
            new_body = serialize(raws)
            new_src = src[:lb + 1] + new_body + src[end:]
            for attempt in range(5):
                try:
                    open(full, "w", encoding="utf-8", newline="").write(new_src)
                    break
                except PermissionError:
                    if attempt == 4:
                        raise
                    import time
                    time.sleep(0.6 * (attempt + 1))

json.dump(log, open(LOG_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"命中文件: {log['files_written']} ｜ 变更题次: {log['total_changed']} ｜ 删除题数: {log['total_deleted']} ｜ 警告: {len(warn)}")
for w in warn[:30]:
    print("  WARN:", w)
print("log ->", LOG_PATH)
