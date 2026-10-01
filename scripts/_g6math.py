# -*- coding: utf-8 -*-
"""六年级数学出题器（人教版上、下册共用）：程序化出题 + 题干反解自动验算。

约定（照 _g5math.py 的套路）：
  * 生成器 g_xxx(rng, mode) 返回 N(stem, ans, 干扰项) 打包好的题目；
    凑不出合适的数就返回 None，gen() 会自动重试；
  * expect_g6(stem) 按题干正则反解出数字并重算，手写概念题返回 None（跳过）；
  * verify(units) 遍历题库比对标注答案与重算结果，错误为 0 才允许生成 HTML；
  * selftest() 对每种模式抽查：保证「程序化出的题都能被 expect 反解」——
    否则那道题会被 verify 悄悄跳过，等于没验算。
"""
import math
import random
import re
from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction

from _g1math import N, gen  # noqa: F401  （gen 供生成脚本复用）


# ---------------- 通用小工具 ----------------
def D(x):
    return Decimal(str(x))


def fmt(v):
    """数值 → 去掉多余末尾 0 的十进制字符串。"""
    if isinstance(v, int):
        return str(v)
    s = format(v, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s or "0"


def r2(v):
    """保留两位小数（四舍五入），再去掉多余末尾 0。"""
    if isinstance(v, Fraction):
        val = Decimal(v.numerator) / Decimal(v.denominator)
    elif isinstance(v, bool):
        val = D(int(v))
    elif isinstance(v, (int, float)):
        val = D(v)
    else:
        val = v
    return fmt(val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _terminating(v):
    v = Fraction(v)
    t = v.denominator
    while t % 2 == 0:
        t //= 2
    while t % 5 == 0:
        t //= 5
    return t == 1


def dec_ans(v):
    """结果能写成有限小数就返回两位以内的小数串，否则返回 None（调用方重摇）。"""
    v = Fraction(v)
    if not _terminating(v):
        return None
    return r2(v)


def fs(v):
    """分数题答案：整数写整数，否则写最简分数。"""
    v = Fraction(v)
    return str(v.numerator) if v.denominator == 1 else str(v)


def rnum(v):
    """比值 / 小数题答案：整数或有限小数，否则最简分数。"""
    v = Fraction(v)
    if v.denominator == 1:
        return str(v.numerator)
    return r2(v) if _terminating(v) else str(v)


def rs(a, b):
    """最简整数比，写作 a:b。"""
    g = math.gcd(int(a), int(b))
    return "%d:%d" % (int(a) // g, int(b) // g)


def pick3(ans, cands):
    """取 3 个与答案不同、彼此不同的干扰项；不够就用常见错值补齐。"""
    s = str(ans)
    out, seen = [], {s}
    for c in cands:
        c = str(c)
        if c and c not in seen:
            seen.add(c)
            out.append(c)
            if len(out) == 3:
                return out
    try:
        v = Fraction(s)
        for cand in (v + 1, v * 2, v + Fraction(1, 2), v - 1, v * Fraction(1, 2)):
            if cand <= 0:
                continue
            c = fs(cand)
            if c not in seen:
                seen.add(c)
                out.append(c)
            if len(out) == 3:
                return out
    except (ValueError, ZeroDivisionError):
        pass
    i = 1
    while len(out) < 3:
        c = "%s%d" % (s, i)
        if c not in seen:
            seen.add(c)
            out.append(c)
        i += 1
    return out


# 常用数值池
_FR = [Fraction(1, 2), Fraction(1, 3), Fraction(2, 3), Fraction(1, 4), Fraction(3, 4),
       Fraction(1, 5), Fraction(2, 5), Fraction(3, 5), Fraction(4, 5),
       Fraction(1, 6), Fraction(5, 6), Fraction(1, 8), Fraction(3, 8), Fraction(5, 8),
       Fraction(7, 8), Fraction(2, 9), Fraction(4, 9), Fraction(5, 9), Fraction(7, 9)]
_FR25 = [Fraction(1, 2), Fraction(1, 4), Fraction(3, 4), Fraction(1, 5), Fraction(2, 5),
         Fraction(3, 5), Fraction(4, 5), Fraction(3, 10)]
_DEC = [Decimal("0.2"), Decimal("0.4"), Decimal("0.5"), Decimal("0.6"), Decimal("0.8"),
        Decimal("1.2"), Decimal("1.5"), Decimal("1.6"), Decimal("2.4"), Decimal("2.5"),
        Decimal("3.5"), Decimal("3.6"), Decimal("4.5")]
_SMALL = [2, 3, 4, 5, 6, 8, 9, 10, 12, 15, 16, 18, 20, 24, 25, 30, 36, 40, 45, 48, 50, 60, 80]

_CN = "零一二三四五六七八九"
_CNSET = dict((c, i) for i, c in enumerate(_CN))


def cn2(n):
    """1~100 的中文写法（用于百分数的读法）。"""
    n = int(n)
    if n == 100:
        return "一百"
    if n < 10:
        return _CN[n]
    if n < 20:
        return "十" + (_CN[n % 10] if n % 10 else "")
    return _CN[n // 10] + "十" + (_CN[n % 10] if n % 10 else "")


def cn_parse(s):
    """cn2 的逆：把「三十五」还原成 35。"""
    if s == "一百":
        return 100
    if "十" in s:
        a, b = s.split("十", 1)
        tens = 1 if a == "" else _CNSET.get(a)
        ones = 0 if b == "" else _CNSET.get(b)
        if tens is None or ones is None:
            return None
        return tens * 10 + ones
    return _CNSET.get(s)


def FR(s):
    """'3/4' → Fraction（expect 里用）。"""
    return Fraction(s)


def pctf(x):
    """百分数化分数：'2.5' → 2.5/100。"""
    return Fraction(D(x)) / 100


def dv(a, b):
    """小数相除（Decimal 不能直接做 Fraction(a, b)）。"""
    return Fraction(D(a)) / Fraction(D(b))


OPP_DIR = {"北偏东": "南偏西", "南偏西": "北偏东", "北偏西": "南偏东", "南偏东": "北偏西"}
ALT_DIR = {"北偏东": "东偏北", "北偏西": "西偏北", "南偏东": "东偏南", "南偏西": "西偏南"}
OPP_DIR2 = {"东": "西", "西": "东", "南": "北", "北": "南"}


# ---------------- 上册 1：分数乘法 ----------------
def g_fmul(rng, mode):
    if mode == "int":
        f = rng.choice(_FR)
        k = rng.choice([2, 3, 4, 5, 6, 8, 9, 10, 12])
        v = f * k
        ans = fs(v)
        n, d = f.numerator, f.denominator
        cands = ["%d/%d" % (n * k, d), "%d/%d" % (n, d * k), fs(f + k),
                 "%d/%d" % (n + k, d), fs(v * 2)]
        return N("计算：%s × %d = （　）" % (f, k), ans, pick3(ans, cands))
    if mode == "frac":
        f1, f2 = rng.choice(_FR), rng.choice(_FR)
        v = f1 * f2
        ans = fs(v)
        n1, d1, n2, d2 = f1.numerator, f1.denominator, f2.numerator, f2.denominator
        cands = ["%d/%d" % (n1 * n2, d1 * d2), fs(f1 + f2),
                 "%d/%d" % (n1 + n2, d1 + d2), fs(v * 2)]
        return N("计算：%s × %s = （　）" % (f1, f2), ans, pick3(ans, cands))
    if mode == "dec":
        d = rng.choice(_DEC)
        f = rng.choice(_FR25)
        v = Fraction(D(d)) * f
        ans = rnum(v)
        cands = [fs(v), rnum(v * 2), rnum(v + 1), rnum(Fraction(D(d)) + f)]
        return N("计算：%s × %s = （　）" % (fmt(d), f), ans, pick3(ans, cands))
    if mode == "mix":
        k = rng.randint(0, 4)
        if k == 0:
            f1, f2, f3 = rng.choice(_FR), rng.choice(_FR), rng.choice(_FR)
            v = f1 * f2 + f3
            ans = fs(v)
            return N("计算：%s × %s + %s = （　）" % (f1, f2, f3), ans,
                     pick3(ans, [fs(v * 2), fs(v + 1), fs(f1 * f2 - f3) if f1 * f2 > f3 else
                                 fs(f1 * f2 * f3), fs(f1 * f2)]))
        if k == 1:
            f1, f2, f3 = rng.choice(_FR), rng.choice(_FR), rng.choice(_FR)
            v = f1 * f2 - f3
            if v <= 0:
                return None
            ans = fs(v)
            return N("计算：%s × %s - %s = （　）" % (f1, f2, f3), ans,
                     pick3(ans, [fs(v * 2), fs(v + 1), fs(f1 * f2), fs(f1 * f3 - f2)]))
        if k == 2:
            f1, f2, f3 = rng.choice(_FR), rng.choice(_FR), rng.choice(_FR)
            if f1 <= f2:
                return None
            v = (f1 - f2) * f3
            ans = fs(v)
            return N("计算：(%s - %s) × %s = （　）" % (f1, f2, f3), ans,
                     pick3(ans, [fs(v * 2), fs(v + 1), fs(f1 - f2), fs(f1 - f2 + f3)]))
        if k == 3:
            f1, f2 = rng.choice(_FR), rng.choice(_FR)
            v = 1 - f1 * f2
            ans = fs(v)
            return N("计算：1 - %s × %s = （　）" % (f1, f2), ans,
                     pick3(ans, [fs(f1 * f2), fs(v * 2), fs(f1 + f2 - v)]))
        f1, f2 = rng.choice(_FR), rng.choice(_FR)
        k2 = rng.choice([2, 3, 4, 6, 8, 9, 12])
        v = f1 * f2 * k2
        ans = fs(v)
        return N("计算：%s × %s × %d = （　）" % (f1, f2, k2), ans,
                 pick3(ans, [fs(v * 2), fs(f1 * f2), fs(f1 * f2 * (k2 + 1))]))
    if mode == "word":
        k = rng.randint(0, 3)
        f = rng.choice(_FR)
        base = rng.choice(_SMALL)
        if (Fraction(base) * f).denominator != 1:
            return None
        v = Fraction(base) * f
        ans = fs(v)
        cands = [fs(v + 1), fs(Fraction(base) - v), fs(base * 2 * f)]
        if k == 0:
            return N("一堆煤有 %d 吨，运走了它的 %s，运走了（　）吨。" % (base, f), ans,
                     pick3(ans, cands))
        if k == 1:
            return N("一条路长 %d 千米，已经修了它的 %s，已经修了（　）千米。" % (base, f),
                     ans, pick3(ans, cands))
        if k == 2:
            return N("六（1）班有 %d 人，男生人数占全班的 %s，男生有（　）人。" % (base, f),
                     ans, pick3(ans, cands))
        return N("一件商品原价 %d 元，现在降价 %s 出售，降低了（　）元。" % (base, f),
                 ans, pick3(ans, cands))
    return None


# ---------------- 上册 2：位置与方向（二） ----------------
def g_posdir(rng, mode):
    if mode == "pos":
        k = rng.randint(0, 3)
        d1 = rng.choice(["北偏东", "北偏西", "南偏东", "南偏西"])
        ang = rng.choice([15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70])
        if k == 0:
            ans = "%s %d°" % (OPP_DIR[d1], ang)
            return N("甲在乙的%s %d° 方向，那么乙在甲的（　）方向。" % (d1, ang), ans,
                     pick3(ans, ["%s %d°" % (d1, ang), "%s %d°" % (ALT_DIR[d1], ang),
                                 "%s %d°" % (OPP_DIR[d1], 90 - ang)]))
        if k == 1:
            dist = rng.choice([200, 300, 400, 500, 600, 800])
            ans = "%s %d°" % (OPP_DIR[d1], ang)
            return N("小明家在学校%s %d° 方向 %d 米处，以小明家为观测点，学校在小明家的（　）方向。"
                     % (d1, ang, dist), ans,
                     pick3(ans, ["%s %d°" % (d1, ang), "%s %d°" % (ALT_DIR[d1], ang),
                                 "%s %d°" % (OPP_DIR[d1], 90 - ang)]))
        if k == 2:
            unit = rng.choice([20, 30, 40, 50, 60])
            seg = rng.randint(2, 9)
            ans = unit * seg
            return N("在一幅路线图上，每段代表 %d 米，从 A 地到 B 地一共 %d 段，"
                     "A、B 两地相距（　）米。" % (unit, seg), ans,
                     pick3(ans, [ans + unit, ans - unit, unit + seg]))
        cm = rng.randint(2, 9)
        unit = rng.choice([50, 100, 200, 500])
        ans = cm * unit
        return N("在平面图上量得两地相距 %d 厘米，图上 1 厘米表示实际距离 %d 米，"
                 "两地实际相距（　）米。" % (cm, unit), ans,
                 pick3(ans, [ans + unit, ans // 10 or unit, cm + unit]))
    if mode == "route":
        k = rng.randint(0, 3)
        if k == 0:
            a, b = rng.choice(_SMALL) * 5, rng.choice(_SMALL) * 5
            ans = a + b
            return N("从 A 地出发，先向东走 %d 米到 B 地，再向北走 %d 米到 C 地，"
                     "一共走了（　）米。" % (a, b), ans, pick3(ans, [abs(a - b), ans + 10, a * b]))
        if k == 1:
            a, b = rng.choice(_SMALL) * 5, rng.choice(_SMALL) * 5
            ans = a + b
            return N("小玲从家出发向南走 %d 米到学校，再从学校向西走 %d 米到图书馆，"
                     "她一共走了（　）米。" % (a, b), ans,
                     pick3(ans, [abs(a - b), ans + 10, a]))
        if k == 2:
            d1 = rng.choice(["东", "西", "南", "北"])
            dist = rng.choice(_SMALL) * 5
            ans = OPP_DIR2[d1]
            return N("从甲地向%s走 %d 米到乙地，沿原路返回时应向（　）走 %d 米。"
                     % (d1, dist, dist), ans,
                     [c for c in ["东", "西", "南", "北"] if c != ans][:3])
        d1 = rng.choice(["东", "西", "南", "北"])
        d2 = rng.choice([c for c in ["东", "西", "南", "北"] if c != OPP_DIR2[d1]])
        a, b = rng.randint(2, 8), rng.randint(2, 8)
        unit = rng.choice([20, 30, 40, 50, 60])
        ans = (a + b) * unit
        return N("从起点出发，先向%s走 %d 段，再向%s走 %d 段，每段长 %d 米，"
                 "一共走了（　）米。" % (d1, a, d2, b, unit), ans,
                 pick3(ans, [(a + b) + unit, (a - b) * unit if a != b else unit, (a + b) * 2]))
    return None


# ---------------- 上册 3：分数除法 ----------------
def g_fdiv(rng, mode):
    if mode == "rev":
        k = rng.randint(0, 3)
        if k == 0:
            f = rng.choice([f for f in _FR if f.numerator != 1])
            ans = fs(1 / f)
            return N("%s 的倒数是（　）。" % f, ans,
                     pick3(ans, [str(f), "%d/%d" % (f.denominator + 1, f.numerator),
                                 "%d/%d" % (f.numerator, f.denominator + 1)]))
        if k == 1:
            n = rng.randint(2, 20)
            ans = fs(Fraction(1, n))
            return N("%d 的倒数是（　）。" % n, ans,
                     pick3(ans, [str(n), "0", fs(Fraction(n, n + 1))]))
        if k == 2:
            d = rng.choice([Decimal("0.2"), Decimal("0.25"), Decimal("0.4"), Decimal("0.5"),
                            Decimal("0.8"), Decimal("1.25"), Decimal("2.5")])
            ans = rnum(1 / Fraction(D(d)))
            return N("%s 的倒数是（　）。" % fmt(d), ans,
                     pick3(ans, [fmt(d), rnum(Fraction(D(d)) * 2), str(int(D(d) * 10))
                     if (D(d) * 10) % 1 == 0 else fmt(d)]))
        f = rng.choice([f for f in _FR if f.numerator != 1 and f.numerator != f.denominator])
        ans = fs(f)
        return N("一个数与 %s 互为倒数，这个数是（　）。" % fs(1 / f), ans,
                 pick3(ans, [fs(1 / f), fs(Fraction(f.denominator + 1, f.numerator)), "1"]))
    if mode == "int":
        f = rng.choice(_FR)
        k = rng.choice([2, 3, 4, 5, 6, 8, 9, 12])
        v = f / k
        ans = fs(v)
        n, d = f.numerator, f.denominator
        return N("计算：%s ÷ %d = （　）" % (f, k), ans,
                 pick3(ans, [fs(f * k), "%d/%d" % (n * k, d), "%d/%d" % (n, d * k)]))
    if mode == "frac":
        f1, f2 = rng.choice(_FR), rng.choice(_FR)
        if f1 == f2:
            return None
        v = f1 / f2
        ans = fs(v)
        return N("计算：%s ÷ %s = （　）" % (f1, f2), ans,
                 pick3(ans, [fs(f1 * f2), fs(f2 / f1), fs(f1 - f2) if f1 > f2 else fs(f2 - f1)]))
    if mode == "mix":
        k = rng.randint(0, 3)
        if k == 0:
            f1, f2, f3 = rng.choice(_FR), rng.choice(_FR), rng.choice(_FR)
            v = f1 / f2 * f3
            ans = fs(v)
            return N("计算：%s ÷ %s × %s = （　）" % (f1, f2, f3), ans,
                     pick3(ans, [fs(f1 * f2 * f3), fs(f1 / f2), fs(f1 * f2 / f3)]))
        if k == 1:
            f1, f2, f3 = rng.choice(_FR), rng.choice(_FR), rng.choice(_FR)
            v = f1 * f2 / f3
            ans = fs(v)
            return N("计算：%s × %s ÷ %s = （　）" % (f1, f2, f3), ans,
                     pick3(ans, [fs(f1 * f2 * f3), fs(f1 / f3), fs(f1 * f3 / f2)]))
        if k == 2:
            f1, f2, f3 = rng.choice(_FR), rng.choice(_FR), rng.choice(_FR)
            v = (f1 + f2) / f3
            ans = fs(v)
            return N("计算：(%s + %s) ÷ %s = （　）" % (f1, f2, f3), ans,
                     pick3(ans, [fs(f1 + f2), fs((f1 + f2) * f3), fs(v * 2)]))
        f1, f2 = rng.choice(_FR), rng.choice(_FR)
        n = rng.choice([2, 3, 4, 5, 6, 8])
        v = Fraction(n) / (f1 * f2)
        ans = fs(v)
        return N("计算：%d ÷ (%s × %s) = （　）" % (n, f1, f2), ans,
                 pick3(ans, [fs(n * f1 * f2), fs(n / f1), fs(n / f2)]))
    if mode == "word":
        k = rng.randint(0, 3)
        f = rng.choice(_FR)
        whole = rng.choice([10, 12, 15, 16, 18, 20, 24, 25, 30, 36, 40, 45, 48, 50, 60])
        part = Fraction(whole) * f
        if part.denominator != 1:
            return None
        ans = str(whole)
        cands = [str(int(part)), fs(Fraction(whole) + part), str(whole * 2)]
        if k == 0:
            return N("一个数的 %s 是 %d，这个数是（　）。" % (f, int(part)), ans,
                     pick3(ans, cands))
        if k == 1:
            return N("一桶食用油用去了它的 %s，正好用去 %d 千克，这桶油原来有（　）千克。"
                     % (f, int(part)), ans, pick3(ans, cands))
        if k == 2:
            return N("六（1）班男生有 %d 人，占全班人数的 %s，全班有（　）人。"
                     % (int(part), f), ans, pick3(ans, cands))
        return N("一件衣服降价后是原价的 %s，现价 %d 元，原价是（　）元。" % (f, int(part)),
                 ans, pick3(ans, cands))
    return None


# ---------------- 上册 4：比 ----------------
def g_ratio(rng, mode):
    if mode == "mean":
        k = rng.randint(0, 2)
        a = rng.randint(2, 60)
        b = rng.randint(2, 60)
        if a == b:
            return None
        ans = rs(a, b)
        if ans.count(":") and ans.split(":") == ["1", "1"]:
            return None
        if k == 0:
            return N("甲数是 %d，乙数是 %d，甲数与乙数的比是（　）。" % (a, b), ans,
                     pick3(ans, ["%d:%d" % (b, a), "%d:%d" % (a, b + 1), "%d:%d" % (a + 1, b)]))
        if k == 1:
            return N("六（1）班有男生 %d 人、女生 %d 人，男生人数与女生人数的比是（　）。"
                     % (a, b), ans,
                     pick3(ans, ["%d:%d" % (b, a), "%d:%d" % (a, b + 1), "%d:%d" % (a + 1, b)]))
        return N("一辆汽车 %d 小时行驶 %d 千米，路程与时间的比是（　）。" % (b, a), ans,
                 pick3(ans, ["%d:%d" % (b, a), "%d:%d" % (a, b + 1), "%d:%d" % (a + 1, b)]))
    if mode == "prop":
        k = rng.randint(0, 2)
        a, b = rng.randint(2, 9), rng.randint(2, 9)
        m = rng.choice([2, 3, 4, 5, 6, 10])
        if k == 0:
            ans = "%d:%d" % (a * m, b * m)
            return N("把 %d : %d 的前项和后项同时乘 %d，得到（　）。" % (a, b, m), ans,
                     pick3(ans, [rs(a * m, b * m), "%d:%d" % (a + m, b + m),
                                 "%d:%d" % (a * m, b)]))
        if k == 1:
            g = rng.choice([2, 3, 4, 5, 6])
            a2, b2 = a * g, b * g
            ans = rs(a2, b2)
            return N("把 %d : %d 的前项和后项同时除以 %d，得到（　）。" % (a2, b2, g), ans,
                     pick3(ans, ["%d:%d" % (a2, b2), "%d:%d" % (a2 - g, b2 - g),
                                 "%d:%d" % (a * g, b)]))
        ans = str(m)
        return N("%d : %d 的前项扩大到原来的 %d 倍，要使比值不变，后项也应扩大到原来的（　）倍。"
                 % (a, b, m), ans, pick3(ans, [str(a), str(b), str(m + 1)]))
    if mode == "simp":
        k = rng.randint(0, 2)
        a = rng.randint(2, 40)
        b = rng.randint(2, 40)
        g = rng.choice([2, 3, 4, 5, 6, 8])
        if a == b or math.gcd(a, b) == g:
            return None
        ans = rs(a * g, b * g)
        if k == 0:
            stem = "把 %d : %d 化成最简单的整数比是（　）。" % (a * g, b * g)
        elif k == 1:
            stem = "化简比：%d : %d = （　）。" % (a * g, b * g)
        else:
            stem = "%d : %d 化简后是（　）。" % (a * g, b * g)
        return N(stem, ans, pick3(ans, ["%d:%d" % (a * g, b * g), "%d:%d" % (a, b + 1),
                                        "%d:%d" % (a + 1, b)]))
    if mode == "alloc":
        k = rng.randint(0, 3)
        if k == 0:
            total = rng.choice([30, 40, 50, 60, 80, 90, 100, 120, 150])
            a, b = rng.randint(1, 5), rng.randint(1, 5)
            s = a + b
            if a == b or math.gcd(a, b) != 1 or total % s:
                return None
            ans = total * a // s
            stem = "把 %d 个球按 %d : %d 分给甲、乙两人，甲分得（　）个。" % (total, a, b)
            return N(stem, ans, pick3(ans, [total * b // s, total // s, total // 2]))
        if k == 1:
            total = rng.choice([30, 40, 50, 60, 80, 90, 100, 120, 150])
            a, b = rng.randint(1, 5), rng.randint(1, 5)
            s = a + b
            if a == b or math.gcd(a, b) != 1 or total % s:
                return None
            ans = total * b // s
            stem = "把 %d 棵树按 %d : %d 分给五年级和六年级，六年级分得（　）棵。" % (total, a, b)
            return N(stem, ans, pick3(ans, [total * a // s, total // s, total // 2]))
        if k == 2:
            total = rng.choice([20, 30, 40, 50, 60, 80, 100])
            a, b, c = 2, 3, 5
            s = a + b + c
            if total % s:
                return None
            who = rng.choice([("水泥", a), ("沙子", b), ("石子", c)])
            ans = total * who[1] // s
            return N("一种混凝土中水泥、沙子、石子的质量比是 2 : 3 : 5，"
                     "要配制 %d 吨这种混凝土，需要%s（　）吨。" % (total, who[0]), ans,
                     pick3(ans, [total // s, total // 3, total * 5 // s]))
        r = rng.choice([1, 2, 3, 4])
        parts = rng.choice([(1, 2, 3), (1, 1, 2), (2, 3, 4), (1, 3, 5), (1, 2, 5)])
        s = sum(parts)
        ans = 180 * max(parts) // s
        return N("一个三角形三个内角的度数比是 %d : %d : %d，最大的角是（　）度。"
                 % parts, ans, pick3(ans, [180 * min(parts) // s, 180 // s, 90]))
    return None


# ---------------- 上册 5：圆 ----------------
_PI = Fraction(314, 100)


def _pi(v):
    """π 取 3.14 时的结果（≤2 位小数才返回字符串）。"""
    return dec_ans(_PI * Fraction(v))


def g_circle(rng, mode):
    if mode == "know":
        k = rng.randint(0, 3)
        if k == 0:
            r = rng.randint(2, 20)
            ans = 2 * r
            return N("一个圆的半径是 %d 厘米，它的直径是（　）厘米。" % r, ans,
                     pick3(ans, [r, r * 3, r * 4]))
        if k == 1:
            d = 2 * rng.randint(2, 20)
            ans = d // 2
            return N("一个圆的直径是 %d 厘米，它的半径是（　）厘米。" % d, ans,
                     pick3(ans, [d, d * 2, d // 4 or 1]))
        if k == 2:
            ans = rs(2, 1)
            return N("在同一个圆里，直径和半径的比是（　）。", ans,
                     pick3(ans, ["1:2", "1:1", "4:1"]))
        return N("圆有（　）条对称轴。", "无数", ["1", "2", "4"])
    if mode == "circ":
        k = rng.randint(0, 2)
        if k == 0:
            r = rng.randint(1, 20)
            ans = _pi(2 * r)
            return N("一个圆的半径是 %d 厘米，它的周长是（　）厘米。（π 取 3.14）" % r, ans,
                     pick3(ans, [r2(_PI * r), r2(_PI * r * r), r2(_PI * 4 * r)]))
        if k == 1:
            d = rng.randint(2, 20)
            ans = _pi(d)
            return N("一个圆的直径是 %d 厘米，它的周长是（　）厘米。（π 取 3.14）" % d, ans,
                     pick3(ans, [r2(_PI * d * d), r2(_PI * d / 2), r2(_PI * 2 * d)]))
        r = rng.randint(1, 15)
        ans = _pi(2 * r)
        return N("一个圆形花坛的半径是 %d 米，绕花坛走一圈要走（　）米。（π 取 3.14）" % r, ans,
                 pick3(ans, [r2(_PI * r), r2(_PI * r * r), r2(_PI * 4 * r)]))
    if mode == "area":
        k = rng.randint(0, 2)
        if k == 0:
            r = rng.randint(1, 15)
            ans = _pi(r * r)
            return N("一个圆的半径是 %d 厘米，它的面积是（　）平方厘米。（π 取 3.14）" % r, ans,
                     pick3(ans, [r2(_PI * 2 * r), r2(_PI * r), r2(_PI * r * r * 2)]))
        if k == 1:
            r = rng.randint(1, 12)
            ans = _pi(r * r)
            return N("一个圆的直径是 %d 厘米，它的面积是（　）平方厘米。（π 取 3.14）" % (2 * r),
                     ans, pick3(ans, [r2(_PI * 2 * r), r2(_PI * 4 * r * r), r2(_PI * r * r / 2)]))
        R = rng.randint(4, 12)
        r = rng.randint(1, R - 1)
        ans = _pi(R * R - r * r)
        return N("一个环形垫片的外圆半径是 %d 厘米，内圆半径是 %d 厘米，"
                 "它的面积是（　）平方厘米。（π 取 3.14）" % (R, r), ans,
                 pick3(ans, [r2(_PI * R * R), r2(_PI * (R - r) ** 2), r2(_PI * (R + r) ** 2)]))
    if mode == "sector":
        k = rng.randint(0, 2)
        if k == 0:
            r = rng.randint(2, 12)
            ang = rng.choice([30, 45, 60, 90, 120, 180])
            ans = dec_ans(_PI * r * r * Fraction(ang, 360))
            if ans is None:
                return None
            return N("一个扇形的半径是 %d 厘米，圆心角是 %d°，它的面积是（　）平方厘米。"
                     "（π 取 3.14）" % (r, ang), ans,
                     pick3(ans, [r2(_PI * r * r), r2(_PI * 2 * r),
                                 r2(_PI * r * r * Fraction(ang, 180))]))
        if k == 1:
            r = rng.randint(2, 12)
            ang = rng.choice([30, 45, 60, 90, 120])
            ans = dec_ans(_PI * r * r * Fraction(ang, 360))
            if ans is None:
                return None
            return N("一个圆半径为 %d 分米的圆中，圆心角是 %d° 的扇形面积是（　）平方分米。"
                     "（π 取 3.14）" % (r, ang), ans,
                     pick3(ans, [r2(_PI * r * r), r2(_PI * r * r / 2), r2(_PI * r * 2)]))
        whole = rng.choice(["12.56", "28.26", "50.24", "78.5", "113.04"])
        ang = rng.choice([90, 120, 180, 60])
        ans = dec_ans(Fraction(D(whole)) * Fraction(ang, 360))
        if ans is None:
            return None
        return N("一个圆的面积是 %s 平方厘米，其中圆心角是 %d° 的扇形面积是（　）平方厘米。"
                 % (whole, ang), ans,
                 pick3(ans, [r2(Fraction(D(whole)) * Fraction(ang, 180)),
                             r2(Fraction(D(whole)) / 2), r2(Fraction(D(whole)) / 4)]))
    return None


# ---------------- 上册 6：百分数（一） ----------------
def g_pct1(rng, mode):
    if mode == "rw":
        k = rng.randint(0, 1)
        n = rng.randint(1, 100)
        if k == 0:
            ans = "%d%%" % n
            return N("百分之%s写作（　）。" % cn2(n), ans,
                     pick3(ans, ["%d%%" % (n + 1), "%s%%" % fmt(D(n) / 100), "%d" % n]))
        ans = "百分之%s" % cn2(n)
        return N("%d%% 读作（　）。" % n, ans,
                 pick3(ans, ["百分之%s" % cn2(n % 10 + 1), "百分之%s" % cn2((n + 10) % 100),
                             "一百分之%s" % cn2(n)]))
    if mode == "conv":
        k = rng.randint(0, 3)
        if k == 0:
            d = rng.choice([Decimal("0.35"), Decimal("0.6"), Decimal("0.08"), Decimal("1.25"),
                            Decimal("0.9"), Decimal("1.5"), Decimal("0.05"), Decimal("0.375")])
            ans = "%s%%" % fs(Fraction(D(d)) * 100)
            return N("把 %s 化成百分数是（　）。" % fmt(d), ans,
                     pick3(ans, ["%s%%" % fmt(d), "%s%%" % fmt(D(d) / 10), "%s%%" % fs(
                         Fraction(D(d)) * 10)]))
        if k == 1:
            f = rng.choice([Fraction(1, 2), Fraction(1, 4), Fraction(3, 4), Fraction(1, 5),
                            Fraction(3, 5), Fraction(4, 5), Fraction(2, 5), Fraction(1, 8),
                            Fraction(7, 10), Fraction(3, 20)])
            ans = "%s%%" % fs(f * 100)
            return N("把 %s 化成百分数是（　）。" % f, ans,
                     pick3(ans, ["%s%%" % fs(f * 10), "%s%%" % fs(f * 1000), "%s%%" % fs(f)]))
        if k == 2:
            n = rng.randint(1, 100)
            ans = fmt(D(n) / 100)
            return N("把 %d%% 化成小数是（　）。" % n, ans,
                     pick3(ans, [fmt(D(n)), fmt(D(n) / 10), fmt(D(n) / 1000)]))
        f = rng.choice([Fraction(1, 2), Fraction(1, 4), Fraction(3, 4), Fraction(1, 5),
                        Fraction(2, 5), Fraction(3, 5), Fraction(4, 5), Fraction(1, 8),
                        Fraction(3, 8), Fraction(7, 10)])
        ans = fs(f)
        n = int(f * 100) if (f * 100).denominator == 1 else None
        if n is None:
            return None
        return N("把 %d%% 化成分数是（　）。" % n, ans,
                 pick3(ans, [fs(f / 10), fs(f * 10), "%d/%d" % (int(f * 100), 1000)]))
    if mode == "rate":
        k = rng.randint(0, 2)
        total = rng.choice([20, 25, 40, 50, 80, 100, 200, 250, 400, 500])
        part = rng.randint(1, total - 1)
        r = Fraction(part * 100, total)
        if r.denominator != 1:
            return None
        ans = "%d%%" % int(r)
        if k == 0:
            return N("六（1）班有 %d 人，今天出勤 %d 人，今天的出勤率是（　）。"
                     % (total, part), ans,
                     pick3(ans, ["%d%%" % (int(r) + 1), "%d%%" % (part), "%d%%" % (100 - int(r))]))
        if k == 1:
            return N("科技小组做种子发芽试验，用 %d 粒种子做试验，有 %d 粒发芽，"
                     "发芽率是（　）。" % (total, part), ans,
                     pick3(ans, ["%d%%" % (int(r) + 1), "%d%%" % part, "%d%%" % (100 - int(r))]))
        return N("检验一批产品，合格的有 %d 件，这批产品共 %d 件，合格率是（　）。"
                 % (part, total), ans,
                 pick3(ans, ["%d%%" % (int(r) + 2), "%d%%" % part, "%d%%" % (100 - int(r))]))
    if mode == "of":
        k = rng.randint(0, 2)
        base = rng.choice([20, 40, 50, 80, 100, 120, 150, 200, 240, 300, 400, 500])
        p = rng.choice([5, 10, 15, 20, 25, 30, 40, 50, 60, 75, 80])
        v = Fraction(base) * Fraction(p, 100)
        if v.denominator != 1:
            return None
        ans = fs(v)
        if k == 0:
            return N("%d 的 %d%% 是（　）。" % (base, p), ans,
                     pick3(ans, [fs(v * 2), fs(v + base), fs(base - v)]))
        if k == 1:
            return N("六（2）班有 %d 人，其中 %d%% 的同学参加了书法小组，"
                     "参加书法小组的有（　）人。" % (base, p), ans,
                     pick3(ans, [fs(v * 2), fs(base - v), fs(v + 10)]))
        return N("一堆煤有 %d 吨，用去了 %d%%，用去了（　）吨。" % (base, p), ans,
                 pick3(ans, [fs(base - v), fs(v * 2), fs(v + 10)]))
    return None


# ---------------- 上册 7：扇形统计图 ----------------
def g_pie(rng):
    k = rng.randint(0, 2)
    if k == 0:
        total = rng.choice([40, 50, 80, 100, 200, 240, 300, 400, 500])
        p = rng.choice([10, 15, 20, 25, 30, 40, 50, 60])
        v = Fraction(total) * Fraction(p, 100)
        if v.denominator != 1:
            return None
        ans = fs(v)
        return N("一个扇形统计图表示六（1）班 %d 名同学最喜欢的运动项目，"
                 "其中喜欢乒乓球的占 %d%%，喜欢乒乓球的有（　）人。" % (total, p), ans,
                 pick3(ans, [fs(total - v), fs(v * 2), fs(v + 10)]))
    if k == 1:
        p = rng.choice([10, 15, 20, 25, 30, 40, 45, 50, 60, 75])
        ans = fs(Fraction(360) * Fraction(p, 100))
        return N("在一个扇形统计图中，某一项占总数的 %d%%，"
                 "它对应的扇形圆心角是（　）度。" % p, ans,
                 pick3(ans, [str(p), str(int(ans) * 2), str(360 - int(ans))]))
    total = rng.choice([200, 300, 400, 500, 600, 800])
    a, b = rng.choice([(25, 35), (30, 20), (40, 15), (20, 50), (45, 25)])
    va = Fraction(total) * Fraction(a, 100)
    if va.denominator != 1:
        return None
    ans = fs(va)
    return N("某校六年级有 %d 人，参加课外小组情况如扇形统计图所示，"
             "其中美术组占 %d%%，美术组有（　）人。" % (total, a), ans,
             pick3(ans, [fs(Fraction(total) * Fraction(b, 100)), fs(va * 2), fs(va + 10)]))


# ---------------- 上册 8：数学广角——数与形 ----------------
def g_ns(rng):
    k = rng.randint(0, 3)
    if k == 0:
        n = rng.randint(2, 9)
        odds = [2 * i + 1 for i in range(n)]
        ans = n * n
        return N("按规律计算：%s = （　）" % " + ".join(str(o) for o in odds), ans,
                 pick3(ans, [ans + n, n * (n + 1), 2 * n]))
    if k == 1:
        n = rng.randint(2, 9)
        odds = [2 * i + 1 for i in range(n)]
        ans = n * n
        return N("从 1 开始的连续奇数相加：%s = （　）" % " + ".join(str(o) for o in odds), ans,
                 pick3(ans, [n * (n + 1), ans + 1, ans - 1]))
    if k == 2:
        n = rng.randint(2, 12)
        ans = 3 * n + 1
        return N("用小棒摆正方形，摆 1 个用 4 根，摆 2 个用 7 根，摆 3 个用 10 根……"
                 "照这样摆 %d 个要用（　）根小棒。" % n, ans,
                 pick3(ans, [4 * n, 3 * n, 3 * n + 2]))
    n = rng.randint(2, 10)
    ans = n * n
    return N("观察下列数：1、4、9、16……照这样的规律，第 %d 个数是（　）。" % n, ans,
             pick3(ans, [2 * n, n * (n + 1), (n + 1) ** 2]))


# ---------------- 下册 1：负数 ----------------
def g_neg(rng, mode):
    if mode == "know":
        k = rng.randint(0, 2)
        if k == 0:
            t = rng.randint(1, 30)
            ans = "-%d" % t
            return N("某天的最低气温是零下 %d 摄氏度，记作（　）℃。" % t, ans,
                     pick3(ans, ["%d" % t, "-%d" % (t + 1), "0"]))
        if k == 1:
            money = rng.choice([100, 200, 300, 500, 800, 1200])
            ans = "-%d" % money
            return N("如果收入 500 元记作 +500 元，那么支出 %d 元记作（　）元。" % money, ans,
                     pick3(ans, ["+%d" % money, "%d" % money, "-%d" % (money + 100)]))
        dist = rng.choice([3, 4, 5, 6, 8, 10, 12, 15, 20])
        ans = "-%d" % dist
        return N("如果向东走 5 米记作 +5 米，那么向西走 %d 米记作（　）米。" % dist, ans,
                 pick3(ans, ["+%d" % dist, "%d" % dist, "-%d" % (dist + 1)]))
    if mode == "axis":
        k = rng.randint(0, 2)
        if k == 0:
            n = rng.randint(1, 10)
            side = rng.choice(["左", "右"])
            ans = str(-n) if side == "左" else str(n)
            return N("在数轴上，从 0 点向%s移动 %d 个单位长度，到达的点表示的数是（　）。"
                     % (side, n), ans,
                     pick3(ans, [str(n if side == "左" else -n), "0", str(n + 1)]))
        if k == 1:
            n = rng.randint(1, 10)
            ans = str(n)
            return N("在数轴上，表示 -%d 的点在原点左边，它与原点相距（　）个单位长度。" % n, ans,
                     pick3(ans, ["-%d" % n, "0", str(n + 1)]))
        a = rng.randint(1, 8)
        b = rng.randint(1, 8)
        ans = a + b + 1
        return N("在数轴上，从 -%d 到 +%d（含两端）一共有（　）个整数点。" % (a, b), ans,
                 pick3(ans, [a + b, a + b - 1, a + b + 2]))
    if mode == "cmp":
        a = rng.randint(-20, -1)
        b = rng.randint(-20, 20)
        if a == b:
            return None
        ans = "＞" if a > b else "＜"
        other = "＜" if ans == "＞" else "＞"
        return N("在 ○ 里填上「＞」或「＜」：%d ○ %d，○ 里应填（　）。" % (a, b), ans,
                 [other, "＝", "≈"])
    if mode == "word":
        k = rng.randint(0, 1)
        if k == 0:
            low = rng.randint(-20, -1)
            high = rng.randint(1, 25)
            ans = high - low
            return N("某地一天的最低气温是 %d ℃，最高气温是 %d ℃，"
                     "这一天的温差是（　）℃。" % (low, high), ans,
                     pick3(ans, [high + low, ans + 1, abs(low)]))
        low = rng.randint(-15, -1)
        up = rng.randint(2, 20)
        ans = low + up
        return N("某地早晨的气温是 %d ℃，中午上升了 %d ℃，中午的气温是（　）℃。"
                 % (low, up), ans, pick3(ans, [abs(low) + up, up - abs(low), ans + 1]))
    return None


# ---------------- 下册 2：百分数（二） ----------------
def g_pct2(rng, mode):
    if mode == "discount":
        k = rng.randint(0, 2)
        price = rng.choice([50, 80, 100, 120, 150, 180, 200, 240, 300, 360, 400, 500])
        zhe = rng.choice([Fraction(9, 10), Fraction(8, 10), Fraction(75, 100),
                          Fraction(7, 10), Fraction(6, 10), Fraction(95, 100),
                          Fraction(85, 100)])
        cn = {Fraction(9, 10): "九", Fraction(8, 10): "八", Fraction(75, 100): "七五",
              Fraction(7, 10): "七", Fraction(6, 10): "六", Fraction(95, 100): "九五",
              Fraction(85, 100): "八五"}[zhe]
        pay = Fraction(price) * zhe
        ansd = dec_ans(pay)
        if ansd is None:
            return None
        if k == 0:
            ans = ansd
            return N("一件商品原价 %d 元，现在打%s折出售，现价是（　）元。" % (price, cn), ans,
                     pick3(ans, [r2(pay * 2), r2(Fraction(price) - pay), r2(pay / 2)]))
        if k == 1:
            ans = dec_ans(Fraction(price) - pay)
            if ans is None:
                return None
            return N("一件商品原价 %d 元，打%s折出售，比原价便宜了（　）元。" % (price, cn), ans,
                     pick3(ans, [ansd, r2((Fraction(price) - pay) * 2), r2(Fraction(price) + pay)]))
        ans = ansd
        return N("一本原价 %d 元的书，现在按%s折销售，现在买要付（　）元。" % (price, cn), ans,
                 pick3(ans, [r2(pay * 2), r2(Fraction(price) - pay), r2(pay + 10)]))
    if mode == "cheng":
        k = rng.randint(0, 1)
        base = rng.choice([100, 200, 300, 400, 500, 600, 800, 1000, 1200])
        rate = rng.choice([Fraction(1, 10), Fraction(2, 10), Fraction(15, 100),
                           Fraction(25, 100), Fraction(3, 10)])
        cnc = {Fraction(1, 10): "一成", Fraction(2, 10): "二成", Fraction(15, 100): "一成五",
               Fraction(25, 100): "二成五", Fraction(3, 10): "三成"}[rate]
        v = Fraction(base) * rate
        ans = dec_ans(v)
        if ans is None:
            return None
        if k == 0:
            return N("某村去年收稻谷 %d 吨，今年比去年增产%s，今年比去年增产（　）吨。"
                     % (base, cnc), ans,
                     pick3(ans, [r2(v * 2), r2(Fraction(base) + v), r2(v / 2)]))
        return N("某农场去年收小麦 %d 吨，今年比去年减产%s，今年比去年减产（　）吨。"
                 % (base, cnc), ans,
                 pick3(ans, [r2(v * 2), r2(Fraction(base) - v), r2(v + 10)]))
    if mode == "tax":
        k = rng.randint(0, 1)
        amount = rng.choice([2000, 3000, 4000, 5000, 6000, 8000, 10000, 12000, 20000])
        rate = rng.choice([3, 5, 6, 10])
        v = Fraction(amount) * Fraction(rate, 100)
        ans = dec_ans(v)
        if ans is None:
            return None
        if k == 0:
            return N("一家饭店上个月的营业额是 %d 元，按营业额的 %d%% 缴纳营业税，"
                     "应缴纳营业税（　）元。" % (amount, rate), ans,
                     pick3(ans, [r2(v * 2), r2(Fraction(amount) - v), r2(v / 2)]))
        return N("某商店一个月的营业额是 %d 元，按 %d%% 的税率缴税，应缴纳（　）元税款。"
                 % (amount, rate), ans,
                 pick3(ans, [r2(v * 2), r2(Fraction(amount) + v), r2(v + 100)]))
    if mode == "interest":
        k = rng.randint(0, 1)
        money = rng.choice([1000, 2000, 3000, 4000, 5000, 6000, 8000, 10000])
        rate = rng.choice([Decimal("1.5"), Decimal("2.1"), Decimal("2.5"), Decimal("2.75"),
                           Decimal("3.0"), Decimal("1.75")])
        year = rng.choice([1, 2, 3])
        v = Fraction(D(money)) * pctf(rate) * year
        ans = dec_ans(v)
        if ans is None:
            return None
        if k == 0:
            return N("把 %d 元存入银行，定期 %d 年，年利率是 %s%%，到期时可得到利息（　）元。"
                     % (money, year, fmt(rate)), ans,
                     pick3(ans, [r2(v * 2), r2(Fraction(D(money)) + v), r2(v / 2)]))
        return N("妈妈存入银行 %d 元，存期 %d 年，年利率 %s%%，到期时连本带息一共可以取回（　）元。"
                 % (money, year, fmt(rate)), dec_ans(Fraction(D(money)) + v) or "0",
                 pick3(dec_ans(Fraction(D(money)) + v) or "0",
                       [r2(v), r2(Fraction(D(money)) * 2 + v), r2(Fraction(D(money)) - v)]))
    if mode == "shop":
        k = rng.randint(0, 1)
        price = rng.choice([100, 200, 300, 400, 500, 600, 800, 1000])
        zhe = rng.choice([Fraction(9, 10), Fraction(8, 10), Fraction(75, 100)])
        cn = {Fraction(9, 10): "九", Fraction(8, 10): "八", Fraction(75, 100): "七五"}[zhe]
        v = Fraction(price) * zhe
        ans = dec_ans(v)
        if ans is None:
            return None
        if k == 0:
            return N("甲商场一件标价 %d 元的商品打%s折销售，在甲商场买要付（　）元。"
                     % (price, cn), ans,
                     pick3(ans, [r2(v * 2), r2(Fraction(price) - v), r2(v + 50)]))
        n = int(Fraction(price) // 100)
        v2 = Fraction(price) - Fraction(n * 20)
        ans = dec_ans(v2)
        return N("乙商场开展「每满 100 元减 20 元」的活动，买一件标价 %d 元的商品，"
                 "实际要付（　）元。" % price, ans,
                 pick3(ans, [r2(v2 + 20), r2(v2 - 20), r2(v2 + 100)]))
    return None


# ---------------- 下册 3：圆柱与圆锥 ----------------
def g_cyl(rng, mode):
    if mode == "know":
        k = rng.randint(0, 1)
        r = rng.randint(1, 15)
        if k == 0:
            ans = dec_ans(_PI * 2 * r)
            return N("一个圆柱的底面半径是 %d 厘米，它的底面周长是（　）厘米。（π 取 3.14）" % r,
                     ans, pick3(ans, [r2(_PI * r), r2(_PI * r * r), r2(_PI * 4 * r)]))
        ans = dec_ans(_PI * r * r)
        return N("一个圆柱的底面积是（　）平方厘米，已知它的底面半径是 %d 厘米。（π 取 3.14）" % r,
                 ans, pick3(ans, [r2(_PI * 2 * r), r2(_PI * r * r * 2), r2(_PI * r)]))
    if mode == "surf":
        k = rng.randint(0, 2)
        r = rng.randint(1, 10)
        h = rng.randint(2, 15)
        if k == 0:
            ans = dec_ans(_PI * r * r * 2 + _PI * 2 * r * h)
            return N("一个圆柱的底面半径是 %d 厘米，高是 %d 厘米，它的表面积是（　）平方厘米。"
                     "（π 取 3.14）" % (r, h), ans,
                     pick3(ans, [r2(_PI * 2 * r * h), r2(_PI * r * r * 2),
                                 r2(_PI * r * r * 2 + _PI * 2 * r * h + _PI * r * r)]))
        if k == 1:
            ans = dec_ans(_PI * 2 * r * h)
            return N("一个圆柱的底面半径是 %d 厘米，高是 %d 厘米，它的侧面积是（　）平方厘米。"
                     "（π 取 3.14）" % (r, h), ans,
                     pick3(ans, [r2(_PI * r * h), r2(_PI * r * r * h), r2(_PI * 4 * r * h)]))
        ans = dec_ans(_PI * r * r + _PI * 2 * r * h)
        return N("一个圆柱形无盖水桶，底面半径是 %d 分米，高是 %d 分米，"
                 "做这个水桶至少需要（　）平方分米铁皮。（π 取 3.14）" % (r, h), ans,
                 pick3(ans, [r2(_PI * r * r * 2 + _PI * 2 * r * h), r2(_PI * 2 * r * h),
                             r2(_PI * r * r)]))
    if mode == "vol":
        k = rng.randint(0, 2)
        r = rng.randint(1, 10)
        h = rng.randint(2, 15)
        if k == 0:
            ans = dec_ans(_PI * r * r * h)
            return N("一个圆柱的底面半径是 %d 厘米，高是 %d 厘米，它的体积是（　）立方厘米。"
                     "（π 取 3.14）" % (r, h), ans,
                     pick3(ans, [r2(_PI * r * r), r2(_PI * 2 * r * h),
                                 r2(_PI * r * r * h * 2)]))
        if k == 1:
            ans = dec_ans(_PI * r * r * h)
            return N("一个圆柱的底面积是 %s 平方厘米，高是 %d 厘米，它的体积是（　）立方厘米。"
                     % (dec_ans(_PI * r * r), h), ans,
                     pick3(ans, [r2(_PI * r * r), r2(_PI * 2 * r * h), r2(_PI * r * r + h)]))
        ans = dec_ans(_PI * r * r * h)
        return N("一个圆柱形水杯，从里面量底面半径是 %d 厘米、高是 %d 厘米，"
                 "它的容积是（　）毫升。（π 取 3.14）" % (r, h), ans,
                 pick3(ans, [r2(_PI * r * r), r2(_PI * 2 * r * h), r2(_PI * r * r * h * 2)]))
    if mode == "cone":
        k = rng.randint(0, 2)
        r = rng.randint(1, 10)
        h = rng.randint(2, 15)
        if (r * r * h) % 3:
            return None
        v = _PI * r * r * Fraction(h, 3)
        ans = dec_ans(v)
        if ans is None:
            return None
        if k == 0:
            return N("一个圆锥的底面半径是 %d 厘米，高是 %d 厘米，它的体积是（　）立方厘米。"
                     "（π 取 3.14）" % (r, h), ans,
                     pick3(ans, [r2(_PI * r * r * h), r2(_PI * r * r * h / 2),
                                 r2(_PI * r * r * h / 6)]))
        if k == 1:
            return N("一个圆锥形沙堆，底面半径是 %d 米，高是 %d 米，它的体积是（　）立方米。"
                     "（π 取 3.14）" % (r, h), ans,
                     pick3(ans, [r2(_PI * r * r * h), r2(_PI * r * r), r2(_PI * r * h)]))
        base = dec_ans(_PI * r * r)
        return N("一个圆锥的底面积是 %s 平方厘米，高是 %d 厘米，它的体积是（　）立方厘米。"
                 % (base, h), ans,
                 pick3(ans, [r2(Fraction(D(base)) * h), r2(Fraction(D(base)) * h / 2),
                             r2(Fraction(D(base)) * h * 3)]))
    if mode == "word":
        k = rng.randint(0, 2)
        r = rng.randint(1, 10)
        h = rng.randint(2, 12)
        if k == 0:
            ans = dec_ans(_PI * r * r * h)
            return N("一个圆柱形粮囤，从里面量底面半径是 %d 米、高是 %d 米，"
                     "这个粮囤的容积是（　）立方米。（π 取 3.14）" % (r, h), ans,
                     pick3(ans, [r2(_PI * 2 * r * h), r2(_PI * r * r), r2(_PI * r * r * h * 2)]))
        if k == 1:
            if (r * r * h) % 3:
                return None
            ans = dec_ans(_PI * r * r * Fraction(h, 3))
            return N("一个圆锥形铅块，底面半径是 %d 厘米、高是 %d 厘米，"
                     "它的体积是（　）立方厘米。（π 取 3.14）" % (r, h), ans,
                     pick3(ans, [r2(_PI * r * r * h), r2(_PI * r * r * h / 6),
                                 r2(_PI * r * r)]))
        d = 2 * rng.randint(1, 8)
        h = rng.randint(2, 12)
        ans = dec_ans(_PI * 2 * (d // 2) * h)
        return N("一节圆柱形铁皮通风管，底面直径是 %d 分米、长 %d 分米，"
                 "做这样一节通风管至少需要（　）平方分米铁皮。（π 取 3.14）" % (d, h), ans,
                 pick3(ans, [r2(_PI * (d // 2) ** 2 * h), r2(_PI * d * h * 2),
                             r2(_PI * d * h)]))
    return None


# ---------------- 下册 4：比例 ----------------
def g_prop(rng, mode):
    if mode == "mean":
        k = rng.randint(0, 2)
        if k == 0:
            a, b = rng.randint(2, 40), rng.randint(2, 20)
            ans = rnum(Fraction(a, b))
            return N("%d : %d 的比值是（　）。" % (a, b), ans,
                     pick3(ans, [rnum(Fraction(b, a)), fs(Fraction(a, b)), str(a)]))
        if k == 1:
            d1 = rng.choice([Decimal("0.6"), Decimal("0.9"), Decimal("1.2"), Decimal("2.4"),
                             Decimal("3.6"), Decimal("0.8"), Decimal("1.5")])
            d2 = rng.choice([Decimal("0.2"), Decimal("0.3"), Decimal("0.4"), Decimal("0.6")])
            ans = rnum(Fraction(D(d1)) / Fraction(D(d2)))
            return N("%s : %s 的比值是（　）。" % (fmt(d1), fmt(d2)), ans,
                     pick3(ans, [rnum(Fraction(D(d2)) / Fraction(D(d1))), fmt(d1), fmt(d2)]))
        f1, f2 = rng.choice(_FR), rng.choice(_FR)
        if f1 == f2:
            return None
        ans = rnum(f1 / f2)
        return N("%s : %s 的比值是（　）。" % (f1, f2), ans,
                 pick3(ans, [rnum(f2 / f1), fs(f1 / f2), fs(f1 * f2)]))
    if mode == "basic":
        k = rng.randint(0, 1)
        b, c = rng.randint(2, 12), rng.randint(2, 12)
        a = rng.randint(2, 12)
        if (b * c) % a or a == b or a == c or b == c:
            return None
        d = b * c // a
        inner = b * c
        outer = a * d
        if k == 0:
            ans = inner
            return N("在比例 %d : %d = %d : %d 中，两个内项的积是（　）。" % (a, b, c, d), ans,
                     pick3(ans, [outer, b + c, abs(b - c)]))
        ans = outer
        return N("在比例 %d : %d = %d : %d 中，两个外项的积是（　）。" % (a, b, c, d), ans,
                 pick3(ans, [inner, a + d, abs(a - d)]))
    if mode == "solve":
        k = rng.randint(0, 2)
        if k == 0:
            a, b, c = rng.randint(2, 12), rng.randint(2, 12), rng.randint(2, 12)
            if (b * c) % a:
                return None
            ans = fs(Fraction(b * c, a))
            return N("解比例：%d : %d = %d : x，x = （　）。" % (a, b, c), ans,
                     pick3(ans, [a * c, a * b, b * c]))
        if k == 1:
            b, c, d = rng.randint(2, 12), rng.randint(2, 12), rng.randint(2, 12)
            if (b * c) % d:
                return None
            ans = fs(Fraction(b * c, d))
            return N("解比例：x : %d = %d : %d，x = （　）。" % (b, c, d), ans,
                     pick3(ans, [b * d, c * d, b + c]))
        a, b, c = rng.randint(2, 12), rng.randint(2, 12), rng.randint(2, 12)
        if (a * b) % c:
            return None
        ans = fs(Fraction(a * b, c))
        return N("解比例：%d : x = %d : %d，x = （　）。" % (a, c, b), ans,
                 pick3(ans, [a * c, b * c, a + b]))
    if mode == "direct":
        k = rng.randint(0, 1)
        if k == 0:
            v = rng.choice([40, 50, 60, 70, 80, 90])
            t1, s1 = 2, v * 2
            t2 = rng.randint(3, 9)
            ans = v * t2
            return N("一辆汽车每小时行驶 %d 千米，2 小时行驶 %d 千米，照这样的速度，"
                     "%d 小时行驶（　）千米。" % (v, s1, t2), ans,
                     pick3(ans, [ans + v, ans - v, v * t2 * 2]))
        n1, m1 = 3, rng.choice([6, 9, 12, 15])
        price = Fraction(m1, n1)
        n2 = rng.randint(2, 10)
        v = price * n2
        if v.denominator != 1:
            return None
        ans = fs(v)
        return N("买 %d 支同样的铅笔花 %d 元，照这样计算，买 %d 支要花（　）元。"
                 % (n1, m1, n2), ans, pick3(ans, [fs(v + m1), fs(v * 2), fs(n2 * m1)]))
    if mode == "inverse":
        k = rng.randint(0, 1)
        if k == 0:
            total = rng.choice([60, 72, 84, 90, 96, 108, 120, 144, 160])
            a = rng.choice([c for c in [2, 3, 4, 5, 6, 8, 9, 10, 12] if total % c == 0])
            n1 = total // a
            b = rng.choice([c for c in [2, 3, 4, 5, 6, 8, 9, 10, 12]
                            if c != a and total % c == 0])
            ans = total // b
            return N("一批货物每车装 %d 吨，正好装 %d 车；如果每车装 %d 吨，要装（　）车。"
                     % (a, n1, b), ans, pick3(ans, [n1, total // (a + b) or 2, ans + 2]))
        side = rng.choice([2, 3, 4, 5, 6])
        cnt = rng.choice([48, 72, 96, 108, 144, 192, 300])
        total = side * side * cnt
        side2 = rng.choice([c for c in [2, 3, 4, 5, 6] if c != side])
        if total % (side2 * side2):
            return None
        ans = total // (side2 * side2)
        return N("一间会议室用边长 %d 分米的方砖铺地需要 %d 块，改用边长 %d 分米的方砖，"
                 "需要（　）块。" % (side, cnt, side2), ans,
                 pick3(ans, [cnt, total // side2, ans + cnt // 4 or 1]))
    if mode == "scale":
        k = rng.randint(0, 1)
        if k == 0:
            unit = rng.choice([200000, 300000, 500000, 600000, 2000000, 4000000, 5000000,
                               8000000])
            cm = rng.randint(2, 9)
            ans = unit * cm // 100000
            return N("一幅地图的比例尺是 1:%d，图上 %d 厘米表示实际距离（　）千米。" % (unit, cm),
                     ans, pick3(ans, [ans * 10, ans // 10 or 1, unit // 100000]))
        unit = rng.choice([200000, 500000, 600000, 1000000, 2000000, 4000000])
        km = rng.randint(2, 20) * (unit // 100000)
        ans = Fraction(km * 100000, unit)
        if ans.denominator != 1:
            return None
        return N("甲乙两地实际相距 %d 千米，画在比例尺是 1:%d 的地图上，图上距离是（　）厘米。"
                 % (km, unit), fs(ans),
                 pick3(fs(ans), [fs(ans * 10), fs(ans * 2), fs(ans + 1)]))
    if mode == "zoom":
        k = rng.randint(0, 2)
        n = rng.choice([2, 3, 4, 5, 6, 8, 10])
        if k == 0:
            ans = n
            return N("把一个长方形按 %d : 1 放大后，它的周长扩大到原来的（　）倍。" % n, ans,
                     pick3(ans, [n * n, n + 1, n * 2]))
        if k == 1:
            ans = n * n
            return N("把一个图形按 %d : 1 放大后，它的面积扩大到原来的（　）倍。" % n, ans,
                     pick3(ans, [n, n * 2, n * n * n]))
        ans = fs(Fraction(1, n * n))
        return N("把一个长方形的长和宽都缩小到原来的 1/%d，"
                 "它的面积缩小到原来的（　）。" % n, ans,
                 pick3(ans, [fs(Fraction(1, n)), fs(Fraction(1, 2 * n)),
                             fs(Fraction(1, n * n * 2))]))
    if mode == "word":
        k = rng.randint(0, 2)
        if k == 0:
            a = rng.choice([2, 3, 4, 5, 6, 8, 10])
            oil = rng.choice([Decimal("0.4"), Decimal("0.6"), Decimal("0.8"), Decimal("1.2"),
                              Decimal("1.5"), Decimal("2.4")])
            b = rng.choice([c for c in [5, 6, 8, 9, 10, 12, 15, 20] if c != a])
            v = Fraction(D(oil)) * Fraction(b, a)
            ans = rnum(v)
            return N("用 %d 千克大豆可以榨油 %s 千克，照这样计算，用 %d 千克大豆可以榨油（　）千克。"
                     % (a, fmt(oil), b), ans,
                     pick3(ans, [rnum(v * 2), rnum(v + 1), rnum(Fraction(D(oil)) + b)]))
        if k == 1:
            heights = rng.choice([(2, 6), (3, 12), (4, 8), (5, 15), (6, 12), (2.5, 7.5)])
            h1, s1 = heights
            h2 = rng.choice([3, 4, 5, 6, 8, 9, 10, 12, 15])
            if h2 == h1:
                return None
            v = Fraction(D(s1)) * dv(h2, h1)
            ans = rnum(v)
            return N("同一时间、同一地点，一根 %s 米高的竹竿的影子长 %s 米，"
                     "一棵 %d 米高的树的影子长（　）米。"
                     % (fmt(D(h1) / 2), fmt(D(s1) / 2), h2), ans,
                     pick3(ans, [rnum(v * 2), rnum(v + 1), str(h2)]))
        v_speed = rng.choice([40, 50, 60, 72, 80])
        t1, d1 = 2, v_speed * 2
        t2 = rng.randint(3, 9)
        ans = v_speed * t2
        return N("一辆汽车匀速行驶，2 小时行 %d 千米，照这样计算，行 %d 小时一共行（　）千米。"
                 % (d1, t2), ans, pick3(ans, [ans + v_speed, ans - v_speed, ans * 2]))
    return None


# ---------------- 下册 5：数学广角——鸽巢问题 ----------------
def g_pigeon(rng):
    k = rng.randint(0, 2)
    if k == 0:
        n = rng.randint(4, 30)
        m = rng.randint(2, 8)
        if n <= m:
            return None
        ans = -(-n // m)
        return N("%d 只鸽子飞进 %d 个鸽笼，总有一个鸽笼里至少飞进（　）只鸽子。" % (n, m), ans,
                 pick3(ans, [ans + 1, max(ans - 1, 1), n - m]))
    if k == 1:
        n = rng.randint(4, 30)
        m = rng.randint(2, 8)
        if n <= m:
            return None
        ans = -(-n // m)
        return N("把 %d 本书放进 %d 个抽屉，总有一个抽屉里至少放进（　）本书。" % (n, m), ans,
                 pick3(ans, [ans + 1, max(ans - 1, 1), n - m]))
    n = rng.randint(13, 40)
    ans = -(-n // 12)
    return N("六年级有 %d 名同学，他们中至少有（　）人是同一个月出生的。" % n, ans,
             pick3(ans, [ans + 1, max(ans - 1, 1), 12]))


# ---------------- 自动验算：题干反解重算 ----------------
def expect_g6(stem):
    """按题干反解重算；识别不了（手写概念题）返回 None，verify 会跳过。"""
    s = stem
    m = None

    # ---- 分数乘除法：四则模板（先复杂后简单，注意顺序） ----
    m = re.fullmatch(r"计算：1 - (\d+/\d+) × (\d+/\d+) = （　）", s)
    if m:
        return fs(1 - FR(m.group(1)) * FR(m.group(2)))
    m = re.fullmatch(r"计算：\((\d+/\d+) - (\d+/\d+)\) × (\d+/\d+) = （　）", s)
    if m:
        return fs((FR(m.group(1)) - FR(m.group(2))) * FR(m.group(3)))
    m = re.fullmatch(r"计算：\((\d+/\d+) \+ (\d+/\d+)\) ÷ (\d+/\d+) = （　）", s)
    if m:
        return fs((FR(m.group(1)) + FR(m.group(2))) / FR(m.group(3)))
    m = re.fullmatch(r"计算：(\d+) ÷ \((\d+/\d+) × (\d+/\d+)\) = （　）", s)
    if m:
        return fs(int(m.group(1)) / (FR(m.group(2)) * FR(m.group(3))))
    m = re.fullmatch(r"计算：(\d+/\d+) × (\d+/\d+) ([+\-]) (\d+/\d+) = （　）", s)
    if m:
        v = FR(m.group(1)) * FR(m.group(2))
        return fs(v + FR(m.group(4)) if m.group(3) == "+" else v - FR(m.group(4)))
    m = re.fullmatch(r"计算：(\d+/\d+) ÷ (\d+/\d+) ([×]) (\d+/\d+) = （　）", s)
    if m:
        return fs(FR(m.group(1)) / FR(m.group(2)) * FR(m.group(4)))
    m = re.fullmatch(r"计算：(\d+/\d+) × (\d+/\d+) ÷ (\d+/\d+) = （　）", s)
    if m:
        return fs(FR(m.group(1)) * FR(m.group(2)) / FR(m.group(3)))
    m = re.fullmatch(r"计算：(\d+/\d+) ÷ (\d+/\d+) = （　）", s)
    if m:
        return fs(FR(m.group(1)) / FR(m.group(2)))
    m = re.fullmatch(r"计算：(\d+/\d+) ÷ (\d+) = （　）", s)
    if m:
        return fs(FR(m.group(1)) / int(m.group(2)))
    m = re.fullmatch(r"计算：(\d+/\d+) × (\d+/\d+) × (\d+) = （　）", s)
    if m:
        return fs(FR(m.group(1)) * FR(m.group(2)) * int(m.group(3)))
    m = re.fullmatch(r"计算：(\d+/\d+) × (\d+/\d+) = （　）", s)
    if m:
        return fs(FR(m.group(1)) * FR(m.group(2)))
    m = re.fullmatch(r"计算：(\d+/\d+) × (\d+) = （　）", s)
    if m:
        return fs(FR(m.group(1)) * int(m.group(2)))
    m = re.fullmatch(r"计算：([\d.]+) × (\d+/\d+) = （　）", s)
    if m:
        return rnum(Fraction(D(m.group(1))) * FR(m.group(2)))

    # ---- 倒数 ----
    m = re.fullmatch(r"(\d+/\d+) 的倒数是（　）。", s)
    if m:
        return fs(1 / FR(m.group(1)))
    m = re.fullmatch(r"(\d+) 的倒数是（　）。", s)
    if m:
        return fs(Fraction(1, int(m.group(1))))
    m = re.fullmatch(r"([\d.]+) 的倒数是（　）。", s)
    if m:
        return rnum(1 / Fraction(D(m.group(1))))
    m = re.fullmatch(r"一个数与 (\d+/\d+) 互为倒数，这个数是（　）。", s)
    if m:
        return fs(1 / FR(m.group(1)))

    # ---- 分数乘法·解决问题 ----
    m = re.fullmatch(r"一堆煤有 (\d+) 吨，运走了它的 (\d+/\d+)，运走了（　）吨。", s)
    if m:
        return fs(int(m.group(1)) * FR(m.group(2)))
    m = re.fullmatch(r"一条路长 (\d+) 千米，已经修了它的 (\d+/\d+)，已经修了（　）千米。", s)
    if m:
        return fs(int(m.group(1)) * FR(m.group(2)))
    m = re.fullmatch(r"六（1）班有 (\d+) 人，男生人数占全班的 (\d+/\d+)，男生有（　）人。", s)
    if m:
        return fs(int(m.group(1)) * FR(m.group(2)))
    m = re.fullmatch(r"一件商品原价 (\d+) 元，现在降价 (\d+/\d+) 出售，降低了（　）元。", s)
    if m:
        return fs(int(m.group(1)) * FR(m.group(2)))

    # ---- 分数除法·解决问题 ----
    m = re.fullmatch(r"一个数的 (\d+/\d+) 是 (\d+)，这个数是（　）。", s)
    if m:
        return fs(int(m.group(2)) / FR(m.group(1)))
    m = re.fullmatch(r"一桶食用油用去了它的 (\d+/\d+)，正好用去 (\d+) 千克，这桶油原来有（　）千克。", s)
    if m:
        return fs(int(m.group(2)) / FR(m.group(1)))
    m = re.fullmatch(r"六（1）班男生有 (\d+) 人，占全班人数的 (\d+/\d+)，全班有（　）人。", s)
    if m:
        return fs(int(m.group(1)) / FR(m.group(2)))
    m = re.fullmatch(r"一件衣服降价后是原价的 (\d+/\d+)，现价 (\d+) 元，原价是（　）元。", s)
    if m:
        return fs(int(m.group(2)) / FR(m.group(1)))

    # ---- 位置与方向（二） ----
    m = re.fullmatch(r"甲在乙的(北偏东|北偏西|南偏东|南偏西) (\d+)° 方向，"
                     r"那么乙在甲的（　）方向。", s)
    if m:
        return "%s %s°" % (OPP_DIR[m.group(1)], m.group(2))
    m = re.fullmatch(r"小明家在学校(北偏东|北偏西|南偏东|南偏西) (\d+)° 方向 \d+ 米处，"
                     r"以小明家为观测点，学校在小明家的（　）方向。", s)
    if m:
        return "%s %s°" % (OPP_DIR[m.group(1)], m.group(2))
    m = re.fullmatch(r"在一幅路线图上，每段代表 (\d+) 米，从 A 地到 B 地一共 (\d+) 段，"
                     r"A、B 两地相距（　）米。", s)
    if m:
        return int(m.group(1)) * int(m.group(2))
    m = re.fullmatch(r"在平面图上量得两地相距 (\d+) 厘米，图上 1 厘米表示实际距离 (\d+) 米，"
                     r"两地实际相距（　）米。", s)
    if m:
        return int(m.group(1)) * int(m.group(2))
    m = re.fullmatch(r"从 A 地出发，先向东走 (\d+) 米到 B 地，再向北走 (\d+) 米到 C 地，"
                     r"一共走了（　）米。", s)
    if m:
        return int(m.group(1)) + int(m.group(2))
    m = re.fullmatch(r"小玲从家出发向南走 (\d+) 米到学校，再从学校向西走 (\d+) 米到图书馆，"
                     r"她一共走了（　）米。", s)
    if m:
        return int(m.group(1)) + int(m.group(2))
    m = re.fullmatch(r"从甲地向(东|西|南|北)走 (\d+) 米到乙地，沿原路返回时应向（　）走 \d+ 米。", s)
    if m:
        return OPP_DIR2[m.group(1)]
    m = re.fullmatch(r"从起点出发，先向(东|西|南|北)走 (\d+) 段，再向(东|西|南|北)走 (\d+) 段，"
                     r"每段长 (\d+) 米，一共走了（　）米。", s)
    if m:
        return (int(m.group(2)) + int(m.group(4))) * int(m.group(5))

    # ---- 比 ----
    m = re.fullmatch(r"甲数是 (\d+)，乙数是 (\d+)，甲数与乙数的比是（　）。", s)
    if m:
        return rs(m.group(1), m.group(2))
    m = re.fullmatch(r"六（1）班有男生 (\d+) 人、女生 (\d+) 人，男生人数与女生人数的比是（　）。", s)
    if m:
        return rs(m.group(1), m.group(2))
    m = re.fullmatch(r"一辆汽车 (\d+) 小时行驶 (\d+) 千米，路程与时间的比是（　）。", s)
    if m:
        return rs(m.group(2), m.group(1))
    m = re.fullmatch(r"把 (\d+) : (\d+) 的前项和后项同时乘 (\d+)，得到（　）。", s)
    if m:
        return "%d:%d" % (int(m.group(1)) * int(m.group(3)), int(m.group(2)) * int(m.group(3)))
    m = re.fullmatch(r"把 (\d+) : (\d+) 的前项和后项同时除以 (\d+)，得到（　）。", s)
    if m:
        return rs(m.group(1), m.group(2))
    m = re.fullmatch(r"\d+ : \d+ 的前项扩大到原来的 (\d+) 倍，要使比值不变，"
                     r"后项也应扩大到原来的（　）倍。", s)
    if m:
        return int(m.group(1))
    m = re.fullmatch(r"把 (\d+) : (\d+) 化成最简单的整数比是（　）。", s)
    if m:
        return rs(m.group(1), m.group(2))
    m = re.fullmatch(r"化简比：(\d+) : (\d+) = （　）。", s)
    if m:
        return rs(m.group(1), m.group(2))
    m = re.fullmatch(r"(\d+) : (\d+) 化简后是（　）。", s)
    if m:
        return rs(m.group(1), m.group(2))
    m = re.fullmatch(r"把 (\d+) 个球按 (\d+) : (\d+) 分给甲、乙两人，甲分得（　）个。", s)
    if m:
        total, a, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return total * a // (a + b)
    m = re.fullmatch(r"把 (\d+) 棵树按 (\d+) : (\d+) 分给五年级和六年级，六年级分得（　）棵。", s)
    if m:
        total, a, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return total * b // (a + b)
    m = re.fullmatch(r"一种混凝土中水泥、沙子、石子的质量比是 2 : 3 : 5，"
                     r"要配制 (\d+) 吨这种混凝土，需要(水泥|沙子|石子)（　）吨。", s)
    if m:
        total = int(m.group(1))
        part = {"水泥": 2, "沙子": 3, "石子": 5}[m.group(2)]
        return total * part // 10
    m = re.fullmatch(r"一个三角形三个内角的度数比是 (\d+) : (\d+) : (\d+)，最大的角是（　）度。", s)
    if m:
        parts = [int(m.group(1)), int(m.group(2)), int(m.group(3))]
        return 180 * max(parts) // sum(parts)

    # ---- 圆 ----
    m = re.fullmatch(r"一个圆的半径是 (\d+) 厘米，它的直径是（　）厘米。", s)
    if m:
        return 2 * int(m.group(1))
    m = re.fullmatch(r"一个圆的直径是 (\d+) 厘米，它的半径是（　）厘米。", s)
    if m:
        return int(m.group(1)) // 2
    m = re.fullmatch(r"在同一个圆里，直径和半径的比是（　）。", s)
    if m:
        return rs(2, 1)
    m = re.fullmatch(r"圆有（　）条对称轴。", s)
    if m:
        return "无数"
    m = re.fullmatch(r"一个圆的半径是 (\d+) 厘米，它的周长是（　）厘米。（π 取 3.14）", s)
    if m:
        return dec_ans(_PI * 2 * int(m.group(1)))
    m = re.fullmatch(r"一个圆的直径是 (\d+) 厘米，它的周长是（　）厘米。（π 取 3.14）", s)
    if m:
        return dec_ans(_PI * int(m.group(1)))
    m = re.fullmatch(r"一个圆形花坛的半径是 (\d+) 米，绕花坛走一圈要走（　）米。（π 取 3.14）", s)
    if m:
        return dec_ans(_PI * 2 * int(m.group(1)))
    m = re.fullmatch(r"一个圆的半径是 (\d+) 厘米，它的面积是（　）平方厘米。（π 取 3.14）", s)
    if m:
        r = int(m.group(1))
        return dec_ans(_PI * r * r)
    m = re.fullmatch(r"一个圆的直径是 (\d+) 厘米，它的面积是（　）平方厘米。（π 取 3.14）", s)
    if m:
        r = Fraction(int(m.group(1)), 2)
        return dec_ans(_PI * r * r)
    m = re.fullmatch(r"一个环形垫片的外圆半径是 (\d+) 厘米，内圆半径是 (\d+) 厘米，"
                     r"它的面积是（　）平方厘米。（π 取 3.14）", s)
    if m:
        R, r = int(m.group(1)), int(m.group(2))
        return dec_ans(_PI * (R * R - r * r))
    m = re.fullmatch(r"一个扇形的半径是 (\d+) 厘米，圆心角是 (\d+)°，它的面积是（　）平方厘米。"
                     r"（π 取 3.14）", s)
    if m:
        r, ang = int(m.group(1)), int(m.group(2))
        return dec_ans(_PI * r * r * Fraction(ang, 360))
    m = re.fullmatch(r"一个圆半径为 (\d+) 分米的圆中，圆心角是 (\d+)° 的扇形面积是（　）平方分米。"
                     r"（π 取 3.14）", s)
    if m:
        r, ang = int(m.group(1)), int(m.group(2))
        return dec_ans(_PI * r * r * Fraction(ang, 360))
    m = re.fullmatch(r"一个圆的面积是 ([\d.]+) 平方厘米，其中圆心角是 (\d+)° 的扇形面积是（　）"
                     r"平方厘米。", s)
    if m:
        return dec_ans(Fraction(D(m.group(1))) * Fraction(int(m.group(2)), 360))

    # ---- 百分数（一） ----
    m = re.fullmatch(r"百分之(\S+)写作（　）。", s)
    if m:
        n = cn_parse(m.group(1))
        return None if n is None else "%d%%" % n
    m = re.fullmatch(r"(\d+)% 读作（　）。", s)
    if m:
        return "百分之%s" % cn2(int(m.group(1)))
    m = re.fullmatch(r"把 ([\d.]+) 化成百分数是（　）。", s)
    if m:
        return "%s%%" % fs(Fraction(D(m.group(1))) * 100)
    m = re.fullmatch(r"把 (\d+/\d+) 化成百分数是（　）。", s)
    if m:
        return "%s%%" % fs(FR(m.group(1)) * 100)
    m = re.fullmatch(r"把 (\d+)% 化成小数是（　）。", s)
    if m:
        return fmt(D(int(m.group(1))) / 100)
    m = re.fullmatch(r"把 (\d+)% 化成分数是（　）。", s)
    if m:
        return fs(Fraction(int(m.group(1)), 100))
    m = re.fullmatch(r"六（1）班有 (\d+) 人，今天出勤 (\d+) 人，今天的出勤率是（　）。", s)
    if m:
        return "%d%%" % int(Fraction(int(m.group(2)) * 100, int(m.group(1))))
    m = re.fullmatch(r"科技小组做种子发芽试验，用 (\d+) 粒种子做试验，有 (\d+) 粒发芽，"
                     r"发芽率是（　）。", s)
    if m:
        return "%d%%" % int(Fraction(int(m.group(2)) * 100, int(m.group(1))))
    m = re.fullmatch(r"检验一批产品，合格的有 (\d+) 件，这批产品共 (\d+) 件，合格率是（　）。", s)
    if m:
        return "%d%%" % int(Fraction(int(m.group(1)) * 100, int(m.group(2))))
    m = re.fullmatch(r"(\d+) 的 (\d+)% 是（　）。", s)
    if m:
        return fs(int(m.group(1)) * Fraction(int(m.group(2)), 100))
    m = re.fullmatch(r"六（2）班有 (\d+) 人，其中 (\d+)% 的同学参加了书法小组，"
                     r"参加书法小组的有（　）人。", s)
    if m:
        return fs(int(m.group(1)) * Fraction(int(m.group(2)), 100))
    m = re.fullmatch(r"一堆煤有 (\d+) 吨，用去了 (\d+)%，用去了（　）吨。", s)
    if m:
        return fs(int(m.group(1)) * Fraction(int(m.group(2)), 100))

    # ---- 扇形统计图 ----
    m = re.fullmatch(r"一个扇形统计图表示六（1）班 (\d+) 名同学最喜欢的运动项目，"
                     r"其中喜欢乒乓球的占 (\d+)%，喜欢乒乓球的有（　）人。", s)
    if m:
        return fs(int(m.group(1)) * Fraction(int(m.group(2)), 100))
    m = re.fullmatch(r"在一个扇形统计图中，某一项占总数的 (\d+)%，它对应的扇形圆心角是（　）度。", s)
    if m:
        return fs(360 * Fraction(int(m.group(1)), 100))
    m = re.fullmatch(r"某校六年级有 (\d+) 人，参加课外小组情况如扇形统计图所示，"
                     r"其中美术组占 (\d+)%，美术组有（　）人。", s)
    if m:
        return fs(int(m.group(1)) * Fraction(int(m.group(2)), 100))

    # ---- 数学广角：数与形 ----
    m = re.fullmatch(r"按规律计算：(.+) = （　）", s)
    if m:
        vals = [int(x) for x in re.findall(r"\d+", m.group(1))]
        return sum(vals)
    m = re.fullmatch(r"从 1 开始的连续奇数相加：(.+) = （　）", s)
    if m:
        vals = [int(x) for x in re.findall(r"\d+", m.group(1))]
        return sum(vals)
    m = re.fullmatch(r"用小棒摆正方形，摆 1 个用 4 根，摆 2 个用 7 根，摆 3 个用 10 根……"
                     r"照这样摆 (\d+) 个要用（　）根小棒。", s)
    if m:
        return 3 * int(m.group(1)) + 1
    m = re.fullmatch(r"观察下列数：1、4、9、16……照这样的规律，第 (\d+) 个数是（　）。", s)
    if m:
        n = int(m.group(1))
        return n * n

    # ---- 负数 ----
    m = re.fullmatch(r"某天的最低气温是零下 (\d+) 摄氏度，记作（　）℃。", s)
    if m:
        return "-%s" % m.group(1)
    m = re.fullmatch(r"如果收入 500 元记作 \+500 元，那么支出 (\d+) 元记作（　）元。", s)
    if m:
        return "-%s" % m.group(1)
    m = re.fullmatch(r"如果向东走 5 米记作 \+5 米，那么向西走 (\d+) 米记作（　）米。", s)
    if m:
        return "-%s" % m.group(1)
    m = re.fullmatch(r"在数轴上，从 0 点向(左|右)移动 (\d+) 个单位长度，"
                     r"到达的点表示的数是（　）。", s)
    if m:
        n = int(m.group(2))
        return str(-n if m.group(1) == "左" else n)
    m = re.fullmatch(r"在数轴上，表示 -(\d+) 的点在原点左边，它与原点相距（　）个单位长度。", s)
    if m:
        return int(m.group(1))
    m = re.fullmatch(r"在数轴上，从 -(\d+) 到 \+(\d+)（含两端）一共有（　）个整数点。", s)
    if m:
        return int(m.group(1)) + int(m.group(2)) + 1
    m = re.fullmatch(r"在 ○ 里填上「＞」或「＜」：(-?\d+) ○ (-?\d+)，○ 里应填（　）。", s)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        return "＞" if a > b else "＜"
    m = re.fullmatch(r"某地一天的最低气温是 (-?\d+) ℃，最高气温是 (-?\d+) ℃，"
                     r"这一天的温差是（　）℃。", s)
    if m:
        return int(m.group(2)) - int(m.group(1))
    m = re.fullmatch(r"某地早晨的气温是 (-?\d+) ℃，中午上升了 (\d+) ℃，"
                     r"中午的气温是（　）℃。", s)
    if m:
        return int(m.group(1)) + int(m.group(2))

    # ---- 百分数（二） ----
    m = re.fullmatch(r"一件商品原价 (\d+) 元，现在打(九五|八五|七五|九|八|七|六)折出售，"
                     r"现价是（　）元。", s)
    if m:
        return dec_ans(int(m.group(1)) * zhe_val(m.group(2)))
    m = re.fullmatch(r"一件商品原价 (\d+) 元，打(九五|八五|七五|九|八|七|六)折出售，"
                     r"比原价便宜了（　）元。", s)
    if m:
        p = int(m.group(1))
        return dec_ans(Fraction(p) - Fraction(p) * zhe_val(m.group(2)))
    m = re.fullmatch(r"一本原价 (\d+) 元的书，现在按(九五|八五|七五|九|八|七|六)折销售，"
                     r"现在买要付（　）元。", s)
    if m:
        return dec_ans(int(m.group(1)) * zhe_val(m.group(2)))
    m = re.fullmatch(r"甲商场一件标价 (\d+) 元的商品打(九五|八五|七五|九|八|七|六)折销售，"
                     r"在甲商场买要付（　）元。", s)
    if m:
        return dec_ans(int(m.group(1)) * zhe_val(m.group(2)))
    m = re.fullmatch(r"乙商场开展「每满 100 元减 20 元」的活动，买一件标价 (\d+) 元的商品，"
                     r"实际要付（　）元。", s)
    if m:
        price = int(m.group(1))
        return dec_ans(Fraction(price) - Fraction(price // 100 * 20))
    m = re.fullmatch(r"某村去年收稻谷 (\d+) 吨，今年比去年增产(三成|二成五|一成五|二成|一成)，"
                     r"今年比去年增产（　）吨。", s)
    if m:
        return dec_ans(int(m.group(1)) * cheng_val(m.group(2)))
    m = re.fullmatch(r"某农场去年收小麦 (\d+) 吨，今年比去年减产(三成|二成五|一成五|二成|一成)，"
                     r"今年比去年减产（　）吨。", s)
    if m:
        return dec_ans(int(m.group(1)) * cheng_val(m.group(2)))
    m = re.fullmatch(r"一家饭店上个月的营业额是 (\d+) 元，按营业额的 (\d+)% 缴纳营业税，"
                     r"应缴纳营业税（　）元。", s)
    if m:
        return dec_ans(int(m.group(1)) * Fraction(int(m.group(2)), 100))
    m = re.fullmatch(r"某商店一个月的营业额是 (\d+) 元，按 (\d+)% 的税率缴税，"
                     r"应缴纳（　）元税款。", s)
    if m:
        return dec_ans(int(m.group(1)) * Fraction(int(m.group(2)), 100))
    m = re.fullmatch(r"把 (\d+) 元存入银行，定期 (\d+) 年，年利率是 ([\d.]+)%，"
                     r"到期时可得到利息（　）元。", s)
    if m:
        return dec_ans(Fraction(int(m.group(1))) * pctf(m.group(3))
                       * int(m.group(2)))
    m = re.fullmatch(r"妈妈存入银行 (\d+) 元，存期 (\d+) 年，年利率 ([\d.]+)%，"
                     r"到期时连本带息一共可以取回（　）元。", s)
    if m:
        v = Fraction(int(m.group(1))) * pctf(m.group(3)) * int(m.group(2))
        return dec_ans(Fraction(int(m.group(1))) + v)

    # ---- 圆柱与圆锥 ----
    m = re.fullmatch(r"一个圆柱的底面半径是 (\d+) 厘米，它的底面周长是（　）厘米。（π 取 3.14）", s)
    if m:
        return dec_ans(_PI * 2 * int(m.group(1)))
    m = re.fullmatch(r"一个圆柱的底面积是（　）平方厘米，已知它的底面半径是 (\d+) 厘米。"
                     r"（π 取 3.14）", s)
    if m:
        r = int(m.group(1))
        return dec_ans(_PI * r * r)
    m = re.fullmatch(r"一个圆柱的底面半径是 (\d+) 厘米，高是 (\d+) 厘米，"
                     r"它的表面积是（　）平方厘米。（π 取 3.14）", s)
    if m:
        r, h = int(m.group(1)), int(m.group(2))
        return dec_ans(_PI * r * r * 2 + _PI * 2 * r * h)
    m = re.fullmatch(r"一个圆柱的底面半径是 (\d+) 厘米，高是 (\d+) 厘米，"
                     r"它的侧面积是（　）平方厘米。（π 取 3.14）", s)
    if m:
        r, h = int(m.group(1)), int(m.group(2))
        return dec_ans(_PI * 2 * r * h)
    m = re.fullmatch(r"一个圆柱形无盖水桶，底面半径是 (\d+) 分米，高是 (\d+) 分米，"
                     r"做这个水桶至少需要（　）平方分米铁皮。（π 取 3.14）", s)
    if m:
        r, h = int(m.group(1)), int(m.group(2))
        return dec_ans(_PI * r * r + _PI * 2 * r * h)
    m = re.fullmatch(r"一个圆柱的底面半径是 (\d+) 厘米，高是 (\d+) 厘米，"
                     r"它的体积是（　）立方厘米。（π 取 3.14）", s)
    if m:
        r, h = int(m.group(1)), int(m.group(2))
        return dec_ans(_PI * r * r * h)
    m = re.fullmatch(r"一个圆柱的底面积是 ([\d.]+) 平方厘米，高是 (\d+) 厘米，"
                     r"它的体积是（　）立方厘米。", s)
    if m:
        return dec_ans(Fraction(D(m.group(1))) * int(m.group(2)))
    m = re.fullmatch(r"一个圆柱形水杯，从里面量底面半径是 (\d+) 厘米、高是 (\d+) 厘米，"
                     r"它的容积是（　）毫升。（π 取 3.14）", s)
    if m:
        r, h = int(m.group(1)), int(m.group(2))
        return dec_ans(_PI * r * r * h)
    m = re.fullmatch(r"一个圆锥的底面半径是 (\d+) 厘米，高是 (\d+) 厘米，"
                     r"它的体积是（　）立方厘米。（π 取 3.14）", s)
    if m:
        r, h = int(m.group(1)), int(m.group(2))
        return dec_ans(_PI * r * r * Fraction(h, 3))
    m = re.fullmatch(r"一个圆锥形沙堆，底面半径是 (\d+) 米，高是 (\d+) 米，"
                     r"它的体积是（　）立方米。（π 取 3.14）", s)
    if m:
        r, h = int(m.group(1)), int(m.group(2))
        return dec_ans(_PI * r * r * Fraction(h, 3))
    m = re.fullmatch(r"一个圆锥的底面积是 ([\d.]+) 平方厘米，高是 (\d+) 厘米，"
                     r"它的体积是（　）立方厘米。", s)
    if m:
        return dec_ans(Fraction(D(m.group(1))) * Fraction(int(m.group(2)), 3))
    m = re.fullmatch(r"一个圆柱形粮囤，从里面量底面半径是 (\d+) 米、高是 (\d+) 米，"
                     r"这个粮囤的容积是（　）立方米。（π 取 3.14）", s)
    if m:
        r, h = int(m.group(1)), int(m.group(2))
        return dec_ans(_PI * r * r * h)
    m = re.fullmatch(r"一个圆锥形铅块，底面半径是 (\d+) 厘米、高是 (\d+) 厘米，"
                     r"它的体积是（　）立方厘米。（π 取 3.14）", s)
    if m:
        r, h = int(m.group(1)), int(m.group(2))
        return dec_ans(_PI * r * r * Fraction(h, 3))
    m = re.fullmatch(r"一节圆柱形铁皮通风管，底面直径是 (\d+) 分米、长 (\d+) 分米，"
                     r"做这样一节通风管至少需要（　）平方分米铁皮。（π 取 3.14）", s)
    if m:
        r = Fraction(int(m.group(1)), 2)
        return dec_ans(_PI * 2 * r * int(m.group(2)))

    # ---- 比例 ----
    m = re.fullmatch(r"(\d+) : (\d+) 的比值是（　）。", s)
    if m:
        return rnum(Fraction(int(m.group(1)), int(m.group(2))))
    m = re.fullmatch(r"([\d.]+) : ([\d.]+) 的比值是（　）。", s)
    if m:
        return rnum(Fraction(D(m.group(1))) / Fraction(D(m.group(2))))
    m = re.fullmatch(r"(\d+/\d+) : (\d+/\d+) 的比值是（　）。", s)
    if m:
        return rnum(FR(m.group(1)) / FR(m.group(2)))
    m = re.fullmatch(r"在比例 (\d+) : (\d+) = (\d+) : (\d+) 中，两个内项的积是（　）。", s)
    if m:
        return int(m.group(2)) * int(m.group(3))
    m = re.fullmatch(r"在比例 (\d+) : (\d+) = (\d+) : (\d+) 中，两个外项的积是（　）。", s)
    if m:
        return int(m.group(1)) * int(m.group(4))
    m = re.fullmatch(r"解比例：(\d+) : (\d+) = (\d+) : x，x = （　）。", s)
    if m:
        return fs(Fraction(int(m.group(2)) * int(m.group(3)), int(m.group(1))))
    m = re.fullmatch(r"解比例：x : (\d+) = (\d+) : (\d+)，x = （　）。", s)
    if m:
        return fs(Fraction(int(m.group(1)) * int(m.group(2)), int(m.group(3))))
    m = re.fullmatch(r"解比例：(\d+) : x = (\d+) : (\d+)，x = （　）。", s)
    if m:
        return fs(Fraction(int(m.group(1)) * int(m.group(3)), int(m.group(2))))
    m = re.fullmatch(r"一辆汽车每小时行驶 (\d+) 千米，2 小时行驶 (\d+) 千米，照这样的速度，"
                     r"(\d+) 小时行驶（　）千米。", s)
    if m:
        return int(m.group(1)) * int(m.group(3))
    m = re.fullmatch(r"买 (\d+) 支同样的铅笔花 (\d+) 元，照这样计算，买 (\d+) 支要花（　）元。", s)
    if m:
        return fs(Fraction(int(m.group(2)), int(m.group(1))) * int(m.group(3)))
    m = re.fullmatch(r"一批货物每车装 (\d+) 吨，正好装 (\d+) 车；如果每车装 (\d+) 吨，"
                     r"要装（　）车。", s)
    if m:
        total = int(m.group(1)) * int(m.group(2))
        return total // int(m.group(3))
    m = re.fullmatch(r"一间会议室用边长 (\d+) 分米的方砖铺地需要 (\d+) 块，"
                     r"改用边长 (\d+) 分米的方砖，需要（　）块。", s)
    if m:
        total = int(m.group(1)) ** 2 * int(m.group(2))
        return total // (int(m.group(3)) ** 2)
    m = re.fullmatch(r"一幅地图的比例尺是 1:(\d+)，图上 (\d+) 厘米表示实际距离（　）千米。", s)
    if m:
        return int(m.group(1)) * int(m.group(2)) // 100000
    m = re.fullmatch(r"甲乙两地实际相距 (\d+) 千米，画在比例尺是 1:(\d+) 的地图上，"
                     r"图上距离是（　）厘米。", s)
    if m:
        return fs(Fraction(int(m.group(1)) * 100000, int(m.group(2))))
    m = re.fullmatch(r"把一个长方形按 (\d+) : 1 放大后，它的周长扩大到原来的（　）倍。", s)
    if m:
        return int(m.group(1))
    m = re.fullmatch(r"把一个图形按 (\d+) : 1 放大后，它的面积扩大到原来的（　）倍。", s)
    if m:
        n = int(m.group(1))
        return n * n
    m = re.fullmatch(r"把一个长方形的长和宽都缩小到原来的 1/(\d+)，"
                     r"它的面积缩小到原来的（　）。", s)
    if m:
        n = int(m.group(1))
        return fs(Fraction(1, n * n))
    m = re.fullmatch(r"用 (\d+) 千克大豆可以榨油 ([\d.]+) 千克，照这样计算，"
                     r"用 (\d+) 千克大豆可以榨油（　）千克。", s)
    if m:
        return rnum(Fraction(D(m.group(2))) * Fraction(int(m.group(3)), int(m.group(1))))
    m = re.fullmatch(r"同一时间、同一地点，一根 ([\d.]+) 米高的竹竿的影子长 ([\d.]+) 米，"
                     r"一棵 (\d+) 米高的树的影子长（　）米。", s)
    if m:
        return rnum(dv(m.group(2), m.group(1)) * int(m.group(3)))
    m = re.fullmatch(r"一辆汽车匀速行驶，2 小时行 (\d+) 千米，照这样计算，"
                     r"行 (\d+) 小时一共行（　）千米。", s)
    if m:
        return fs(Fraction(int(m.group(1)), 2) * int(m.group(2)))

    # ---- 鸽巢问题 ----
    m = re.fullmatch(r"(\d+) 只鸽子飞进 (\d+) 个鸽笼，总有一个鸽笼里至少飞进（　）只鸽子。", s)
    if m:
        return -(-int(m.group(1)) // int(m.group(2)))
    m = re.fullmatch(r"把 (\d+) 本书放进 (\d+) 个抽屉，总有一个抽屉里至少放进（　）本书。", s)
    if m:
        return -(-int(m.group(1)) // int(m.group(2)))
    m = re.fullmatch(r"六年级有 (\d+) 名同学，他们中至少有（　）人是同一个月出生的。", s)
    if m:
        return -(-int(m.group(1)) // 12)

    return None


ZHE = {"九": Fraction(9, 10), "八": Fraction(8, 10), "七": Fraction(7, 10),
       "六": Fraction(6, 10), "九五": Fraction(95, 100), "八五": Fraction(85, 100),
       "七五": Fraction(75, 100)}
CHENG = {"一成": Fraction(1, 10), "二成": Fraction(2, 10), "一成五": Fraction(15, 100),
         "二成五": Fraction(25, 100), "三成": Fraction(3, 10)}


def zhe_val(name):
    return ZHE[name]


def cheng_val(name):
    return CHENG[name]


def verify(units):
    """按题干反解重算，与标注答案比对（只查能被反解的题，手写概念题跳过）。"""
    total = 0
    bad = 0
    for uname, lessons in units:
        for lname, _bc, qs in lessons:
            for q in qs:
                stem = q[1]
                ans = str(q[2][0])
                v = expect_g6(stem)
                if v is None:
                    continue
                total += 1
                if str(v) != ans:
                    bad += 1
                    if bad <= 20:
                        print("答案错误: %s | %s | 期望 %s 标注 %s" % (lname, stem[:46], v, ans))
    if bad == 0:
        print("验算 %d/%d 全对" % (total, total))
    else:
        print("验算 %d/%d，错误 %d" % (total - bad, total, bad))
    return 0 if bad == 0 else 1


MODES = [("g_fmul", g_fmul, ["int", "frac", "dec", "mix", "word"]),
         ("g_posdir", g_posdir, ["pos", "route"]),
         ("g_fdiv", g_fdiv, ["rev", "int", "frac", "mix", "word"]),
         ("g_ratio", g_ratio, ["mean", "prop", "simp", "alloc"]),
         ("g_circle", g_circle, ["know", "circ", "area", "sector"]),
         ("g_pct1", g_pct1, ["rw", "conv", "rate", "of"]),
         ("g_pie", g_pie, [None]),
         ("g_ns", g_ns, [None]),
         ("g_neg", g_neg, ["know", "axis", "cmp", "word"]),
         ("g_pct2", g_pct2, ["discount", "cheng", "tax", "interest", "shop"]),
         ("g_cyl", g_cyl, ["know", "surf", "vol", "cone", "word"]),
         ("g_prop", g_prop, ["mean", "basic", "solve", "direct", "inverse", "scale", "zoom",
                             "word"]),
         ("g_pigeon", g_pigeon, [None])]


def selftest(n=20, seeds=(20260930, 4242, 777)):
    """抽查每种模式：确认出的题都能被 expect 反解，且重算结果与标注一致。"""
    total = missing = bad = 0
    for name, fn, modes in MODES:
        for mode in modes:
            args = (mode,) if mode is not None else ()
            for seed in seeds:
                try:
                    qs = gen(fn, n, seed, *args)
                except SystemExit as e:
                    print("出题不足：%s/%s seed=%s —— %s" % (name, mode, seed, e))
                    bad += 1
                    continue
                for q in qs:
                    total += 1
                    stem, opts = q[1], q[2]
                    v = expect_g6(stem)
                    if v is None:
                        missing += 1
                        if missing <= 15:
                            print("无法反解：%s/%s | %s" % (name, mode, stem[:50]))
                    elif str(v) != str(opts[0]):
                        bad += 1
                        if bad <= 15:
                            print("答案不符：%s/%s | %s | 期望 %s 标注 %s"
                                  % (name, mode, stem[:46], v, opts[0]))
                    if len(opts) != 4 or len(set(opts)) != 4:
                        print("选项异常：%s/%s | %s | %r" % (name, mode, stem[:40], opts))
    print("自检：共 %d 题；无法反解 %d；答案不符 %d" % (total, missing, bad))
    return 0 if (missing == 0 and bad == 0) else 1


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    print("本模块只提供给 build_math_g6v1_quiz.py / build_math_g6v2_quiz.py 使用")
