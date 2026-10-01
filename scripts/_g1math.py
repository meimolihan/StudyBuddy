# -*- coding: utf-8 -*-
"""一年级数学（人教版 2024 新版）出题器：上、下两册共用。

设计要点：数字范围严格按教材（上册 5 以内 → 10 以内 → 20 以内进位加；下册 20 以内退位减 →
100 以内数的认识 → 100 以内加减法）；答案由代码算出，干扰项取「相邻数、看错运算、
漏写一个十」等常见错误；固定随机种子，可复现、可验算。
"""
import random
import re

from _quizlib import S


def dstr(x):
    return str(x)


def N(stem, ans, ws):
    return S(stem, dstr(ans), [dstr(w) for w in ws])


def gen(fn, count, seed, *args, **kwargs):
    rng = random.Random(seed)
    qs, seen, tries = [], set(), 0
    while len(qs) < count and tries < count * 100:
        tries += 1
        q = fn(rng, *args, **kwargs)
        if not q or q[1] in seen:
            continue
        seen.add(q[1])
        qs.append(q)
    if len(qs) < count:
        raise SystemExit("出题不足：%s 只凑到 %d/%d" % (fn.__name__, len(qs), count))
    return qs


# ---------------- 数的认识 ----------------
def g_count(rng, lo=1, hi=5):
    """1~5（或 6~10）数的认识：比大小、相邻数、数序、多几少几。"""
    k = rng.randint(0, 5)
    a = rng.randint(lo, hi)
    b = rng.randint(lo, hi)
    if k == 0:
        if a == b:
            return None
        big, small = max(a, b), min(a, b)
        return N("%d 和 %d 相比，（　）大。" % (a, b), big, [small, big + 1, small - 1])
    if k == 1:
        if a <= lo:
            return None
        return N("比 %d 少 1 的数是（　）。" % a, a - 1, [a + 1, a, a - 2])
    if k == 2:
        if a >= hi:
            return None
        return N("比 %d 多 1 的数是（　）。" % a, a + 1, [a - 1, a, a + 2])
    if k == 3:
        n = rng.randint(lo + 1, hi - 1)
        return N("与 %d 相邻的两个数是（　）。" % n, "%d 和 %d" % (n - 1, n + 1),
                 ["%d 和 %d" % (n - 2, n - 1), "%d 和 %d" % (n + 1, n + 2), "%d 和 %d" % (n - 1, n)])
    if k == 4:
        n = rng.randint(lo, hi - 2)
        return N("%d、%d、（　）、%d，横线上应填（　）。" % (n, n + 1, n + 3), n + 2,
                 [n + 4, n - 1, n + 3])
    return N("比 %d 小 1 的数是（　）。" % a, a - 1, [a + 1, a, a - 2])


def g_split(rng, totals=(5,)):
    """分与合。"""
    total = rng.choice(totals) if not isinstance(totals, int) else totals
    a = rng.randint(0, total)
    if rng.random() < 0.5:
        stem = "%d 可以分成 %d 和（　）。" % (total, a)
    else:
        stem = "把 %d 分成两份，一份是 %d，另一份是（　）。" % (total, a)
    return N(stem, total - a, [total - a + 1, total - a - 1, total])


def g_combine(rng, totals=(10,)):
    total = rng.choice(totals) if not isinstance(totals, int) else totals
    a = rng.randint(1, total - 1)
    if rng.random() < 0.5:
        stem = "%d 和 %d 合起来是（　）。" % (a, total - a)
    else:
        stem = "把 %d 和 %d 合起来，一共是（　）。" % (a, total - a)
    return N(stem, total, [total + 1, total - 1, a])


def g_ordinal(rng):
    """第几。"""
    n = rng.randint(3, 9)
    k = rng.randint(1, n)
    return N("有 %d 个小动物排成一队，从左往右数，第 %d 个小动物前面有（　）个小动物。" % (n, k),
             k - 1, [k, k + 1, n - k])


# ---------------- 加减法 ----------------
def g_add(rng, lo, hi, total):
    a = rng.randint(lo, hi)
    b = rng.randint(lo, hi)
    if a + b > total:
        return None
    s = a + b
    k = rng.randint(0, 2)
    if k == 0:
        stem = "计算：%d + %d = （　）" % (a, b)
    elif k == 1:
        stem = "%d 个和 %d 个合起来是（　）个。" % (a, b)
    else:
        if a == 0 or b == 0:
            return None
        stem = "小明有 %d 朵花，小红有 %d 朵花，两人一共有（　）朵。" % (a, b)
    return N(stem, s, [s + 1, s - 1, s + 2, abs(a - b) if a != b else s + 3])


def g_add_fixed(rng, a_choices, bmin, bmax, total, need_carry=False):
    """固定第一个加数（如「9 加几」）：a 从 a_choices 里取，b 随机，可选必须进位。"""
    a = a_choices if isinstance(a_choices, int) else rng.choice(a_choices)
    lo = max(bmin, 10 - a + 1) if need_carry else bmin
    if lo > bmax:
        return None
    b = rng.randint(lo, bmax)
    if a + b > total or (need_carry and a + b <= 10):
        return None
    s = a + b
    k = rng.randint(0, 2)
    if k == 0:
        stem = "计算：%d + %d = （　）" % (a, b)
    elif k == 1:
        stem = "%d 加 %d 得（　）。" % (a, b)
    else:
        c = 10 - a
        if not (1 <= c <= b):
            return None
        stem = ("用凑十法算：%d + %d，先算 %d + %d = 10，再算 10 + %d = （　）。"
                % (a, b, a, c, b - c))
    return N(stem, s, [s + 1, s - 1, s + 2, s - 10 if s > 10 else s + 3])


def g_sub(rng, lo, hi, total):
    a = rng.randint(lo, hi)
    b = rng.randint(lo, min(hi, a))
    if a - b < 0:
        return None
    d = a - b
    if rng.random() < 0.5:
        stem = "计算：%d - %d = （　）" % (a, b)
    else:
        stem = "从 %d 里去掉 %d，还剩（　）。" % (a, b)
    return N(stem, d, [d + 1, d - 1, d + 2, a + b])


def g_teen_sub(rng, kind):
    """20 以内退位减法（下册）：十几减 9 / 8、7、6 / 5、4、3、2。"""
    if kind == "9":
        b = 9
    elif kind == "876":
        b = rng.choice([6, 7, 8])
    else:
        b = rng.choice([2, 3, 4, 5])
    a = rng.randint(b + 1, 18)
    if a <= b or a - b >= 10:
        return None                      # 只要退位（差小于 10）
    d = a - b
    k = rng.randint(0, 3)
    if k == 0:
        stem = "计算：%d - %d = （　）" % (a, b)
    elif k == 1:
        stem = ("用破十法算：%d - %d，先算 10 - %d = %d，再算 %d + %d = （　）。"
                % (a, b, b, 10 - b, a - 10, 10 - b))
    elif k == 2:
        stem = "想加法算减法：因为 %d + %d = %d，所以 %d - %d = （　）。" % (b, d, a, a, b)
    else:
        stem = "有 %d 个气球，飞走了 %d 个，还剩（　）个。" % (a, b)
    return N(stem, d, [d + 1, d - 1, a + b, 10 - b])


def g_place(rng, tmin, tmax):
    """数的组成：几个十和几个一。"""
    k = rng.randint(0, 3)
    t = rng.randint(tmin, tmax)
    o = rng.randint(1, 9)
    if k == 0:
        return N("%d 个十和 %d 个一合起来是（　）。" % (t, o), t * 10 + o,
                 [t + o, t * 10, o * 10 + t, t * 10 + o + 10])
    if k == 1:
        return N("%d 里面有 %d 个十和（　）个一。" % (t * 10 + o, t), o,
                 [t, o + 1, o - 1])
    if k == 2:
        return N("%d 里面有（　）个十和 %d 个一。" % (t * 10 + o, o), t,
                 [t + 1, o, t - 1])
    return N("%d 个一和 %d 个十合起来是（　）。" % (o, t), t * 10 + o,
             [o * 10 + t, t + o, t * 10 + o + 1, t * 10])


def g_teen_add(rng):
    """十几加几（不进位）和相应的减法。"""
    a = rng.randint(11, 18)
    b = rng.randint(1, 9 - (a - 10))
    if rng.random() < 0.5:
        s = a + b
        return N("计算：%d + %d = （　）" % (a, b), s, [s + 1, s - 1, s + 10, a - b])
    a = rng.randint(12, 19)
    b = rng.randint(1, a - 11)
    return N("计算：%d - %d = （　）" % (a, b), a - b, [a - b + 1, a - b - 1, a + b, a - b + 10])


def g_readwrite100(rng):
    """100 以内数的读法和写法。"""
    D = "零一二三四五六七八九"
    k = rng.randint(0, 3)
    t = rng.randint(1, 9)
    o = rng.randint(1, 9)
    n = t * 10 + o
    if k == 0:
        return N("%d 读作（　）。" % n, "%s十%s" % (D[t], D[o]),
                 ["%s%s" % (D[t], D[o]), "%s十" % D[o], "%s百%s" % (D[t], D[o]), "%s十%s" % (D[o], D[t])])
    if k == 1:
        return N("「%s十」写作（　）。" % D[t], t * 10, [t, t * 10 + 1, o * 10, t * 100])
    if k == 2:
        return N("「%s十%s」写作（　）。" % (D[t], D[o]), n, [o * 10 + t, t + o, t * 10, n + 10])
    m = rng.randint(0, 9)
    return N("%d 个十是（　）。" % t, t * 10, [t, t * 10 + 10, t * 10 - 10, t * 100])


def g_tens(rng, mode):
    """整十数加、减整十数（mode="add"/"sub"）。"""
    t = rng.randint(1, 8)
    u = rng.randint(1, 9 - t) if mode == "add" else rng.randint(1, t - 1)
    if u <= 0:
        return None
    a, b = t * 10, u * 10
    if mode == "add":
        return N("计算：%d + %d = （　）" % (a, b), a + b, [a + b + 10, a + b - 10, t + u])
    return N("计算：%d - %d = （　）" % (a, b), a - b, [a - b + 10, a - b - 10, a + b])


def g_more_less(rng):
    """求比一个数多几、少几的数。"""
    a = rng.randint(10, 70)
    b = rng.randint(2, 20)
    if rng.random() < 0.5:
        return N("小明有 %d 张卡片，小红比小明多 %d 张，小红有（　）张。" % (a, b), a + b,
                 [a - b, a, a + b + 1])
    if a - b <= 0:
        return None
    return N("小明有 %d 张卡片，小红比小明少 %d 张，小红有（　）张。" % (a, b), a - b,
             [a + b, a, a - b + 1])


def g_chain100(rng):
    """100 以内的连加、连减和加减混合。"""
    k = rng.randint(0, 2)
    a = rng.randint(20, 60)
    b = rng.randint(5, 30)
    c = rng.randint(5, 30)
    if k == 0:
        if a + b + c > 100:
            return None
        return N("计算：%d + %d + %d = （　）" % (a, b, c), a + b + c,
                 [a + b, a + b + c + 10, a + b + c - 10])
    if k == 1:
        if a - b - c <= 0:
            return None
        return N("计算：%d - %d - %d = （　）" % (a, b, c), a - b - c,
                 [a - b, a - b - c + 10, a - b - c - 10])
    if a + b - c <= 0:
        return None
    return N("计算：%d + %d - %d = （　）" % (a, b, c), a + b - c,
             [a + b, a + b - c + 10, a + b - c - 10])


def g_mix(rng, total=10):
    """连加、连减、加减混合。"""
    k = rng.randint(0, 2)
    a = rng.randint(1, total - 2)
    b = rng.randint(1, total - a)
    c = rng.randint(1, max(1, a + b - 1))
    if k == 0:
        if a + b + 1 > total:
            return None
        c = rng.randint(1, total - a - b)
        return N("计算：%d + %d + %d = （　）" % (a, b, c), a + b + c,
                 [a + b + c + 1, a + b, a + b + c - 1])
    if k == 1:
        if a + b < 2:
            return None
        return N("计算：%d + %d - %d = （　）" % (a, b, c % (a + b) + 1), a + b - (c % (a + b) + 1),
                 [a + b - (c % (a + b) + 1) + 1, a + b + c, a + b])
    s = rng.randint(4, total)
    x = rng.randint(1, s - 2)
    y = rng.randint(1, s - x)
    return N("计算：%d - %d + %d = （　）" % (s, x, y), s - x + y,
             [s - x + y + 1, s - x + y - 1, s - x - y])


# ---------------- 下册：100 以内 ----------------
def g_num100(rng):
    """100 以内数的认识：组成、读法、比较大小、数序。"""
    k = rng.randint(0, 5)
    if k == 0:
        t = rng.randint(2, 9)
        o = rng.randint(1, 9)
        return N("%d 个十和 %d 个一合起来是（　）。" % (t, o), t * 10 + o,
                 [t + o, t * 10 + o + 10, t * 10, o * 10 + t])
    if k == 1:
        n = rng.randint(11, 99)
        if n % 10 == 0:
            return None
        return N("%d 里面有（　）个十和 %d 个一。" % (n, n % 10), n // 10,
                 [n // 10 + 1, n % 10, n // 10 - 1])
    if k == 2:
        n = rng.randint(2, 9)
        return N("%d 个十是（　）。" % n, n * 10, [n, n * 10 + 10, n * 10 - 10])
    if k == 3:
        a = rng.randint(10, 99)
        b = rng.randint(10, 99)
        if a == b:
            return None
        return N("比 %d 与 %d 的大小：%d ○ %d，○ 里应填（　）。" % (a, b, a, b),
                 ">" if a > b else "<", ["<" if a > b else ">", "=", "不能比较"])
    if k == 4:
        n = rng.randint(10, 98)
        return N("与 %d 相邻的两个数是（　）。" % n, "%d 和 %d" % (n - 1, n + 1),
                 ["%d 和 %d" % (n - 2, n - 1), "%d 和 %d" % (n + 1, n + 2), "%d 和 %d" % (n, n + 1)])
    n = rng.randint(1, 9)
    return N("%d 个十和 %d 个一合起来是（　）。" % (n, 0), n * 10,
             [n, n * 10 + 10, n * 10 - 10])


def g_round10(rng, mode=None):
    """整十数加减整十数、两位数加减一位数/整十数（口算）。

    mode: None 全混合 / "tens" 整十数±整十数 / "add" 加法 / "sub" 减法 /
          "a1" 加一位数 / "s1" 减一位数 / "at" 加整十数 / "st" 减整十数
    """
    mode_kinds = {None: [0, 1, 2, 3, 4, 5], "tens": [0, 1], "add": [0, 2, 4],
                  "sub": [1, 3, 5], "a1": [2], "s1": [3], "at": [4], "st": [5]}
    kinds = mode_kinds.get(mode, [0, 1, 2, 3, 4, 5])
    k = rng.choice(kinds)
    t = rng.randint(1, 8)
    u = rng.randint(1, 9)
    if k == 0:
        s = t * 10 + u * 10
        if s > 100:
            return None
        return N("计算：%d + %d = （　）" % (t * 10, u * 10), s, [s + 10, s - 10, t * 10 + u])
    if k == 1:
        a, b = sorted([t * 10, u * 10], reverse=True)
        if a - b < 0:
            return None
        return N("计算：%d - %d = （　）" % (a, b), a - b, [a - b + 10, a - b - 10, a + b])
    if k == 2:
        n = rng.randint(2, 9) * 10 + rng.randint(1, 9)
        s = n + u
        if s > 100:
            return None
        return N("计算：%d + %d = （　）" % (n, u), s, [s + 1, s - 10, s + 10, n])
    if k == 3:
        n = rng.randint(2, 9) * 10 + rng.randint(1, 9)
        u2 = rng.randint(1, 9)
        if n - u2 < 10:
            return None
        return N("计算：%d - %d = （　）" % (n, u2), n - u2, [n - u2 + 1, n - u2 - 1, n + u2])
    if k == 4:
        n = rng.randint(2, 9) * 10 + rng.randint(1, 9)
        t2 = rng.randint(1, 8) * 10
        if n + t2 > 100:
            return None
        return N("计算：%d + %d = （　）" % (n, t2), n + t2, [n + t2 + 10, n + t2 - 10, n])
    n = rng.randint(3, 9) * 10 + rng.randint(1, 9)
    t2 = rng.randint(1, n // 10 - 1) * 10
    return N("计算：%d - %d = （　）" % (n, t2), n - t2, [n - t2 + 10, n - t2 - 10, n + t2])


def g_tens_unit(rng, mode=None):
    """整十数加一位数及相应的减法。mode: None 混合 / "add" / "sub"。"""
    t = rng.randint(2, 9) * 10
    u = rng.randint(1, 9)
    a = t + u
    if mode == "add":
        k = 0
    elif mode == "sub":
        k = rng.randint(1, 2)
    else:
        k = rng.randint(0, 2)
    if k == 0:
        return N("计算：%d + %d = （　）" % (t, u), a, [a + 1, a - 1, a + 10, t])
    if k == 1:
        return N("计算：%d - %d = （　）" % (a, u), t, [t + 10, t + 1, a + u, u])
    return N("计算：%d - %d = （　）" % (a, t), u, [u + 10, u + 1, u - 1 if u > 1 else u + 2, a])


def g_order100(rng):
    """100 以内数的顺序与比较大小。"""
    k = rng.randint(0, 4)
    if k == 0:
        a = rng.randint(11, 99)
        b = rng.randint(11, 99)
        if a == b:
            return None
        return N("比 %d 与 %d 的大小：%d ○ %d，○ 里应填（　）。" % (a, b, a, b),
                 ">" if a > b else "<",
                 ["<" if a > b else ">", "=", "不能比较"])
    if k == 1:
        n = rng.randint(11, 98)
        return N("比 %d 多 1 的数是（　）。" % n, n + 1, [n - 1, n, n + 2])
    if k == 2:
        n = rng.randint(12, 99)
        return N("比 %d 少 1 的数是（　）。" % n, n - 1, [n + 1, n, n - 2])
    if k == 3:
        n = rng.randint(11, 98)
        return N("与 %d 相邻的两个数是（　）。" % n, "%d 和 %d" % (n - 1, n + 1),
                 ["%d 和 %d" % (n - 2, n - 1), "%d 和 %d" % (n + 1, n + 2), "%d 和 %d" % (n, n + 1)])
    nums = rng.sample(range(11, 100), 4)
    a, b, c, d = nums
    if rng.random() < 0.5:
        return N("在 %d、%d、%d、%d 这四个数中，最大的是（　）。" % (a, b, c, d), max(nums),
                 sorted(nums)[:3])
    return N("在 %d、%d、%d、%d 这四个数中，最小的是（　）。" % (a, b, c, d), min(nums),
             sorted(nums, reverse=True)[:3])


def g_shopping(rng):
    """购物中的数学：总价、找钱、比贵贱、元角换算。"""
    k = rng.randint(0, 3)
    p = rng.randint(1, 9)
    n = rng.randint(2, 5)
    if k == 0:
        return N("一本练习本 %d 元，买 %d 本一共要（　）元。" % (p, n), p * n,
                 [p + n, p * n + 1, p * n - 1])
    if k == 1:
        m = rng.choice([10, 20, 50])
        cost = rng.randint(1, 9)
        if cost >= m:
            return None
        return N("一支笔 %d 元，付给售货员 %d 元，应找回（　）元。" % (cost, m), m - cost,
                 [m + cost, m - cost + 1, m - cost - 1])
    if k == 2:
        a = rng.randint(2, 9)
        b = rng.randint(a + 1, 15)
        return N("一块橡皮 %d 角，一把尺子 %d 角，橡皮比尺子便宜（　）角。" % (a, b), b - a,
                 [a + b, b - a + 1, b - a - 1])
    y = rng.randint(1, 5)
    j = rng.randint(1, 9)
    return N("%d 元 %d 角 = （　）角。" % (y, j), y * 10 + j, [y + j, y * 10, j * 10])


def g_teen_compare(rng):
    """20 以内退位减法的应用：比多少、还剩多少。"""
    k = rng.randint(0, 2)
    b = rng.choice([6, 7, 8, 9])
    a = rng.randint(b + 1, 18)
    if a - b >= 10:
        return None
    if k == 0:
        return N("小红有 %d 朵花，小明有 %d 朵花，小红比小明多（　）朵。" % (a, b), a - b,
                 [a + b, a - b + 1, a - b - 1])
    if k == 1:
        return N("篮子里有 %d 个鸡蛋，拿走了 %d 个，还剩（　）个。" % (a, b), a - b,
                 [a + b, a - b + 1, a - b + 10])
    return N("停车场有 %d 辆汽车，开走了 %d 辆，还剩（　）辆。" % (a, b), a - b,
             [a + b, a - b - 1, a - b + 2])


def g_written_add(rng):
    """两位数加两位数（笔算，含进位）。"""
    a = rng.randint(11, 88)
    if 99 - a < 11:
        return None
    b = rng.randint(11, 99 - a)
    return N("计算：%d + %d = （　）" % (a, b), a + b,
             [a + b + 10, a + b - 10, a + b + 1, abs(a - b)])


def g_written_sub(rng):
    """两位数减两位数（笔算，含退位）。"""
    a = rng.randint(21, 99)
    b = rng.randint(11, a - 1)
    if a - b <= 0:
        return None
    return N("计算：%d - %d = （　）" % (a, b), a - b, [a - b + 10, a - b - 10, a - b + 1, a + b])


def g_relation(rng):
    """求比一个数多几、少几的数；连加连减。"""
    k = rng.randint(0, 3)
    a = rng.randint(10, 60)
    b = rng.randint(2, 20)
    if k == 0:
        return N("小明有 %d 张卡片，小红比小明多 %d 张，小红有（　）张。" % (a, b), a + b,
                 [a - b, a, a + b + 1])
    if k == 1:
        if a - b <= 0:
            return None
        return N("树上有 %d 只小鸟，飞走了 %d 只，还剩（　）只。" % (a, b), a - b,
                 [a + b, a - b + 1, a])
    if k == 2:
        c = rng.randint(2, 20)
        if a + b + c > 100:
            return None
        return N("篮子里有 %d 个苹果，又放进 %d 个，再放进 %d 个，一共有（　）个。" % (a, b, c),
                 a + b + c, [a + b, a + b + c + 1, a + b + c - 1])
    b2 = rng.randint(1, a - 1) if a > 1 else 1
    r = rng.randint(1, 30)
    return N("一本书有 %d 页，第一天看了 %d 页，第二天看了 %d 页，还剩（　）页。"
             % (a + b2 + r, a, b2), r, [a + b2, a + b2 + r, r + 1])


def g_money(rng):
    """认识人民币（欢乐购物街）。"""
    k = rng.randint(0, 3)
    if k == 0:
        return N("1 元 = （　）角。", 10, [1, 100, 5])
    if k == 1:
        return N("1 角 = （　）分。", 10, [1, 100, 5])
    if k == 2:
        y = rng.randint(1, 9)
        j = rng.randint(1, 9)
        return N("一支笔 %d 元 %d 角，用角作单位是（　）角。" % (y, j), y * 10 + j,
                 [y + j, y * 10, j * 10])
    p = rng.randint(1, 9)
    n = rng.randint(1, 5)
    return N("一本本子 %d 元，买 %d 本要（　）元。" % (p, n), p * n,
             [p + n, p * n + 1, p * n - 1])


# ---------------- 自动验算：题干反解 ----------------
_CN_DIGIT = "零一二三四五六七八九"


def _cn2int(ch):
    return _CN_DIGIT.index(ch) if ch in _CN_DIGIT else None


def expect_g1(stem):
    """按题干反解数字并重算答案；无法识别的题型（手工概念题）返回 None。

    所有生成器都用固定句式，按句式从前往后匹配即可；注意先匹配三数运算、
    再匹配两数运算，避免「a + b - c」被当成「a + b」。
    """
    s = stem
    m = None

    # ---- 三数连加 / 连减 / 加减混合 ----
    m = re.match(r"^计算：(\d+) \+ (\d+) \+ (\d+) = ", s)
    if m:
        return int(m.group(1)) + int(m.group(2)) + int(m.group(3))
    m = re.match(r"^计算：(\d+) - (\d+) - (\d+) = ", s)
    if m:
        return int(m.group(1)) - int(m.group(2)) - int(m.group(3))
    m = re.match(r"^计算：(\d+) \+ (\d+) - (\d+) = ", s)
    if m:
        return int(m.group(1)) + int(m.group(2)) - int(m.group(3))
    m = re.match(r"^计算：(\d+) - (\d+) \+ (\d+) = ", s)
    if m:
        return int(m.group(1)) - int(m.group(2)) + int(m.group(3))

    # ---- 两数加减 ----
    m = re.match(r"^计算：(\d+) \+ (\d+) = ", s)
    if m:
        return int(m.group(1)) + int(m.group(2))
    m = re.match(r"^计算：(\d+) - (\d+) = ", s)
    if m:
        return int(m.group(1)) - int(m.group(2))
    m = re.match(r"^用凑十法算：(\d+) \+ (\d+)，", s)
    if m:
        return int(m.group(1)) + int(m.group(2))
    m = re.match(r"^用破十法算：(\d+) - (\d+)，", s)
    if m:
        return int(m.group(1)) - int(m.group(2))
    m = re.match(r"^想加法算减法：因为 (\d+) \+ (\d+) = (\d+)，所以 (\d+) - (\d+) = ", s)
    if m:
        return int(m.group(2))
    m = re.match(r"^(\d+) 加 (\d+) 得（　）。", s)
    if m:
        return int(m.group(1)) + int(m.group(2))
    m = re.match(r"^(\d+) 个和 (\d+) 个合起来是", s)
    if m:
        return int(m.group(1)) + int(m.group(2))
    m = re.match(r"^小明有 (\d+) 朵花，小红有 (\d+) 朵花，两人一共有", s)
    if m:
        return int(m.group(1)) + int(m.group(2))
    m = re.match(r"^从 (\d+) 里去掉 (\d+)，还剩", s)
    if m:
        return int(m.group(1)) - int(m.group(2))

    # ---- 数的认识：比多少、相邻数、数序 ----
    m = re.match(r"^(\d+) 和 (\d+) 相比，", s)
    if m:
        return max(int(m.group(1)), int(m.group(2)))
    m = re.match(r"^比 (\d+) 少 1 的数是", s)
    if m:
        return int(m.group(1)) - 1
    m = re.match(r"^比 (\d+) 多 1 的数是", s)
    if m:
        return int(m.group(1)) + 1
    m = re.match(r"^比 (\d+) 小 1 的数是", s)
    if m:
        return int(m.group(1)) - 1
    m = re.match(r"^与 (\d+) 相邻的两个数是", s)
    if m:
        n = int(m.group(1))
        return "%d 和 %d" % (n - 1, n + 1)
    m = re.match(r"^(\d+)、(\d+)、（　）、(\d+)，横线上应填", s)
    if m:
        return int(m.group(1)) + 2
    m = re.match(r"^在 (\d+)、(\d+)、(\d+)、(\d+) 这四个数中，最大的是", s)
    if m:
        return max(int(m.group(i)) for i in range(1, 5))
    m = re.match(r"^在 (\d+)、(\d+)、(\d+)、(\d+) 这四个数中，最小的是", s)
    if m:
        return min(int(m.group(i)) for i in range(1, 5))

    # ---- 分与合、合起来 ----
    m = re.match(r"^(\d+) 可以分成 (\d+) 和（　）。", s)
    if m:
        return int(m.group(1)) - int(m.group(2))
    m = re.match(r"^把 (\d+) 分成两份，一份是 (\d+)，另一份是", s)
    if m:
        return int(m.group(1)) - int(m.group(2))
    m = re.match(r"^(\d+) 和 (\d+) 合起来是（　）。", s)
    if m:
        return int(m.group(1)) + int(m.group(2))
    m = re.match(r"^把 (\d+) 和 (\d+) 合起来，一共是", s)
    if m:
        return int(m.group(1)) + int(m.group(2))
    m = re.match(r"^(\d+) 个十和 (\d+) 个一合起来是", s)
    if m:
        return int(m.group(1)) * 10 + int(m.group(2))
    m = re.match(r"^(\d+) 个一和 (\d+) 个十合起来是", s)
    if m:
        return int(m.group(1)) + int(m.group(2)) * 10
    m = re.match(r"^(\d+) 里面有 (\d+) 个十和（　）个一。", s)
    if m:
        return int(m.group(1)) - int(m.group(2)) * 10
    m = re.match(r"^(\d+) 里面有（　）个十和 (\d+) 个一。", s)
    if m:
        return (int(m.group(1)) - int(m.group(2))) // 10
    m = re.match(r"^(\d+) 个十是（　）。", s)
    if m:
        return int(m.group(1)) * 10

    # ---- 第几 ----
    m = re.match(r"^有 \d+ 个小动物排成一队，从左往右数，第 (\d+) 个小动物前面有", s)
    if m:
        return int(m.group(1)) - 1

    # ---- 读法 / 写法 ----
    m = re.match(r"^(\d+) 读作", s)
    if m:
        n = int(m.group(1))
        t, o = n // 10, n % 10
        return "%s十%s" % (_CN_DIGIT[t], _CN_DIGIT[o]) if o else "%s十" % _CN_DIGIT[t]
    m = re.match(r"^「(.)十」写作", s)
    if m:
        return _cn2int(m.group(1)) * 10
    m = re.match(r"^「(.)十(.)」写作", s)
    if m:
        return _cn2int(m.group(1)) * 10 + _cn2int(m.group(2))

    # ---- 比大小（○ 里填 > < =） ----
    m = re.match(r"^比 (\d+) 与 (\d+) 的大小：", s)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        return ">" if a > b else ("<" if a < b else "=")

    # ---- 求比一个数多几、少几 ----
    m = re.match(r"^小明有 (\d+) 张卡片，小红比小明多 (\d+) 张", s)
    if m:
        return int(m.group(1)) + int(m.group(2))
    m = re.match(r"^小明有 (\d+) 张卡片，小红比小明少 (\d+) 张", s)
    if m:
        return int(m.group(1)) - int(m.group(2))
    m = re.match(r"^树上有 (\d+) 只小鸟，飞走了 (\d+) 只，还剩", s)
    if m:
        return int(m.group(1)) - int(m.group(2))
    m = re.match(r"^小红有 (\d+) 朵花，小明有 (\d+) 朵花，小红比小明多", s)
    if m:
        return int(m.group(1)) - int(m.group(2))
    m = re.match(r"^篮子里有 (\d+) 个鸡蛋，拿走了 (\d+) 个，还剩", s)
    if m:
        return int(m.group(1)) - int(m.group(2))
    m = re.match(r"^停车场有 (\d+) 辆汽车，开走了 (\d+) 辆，还剩", s)
    if m:
        return int(m.group(1)) - int(m.group(2))
    m = re.match(r"^有 (\d+) 个气球，飞走了 (\d+) 个，还剩", s)
    if m:
        return int(m.group(1)) - int(m.group(2))
    m = re.match(r"^篮子里有 (\d+) 个苹果，又放进 (\d+) 个，再放进 (\d+) 个，一共有", s)
    if m:
        return int(m.group(1)) + int(m.group(2)) + int(m.group(3))
    m = re.match(r"^一本书有 (\d+) 页，第一天看了 (\d+) 页，第二天看了 (\d+) 页，还剩", s)
    if m:
        return int(m.group(1)) - int(m.group(2)) - int(m.group(3))

    # ---- 人民币 ----
    if s.startswith("1 元 = "):
        return 10
    if s.startswith("1 角 = "):
        return 10
    m = re.match(r"^一支笔 (\d+) 元 (\d+) 角，用角作单位是", s)
    if m:
        return int(m.group(1)) * 10 + int(m.group(2))
    m = re.match(r"^一本本子 (\d+) 元，买 (\d+) 本要", s)
    if m:
        return int(m.group(1)) * int(m.group(2))
    m = re.match(r"^一本练习本 (\d+) 元，买 (\d+) 本一共要", s)
    if m:
        return int(m.group(1)) * int(m.group(2))
    m = re.match(r"^一支笔 (\d+) 元，付给售货员 (\d+) 元，应找回", s)
    if m:
        return int(m.group(2)) - int(m.group(1))
    m = re.match(r"^一块橡皮 (\d+) 角，一把尺子 (\d+) 角，橡皮比尺子便宜", s)
    if m:
        return int(m.group(2)) - int(m.group(1))
    m = re.match(r"^(\d+) 元 (\d+) 角 = （　）角。", s)
    if m:
        return int(m.group(1)) * 10 + int(m.group(2))

    return None
