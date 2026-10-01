# -*- coding: utf-8 -*-
"""五年级数学出题器（上下册共用）：程序化出题 + 题干反解自动验算。

约定（照 _g3math.py 的套路）：
  * 生成器 g_xxx(rng, mode) 返回 N(stem, ans, 干扰项) 打包好的题目；
    凑不出合适的题就返回 None，gen() 会自动重试；
  * expect_g5(stem) 按题干正则反解出数字并重算，手写的概念题返回 None（跳过）；
  * verify(units) 遍历题库比对标注答案与重算结果，错误为 0 才允许生成 HTML。
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
    if isinstance(v, Fraction):
        return str(v)
    s = format(v, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s or "0"


def rnd(v, nd):
    """四舍五入到 nd 位小数（nd=0 保留整数），返回字符串（保留 nd 位小数的写法）。"""
    if nd <= 0:
        return str(v.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return str(v.quantize(Decimal(1).scaleb(-nd), rounding=ROUND_HALF_UP))


def nd_of(label):
    return {"整数": 0, "一位小数": 1, "两位小数": 2}[label]


def rd(rng, nd, lo, hi):
    """随机小数：nd 位小数，取值区间 [lo, hi]。"""
    scale = 10 ** nd
    return Decimal(rng.randint(lo * scale, hi * scale)) / scale


def dw(v):
    """小数题的 3 个常见错误干扰项：×10、÷10、+1。"""
    return [fmt(v * 10), fmt(v / 10), fmt(v + 1)]


def divisors(n):
    return [i for i in range(1, n + 1) if n % i == 0]


def is_prime(n):
    if n < 2:
        return False
    i = 2
    while i * i <= n:
        if n % i == 0:
            return False
        i += 1
    return True


def fw(f):
    """分数题的 3 个干扰项：分子±1、分母+1、分子分母颠倒（约分后去重）。"""
    base = str(f)
    cands = ["%d/%d" % (f.numerator + 1, f.denominator),
             "%d/%d" % (f.numerator, f.denominator + 1),
             "%d/%d" % (f.denominator, f.numerator)]
    if f.numerator - 1 >= 1:
        cands.append("%d/%d" % (f.numerator - 1, f.denominator))
    out = []
    for c in cands:
        v = str(Fraction(c))
        if v != base and v not in out:
            out.append(v)
    return out[:3]


# ---------------- 上册：小数乘法 ----------------
def g_dmul(rng, mode="int"):
    if mode == "int":                                   # 小数乘整数
        nd = rng.choice([1, 2])
        a = rd(rng, nd, 1, 9)
        if "." not in fmt(a):
            return None
        b = rng.randint(2, 12)
        p = a * b
        k = rng.randint(0, 2)
        if k == 0:
            return N("计算：%s × %d = （　）" % (fmt(a), b), fmt(p), dw(p))
        if k == 1:
            return N("计算：%d × %s = （　）" % (b, fmt(a)), fmt(p), dw(p))
        return N("每千克苹果 %s 元，买 %d 千克要付（　）元。" % (fmt(a), b), fmt(p), dw(p))
    if mode == "dec":                                   # 小数乘小数
        a = rd(rng, rng.choice([1, 2]), 1, 9)
        b = rd(rng, rng.choice([1, 2]), 1, 9)
        if "." not in fmt(a) or "." not in fmt(b):
            return None
        p = a * b
        k = rng.randint(0, 2)
        if k == 0:
            return N("计算：%s × %s = （　）" % (fmt(a), fmt(b)), fmt(p), dw(p))
        if k == 1:
            ndp = len(fmt(p).split(".")[1]) if "." in fmt(p) else 0
            return N("%s × %s 的积有（　）位小数。" % (fmt(a), fmt(b)), ndp,
                     [ndp + 1, max(ndp - 1, 0), ndp + 2])
        return N("一个长方形的长是 %s 米、宽是 %s 米，面积是（　）平方米。" % (fmt(a), fmt(b)), fmt(p), dw(p))
    if mode == "approx":                                # 积的近似数
        a = rd(rng, 2, 1, 9)
        b = rd(rng, rng.choice([1, 2]), 1, 9)
        if "." not in fmt(a) or "." not in fmt(b):
            return None
        p = a * b
        nd = rng.choice([0, 1, 2])
        label = {0: "整数", 1: "一位小数", 2: "两位小数"}[nd]
        ans = rnd(p, nd)
        ws = [w for w in [fmt(p), rnd(p * 10, nd), rnd(p + 1, nd), rnd(p / 10, nd)] if w != ans]
        return N("计算：%s × %s ≈ （　）（保留%s）。" % (fmt(a), fmt(b), label), ans, ws[:3])
    if mode == "law":                                   # 整数乘法运算定律推广到小数
        k = rng.randint(0, 2)
        if k == 0:
            a = rd(rng, 1, 1, 9); b = rd(rng, 1, 1, 9); c = rd(rng, 1, 1, 9)
            if "." not in fmt(a):
                return None
            p = a * (b + c)
            return N("用乘法分配律计算：%s × (%s + %s) = （　）。" % (fmt(a), fmt(b), fmt(c)), fmt(p),
                     [fmt(a * b + c), fmt(p + 1), fmt(p * 10)])
        if k == 1:
            a = rd(rng, 1, 1, 9); b = rd(rng, 1, 1, 9); c = rng.choice([2, 4, 5, 8])
            if "." not in fmt(a) or "." not in fmt(b):
                return None
            p = a * b * c
            return N("用乘法交换律和结合律计算：%s × %d × %s = （　）。" % (fmt(a), c, fmt(b)), fmt(p),
                     [fmt(a * b), fmt(p + 1), fmt(p * 10)])
        a = rng.randint(2, 9); b = rng.randint(2, 9); c = rd(rng, 1, 1, 9)
        if "." not in fmt(c):
            return None
        p = (a + b) * c
        return N("用乘法分配律计算：%d × %s + %d × %s = （　）。" % (a, fmt(c), b, fmt(c)), fmt(p),
                 [fmt(p + c), fmt(a * c), fmt(b * c)])
    # mode == "word"  解决问题
    k = rng.randint(0, 2)
    if k == 0:
        p = rd(rng, 2, 1, 9); n = rd(rng, 1, 1, 9)
        if "." not in fmt(p) or "." not in fmt(n):
            return None
        return N("苹果每千克 %s 元，买 %s 千克应付（　）元。" % (fmt(p), fmt(n)), fmt(p * n), dw(p * n))
    if k == 1:
        v = rd(rng, 1, 10, 90); t = rd(rng, 1, 1, 9)
        if "." not in fmt(t):
            return None
        return N("一辆汽车每小时行驶 %s 千米，%s 小时行驶（　）千米。" % (fmt(v), fmt(t)), fmt(v * t), dw(v * t))
    p = rd(rng, 2, 1, 9); a = rd(rng, 1, 1, 9)
    if "." not in fmt(p) or "." not in fmt(a):
        return None
    return N("铺 1 平方米草坪要 %s 元，铺 %s 平方米要（　）元。" % (fmt(p), fmt(a)), fmt(p * a), dw(p * a))


# ---------------- 上册：位置 ----------------
def g_position(rng):
    k = rng.randint(0, 4)
    c = rng.randint(1, 8)
    r = rng.randint(1, 8)
    if k == 0:
        return N("小明坐在教室的第 %d 列、第 %d 行，用数对表示是（　）。" % (c, r), "(%d, %d)" % (c, r),
                 ["(%d, %d)" % (r, c), "(%d, %d)" % (c + 1, r), "(%d, %d)" % (c, r + 1)])
    if k == 1:
        return N("数对 (%d, %d) 表示的列数是（　）。" % (c, r), c, [r, c + 1, max(c - 1, 1)])
    if k == 2:
        return N("数对 (%d, %d) 表示的行数是（　）。" % (c, r), r, [c, r + 1, max(r - 1, 1)])
    if k == 3:
        d = rng.randint(1, 4)
        return N("点 A 用数对 (%d, %d) 表示，向右平移 %d 格后用数对表示是（　）。" % (c, r, d), "(%d, %d)" % (c + d, r),
                 ["(%d, %d)" % (c, r + d), "(%d, %d)" % (max(c - d, 1), r), "(%d, %d)" % (c + d, r + d)])
    d = rng.randint(1, 4)
    return N("点 A 用数对 (%d, %d) 表示，向上平移 %d 格后用数对表示是（　）。" % (c, r, d), "(%d, %d)" % (c, r + d),
             ["(%d, %d)" % (c + d, r), "(%d, %d)" % (c, max(r - d, 1)), "(%d, %d)" % (c + d, r + d)])


# ---------------- 上册：小数除法 ----------------
def g_ddiv(rng, mode="int"):
    if mode == "int":                                   # 除数是整数的小数除法
        d = rng.randint(2, 9)
        nd = rng.choice([1, 2])
        q = rd(rng, nd, 1, 20)
        if "." not in fmt(q):
            return None
        a = q * d
        k = rng.randint(0, 2)
        if k == 0:
            return N("计算：%s ÷ %d = （　）" % (fmt(a), d), fmt(q), dw(q))
        if k == 1:
            return N("把 %s 米长的铁丝平均分成 %d 段，每段长（　）米。" % (fmt(a), d), fmt(q), dw(q))
        return N("把 %s 千克糖果平均分装在 %d 个袋子里，每袋重（　）千克。" % (fmt(a), d), fmt(q), dw(q))
    if mode == "dec":                                   # 一个数除以小数
        k = rng.randint(0, 2)
        if k == 0:
            b = rd(rng, rng.choice([1, 2]), 1, 9)
            q = rd(rng, rng.choice([1, 2]), 1, 20)
            if "." not in fmt(b) or "." not in fmt(q):
                return None
            return N("计算：%s ÷ %s = （　）" % (fmt(q * b), fmt(b)), fmt(q), dw(q))
        if k == 1:
            t = rd(rng, 1, 1, 9); v = rd(rng, 1, 10, 90)
            if "." not in fmt(t):
                return None
            return N("一辆汽车 %s 小时行驶 %s 千米，平均每小时行驶（　）千米。" % (fmt(t), fmt(v * t)), fmt(v), dw(v))
        b = rd(rng, rng.choice([1, 2]), 1, 9)
        if "." not in fmt(b):
            return None
        n = len(fmt(b).split(".")[1])
        return N("计算 %d ÷ %s 时，把除数变成整数，被除数和除数要同时扩大到原来的（　）倍。"
                 % (rng.randint(10, 99), fmt(b)), 10 ** n,
                 [10 ** (n + 1), 10 ** max(n - 1, 0), 10 ** n + 1])
    if mode == "approx":                                # 商的近似数
        a = rd(rng, 2, 1, 99)
        b = rng.randint(2, 9)
        nd = rng.choice([1, 2])
        label = {1: "一位小数", 2: "两位小数"}[nd]
        q = a / b
        ans = rnd(q, nd)
        ws = [w for w in [rnd(q, nd + 2), rnd(q * 10, nd), rnd(q + 1, nd)] if w != ans]
        return N("计算：%s ÷ %d ≈ （　）（保留%s）。" % (fmt(a), b, label), ans, ws[:3])
    if mode == "repeat":                                # 循环小数
        k = rng.randint(0, 1)
        b = "".join(str(rng.randint(1, 9)) for _ in range(rng.choice([1, 2])))
        if k == 0:
            return N("循环小数 0.%s…（循环节重复 3 次）的循环节是（　）。" % (b * 3), b,
                     [b * 2, str(int(b) + 1), str(int(b) + 2)])
        s = "0." + b * 4
        return N("把循环小数 %s… 保留两位小数是（　）。" % s, rnd(D(s), 2),
                 [rnd(D(s), 1), rnd(D(s) + D("0.01"), 2), rnd(D(s) - D("0.01"), 2)])
    if mode == "rule":                                  # 用计算器探索规律
        base = rng.choice([9, 11])
        k = rng.randint(2, 8)
        if base == 9:
            return N("根据规律：1 ÷ 9 = 0.111…，2 ÷ 9 = 0.222…，那么 %d ÷ 9 = （　）。" % k,
                     "0.%s…" % (str(k) * 3),
                     ["0.%s…" % (str(k) * 2), "0.%s…" % (str(k + 1) * 3), "0.%s…" % (str(k) * 4)])
        blk = "%02d" % (k * 9)
        return N("根据规律：1 ÷ 11 = 0.0909…，2 ÷ 11 = 0.1818…，那么 %d ÷ 11 = （　）。" % k,
                 "0.%s…" % (blk * 3),
                 ["0.%s…" % (blk * 2), "0.%s…" % ("%02d" % ((k + 1) * 9) * 3), "0.%s…" % (blk * 4)])
    # mode == "word"  进一法 / 去尾法
    k = rng.randint(0, 2)
    if k == 0:
        cap = rng.randint(2, 9); tot = rng.randint(10, 100)
        if tot % cap == 0:
            return None
        need = -(-tot // cap)
        return N("每个纸箱最多装 %d 千克苹果，装 %d 千克苹果至少需要（　）个纸箱。" % (cap, tot),
                 need, [tot // cap, need + 1, max(need - 1, 1)])
    if k == 1:
        cap = rd(rng, 1, 1, 9); tot = rd(rng, 1, 10, 90)
        if "." not in fmt(cap):
            return None
        n = int(tot // cap)
        if n < 1:
            return None
        return N("每套衣服用布 %s 米，%s 米布最多可以做（　）套衣服。" % (fmt(cap), fmt(tot)), n,
                 [n + 1, max(n - 1, 1), n + 2])
    seg = rd(rng, 1, 1, 9); tot = rd(rng, 1, 5, 50)
    if "." not in fmt(seg):
        return None
    n = int(tot // seg)
    if n < 2:
        return None
    return N("一根绳子长 %s 米，每 %s 米截一段，最多可以截成（　）段。" % (fmt(tot), fmt(seg)), n,
             [n + 1, n - 1, n + 2])


# ---------------- 上册：可能性 / 掷一掷 ----------------
def g_prob(rng, mode="box"):
    if mode == "box":
        r = rng.randint(1, 9); w = rng.randint(1, 9)
        if r == w:
            return None
        big = "红球" if r > w else "白球"
        sml = "白球" if r > w else "红球"
        return N("盒子里有 %d 个红球和 %d 个白球，任意摸出一个，摸到（　）的可能性大。" % (r, w), big,
                 [sml, "两种球一样大", "无法确定"])
    s = rng.randint(2, 12)
    cnt = sum(1 for i in range(1, 7) for j in range(1, 7) if i + j == s)
    return N("同时掷两个骰子，两个骰子的点数之和是 %d 的情况有（　）种。" % s, cnt,
             [cnt + 1, max(cnt - 1, 1), 6])


# ---------------- 上册：简易方程 ----------------
def g_eq(rng, mode="letter"):
    if mode == "letter":                                # 用字母表示数
        k = rng.randint(0, 3)
        if k == 0:
            a = rng.randint(2, 9); c = rng.randint(1, 20); v = rng.randint(1, 9)
            return N("当 x = %d 时，%dx + %d 的值是（　）。" % (v, a, c), a * v + c, [a * v, a * v + c + 1, c])
        if k == 1:
            n = rng.randint(2, 9)
            return N("每支笔 a 元，买 %d 支要（　）元。" % n, "%da" % n,
                     ["a%d" % n, "a + %d" % n, "%d + a" % n])
        if k == 2:
            a = rng.randint(2, 9); c = rng.randint(1, 20)
            return N("用含有字母的式子表示：比 x 的 %d 倍多 %d 的数写作（　）。" % (a, c), "%dx + %d" % (a, c),
                     ["%d + %dx" % (c, a), "%d(x + %d)" % (a, c), "x%d + %d" % (a, c)])
        a = rng.randint(2, 9); c = rng.randint(1, 20)
        return N("用含有字母的式子表示：比 x 的 %d 倍少 %d 的数写作（　）。" % (a, c), "%dx - %d" % (a, c),
                 ["%dx + %d" % (a, c), "%d - %dx" % (c, a), "%d(x - %d)" % (a, c)])
    if mode == "prop":                                  # 等式的性质
        k = rng.randint(0, 2)
        if k == 0:
            n = rng.randint(2, 20)
            return N("根据等式的性质，如果 a = b，那么 a + %d = b + （　）。" % n, n, [n + 1, max(n - 1, 1), 0])
        if k == 1:
            n = rng.randint(2, 20)
            return N("根据等式的性质，如果 a = b，那么 a - %d = b - （　）。" % n, n, [n + 1, max(n - 1, 1), 0])
        n = rng.randint(2, 9)
        return N("根据等式的性质，如果 a = b，那么 a × %d = b × （　）。" % n, n, [n + 1, max(n - 1, 1), 1])
    if mode == "solve":                                 # 解方程
        k = rng.randint(0, 4)
        if k == 0:
            a = rd(rng, rng.choice([1, 2]), 1, 20); x = rd(rng, rng.choice([1, 2]), 1, 20)
            if "." not in fmt(a):
                return None
            return N("解方程：x + %s = %s，x = （　）。" % (fmt(a), fmt(a + x)), fmt(x), dw(x))
        if k == 1:
            a = rd(rng, rng.choice([1, 2]), 1, 20); x = rd(rng, rng.choice([1, 2]), 1, 20)
            if "." not in fmt(a):
                return None
            return N("解方程：x - %s = %s，x = （　）。" % (fmt(a), fmt(x)), fmt(a + x), dw(a + x))
        if k == 2:
            a = rng.randint(2, 9); x = rng.randint(2, 20)
            return N("解方程：%dx = %d，x = （　）。" % (a, a * x), x, [x + 1, max(x - 1, 1), a])
        if k == 3:
            a = rng.randint(2, 9); x = rng.randint(2, 20)
            return N("解方程：x ÷ %d = %d，x = （　）。" % (a, x), a * x, [a * x + 1, a * x - a, x])
        a = rng.randint(2, 9); x = rng.randint(2, 20); c = rng.randint(1, 30)
        return N("解方程：%dx + %d = %d，x = （　）。" % (a, c, a * x + c), x, [x + 1, max(x - 1, 1), c])
    # mode == "word"  实际问题与方程
    k = rng.randint(0, 2)
    if k == 0:
        a = rng.randint(2, 9); x = rng.randint(2, 20); c = rng.randint(1, 30)
        return N("一个数的 %d 倍加上 %d 等于 %d，这个数是（　）。" % (a, c, a * x + c), x,
                 [x + 1, max(x - 1, 1), c])
    if k == 1:
        a = rng.randint(2, 9); x = rng.randint(3, 20); c = rng.randint(1, a * x - 1)
        return N("一个数的 %d 倍减去 %d 等于 %d，这个数是（　）。" % (a, c, a * x - c), x,
                 [x + 1, max(x - 1, 1), c])
    m = rng.randint(2, 5); x = rng.randint(2, 20)
    return N("甲数是乙数的 %d 倍，甲乙两数的和是 %d，乙数是（　）。" % (m, (m + 1) * x), x,
             [x + 1, m * x, (m + 1) * x // 2])


# ---------------- 上册：多边形的面积 ----------------
def g_area(rng, mode="para"):
    if mode == "para":
        k = rng.randint(0, 1)
        a = rng.randint(2, 30); h = rng.randint(2, 20)
        s = a * h
        if k == 0:
            return N("一个平行四边形的底是 %d 厘米，高是 %d 厘米，面积是（　）平方厘米。" % (a, h), s,
                     [a + h, (a + h) * 2, max(s - a, 1)])
        return N("一个平行四边形的面积是 %d 平方厘米，底是 %d 厘米，高是（　）厘米。" % (s, a), h,
                 [h + 1, max(h - 1, 1), a])
    if mode == "tri":
        k = rng.randint(0, 1)
        a = rng.randint(2, 30); h = rng.randint(2, 20)
        while (a * h) % 2:
            h += 1
        s = a * h // 2
        if k == 0:
            return N("一个三角形的底是 %d 厘米，高是 %d 厘米，面积是（　）平方厘米。" % (a, h), s,
                     [a * h, (a + h) * 2, max(s - 1, 1)])
        return N("一个三角形的面积是 %d 平方厘米，底是 %d 厘米，高是（　）厘米。" % (s, a), h,
                 [h + 1, max(h - 1, 1), a])
    if mode == "trap":
        k = rng.randint(0, 1)
        a = rng.randint(2, 20); b = rng.randint(2, 20); h = rng.randint(2, 20)
        while (a + b) * h % 2:
            h += 1
        s = (a + b) * h // 2
        if k == 0:
            return N("一个梯形的上底是 %d 厘米，下底是 %d 厘米，高是 %d 厘米，面积是（　）平方厘米。" % (a, b, h), s,
                     [(a + b) * h, (a + b) + h, max(s - h, 1)])
        return N("一个梯形的面积是 %d 平方厘米，上底是 %d 厘米，下底是 %d 厘米，高是（　）厘米。" % (s, a, b), h,
                 [h + 1, max(h - 1, 1), a + b])
    # mode == "combo"  组合图形
    k = rng.randint(0, 2)
    if k == 0:
        L = rng.randint(4, 20); W = rng.randint(2, 10); b = rng.randint(2, L); h = rng.randint(2, 10)
        while (b * h) % 2:
            h += 1
        s = L * W + b * h // 2
        return N("一个组合图形由一个长 %d 米、宽 %d 米的长方形和一个底 %d 米、高 %d 米的三角形拼成，它的面积是（　）平方米。"
                 % (L, W, b, h), s, [L * W, L * W + b * h, max(s - 1, 1)])
    if k == 1:
        L = rng.randint(6, 20); W = rng.randint(4, 12); b = rng.randint(2, L - 2); h = rng.randint(2, W - 2)
        while (b * h) % 2:
            h += 1
        if b * h // 2 >= L * W:
            return None
        s = L * W - b * h // 2
        return N("一个长 %d 米、宽 %d 米的长方形，去掉一个底 %d 米、高 %d 米的三角形后，剩下部分的面积是（　）平方米。"
                 % (L, W, b, h), s, [L * W, L * W + b * h // 2, max(s - 1, 1)])
    L1 = rng.randint(3, 12); W1 = rng.randint(2, 8); L2 = rng.randint(3, 12); W2 = rng.randint(2, 8)
    s = L1 * W1 + L2 * W2
    return N("一个组合图形由两个长方形组成，一个长 %d 米、宽 %d 米，另一个长 %d 米、宽 %d 米，面积一共是（　）平方米。"
             % (L1, W1, L2, W2), s, [L1 * W1, L2 * W2, max(s - 1, 1)])


# ---------------- 上册：植树问题 ----------------
def g_tree(rng, mode="all"):
    k = rng.randint(0, 5) if mode == "all" else int(mode)
    d = rng.randint(2, 10)
    seg = rng.randint(3, 15)
    L = d * seg
    if k == 0:
        return N("一条 %d 米长的小路，每隔 %d 米栽一棵树（两端都栽），一共要栽（　）棵树。" % (L, d), seg + 1,
                 [seg, seg + 2, max(seg - 1, 1)])
    if k == 1:
        return N("一条 %d 米长的小路，每隔 %d 米栽一棵树（两端都不栽），一共要栽（　）棵树。" % (L, d), seg - 1,
                 [seg, seg + 1, max(seg - 2, 1)])
    if k == 2:
        return N("一条 %d 米长的小路，每隔 %d 米栽一棵树（一端栽一端不栽），一共要栽（　）棵树。" % (L, d), seg,
                 [seg + 1, seg - 1, seg + 2])
    if k == 3:
        return N("一个圆形池塘的周长是 %d 米，每隔 %d 米栽一棵树，一共要栽（　）棵树。" % (L, d), seg,
                 [seg + 1, seg - 1, seg + 2])
    if k == 4:
        n = rng.randint(2, 12); t = rng.randint(2, 9)
        return N("把一根木头锯成 %d 段，每锯一次要 %d 分钟，一共要（　）分钟。" % (n, t), (n - 1) * t,
                 [n * t, (n - 1) * t + t, max((n - 2) * t, 1)])
    n = rng.randint(2, 9); t = rng.randint(8, 20)
    return N("从 1 楼走到 %d 楼，每上一层楼要走 %d 级台阶，一共要走（　）级台阶。" % (n, t), (n - 1) * t,
             [n * t, (n - 1) * t + t, max((n - 2) * t, 1)])


# ---------------- 上册：小数加减（复习用） ----------------
def g_dec_addsub(rng):
    a = rd(rng, 2, 1, 99)
    b = rd(rng, 2, 1, 99)
    if rng.random() < 0.5:
        return N("计算：%s + %s = （　）" % (fmt(a), fmt(b)), fmt(a + b), dw(a + b))
    if a <= b:
        return None
    return N("计算：%s - %s = （　）" % (fmt(a), fmt(b)), fmt(a - b), dw(a - b))


# ---------------- 下册：观察物体（三） ----------------
def g_observe(rng):
    k = rng.randint(0, 2)
    if k == 0:
        n = rng.randint(2, 9)
        return N("用 %d 个同样大的正方体摆成一排，从前面看是（　）个正方形连成的一排。" % n, n,
                 [n + 1, max(n - 1, 1), 2 * n])
    if k == 1:
        layer = rng.randint(2, 6); per = rng.randint(2, 6)
        return N("一个立体图形摆了 %d 层，每层有 %d 个小正方体，一共用了（　）个小正方体。" % (layer, per),
                 layer * per, [layer + per, layer * per + 1, max(layer * per - 1, 1)])
    m = rng.choice([2, 3])
    return N("用同样大的小正方体摆成一个大正方体，每条棱上摆 %d 个，一共需要（　）个小正方体。" % m, m ** 3,
             [m * 3, m * m, m ** 3 + 1])


# ---------------- 下册：因数与倍数 ----------------
def g_fm(rng, mode="factor"):
    if mode == "factor":
        k = rng.randint(0, 2)
        n = rng.randint(6, 60)
        if k == 0:
            c = len(divisors(n))
            return N("%d 的因数有（　）个。" % n, c, [c + 1, max(c - 1, 1), n])
        if k == 1:
            return N("%d 的最小倍数是（　）。" % n, n, [1, 2 * n, 0])
        return N("一个数的最大因数是 %d，这个数的最小倍数是（　）。" % n, n, [1, 2 * n, 2])
    if mode == "feature":
        k = rng.choice([2, 3, 5])
        t = k * rng.randint(2, 20)
        others = []
        while len(others) < 2:
            x = rng.randint(10, 99)
            if x % k and x not in others:
                others.append(x)
        three = others + [t]
        rng.shuffle(three)
        extra = t + 1 if (t + 1) % k else t + 2
        return N("在 %d、%d、%d 中，是 %d 的倍数的数是（　）。" % (three[0], three[1], three[2], k), t,
                 [others[0], others[1], extra])
    # mode == "prime"
    k = rng.randint(0, 1)
    if k == 0:
        n = rng.randint(2, 100)
        ans = "质数" if is_prime(n) else "合数"
        return N("%d 是（　）。" % n, ans, ["合数" if ans == "质数" else "质数", "奇数", "偶数"])
    p = rng.choice([x for x in range(10, 100) if is_prime(x)])
    comps = []
    while len(comps) < 2:
        x = rng.randint(10, 99)
        if not is_prime(x) and x not in comps:
            comps.append(x)
    three = comps + [p]
    rng.shuffle(three)
    extra = p + 1 if not is_prime(p + 1) else p + 2
    return N("在 %d、%d、%d 中，质数是（　）。" % (three[0], three[1], three[2]), p,
             [comps[0], comps[1], extra])


# ---------------- 下册：长方体和正方体 ----------------
def g_cuboid(rng, mode="edge"):
    if mode == "edge":
        a = rng.randint(2, 12); b = rng.randint(2, 12); h = rng.randint(2, 12)
        s = 4 * (a + b + h)
        return N("一个长方体长 %d 分米、宽 %d 分米、高 %d 分米，它的棱长总和是（　）分米。" % (a, b, h), s,
                 [a + b + h, 2 * (a + b + h), max(s - 4, 1)])
    if mode == "surface":
        k = rng.randint(0, 1)
        a = rng.randint(2, 12); b = rng.randint(2, 12); h = rng.randint(2, 12)
        if k == 0:
            s = 2 * (a * b + a * h + b * h)
            return N("一个长方体长 %d 分米、宽 %d 分米、高 %d 分米，它的表面积是（　）平方分米。" % (a, b, h), s,
                     [a * b + a * h + b * h, a * b * h, max(s - 2, 1)])
        s = a * b + 2 * (a * h + b * h)
        return N("一个无盖的长方体水箱长 %d 分米、宽 %d 分米、高 %d 分米，做这个水箱至少需要（　）平方分米铁皮。"
                 % (a, b, h), s, [2 * (a * b + a * h + b * h), a * b, max(s - 2, 1)])
    if mode == "volume":
        k = rng.randint(0, 1)
        a = rng.randint(2, 12); b = rng.randint(2, 12); h = rng.randint(2, 12)
        if k == 0:
            return N("一个长方体长 %d 分米、宽 %d 分米、高 %d 分米，它的体积是（　）立方分米。" % (a, b, h), a * b * h,
                     [2 * (a * b + a * h + b * h), a + b + h, max(a * b * h - 1, 1)])
        return N("一个长方体的底面积是 %d 平方分米，高是 %d 分米，它的体积是（　）立方分米。" % (a * b, h), a * b * h,
                 [a * b + h, max(a * b * h - 1, 1), a * b * (h + 1)])
    if mode == "cube":
        k = rng.randint(0, 2)
        a = rng.randint(2, 10)
        if k == 0:
            return N("一个正方体的棱长是 %d 厘米，它的棱长总和是（　）厘米。" % a, 12 * a, [6 * a, a ** 3, 12 * a + 12])
        if k == 1:
            return N("一个正方体的棱长是 %d 厘米，它的表面积是（　）平方厘米。" % a, 6 * a * a, [a * a, 12 * a, 6 * a * a + 6])
        return N("一个正方体的棱长是 %d 厘米，它的体积是（　）立方厘米。" % a, a ** 3, [a * a, 6 * a * a, (a + 1) ** 3])
    if mode == "unit":
        k = rng.randint(0, 3)
        if k == 0:
            n = rd(rng, rng.choice([1, 2]), 1, 9)
            if "." not in fmt(n):
                return None
            return N("体积单位换算：%s 立方米 = （　）立方分米。" % fmt(n), fmt(n * 1000),
                     [fmt(n * 100), fmt(n * 10), fmt(n)])
        if k == 1:
            n = rd(rng, rng.choice([1, 2]), 1, 9)
            if "." not in fmt(n):
                return None
            return N("体积单位换算：%s 立方分米 = （　）立方厘米。" % fmt(n), fmt(n * 1000),
                     [fmt(n * 100), fmt(n * 10), fmt(n)])
        if k == 2:
            n = rng.randint(2, 9) * 1000
            return N("体积单位换算：%d 立方厘米 = （　）立方分米。" % n, n // 1000, [n, n // 100, n // 10])
        n = rng.randint(2, 9) * 1000
        return N("体积单位换算：%d 立方分米 = （　）立方米。" % n, n // 1000, [n, n // 100, n // 10])
    # mode == "capacity"
    k = rng.randint(0, 1)
    if k == 0:
        a = rng.randint(2, 10); b = rng.randint(2, 10); h = rng.randint(2, 10)
        return N("一个长方体水箱，从里面量长 %d 分米、宽 %d 分米、高 %d 分米，它的容积是（　）升。" % (a, b, h),
                 a * b * h, [2 * (a * b + a * h + b * h), a * b * h * 1000, max(a * b * h - 1, 1)])
    n = rd(rng, rng.choice([1, 2]), 1, 9)
    if "." not in fmt(n):
        return None
    return N("%s 升 = （　）毫升。" % fmt(n), fmt(n * 1000), [fmt(n * 100), fmt(n * 10), fmt(n)])


# ---------------- 下册：分数的意义和性质 ----------------
def g_frac(rng, mode="meaning"):
    if mode == "meaning":
        k = rng.randint(0, 3)
        if k == 0:
            d = rng.randint(2, 10); n = rng.randint(1, d)
            return N("%d/%d 的分数单位是（　）。" % (n, d), "1/%d" % d, ["1/%d" % (d + 1), "1/%d" % n, "1"])
        if k == 1:
            d = rng.randint(2, 10); n = rng.randint(1, d)
            return N("%d/%d 里有（　）个 1/%d。" % (n, d, d), n, [n + 1, max(n - 1, 1), d])
        d = rng.choice([2, 3, 4, 5, 6, 8]); total = d * rng.randint(2, 12)
        if k == 2:
            return N("把 %d 个苹果平均分成 %d 份，每份是这些苹果的（　）。" % (total, d), "1/%d" % d,
                     ["1/%d" % total, "%d/%d" % (d, total), "1"])
        return N("把 %d 个苹果平均分成 %d 份，每份有（　）个。" % (total, d), total // d,
                 [total // d + 1, max(total // d - 1, 1), d])
    if mode == "div":
        k = rng.randint(0, 2)
        if k == 0:
            d = rng.randint(2, 9); a = rng.randint(1, d - 1)
            return N("把 %d 米长的绳子平均分成 %d 段，每段长（　）米。" % (a, d), "%d/%d" % (a, d),
                     ["%d/%d" % (d, a), "%d/%d" % (a + 1, d), "%d/%d" % (a, d + 1)])
        if k == 1:
            d = rng.randint(2, 9); a = rng.randint(1, d - 1)
            return N("%d ÷ %d = （　）（用分数表示）。" % (a, d), "%d/%d" % (a, d),
                     ["%d/%d" % (d, a), "%d/%d" % (a + 1, d), "%d/%d" % (a, d + 1)])
        d = rng.randint(2, 9); total = rng.randint(3, 30)
        if total % d == 0:
            return None
        return N("把 %d 千克糖平均分给 %d 个小朋友，每人分得（　）千克。" % (total, d), "%d/%d" % (total, d),
                 ["%d/%d" % (d, total), "%d/%d" % (total + 1, d), "%d/%d" % (total, d + 1)])
    if mode == "kind":
        k = rng.randint(0, 2)
        if k == 0:
            d = rng.randint(2, 9); n = rng.randint(1, 12)
            ans = "真分数" if n < d else "假分数"
            return N("%d/%d 是（　）。" % (n, d), ans, ["假分数" if ans == "真分数" else "真分数", "带分数", "整数"])
        if k == 1:
            d = rng.randint(2, 9)
            return N("分母是 %d 的真分数有（　）个。" % d, d - 1, [d, d + 1, max(d - 2, 1)])
        w = rng.randint(1, 5); d = rng.randint(2, 6); n = rng.randint(1, d - 1)
        return N("把带分数 %d 又 %d/%d 化成假分数是（　）。" % (w, n, d), "%d/%d" % (w * d + n, d),
                 ["%d/%d" % (w + n, d), "%d/%d" % (w * d, d), "%d/%d" % (d, w * d + n)])
    if mode == "prop":
        k = rng.randint(0, 2)
        if k == 0:
            b = rng.randint(2, 9); a = rng.randint(1, b - 1); m = rng.randint(2, 6)
            return N("%d/%d = （　）/%d。" % (a, b, b * m), a * m, [a * m + 1, a + m, b * m])
        if k == 1:
            b = rng.randint(2, 9); a = rng.randint(1, b - 1); m = rng.randint(2, 6)
            return N("%d/%d = %d/（　）。" % (a, b, a * m), b * m, [b * m + 1, b + m, a * m])
        g = rng.randint(2, 6); a = rng.randint(1, 6); b = rng.randint(a + 1, 9)
        f = Fraction(a, b)
        return N("把 %d/%d 的分子和分母同时除以 %d，得到（　）。" % (a * g, b * g, g), str(f), fw(f))
    if mode == "gcd":
        k = rng.randint(0, 1)
        if k == 0:
            a = rng.randint(2, 60); b = rng.randint(2, 60)
            g = math.gcd(a, b)
            return N("%d 和 %d 的最大公因数是（　）。" % (a, b), g, [g + 1, max(g - 1, 1), a * b])
        b = rng.randint(2, 20); a = b * rng.randint(2, 6)
        return N("%d 和 %d 的最大公因数是（　）。" % (a, b), b, [1, 2 * b, b + 1])
    if mode == "reduce":
        g = rng.randint(2, 6); a = rng.randint(1, 9); b = rng.randint(a + 1, 12)
        while math.gcd(a, b) != 1:
            b = rng.randint(a + 1, 12)
        f = Fraction(a, b)
        return N("把 %d/%d 化成最简分数是（　）。" % (a * g, b * g), str(f), fw(f))
    if mode == "lcm":
        k = rng.randint(0, 1)
        if k == 0:
            a = rng.randint(2, 20); b = rng.randint(2, 20)
            l = a * b // math.gcd(a, b)
            return N("%d 和 %d 的最小公倍数是（　）。" % (a, b), l, [l + a, a * b, max(l - a, 1)])
        a = rng.randint(2, 12); m = rng.randint(2, 6)
        return N("%d 和 %d 的最小公倍数是（　）。" % (a, a * m), a * m, [a, m, a * m + a])
    if mode == "tongfen":
        k = rng.randint(0, 1)
        if k == 0:
            d1 = rng.choice([2, 3, 4, 5, 6]); d2 = rng.choice([2, 3, 4, 5, 6])
            while d2 == d1:
                d2 = rng.choice([2, 3, 4, 5, 6])
            a = rng.randint(1, d1 - 1); b = rng.randint(1, d2 - 1)
            l = d1 * d2 // math.gcd(d1, d2)
            return N("把 %d/%d 和 %d/%d 通分，公分母是（　）。" % (a, d1, b, d2), l,
                     [d1 * d2, l + 1, max(l - 1, 2)])
        f1 = Fraction(rng.randint(1, 8), rng.randint(2, 9))
        f2 = Fraction(rng.randint(1, 8), rng.randint(2, 9))
        if f1 == f2:
            return None
        ans = "＞" if f1 > f2 else "＜"
        return N("比较大小：%s ○ %s，○ 里应填（　）。" % (f1, f2), ans,
                 ["＜" if ans == "＞" else "＞", "＝", "无法比较"])
    # mode == "dec"  分数和小数的互化
    k = rng.randint(0, 1)
    if k == 0:
        d = rng.choice([2, 4, 5, 8, 10, 20, 25]); n = rng.randint(1, d - 1)
        v = Decimal(n) / Decimal(d)
        return N("把 %d/%d 化成小数是（　）。" % (n, d), fmt(v), [fmt(v * 10), fmt(v / 10), fmt(v + 1)])
    dec = rng.choice(["0.5", "0.25", "0.75", "0.2", "0.4", "0.6", "0.8", "0.125", "0.375", "0.05"])
    f = Fraction(Decimal(dec))
    return N("把 %s 化成分数是（　）。" % dec, str(f), fw(f))


# ---------------- 下册：分数的加法和减法 ----------------
def g_fadd(rng, mode="same"):
    if mode == "same":
        d = rng.choice([4, 5, 6, 7, 8, 9, 10, 12])
        a = rng.randint(1, d - 2); b = rng.randint(1, d - a - 1)
        if rng.random() < 0.5:
            f = Fraction(a + b, d)
            return N("计算：%d/%d + %d/%d = （　）" % (a, d, b, d), str(f), fw(f))
        if a < b:
            a, b = b, a
        f = Fraction(a - b, d)
        if f.numerator == 0:
            return None
        return N("计算：%d/%d - %d/%d = （　）" % (a, d, b, d), str(f), fw(f))
    if mode == "diff":
        d1 = rng.choice([2, 3, 4, 5, 6]); d2 = rng.choice([2, 3, 4, 5, 6])
        while d1 == d2:
            d2 = rng.choice([2, 3, 4, 5, 6])
        f1 = Fraction(rng.randint(1, d1 - 1), d1)
        f2 = Fraction(rng.randint(1, d2 - 1), d2)
        if rng.random() < 0.5:
            f = f1 + f2
            return N("计算：%s + %s = （　）" % (f1, f2), str(f), fw(f))
        if f1 < f2:
            f1, f2 = f2, f1
        f = f1 - f2
        if f.numerator == 0:
            return None
        return N("计算：%s - %s = （　）" % (f1, f2), str(f), fw(f))
    # mode == "mix"
    k = rng.randint(0, 1)
    if k == 0:
        a = Fraction(rng.randint(1, 5), rng.choice([2, 3, 4, 6]))
        b = Fraction(rng.randint(1, 5), rng.choice([3, 4, 6, 8]))
        c = Fraction(rng.randint(1, 5), rng.choice([2, 3, 4, 6, 8]))
        if a + b <= c:
            return None
        f = a + b - c
        return N("计算：%s + %s - %s = （　）" % (a, b, c), str(f), fw(f))
    d = rng.choice([3, 4, 5, 6, 8]); a = rng.randint(1, d - 1)
    f = Fraction(1) - Fraction(a, d)
    return N("计算：1 - %d/%d = （　）" % (a, d), str(f), fw(f))


# ---------------- 下册：图形的运动（旋转、平移） ----------------
def g_move(rng, mode="rot"):
    if mode == "rot":
        k = rng.randint(0, 1)
        if k == 0:
            h = rng.randint(1, 11)
            return N("钟面上时针从 12 走到 %d，绕中心点顺时针旋转了（　）度。" % h, 30 * h,
                     [30 * h + 30, max(30 * h - 30, 30), 360])
        a = rng.randint(1, 12); b = rng.randint(1, 12)
        if a == b:
            return None
        deg = ((b - a) % 12) * 30
        return N("钟面上时针从 %d 走到 %d（顺时针，不足一圈），绕中心点旋转了（　）度。" % (a, b), deg,
                 [deg + 30, (deg + 60) % 360 or 360, 30])
    k = rng.randint(0, 1)
    if k == 0:
        dx = rng.randint(1, 4); dy = rng.randint(1, 4)
        c = rng.randint(1, 8); r = rng.randint(dy + 1, 8)
        return N("点 P 用数对 (%d, %d) 表示，先向右平移 %d 格，再向下平移 %d 格，这时点 P 的位置用数对表示是（　）。"
                 % (c, r, dx, dy), "(%d, %d)" % (c + dx, r - dy),
                 ["(%d, %d)" % (c + dx, r + dy), "(%d, %d)" % (max(c - dx, 1), r - dy), "(%d, %d)" % (c, r)])
    dx = rng.randint(1, 4); dy = rng.randint(1, 4)
    c = rng.randint(dx + 1, 8); r = rng.randint(1, 8)
    return N("点 P 用数对 (%d, %d) 表示，先向左平移 %d 格，再向上平移 %d 格，这时点 P 的位置用数对表示是（　）。"
             % (c, r, dx, dy), "(%d, %d)" % (c - dx, r + dy),
             ["(%d, %d)" % (c + dx, r + dy), "(%d, %d)" % (c - dx, max(r - dy, 1)), "(%d, %d)" % (c, r)])


# ---------------- 下册：折线统计图（数据分析） ----------------
def g_stat(rng, mode="avg"):
    if mode == "avg":
        n = rng.randint(4, 6)
        vals = [rng.randint(5, 40) for _ in range(n)]
        total = sum(vals)
        rest = total % n
        if rest:
            vals[-1] += n - rest
        total = sum(vals)
        parts = "、".join(str(v) for v in vals)
        return N("小明 %d 天读课外书的页数分别是 %s，平均每天读（　）页。" % (n, parts), total // n,
                 [total // n + 1, max(total // n - 1, 1), total])
    vals = [rng.randint(15, 35) for _ in range(7)]
    parts = "、".join(str(v) for v in vals)
    d = max(vals) - min(vals)
    return N("某地一周的最高气温分别是 %s ℃，最高气温与最低气温相差（　）℃。" % parts, d,
             [d + 1, max(d - 1, 1), max(vals) + min(vals)])


# ---------------- 下册：找次品 ----------------
def g_fake(rng):
    n = rng.randint(3, 30)
    k = 1
    while 3 ** k < n:
        k += 1
    return N("有 %d 个零件，其中 1 个是次品（轻一些），用天平称，最少称（　）次能保证找出次品。" % n, k,
             [k + 1, max(k - 1, 1), k + 2])


# ---------------- 自动验算：题干反解重算 ----------------
_FR = r"(\d+/\d+)"
_NUM = r"([\d.]+)"


def expect_g5(stem):
    """按题干反解重算；识别不了（手写概念题）返回 None，verify 会跳过。"""
    s = stem
    m = None

    # ---- 位置：数对 ----
    m = re.match(r"^小明坐在教室的第 (\d+) 列、第 (\d+) 行，用数对表示是（　）。$", s)
    if m:
        return "(%s, %s)" % (m.group(1), m.group(2))
    m = re.match(r"^数对 \((\d+), (\d+)\) 表示的列数是（　）。$", s)
    if m:
        return int(m.group(1))
    m = re.match(r"^数对 \((\d+), (\d+)\) 表示的行数是（　）。$", s)
    if m:
        return int(m.group(2))
    m = re.match(r"^点 A 用数对 \((\d+), (\d+)\) 表示，向右平移 (\d+) 格后用数对表示是（　）。$", s)
    if m:
        return "(%d, %d)" % (int(m.group(1)) + int(m.group(3)), int(m.group(2)))
    m = re.match(r"^点 A 用数对 \((\d+), (\d+)\) 表示，向上平移 (\d+) 格后用数对表示是（　）。$", s)
    if m:
        return "(%d, %d)" % (int(m.group(1)), int(m.group(2)) + int(m.group(3)))
    m = re.match(r"^点 P 用数对 \((\d+), (\d+)\) 表示，先向右平移 (\d+) 格，再向下平移 (\d+) 格，"
                 r"这时点 P 的位置用数对表示是（　）。$", s)
    if m:
        return "(%d, %d)" % (int(m.group(1)) + int(m.group(3)), int(m.group(2)) - int(m.group(4)))
    m = re.match(r"^点 P 用数对 \((\d+), (\d+)\) 表示，先向左平移 (\d+) 格，再向上平移 (\d+) 格，"
                 r"这时点 P 的位置用数对表示是（　）。$", s)
    if m:
        return "(%d, %d)" % (int(m.group(1)) - int(m.group(3)), int(m.group(2)) + int(m.group(4)))

    # ---- 旋转 ----
    m = re.match(r"^钟面上时针从 12 走到 (\d+)，绕中心点顺时针旋转了（　）度。$", s)
    if m:
        return 30 * int(m.group(1))
    m = re.match(r"^钟面上时针从 (\d+) 走到 (\d+)（顺时针，不足一圈），绕中心点旋转了（　）度。$", s)
    if m:
        return ((int(m.group(2)) - int(m.group(1))) % 12) * 30

    # ---- 找次品 ----
    m = re.match(r"^有 (\d+) 个零件，其中 1 个是次品（轻一些），用天平称，最少称（　）次能保证找出次品。$", s)
    if m:
        n = int(m.group(1))
        k = 1
        while 3 ** k < n:
            k += 1
        return k

    # ---- 折线统计图（数据分析） ----
    m = re.match(r"^小明 (\d+) 天读课外书的页数分别是 (.+)，平均每天读（　）页。$", s)
    if m:
        vals = [int(x) for x in re.findall(r"\d+", m.group(2))]
        return sum(vals) // int(m.group(1))
    m = re.match(r"^某地一周的最高气温分别是 (.+) ℃，最高气温与最低气温相差（　）℃。$", s)
    if m:
        vals = [int(x) for x in re.findall(r"\d+", m.group(1))]
        return max(vals) - min(vals)

    # ---- 掷一掷 ----
    m = re.match(r"^同时掷两个骰子，两个骰子的点数之和是 (\d+) 的情况有（　）种。$", s)
    if m:
        t = int(m.group(1))
        return sum(1 for i in range(1, 7) for j in range(1, 7) if i + j == t)
    m = re.match(r"^盒子里有 (\d+) 个红球和 (\d+) 个白球，任意摸出一个，摸到（　）的可能性大。$", s)
    if m:
        return "红球" if int(m.group(1)) > int(m.group(2)) else "白球"

    # ---- 观察物体 ----
    m = re.match(r"^用 (\d+) 个同样大的正方体摆成一排，从前面看是（　）个正方形连成的一排。$", s)
    if m:
        return int(m.group(1))
    m = re.match(r"^一个立体图形摆了 (\d+) 层，每层有 (\d+) 个小正方体，一共用了（　）个小正方体。$", s)
    if m:
        return int(m.group(1)) * int(m.group(2))
    m = re.match(r"^用同样大的小正方体摆成一个大正方体，每条棱上摆 (\d+) 个，一共需要（　）个小正方体。$", s)
    if m:
        return int(m.group(1)) ** 3

    # ---- 因数与倍数 ----
    m = re.match(r"^(\d+) 的因数有（　）个。$", s)
    if m:
        return len(divisors(int(m.group(1))))
    m = re.match(r"^(\d+) 的最小倍数是（　）。$", s)
    if m:
        return int(m.group(1))
    m = re.match(r"^一个数的最大因数是 (\d+)，这个数的最小倍数是（　）。$", s)
    if m:
        return int(m.group(1))
    m = re.match(r"^在 (\d+)、(\d+)、(\d+) 中，是 (\d+) 的倍数的数是（　）。$", s)
    if m:
        k = int(m.group(4))
        for i in range(1, 4):
            v = int(m.group(i))
            if v % k == 0:
                return v
        return None
    m = re.match(r"^(\d+) 是（　）。$", s)
    if m:
        return "质数" if is_prime(int(m.group(1))) else "合数"
    m = re.match(r"^在 (\d+)、(\d+)、(\d+) 中，质数是（　）。$", s)
    if m:
        for i in range(1, 4):
            v = int(m.group(i))
            if is_prime(v):
                return v
        return None

    # ---- 长方体和正方体 ----
    m = re.match(r"^一个长方体长 (\d+) 分米、宽 (\d+) 分米、高 (\d+) 分米，它的棱长总和是（　）分米。$", s)
    if m:
        a, b, c = map(int, m.groups())
        return 4 * (a + b + c)
    m = re.match(r"^一个长方体长 (\d+) 分米、宽 (\d+) 分米、高 (\d+) 分米，它的表面积是（　）平方分米。$", s)
    if m:
        a, b, c = map(int, m.groups())
        return 2 * (a * b + a * c + b * c)
    m = re.match(r"^一个长方体长 (\d+) 分米、宽 (\d+) 分米、高 (\d+) 分米，它的体积是（　）立方分米。$", s)
    if m:
        a, b, c = map(int, m.groups())
        return a * b * c
    m = re.match(r"^一个无盖的长方体水箱长 (\d+) 分米、宽 (\d+) 分米、高 (\d+) 分米，"
                 r"做这个水箱至少需要（　）平方分米铁皮。$", s)
    if m:
        a, b, c = map(int, m.groups())
        return a * b + 2 * (a * c + b * c)
    m = re.match(r"^一个长方体的底面积是 (\d+) 平方分米，高是 (\d+) 分米，它的体积是（　）立方分米。$", s)
    if m:
        return int(m.group(1)) * int(m.group(2))
    m = re.match(r"^一个正方体的棱长是 (\d+) 厘米，它的棱长总和是（　）厘米。$", s)
    if m:
        return 12 * int(m.group(1))
    m = re.match(r"^一个正方体的棱长是 (\d+) 厘米，它的表面积是（　）平方厘米。$", s)
    if m:
        a = int(m.group(1))
        return 6 * a * a
    m = re.match(r"^一个正方体的棱长是 (\d+) 厘米，它的体积是（　）立方厘米。$", s)
    if m:
        return int(m.group(1)) ** 3
    m = re.match(r"^体积单位换算：([\d.]+) 立方米 = （　）立方分米。$", s)
    if m:
        return fmt(D(m.group(1)) * 1000)
    m = re.match(r"^体积单位换算：([\d.]+) 立方分米 = （　）立方厘米。$", s)
    if m:
        return fmt(D(m.group(1)) * 1000)
    m = re.match(r"^体积单位换算：(\d+) 立方厘米 = （　）立方分米。$", s)
    if m:
        return int(m.group(1)) // 1000
    m = re.match(r"^体积单位换算：(\d+) 立方分米 = （　）立方米。$", s)
    if m:
        return int(m.group(1)) // 1000
    m = re.match(r"^一个长方体水箱，从里面量长 (\d+) 分米、宽 (\d+) 分米、高 (\d+) 分米，它的容积是（　）升。$", s)
    if m:
        a, b, c = map(int, m.groups())
        return a * b * c
    m = re.match(r"^([\d.]+) 升 = （　）毫升。$", s)
    if m:
        return fmt(D(m.group(1)) * 1000)

    # ---- 分数的意义和性质 ----
    m = re.match(r"^(\d+)/(\d+) 的分数单位是（　）。$", s)
    if m:
        return "1/%s" % m.group(2)
    m = re.match(r"^(\d+)/(\d+) 里有（　）个 1/(\d+)。$", s)
    if m:
        return int(m.group(1))
    m = re.match(r"^把 (\d+) 个苹果平均分成 (\d+) 份，每份是这些苹果的（　）。$", s)
    if m:
        return "1/%s" % m.group(2)
    m = re.match(r"^把 (\d+) 个苹果平均分成 (\d+) 份，每份有（　）个。$", s)
    if m:
        return int(m.group(1)) // int(m.group(2))
    m = re.match(r"^把 (\d+) 米长的绳子平均分成 (\d+) 段，每段长（　）米。$", s)
    if m:
        return "%s/%s" % (m.group(1), m.group(2))
    m = re.match(r"^(\d+) ÷ (\d+) = （　）（用分数表示）。$", s)
    if m:
        return "%s/%s" % (m.group(1), m.group(2))
    m = re.match(r"^把 (\d+) 千克糖平均分给 (\d+) 个小朋友，每人分得（　）千克。$", s)
    if m:
        return "%s/%s" % (m.group(1), m.group(2))
    m = re.match(r"^(\d+)/(\d+) 是（　）。$", s)
    if m:
        return "真分数" if int(m.group(1)) < int(m.group(2)) else "假分数"
    m = re.match(r"^分母是 (\d+) 的真分数有（　）个。$", s)
    if m:
        return int(m.group(1)) - 1
    m = re.match(r"^把带分数 (\d+) 又 (\d+)/(\d+) 化成假分数是（　）。$", s)
    if m:
        w, n, d = map(int, m.groups())
        return "%d/%d" % (w * d + n, d)
    m = re.match(r"^(\d+)/(\d+) = （　）/(\d+)。$", s)
    if m:
        a, b, d = map(int, m.groups())
        return a * d // b
    m = re.match(r"^(\d+)/(\d+) = (\d+)/（　）。$", s)
    if m:
        a, b, c = map(int, m.groups())
        return b * c // a
    m = re.match(r"^把 (\d+)/(\d+) 的分子和分母同时除以 (\d+)，得到（　）。$", s)
    if m:
        return str(Fraction(int(m.group(1)), int(m.group(2))))
    m = re.match(r"^(\d+) 和 (\d+) 的最大公因数是（　）。$", s)
    if m:
        return math.gcd(int(m.group(1)), int(m.group(2)))
    m = re.match(r"^把 (\d+)/(\d+) 化成最简分数是（　）。$", s)
    if m:
        return str(Fraction(int(m.group(1)), int(m.group(2))))
    m = re.match(r"^(\d+) 和 (\d+) 的最小公倍数是（　）。$", s)
    if m:
        a, b = map(int, m.groups())
        return a * b // math.gcd(a, b)
    m = re.match(r"^把 (\d+)/(\d+) 和 (\d+)/(\d+) 通分，公分母是（　）。$", s)
    if m:
        d1, d2 = int(m.group(2)), int(m.group(4))
        return d1 * d2 // math.gcd(d1, d2)
    m = re.match(r"^比较大小：(\d+)/(\d+) ○ (\d+)/(\d+)，○ 里应填（　）。$", s)
    if m:
        f1 = Fraction(int(m.group(1)), int(m.group(2)))
        f2 = Fraction(int(m.group(3)), int(m.group(4)))
        return "＞" if f1 > f2 else ("＜" if f1 < f2 else "＝")
    m = re.match(r"^把 (\d+)/(\d+) 化成小数是（　）。$", s)
    if m:
        return fmt(Decimal(int(m.group(1))) / Decimal(int(m.group(2))))
    m = re.match(r"^把 ([\d.]+) 化成分数是（　）。$", s)
    if m:
        return str(Fraction(Decimal(m.group(1))))

    # ---- 分数加减（先三数、后两数） ----
    m = re.match(r"^计算：(\d+/\d+) ([+\-]) (\d+/\d+) ([+\-]) (\d+/\d+) = （　）$", s)
    if m:
        v = Fraction(m.group(1))
        v = v + Fraction(m.group(3)) if m.group(2) == "+" else v - Fraction(m.group(3))
        v = v + Fraction(m.group(5)) if m.group(4) == "+" else v - Fraction(m.group(5))
        return str(v)
    m = re.match(r"^计算：(\d+|\d+/\d+) ([+\-]) (\d+/\d+) = （　）$", s)
    if m:
        v = Fraction(m.group(1))
        v = v + Fraction(m.group(3)) if m.group(2) == "+" else v - Fraction(m.group(3))
        return str(v)

    # ---- 多边形面积 ----
    m = re.match(r"^一个平行四边形的底是 (\d+) 厘米，高是 (\d+) 厘米，面积是（　）平方厘米。$", s)
    if m:
        return int(m.group(1)) * int(m.group(2))
    m = re.match(r"^一个平行四边形的面积是 (\d+) 平方厘米，底是 (\d+) 厘米，高是（　）厘米。$", s)
    if m:
        return int(m.group(1)) // int(m.group(2))
    m = re.match(r"^一个三角形的底是 (\d+) 厘米，高是 (\d+) 厘米，面积是（　）平方厘米。$", s)
    if m:
        return int(m.group(1)) * int(m.group(2)) // 2
    m = re.match(r"^一个三角形的面积是 (\d+) 平方厘米，底是 (\d+) 厘米，高是（　）厘米。$", s)
    if m:
        return 2 * int(m.group(1)) // int(m.group(2))
    m = re.match(r"^一个梯形的上底是 (\d+) 厘米，下底是 (\d+) 厘米，高是 (\d+) 厘米，面积是（　）平方厘米。$", s)
    if m:
        a, b, h = map(int, m.groups())
        return (a + b) * h // 2
    m = re.match(r"^一个梯形的面积是 (\d+) 平方厘米，上底是 (\d+) 厘米，下底是 (\d+) 厘米，高是（　）厘米。$", s)
    if m:
        s0, a, b = map(int, m.groups())
        return 2 * s0 // (a + b)
    m = re.match(r"^一个组合图形由一个长 (\d+) 米、宽 (\d+) 米的长方形和一个底 (\d+) 米、高 (\d+) 米的三角形拼成，"
                 r"它的面积是（　）平方米。$", s)
    if m:
        L, W, b, h = map(int, m.groups())
        return L * W + b * h // 2
    m = re.match(r"^一个长 (\d+) 米、宽 (\d+) 米的长方形，去掉一个底 (\d+) 米、高 (\d+) 米的三角形后，"
                 r"剩下部分的面积是（　）平方米。$", s)
    if m:
        L, W, b, h = map(int, m.groups())
        return L * W - b * h // 2
    m = re.match(r"^一个组合图形由两个长方形组成，一个长 (\d+) 米、宽 (\d+) 米，另一个长 (\d+) 米、宽 (\d+) 米，"
                 r"面积一共是（　）平方米。$", s)
    if m:
        L1, W1, L2, W2 = map(int, m.groups())
        return L1 * W1 + L2 * W2

    # ---- 植树问题 ----
    m = re.match(r"^一条 (\d+) 米长的小路，每隔 (\d+) 米栽一棵树（(.+?)），一共要栽（　）棵树。$", s)
    if m:
        seg = int(m.group(1)) // int(m.group(2))
        kind = m.group(3)
        if kind == "两端都栽":
            return seg + 1
        if kind == "两端都不栽":
            return seg - 1
        return seg
    m = re.match(r"^一个圆形池塘的周长是 (\d+) 米，每隔 (\d+) 米栽一棵树，一共要栽（　）棵树。$", s)
    if m:
        return int(m.group(1)) // int(m.group(2))
    m = re.match(r"^把一根木头锯成 (\d+) 段，每锯一次要 (\d+) 分钟，一共要（　）分钟。$", s)
    if m:
        return (int(m.group(1)) - 1) * int(m.group(2))
    m = re.match(r"^从 1 楼走到 (\d+) 楼，每上一层楼要走 (\d+) 级台阶，一共要走（　）级台阶。$", s)
    if m:
        return (int(m.group(1)) - 1) * int(m.group(2))

    # ---- 简易方程 ----
    m = re.match(r"^当 x = (\d+) 时，(\d+)x \+ (\d+) 的值是（　）。$", s)
    if m:
        return int(m.group(2)) * int(m.group(1)) + int(m.group(3))
    m = re.match(r"^每支笔 a 元，买 (\d+) 支要（　）元。$", s)
    if m:
        return "%sa" % m.group(1)
    m = re.match(r"^用含有字母的式子表示：比 x 的 (\d+) 倍多 (\d+) 的数写作（　）。$", s)
    if m:
        return "%sx + %s" % (m.group(1), m.group(2))
    m = re.match(r"^用含有字母的式子表示：比 x 的 (\d+) 倍少 (\d+) 的数写作（　）。$", s)
    if m:
        return "%sx - %s" % (m.group(1), m.group(2))
    m = re.match(r"^根据等式的性质，如果 a = b，那么 a \+ (\d+) = b \+ （　）。$", s)
    if m:
        return int(m.group(1))
    m = re.match(r"^根据等式的性质，如果 a = b，那么 a - (\d+) = b - （　）。$", s)
    if m:
        return int(m.group(1))
    m = re.match(r"^根据等式的性质，如果 a = b，那么 a × (\d+) = b × （　）。$", s)
    if m:
        return int(m.group(1))
    m = re.match(r"^解方程：x \+ ([\d.]+) = ([\d.]+)，x = （　）。$", s)
    if m:
        return fmt(D(m.group(2)) - D(m.group(1)))
    m = re.match(r"^解方程：x - ([\d.]+) = ([\d.]+)，x = （　）。$", s)
    if m:
        return fmt(D(m.group(1)) + D(m.group(2)))
    m = re.match(r"^解方程：(\d+)x = (\d+)，x = （　）。$", s)
    if m:
        return int(m.group(2)) // int(m.group(1))
    m = re.match(r"^解方程：x ÷ (\d+) = (\d+)，x = （　）。$", s)
    if m:
        return int(m.group(1)) * int(m.group(2))
    m = re.match(r"^解方程：(\d+)x \+ (\d+) = (\d+)，x = （　）。$", s)
    if m:
        return (int(m.group(3)) - int(m.group(2))) // int(m.group(1))
    m = re.match(r"^一个数的 (\d+) 倍加上 (\d+) 等于 (\d+)，这个数是（　）。$", s)
    if m:
        return (int(m.group(3)) - int(m.group(2))) // int(m.group(1))
    m = re.match(r"^一个数的 (\d+) 倍减去 (\d+) 等于 (\d+)，这个数是（　）。$", s)
    if m:
        return (int(m.group(3)) + int(m.group(2))) // int(m.group(1))
    m = re.match(r"^甲数是乙数的 (\d+) 倍，甲乙两数的和是 (\d+)，乙数是（　）。$", s)
    if m:
        return int(m.group(2)) // (int(m.group(1)) + 1)

    # ---- 循环小数与规律 ----
    m = re.match(r"^循环小数 0\.(\d+)…（循环节重复 3 次）的循环节是（　）。$", s)
    if m:
        ds = m.group(1)
        return ds[:len(ds) // 3]
    m = re.match(r"^把循环小数 ([\d.]+)… 保留两位小数是（　）。$", s)
    if m:
        return rnd(D(m.group(1)), 2)
    m = re.match(r"^根据规律：1 ÷ 9 = 0\.111…，2 ÷ 9 = 0\.222…，那么 (\d+) ÷ 9 = （　）。$", s)
    if m:
        return "0.%s…" % (m.group(1) * 3)
    m = re.match(r"^根据规律：1 ÷ 11 = 0\.0909…，2 ÷ 11 = 0\.1818…，那么 (\d+) ÷ 11 = （　）。$", s)
    if m:
        return "0.%s…" % ("%02d" % (int(m.group(1)) * 9) * 3)

    # ---- 进一法 / 去尾法 ----
    m = re.match(r"^每个纸箱最多装 (\d+) 千克苹果，装 (\d+) 千克苹果至少需要（　）个纸箱。$", s)
    if m:
        cap, tot = int(m.group(1)), int(m.group(2))
        return -(-tot // cap)
    m = re.match(r"^每套衣服用布 ([\d.]+) 米，([\d.]+) 米布最多可以做（　）套衣服。$", s)
    if m:
        return int(D(m.group(2)) // D(m.group(1)))
    m = re.match(r"^一根绳子长 ([\d.]+) 米，每 ([\d.]+) 米截一段，最多可以截成（　）段。$", s)
    if m:
        return int(D(m.group(1)) // D(m.group(2)))

    # ---- 小数乘除法：三数（运算定律） ----
    m = re.match(r"^用乘法分配律计算：([\d.]+) × \(([\d.]+) \+ ([\d.]+)\) = （　）。$", s)
    if m:
        return fmt(D(m.group(1)) * (D(m.group(2)) + D(m.group(3))))
    m = re.match(r"^用乘法交换律和结合律计算：([\d.]+) × (\d+) × ([\d.]+) = （　）。$", s)
    if m:
        return fmt(D(m.group(1)) * int(m.group(2)) * D(m.group(3)))
    m = re.match(r"^用乘法分配律计算：(\d+) × ([\d.]+) \+ (\d+) × ([\d.]+) = （　）。$", s)
    if m:
        return fmt((int(m.group(1)) + int(m.group(3))) * D(m.group(2)))

    # ---- 小数乘除法：两数 ----
    m = re.match(r"^计算：([\d.]+) × (\d+) = （　）$", s)
    if m:
        return fmt(D(m.group(1)) * int(m.group(2)))
    m = re.match(r"^计算：(\d+) × ([\d.]+) = （　）$", s)
    if m:
        return fmt(int(m.group(1)) * D(m.group(2)))
    m = re.match(r"^计算：([\d.]+) × ([\d.]+) = （　）$", s)
    if m:
        return fmt(D(m.group(1)) * D(m.group(2)))
    m = re.match(r"^计算：([\d.]+) ÷ (\d+) = （　）$", s)
    if m:
        return fmt(D(m.group(1)) / int(m.group(2)))
    m = re.match(r"^计算：([\d.]+) ÷ ([\d.]+) = （　）$", s)
    if m:
        return fmt(D(m.group(1)) / D(m.group(2)))
    m = re.match(r"^计算：([\d.]+) \+ ([\d.]+) = （　）$", s)
    if m:
        return fmt(D(m.group(1)) + D(m.group(2)))
    m = re.match(r"^计算：([\d.]+) - ([\d.]+) = （　）$", s)
    if m:
        return fmt(D(m.group(1)) - D(m.group(2)))
    m = re.match(r"^计算：([\d.]+) × ([\d.]+) ≈ （　）（保留(.+?)）。$", s)
    if m:
        return rnd(D(m.group(1)) * D(m.group(2)), nd_of(m.group(3)))
    m = re.match(r"^计算：([\d.]+) ÷ (\d+) ≈ （　）（保留(.+?)）。$", s)
    if m:
        return rnd(D(m.group(1)) / int(m.group(2)), nd_of(m.group(3)))
    m = re.match(r"^计算 ([\d.]+) ÷ ([\d.]+) 时，把除数变成整数，被除数和除数要同时扩大到原来的（　）倍。$", s)
    if m:
        return 10 ** len(m.group(2).split(".")[1])
    m = re.match(r"^([\d.]+) × ([\d.]+) 的积有（　）位小数。$", s)
    if m:
        p = fmt(D(m.group(1)) * D(m.group(2)))
        return len(p.split(".")[1]) if "." in p else 0

    # ---- 小数乘除法：应用题 ----
    m = re.match(r"^每千克苹果 ([\d.]+) 元，买 (\d+) 千克要付（　）元。$", s)
    if m:
        return fmt(D(m.group(1)) * int(m.group(2)))
    m = re.match(r"^苹果每千克 ([\d.]+) 元，买 ([\d.]+) 千克应付（　）元。$", s)
    if m:
        return fmt(D(m.group(1)) * D(m.group(2)))
    m = re.match(r"^一辆汽车每小时行驶 ([\d.]+) 千米，([\d.]+) 小时行驶（　）千米。$", s)
    if m:
        return fmt(D(m.group(1)) * D(m.group(2)))
    m = re.match(r"^铺 1 平方米草坪要 ([\d.]+) 元，铺 ([\d.]+) 平方米要（　）元。$", s)
    if m:
        return fmt(D(m.group(1)) * D(m.group(2)))
    m = re.match(r"^一个长方形的长是 ([\d.]+) 米、宽是 ([\d.]+) 米，面积是（　）平方米。$", s)
    if m:
        return fmt(D(m.group(1)) * D(m.group(2)))
    m = re.match(r"^把 ([\d.]+) 米长的铁丝平均分成 (\d+) 段，每段长（　）米。$", s)
    if m:
        return fmt(D(m.group(1)) / int(m.group(2)))
    m = re.match(r"^把 ([\d.]+) 千克糖果平均分装在 (\d+) 个袋子里，每袋重（　）千克。$", s)
    if m:
        return fmt(D(m.group(1)) / int(m.group(2)))
    m = re.match(r"^一辆汽车 ([\d.]+) 小时行驶 ([\d.]+) 千米，平均每小时行驶（　）千米。$", s)
    if m:
        return fmt(D(m.group(2)) / D(m.group(1)))

    return None


def verify(units):
    """按题干反解重算，与标注答案比对（只查程序化生成的题，手写概念题跳过）。"""
    total = 0
    bad = 0
    for uname, lessons in units:
        for lname, _bc, qs in lessons:
            for q in qs:
                stem = q[1]
                ans = str(q[2][0])
                v = expect_g5(stem)
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
