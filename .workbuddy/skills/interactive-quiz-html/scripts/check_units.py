# -*- coding: utf-8 -*-
"""题库结构自检：把生成脚本里的 UNITS 抠出来检查，生成 HTML 之前先跑一遍。

用法：
    python .workbuddy/skills/interactive-quiz-html/scripts/check_units.py scripts/build_xxx_quiz.py
        （脚本参数缺省为 scripts/build_chinese_v2_quiz.py）

检查项：
    * UNITS 字面量能否解析（先抓括号不配对这类语法错）
    * 单元数 / 课数 / 总题数，每课题量是否在 20~40
    * 每课题目：选项必须是 4 个、答案字母必须在 A~D、单选答案 1 个、多选答案 2~4 个
    * 同课题干是否重复、课号（「第N课」）是否连续
退出码 1 表示有必须修的问题，可串进脚本。

> 为什么不用「跑一遍生成脚本」代替：生成一次要写 28 个文件、只看到题数，
> 括号不配对 / 选项写少一个这类结构问题它不会报。这里直接用 ast 静态检查，快且安全。
"""
import ast
import collections
import os
import re
import sys

DEFAULT = os.path.join("scripts", "build_chinese_v2_quiz.py")


def load_units(path):
    """先按字面量静态解析（能抓括号不配对的语法错）；
    若 UNITS 里用了函数调用（如程序化出题的 build_vocab(...)），
    则退化为「导入该脚本、取其实例化的 UNITS」——两者都能查结构。"""
    src = open(path, encoding="utf-8").read()
    tree = ast.parse(src, filename=path)
    node = None
    for n in tree.body:
        if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "UNITS":
            node = n
            break
    if node is None:
        raise SystemExit("在 %s 里找不到 UNITS = [...]" % path)
    try:
        return ast.literal_eval(node.value)
    except ValueError:
        pass
    # 程序化题库：在受控命名空间里执行脚本（__name__ 非 __main__，不会触发生成）
    import importlib.util
    spec = importlib.util.spec_from_file_location("_quiz_under_check", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_quiz_under_check"] = mod
    # 让被检查的脚本能 import 同目录的辅助模块（如 scripts/_quizlib.py）
    script_dir = os.path.dirname(os.path.abspath(path))
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec.loader.exec_module(mod)
    units = getattr(mod, "UNITS", None)
    if units is None:
        raise SystemExit("导入 %s 后取不到 UNITS" % path)
    print("（UNITS 含程序化生成，已改为导入脚本后实例化检查）")
    return units


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    if not os.path.isfile(path):
        raise SystemExit("找不到脚本：%s" % path)

    units = load_units(path)
    problems = []          # 必须修
    hints = []             # 建议修
    total_q = 0
    lesson_no = 0
    nums = []
    num_groups = []        # 每个单元内部的课号（英语等按「单元内编号」的科目）
    per_lesson = []

    for unit, lessons in units:
        group = []
        for lesson, broadcast, qs in lessons:
            lesson_no += 1
            total_q += len(qs)
            m = re.match(r"^第(\d+)课\s*(.*)$", lesson)
            if not m:
                problems.append("%s：课名要写成「第N课 名字」" % lesson)
            else:
                nums.append(int(m.group(1)))
                group.append(int(m.group(1)))
            if not (20 <= len(qs) <= 40):
                problems.append("%s：题量 %d，应为 20~40" % (lesson, len(qs)))
            if not broadcast or len(broadcast) > 120:
                hints.append("%s：广播提示缺失或过长（%d 字）" % (lesson, len(broadcast or "")))
            stems = collections.Counter(q[1] for q in qs)
            for stem, n in stems.items():
                if n > 1:
                    problems.append("%s：同课题干重复 %d 次 —— %s" % (lesson, n, stem[:30]))
            for t, stem, opts, ans in qs:
                where = "%s / %s" % (lesson, stem[:24])
                if t not in ("s", "m"):
                    problems.append("%s：题型必须是 s 或 m（得到 %r）" % (where, t))
                if len(opts) != 4:
                    problems.append("%s：选项 %d 个，必须 4 个" % (where, len(opts)))
                if not ans or any(a not in "ABCD" for a in ans):
                    problems.append("%s：答案字母越界 %r" % (where, ans))
                if t == "s" and len(ans) != 1:
                    problems.append("%s：单选答案应 1 个（得到 %r）" % (where, ans))
                if t == "m" and not (2 <= len(ans) <= 4):
                    problems.append("%s：多选答案应 2~4 个（得到 %r）" % (where, ans))
            per_lesson.append((lesson, len(qs)))
        if group:
            num_groups.append(group)

    seq = list(range(1, len(nums) + 1))
    unit_local = all(g == list(range(1, len(g) + 1)) for g in num_groups) and len(num_groups) > 1
    if nums != seq and not unit_local:
        hints.append("课号不连续（语文等科目的序号是册内连续编号）：%s" % nums[:40])
    elif unit_local and nums != seq:
        hints.append("课号按单元内重新编号（英语等科目惯例）：%s" % [len(g) for g in num_groups])

    print("脚本：%s" % path)
    print("单元 %d 个 · 课 %d 门 · 题 %d 道 · 平均 %.1f 题/课"
          % (len(units), lesson_no, total_q, total_q / max(lesson_no, 1)))
    for unit, lessons in units:
        print("  %-22s %d 课 / %d 题"
              % (unit, len(lessons), sum(len(q) for _, _, q in lessons)))
    if hints:
        print("\n提示（%d）：" % len(hints))
        for h in hints:
            print("   ⚠ " + h)
    if problems:
        print("\n必须修的问题（%d）：" % len(problems))
        for p in problems:
            print("   ✗ " + p)
        print("\n结论：不通过，先修再生成。")
        return 1
    print("\n结论：结构检查通过 ✓（接着跑生成脚本，再用 go run ./tools/bankcheck 复核一遍）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
