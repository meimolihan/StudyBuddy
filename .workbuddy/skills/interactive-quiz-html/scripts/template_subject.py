# -*- coding: utf-8 -*-
"""【StudyBuddy 项目版模板】往 content/ 加一个科目 / 册别的题库。

用法：
  1. 复制本文件到项目里，例如 scripts/build_xxx_quiz.py
  2. 改下面「2) 配置」三处：ARCHIVE_REL（科目目录，相对项目根）、SUBJECT（科目名）、UNITS（题库数据）
  3. 运行：python scripts/build_xxx_quiz.py
  4. 重启服务（content/ 只在启动时扫一次），导航里才会出现新课

输出布局（LAYOUT）：
  * "content"（本项目默认）按 docs/CONTENT_LAYOUT.md → <NN-单元名>/<NN-课名>.html
  * "flat"    平铺「四年级XX下册 · 单元 · 课.html」，离线自用、双击即开

引擎能力（无需改动）：明暗模式、🔊 朗读、随机抽题、自动判分、继续测试（不重复刷完整库）。
"""
import os
import re
import sys
from pathlib import Path


# ---- 1) 定位项目根与引擎 ----
def _find_project_root(start):
    """向上找含 go.mod 的目录；找不到就退回起点（保证脚本不会因此报错）。"""
    for p in [start] + list(start.parents):
        if (p / "go.mod").is_file():
            return p
    return start


def _find_engine_dir(root):
    """引擎 build_quiz_html.py 可能就在本文件旁边，也可能在 .workbuddy/skills/... 下。"""
    for cand in (Path(__file__).resolve().parent,
                 root / ".workbuddy" / "skills" / "interactive-quiz-html" / "scripts"):
        if (cand / "build_quiz_html.py").is_file():
            return cand
    raise SystemExit("找不到引擎 build_quiz_html.py，请确认技能目录完整")


PROJECT_ROOT = _find_project_root(Path(__file__).resolve().parent)
sys.path.insert(0, str(_find_engine_dir(PROJECT_ROOT)))
from build_quiz_html import build as engine_build  # noqa: E402


# ---- 2) 配置：输出目录 / 科目名 / 学生姓名 / 输出布局 ----
# 科目目录相对项目根；科目目录名固定 chinese / math / english / morallaw / science。
# 也可用环境变量 QUIZ_ARCHIVE 直接覆盖（写绝对路径也行，便于临时试跑）。
ARCHIVE_REL = r"content/primary/pep/grade4/volume2/新科目"
SUBJECT = "新科目下册"        # 写进标题 / 页眉 / 页脚；含"英语"时朗读自动用 en-US
STUDENT = os.environ.get("QUIZ_STUDENT", "郭奕凡")

LAYOUT = os.environ.get("QUIZ_LAYOUT", "content")   # content（进系统）/ flat（离线自用）
ARCHIVE = os.environ.get("QUIZ_ARCHIVE") or (
    ARCHIVE_REL if os.path.isabs(ARCHIVE_REL) else str(PROJECT_ROOT / ARCHIVE_REL)
)


# ---- 3) 题库数据 ----
# 结构：[(单元名, [(课名, 广播提示, [题目...]), ...]), ...]
# 单题格式：(题型, 题干, [A,B,C,D四个选项], [答案字母])
#   题型 "s"=单选（答案1个）  "m"=多选（答案2~4个）
# 单元 / 课名按教材写中文序号即可（「第一单元 示例单元」「第1课 示例课」），
# content 布局会自动去掉前缀并补两位序号 → 01-示例单元/01-示例课.html
UNITS = [
    ("第一单元 示例单元", [
        ("第1课 示例课",
         "📣 今日广播：写一句给孩子的提示，100 字以内。",
         [
             ("s", "例题：下面说法正确的是（　）。",
              ["正确选项", "干扰项1", "干扰项2", "干扰项3"], ["A"]),
             ("m", "例题（多选）：下面属于……的有（　）。",
              ["正确1", "正确2", "干扰项", "干扰项"], ["A", "B"]),
         ]),
    ]),
]


# ---- 4) 生成（一般不用改）----
UNIT_PREFIX = r"^第[一二三四五六七八九十]+单元\s*"   # 「第一单元 自然之美」→「自然之美」
LESSON_PREFIX = r"^第?\d+课?\s*"                     # 「第1课 观潮」→「观潮」（兼容「1 观潮」）


def _strip_prefix(name, pat):
    """去掉单元 / 课的中文序号前缀，只留名字，供 content 布局拼「NN-名字」。"""
    return re.sub(pat, "", name).strip() or name.strip()


# Windows 文件名非法字符：能换全角的换全角（保留可读性），不能换的删掉。
# 例（英语单元）：「What time is it?」→「What time is it？」
_SAFE_MAP = {ord("\\"): None, ord("/"): None, ord("*"): 0xFF0A,
             ord("?"): 0xFF1F, ord('"'): 0x201D, ord("<"): 0xFF1C,
             ord(">"): 0xFF1E, ord("|"): 0xFF5C, ord(":"): 0xFF1A}


def _safe(name):
    return name.translate(_SAFE_MAP).strip()


if __name__ == "__main__":
    os.makedirs(ARCHIVE, exist_ok=True)
    total = 0
    for ui, (unit, lessons) in enumerate(UNITS, 1):
        udir = _safe("%02d-%s" % (ui, _strip_prefix(unit, UNIT_PREFIX)))
        for li, (lesson, broadcast, qs) in enumerate(lessons, 1):
            subtitle = unit + " · " + lesson
            if LAYOUT == "content":
                out = os.path.join(ARCHIVE, udir, _safe("%02d-%s.html" % (
                    li, _strip_prefix(lesson, LESSON_PREFIX))))
                os.makedirs(os.path.dirname(out), exist_ok=True)
            else:
                out = os.path.join(ARCHIVE, "四年级" + SUBJECT + " · " + subtitle + ".html")
            engine_build(subtitle, qs, broadcast, out, SUBJECT)
            total += 1
            print("生成 %2d | %s | %2d 题 | %s" % (total, subtitle, len(qs), os.path.relpath(out, ARCHIVE)))
    print("完成：共生成 %d 个 HTML 文件（布局 %s）" % (total, LAYOUT))
    print("目录：%s" % ARCHIVE)
    if LAYOUT == "content":
        print("下一步：重启 StudyBuddy（content/ 只在启动时扫描一次），再刷新页面。")
        print("        自检：go run ./tools/bankcheck       # 统计课程 / 题数，查命名与解析问题")
