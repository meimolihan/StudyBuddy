# -*- coding: utf-8 -*-
"""二年级数学（人教版 2025 新版）出题器：上、下两册共用。

上册：分类与整理、1~6 表内乘除法、东南西北、厘米和米、7~9 表内乘除法。
下册：有余数的除法、数量间的乘除关系（倍）、万以内数的认识、万以内加减法、时间。
答案由代码算出；固定随机种子；expect_g2 供 --verify 自动验算。
"""
import random
import re

from _quizlib import S
from _g1math import dstr, N, gen, expect_g1


# ---------------- 上册：乘法 ----------------
def g_mul(rng, amin=1, amax=6, bmin=1, bmax=6):
    a = rng.randint(amin, amax)
    b = rng.randint(bmin, bmax)
    s = a * b
    return N("计算：%d × %d = （　）" % (a, b), s,
             [s + a, s - a, s + 1, s - 1, a + b])


def g_muljia(rng, amax=6, bmax=6):
    a = rng.randint(2, amax)
    b = rng.randint(2, bmax)
    c = rng.randint(1, 9)
    s = a * b + c
    return N("计算：%d × %d + %d = （　）" % (a, b, c), s,
             [s + 1, s - 1, a * b, a * b + c + 1])


def g_muljian(rng, amax=6, bmax=6):
    a = rng.randint(2, amax)
    b = rng.randint(2, bmax)
    c = rng.randint(1, a * b - 1)
    s = a * b - c
    return N("计算：%d × %d - %d = （　）" % (a, b, c), s,
             [s + 1, s - 1, a * b, a * b - c - 1])


def g_buy_mul(rng, pmax=9, nmax=9):
    p = rng.randint(2, pmax)
    n = rng.randint(2, nmax)
    s = p * n
    return N("一支笔 %d 元，买 %d 支要（　）元。" % (p, n), s,
             [s + p, s - p, p + n, s + 1])


# ---------------- 上册：除法 ----------------
def g_div(rng, amin=6, amax=36, bmax=6):
    b = rng.randint(2, bmax)
    q = rng.randint(2, amax // b)
    a = b * q
    return N("计算：%d ÷ %d = （　）" % (a, b), q,
             [q + 1, q - 1, a - b, a + b])


def g_div_box(rng, amax=30, kmax=6):
    a = rng.randint(6, amax)
    k = rng.randint(2, kmax)
    if a % k != 0:
        return None
    q = a // k
    return N("有 %d 个皮球，每 %d 个装一箱，可以装（　）箱。" % (a, k), q,
             [q + 1, q - 1, a - k, a + k])


def g_avg(rng, amax=24, kmax=6):
    a = rng.randint(6, amax)
    k = rng.randint(2, kmax)
    if a % k != 0:
        return None
    q = a // k
    return N("把 %d 块蛋糕平均分给 %d 个小朋友，每人分（　）块。" % (a, k), q,
             [q + 1, q - 1, a - k, a + k])


# ---------------- 上册：厘米和米 ----------------
def g_len_rest(rng):
    use = rng.randint(2, 9) * 10
    rest = 100 - use
    return N("一根绳子长 1 米，用去 %d 厘米，还剩（　）厘米。" % use, rest,
             [rest + 10, rest - 10, use, 100 - use - 1])


def g_len_sum(rng):
    a = rng.randint(2, 8) * 10
    b = rng.randint(1, 9) * 10
    if a + b > 100:
        return None
    return N("一根木条长 %d 厘米，另一根长 %d 厘米，两根一共长（　）厘米。" % (a, b), a + b,
             [a + b + 10, a + b - 10, abs(a - b), a + b + 1])


# ---------------- 上册：连续两问 ----------------
def g_two_step(rng):
    a = rng.randint(20, 60)
    b = rng.randint(5, 15)
    if a - b < 1:
        return None
    c = rng.randint(2, 9)
    s = a - b + c
    return N("车上原来有 %d 人，下去了 %d 人，又上来了 %d 人，现在车上有（　）人。" % (a, b, c), s,
             [s + 1, s - 1, a + b - c, a - b - c])


# ---------------- 下册：有余数的除法 ----------------
def g_rem(rng):
    b = rng.randint(2, 9)
    q = rng.randint(2, 9)
    r = rng.randint(1, b - 1)
    a = b * q + r
    k = rng.randint(0, 1)
    if k == 0:
        return N("%d ÷ %d = %d …… （　）" % (a, b, q), r,
                 [r + 1 if r + 1 < b else r - 1, q, b])
    return N("%d ÷ %d = （　）…… %d" % (a, b, r), q,
             [q + 1, q - 1, a - b * q, b])


def g_rem_bag(rng):
    b = rng.randint(3, 8)
    q = rng.randint(2, 8)
    r = rng.randint(1, b - 1)
    a = b * q + r
    k = rng.randint(0, 1)
    if k == 0:
        return N("有 %d 个苹果，每 %d 个装一袋，装了（　）袋。" % (a, b), q,
                 [q + 1, q - 1, q + 2, a - b])
    return N("有 %d 个苹果，每 %d 个装一袋，还剩（　）个。" % (a, b), r,
             [r + 1 if r + 1 < b else r - 1, b, a - b * q + 1])


# ---------------- 下册：倍 ----------------
def g_times_of(rng):
    a = rng.randint(2, 9)
    b = rng.randint(2, 9)
    s = a * b
    return N("%d 的 %d 倍是（　）。" % (a, b), s, [a + b, s + a, s - b, s + 1])


def g_times_is(rng):
    b = rng.randint(2, 9)
    q = rng.randint(2, 9)
    a = b * q
    return N("%d 是 %d 的（　）倍。" % (a, b), q, [q + 1, q - 1, a - b, a + b])


# ---------------- 下册：万以内数的认识 ----------------
def g_read4(rng):
    """四位数读法（含 0 的各种情况）。"""
    k = rng.randint(0, 3)
    if k == 0:      # 中间一个 0：4070
        a = rng.randint(1, 9)
        b = rng.randint(1, 9)
        n = a * 1000 + b * 10
        ans = "%d千零%d十" % (a, b)
        ws = ["%d千%d十" % (a, b), "%d千零%d百" % (a, b), "%d千%d百" % (a, b)]
    elif k == 1:    # 中间两个 0：4005
        a = rng.randint(1, 9)
        b = rng.randint(1, 9)
        n = a * 1000 + b
        ans = "%d千零%d" % (a, b)
        ws = ["%d千%d" % (a, b), "%d千零百零%d" % (a, b), "%d千百%d" % (a, b)]
    elif k == 2:    # 末尾两个 0：4200
        a = rng.randint(1, 9)
        b = rng.randint(1, 9)
        n = a * 1000 + b * 100
        ans = "%d千%d百" % (a, b)
        ws = ["%d千零%d十" % (a, b), "%d千%d" % (a, b), "%d千%d十" % (a, b)]
    else:           # 无 0：3452
        a, b, c, d = (rng.randint(1, 9) for _ in range(4))
        n = a * 1000 + b * 100 + c * 10 + d
        ans = "%d千%d百%d十%d" % (a, b, c, d)
        ws = ["%d千%d百零%d十%d" % (a, b, c, d), "%d千%d百%d" % (a, b, c),
              "%d千%d十%d百%d" % (a, b, c, d)]
    return N("%d 读作（　）。" % n, ans, ws)


def g_write4(rng):
    """组成 → 写作。"""
    k = rng.randint(0, 2)
    if k == 0:
        a = rng.randint(1, 9)
        b = rng.randint(1, 9)
        n = a * 1000 + b
        return N("由 %d 个千和 %d 个一组成的数是（　）。" % (a, b), n,
                 [a * 1000 + b * 100, a * 100 + b, a * 1000 + b * 10, a + b])
    if k == 1:
        a = rng.randint(1, 9)
        b = rng.randint(1, 9)
        n = a * 1000 + b * 100
        return N("由 %d 个千和 %d 个百组成的数是（　）。" % (a, b), n,
                 [a * 1000 + b * 10, a * 100 + b, a * 1000 + b, a + b])
    a = rng.randint(1, 9)
    b = rng.randint(1, 9)
    c = rng.randint(1, 9)
    n = a * 1000 + b * 100 + c
    return N("由 %d 个千、%d 个百和 %d 个一组成的数是（　）。" % (a, b, c), n,
             [a * 1000 + b * 100 + c * 10, a * 1000 + b * 10 + c, a * 100 + b * 10 + c, a + b + c])


def g_comp4(rng):
    a = rng.randint(100, 9999)
    b = rng.randint(100, 9999)
    if a == b:
        return None
    ans = "＞" if a > b else "＜"
    ws = ["＜" if a > b else "＞", "＝", "≥"]
    return N("%d ○ %d，○ 里填（　）。" % (a, b), ans, ws)


def g_round4(rng):
    a = rng.randint(45, 54) * 100 + rng.randint(1, 99)
    return N("学校图书馆有图书 %d 册，大约是（　）册。" % a, round(a, -3),
             [round(a, -3) + 1000, round(a, -3) - 1000, a, round(a, -2)])


def g_hundreds(rng):
    k = rng.randint(0, 2)
    if k == 0:
        n = rng.randint(2, 9) * 1000
        return N("%d 里面有（　）个百。" % n, n // 100, [n // 1000, n // 10, 100])
    if k == 1:
        n = rng.randint(2, 9) * 1000
        return N("%d 里面有（　）个千。" % n, n // 1000, [n // 100, 10, 100])
    n = rng.randint(2, 9) * 100
    return N("%d 里面有（　）个十。" % n, n // 10, [n // 100, 10, n])


# ---------------- 下册：整百整十加减、万以内加减法 ----------------
def g_whole(rng):
    k = rng.randint(0, 2)
    if k == 0:      # 整百加整百
        a = rng.randint(1, 9) * 100
        b = rng.randint(1, 9) * 100
        s = a + b
        return N("计算：%d + %d = （　）" % (a, b), s,
                 [s + 100, s - 100, s + 10, a - b])
    if k == 1:      # 整百减整百
        a = rng.randint(3, 9) * 100
        b = rng.randint(1, a // 100 - 1) * 100
        s = a - b
        return N("计算：%d - %d = （　）" % (a, b), s,
                 [s + 100, s - 100, a + b, s + 10])
    # 整百整十加减整十
    a = rng.randint(2, 9) * 100 + rng.randint(1, 9) * 10
    b = rng.randint(1, 9) * 10
    if rng.randint(0, 1) == 0:
        s = a + b
        return N("计算：%d + %d = （　）" % (a, b), s, [s + 100, s - 10, s + 1, a - b])
    if a - b < 100:
        return None
    s = a - b
    return N("计算：%d - %d = （　）" % (a, b), s, [s + 100, s - 10, a + b, s + 1])


def g_add3(rng):
    a = rng.randint(105, 899)
    b = rng.randint(26, 99)
    s = a + b
    return N("计算：%d + %d = （　）" % (a, b), s,
             [s + 1, s - 1, s + 100, s - 10, a + b // 10 * 10])


def g_sub3(rng):
    a = rng.randint(200, 950)
    b = rng.randint(26, 99)
    s = a - b
    return N("计算：%d - %d = （　）" % (a, b), s,
             [s + 1, s - 1, s + 100, s - 10, a + b])


def g_relation(rng):
    k = rng.randint(0, 1)
    if k == 0:
        a = rng.randint(100, 500)
        s = rng.randint(a + 100, a + 400)
        return N("%d +（　）= %d" % (a, s), s - a,
                 [s + a, s - a + 1, s - a - 1, s])
    a = rng.randint(100, 400)
    b = rng.randint(50, 200)
    return N("（　）- %d = %d" % (a, b), a + b,
             [a - b, a + b + 1, a + b - 1, a])


# ---------------- 下册：时间 ----------------
def g_time(rng):
    k = rng.randint(0, 2)
    if k == 0:
        h = rng.randint(1, 9)
        return N("%d 时 = （　）分。" % h, h * 60, [h * 6, h * 60 + 60, h + 60])
    if k == 1:
        m = rng.randint(1, 9)
        return N("%d 分 = （　）秒。" % m, m * 60, [m * 6, m * 60 + 60, m + 60])
    m = rng.randint(1, 5)
    return N("分针从 12 走到 %d，走了（　）分钟。" % m, m * 5,
             [m, m * 5 + 5, m * 60])


# ---------------- 自动验算：题干反解 ----------------
def expect_g2(stem):
    s = stem
    m = re.match(r"^计算：(\d+) × (\d+) \+ (\d+) = ", s)
    if m:
        return int(m.group(1)) * int(m.group(2)) + int(m.group(3))
    m = re.match(r"^计算：(\d+) × (\d+) - (\d+) = ", s)
    if m:
        return int(m.group(1)) * int(m.group(2)) - int(m.group(3))
    m = re.match(r"^计算：(\d+) × (\d+) = ", s)
    if m:
        return int(m.group(1)) * int(m.group(2))
    m = re.match(r"^计算：(\d+) ÷ (\d+) = ", s)
    if m:
        return int(m.group(1)) // int(m.group(2))
    m = re.match(r"^(\d+) ÷ (\d+) = (\d+) …… （　）$", s)
    if m:
        return int(m.group(1)) - int(m.group(2)) * int(m.group(3))
    m = re.match(r"^(\d+) ÷ (\d+) = （　）…… (\d+)$", s)
    if m:
        return (int(m.group(1)) - int(m.group(3))) // int(m.group(2))
    m = re.match(r"^有 (\d+) 个苹果，每 (\d+) 个装一袋，装了（　）袋。$", s)
    if m:
        return int(m.group(1)) // int(m.group(2))
    m = re.match(r"^有 (\d+) 个苹果，每 (\d+) 个装一袋，还剩（　）个。$", s)
    if m:
        return int(m.group(1)) % int(m.group(2))
    m = re.match(r"^有 (\d+) 个皮球，每 (\d+) 个装一箱，可以装（　）箱。$", s)
    if m:
        return int(m.group(1)) // int(m.group(2))
    m = re.match(r"^把 (\d+) 块蛋糕平均分给 (\d+) 个小朋友，每人分（　）块。$", s)
    if m:
        return int(m.group(1)) // int(m.group(2))
    m = re.match(r"^一支笔 (\d+) 元，买 (\d+) 支要（　）元。$", s)
    if m:
        return int(m.group(1)) * int(m.group(2))
    m = re.match(r"^一根绳子长 1 米，用去 (\d+) 厘米，还剩（　）厘米。$", s)
    if m:
        return 100 - int(m.group(1))
    m = re.match(r"^一根木条长 (\d+) 厘米，另一根长 (\d+) 厘米，两根一共长（　）厘米。$", s)
    if m:
        return int(m.group(1)) + int(m.group(2))
    m = re.match(r"^车上原来有 (\d+) 人，下去了 (\d+) 人，又上来了 (\d+) 人，现在车上有（　）人。$", s)
    if m:
        return int(m.group(1)) - int(m.group(2)) + int(m.group(3))
    m = re.match(r"^(\d+) 的 (\d+) 倍是（　）。$", s)
    if m:
        return int(m.group(1)) * int(m.group(2))
    m = re.match(r"^(\d+) 是 (\d+) 的（　）倍。$", s)
    if m:
        return int(m.group(1)) // int(m.group(2))
    m = re.match(r"^(\d+) \+（　）= (\d+)$", s)
    if m:
        return int(m.group(2)) - int(m.group(1))
    m = re.match(r"^（　）- (\d+) = (\d+)$", s)
    if m:
        return int(m.group(1)) + int(m.group(2))
    m = re.match(r"^(\d+) 时 = （　）分。$", s)
    if m:
        return int(m.group(1)) * 60
    m = re.match(r"^(\d+) 分 = （　）秒。$", s)
    if m:
        return int(m.group(1)) * 60
    m = re.match(r"^分针从 12 走到 (\d+)，走了（　）分钟。$", s)
    if m:
        return int(m.group(1)) * 5
    try:
        v = expect_g1(s)
    except Exception:
        return None
    if v is not None:
        return v
    return None


def verify(units, expect=expect_g2, name=""):
    """遍历所有程序化题目，按题干反解重算，与答案比对。返回错误数（0 = 全对）。"""
    total = errs = 0
    for unit, lessons in units:
        for lesson, _b, qs in lessons:
            for q in qs:
                stem, opts, answers = q[1], q[2], q[3]
                if len(answers) != 1 or answers[0] != "A":
                    continue  # 手工概念题 / 多选不在验算范围
                v = expect(stem)
                if v is None:
                    continue
                total += 1
                try:
                    got = int(str(opts[0]))
                except ValueError:
                    print("解析异常: %s | %s" % (lesson, stem))
                    errs += 1
                    continue
                if got != v:
                    print("错误: %s | %s | 答案=%s 应=%s" % (lesson, stem, opts[0], v))
                    errs += 1
    print("验算完成：%s 共验算 %d 道程序化题，错误 %d" % (name, total, errs))
    return 1 if errs else 0
