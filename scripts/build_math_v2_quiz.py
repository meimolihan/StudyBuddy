# -*- coding: utf-8 -*-
"""人教版 四年级下册 数学 —— 全 9 单元 29 课交互自测生成器（程序化出题）。

输出（默认）：
  content/primary/pep/grade4/volume2/math/<NN-单元名>/<NN-课名>.html
课程序号沿用教材的册内连续编号（1~29），与上册 math/ 的 01~24 命名一致。

课本版本：义务教育教科书 数学 四年级 下册，人民教育出版社。
用法：
  1) python scripts/build_math_v2_quiz.py --verify   # 先自动验算（0 错误才继续）
  2) python scripts/build_math_v2_quiz.py            # 生成 HTML
  3) python .workbuddy/skills/interactive-quiz-html/scripts/check_units.py scripts/build_math_v2_quiz.py
  4) go run ./tools/bankcheck                         # 用系统解析器复核
  5) 重启 StudyBuddy 服务

设计要点（照技能里的「程序化出题」规范）：
  * 固定随机种子，题目可复现、可审查；
  * 数字全部落在教材范围内（三位数乘两位数、除数是两位数、两位小数加减等），不超纲；
  * 答案由代码精确算出，干扰项取「常见错误」（多进一位、漏写 0、小数点位置错、单位差 10 倍）；
  * 每课随机重试直到凑够目标题数且题干不重复；
  * --verify 会按题干正则反解数字、重新计算并与标注答案比对，确认 0 错误。
"""
import os
import re
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import random


# ---- 1) 定位项目根与引擎 ----
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


# ---- 2) 配置 ----
ARCHIVE_REL = r"content/primary/pep/grade4/volume2/math"
SUBJECT = "数学下册"
STUDENT = os.environ.get("QUIZ_STUDENT", "郭奕凡")

LAYOUT = os.environ.get("QUIZ_LAYOUT", "content")
ARCHIVE = os.environ.get("QUIZ_ARCHIVE") or (
    ARCHIVE_REL if os.path.isabs(ARCHIVE_REL) else str(PROJECT_ROOT / ARCHIVE_REL)
)


# ---- 3) 数字工具 ----
def dstr(x):
    """把数字（含 Decimal / int / float）统一格式化成不带科学计数法的字符串。"""
    if isinstance(x, Decimal):
        s = format(x.normalize(), "f")
    elif isinstance(x, float):
        s = format(Decimal(str(round(x, 6))).normalize(), "f")
    else:
        s = str(x)
    if s in ("-0", "-0.0"):
        s = "0"
    return s


def dec(x):
    return Decimal(str(x))


def fill(ans, ws):
    """正确项放首位，补足 3 个互不相同、且不等于正确项的干扰项。"""
    out = [ans]
    for w in ws:
        if len(out) >= 4:
            break
        if w != ans and w not in out:
            out.append(w)
    if len(out) < 4:
        # 兜底：correct 是数值时用「±1 / ±0.1 / ×10」扰动自动补足
        try:
            v = dec(ans)
        except Exception:  # noqa: BLE001
            raise AssertionError("干扰项不足且非数值：ans=%r ws=%r" % (ans, ws))
        step = dec("0.1") if "." in ans else dec(1)
        k = 1
        while len(out) < 4 and k < 500:
            for cand in (v + step * k, v - step * k, v + step * k * 10):
                s = dstr(cand)
                if s != ans and s not in out:
                    out.append(s)
                if len(out) >= 4:
                    break
            k += 1
    if len(out) < 4:
        raise AssertionError("干扰项不足：ans=%r ws=%r" % (ans, ws))
    return out


def gen(fn, count, seed, tries_factor=60, tag=""):
    """随机重试直到凑够 count 道题干不重复的题。"""
    rng = random.Random(seed)
    qs, seen, tries = [], set(), 0
    while len(qs) < count and tries < count * tries_factor:
        tries += 1
        q = fn(rng)
        if not q:
            continue
        if q[1] in seen:
            continue
        seen.add(q[1])
        qs.append(q)
    if len(qs) < count:
        raise SystemExit("出题不足：%s 只凑到 %d/%d 题" % (tag or fn.__name__, len(qs), count))
    return qs


def S(stem, ans, ws):
    return ("s", stem, fill(dstr(ans), [dstr(w) for w in ws]), ["A"])


def S2(stem, opts):
    """手工题：选项自备（正确项在首位）。"""
    assert len(opts) == 4, stem
    return ("s", stem, opts, ["A"])


def M(stem, opts, ans):
    return ("m", stem, opts, ans)


# ---- 4) 各课出题器 ----
# 4.1 四则运算
def g_addsub(rng):
    k = rng.randint(0, 4)
    a = rng.randint(120, 980)
    b = rng.randint(120, 980)
    if k == 0:
        return S("计算：%d + %d = （　）" % (a, b), a + b,
                 [a + b + 10, a + b - 10, a + b + 100, a + b - 1])
    if k == 1:
        c = a + b
        return S("已知两个加数的和是 %d，其中一个加数是 %d，另一个加数是（　）。" % (c, a), b,
                 [b + 1, b - 1, b + 10, c - b + 10])
    if k == 2:
        c = a + b
        return S("被减数是 %d，差是 %d，减数是（　）。" % (c, a), b,
                 [b + 10, b - 10, b + 1, a])
    if k == 3:
        return S("计算：%d - %d = （　）" % (max(a, b), min(a, b)), abs(a - b),
                 [abs(a - b) + 10, abs(a - b) - 10, abs(a - b) + 1, abs(a - b) - 1])
    c = a + b
    return S("减数是 %d，差是 %d，被减数是（　）。" % (a, b), c,
             [c + 10, c - 10, c + 1, a - b])


def g_muldiv(rng):
    k = rng.randint(0, 4)
    a = rng.randint(12, 48)
    b = rng.randint(12, 48)
    if k == 0:
        return S("计算：%d × %d = （　）" % (a, b), a * b,
                 [a * b + a, a * b - a, a * b + 10, a * b - 10])
    if k == 1:
        p = a * b
        return S("两个因数的积是 %d，其中一个因数是 %d，另一个因数是（　）。" % (p, a), b,
                 [b + 1, b - 1, b + 10, a])
    if k == 2:
        p = a * b
        return S("被除数是 %d，商是 %d，除数是（　）。" % (p, b), a,
                 [a + 1, a - 1, a + 10, b])
    if k == 3:
        return S("计算：%d ÷ %d = （　）" % (a * b, b), a,
                 [a + 1, a - 1, a * 2, a + 10])
    return S("除数 × 商 = 被除数。如果除数是 %d、商是 %d，那么被除数是（　）。" % (a, b), a * b,
             [a * b + a, a * b - b, a + b, a * b + 10])


def g_brackets(rng):
    a = rng.randint(12, 60)
    b = rng.randint(12, 60)
    c = rng.randint(2, 9)
    k = rng.randint(0, 3)
    if k == 0:
        return S("计算：(%d + %d) × %d = （　）" % (a, b, c), (a + b) * c,
                 [(a + b) * c + c, a + b * c, (a + b) * c - c, a * c + b])
    if k == 1:
        return S("计算：%d × (%d - %d) = （　）" % (c, max(a, b), min(a, b)), c * abs(a - b),
                 [c * abs(a - b) + c, c * max(a, b) - min(a, b), c * abs(a - b) - c, abs(a - b)])
    if k == 2:
        return S("计算：%d + %d × %d = （　）" % (a, c, c), a + c * c,
                 [(a + c) * c, a + c * c + c, a + c + c, a * c * c])
    d = rng.randint(500, 900)
    return S("计算：%d × (%d + %d) - %d = （　）" % (c, a, b, d), c * (a + b) - d,
             [c * (a + b) - d + c, c * a + b - d, c * (a + b), c * (a + b) - d - c])


def g_problem(rng):
    k = rng.randint(0, 4)
    a = rng.randint(12, 68)
    b = rng.randint(12, 68)
    if k == 0:
        return S("一支钢笔 %d 元，买 %d 支一共要（　）元。" % (a, b), a * b,
                 [a * b + a, a * b - b, a + b, a * b + 10])
    if k == 1:
        return S("汽车每小时行 %d 千米，%d 小时行（　）千米。" % (a, b), a * b,
                 [a * b + a, a + b, a * b - a, a * b + 10])
    if k == 2:
        tot = a * b
        return S("妈妈带了 %d 元，买了 %d 元的东西，还剩（　）元。" % (tot, a), tot - a,
                 [tot - a + 10, tot - a - 10, tot + a, tot - a + 1])
    if k == 3:
        return S("四（1）班有 %d 人，四（2）班比四（1）班多 %d 人，两个班一共有（　）人。" % (a, b),
                 a + a + b,
                 [a + b, a + a + b + 1, a + a + b - 1, a * 2])
    return S("%d 个同学，每人分 %d 本练习本，一共需要（　）本。" % (a, b), a * b,
             [a * b + 10, a + b, a * b - a, a * b + b])


# 4.2 运算定律
def g_add_law(rng):
    a = rng.randint(25, 380)
    b = rng.randint(25, 380)
    c = rng.randint(25, 380)
    k = rng.randint(0, 4)
    if k == 0:
        return S("根据加法交换律：%d + %d = %d + （　）" % (a, b, b), a,
                 [b, a + b, a - b, c])
    if k == 1:
        return S("根据加法结合律：(%d + %d) + %d = %d + (%d + （　）)" % (a, b, c, a, b), c,
                 [a, b, c + 1, a + c])
    if k == 2:
        return S("加法交换律用字母表示是 a + b = （　）", "b + a",
                 ["a - b", "a × b", "b - a", "a + b + a"])
    if k == 3:
        return S("加法结合律用字母表示是 (a + b) + c = （　）", "a + (b + c)",
                 ["(a + b) × c", "a + b + c + a", "a × b × c", "(a - b) + c"])
    return S("计算：%d + %d + %d = （　）" % (a, b, c), a + b + c,
             [a + b + c + 10, a + b + c - 10, a + b, a + c])


def g_add_law_apply(rng):
    k = rng.randint(0, 4)
    a = rng.randint(120, 880)
    if k == 0:
        return S("用简便方法计算：%d + 98 = （　）" % a, a + 98,
                 [a + 98 + 10, a + 98 - 10, a + 100, a + 98 + 2])
    if k == 1:
        return S("用简便方法计算：%d + 199 = （　）" % a, a + 199,
                 [a + 199 + 1, a + 199 - 1, a + 200, a + 199 + 10])
    if k == 2:
        return S("用简便方法计算：%d - 98 = （　）" % a, a - 98,
                 [a - 98 + 10, a - 98 - 2, a - 100, a - 98 - 1])
    b = rng.randint(20, 80)
    c = 100 - b
    return S("用简便方法计算：%d + %d + %d = （　）" % (a, b, c), a + b + c,
             [a + b + c + 10, a + b + c - 10, a + b, a + c])


def g_mul_law(rng):
    a = rng.randint(3, 25)
    b = rng.randint(3, 25)
    c = rng.randint(3, 25)
    k = rng.randint(0, 4)
    if k == 0:
        return S("根据乘法交换律：%d × %d = %d × （　）" % (a, b, b), a,
                 [b, a * b, a + b, b + 1])
    if k == 1:
        return S("根据乘法结合律：(%d × %d) × %d = %d × (%d × （　）)" % (a, b, c, a, b), c,
                 [a, b, a * c, c + 1])
    if k == 2:
        return S("乘法交换律用字母表示是 a × b = （　）", "b × a",
                 ["a + b", "a × b × a", "b + a", "a ÷ b"])
    if k == 3:
        return S("乘法分配律用字母表示是 (a + b) × c = （　）", "a × c + b × c",
                 ["a × c + b", "a + b × c", "a × b × c", "a × c - b × c"])
    return S("根据乘法分配律：(%d + %d) × %d = %d × %d + %d × （　）" % (a, b, c, a, c, b), c,
             [a, b, a + b, c + 1])


def g_mul_law_apply(rng):
    k = rng.randint(0, 5)
    if k == 0:
        n = rng.randint(13, 79)
        return S("用简便方法计算：25 × 4 × %d = （　）" % n, 100 * n,
                 [100 * n + 100, 100 * n - 100, 25 * 4 + n, 100 * n + 10])
    if k == 1:
        n = rng.randint(11, 69)
        return S("用简便方法计算：125 × 8 × %d = （　）" % n, 1000 * n,
                 [1000 * n + 1000, 1000 * n - 1000, 125 * 8 + n, 1000 * n + 100])
    if k == 2:
        n = rng.randint(12, 88)
        return S("用简便方法计算：99 × %d = （　）" % n, 99 * n,
                 [99 * n + n, 99 * n - n, 100 * n, 99 * n + 10])
    if k == 3:
        n = rng.randint(13, 79)
        return S("用简便方法计算：102 × %d = （　）" % n, 102 * n,
                 [102 * n + n, 102 * n - n, 100 * n, 102 * n + 10])
    if k == 4:
        n = rng.randint(12, 88)
        return S("用简便方法计算：%d × 99 + %d = （　）" % (n, n), 100 * n,
                 [99 * n, 101 * n, 100 * n + 100, 100 * n - 100])
    n = rng.randint(2, 9)
    return S("用简便方法计算：%d × 101 = （　）" % n, 101 * n,
             [100 * n, 101 * n + n, 101 * n - n, 101 * n + 10])


# 4.3 小数
def _dec_str(a, b):
    """把随机整数拼成两位以内的小数，保证教材范围内。"""
    ip = a % 100
    fp = b % 100
    return "%d.%02d" % (ip, fp)


def g_dec_meaning(rng):
    k = rng.randint(0, 4)
    n = rng.randint(1, 99)
    if k == 0:
        return S("把 1 米平均分成 100 份，每份是（　）米。", "0.01",
                 ["0.1", "0.001", "1.00", "0.10"])
    if k == 1:
        return S("0.%02d 里面有 %d 个（　）。" % (n, n), "0.01",
                 ["0.1", "0.001", "1", "0.10"])
    if k == 2:
        x = rng.randint(1, 9)
        y = rng.randint(1, 9)
        return S("%d 个 0.1 和 %d 个 0.01 组成的数是（　）。" % (x, y),
                 dstr(dec(x) / 10 + dec(y) / 100),
                 [dstr(dec(x) / 10 + dec(y) / 1000), dstr(dec(x) + dec(y) / 100),
                  dstr(dec(y) / 10 + dec(x) / 100), dstr(dec(x) / 10 + dec(y) / 10)])
    if k == 3:
        t = rng.randint(2, 9)
        return S("把 %d 米平均分成 10 份，每份是（　）米。" % t, dstr(dec(t) / 10),
                 [dstr(dec(t) / 100), dstr(dec(t)), dstr(dec(t) / 1000),
                  dstr(dec(t) / 10 + dec("0.1"))])
    t = rng.randint(2, 9)
    return S("十分之%d 写成小数是（　）。" % t, dstr(dec(t) / 10),
             [dstr(dec(t) / 100), dstr(dec(t)), dstr(dec(t) / 1000),
              dstr(dec(t) / 10 + dec("0.1"))])


def g_dec_readwrite(rng):
    k = rng.randint(0, 5)
    ip = rng.randint(0, 9)
    fp = rng.randint(1, 99)
    DIG = "零一二三四五六七八九"
    if k == 0:
        return S("0.%02d 读作（　）。" % fp, "零点" + "".join(DIG[int(c)] for c in "%02d" % fp),
                 ["零点" + str(fp), "百分之" + str(fp),
                  "零点" + "".join(DIG[int(c)] for c in str(fp)), "零点" + str(fp) + "零"])
    if k == 1:
        return S("%d.%02d 读作（　）。" % (ip, fp),
                 "%d点%s" % (ip, "".join(DIG[int(c)] for c in "%02d" % fp)),
                 ["%d点%d" % (ip, fp), "%d点%s" % (ip, str(fp)), "%d百分之%d" % (ip, fp),
                  "零点%s" % "".join(DIG[int(c)] for c in "%02d" % fp)])
    if k == 2:
        d1, d2 = rng.randint(0, 9), rng.randint(1, 9)
        base = dec(d1) / 10 + dec(d2) / 100
        return S("写出小数：零点%s%s（　）。" % (DIG[d1], DIG[d2]), dstr(base),
                 [dstr(base + dec("0.1")), dstr(base + dec("0.01")),
                  dstr(base * 10), dstr(base / 10)])
    if k == 3:
        return S("%d.%02d 中，百分位上的数字是（　）。" % (ip, fp), str(fp % 10),
                 [str((fp % 10 + 1) % 10), str((fp % 10 + 2) % 10), str((fp % 10 + 3) % 10),
                  str(fp // 10), str(ip)])
    if k == 4:
        return S("%d.%d 中，十分位上的数字是（　）。" % (ip, fp % 10), str(fp % 10),
                 [str((fp % 10 + 1) % 10), str((fp % 10 + 2) % 10), str((fp % 10 + 3) % 10),
                  str(ip), str(fp // 10)])
    return S("由 3 个 1、5 个 0.1 组成的数是（　）。", "3.5",
             ["3.05", "35", "3.50", "5.3"])


def g_dec_property(rng):
    k = rng.randint(0, 4)
    ip = rng.randint(0, 20)
    d = rng.randint(1, 9)
    alt = d + 1 if d < 9 else d - 1
    if k == 0:
        a = "%d.%d" % (ip, d)
        return S("与 %s 相等的小数是（　）。" % a, a + "0",
                 ["%d.0%d" % (ip, d), "%d.0%d" % (ip, d), "%d.%d0" % (ip, alt), "%d.%d" % (ip, alt)])
    if k == 1:
        a = "%d.%d0" % (ip, d)
        return S("%s 化简后是（　）。" % a, "%d.%d" % (ip, d),
                 ["%d.0%d" % (ip, d), "%d.0%d" % (ip, d), "%d.%d" % (ip, alt),
                  "%d.%d0" % (ip, alt)])
    if k == 2:
        a = "%d.%d" % (ip, d)
        return S("在 %s 的末尾添上一个 0，这个数（　）。" % a, "大小不变",
                 ["比原来大 10 倍", "比原来小 10 倍", "比原来大 1", "比原来小 1"])
    if k == 3:
        x = rng.randint(1, 9)
        y = x + 1 if x < 9 else x - 1
        return S("去掉 0.%d0 末尾的 0，得到（　）。" % x, "0.%d" % x,
                 ["0.0%d" % x, "0.%d0" % x, "%d.0" % x, "0.%d" % y])
    return S("%d.%d0 与 %d.%d 的关系是（　）。" % (ip, d, ip, d), "相等",
             ["前面的大", "后面的大", "无法比较", "相差 0.1"])


def g_dec_compare(rng):
    a = "%d.%02d" % (rng.randint(0, 9), rng.randint(1, 99))
    b = "%d.%d" % (rng.randint(0, 9), rng.randint(1, 9))
    if rng.random() < 0.5:
        b = "%d.%02d" % (rng.randint(0, 9), rng.randint(1, 99))
    da, db = dec(a), dec(b)
    if da == db:
        b = dstr(da + dec("0.01"))
        db = dec(b)
    op = ">" if da > db else "<"
    return S("比较大小：%s ○ %s，○ 里应填（　）。" % (a, b), op,
             ["<" if op == ">" else ">", "=", "无法比较", "≈"])


def g_dec_shift(rng):
    k = rng.randint(0, 5)
    a = rng.randint(1, 99)
    b = rng.randint(1, 99)
    s = "%d.%02d" % (a, b)
    d = dec(s)
    if k == 0:
        return S("把 %s 的小数点向右移动一位，结果是（　）。" % s, dstr(d.scaleb(1)),
                 [dstr(d.scaleb(2)), dstr(d.scaleb(-1)), dstr(d), dstr(d.scaleb(3))])
    if k == 1:
        return S("把 %s 的小数点向右移动两位，结果是（　）。" % s, dstr(d.scaleb(2)),
                 [dstr(d.scaleb(1)), dstr(d.scaleb(3)), dstr(d.scaleb(-2)), dstr(d)])
    if k == 2:
        return S("把 %s 的小数点向左移动一位，结果是（　）。" % s, dstr(d.scaleb(-1)),
                 [dstr(d.scaleb(-2)), dstr(d.scaleb(1)), dstr(d), dstr(d.scaleb(-3))])
    if k == 3:
        return S("把 %s 的小数点向左移动两位，结果是（　）。" % s, dstr(d.scaleb(-2)),
                 [dstr(d.scaleb(-1)), dstr(d.scaleb(2)), dstr(d.scaleb(-3)), dstr(d)])
    if k == 4:
        return S("计算：%s × 100 = （　）" % s, dstr(d.scaleb(2)),
                 [dstr(d.scaleb(1)), dstr(d.scaleb(3)), dstr(d.scaleb(-2)), dstr(d)])
    return S("计算：%s ÷ 10 = （　）" % s, dstr(d.scaleb(-1)),
             [dstr(d.scaleb(-2)), dstr(d.scaleb(1)), dstr(d), dstr(d.scaleb(-3))])


def g_dec_unit(rng):
    k = rng.randint(0, 5)
    a = rng.randint(1, 9)
    b = rng.randint(1, 99)
    if k == 0:
        return S("%d 米 %d 厘米 = （　）米" % (a, b), dstr(dec(a) + dec(b) / 100),
                 [dstr(dec(a) + dec(b)), dstr(dec(a) + dec(b) / 1000),
                  dstr(dec(a) + dec(b) / 10), dstr(dec(a) * 100 + dec(b))])
    if k == 1:
        return S("%d 千克 %d 克 = （　）千克" % (a, b), dstr(dec(a) + dec(b) / 1000),
                 [dstr(dec(a) + dec(b) / 100), dstr(dec(a) + dec(b)),
                  dstr(dec(a) + dec(b) / 10), dstr(dec(a) * 1000 + dec(b))])
    if k == 2:
        return S("%d.%02d 米 = （　）厘米" % (a, b), dstr((dec(a) + dec(b) / 100) * 100),
                 [dstr(dec(a) * 100 + dec(b) * 10), dstr(dec(a) + dec(b) / 100),
                  dstr((dec(a) + dec(b) / 100) * 10), dstr((dec(a) + dec(b) / 100) * 1000)])
    if k == 3:
        return S("%d 元 %d 角 = （　）元" % (a, b % 10), dstr(dec(a) + dec(b % 10) / 10),
                 [dstr(dec(a) + dec(b % 10) / 100), dstr(dec(a) + dec(b % 10)),
                  dstr(dec(a) * 10 + dec(b % 10)), dstr(dec(a) + dec(b % 10) / 10 + dec("0.1"))])
    if k == 4:
        return S("%d 分米 = （　）米" % b, dstr(dec(b) / 10),
                 [dstr(dec(b) / 100), dstr(dec(b)), dstr(dec(b) * 10),
                  dstr(dec(b) / 10 + dec("0.1"))])
    return S("%d 克 = （　）千克" % (b * 10), dstr(dec(b * 10) / 1000),
             [dstr(dec(b * 10) / 100), dstr(dec(b * 10)), dstr(dec(b * 10) / 10),
              dstr(dec(b * 10) / 10000)])


def g_dec_round(rng):
    k = rng.randint(0, 3)
    ip = rng.randint(0, 9)
    fp = rng.randint(1, 999)
    s = "%d.%03d" % (ip, fp)
    d = dec(s)
    q1 = d.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    q2 = d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    q0 = d.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    if k == 0:
        return S("把 %s 保留一位小数约是（　）。" % s, dstr(q1),
                 [dstr(q1 + dec("0.1")), dstr(q1 - dec("0.1")), dstr(q1 + dec("0.2")), dstr(q2)])
    if k == 1:
        return S("把 %s 保留两位小数约是（　）。" % s, dstr(q2),
                 [dstr(q2 + dec("0.01")), dstr(q2 - dec("0.01")), dstr(q2 + dec("0.1")), dstr(q1)])
    if k == 2:
        return S("把 %s 保留整数约是（　）。" % s, dstr(q0),
                 [dstr(q0 + dec("1")), dstr(q0 - dec("1")), dstr(q0 + dec("2")), dstr(q1)])
    return S("%s ≈ （　）（保留一位小数）" % s, dstr(q1),
             [dstr(q1 + dec("0.1")), dstr(q1 - dec("0.1")), dstr(q1 + dec("0.2")), dstr(q2)])


def g_dec_add(rng):
    a = "%d.%d" % (rng.randint(1, 40), rng.randint(1, 9))
    b = "%d.%02d" % (rng.randint(1, 40), rng.randint(1, 99))
    if rng.random() < 0.5:
        return S("计算：%s + %s = （　）" % (a, b), dstr(dec(a) + dec(b)),
                 [dstr(dec(a) + dec(b) + dec("0.1")), dstr(dec(a) + dec(b) - dec("0.1")),
                  dstr(dec(a) + dec(b) + dec("1")), dstr(dec(a) / 10 + dec(b))])
    x, y = dec(a), dec(b)
    if x < y:
        x, y = y, x
    return S("计算：%s - %s = （　）" % (dstr(x), dstr(y)), dstr(x - y),
             [dstr(x - y + dec("0.1")), dstr(x - y - dec("0.1")),
              dstr(x + y), dstr(x - y + dec("1"))])


def g_dec_addsub_mix(rng):
    a = dec("%d.%d" % (rng.randint(5, 40), rng.randint(1, 9)))
    b = dec("%d.%d" % (rng.randint(1, 30), rng.randint(1, 9)))
    c = dec("%d.%d" % (rng.randint(1, 20), rng.randint(1, 9)))
    if rng.random() < 0.5:
        return S("计算：%s + %s - %s = （　）" % (dstr(a), dstr(b), dstr(c)), dstr(a + b - c),
                 [dstr(a + b - c + dec("0.1")), dstr(a + b - c - dec("0.1")),
                  dstr(a + b + c), dstr(a - b - c)])
    if a < b + c:
        a = b + c + dec("0.5")
    return S("计算：%s - %s - %s = （　）" % (dstr(a), dstr(b), dstr(c)), dstr(a - b - c),
             [dstr(a - b - c + dec("0.1")), dstr(a - b - c - dec("0.1")),
              dstr(a - b + c), dstr(a + b + c)])


def g_dec_add_law(rng):
    a = dec("%d.%d" % (rng.randint(1, 40), rng.randint(1, 9)))
    b = dec("%d.%d" % (rng.randint(1, 50), rng.randint(1, 9)))
    c = dec("100") - b if rng.random() < 0.5 else dec("%d.%d" % (rng.randint(1, 50), rng.randint(1, 9)))
    return S("用简便方法计算：%s + %s + %s = （　）" % (dstr(a), dstr(b), dstr(c)),
             dstr(a + b + c),
             [dstr(a + b + c + dec("0.1")), dstr(a + b + c - dec("0.1")),
              dstr(a + b), dstr(a + c)])


# 4.4 图形与几何
def g_tri_sides(rng):
    k = rng.randint(0, 2)
    if k == 0:
        a, b, c = rng.randint(3, 12), rng.randint(3, 12), rng.randint(3, 12)
        ok = (a + b > c) and (a + c > b) and (b + c > a)
        return S("三条线段的长分别是 %d 厘米、%d 厘米、%d 厘米，它们（　）围成一个三角形。" % (a, b, c),
                 "能" if ok else "不能",
                 (["不能", "无法判断", "只有两边相等时才能", "要看线段摆放的方向"] if ok
                  else ["能", "无法判断", "把最短的边去掉就能", "三条边相等时才能"]))
    if k == 1:
        a, b = rng.randint(4, 10), rng.randint(4, 10)
        lo, hi = abs(a - b), a + b
        if hi - lo < 2:
            return None
        x = rng.randint(lo + 1, hi - 1)
        return S("一个三角形的两条边分别是 %d 厘米和 %d 厘米，第三条边可能是（　）厘米。" % (a, b), x,
                 [lo, hi, hi + 1, max(0, lo - 1)])
    n = rng.randint(3, 9)
    return S("一个等边三角形的边长是 %d 厘米，它的周长是（　）厘米。" % n, n * 3,
             [n * 2, n * 4, n + 3, n * 3 + n])


def g_tri_angle(rng):
    k = rng.randint(0, 3)
    if k == 0:
        a = rng.randint(20, 90)
        b = rng.randint(20, 160 - a)
        c = 180 - a - b
        return S("在一个三角形中，∠1 = %d°，∠2 = %d°，∠3 = （　）°" % (a, b), c,
                 [180 - a, a + b, 360 - a - b, c + 10])
    if k == 1:
        x = rng.randrange(20, 141, 2)
        return S("一个等腰三角形的顶角是 %d°，它的一个底角是（　）°" % x, (180 - x) // 2,
                 [180 - x, (180 - x) // 2 + 10, x, 90 - x // 2])
    if k == 2:
        a = rng.randint(25, 65)
        return S("在一个直角三角形中，一个锐角是 %d°，另一个锐角是（　）°" % a, 90 - a,
                 [180 - a, a, 90 + a, 90 - a + 10])
    return S("一个三角形中，∠1 = %d°，∠2 = %d°，∠3 是（　）°" % (90, 45), 45,
             [90, 60, 30, 135])


def g_tri_class(rng):
    if rng.random() < 0.35:
        a = 90
        b = rng.randint(25, 65)
    else:
        a = rng.randint(25, 85)
        b = rng.randint(25, 85)
    c = 180 - a - b
    if c <= 0 or c >= 180:
        return None
    mx = max(a, b, c)
    kind = "直角" if mx == 90 else ("钝角" if mx > 90 else "锐角")
    return S("一个三角形的两个内角分别是 %d° 和 %d°，第三个内角是 %d°，按角分这是一个（　）三角形。"
             % (a, b, c), kind,
             [x for x in ["锐角", "直角", "钝角", "等边"] if x != kind][:3])


def g_bar_chart(rng):
    boys = rng.sample(range(15, 31), 4)
    girls = rng.sample(range(15, 31), 4)
    names = ["一班", "二班", "三班", "四班"]
    data = "一班 %d/%d、二班 %d/%d、三班 %d/%d、四班 %d/%d（男/女人数）" % (
        boys[0], girls[0], boys[1], girls[1], boys[2], girls[2], boys[3], girls[3])
    k = rng.randint(0, 3)
    if k == 0:
        i = boys.index(max(boys))
        return S("某校四年级四个班的人数如下（" + data + "）。男生人数最多的班是（　）。", names[i],
                 [n for n in names if n != names[i]])
    if k == 1:
        i = girls.index(min(girls))
        return S("某校四年级四个班的人数如下（" + data + "）。女生人数最少的班是（　）。", names[i],
                 [n for n in names if n != names[i]])
    if k == 2:
        tot = [boys[i] + girls[i] for i in range(4)]
        if len(set(tot)) < 4:
            return None
        i = tot.index(max(tot))
        return S("某校四年级四个班的人数如下（" + data + "）。男、女生合计人数最多的班是（　）。", names[i],
                 [n for n in names if n != names[i]])
    s = sum(boys) + sum(girls)
    return S("某校四年级四个班的人数如下（" + data + "）。四个班一共有（　）人。", s,
             [s + 2, s - 2, sum(boys), sum(girls)])


def g_mean(rng):
    k = rng.randint(0, 3)
    n = rng.choice([3, 4, 5])
    m = rng.randint(55, 95)
    ds = [rng.randint(-4, 4) for _ in range(n - 1)]
    last = -sum(ds)
    if abs(last) > 4:
        return None
    vals = [m + d for d in ds] + [m + last]
    if len(set(vals)) < n:
        return None
    if k == 0:
        return S("小明 %d 次数学测验的成绩分别是 %s 分，平均成绩是（　）分。"
                 % (n, "、".join(map(str, vals))), m,
                 [m + 1, m - 1, m + n, m + max(vals) - m + 1])
    if k == 1:
        return S("%d 个数的平均数是 %d，这 %d 个数的和是（　）。" % (n, m, n), n * m,
                 [m + n, n * m + n, n * m - n, m])
    if k == 2:
        s = sum(vals)
        return S("%s 这 %d 个数的平均数是（　）。" % ("、".join(map(str, vals)), n), m,
                 [m + 1, m - 1, m + 2, m - 2])
    return S("四（1）班 %d 名同学的捐款分别是 %s 元，平均每人捐款（　）元。"
             % (n, "、".join(map(str, vals))), m,
             [m + 1, m - 1, m + n, sum(vals)])


def g_chicken_rabbit(rng):
    heads = rng.randint(8, 30)
    chickens = rng.randint(1, heads - 1)
    rabbits = heads - chickens
    feet = chickens * 2 + rabbits * 4
    k = rng.randint(0, 2)
    if k == 0:
        return S("笼子里有鸡和兔共 %d 只，一共有 %d 只脚。鸡有（　）只。" % (heads, feet), chickens,
                 [rabbits, chickens + 1, chickens - 1, heads])
    if k == 1:
        return S("笼子里有鸡和兔共 %d 只，一共有 %d 只脚。兔有（　）只。" % (heads, feet), rabbits,
                 [chickens, rabbits + 1, rabbits - 1, heads])
    if chickens <= rabbits:
        return None
    return S("笼子里有鸡和兔共 %d 只，一共有 %d 只脚。鸡比兔多（　）只。" % (heads, feet),
             chickens - rabbits, [rabbits - chickens, chickens, rabbits, chickens - rabbits + 1])


# ---- 5) 手工题库（概念 / 图形类）----
OBSERVE = [
    S2("从不同位置观察同一个物体，看到的形状（　）。",
       ["可能不同", "一定相同", "一定不同", "无法观察"]),
    S2("观察由小正方体搭成的物体，通常从前面、上面和（　）三个方向观察。",
       ["左面", "里面", "下面", "背面"]),
    S2("从前面看到的图形，通常叫做（　）。",
       ["正视图（从前面看到的图形）", "左视图", "俯视图", "展开图"]),
    S2("从上面看到的图形，通常叫做（　）。",
       ["俯视图（从上面看到的图形）", "正视图", "左视图", "剖面图"]),
    S2("一个正方体木块，从上面看到的是（　）。",
       ["正方形", "长方形", "三角形", "圆"]),
    S2("一个圆柱形茶叶罐，从上面看到的是（　）。",
       ["圆", "长方形", "正方形", "三角形"]),
    S2("一个球，从任何方向看到的都是（　）。",
       ["圆", "正方形", "长方形", "三角形"]),
    S2("一个长方体，从前面看到的一般是（　）。",
       ["长方形", "正方形", "圆", "三角形"]),
    S2("用 2 个同样的小正方体前后摆成一行，从上面看到的是（　）。",
       ["一行 2 个正方形", "一列 2 个正方形", "1 个正方形", "一个长方形"]),
    S2("用 2 个同样的小正方体上下叠放，从前面看到的是（　）。",
       ["一列 2 个正方形", "一行 2 个正方形", "1 个正方形", "一个长方形"]),
    S2("用 3 个同样的小正方体紧挨着排成一行，从前面看到的是（　）。",
       ["一行 3 个正方形", "一列 3 个正方形", "一行 2 个正方形", "3 个分开的正方形"]),
    S2("只从一个方向观察物体，得到的形状（　）。",
       ["不能确定物体的全貌", "一定能确定物体的全貌", "就是物体的真实形状", "没有意义"]),
    S2("从左边看和从右边看同一个物体，看到的形状（　）。",
       ["可能相同，也可能不同", "一定相同", "一定不同", "一定相反"]),
    S2("要同时看到一个长方体的三个面，应该站在（　）位置观察。",
       ["能同时看到前面、上面和侧面的位置", "正对着前面", "正对着上面", "贴着物体"]),
    S2("用 4 个同样的小正方体搭成一个长方体，从前面看到 4 个正方形排成一行，那么这 4 个小正方体是（　）。",
       ["排成一行的", "叠成两层的", "摆成两列的", "分开摆的"]),
    S2("从上面看到一行 3 个正方形，从前面也看到一行 3 个正方形，这个物体最有可能是（　）。",
       ["3 个同样的小正方体排成一行", "3 个小正方体叠成一列",
        "3 个小正方体摆成三角形", "1 个大正方体"]),
    S2("观察物体时，把从前面、上面、左面看到的形状画下来，这些图形叫做（　）。",
       ["视图（三视图）", "展开图", "统计图", "示意图"]),
    S2("一个圆柱形的笔筒，从侧面看到的是（　）。",
       ["长方形", "圆", "三角形", "正方形"]),
    S2("下面说法正确的是（　）。",
       ["从不同方向观察同一物体，看到的形状可能不同",
        "从不同方向观察同一物体，看到的形状一定相同",
        "只要看一个方向就能知道物体的样子",
        "观察物体不需要固定方向"]),
    M("观察物体时，下面说法正确的有（　）。",
      ["一次观察通常要选前面、上面、左面三个方向", "同一物体不同方向看到的形状可能不同",
       "从一个方向看到的形状不能确定物体的全貌", "球从任何方向看都是圆"],
      ["A", "B", "C", "D"]),
    M("下面是常见的立体图形，从上面看是圆形的有（　）。",
      ["圆柱", "球", "圆锥", "正方体"], ["A", "B", "C"]),
    M("用 2 个同样的小正方体，可能搭出的形状有（　）。",
      ["前后排成一行", "上下叠成一列", "左右排成一行", "摆成三角形"], ["A", "B", "C"]),
]

TRI_FEATURE = [
    S2("由三条线段围成的图形（每相邻两条线段的端点相连）叫做（　）。",
       ["三角形", "四边形", "长方形", "梯形"]),
    S2("三角形有（　）条边、3 个角和 3 个顶点。",
       ["3", "4", "2", "6"]),
    S2("从三角形的一个顶点到它的对边作一条垂线，顶点和垂足之间的线段叫做三角形的（　）。",
       ["高", "中线", "角平分线", "对角线"]),
    S2("三角形的高与它对应的底（　）。",
       ["互相垂直", "互相平行", "长度相等", "没有关系"]),
    S2("一个三角形有（　）条高。",
       ["3", "1", "2", "无数"]),
    S2("三角形具有（　）。",
       ["稳定性", "易变形性", "对称性", "不稳定性"]),
    S2("生活中利用三角形稳定性的是（　）。",
       ["自行车三角架", "伸缩门", "推拉窗", "折叠椅"]),
    S2("平行四边形容易变形，而三角形（　）。",
       ["不容易变形，具有稳定性", "同样容易变形", "比平行四边形更容易变形", "不能变形"]),
    S2("画三角形的高时，要用（　）。",
       ["三角尺（利用直角边画垂线）", "圆规", "量角器画弧", "直尺随意连线"]),
    S2("三角形的底和高必须（　）。",
       ["相对应", "一样长", "互相平行", "在同一条直线上"]),
    S2("三角形是由三条（　）围成的。",
       ["线段", "直线", "射线", "曲线"]),
    S2("围成三角形时，相邻两条线段的端点要（　）。",
       ["首尾相连", "互相平行", "留出空隙", "交叉重叠"]),
    S2("三角形的三个顶点（　）。",
       ["不在同一条直线上", "在同一条直线上", "可以任意在一条直线上", "都在高上"]),
    S2("在三角形中，顶点 A 的对边是（　）。",
       ["BC 边", "AB 边", "AC 边", "过 A 的高"]),
    S2("直角三角形中，两条直角边可以分别看作它的（　）。",
       ["底和高", "两条高", "两条中线", "两条对角线"]),
    S2("钝角三角形中，有（　）条高在三角形的外部。",
       ["2", "1", "0", "3"]),
    S2("一个三角形的三条高（　）。",
       ["所在直线一定相交于一点", "一定互相平行", "一定互相垂直", "长度一定相等"]),
    S2("关于三角形的描述，正确的是（　）。",
       ["三条线段首尾相接围成的图形", "三条直线围成的图形",
        "有三条边的图形都是三角形", "三条线段不连接也叫三角形"]),
    S2("三角形有 3 个（　）。",
       ["顶点", "高", "周长", "面积"]),
    S2("下面图形中最牢固、不易变形的是（　）。",
       ["三角形", "平行四边形", "长方形", "正方形"]),
    M("关于三角形的高，下面说法正确的有（　）。",
      ["从顶点向对边作垂线", "顶点到垂足的线段是高", "高与对应的底互相垂直",
       "一个三角形有 3 条高"], ["A", "B", "C", "D"]),
    M("下面哪些地方用到了三角形的稳定性（　）。",
      ["自行车三角架", "屋顶的人字架", "电线杆的三角支架", "推拉的铁栅门"], ["A", "B", "C"]),
]

TRI_CLASS_STATIC = [
    S2("三角形按角分，可以分为（　）。",
       ["锐角三角形、直角三角形、钝角三角形", "等腰三角形、等边三角形、不等边三角形",
        "大三角形、小三角形", "直角梯形、等腰梯形"]),
    S2("三角形按边分，可以分为（　）。",
       ["等腰三角形、等边三角形、不等边三角形", "锐角三角形、直角三角形、钝角三角形",
        "长三角形、短三角形", "正三角形、斜三角形"]),
    S2("三个角都是锐角的三角形叫做（　）。",
       ["锐角三角形", "直角三角形", "钝角三角形", "等边三角形"]),
    S2("有一个角是直角的三角形叫做（　）。",
       ["直角三角形", "锐角三角形", "钝角三角形", "等腰三角形"]),
    S2("有一个角是钝角的三角形叫做（　）。",
       ["钝角三角形", "锐角三角形", "直角三角形", "等边三角形"]),
    S2("三个角都相等（都是 60°）的三角形叫做（　）。",
       ["等边三角形（正三角形）", "等腰三角形", "直角三角形", "钝角三角形"]),
    S2("等边三角形一定是（　）。",
       ["等腰三角形", "直角三角形", "钝角三角形", "不等边三角形"]),
    S2("有两条边相等的三角形叫做（　）。",
       ["等腰三角形", "等边三角形", "不等边三角形", "直角三角形"]),
    S2("三条边都不相等的三角形叫做（　）。",
       ["不等边三角形", "等腰三角形", "等边三角形", "锐角三角形"]),
    S2("等腰三角形中，相等的两条边叫做（　）。",
       ["腰", "底", "高", "底角"]),
    S2("等腰三角形中，两腰的夹角叫做（　）。",
       ["顶角", "底角", "直角", "外角"]),
    S2("等腰三角形中，腰和底的夹角叫做（　）。",
       ["底角", "顶角", "直角", "钝角"]),
    S2("一个三角形中最多有（　）个直角。",
       ["1", "2", "3", "0"]),
    S2("一个三角形中最多有（　）个钝角。",
       ["1", "2", "3", "0"]),
    S2("一个三角形中至少有（　）个锐角。",
       ["2", "1", "0", "3"]),
    S2("一个三角形如果有一个角是 100°，它一定是（　）。",
       ["钝角三角形", "锐角三角形", "直角三角形", "等边三角形"]),
    S2("一个三角形如果有一个角是 90°，它一定是（　）。",
       ["直角三角形", "锐角三角形", "钝角三角形", "等腰三角形"]),
    S2("一个三角形如果两个角分别是 45° 和 45°，它一定是（　）。",
       ["等腰直角三角形", "等边三角形", "钝角三角形", "不等边三角形"]),
    S2("等腰三角形的两个底角（　）。",
       ["相等", "不相等", "都是 60°", "一个是直角"]),
    S2("把一个大三角形剪成两个小三角形，每个小三角形的内角和是（　）。",
       ["180°", "90°", "360°", "不确定"]),
    M("下面说法正确的有（　）。",
      ["按角分可以把三角形分成三类", "按边分也可以把三角形分成三类",
       "等边三角形是特殊的等腰三角形", "一个三角形中至少有两个锐角"], ["A", "B", "C", "D"]),
    M("一定是等腰三角形的有（　）。",
      ["等边三角形", "有两个角相等的三角形", "两条边相等的三角形", "有一个角是 90° 的三角形"],
      ["A", "B", "C"]),
]

AXIS_SYM = [
    S2("把一个图形沿一条直线对折，直线两边的图形能够完全重合，这个图形叫做（　）。",
       ["轴对称图形", "平移图形", "旋转图形", "相似图形"]),
    S2("折痕所在的这条直线叫做对称图形的（　）。",
       ["对称轴", "中线", "高", "对角线"]),
    S2("长方形有（　）条对称轴。",
       ["2", "1", "4", "无数"]),
    S2("正方形有（　）条对称轴。",
       ["4", "2", "1", "无数"]),
    S2("圆有（　）条对称轴。",
       ["无数", "4", "2", "1"]),
    S2("等腰三角形有（　）条对称轴。",
       ["1", "2", "3", "0"]),
    S2("等边三角形有（　）条对称轴。",
       ["3", "1", "2", "无数"]),
    S2("平行四边形（一般情况）有（　）条对称轴。",
       ["0", "1", "2", "4"]),
    S2("等腰梯形有（　）条对称轴。",
       ["1", "2", "0", "4"]),
    S2("画轴对称图形的另一半时，关键是找出对应点，对应点到对称轴的距离（　）。",
       ["相等", "不相等", "相差 1 格", "没有关系"]),
    S2("轴对称图形沿对称轴对折后，两边的图形（　）。",
       ["完全重合", "完全分开", "部分重合", "没有关系"]),
    S2("下面图形中不是轴对称图形的是（　）。",
       ["一般平行四边形", "长方形", "正方形", "圆"]),
    S2("下面图形中是轴对称图形的是（　）。",
       ["等腰梯形", "一般平行四边形", "任意三角形", "任意四边形"]),
    S2("长方形和正方形都有对称轴，其中（　）的对称轴更多。",
       ["正方形", "长方形", "一样多", "无法比较"]),
    S2("字母中，是轴对称图形的是（　）。",
       ["A", "F", "G", "J"]),
    S2("汉字中，可以看作轴对称图形的是（　）。",
       ["田", "上", "下", "多"]),
    S2("五角星（正五角星）有（　）条对称轴。",
       ["5", "4", "1", "10"]),
    S2("把一个轴对称图形沿对称轴对折，得到的两个图形（　）。",
       ["完全相同（全等）", "大小不同", "形状不同", "没有关系"]),
    S2("对称轴两边的对应点到对称轴的距离相等，这条性质可以用来（　）。",
       ["画出轴对称图形的另一半", "计算图形的面积", "计算周长", "判断三角形类型"]),
    M("下面是轴对称图形的有（　）。",
      ["正方形", "长方形", "圆", "等腰三角形"], ["A", "B", "C", "D"]),
    M("关于对称轴，下面说法正确的有（　）。",
      ["对称轴是一条直线", "对称轴两边的图形完全重合",
       "不同图形的对称轴条数可能不同", "圆有无数条对称轴"], ["A", "B", "C", "D"]),
    M("下面图形中对称轴条数为 1 的有（　）。",
      ["等腰三角形", "等腰梯形", "长方形", "正方形"], ["A", "B"]),
]

TRANSLATE = [
    S2("把一个图形整体沿某条直线移动一定的距离，这样的运动叫做（　）。",
       ["平移", "旋转", "轴对称", "放大"]),
    S2("图形平移后，形状和大小（　）。",
       ["都不变", "都改变", "形状变大小不变", "大小变形状不变"]),
    S2("图形平移后，图形的（　）发生了变化。",
       ["位置", "大小", "形状", "内角和"]),
    S2("一个图形向右平移 5 格，再向右平移 3 格，相当于向右平移（　）格。",
       ["8", "2", "15", "5"]),
    S2("一个图形先向右平移 4 格，再向左平移 4 格，这时图形（　）。",
       ["回到原来的位置", "向右 8 格", "向左 8 格", "向右 4 格"]),
    S2("一个图形先向上平移 2 格，再向上平移 6 格，一共向上平移了（　）格。",
       ["8", "4", "12", "2"]),
    S2("判断一个图形平移了几格，可以数（　）移动的格数。",
       ["对应点（或对应边）", "图形的边数", "图形的面积", "图形的周长"]),
    S2("平移的方向可以是（　）。",
       ["上下或左右等各个方向", "只能是上下", "只能是左右", "只能是斜方向"]),
    S2("（　）是平移现象。",
       ["电梯上下运动", "风扇叶片转动", "钟表指针走动", "拧开水龙头"]),
    S2("下面属于平移现象的是（　）。",
       ["推拉抽屉", "摩天轮转动", "翻书", "转动方向盘"]),
    S2("平移时，图形上每个点移动的方向（　）。",
       ["相同", "不同", "相反", "随意"]),
    S2("平移时，图形上每个点移动的距离（　）。",
       ["相同", "不同", "有大有小", "随意"]),
    S2("画平移后的图形，先要找出图形的（　）点。",
       ["关键（对应）", "中心", "顶", "中"]),
    S2("平移不改变图形的（　）。",
       ["形状和大小", "位置", "所在方向", "坐标"]),
    S2("一个长方形向左平移 6 格，它的长和宽（　）。",
       ["都不变", "都变小", "长变大", "宽变大"]),
    S2("图形平移前后，对应线段（　）。",
       ["平行且相等", "互相垂直", "长度不等", "相交"]),
    S2("把一条线段向上平移 3 格，线段的长度（　）。",
       ["不变", "变长 3 格", "变短 3 格", "变成原来的 3 倍"]),
    S2("下面说法正确的是（　）。",
       ["平移只改变图形的位置，不改变形状和大小",
        "平移会改变图形的形状", "平移会改变图形的大小", "平移后图形方向会改变"]),
    S2("在方格纸上把一个图形向右平移 7 格，每个关键点都要向右数（　）格。",
       ["7", "1", "14", "不确定"]),
    M("下面是平移现象的有（　）。",
      ["电梯上下运动", "推拉抽屉", "火车在直轨道上行驶", "钟表指针走动"], ["A", "B", "C"]),
    M("关于平移，下面说法正确的有（　）。",
      ["平移方向可以上下左右", "平移距离用格数表示", "平移后形状不变",
       "平移后大小不变"], ["A", "B", "C", "D"]),
    M("图形平移后保持不变的有（　）。",
      ["形状", "大小", "对应线段的长度", "图形所在的位置"], ["A", "B", "C"]),
]

LUNCH = [
    S2("营养午餐的搭配要尽量做到（　）。",
       ["荤素搭配、营养均衡", "只吃肉", "只吃蔬菜", "只吃主食"]),
    S2("下面属于荤菜的是（　）。",
       ["红烧肉", "炒青菜", "凉拌黄瓜", "煮玉米"]),
    S2("下面属于素菜的是（　）。",
       ["炒豆芽", "红烧鱼", "炒鸡蛋", "炒肉片"]),
    S2("人体每天所需的营养中，含量最多的是（　）。",
       ["水", "脂肪", "盐", "糖"]),
    S2("午餐中米饭主要提供（　）。",
       ["糖类（碳水化合物）", "蛋白质", "脂肪", "维生素"]),
    S2("鸡蛋、瘦肉主要提供（　）。",
       ["蛋白质", "糖类", "维生素", "水"]),
    S2("蔬菜、水果主要提供（　）。",
       ["维生素和无机盐", "脂肪", "糖类", "蛋白质"]),
    S2("统计本班同学最喜欢的午餐菜肴，最合适的统计图是（　）。",
       ["条形统计图", "折线统计图", "扇形统计图", "统计表就够了"]),
    S2("要把男生和女生喜欢菜肴的人数同时表示出来，最好用（　）。",
       ["复式条形统计图", "单式条形统计图", "折线统计图", "只有统计表"]),
    S2("挑食、偏食的坏处是（　）。",
       ["容易营养不良", "长得更快", "更聪明", "没有坏处"]),
    S2("下面午餐搭配最合理的是（　）。",
       ["米饭 + 西红柿炒鸡蛋 + 炒青菜", "只有两碗米饭",
        "只有一盘红烧肉", "三包薯片 + 一杯可乐"]),
    S2("吃饭时要注意（　）。",
       ["按时吃饭、不挑食", "边跑边吃", "吃得越快越好", "只喝饮料"]),
    S2("菜肴中油脂太多，长期食用容易（　）。",
       ["发胖", "长高", "变瘦", "更健康"]),
    S2("挑选午餐时，下面做法正确的是（　）。",
       ["荤素搭配，适量摄入", "只挑最贵的", "只挑油炸的", "只喝饮料"]),
    S2("条形统计图的特点是（　）。",
       ["能清楚地看出各种数量的多少", "能看出数量增减变化趋势",
        "只能看出总数", "看不出多少"]),
    S2("要比较两种菜肴受欢迎的程度，可以先（　）。",
       ["统计喜欢的人数", "称它们的重量", "量它们的体积", "闻它们的味道"]),
    S2("维生素含量比较丰富的食物是（　）。",
       ["新鲜蔬菜和水果", "肥肉", "白糖", "食盐"]),
    S2("下面说法正确的是（　）。",
       ["营养均衡有利于身体健康", "吃得油腻越多越有营养",
        "只看好不好吃就行", "少吃蔬菜没关系"]),
    M("下面属于荤菜的有（　）。",
      ["红烧肉", "清蒸鱼", "炒鸡丁", "炒青菜"], ["A", "B", "C"]),
    M("合理搭配午餐应当考虑的有（　）。",
      ["荤素搭配", "营养均衡", "粗细搭配", "只考虑颜色好看"], ["A", "B", "C"]),
    M("统计本班午餐情况时，可以统计的内容有（　）。",
      ["喜欢各种菜肴的人数", "每天吃剩的数量", "男生与女生的人数的对比",
       "同学的身高体重"], ["A", "B", "C"]),
    M("下面食物能提供糖类（碳水化合物）的有（　）。",
      ["米饭", "面条", "馒头", "肥肉"], ["A", "B", "C"]),
]


# ---- 6) 题库 ----
SEED = 20260929

UNITS = [
    ("第一单元 四则运算", [
        ("第1课 加减法的意义和各部分间的关系",
         "📣 今日广播：加数 + 加数 = 和，和 - 一个加数 = 另一个加数；被减数 - 减数 = 差，减数 + 差 = 被减数。",
         gen(g_addsub, 24, SEED + 1)),
        ("第2课 乘除法的意义和各部分间的关系",
         "📣 今日广播：因数 × 因数 = 积，积 ÷ 一个因数 = 另一个因数；被除数 ÷ 除数 = 商，商 × 除数 = 被除数。",
         gen(g_muldiv, 24, SEED + 2)),
        ("第3课 括号",
         "📣 今日广播：有括号的先算括号里面的；既有中括号又有小括号，先算小括号里面的，再算中括号里面的。",
         gen(g_brackets, 24, SEED + 3)),
        ("第4课 解决问题",
         "📣 今日广播：单价 × 数量 = 总价，速度 × 时间 = 路程。读题时先找出「每份是多少、有几份」。",
         gen(g_problem, 24, SEED + 4)),
    ]),
    ("第二单元 观察物体（二）", [
        ("第5课 观察物体（二）",
         "📣 今日广播：从前面、上面、左面三个方向观察物体，看到的形状可能不同；只看一个方向不能确定物体的全貌。",
         OBSERVE),
    ]),
    ("第三单元 运算定律", [
        ("第6课 加法运算定律",
         "📣 今日广播：加法交换律 a + b = b + a；加法结合律 (a + b) + c = a + (b + c)。",
         gen(g_add_law, 24, SEED + 6)),
        ("第7课 加法运算定律的应用",
         "📣 今日广播：把接近整百的数看成整百数再加、再减。如 137 + 98 = 137 + 100 - 2。",
         gen(g_add_law_apply, 24, SEED + 7)),
        ("第8课 乘法运算定律",
         "📣 今日广播：乘法交换律 a × b = b × a；结合律 (a × b) × c = a × (b × c)；分配律 (a + b) × c = a × c + b × c。",
         gen(g_mul_law, 24, SEED + 8)),
        ("第9课 乘法运算定律的应用",
         "📣 今日广播：25 × 4 = 100，125 × 8 = 1000，看准这两个「好朋友」，计算就快多了。",
         gen(g_mul_law_apply, 24, SEED + 9)),
    ]),
    ("第四单元 小数的意义和性质", [
        ("第10课 小数的意义",
         "📣 今日广播：把 1 平均分成 10 份，每份是 0.1；分成 100 份，每份是 0.01；分成 1000 份，每份是 0.001。",
         gen(g_dec_meaning, 24, SEED + 10)),
        ("第11课 小数的读法和写法",
         "📣 今日广播：小数点读作「点」，小数部分要一位一位地读。如 3.05 读作三点零五。",
         gen(g_dec_readwrite, 24, SEED + 11)),
        ("第12课 小数的性质",
         "📣 今日广播：小数的末尾添上 0 或者去掉 0，小数的大小不变。注意是「末尾」，不是「中间」！",
         gen(g_dec_property, 24, SEED + 12)),
        ("第13课 小数的大小比较",
         "📣 今日广播：先比整数部分，整数部分大的那个数就大；整数部分相同，再比十分位、百分位……",
         gen(g_dec_compare, 24, SEED + 13)),
        ("第14课 小数点移动引起小数大小的变化",
         "📣 今日广播：小数点向右移动一位、两位、三位，小数就扩大到原来的 10 倍、100 倍、1000 倍；向左移动就缩小。",
         gen(g_dec_shift, 24, SEED + 14)),
        ("第15课 小数与单位换算",
         "📣 今日广播：1 米 = 100 厘米，1 千克 = 1000 克，1 元 = 10 角。低级单位换算成高级单位要除以进率。",
         gen(g_dec_unit, 24, SEED + 15)),
        ("第16课 小数的近似数",
         "📣 今日广播：保留几位小数，就要看它后面一位上的数，用「四舍五入」法求近似数。",
         gen(g_dec_round, 24, SEED + 16)),
    ]),
    ("第五单元 三角形", [
        ("第17课 三角形的特性",
         "📣 今日广播：三角形由三条线段首尾相接围成，有 3 条边、3 个角、3 个顶点、3 条高；三角形具有稳定性。",
         TRI_FEATURE),
        ("第18课 三角形的三边关系",
         "📣 今日广播：三角形任意两边的和大于第三边；任意两边的差小于第三边。",
         gen(g_tri_sides, 24, SEED + 18)),
        ("第19课 三角形的分类",
         "📣 今日广播：按角分有锐角三角形、直角三角形、钝角三角形；按边分有等腰三角形、等边三角形、不等边三角形。",
         TRI_CLASS_STATIC + gen(g_tri_class, 12, SEED + 19)),
        ("第20课 三角形的内角和",
         "📣 今日广播：三角形三个内角的和是 180°。等腰三角形两底角相等，等边三角形每个角都是 60°。",
         gen(g_tri_angle, 24, SEED + 20)),
    ]),
    ("第六单元 小数的加法和减法", [
        ("第21课 小数加减法",
         "📣 今日广播：计算小数加减法要把小数点对齐，也就是相同数位对齐，得数的小数点与上面的对齐。",
         gen(g_dec_add, 24, SEED + 21)),
        ("第22课 小数加减混合运算",
         "📣 今日广播：小数加减混合运算的运算顺序和整数一样，从左往右算，有括号先算括号里面的。",
         gen(g_dec_addsub_mix, 24, SEED + 22)),
        ("第23课 整数加法运算定律推广到小数",
         "📣 今日广播：整数加法的交换律、结合律在小数加法里同样适用，可以先算出 100 凑整。",
         gen(g_dec_add_law, 24, SEED + 23)),
    ]),
    ("第七单元 图形的运动（二）", [
        ("第24课 轴对称",
         "📣 今日广播：沿一条直线对折能完全重合的图形叫轴对称图形，这条直线叫对称轴；对应点到对称轴的距离相等。",
         AXIS_SYM),
        ("第25课 平移",
         "📣 今日广播：平移只改变图形的位置，不改变形状和大小；平移的距离用格数表示。",
         TRANSLATE),
    ]),
    ("第八单元 平均数与条形统计图", [
        ("第26课 平均数",
         "📣 今日广播：平均数 = 总数量 ÷ 总份数，它代表一组数据的整体水平，一定在最小数和最大数之间。",
         gen(g_mean, 22, SEED + 26)),
        ("第27课 复式条形统计图",
         "📣 今日广播：复式条形统计图能同时表示两组数据，看清图例（谁代表谁）再比较。",
         gen(g_bar_chart, 22, SEED + 27)),
        ("第28课 营养午餐",
         "📣 今日广播：午餐要荤素搭配、营养均衡；统计喜欢的人数可以用条形统计图。",
         LUNCH),
    ]),
    ("第九单元 数学广角——鸡兔同笼", [
        ("第29课 鸡兔同笼",
         "📣 今日广播：鸡有 2 只脚，兔有 4 只脚。假设全是鸡，脚数就比实际少，每少 2 只脚就多 1 只兔。",
         gen(g_chicken_rabbit, 24, SEED + 29)),
    ]),
]


# ---- 7) 自动验算（--verify）----
def _eval(expr):
    e = expr.replace("×", "*").replace("÷", "/")
    e = re.sub(r"[^0-9+\-*/().]", "", e)
    val = eval(e, {"__builtins__": {}}, {})
    return Decimal(str(round(val, 6)))


def _q(x):
    return Decimal(str(round(x, 6)))


def expect(stem):
    """按题干反解出正确答案（字符串）；无法识别时返回 None（记为未验算）。"""
    m = re.search(r"计算：(.+?)\s*=\s*（　）", stem)
    if m:
        return dstr(_eval(m.group(1)))
    m = re.search(r"把 ([\d.]+) 的小数点向右移动(一|两|二|三)位", stem)
    if m:
        return dstr(dec(m.group(1)).scaleb({"一": 1, "两": 2, "二": 2, "三": 3}[m.group(2)]))
    m = re.search(r"把 ([\d.]+) 的小数点向左移动(一|两|二|三)位", stem)
    if m:
        return dstr(dec(m.group(1)).scaleb(-{"一": 1, "两": 2, "二": 2, "三": 3}[m.group(2)]))
    for word, q in (("保留一位小数", "0.1"), ("保留两位小数", "0.01"), ("保留整数", "1")):
        m = re.search(r"把 ([\d.]+) " + word, stem)
        if m:
            return dstr(dec(m.group(1)).quantize(Decimal(q), rounding=ROUND_HALF_UP))
    m = re.search(r"([\d.]+) ≈ （　）（保留一位小数）", stem)
    if m:
        return dstr(dec(m.group(1)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
    m = re.search(r"(\d+) 米 (\d+) 厘米 = （　）米", stem)
    if m:
        return dstr(_q(int(m.group(1)) + int(m.group(2)) / 100))
    m = re.search(r"(\d+) 千克 (\d+) 克 = （　）千克", stem)
    if m:
        return dstr(_q(int(m.group(1)) + int(m.group(2)) / 1000))
    m = re.search(r"(\d+)\.(\d+) 米 = （　）厘米", stem)
    if m:
        return dstr(_q((int(m.group(1)) + int(m.group(2)) / 10 ** len(m.group(2))) * 100))
    m = re.search(r"(\d+) 元 (\d+) 角 = （　）元", stem)
    if m:
        return dstr(_q(int(m.group(1)) + int(m.group(2)) / 10))
    m = re.search(r"(\d+) 分米 = （　）米", stem)
    if m:
        return dstr(_q(int(m.group(1)) / 10))
    m = re.search(r"(\d+) 克 = （　）千克", stem)
    if m:
        return dstr(_q(int(m.group(1)) / 1000))
    m = re.search(r"∠1 = (\d+)°，∠2 = (\d+)°", stem)
    if m:
        return dstr(180 - int(m.group(1)) - int(m.group(2)))
    m = re.search(r"顶角是 (\d+)°，它的一个底角", stem)
    if m:
        return dstr((180 - int(m.group(1))) // 2)
    m = re.search(r"一个锐角是 (\d+)°，另一个锐角", stem)
    if m:
        return dstr(90 - int(m.group(1)))
    m = re.search(r"等边三角形的边长是 (\d+) 厘米", stem)
    if m:
        return dstr(int(m.group(1)) * 3)
    for pat, fn in (
        (r"成绩分别是 ([\d、]+) 分，平均成绩", None),
        (r"([\d、]+) 这 (\d+) 个数的平均数", None),
        (r"捐款分别是 ([\d、]+) 元，平均每人", None),
    ):
        m = re.search(pat, stem)
        if m:
            nums = [int(x) for x in m.group(1).split("、")]
            return dstr(_q(sum(nums) / len(nums)))
    m = re.search(r"(\d+) 个数的平均数是 (\d+)，这", stem)
    if m:
        return dstr(int(m.group(1)) * int(m.group(2)))
    m = re.search(r"共 (\d+) 只，一共有 (\d+) 只脚", stem)
    if m:
        heads, feet = int(m.group(1)), int(m.group(2))
        if "鸡有（　）" in stem:
            return dstr((4 * heads - feet) // 2)
        if "兔有（　）" in stem:
            return dstr((feet - 2 * heads) // 2)
        if "鸡比兔多" in stem:
            return dstr((4 * heads - feet) // 2 - (feet - 2 * heads) // 2)
    for pat, fn in (
        (r"已知两个加数的和是 (\d+)，其中一个加数是 (\d+)，另一个加数是", lambda a, b: a - b),
        (r"被减数是 (\d+)，差是 (\d+)，减数是", lambda a, b: a - b),
        (r"减数是 (\d+)，差是 (\d+)，被减数是", lambda a, b: a + b),
    ):
        m = re.search(pat, stem)
        if m:
            return dstr(fn(int(m.group(1)), int(m.group(2))))
    for pat, fn in (
        (r"两个因数的积是 (\d+)，其中一个因数是 (\d+)，另一个因数是", lambda a, b: a // b),
        (r"被除数是 (\d+)，商是 (\d+)，除数是", lambda a, b: a // b),
        (r"除数是 (\d+)、商是 (\d+)，那么被除数是", lambda a, b: a * b),
    ):
        m = re.search(pat, stem)
        if m:
            return dstr(fn(int(m.group(1)), int(m.group(2))))
    m = re.search(r"根据加法交换律：(\d+) \+ (\d+) = (\d+) \+ （　）", stem)
    if m:
        return m.group(1)
    m = re.search(r"根据加法结合律：\((\d+) \+ (\d+)\) \+ (\d+) = ", stem)
    if m:
        return m.group(3)
    m = re.search(r"根据乘法交换律：(\d+) × (\d+) = (\d+) × （　）", stem)
    if m:
        return m.group(1)
    m = re.search(r"根据乘法结合律：\((\d+) × (\d+)\) × (\d+) = ", stem)
    if m:
        return m.group(3)
    m = re.search(r"根据乘法分配律：\((\d+) \+ (\d+)\) × (\d+) = ", stem)
    if m:
        return m.group(3)
    for pat in (r"与 ([\d.]+) 相等的小数是", r"([\d.]+) 化简后是", r"去掉 ([\d.]+) 末尾的 0"):
        m = re.search(pat, stem)
        if m:
            return dstr(dec(m.group(1)))
    m = re.search(r"比较大小：([\d.]+) ○ ([\d.]+)", stem)
    if m:
        a, b = dec(m.group(1)), dec(m.group(2))
        return ">" if a > b else ("<" if a < b else "=")
    m = re.search(r"([\d.]+) 中，百分位上的数字是", stem)
    if m:
        return m.group(1).split(".")[1][1]
    m = re.search(r"([\d.]+) 中，十分位上的数字是", stem)
    if m:
        return m.group(1).split(".")[1][0]
    m = re.search(r"0\.(\d\d) 里面有 \d+ 个（　）", stem)
    if m:
        return "0.01"
    m = re.search(r"(\d+) 个 0\.1 和 (\d+) 个 0\.01 组成的数是", stem)
    if m:
        return dstr(_q(int(m.group(1)) / 10 + int(m.group(2)) / 100))
    m = re.search(r"把 (\d+) 米平均分成 10 份，每份是（　）米", stem)
    if m:
        return dstr(_q(int(m.group(1)) / 10))
    m = re.search(r"把 1 米平均分成 100 份，每份是（　）米", stem)
    if m:
        return "0.01"
    m = re.search(r"十分之(\d+) 写成小数是", stem)
    if m:
        return dstr(_q(int(m.group(1)) / 10))
    m = re.search(r"一支钢笔 (\d+) 元，买 (\d+) 支一共要", stem)
    if m:
        return dstr(int(m.group(1)) * int(m.group(2)))
    m = re.search(r"汽车每小时行 (\d+) 千米，(\d+) 小时行", stem)
    if m:
        return dstr(int(m.group(1)) * int(m.group(2)))
    m = re.search(r"妈妈带了 (\d+) 元，买了 (\d+) 元的东西，还剩", stem)
    if m:
        return dstr(int(m.group(1)) - int(m.group(2)))
    m = re.search(r"四（1）班有 (\d+) 人，四（2）班比四（1）班多 (\d+) 人，两个班一共有", stem)
    if m:
        return dstr(2 * int(m.group(1)) + int(m.group(2)))
    m = re.search(r"(\d+) 个同学，每人分 (\d+) 本练习本，一共需要", stem)
    if m:
        return dstr(int(m.group(1)) * int(m.group(2)))
    m = re.search(r"一个三角形的两个内角分别是 (\d+)° 和 (\d+)°，第三个内角是 (\d+)°，按角分这是一个（　）三角形", stem)
    if m:
        mx = max(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        return "直角" if mx == 90 else ("钝角" if mx > 90 else "锐角")
    m = re.search(r"一班 (\d+)/(\d+)、二班 (\d+)/(\d+)、三班 (\d+)/(\d+)、四班 (\d+)/(\d+)（男/女人数）", stem)
    if m:
        b = [int(m.group(i)) for i in (1, 3, 5, 7)]
        g = [int(m.group(i)) for i in (2, 4, 6, 8)]
        names = ["一班", "二班", "三班", "四班"]
        if "男生人数最多" in stem:
            return names[b.index(max(b))]
        if "女生人数最少" in stem:
            return names[g.index(min(g))]
        if "合计人数最多" in stem:
            tot = [b[i] + g[i] for i in range(4)]
            return names[tot.index(max(tot))]
        if "四个班一共有" in stem:
            return dstr(sum(b) + sum(g))
    if "的末尾添上一个 0，这个数（　）" in stem:
        return "大小不变"
    m = re.search(r"([\d.]+) 与 ([\d.]+) 的关系是（　）", stem)
    if m:
        return "相等" if dec(m.group(1)) == dec(m.group(2)) else "不相等"
    m = re.search(r"一个三角形的两条边分别是 (\d+) 厘米和 (\d+) 厘米，第三条边可能是（　）厘米", stem)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        lo, hi = abs(a - b), a + b
        return "range(%d,%d)" % (lo + 1, hi)      # 特殊：区间校验
    return None


def verify(units):
    total = good = bad = skipped = 0
    bads = []
    for unit, lessons in units:
        for lesson, _b, qs in lessons:
            for t, stem, opts, ans in qs:
                total += 1
                try:
                    exp = expect(stem)
                except Exception as e:  # noqa: BLE001
                    bads.append((lesson, stem, "解析异常:" + str(e), opts[0]))
                    bad += 1
                    continue
                if exp is None:
                    skipped += 1
                    continue
                got = opts[0]
                if exp.startswith("range("):
                    lo, hi = [int(x) for x in exp[6:-1].split(",")]
                    right = (lo <= int(got) < hi)
                else:
                    try:
                        right = dec(exp) == dec(got)
                    except Exception:  # noqa: BLE001
                        right = str(exp).strip() == str(got).strip()
                if right:
                    good += 1
                else:
                    bad += 1
                    bads.append((lesson, stem, exp, got))
    print("自动验算：共 %d 题，验算 %d 题（正确 %d / 错误 %d），未覆盖 %d 题"
          % (total, good + bad, good, bad, skipped))
    for lesson, stem, exp, got in bads[:20]:
        print("   ✗ %s | %s\n      期望 %s，实际 %s" % (lesson, stem[:70], exp, got))
    return 1 if bad else 0


# ---- 8) 生成 ----
UNIT_PREFIX = re.compile(r"^第[一二三四五六七八九十]+单元\s*")
LESSON_PREFIX = re.compile(r"^第(\d+)课\s*(.*)$")
CN_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
          "七": 7, "八": 8, "九": 9, "十": 10}
_SAFE_MAP = {ord("\\"): None, ord("/"): None, ord("*"): 0xFF0A, ord("?"): 0xFF1F,
             ord('"'): 0x201D, ord("<"): 0xFF1C, ord(">"): 0xFF1E,
             ord("|"): 0xFF5C, ord(":"): 0xFF1A}


def _safe(name):
    return name.translate(_SAFE_MAP).strip()


def _unit_dir(unit):
    m = UNIT_PREFIX.match(unit)
    name = unit[m.end():].strip() if m else unit.strip()
    no = CN_NUM.get(m.group(0)[1], 0) if m else 0
    return _safe("%02d-%s" % (no, name or unit.strip()))


def _lesson_file(lesson):
    m = LESSON_PREFIX.match(lesson)
    if not m:
        raise SystemExit("课名必须写成「第N课 名字」：%s" % lesson)
    return _safe("%02d-%s.html" % (int(m.group(1)), m.group(2).strip() or lesson))


if __name__ == "__main__":
    if "--verify" in sys.argv:
        sys.exit(verify(UNITS))
    os.makedirs(ARCHIVE, exist_ok=True)
    total = 0
    for unit, lessons in UNITS:
        udir = _unit_dir(unit)
        for lesson, broadcast, qs in lessons:
            subtitle = unit + " · " + lesson
            if LAYOUT == "content":
                out = os.path.join(ARCHIVE, udir, _lesson_file(lesson))
                os.makedirs(os.path.dirname(out), exist_ok=True)
            else:
                out = os.path.join(ARCHIVE, "四年级" + SUBJECT + " · " + subtitle + ".html")
            engine_build(subtitle, qs, broadcast, out, SUBJECT)
            total += 1
            print("生成 %2d | %-34s | %2d 题 | %s" %
                  (total, subtitle, len(qs), os.path.relpath(out, ARCHIVE)))
    print("完成：共生成 %d 个 HTML 文件（布局 %s）" % (total, LAYOUT))
    print("目录：%s" % ARCHIVE)
    if LAYOUT == "content":
        print("下一步：重启 StudyBuddy（content/ 只在启动时扫描一次），再刷新页面")
        print("        自检：go run ./tools/bankcheck")

