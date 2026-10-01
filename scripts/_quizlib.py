# -*- coding: utf-8 -*-
"""题库脚本的共用小库（StudyBuddy 项目内）。

给「一个科目一个脚本」的题库生成器复用，省掉每个脚本都要抄一遍的样板：
  * 自动定位项目根（找 go.mod）与引擎 build_quiz_html.py
  * content 布局的目录 / 文件名生成（含 Windows 非法字符处理）
  * 题目打包助手 S / S2 / M
  * 统一入口 run()

用法（写在 scripts/build_xxx_quiz.py 里）：

    from _quizlib import S, S2, M, run
    UNITS = [("第一单元 xx", [("第1课 xx", "📣 广播", [S("题干", 答案, [干扰1, 干扰2, 干扰3])])])]
    if __name__ == "__main__":
        run(r"content/primary/pep/grade1/volume1/chinese", "语文上册", UNITS)

注意：本文件必须放在 scripts/ 下与调用脚本同目录。
"""
import os
import re
import sys
from pathlib import Path


def _find_project_root(start):
    for p in [start] + list(start.parents):
        if (p / "go.mod").is_file():
            return p
    return start


def _find_engine_dir(root):
    for cand in (Path(__file__).resolve().parent,
                 root / ".workbuddy" / "skills" / "interactive-quiz-html" / "scripts"):
        if (cand / "build_quiz_html.py").is_file():
            return cand
    raise SystemExit("找不到引擎 build_quiz_html.py，请确认技能目录完整")


PROJECT_ROOT = _find_project_root(Path(__file__).resolve().parent)
sys.path.insert(0, str(_find_engine_dir(PROJECT_ROOT)))
from build_quiz_html import build as engine_build  # noqa: E402


# ---- 题目打包 ----
def S(stem, ans, ws):
    """单选：正确项写在首位，给出 3 个干扰项（自动去重 / 兜底补足）。"""
    opts = [ans]
    for w in ws:
        if len(opts) >= 4:
            break
        if w != ans and w not in opts:
            opts.append(w)
    k = 1
    while len(opts) < 4:
        cand = "%s%d" % (ans, k) if not str(ans).isdigit() else str(int(ans) + k)
        if cand not in opts:
            opts.append(cand)
        k += 1
    return ("s", stem, opts, ["A"])


def S2(stem, opts):
    """单选：选项自备（必须 4 个，正确项在首位）。"""
    assert len(opts) == 4, stem
    return ("s", stem, opts, ["A"])


def M(stem, opts, ans):
    """多选：选项自备 4 个，答案字母 ≥2 个。"""
    assert len(opts) == 4 and 2 <= len(ans) <= 4, stem
    return ("m", stem, opts, ans)


# ---- content 布局命名 ----
UNIT_PREFIX = re.compile(r"^第[一二三四五六七八九十]+单元\s*")
LESSON_PREFIX = re.compile(r"^第(\d+)课\s*(.*)$")
CN_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
          "七": 7, "八": 8, "九": 9, "十": 10}
_SAFE_MAP = {ord("\\"): None, ord("/"): None, ord("*"): 0xFF0A, ord("?"): 0xFF1F,
             ord('"'): 0x201D, ord("<"): 0xFF1C, ord(">"): 0xFF1E,
             ord("|"): 0xFF5C, ord(":"): 0xFF1A}


def safe(name):
    return name.translate(_SAFE_MAP).strip()


def unit_dir(unit, index):
    """单元目录名：优先用「第N单元」里的中文序号，没有就用 enumerate 序号。"""
    m = UNIT_PREFIX.match(unit)
    name = unit[m.end():].strip() if m else unit.strip()
    no = CN_NUM.get(m.group(0)[1], 0) if m else 0
    return safe("%02d-%s" % (no or index, name or unit.strip()))


def lesson_file(lesson, index):
    """课文件名：「第N课 名字」→「NN-名字.html」（N 为教材册内连续编号）。"""
    m = LESSON_PREFIX.match(lesson)
    if m:
        return safe("%02d-%s.html" % (int(m.group(1)), m.group(2).strip() or lesson))
    return safe("%02d-%s.html" % (index, lesson.strip()))


def run(archive_rel, subject, units, student=None, layout=None, title=None):
    if student:
        os.environ["QUIZ_STUDENT"] = student
        import build_quiz_html as _eng
        _eng.STUDENT_NAME = student
    layout = layout or os.environ.get("QUIZ_LAYOUT", "content")
    archive = os.environ.get("QUIZ_ARCHIVE") or (
        archive_rel if os.path.isabs(archive_rel) else str(PROJECT_ROOT / archive_rel))
    os.makedirs(archive, exist_ok=True)
    total = 0
    for ui, (unit, lessons) in enumerate(units, 1):
        udir = unit_dir(unit, ui)
        for li, (lesson, broadcast, qs) in enumerate(lessons, 1):
            subtitle = unit + " · " + lesson
            if layout == "content":
                out = os.path.join(archive, udir, lesson_file(lesson, li))
                os.makedirs(os.path.dirname(out), exist_ok=True)
            else:
                out = os.path.join(archive, (title or subject) + " · " + subtitle + ".html")
            engine_build(subtitle, qs, broadcast, out, subject)
            total += 1
            print("生成 %2d | %-34s | %2d 题 | %s" %
                  (total, subtitle, len(qs), os.path.relpath(out, archive)))
    print("完成：共生成 %d 个 HTML 文件（布局 %s）" % (total, layout))
    print("目录：%s" % archive)
    if layout == "content":
        print("下一步：重启 StudyBuddy（content/ 只在启动时扫描一次），再刷新页面")
        print("        自检：go run ./tools/bankcheck")
