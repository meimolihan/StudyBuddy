# -*- coding: utf-8 -*-
"""三年级数学出题器（上下册共用）：程序化出题 + 题干反解自动验算。"""
import random

from _g1math import N  # N(stem, ans, wrongs)
import re


# ---------------- 上册 ----------------

def g_mix_ops(rng):
    """100 以内混合运算：同级连加减 / 两级（乘加乘减）/ 带小括号。"""
    k = rng.randint(0, 2)
    if k == 0:  # 同级连加连减
        a = rng.randint(10, 50)
        b = rng.randint(5, 40)
        c = rng.randint(5, 30)
        if rng.random() < 0.5:
            s = a + b + c
            if s > 100:
                return None
            return N("计算：%d + %d + %d = （　）" % (a, b, c), s, [s + 1, s - 1, s + 10, s - b])
        m = a - b - c
        if m < 0:
            return None
        return N("计算：%d - %d - %d = （　）" % (a, b, c), m, [m + 1, m - 1, a - b, m + 10])
    if k == 1:  # 两级：乘加 / 乘减
        a = rng.randint(2, 9)
        b = rng.randint(2, 9)
        c = rng.randint(5, 40)
        if rng.random() < 0.5:
            s = a * b + c
            return N("计算：%d × %d + %d = （　）" % (a, b, c), s, [a * b, s + 1, s - 1, a * b + c + 10])
        s = a * b - c
        if s < 0:
            return None
        return N("计算：%d × %d - %d = （　）" % (a, b, c), s, [a * b, s + 1, s - 1, a * b + c])
    # 带小括号
    a = rng.randint(3, 9)
    b = rng.randint(2, 9)
    c = rng.randint(2, 9)
    s = a * (b + c)
    return N("计算：%d × (%d + %d) = （　）" % (a, b, c), s,
             [a * b + c, s + a, s - a, a * b * c if a * b * c != s else s + 5])


def g_len(rng):
    """长度单位换算：毫米、分米、米、千米。"""
    k = rng.randint(0, 4)
    n = rng.randint(2, 90)
    if k == 0:
        cm = rng.randint(2, 20)
        return N("%d 厘米 = （　）毫米。" % cm, cm * 10, [cm, cm * 100, cm + 10])
    if k == 1:
        dm = rng.randint(2, 9)
        return N("%d 分米 = （　）厘米。" % dm, dm * 10, [dm, dm * 100, dm + 10])
    if k == 2:
        m = rng.randint(2, 9)
        return N("%d 米 = （　）分米。" % m, m * 10, [m, m * 100, m + 10])
    if k == 3:
        km = rng.randint(2, 9)
        return N("%d 千米 = （　）米。" % km, km * 1000, [km, km * 100, km + 1000])
    m = rng.randint(10, 90)
    return N("%d 分米 = （　）米。（填整数）" % (m * 10), m, [m * 10, m + 1, m - 1])


def g_ton(rng):
    """吨与千克。"""
    t = rng.randint(2, 9)
    if rng.random() < 0.6:
        return N("%d 吨 = （　）千克。" % t, t * 1000, [t, t * 100, t + 1000])
    kg = rng.choice([1000, 2000, 3000, 4000, 5000])
    return N("%d 千克 = （　）吨。" % kg, kg // 1000, [kg, kg // 100, kg // 1000 + 1])


def g_mul(rng):
    """多位数乘一位数。"""
    k = rng.randint(0, 2)
    b = rng.randint(2, 9)
    if k == 0:
        a = rng.randint(11, 99)
    elif k == 1:
        a = rng.randint(100, 999)
        if a % 10 == 0:
            a += 1
    else:
        a = rng.choice([110, 120, 230, 340, 420, 250, 370, 480, 260, 510])
    s = a * b
    return N("计算：%d × %d = （　）" % (a, b), s,
             [s + b, s - b, s + 10, s - 10] if s % 10 else [s + b, s - b, s + 100, a * (b + 1)])


def g_mul_est(rng):
    """乘法估算：接近整十整百的数 × 一位数，估到整十整百。"""
    a = rng.choice([29, 31, 48, 52, 68, 71, 79, 82, 98, 102, 199, 202, 298, 301])
    b = rng.randint(3, 9)
    base = round(a / 10) * 10 if a < 150 else round(a / 100) * 100
    s = base * b
    return N("估算：%d × %d ≈ （　）" % (a, b), s, [s + b, s - b, s + 100, a * b])


def g_frac_cmp(rng):
    """同分母分数比较大小。"""
    d = rng.choice([4, 6, 8, 9, 10])
    a = rng.randint(1, d - 2)
    b = rng.randint(a + 1, d - 1)
    return N("比较大小：%d/%d ○ %d/%d" % (a, d, b, d), "＜", ["＞", "＝", "无法比较"])


def g_frac_add(rng):
    """同分母分数加减（结果不超过 1）。"""
    d = rng.choice([6, 8, 9, 10, 12])
    a = rng.randint(1, d - 3)
    b = rng.randint(1, d - a - 1)
    k = rng.randint(0, 1)
    if k == 0:
        s = a + b
        return N("计算：%d/%d + %d/%d = （　）" % (a, d, b, d), "%d/%d" % (s, d),
                 ["%d/%d" % (s + 1, d), "%d/%d" % (a * b, d), "%d/%d" % (s, d + d)])
    if a <= b:
        a, b = b, a
    s = a - b
    return N("计算：%d/%d - %d/%d = （　）" % (a, d, b, d), "%d/%d" % (s, d),
             ["%d/%d" % (s + 1, d), "%d/%d" % (a + b, d), "%d/%d" % (s, d + d)])


def g_match(rng):
    """搭配问题：m 件 A 配 n 件 B，共 m×n 种。物品名随机，扩大题干空间。"""
    pairs = [("件上衣", "条裤子", "穿法"), ("种饮料", "种点心", "搭配"),
             ("顶帽子", "条围巾", "搭配"), ("条裙子", "件上衣", "穿法"),
             ("条路线", "条路线", "走法"), ("种门票", "种交通方式", "方案"),
             ("个笔袋", "支钢笔", "组合"), ("种包子", "种粥", "搭配")]
    pa, pb, act = rng.choice(pairs)
    m = rng.randint(2, 4)
    n = rng.randint(2, 4)
    return N("有 %d %s和 %d %s，各选一个搭配，共有（　）种%s。" % (m, pa, n, pb, act), m * n,
             [m + n, m * n + 1, m * n - 1])


# ---------------- 下册 ----------------

def g_div(rng):
    """口算除法：整十、整百数除以一位数。"""
    b = rng.randint(2, 9)
    k = rng.randint(0, 1)
    if k == 0:
        a = b * rng.randint(2, 9) * 10
    else:
        a = b * rng.randint(2, 9) * 100
    s = a // b
    return N("计算：%d ÷ %d = （　）" % (a, b), s, [s * 10 if s * 10 != s else s + 1, s // 10 if s // 10 != s else s - 1, s + 1, s - 1])


def g_div3(rng):
    """笔算除法：三位数除以一位数（商两、三位数，含余数）。"""
    b = rng.randint(2, 9)
    if rng.random() < 0.5:
        q = rng.randint(20, 99)
        a = q * b
        return N("计算：%d ÷ %d = （　）" % (a, b), q, [q + 1, q - 1, q + 10, a // 10])
    q = rng.randint(30, 99)
    r = rng.randint(1, b - 1)
    a = q * b + r
    return N("计算：%d ÷ %d = （　）……（　）" % (a, b), "%d 余 %d" % (q, r),
             ["%d 余 %d" % (q, r + 1), "%d 余 %d" % (q + 1, r), "%d 余 0" % q, "%d 余 %d" % (q - 1, r)])


def g_perim(rng):
    """长方形、正方形的周长。"""
    if rng.random() < 0.5:
        a = rng.randint(4, 30)
        b = rng.randint(2, a - 1)
        s = (a + b) * 2
        return N("一个长方形长 %d 厘米，宽 %d 厘米，周长是（　）厘米。" % (a, b), s,
                 [a + b, a * b, s + 2, s - 2])
    a = rng.randint(3, 25)
    s = a * 4
    return N("一个正方形边长 %d 厘米，周长是（　）厘米。" % a, s,
             [a * 2, a * a, s + 4, s - 4])


def g_area(rng):
    """长方形、正方形的面积。"""
    if rng.random() < 0.5:
        a = rng.randint(3, 20)
        b = rng.randint(2, a)
        s = a * b
        return N("一个长方形长 %d 厘米，宽 %d 厘米，面积是（　）平方厘米。" % (a, b), s,
                 [(a + b) * 2, a + b, s + a, s - b])
    a = rng.randint(2, 15)
    s = a * a
    return N("一个正方形边长 %d 厘米，面积是（　）平方厘米。" % a, s,
             [a * 4, a + a, s + a, s - a])


def g_squnit(rng):
    """面积单位换算：1 平方分米 = 100 平方厘米，1 平方米 = 100 平方分米。"""
    k = rng.randint(0, 1)
    n = rng.randint(2, 9)
    if k == 0:
        return N("面积换算：%d 平方分米 = （　）平方厘米。" % n, n * 100, [n * 10, n, n + 100])
    return N("面积换算：%d 平方米 = （　）平方分米。" % n, n * 100, [n * 10, n, n + 100])


def g_stat(rng):
    """数据统计：各部分之和。"""
    n = rng.randint(3, 4)
    vals = [rng.randint(5, 30) for _ in range(n)]
    names = ["晴天", "阴天", "雨天", "雪天"][:n]
    parts = "、".join("%s %d 天" % (nm, v) for nm, v in zip(names, vals))
    s = sum(vals)
    return N("某月天气统计：%s。这个月共（　）天。" % parts, s,
             [s + 1, s - 1, max(vals), min(vals)])


def g_days(rng):
    """年、月、日：某月天数 / 平年全年天数。"""
    k = rng.randint(0, 2)
    if k == 0:
        m, d = rng.choice([(1, 31), (3, 31), (4, 30), (5, 31), (6, 30), (9, 30), (11, 30)])
        return N("%d 月有（　）天。" % m, d, [28, 29, 31 if d == 30 else 30])
    if k == 1:
        y = rng.randint(2000, 2030)
        if y % 4 == 0 and y % 100 != 0:
            d, w = 366, "闰年"
        else:
            d, w = 365, "平年"
        return N("%d 年是（　）。" % y, w, ["平年" if w == "闰年" else "闰年", "大月", "小月"])
    return N("平年 2 月有（　）天，闰年 2 月有（　）天。", "28，29",
             ["29，28", "28，30", "30，31"])


def g_time(rng):
    """经过时间：几时几分到几时几分。"""
    h1 = rng.randint(7, 17)
    m1 = rng.choice([0, 15, 30, 45])
    dur = rng.choice([30, 40, 50, 90, 120])
    total = h1 * 60 + m1 + dur
    if total >= 1440:
        return None
    h2, m2 = divmod(total, 60)
    return N("从 %d 时 %d 分到 %d 时 %d 分，经过了（　）分钟。" % (h1, m1, h2, m2), dur,
             [dur + 10, dur - 10, dur + 60, max(dur - 30, 5)])


def g_dec_cmp(rng):
    """一位小数比较大小。"""
    a = rng.randint(1, 9)
    b = rng.randint(1, 9)
    c = rng.randint(0, 9)
    d = rng.randint(0, 9)
    while (a, c) == (b, d):
        d = rng.randint(0, 9)
    x, y = "%d.%d" % (a, c), "%d.%d" % (b, d)
    ans = "＞" if (a, c) > (b, d) else "＜"
    return N("比较大小：%s ○ %s" % (x, y), ans, ["＜" if ans == "＞" else "＞", "＝", "无法比较"])


def g_dec_add(rng):
    """简单的一位小数加减法。"""
    a = rng.randint(1, 8)
    b = rng.randint(1, 9)
    c = rng.randint(0, 9)
    d = rng.randint(0, 9)
    if rng.random() < 0.5:
        x, y = a + b / 10.0, c + d / 10.0
        s = x + y
        ans = "%.1f" % s
        return N("计算：%.1f + %.1f = （　）" % (x, y), ans, ["%.1f" % (s + 1), "%.1f" % (s + 0.1), "%.1f" % (s - 0.1)])
    if (a + b / 10.0) < (c + d / 10.0):
        a, b, c, d = c, d, a, b
    x, y = a + b / 10.0, c + d / 10.0
    s = x - y
    if s <= 0:
        return None
    ans = "%.1f" % s
    return N("计算：%.1f - %.1f = （　）" % (x, y), ans, ["%.1f" % (s + 1), "%.1f" % (s + 0.1), "%.1f" % (s - 0.1)])


def g_relation(rng):
    """数量关系：总价 = 单价 × 数量 / 倍数关系。"""
    if rng.random() < 0.5:
        p = rng.randint(2, 9)
        n = rng.randint(3, 9)
        s = p * n
        return N("一支笔 %d 元，买 %d 支要（　）元。" % (p, n), s, [p + n, s + p, s - 1])
    a = rng.randint(3, 9)
    k = rng.randint(2, 5)
    s = a * k
    return N("小明有 %d 本书，小红的本数是小明的 %d 倍，小红有（　）本。" % (a, k), s,
             [a + k, s + a, s - 1])


# ---------------- 自动验算：题干反解重算 ----------------

def expect_g3(s):
    import _g1math
    # 带余数除法要先于 expect_g1 的整除匹配
    m = re.match(r"^计算：(\d+) ÷ (\d+) = （　）……（　）$", s)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        return "%d 余 %d" % (a // b, a % b)
    v = _g1math.expect_g1(s)
    if v is not None:
        return v
    m = re.match(r"^计算：(\d+) \+ (\d+) \+ (\d+) = ", s)
    if m:
        return int(m.group(1)) + int(m.group(2)) + int(m.group(3))
    m = re.match(r"^计算：(\d+) - (\d+) - (\d+) = ", s)
    if m:
        return int(m.group(1)) - int(m.group(2)) - int(m.group(3))
    m = re.match(r"^计算：(\d+) × (\d+) \+ (\d+) = ", s)
    if m:
        return int(m.group(1)) * int(m.group(2)) + int(m.group(3))
    m = re.match(r"^计算：(\d+) × (\d+) - (\d+) = ", s)
    if m:
        return int(m.group(1)) * int(m.group(2)) - int(m.group(3))
    m = re.match(r"^计算：(\d+) × \((\d+) \+ (\d+)\) = ", s)
    if m:
        return int(m.group(1)) * (int(m.group(2)) + int(m.group(3)))
    m = re.match(r"^计算：(\d+) × (\d+) = ", s)
    if m:
        return int(m.group(1)) * int(m.group(2))
    m = re.match(r"^计算：(\d+) ÷ (\d+) = ", s)
    if m:
        return int(m.group(1)) // int(m.group(2))
    m = re.match(r"^估算：(\d+) × (\d+) ≈ ", s)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        base = round(a / 10) * 10 if a < 150 else round(a / 100) * 100
        return base * b
    # 长度/质量/面积换算
    m = re.match(r"^(\d+) 厘米 = （　）毫米。", s)
    if m:
        return int(m.group(1)) * 10
    m = re.match(r"^(\d+) 分米 = （　）厘米。", s)
    if m:
        return int(m.group(1)) * 10
    m = re.match(r"^(\d+) 米 = （　）分米。", s)
    if m:
        return int(m.group(1)) * 10
    m = re.match(r"^(\d+) 千米 = （　）米。", s)
    if m:
        return int(m.group(1)) * 1000
    m = re.match(r"^(\d+) 分米 = （　）米。（填整数）", s)
    if m:
        return int(m.group(1)) // 10
    m = re.match(r"^(\d+) 吨 = （　）千克。", s)
    if m:
        return int(m.group(1)) * 1000
    m = re.match(r"^(\d+) 千克 = （　）吨。", s)
    if m:
        return int(m.group(1)) // 1000
    m = re.match(r"^面积换算：(\d+) 平方分米 = （　）平方厘米。", s)
    if m:
        return int(m.group(1)) * 100
    m = re.match(r"^面积换算：(\d+) 平方米 = （　）平方分米。", s)
    if m:
        return int(m.group(1)) * 100
    # 周长面积
    m = re.match(r"^一个长方形长 (\d+) 厘米，宽 (\d+) 厘米，周长是", s)
    if m:
        return (int(m.group(1)) + int(m.group(2))) * 2
    m = re.match(r"^一个长方形长 (\d+) 厘米，宽 (\d+) 厘米，面积是", s)
    if m:
        return int(m.group(1)) * int(m.group(2))
    m = re.match(r"^一个正方形边长 (\d+) 厘米，周长是", s)
    if m:
        return int(m.group(1)) * 4
    m = re.match(r"^一个正方形边长 (\d+) 厘米，面积是", s)
    if m:
        a = int(m.group(1))
        return a * a
    # 搭配 / 数量关系 / 统计
    m = re.match(r"^有 (\d+) \S+和 (\d+) \S+，各选一个搭配", s)
    if m:
        return int(m.group(1)) * int(m.group(2))
    m = re.match(r"^一支笔 (\d+) 元，买 (\d+) 支要", s)
    if m:
        return int(m.group(1)) * int(m.group(2))
    m = re.match(r"^小明有 (\d+) 本书，小红的本数是小明的 (\d+) 倍", s)
    if m:
        return int(m.group(1)) * int(m.group(2))
    m = re.match(r"^某月天气统计：(.+)。这个月共（　）天。", s)
    if m:
        return sum(int(x) for x in re.findall(r"(\d+) 天", m.group(1)))
    # 经过时间
    m = re.match(r"^从 (\d+) 时 (\d+) 分到 (\d+) 时 (\d+) 分，经过了（　）分钟。", s)
    if m:
        h1, m1, h2, m2 = map(int, m.groups())
        return h2 * 60 + m2 - (h1 * 60 + m1)
    # 分数比较/计算
    m = re.match(r"^比较大小：a/(\d+) ○ b/\d+，括号里填＞或＜：(\d+)/(\d+) ○ (\d+)/(\d+)$", s)
    if m:
        d, a, d2, b, d3 = map(int, m.groups())
        return "＜" if a < b else "＞"
    m = re.match(r"^比较大小：(\d+)/(\d+) ○ (\d+)/(\d+)$", s)
    if m:
        a, d1, b, d2 = map(int, m.groups())
        if d1 == d2:
            return "＜" if a < b else "＞"
        return "＜" if a * d2 < b * d1 else "＞"
    m = re.match(r"^计算：(\d+)/(\d+) \+ (\d+)/(\d+) = （　）$", s)
    if m:
        a, d1, b, d2 = map(int, m.groups())
        return "%d/%d" % (a + b, d1)
    m = re.match(r"^计算：(\d+)/(\d+) - (\d+)/(\d+) = （　）$", s)
    if m:
        a, d1, b, d2 = map(int, m.groups())
        return "%d/%d" % (a - b, d1)
    # 一位小数
    m = re.match(r"^计算：(\d+)\.(\d+) \+ (\d+)\.(\d+) = （　）$", s)
    if m:
        a, b, c, d = map(int, m.groups())
        return "%.1f" % (a + b / 10.0 + c + d / 10.0)
    m = re.match(r"^计算：(\d+)\.(\d+) - (\d+)\.(\d+) = （　）$", s)
    if m:
        a, b, c, d = map(int, m.groups())
        return "%.1f" % (a + b / 10.0 - (c + d / 10.0))
    m = re.match(r"^比较大小：(\d+)\.(\d+) ○ (\d+)\.(\d+)$", s)
    if m:
        a, b, c, d = map(int, m.groups())
        return "＞" if (a, b) > (c, d) else "＜"
    return None


def verify(units):
    """按题干反解重算，与标注答案比对（仅程序化生成的数字题）。"""
    total = 0
    bad = 0
    for uname, lessons in units:
        for lname, _bc, qs in lessons:
            for q in qs:
                stem = q[1]
                ans = str(q[2][0])
                v = expect_g3(stem)
                if v is None:
                    continue
                total += 1
                if str(v) != ans:
                    bad += 1
                    if bad <= 10:
                        print("答案错误: %s | %s | 期望 %s 标注 %s" % (lname, stem[:40], v, ans))
    print("验算 %d/%d 全对" % (total - bad, total) if bad == 0 else "验算 %d/%d，错误 %d" % (total - bad, total, bad))
    return 0 if bad == 0 else 1
