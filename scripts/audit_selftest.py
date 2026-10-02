# -*- coding: utf-8 -*-
"""audit_bank.py 检测器的注入式自测（确定性、纯离线、不触碰 content/）。

要解决的是「假阴性」：审计报告说「问题 0」时，必须有证据说明检测器在真有问题的
输入上确实会报出来，而不是因为写错了键空间、把唯一性范围搞错、或统计恒为 0 而
静默放过。本脚本对每条检测器做「注入 → 必须报出 / 不注入 → 必须不报」双向验证。

用法：
    python scripts/audit_selftest.py        # 全部用例
    python scripts/audit_selftest.py -v     # 附每条用例明细

工作方式：在系统临时目录里造一套最小课件树（不复制、不修改 content/），
以子进程方式调用 audit_bank.py，读取其 JSON 报告，断言各类问题按预期出现。
退出码 0 = 全部通过；1 = 有用例失败。
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIT = os.path.join(ROOT, "scripts", "audit_bank.py")
PY = sys.executable

VERBOSE = "-v" in sys.argv

CHOOSE_HEAD = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>.wrap{{color:#111}} .head{{color:#222}}</style>
</head>
<body>
<div class="wrap"><div class="head">自测</div>
<button id="themebtn" onclick="applyTheme('auto')">主题</button>
<button onclick="speechSynthesis.cancel()">朗读</button>
<script>
"""

CHOOSE_TAIL = """function applyTheme(){}
</script>
</body>
</html>
"""


def q_single(i, stem=None):
    stem = stem or f"第{i}道题：{i} 加 1 等于多少（　）。"
    return '{t:"s",q:"%s",o:["%d", "%d", "%d", "%d"],a:["A"],e:"解析：选 A。"}' % (
        stem, i, i + 1, i + 2, i + 3)


def q_multi(i, stem=None):
    stem = stem or f"第{i}道多选：下列属于整数的有（　）。"
    return '{t:"m",q:"%s",o:["1", "2", "3", "4"],a:["A","B"],e:"解析：选 AB。"}' % stem


def q_judge(i, stem=None, opts='["正确", "错误"]', ans='["A"]', has_exp=True):
    stem = stem or f"第{i}道判断：{i} 是偶数。"
    e = 'e:"解析：本句说法正确。"' if has_exp else ""
    return '{t:"j",q:"%s",o:%s,a:%s,%s}' % (stem, opts, ans, e)


def page(title, objs, extra_js=""):
    body = ",\n ".join(objs)
    return (CHOOSE_HEAD.format(title=title)
            + "const ALL = [\n " + body + "\n];\n"
            + extra_js
            + CHOOSE_TAIL)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def unit_dir(root, stage, grade, vol, subject, unit):
    return os.path.join(root, stage, "pep", "choose", grade, vol, subject, unit)


def run_audit(root):
    out = os.path.join(root, "_report.json")
    p = subprocess.run([PY, AUDIT, root, out], capture_output=True, text=True, encoding="utf-8")
    if not os.path.exists(out):
        raise AssertionError("审计未产出报告：\n" + p.stdout + p.stderr)
    with open(out, encoding="utf-8") as f:
        return json.load(f)


def counts(rep, cat):
    return rep.get("issue_counts", {}).get(cat, 0)


def base_tree(root, choose_objs, judge_objs, unit="01-第一单元", lesson="01-第一课"):
    """造一对 choose/judge 镜像课件（题量各 20，落在 20~40 合格区间）。"""
    c = choose_objs if choose_objs is not None else [q_single(i) for i in range(1, 21)]
    j = judge_objs if judge_objs is not None else [q_judge(i) for i in range(1, 21)]
    d = unit_dir(root, "primary", "grade4", "volume1", "math", unit)
    write(os.path.join(d, lesson + ".html"),
          page("四年级数学上册 自测 · 第一单元 · 第1课", c))
    write(os.path.join(root, "primary", "pep", "judge", "grade4", "volume1", "math", unit,
                       lesson + ".html"),
          page("四年级数学上册 自测 · 第一单元 · 第1课 · 判断题", j))
    return d

# ---------------------------------------------------------------- 用例
# 每个用例返回 None（仅造课件）或一个断言函数（造完课件后拿报告校验）。

CASES = []


def case(name):
    def deco(fn):
        CASES.append((name, fn))
        return fn
    return deco


@case("基线：干净题库零问题（防假阳性）")
def t_clean(root):
    base_tree(root, None, None)

    def check(rep):
        bad = {k: v for k, v in rep["issue_counts"].items() if k != "unit_thin"}
        assert not bad, "干净输入却报了问题：%s" % bad
        assert rep["stats"]["mirror_unpaired"] == 0, rep["stats"]
        assert rep["stats"]["questions_total_scanned"] == 40, rep["stats"]
    return check


@case("扫描题量统计非零且等于解析成功数（防统计恒 0）")
def t_scanned_nonzero(root):
    base_tree(root, None, None)

    def check(rep):
        s = rep["stats"]
        assert s["questions_total_scanned"] == 40, s
        assert s["questions_choose"] + s["questions_judge"] == s["questions_total_scanned"], s
    return check


@case("文件内完全重复题（题干+选项）必须报出")
def t_dup_in_file(root):
    objs = [q_single(i) for i in range(1, 21)]
    objs.append(q_single(1))
    base_tree(root, objs, None)

    def check(rep):
        assert counts(rep, "dup_in_file") >= 1, \
            "注入 1 道完全重复题却没报：%s" % rep["issue_counts"]
    return check


@case("文件内同题干不同选项必须报出")
def t_dup_stem(root):
    objs = [q_single(i) for i in range(1, 21)]
    objs.append('{t:"s",q:"第1道题：1 加 1 等于多少（　）。",o:["9","8","7","6"],a:["B"],e:"解析：选 B。"}')
    base_tree(root, objs, None)

    def check(rep):
        assert counts(rep, "dup_stem_in_file") >= 1, \
            "注入同题干异选项却没报：%s" % rep["issue_counts"]
    return check


@case("无重复的题库不应被误判（防假阳性）")
def t_no_false_dup(root):
    base_tree(root, None, None)

    def check(rep):
        assert counts(rep, "dup_in_file") == 0, rep["issues"].get("dup_in_file")
        assert counts(rep, "dup_stem_in_file") == 0, rep["issues"].get("dup_stem_in_file")
        assert rep["cross_dup_total_groups"] == 0, rep["cross_dup_total_groups"]
    return check


@case("判断题选项/答案/解析异常必须报出")
def t_judge_fields(root):
    j = [q_judge(i) for i in range(1, 19)]
    j.append(q_judge(19, opts='["对", "错"]'))
    j.append(q_judge(20, ans='["A","B"]'))
    j.append(q_judge(20, has_exp=False))
    base_tree(root, None, j)

    def check(rep):
        assert counts(rep, "judge_opts") >= 1, rep["issue_counts"]
        assert counts(rep, "judge_answer") >= 1, rep["issue_counts"]
        assert counts(rep, "judge_no_explain") >= 1, rep["issue_counts"]
    return check


@case("选择题选项数/答案越界/缺解析必须报出")
def t_choose_fields(root):
    c = [q_single(i) for i in range(1, 19)]
    c.append('{t:"s",q:"第19题：只有三个选项的题（　）。",o:["A","B","C"],a:["A"],e:"解析：选 A。"}')
    c.append('{t:"s",q:"第20题：答案越界的题（　）。",o:["A","B","C","D"],a:["E"],e:"解析：越界。"}')
    c.append('{t:"s",q:"第21题：没有解析的题（　）。",o:["A","B","C","D"],a:["A"]}')
    base_tree(root, c, None)

    def check(rep):
        assert counts(rep, "format_opts") >= 1, rep["issue_counts"]
        assert counts(rep, "choose_answer") >= 1, rep["issue_counts"]
        assert counts(rep, "choose_no_explain") >= 1, rep["issue_counts"]
    return check


@case("选项重复/空选项必须报出")
def t_dup_opts(root):
    c = [q_single(i) for i in range(1, 20)]
    c.append('{t:"s",q:"第20题：选项里有空项（　）。",o:["A","","C","D"],a:["A"],e:"解析：选 A。"}')
    base_tree(root, c, None)

    def check(rep):
        assert counts(rep, "format_opts") >= 1, rep["issue_counts"]
    return check


@case("多选题答案数越界必须报出")
def t_multi_answer(root):
    c = [q_single(i) for i in range(1, 20)]
    c.append('{t:"m",q:"第20题：多选只给一个答案（　）。",o:["1","2","3","4"],a:["A"],e:"解析：选 A。"}')
    base_tree(root, c, None)

    def check(rep):
        assert counts(rep, "choose_answer") >= 1, rep["issue_counts"]
    return check


@case("空题干必须报出")
def t_empty_stem(root):
    c = [q_single(i) for i in range(1, 20)]
    c.append('{t:"s",q:"",o:["A","B","C","D"],a:["A"],e:"解析：选 A。"}')
    base_tree(root, c, None)

    def check(rep):
        assert counts(rep, "format_empty_stem") >= 1, rep["issue_counts"]
    return check


@case("题量越界（<20）必须报出")
def t_count_low(root):
    base_tree(root, [q_single(i) for i in range(1, 12)], None)

    def check(rep):
        assert counts(rep, "count_out_of_range") >= 1, rep["issue_counts"]
    return check


@case("题量越界（>40）必须报出")
def t_count_high(root):
    base_tree(root, [q_single(i) for i in range(1, 46)], None)

    def check(rep):
        assert counts(rep, "count_out_of_range") >= 1, rep["issue_counts"]
    return check


@case("缺少 const ALL 数组必须报出")
def t_no_all(root):
    d = base_tree(root, None, None)
    p = os.path.join(d, "01-第一课.html")
    with open(p, encoding="utf-8") as f:
        s = f.read()
    with open(p, "w", encoding="utf-8") as f:
        f.write(s.replace("const ALL = [", "const OTHER = ["))

    def check(rep):
        assert counts(rep, "format_no_all") >= 1, rep["issue_counts"]
    return check


@case("choose/judge 未配对必须报出")
def t_mirror(root):
    base_tree(root, None, None)
    os.remove(os.path.join(root, "primary", "pep", "judge", "grade4", "volume1", "math",
                           "01-第一单元", "01-第一课.html"))

    def check(rep):
        assert counts(rep, "mirror_missing_judge") >= 1, rep["issue_counts"]
        assert rep["stats"]["mirror_unpaired"] == 1, rep["stats"]
    return check


@case("路径命名不合规必须报出")
def t_bad_naming(root):
    base_tree(root, None, None)
    bad = unit_dir(root, "primary", "grade4", "volume1", "math", "badunit")
    write(os.path.join(bad, "第一课.html"), page("自测", [q_single(i) for i in range(1, 21)]))

    def check(rep):
        assert counts(rep, "naming_bad") >= 1, rep["issue_counts"]
    return check


@case("单元内课序号重复必须报出（唯一性范围=单元目录内）")
def t_dup_lesson_no(root):
    d = unit_dir(root, "primary", "grade4", "volume1", "math", "01-第一单元")
    for lesson in ("01-甲课", "01-乙课"):
        write(os.path.join(d, lesson + ".html"), page("自测", [q_single(i) for i in range(1, 21)]))
        write(os.path.join(root, "primary", "pep", "judge", "grade4", "volume1", "math",
                           "01-第一单元", lesson + ".html"),
              page("自测 判断题", [q_judge(i) for i in range(1, 21)]))

    def check(rep):
        assert counts(rep, "naming_dup_lesson") >= 1, \
            "同单元内两个 01- 课号却没报：%s" % rep["issue_counts"]
    return check


@case("跨单元课序号相同不算问题（防假阳性：各单元都从 01 起编）")
def t_lesson_no_cross_unit_ok(root):
    for unit, lesson in [("01-第一单元", "01-甲课"), ("02-第二单元", "01-乙课"),
                         ("03-第三单元", "01-丙课")]:
        d = unit_dir(root, "primary", "grade4", "volume1", "chinese", unit)
        write(os.path.join(d, lesson + ".html"),
              page("自测 · %s · %s" % (unit, lesson), [q_single(i) for i in range(1, 21)]))
        write(os.path.join(root, "primary", "pep", "judge", "grade4", "volume1", "chinese",
                           unit, lesson + ".html"),
              page("自测 判断题 · %s" % unit, [q_judge(i) for i in range(1, 21)]))

    def check(rep):
        assert counts(rep, "naming_dup_lesson") == 0, \
            "跨单元的 01- 课号被误判为重复：%s" % rep["issues"].get("naming_dup_lesson")
        assert counts(rep, "naming_dup_unit") == 0, rep["issue_counts"]
    return check


@case("同序号不同单元目录：登记待整理清单但不判为缺陷")
def t_dup_unit_no(root):
    for unit in ("01-甲单元", "01-乙单元"):
        d = unit_dir(root, "primary", "grade4", "volume1", "math", unit)
        write(os.path.join(d, "01-甲课.html"), page("自测", [q_single(i) for i in range(1, 21)]))
        write(os.path.join(root, "primary", "pep", "judge", "grade4", "volume1", "math",
                           unit, "01-甲课.html"),
              page("自测 判断题", [q_judge(i) for i in range(1, 21)]))

    def check(rep):
        # 同序号不同名不是缺陷（运行时按复合键并列展示），只登记待整理清单
        assert counts(rep, "naming_dup_unit") == 0, \
            "同序号不同名不应再判为命名缺陷：%s" % rep["issues"].get("naming_dup_unit")
        assert rep.get("todo_counts", {}).get("shared_unit_no_dirs", 0) >= 1, \
            "同序号不同名应登记到待整理清单：%s" % rep.get("todo_counts")
        assert rep["stats"]["unit_no_shared_dirs"] >= 1, rep["stats"]
    return check


@case("同单元内同课名多份文件必须报出")
def t_same_name(root):
    d = unit_dir(root, "primary", "grade4", "volume1", "math", "01-第一单元")
    for lesson in ("01-甲课", "02-甲课"):
        write(os.path.join(d, lesson + ".html"), page("自测", [q_single(i) for i in range(1, 21)]))
        write(os.path.join(root, "primary", "pep", "judge", "grade4", "volume1", "math",
                           "01-第一单元", lesson + ".html"),
              page("自测 判断题", [q_judge(i) for i in range(1, 21)]))

    def check(rep):
        assert counts(rep, "dup_lesson_same_unit") >= 1, rep["issue_counts"]
    return check


@case("跨文件重复题干必须报出并计入统计")
def t_cross_dup(root):
    shared = "这道跨文件重复的题干：下列哪个是质数（　）。"
    for unit in ("01-第一单元", "02-第二单元"):
        objs = [q_single(i) for i in range(1, 20)] + [q_single(20, stem=shared)]
        d = unit_dir(root, "primary", "grade4", "volume1", "math", unit)
        write(os.path.join(d, "01-甲课.html"), page("自测", objs))
        write(os.path.join(root, "primary", "pep", "judge", "grade4", "volume1", "math",
                           unit, "01-甲课.html"),
              page("自测 判断题", [q_judge(i) for i in range(1, 21)]))

    def check(rep):
        assert rep["cross_dup_total_groups"] >= 1, \
            "跨文件同题干未计入重复组：%s" % rep["cross_dup_total_groups"]
    return check


@case("DOM 模板标记缺失必须报出")
def t_dom_marker(root):
    d = base_tree(root, None, None)
    p = os.path.join(d, "01-第一课.html")
    with open(p, encoding="utf-8") as f:
        s = f.read()
    s = s.replace('class="wrap"', 'class="wrapper"').replace("speechSynthesis", "speech")
    with open(p, "w", encoding="utf-8") as f:
        f.write(s)

    def check(rep):
        assert counts(rep, "dom_marker_missing") >= 1, rep["issue_counts"]
    return check


@case("choose 页标题混入「判断题」必须报出")
def t_choose_title(root):
    d = base_tree(root, None, None)
    p = os.path.join(d, "01-第一课.html")
    with open(p, encoding="utf-8") as f:
        s = f.read()
    with open(p, "w", encoding="utf-8") as f:
        f.write(s.replace("</title>", " · 判断题</title>"))

    def check(rep):
        assert counts(rep, "dom_marker_missing") >= 1, rep["issue_counts"]
    return check


@case("judge 页标题缺「判断题」标识必须报出")
def t_judge_title(root):
    base_tree(root, None, None)
    p = os.path.join(root, "primary", "pep", "judge", "grade4", "volume1", "math",
                     "01-第一单元", "01-第一课.html")
    with open(p, encoding="utf-8") as f:
        s = f.read()
    with open(p, "w", encoding="utf-8") as f:
        f.write(s.replace(" · 判断题</title>", "</title>"))

    def check(rep):
        assert counts(rep, "dom_marker_missing") >= 1, rep["issue_counts"]
    return check


@case("题元组解析失败必须报出，且不计入解析成功数")
def t_bad_item(root):
    # 19 道合法 + 1 道缺 t/q 字段的坏题元组；judge 侧 20 道合法
    c = [q_single(i) for i in range(1, 20)] + ['{foo:"没有 t 和 q 字段"}']
    base_tree(root, c, None)

    def check(rep):
        assert counts(rep, "format_bad_item") >= 1, rep["issue_counts"]
        assert rep["stats"]["files_with_parse_errors"] == 1, rep["stats"]
        assert rep["stats"]["questions_total_scanned"] == 40, \
            "扫描数应含坏题元组（20 choose + 20 judge）：%s" % rep["stats"]
        assert rep["stats"]["questions_choose"] == 19, \
            "解析失败题元组不应计入 questions_choose：%s" % rep["stats"]
    return check


def main():
    if not os.path.exists(AUDIT):
        print("找不到 audit_bank.py：%s" % AUDIT)
        return 1
    failed = []
    for name, fn in CASES:
        root = tempfile.mkdtemp(prefix="sb_audit_selftest_")
        try:
            # 用例先在 root 里造课件，再跑审计读报告——顺序不能反，
            # 否则会在空目录上空跑，得到「全部零问题」的假通过。
            result = fn(root)
            rep = run_audit(root)
            if result is not None:
                result(rep)
            print("  ✓ %s" % name)
        except AssertionError as e:
            failed.append(name)
            print("  ✗ %s\n      %s" % (name, e))
        except Exception as e:  # noqa: BLE001
            failed.append(name)
            print("  ✗ %s\n      用例执行异常：%r" % (name, e))
        finally:
            shutil.rmtree(root, ignore_errors=True)
    print("-" * 56)
    print("审计检测器自测：%d/%d 通过" % (len(CASES) - len(failed), len(CASES)))
    if failed:
        print("失败用例：")
        for n in failed:
            print("  - %s" % n)
        return 1
    print("检测器在注入用例上均能报出，且在干净输入上不误报。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
