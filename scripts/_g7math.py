# -*- coding: utf-8 -*-
"""七年级数学出题器（人教版 2024/2025 新版，上、下册共用）：程序化出题 + 题干反解自动验算。

约定（照 _g6math.py 的套路）：
  * 生成器 g_xxx(rng, mode) 返回 N(stem, ans, 干扰项) 打包好的题目；
    凑不出合适的数就返回 None，gen() 会自动重试；
  * expect_g7(stem) 按题干正则反解出数字并重算，手写概念题返回 None（跳过）；
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
    else:
        val = D(v)
    return fmt(val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def fs(v):
    """有理数 → 整数串或最简分数串。"""
    v = Fraction(v)
    return str(v.numerator) if v.denominator == 1 else str(v)


def p3(ans, cands):
    """取 3 个与答案不同、彼此不同的干扰项（干扰项应是常见错误）。"""
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
        for d in (1, -1, 2, -2, 3, -3, Fraction(1, 2), -Fraction(1, 2)):
            c = fs(v + d)
            if c not in seen:
                seen.add(c)
                out.append(c)
            if len(out) == 3:
                return out
    except (ValueError, ZeroDivisionError):
        pass
    i = 1
    while len(out) < 3:
        c = "%s(%d)" % (s, i)
        if c not in seen:
            seen.add(c)
            out.append(c)
        i += 1
    return out


def _sf(x):
    """负数加括号：(-7)；非负数直接写。"""
    return "(%d)" % x if x < 0 else str(x)


# ---------------- 算式求值（供反解重算用） ----------------
_SUP = {"²": "^2", "³": "^3", "⁴": "^4", "⁵": "^5"}
_OPC = {"×": "*", "÷": "/"}


def _norm(s):
    for k, v in _SUP.items():
        s = s.replace(k, v)
    for k, v in _OPC.items():
        s = s.replace(k, v)
    s = s.replace(" ", "")
    # 补上省略的乘号：2b → 2*b，)( → )*(
    s = re.sub(r"(\d)(?=[a-z(])", r"\1*", s)
    s = re.sub(r"\)(?=[\da-z(])", r")*", s)
    return s


def _lex(s):
    toks, i = [], 0
    while i < len(s):
        c = s[i]
        if c.isdigit():
            j = i
            while j < len(s) and s[j].isdigit():
                j += 1
            toks.append(Fraction(int(s[i:j])))
            i = j
        elif c in "+-*/()^":
            toks.append(c)
            i += 1
        elif c.isalpha():
            toks.append(c)
            i += 1
        else:
            raise ValueError("无法识别的字符 %r（算式 %r）" % (c, s))
    return toks


class _Parser(object):
    def __init__(self, toks, env):
        self.t, self.i, self.env = toks, 0, env or {}

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else None

    def take(self):
        v = self.t[self.i]
        self.i += 1
        return v

    def expr(self):
        v = self.term()
        while self.peek() in ("+", "-"):
            op = self.take()
            r = self.term()
            v = v + r if op == "+" else v - r
        return v

    def term(self):
        v = self.factor()
        while self.peek() in ("*", "/"):
            op = self.take()
            r = self.factor()
            if op == "/" and r == 0:
                raise ZeroDivisionError("除以 0")
            v = v * r if op == "*" else v / r
        return v

    def factor(self):
        if self.peek() == "-":
            self.take()
            return -self.power()
        if self.peek() == "+":
            self.take()
        return self.power()

    def power(self):
        base = self.atom()
        if self.peek() == "^":
            self.take()
            return base ** int(self.factor())
        return base

    def atom(self):
        tk = self.take()
        if isinstance(tk, Fraction):
            return tk
        if tk == "(":
            v = self.expr()
            if self.peek() == ")":
                self.take()
            return v
        if isinstance(tk, str) and tk.isalpha():
            if tk not in self.env:
                raise ValueError("未知字母 %s" % tk)
            return Fraction(self.env[tk])
        raise ValueError("无法识别的记号 %r" % (tk,))


def eval_expr(s, env=None):
    """计算只含整数、+ - × ÷、括号与乘方的算式（可用 env 代入字母的值）。"""
    toks = _lex(_norm(s))
    if not toks:
        raise ValueError("空算式")
    p = _Parser(toks, env)
    v = p.expr()
    if p.i != len(toks):
        raise ValueError("算式没读完：%r" % s)
    return v


# ---------------- 一次整式（线性式）的小工具 ----------------
_VAR_ORDER = ["a", "b", "m", "n", "x", "y", ""]


def _join(terms):
    """[(系数, 变量名), ...] → '3a - 2b + 5'（常数项的变量名写 ''）。"""
    ts = [(c, v) for c, v in terms if c]
    if not ts:
        return "0"
    out = ""
    for i, (c, v) in enumerate(ts):
        if v == "":
            body = str(abs(c))
        else:
            body = {1: v, -1: "-" + v}.get(c, "%d%s" % (c, v))
        if i == 0:
            out += body
        else:
            out += (" + " + body) if c > 0 else (" - " + body.lstrip("-"))
    return out


def parse_lin(s):
    """'3a-2b+5' → {'a': 3, 'b': -2, '': 5}"""
    s = s.replace(" ", "")
    if not s:
        return {}
    if s[0] not in "+-":
        s = "+" + s
    d = {}
    for sign, num, var in re.findall(r"([+-])(\d*)([a-z]?)", s):
        if not num and not var:
            continue
        c = int(num) if num else 1
        if sign == "-":
            c = -c
        key = var or ""
        d[key] = d.get(key, 0) + c
        if d[key] == 0:
            del d[key]
    return d


def lin_str(d):
    d = dict((k, v) for k, v in d.items() if v)
    return _join([(d.get(k, 0), k) for k in _VAR_ORDER if d.get(k, 0)])


# ---------------- 单项式 / 多项式 ----------------
def _mono_str(c, parts):
    """parts: [(变量名, 指数)]；c 为系数。"""
    if parts and c == 1:
        head = ""
    elif parts and c == -1:
        head = "-"
    else:
        head = str(c)
    return head + "".join(v + {1: "", 2: "²", 3: "³"}[e] for v, e in parts)


def parse_mono(s):
    """'  -3x²y' → (系数, 次数)。"""
    m = re.fullmatch(r"(-?)(\d*)((?:[a-z][²³]?)*)", s)
    if not m:
        return None
    coef = int(m.group(2)) if m.group(2) else 1
    if m.group(1):
        coef = -coef
    deg = 0
    for _v, e in re.findall(r"([a-z])([²³]?)", m.group(3)):
        deg += {"": 1, "²": 2, "³": 3}[e]
    return coef, deg


def _poly_str(terms, var):
    """terms: [(系数, 指数), ...]，指数 0 表示常数项。"""
    out = ""
    for i, (c, e) in enumerate(terms):
        if c == 0:
            continue
        body = _mono_str(abs(c), [(var, e)] if e else [])
        if i == 0:
            out += ("-" if c < 0 else "") + body
        else:
            out += (" - " if c < 0 else " + ") + body
    return out or "0"


def parse_poly(s):
    """'3x² - 2x + 1' → [(系数, 次数), ...]"""
    s = s.replace(" ", "")
    if not s:
        return []
    if s[0] not in "+-":
        s = "+" + s
    out = []
    for sign, body in re.findall(r"([+-])([^+-]+)", s):
        r = parse_mono(body)
        if r is None:
            return []
        c, d = r
        out.append((c if sign == "+" else -c, d))
    return out


# ---------------- 上册 1：有理数 ----------------
_OPP_WORD = [("向东走", "向西走", "米"), ("收入", "支出", "元"), ("上升", "下降", "米"),
             ("运进", "运出", "吨"), ("高于海平面", "低于海平面", "米"),
             ("零上", "零下", "℃"), ("盈利", "亏损", "元"), ("前进", "后退", "米"),
             ("水位上涨", "水位下降", "厘米")]
_PW2NW = dict((pw, (nw, u)) for pw, nw, u in _OPP_WORD)


def g_rat(rng, mode):
    if mode == "pos":
        k = rng.randint(0, 2)
        pw, nw, u = rng.choice(_OPP_WORD)
        a = rng.choice([2, 3, 5, 6, 8, 10, 12, 15, 20, 25, 30, 40, 50, 80, 100, 120, 200])
        b = rng.choice([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 18, 20, 25, 30, 40, 60])
        if k == 0:
            stem = ("如果%s %d %s记作 +%d %s，那么%s %d %s记作（　）%s。"
                    % (pw, a, u, a, u, nw, b, u, u))
            ans = "-%d" % b
            return N(stem, ans, p3(ans, ["+%d" % b, "%d" % b, "%d" % (a + b), "-%d" % a]))
        if k == 1:
            if a == b:
                return None
            stem = "如果%s %d %s记作 +%d %s，那么 -%d %s表示（　）。" % (pw, a, u, a, u, b, u)
            ans = "%s %d %s" % (nw, b, u)
            return N(stem, ans, p3(ans, ["%s %d %s" % (pw, b, u), "%s %d %s" % (nw, a, u),
                                         "%s %d %s" % (pw, a, u)]))
        base = rng.choice([60, 70, 75, 80, 85, 90, 95, 100])
        hi = rng.randint(1, 15)
        lo = rng.randint(1, 15)
        ans = "-%d" % lo
        stem = ("某次测验班级平均分是 %d 分，规定高于平均分记为正，小明比平均分高 %d 分记作 "
                "+%d 分，小红比平均分低 %d 分记作（　）分。" % (base, hi, hi, lo))
        return N(stem, ans, p3(ans, ["+%d" % lo, "%d" % lo, "%d" % (base - lo)]))
    if mode == "axis":
        k = rng.randint(0, 4)
        if k == 0:
            a = rng.randint(1, 15)
            return N("数轴上表示 -%d 的点到原点的距离是（　）。" % a, a,
                     p3(a, [a + 1, -a, 2 * a]))
        if k == 1:
            a = rng.randint(1, 15)
            ans = "±%d" % a
            return N("数轴上与原点相距 %d 个单位长度的点表示的数是（　）。" % a, ans,
                     p3(ans, [str(a), "-%d" % a, "±%d" % (a + 1)]))
        if k == 2:
            st = rng.randint(-12, -1)
            mv = rng.randint(1, 18)
            return N("数轴上点 A 表示 %d，把点 A 向右移动 %d 个单位长度后表示的数是（　）。"
                     % (st, mv), st + mv, p3(st + mv, [st - mv, mv - st, abs(st) + mv]))
        if k == 3:
            st = rng.randint(-8, 12)
            mv = rng.randint(1, 18)
            return N("数轴上点 A 表示 %d，把点 A 向左移动 %d 个单位长度后表示的数是（　）。"
                     % (st, mv), st - mv, p3(st - mv, [st + mv, mv - st, abs(st - mv)]))
        a = rng.randint(-12, -1)
        b = rng.randint(1, 12)
        return N("数轴上点 A 表示 %d，点 B 表示 %d，则 A、B 两点之间的距离是（　）。" % (a, b),
                 b - a, p3(b - a, [a + b, b + a, abs(a) + b + 1]))
    if mode == "opp":
        k = rng.randint(0, 4)
        a = rng.randint(1, 25)
        if k == 0:
            return N("%d 的相反数是（　）。" % a, -a, p3(-a, [a, -a - 1, a + 1]))
        if k == 1:
            return N("(-%d) 的相反数是（　）。" % a, a, p3(a, [-a, -a - 1, a + 1]))
        if k == 2:
            return N("-(-%d) 化简的结果是（　）。" % a, a, p3(a, [-a, a + 1, -a - 1]))
        if k == 3:
            return N("-(+%d) 化简的结果是（　）。" % a, -a, p3(-a, [a, -a + 1, a + 1]))
        v = rng.choice(["a", "b", "m", "x"])
        return N("若 %s 与 -%d 互为相反数，则 %s = （　）。" % (v, a, v), a,
                 p3(a, [-a, a + 1, -a - 1]))
    if mode == "abs":
        k = rng.randint(0, 4)
        if k == 0:
            a = rng.randint(-30, 30)
            return N("|%d| = （　）。" % a, abs(a), p3(abs(a), [-abs(a), abs(a) + 1,
                                                              abs(a) + 2]))
        if k == 1:
            a = rng.randint(-25, 25)
            b = rng.randint(-25, 25)
            return N("|%d - %d| = （　）。" % (a, b), abs(a - b),
                     p3(abs(a - b), [a + b, abs(a - b) + 1, abs(a) + abs(b)]))
        if k == 2:
            a = rng.randint(1, 25)
            return N("-|%d| = （　）。" % a, -a, p3(-a, [a, -a - 1, a + 1]))
        if k == 3:
            a = rng.randint(1, 25)
            ans = "±%d" % a
            return N("若 |x| = %d，则 x = （　）。" % a, ans,
                     p3(ans, [str(a), "-%d" % a, "±%d" % (a + 1)]))
        a = rng.randint(1, 25)
        ans = "±%d" % a
        return N("绝对值等于 %d 的数是（　）。" % a, ans,
                 p3(ans, [str(a), "-%d" % a, "±%d" % (a + 1)]))
    if mode == "cmp":
        k = rng.randint(0, 3)
        if k == 0:
            a, b = rng.randint(-40, 40), rng.randint(-40, 40)
            if a == b:
                return None
            return N("在 %d 和 %d 中，较大的数是（　）。" % (a, b), max(a, b),
                     p3(max(a, b), [min(a, b), a + b, abs(a) + abs(b)]))
        if k == 1:
            a, b = rng.randint(-40, 40), rng.randint(-40, 40)
            if a == b:
                return None
            return N("在 %d 和 %d 中，较小的数是（　）。" % (a, b), min(a, b),
                     p3(min(a, b), [max(a, b), a - b, abs(a) - abs(b)]))
        if k == 2:
            four = rng.sample(range(-25, 26), 4)
            ans = sorted(four, reverse=True)[1]
            return N("把 %d、%d、%d、%d 按从大到小的顺序排列，排在第 2 位的是（　）。"
                     % tuple(four), ans,
                     p3(ans, [sorted(four, reverse=True)[0], sorted(four, reverse=True)[2],
                              sorted(four)[0]]))
        four = rng.sample(range(-25, 26), 4)
        ans = min(four, key=lambda v: abs(v))
        return N("在 %d、%d、%d、%d 中，绝对值最小的数是（　）。" % tuple(four), ans,
                 p3(ans, [max(four, key=lambda v: abs(v)), sorted(four)[0], sorted(four)[-1]]))
    return None


# ---------------- 上册 2：有理数的运算 ----------------
def g_rop(rng, mode):
    if mode == "add":
        a, b = rng.randint(-40, 40), rng.randint(-40, 40)
        if a == 0 or b == 0:
            return None
        v = a + b
        return N("计算：%s + %s = （　）" % (_sf(a), _sf(b)), v,
                 p3(v, [a - b, abs(a) + abs(b), -(a + b), v + 1]))
    if mode == "sub":
        a, b = rng.randint(-40, 40), rng.randint(-40, 40)
        if a == 0 or b == 0:
            return None
        v = a - b
        return N("计算：%s - %s = （　）" % (_sf(a), _sf(b)), v,
                 p3(v, [a + b, b - a, abs(a) + abs(b), v + 1]))
    if mode == "addsub":
        a = rng.randint(-25, 25)
        b = rng.randint(-25, 25)
        c = rng.randint(-25, 25)
        if 0 in (a, b, c):
            return None
        v = a + b - c
        return N("计算：%s + %s - %s = （　）" % (_sf(a), _sf(b), _sf(c)), v,
                 p3(v, [a - b - c, a + b + c, -(a + b - c), v + 1]))
    if mode == "mul":
        a = rng.randint(-12, 12)
        b = rng.randint(-12, 12)
        if a == 0 or b == 0 or abs(a) == 1 or abs(b) == 1:
            return None
        v = a * b
        return N("计算：%s × %s = （　）" % (_sf(a), _sf(b)), v,
                 p3(v, [-v, abs(a) * abs(b), a + b, v + a]))
    if mode == "div":
        b = rng.choice([-9, -8, -7, -6, -5, -4, -3, -2, 2, 3, 4, 5, 6, 7, 8, 9])
        q = rng.choice([-9, -8, -7, -6, -5, -4, -3, -2, 2, 3, 4, 5, 6, 7, 8, 9])
        a = b * q
        return N("计算：%s ÷ %s = （　）" % (_sf(a), _sf(b)), q,
                 p3(q, [-q, abs(q), q + 1, q - 1]))
    if mode == "mix":
        k = rng.randint(0, 4)
        if k == 0:
            a = rng.randint(-9, 9)
            b = rng.randint(-9, 9)
            c = rng.randint(-30, 30)
            if a == 0 or b == 0:
                return None
            v = a * b + c
            return N("计算：%s × %s + %s = （　）" % (_sf(a), _sf(b), _sf(c)), v,
                     p3(v, [a * b - c, -(a * b) + c, v + 1, a * b]))
        if k == 1:
            a = rng.randint(-9, 9)
            b = rng.randint(-9, 9)
            c = rng.randint(-30, 30)
            if a == 0 or b == 0:
                return None
            v = a * b - c
            return N("计算：%s × %s - %s = （　）" % (_sf(a), _sf(b), _sf(c)), v,
                     p3(v, [a * b + c, -(a * b) - c, v + 1, a * b]))
        if k == 2:
            a = rng.randint(-40, 40)
            b = rng.randint(-9, 9)
            c = rng.randint(-9, 9)
            if b == 0 or c == 0:
                return None
            v = a - b * c
            return N("计算：%s - %s × %s = （　）" % (_sf(a), _sf(b), _sf(c)), v,
                     p3(v, [a + b * c, (a - b) * c, v + 1, a - b - c]))
        if k == 3:
            c = rng.choice([-9, -8, -7, -6, -5, -4, -3, -2, 2, 3, 4, 5, 6, 7, 8, 9])
            q = rng.randint(-9, 9)
            inner = c * q
            a = rng.randint(-30, 30)
            b = inner - a
            if b == 0:
                return None
            v = q
            return N("计算：(%s + %s) ÷ %s = （　）" % (_sf(a), _sf(b), _sf(c)), v,
                     p3(v, [-q, abs(q), q + 1, q - 1]))
        a = rng.randint(-9, 9)
        b = rng.randint(-12, 12)
        c = rng.randint(-12, 12)
        if a == 0:
            return None
        v = a * (b - c)
        return N("计算：%s × (%s - %s) = （　）" % (_sf(a), _sf(b), _sf(c)), v,
                 p3(v, [a * b - c, a * (b + c), v + 1, -v]))
    if mode == "pow":
        k = rng.randint(0, 3)
        if k == 0:
            a = rng.randint(2, 15)
            v = a * a
            return N("计算：(-%d)² = （　）" % a, v, p3(v, [-v, 2 * a, -2 * a, a * a + a]))
        if k == 1:
            a = rng.randint(2, 15)
            v = -(a * a)
            return N("计算：-%d² = （　）" % a, v, p3(v, [a * a, -2 * a, 2 * a, -(a * a) - a]))
        if k == 2:
            a = rng.randint(2, 9)
            e = rng.choice([3, 4])
            v = (-a) ** e
            return N("计算：(-%d)%s = （　）" % (a, "³" if e == 3 else "⁴"), v,
                     p3(v, [-v, a ** e, a * e, -(a ** e)]))
        a = rng.randint(2, 9)
        e = rng.choice([2, 3, 4])
        v = a ** e
        return N("计算：%d%s = （　）" % (a, {2: "²", 3: "³", 4: "⁴"}[e]), v,
                 p3(v, [a * e, -(a ** e), a ** (e + 1), a * e * e]))
    if mode == "sci":
        k = rng.randint(0, 1)
        if k == 0:
            n = rng.randint(3, 9)
            a = rng.choice([1.2, 1.5, 2.4, 3.6, 4.8, 5.2, 6.7, 7.5, 8.1, 9.9])
            v = int(round(a * 10)) * 10 ** (n - 1)
            return N("把 %s×10^%d 写成原数是（　）。" % (a, n), v,
                     p3(v, [v // 10, v * 10, v // 100 or v + 1]))
        n = rng.randint(4, 9)
        m = rng.randint(2, 9)
        v = m * 10 ** n
        return N("把 %d 写成 a×10^n 的形式（1 ≤ a < 10），则 n = （　）。" % v, n,
                 p3(n, [n - 1, n + 1, n + 2]))
    if mode == "approx":
        whole = rng.randint(0, 99)
        frac = rng.randint(1, 999)
        s = "%d.%03d" % (whole, frac)
        name, q = rng.choice([("0.1", "0.1"), ("0.01", "0.01"), ("十分位", "0.1"),
                              ("百分位", "0.01"), ("个位", "1")])
        ans = round_to(s, q)
        cands = []
        for q2 in ("0.001", "0.01", "0.1", "1"):
            c = round_to(s, q2)
            if c != ans and c not in cands:
                cands.append(c)
            if len(cands) == 3:
                break
        return N("把 %s 精确到 %s 得（　）。" % (s, name), ans, p3(ans, cands))
    return None


def round_to(v, q):
    """按 q（'1' / '0.1' / '0.01' / '0.001'）四舍五入。"""
    return fmt(D(v).quantize(D(q), rounding=ROUND_HALF_UP))


# ---------------- 上册 3：代数式 ----------------
def g_alg(rng, mode):
    if mode == "write":
        k = rng.randint(0, 5)
        v = rng.choice(["a", "b", "m", "n", "x", "y"])
        w = rng.choice([c for c in ["b", "m", "n", "y"] if c != v])
        n = rng.randint(2, 9)
        c = rng.randint(1, 20)
        if k == 0:
            ans = "%d%s+%d" % (n, v, c)
            stem = "「比 %s 的 %d 倍大 %d 的数」用代数式表示是（　）。" % (v, n, c)
            return N(stem, ans, p3(ans, ["%d(%s+%d)" % (n, v, c), "%s+%d" % (v, c),
                                         "%d%s-%d" % (n, v, c)]))
        if k == 1:
            ans = "%d%s-%d" % (n, v, c)
            stem = "「比 %s 的 %d 倍小 %d 的数」用代数式表示是（　）。" % (v, n, c)
            return N(stem, ans, p3(ans, ["%d(%s-%d)" % (n, v, c), "%s-%d" % (v, c),
                                         "%d%s+%d" % (n, v, c)]))
        if k == 2:
            ans = "%d(%s+%s)" % (n, v, w)
            stem = "「%s 与 %s 的和的 %d 倍」用代数式表示是（　）。" % (v, w, n)
            return N(stem, ans, p3(ans, ["%d%s+%s" % (n, v, w), "%s+%d%s" % (v, n, w),
                                         "%s+%s+%d" % (v, w, n)]))
        if k == 3:
            ans = "%d(%s-%s)" % (n, v, w)
            stem = "「%s 与 %s 的差的 %d 倍」用代数式表示是（　）。" % (v, w, n)
            return N(stem, ans, p3(ans, ["%d%s-%s" % (n, v, w), "%s-%d%s" % (v, n, w),
                                         "%s-%s+%d" % (v, w, n)]))
        if k == 4:
            ans = "%s²+%d%s" % (v, n, w)
            stem = "「%s 的平方与 %s 的 %d 倍的和」用代数式表示是（　）。" % (v, w, n)
            return N(stem, ans, p3(ans, ["%s²-%d%s" % (v, n, w), "(%s+%s)²" % (v, w),
                                         "%d%s²+%s" % (n, v, w)]))
        ans = "%d(%s+%d)" % (n, v, c)
        stem = "「比 %s 大 %d 的数的 %d 倍」用代数式表示是（　）。" % (v, c, n)
        return N(stem, ans, p3(ans, ["%d%s+%d" % (n, v, c), "%d%s+%d" % (n, v, n * c),
                                     "%s+%d+%d" % (v, c, n)]))
    if mode == "val":
        k = rng.randint(0, 1)
        if k == 0:
            v = rng.choice(["a", "b", "m", "x"])
            val = rng.randint(-9, 9)
            tpl = rng.choice(["2{v}+3", "{v}²-4", "5-2{v}", "{v}²+2{v}", "4-{v}²",
                              "3{v}-7", "{v}²+1"])
            e = tpl.replace("{v}", v)
            ans = fs(eval_expr(e, {v: val}))
            stem = "当 %s = %d 时，代数式 %s 的值是（　）。" % (v, val, e)
            return N(stem, ans, p3(ans, [fs(eval_expr(e, {v: val + 1})),
                                         fs(eval_expr(e, {v: val - 1})),
                                         fs(eval_expr(e, {v: -val})),
                                         fs(eval_expr(e, {v: val}) + 1)]))
        v, w = rng.choice([("a", "b"), ("x", "y"), ("m", "n")])
        vv = rng.randint(-9, 9)
        ww = rng.randint(-9, 9)
        tpl = rng.choice(["2{v}+3{w}", "3{v}-2{w}", "{v}²+2{w}", "5{v}-{w}", "{v}+{w}²"])
        e = tpl.replace("{v}", v).replace("{w}", w)
        ans = fs(eval_expr(e, {v: vv, w: ww}))
        stem = "当 %s = %d，%s = %d 时，代数式 %s 的值是（　）。" % (v, vv, w, ww, e)
        return N(stem, ans, p3(ans, [fs(eval_expr(e, {v: vv + 1, w: ww})),
                                     fs(eval_expr(e, {v: vv, w: ww + 1})),
                                     fs(eval_expr(e, {v: -vv, w: ww})),
                                     fs(eval_expr(e, {v: vv, w: ww}) + 1)]))
    return None


# ---------------- 上册 4：整式的加减 ----------------
def g_poly(rng, mode):
    if mode == "mono":
        nv = rng.randint(1, 2)
        vs = rng.sample(["x", "y", "z"], nv)
        parts = [(v, rng.randint(1, 3)) for v in vs]
        deg = sum(e for _v, e in parts)
        c = rng.choice([-9, -7, -6, -5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 6, 7, 8, 9])
        s = _mono_str(c, parts)
        if rng.randint(0, 1):
            return N("单项式 %s 的系数是（　）。" % s, c,
                     p3(c, [abs(c) if abs(c) != c else -c, -c if -c != c else c + 1, c + 1]))
        return N("单项式 %s 的次数是（　）。" % s, deg,
                 p3(deg, [deg + 1, deg - 1 if deg > 1 else deg + 2, len(parts)]))
    if mode == "poly":
        var = rng.choice(["x", "y", "a"])
        hi = rng.randint(2, 3)
        exps = list(range(hi, 0, -1))
        if rng.randint(0, 1):
            exps = [e for e in exps if e != 1]
        coefs = [rng.choice([-9, -6, -5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 6, 7])
                 for _ in exps]
        const = rng.choice([-9, -7, -5, -3, -2, -1, 1, 2, 3, 4, 6, 8])
        terms = list(zip(coefs, exps)) + [(const, 0)]
        s = _poly_str(terms, var)
        k = rng.randint(0, 2)
        if k == 0:
            deg = max(e for _c, e in terms)
            return N("多项式 %s 的次数是（　）。" % s, deg,
                     p3(deg, [deg + 1, deg - 1 if deg > 1 else deg + 2, len(terms)]))
        if k == 1:
            return N("多项式 %s 的常数项是（　）。" % s, const,
                     p3(const, [-const, const + 1, 0]))
        return N("多项式 %s 一共有（　）项。" % s, len(terms),
                 p3(len(terms), [len(terms) + 1, len(terms) - 1, len(terms) + 2]))
    if mode == "comb":
        var = rng.choice(["a", "b", "m", "n", "x", "y"])
        cnt = rng.randint(2, 3)
        coefs = [rng.choice([-9, -8, -7, -6, -5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 6, 7, 8, 9])
                 for _ in range(cnt)]
        tot = sum(coefs)
        if tot == 0:
            return None
        expr = _join([(c, var) for c in coefs])
        ans = lin_str({var: tot})
        return N("合并同类项：%s = （　）" % expr, ans,
                 p3(ans, [lin_str({var: tot + 1}), lin_str({var: tot - 1}),
                          lin_str({var: -tot}), "%s%s" % (var, tot)]))
    if mode == "brk":
        k = rng.choice([-1, 2, 3, -2, -3, 4, -4])
        nv = rng.randint(1, 2)
        vs = rng.sample(["a", "b", "x", "y"], nv)
        d = dict((v, rng.choice([-6, -5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 6])) for v in vs)
        if rng.randint(0, 1):
            d[""] = rng.choice([-9, -7, -5, -3, 3, 5, 7, 9])
        inner = lin_str(d)
        out = "-" if k == -1 else str(k)
        ans = lin_str(dict((key, v * k) for key, v in d.items()))
        first = list(d)[0]
        wrongs = [inner,
                  lin_str({first: d[first] * k}),
                  lin_str(dict((key, v * k + 1) for key, v in d.items())),
                  lin_str(dict((key, v * k - 1) for key, v in d.items())),
                  lin_str(dict((key, -v * k) for key, v in d.items()))]
        return N("去括号：%s(%s) = （　）" % (out, inner), ans, p3(ans, wrongs))
    if mode == "addsub":
        k = rng.randint(0, 2)
        nv = rng.randint(1, 2)
        vs = rng.sample(["a", "b", "m", "x", "y"], nv)
        if k < 2:
            d1 = dict((v, rng.randint(-9, 9) or 2) for v in vs)
            d2 = dict((v, rng.randint(-9, 9) or -3) for v in vs)
            sgn = 1 if k == 0 else -1
            sign = "+" if k == 0 else "-"
            res = dict((v, d1[v] + sgn * d2[v]) for v in vs)
            if not any(res.values()):
                return None
            ans = lin_str(res)
            e1, e2 = lin_str(d1), lin_str(d2)
            wrongs = [lin_str(d1), lin_str(d2),
                      lin_str(dict((v, d1[v] - d2[v]) for v in vs)),
                      lin_str(dict((v, -d1[v] - d2[v]) for v in vs)),
                      lin_str(dict((v, d1[v] + sgn * d2[v] + 1) for v in vs))]
            return N("化简：(%s) %s (%s) = （　）" % (e1, sign, e2), ans, p3(ans, wrongs))
        va, vb = rng.sample(["a", "b", "m", "n", "x", "y"], 2)
        p = rng.randint(-9, 9) or 2
        q = rng.randint(-9, 9) or 3
        r = rng.randint(-9, 9) or 4
        expr = _join([(p, va), (q, va), (r, vb)])
        res = {va: p + q, vb: r}
        if not any(res.values()):
            return None
        ans = lin_str(res)
        wrongs = [lin_str({va: p - q, vb: r}), lin_str({va: p + q, vb: -r}),
                  lin_str({va: p + q + 1, vb: r}), lin_str({vb: r})]
        return N("化简：%s = （　）" % expr, ans, p3(ans, wrongs))
    return None


# ---------------- 上册 5：一元一次方程 ----------------
def g_eq(rng, mode):
    if mode == "solve":
        if rng.randint(0, 1):
            a1 = rng.randint(2, 9)
            a2 = rng.randint(1, 9)
            if a1 == a2:
                return None
            x0 = rng.randint(-9, 9)
            b1 = rng.randint(1, 25)
            b2 = (a1 - a2) * x0 + b1
            if b2 <= 0:
                return None
            v = fs(Fraction(b2 - b1, a1 - a2))
            stem = "解方程：%dx + %d = %dx + %d，则 x = （　）。" % (a1, b1, a2, b2)
            return N(stem, v, p3(v, [fs(Fraction(b2 - b1, a1 - a2) + 1),
                                     fs(Fraction(b2 - b1, a1 - a2) - 1),
                                     fs(Fraction(b1 - b2, a1 - a2)),
                                     fs(Fraction(b1 + b2, a1 + a2))]))
        a = rng.choice([-9, -8, -7, -6, -5, -4, -3, -2, 2, 3, 4, 5, 6, 7, 8, 9])
        x0 = rng.randint(-12, 12)
        b = rng.randint(1, 30)
        op = rng.choice(["+", "-"])
        c = a * x0 + b if op == "+" else a * x0 - b
        v = fs(Fraction(c - b, a) if op == "+" else Fraction(c + b, a))
        stem = "解方程：%dx %s %d = %d，则 x = （　）。" % (a, op, b, c)
        return N(stem, v, p3(v, [fs(Fraction(c - b, a) + 1 if op == "+"
                                    else Fraction(c + b, a) + 1),
                                 fs(Fraction(c, a)), fs(Fraction(b - c, a)),
                                 fs(-Fraction(c - b, a) if op == "+"
                                    else -Fraction(c + b, a))]))
    if mode == "word":
        k = rng.randint(0, 5)
        if k == 0:
            a = rng.randint(2, 9)
            x0 = rng.randint(1, 25)
            b = rng.randint(1, 30)
            c = a * x0 + b
            v = fs(Fraction(c - b, a))
            stem = "一个数的 %d 倍加上 %d 等于 %d，这个数是（　）。" % (a, b, c)
            return N(stem, v, p3(v, [fs(Fraction(c + b, a)), fs(Fraction(c, a)),
                                     fs(Fraction(c - b, a) + 1), fs(Fraction(b - c, a))]))
        if k == 1:
            a = rng.randint(2, 9)
            x0 = rng.randint(1, 25)
            b = rng.randint(1, 30)
            c = a * x0 - b
            v = fs(Fraction(c + b, a))
            stem = "一个数的 %d 倍减去 %d 等于 %d，这个数是（　）。" % (a, b, c)
            return N(stem, v, p3(v, [fs(Fraction(c - b, a)), fs(Fraction(c, a)),
                                     fs(Fraction(c + b, a) + 1), fs(Fraction(b + c, a))]))
        if k == 2:
            a = rng.randint(2, 9)
            x0 = rng.randint(1, 25)
            d = (a - 1) * x0
            v = fs(Fraction(d, a - 1))
            stem = "一个数的 %d 倍比它本身大 %d，这个数是（　）。" % (a, d)
            return N(stem, v, p3(v, [fs(Fraction(d, a)), fs(Fraction(d, a - 1) + 1),
                                     fs(Fraction(d + 1, a - 1)), str(d)]))
        if k == 3:
            a = rng.randint(2, 5)
            b = rng.randint(1, 15)
            x0 = rng.randint(1, 20)
            s = (a + 1) * x0 - b
            v = fs(Fraction(s + b, a + 1))
            stem = ("甲数是 x，乙数比甲数的 %d 倍少 %d，两数之和是 %d，则 x = （　）。"
                    % (a, b, s))
            return N(stem, v, p3(v, [fs(Fraction(s - b, a + 1)), fs(Fraction(s, a + 1)),
                                     fs(Fraction(s + b, a + 1) + 1),
                                     fs(Fraction(s + b, a))]))
        if k == 4:
            kk = rng.randint(2, 5)
            x0 = rng.randint(2, 20)
            p = 2 * (kk + 1) * x0
            v = fs(Fraction(p, 2 * (kk + 1)))
            stem = "一个长方形的长是宽的 %d 倍，周长是 %d cm，宽是（　）cm。" % (kk, p)
            return N(stem, v, p3(v, [fs(Fraction(p, 2 * kk)), fs(Fraction(p, 2)),
                                     fs(Fraction(p, 2 * (kk + 1)) + 1),
                                     fs(Fraction(p, kk + 1))]))
        disc = rng.choice([5, 6, 7, 8, 9])
        x0 = 10 * rng.randint(2, 30)
        if x0 * disc % 10:
            return None
        price = x0 * disc // 10
        v = fs(Fraction(price * 10, disc))
        stem = "一件商品按标价打 %d 折出售，售价是 %d 元，标价是（　）元。" % (disc, price)
        return N(stem, v, p3(v, [fs(Fraction(price * disc, 10)),
                                 fs(Fraction(price * 10, disc) + 1),
                                 fs(Fraction(price, disc)), str(price)]))
    return None


# ---------------- 上册 6：几何图形初步 ----------------
def g_geo(rng, mode):
    if mode == "seg":
        k = rng.randint(0, 4)
        if k == 0:
            L = 2 * rng.randint(2, 30)
            return N("线段 AB 长 %d cm，点 C 是 AB 的中点，则 AC = （　）cm。" % L, L // 2,
                     p3(L // 2, [L, L // 4 or 1, L + 2]))
        if k == 1:
            L = rng.randint(10, 60)
            a = rng.randint(1, L - 1)
            return N("已知线段 AB = %d cm，点 C 在线段 AB 上，且 AC = %d cm，则 BC = （　）cm。"
                     % (L, a), L - a, p3(L - a, [L + a, L, abs(L - 2 * a) or 1]))
        if k == 2:
            a = rng.randint(2, 30)
            return N("点 C 是线段 AB 的中点，AC = %d cm，则 AB = （　）cm。" % a, 2 * a,
                     p3(2 * a, [a, a // 2 or 1, 3 * a]))
        if k == 3:
            L = rng.randint(5, 40)
            b = rng.randint(1, 30)
            return N("已知线段 AB = %d cm，延长 AB 到点 C，使 BC = %d cm，则 AC = （　）cm。"
                     % (L, b), L + b, p3(L + b, [abs(L - b) or 1, L, b]))
        L = 3 * rng.randint(2, 20)
        return N("点 C、D 是线段 AB 的三等分点，AB = %d cm，则 AC = （　）cm。" % L, L // 3,
                 p3(L // 3, [L // 2, 2 * L // 3, L]))
    if mode == "angle":
        k = rng.randint(0, 4)
        if k == 0:
            deg = rng.choice(["0.5", "1.5", "2.5", "3.5", "0.2", "1.2", "2.4"])
            v = int(D(deg) * 60)
            return N("%s° = （　）′" % deg, v,
                     p3(v, [v + 60, max(v - 60, 1), int(D(deg) * 100)]))
        if k == 1:
            mi = rng.choice([30, 90, 150, 12, 72, 210, 45, 15, 18])
            v = fmt(D(mi) / 60)
            return N("%d′ = （　）°" % mi, v,
                     p3(v, [fmt(D(mi) * 60), fmt(D(mi) / 100), fmt(D(mi) / 6)]))
        if k == 2:
            h = rng.randint(1, 11)
            v = min(h * 30, 360 - h * 30)
            return N("钟面上 %d 点整，时针与分针的夹角是（　）°。" % h, v,
                     p3(v, [h * 6, (v + 30) % 360 or 30, abs(v - 30) or 60]))
        if k == 3:
            n = rng.choice([4, 5, 6, 8, 9, 12])
            return N("把一个周角平均分成 %d 份，每份是（　）°。" % n, 360 // n,
                     p3(360 // n, [360 // (n + 1) or 30, 360 // max(n - 1, 1), 360 - n]))
        n = rng.choice([2, 3, 4, 6, 9])
        return N("把一个平角平均分成 %d 份，每份是（　）°。" % n, 180 // n,
                 p3(180 // n, [180 // (n + 1) or 20, 180 // max(n - 1, 1), 180 - n]))
    if mode == "anglecmp":
        k = rng.randint(0, 3)
        if k == 0:
            a = 2 * rng.randint(5, 89)
            return N("∠AOB = %d°，射线 OC 平分 ∠AOB，则 ∠AOC = （　）°。" % a, a // 2,
                     p3(a // 2, [a, (a * 2) % 360 or 10, abs(a // 2 - 10) or 5]))
        if k == 1:
            a = rng.randint(10, 90)
            b = rng.randint(10, 80)
            if a + b >= 180:
                return None
            return N("∠1 = %d°，∠2 = %d°，则 ∠1 + ∠2 = （　）°。" % (a, b), a + b,
                     p3(a + b, [abs(a - b) or 10, a + b + 10, 180 - a - b]))
        if k == 2:
            a = rng.randint(30, 160)
            b = rng.randint(5, a - 1)
            return N("∠AOB = %d°，∠BOC = %d°，射线 OC 在 ∠AOB 的内部，"
                     "则 ∠AOC = （　）°。" % (a, b), a - b,
                     p3(a - b, [a + b, b, abs(a - 2 * b) or 10]))
        a = rng.randint(10, 90)
        b = rng.randint(10, 90)
        return N("∠AOB = %d°，∠BOC = %d°，射线 OC 在 ∠AOB 的外部，"
                 "则 ∠AOC = （　）°。" % (a, b), a + b,
                 p3(a + b, [abs(a - b) or 10, a + b + 10, 180 - (a + b) if a + b < 180
                            else 10]))
    if mode == "comp":
        k = rng.randint(0, 5)
        if k == 0:
            a = rng.randint(1, 89)
            return N("一个角是 %d°，它的余角是（　）°。" % a, 90 - a,
                     p3(90 - a, [90 + a, 180 - a, a]))
        if k == 1:
            a = rng.randint(1, 179)
            return N("一个角是 %d°，它的补角是（　）°。" % a, 180 - a,
                     p3(180 - a, [90 - a if a < 90 else a - 90, a, 360 - a]))
        if k == 2:
            a = rng.randint(1, 89)
            return N("∠1 与 ∠2 互余，∠1 = %d°，则 ∠2 = （　）°。" % a, 90 - a,
                     p3(90 - a, [90 + a, 180 - a, a]))
        if k == 3:
            a = rng.randint(1, 179)
            return N("∠1 与 ∠2 互补，∠1 = %d°，则 ∠2 = （　）°。" % a, 180 - a,
                     p3(180 - a, [90 - a if a < 90 else a - 90, a, 360 - a]))
        if k == 4:
            a = rng.randint(1, 89)
            return N("一个角是 %d°，它的补角比它的余角大（　）°。" % a, 90,
                     p3(90, [180, 90 + a, 180 - a]))
        kk = rng.choice([2, 4, 5, 8, 9])
        if 90 % (kk + 1):
            return None
        v = 90 // (kk + 1)
        return N("∠1 与 ∠2 互余，且 ∠1 是 ∠2 的 %d 倍，则 ∠2 = （　）°。" % kk, v,
                 p3(v, [(90 // kk) or 10, v * kk, 90 - v]))
    return None


# ---------------- 下册 1：相交线与平行线 ----------------
def g_par(rng, mode):
    if mode == "isect":
        k = rng.randint(0, 2)
        if k == 0:
            a = rng.randint(10, 170)
            return N("直线 AB、CD 相交于点 O，∠AOC = %d°，则 ∠BOD = （　）°。" % a, a,
                     p3(a, [180 - a, 90 + a if 90 + a < 180 else a - 90, 360 - a]))
        if k == 1:
            a = rng.randint(10, 170)
            return N("直线 AB、CD 相交于点 O，∠AOC = %d°，则 ∠BOC = （　）°。" % a, 180 - a,
                     p3(180 - a, [a, 360 - a, 180 + a]))
        kk = rng.choice([2, 3, 4, 5, 8, 9])
        if 180 % (kk + 1):
            return None
        v = 180 // (kk + 1)
        return N("直线 AB、CD 相交于点 O，∠BOC 是 ∠AOC 的 %d 倍，则 ∠AOC = （　）°。" % kk, v,
                 p3(v, [(180 // kk) or 10, v * kk, 180 - v]))
    if mode == "perp":
        if rng.randint(0, 1):
            a = rng.randint(1, 30)
            return N("点 P 是直线 l 外一点，PO ⊥ l 于点 O，PO = %d cm，"
                     "则点 P 到直线 l 的距离是（　）cm。" % a, a,
                     p3(a, [2 * a, a + 5, a // 2 or 1]))
        a = rng.randint(1, 89)
        return N("直线 AB ⊥ CD 于点 O，射线 OE 在 ∠AOC 的内部，若 ∠AOE = %d°，"
                 "则 ∠EOC = （　）°。" % a, 90 - a, p3(90 - a, [90 + a, a, 180 - a]))
    if mode == "parprop":
        k = rng.randint(0, 2)
        if k == 0:
            a = rng.randint(10, 170)
            return N("两直线平行，一对同位角中 ∠1 = %d°，则 ∠2 = （　）°。" % a, a,
                     p3(a, [180 - a, 90 + a if 90 + a < 180 else a - 90, a + 10]))
        if k == 1:
            a = rng.randint(10, 170)
            return N("两直线平行，一对内错角中 ∠1 = %d°，则 ∠2 = （　）°。" % a, a,
                     p3(a, [180 - a, 90 + a if 90 + a < 180 else a - 90, a + 10]))
        a = rng.randint(10, 170)
        return N("两直线平行，一对同旁内角中 ∠1 = %d°，则 ∠2 = （　）°。" % a, 180 - a,
                 p3(180 - a, [a, 360 - a, (180 - a + 10) if 180 - a + 10 < 180 else a - 10]))
    if mode == "trans":
        if rng.randint(0, 1):
            a = rng.randint(2, 40)
            return N("线段 AB = %d cm，平移后得到线段 A′B′，则 A′B′ = （　）cm。" % a, a,
                     p3(a, [2 * a, a + 3, a // 2 or 1]))
        a = rng.randint(2, 30)
        return N("△ABC 平移 %d cm 得到 △A′B′C′，则 AA′ = （　）cm。" % a, a,
                 p3(a, [2 * a, a + 2, a // 2 or 1]))
    if mode == "parjud":
        if rng.randint(0, 1):
            a = rng.randint(10, 170)
            stem = "直线 a、b 被直线 c 所截，同位角 ∠1 = ∠2 = %d°，则 a 与 b（　）。" % a
        else:
            a = rng.randint(10, 170)
            stem = ("直线 a、b 被直线 c 所截，同旁内角 ∠1 = %d°，∠2 = %d°，"
                    "且 ∠1 + ∠2 = 180°，则 a 与 b（　）。" % (a, 180 - a))
        return N(stem, "平行", ["垂直", "相交", "重合"])
    return None


# ---------------- 下册 2：实数 ----------------
_CUBES = dict((i ** 3, i) for i in range(-12, 13))
_SQRT_PAIRS = [(2, 8), (2, 18), (3, 12), (2, 32), (5, 20), (3, 27), (6, 24), (7, 28),
               (8, 18), (12, 3)]


def g_real(rng, mode):
    if mode == "sqrt":
        k = rng.randint(0, 5)
        n = rng.randint(1, 20)
        sq = n * n
        if k == 0:
            return N("%d 的算术平方根是（　）。" % sq, n,
                     p3(n, [-n, "±%d" % n, 2 * n, n + 1]))
        if k == 1:
            ans = "±%d" % n
            return N("%d 的平方根是（　）。" % sq, ans,
                     p3(ans, [str(n), str(-n), "±%d" % (n + 1)]))
        if k == 2:
            return N("√%d = （　）。" % sq, n, p3(n, [-n, "±%d" % n, n + 1, 2 * n]))
        if k == 3:
            p = rng.randint(1, 9)
            q = rng.randint(2, 9)
            ans = fs(Fraction(p, q))
            return N("√(%d/%d) = （　）。" % (p * p, q * q), ans,
                     p3(ans, ["%d/%d" % (q, p), "%d/%d" % (p, q * q), "%d/%d" % (p * p, q)]))
        if k == 4:
            n = rng.randint(2, 40)
            if math.isqrt(n) ** 2 == n:
                return None
            return N("√%d 的整数部分是（　）。" % n, math.isqrt(n),
                     p3(math.isqrt(n), [math.isqrt(n) + 1,
                                        math.isqrt(n) - 1 if math.isqrt(n) > 1
                                        else math.isqrt(n) + 2, n]))
        ans = "±%d" % n
        return N("若 x² = %d，则 x = （　）。" % sq, ans,
                 p3(ans, [str(n), str(-n), "±%d" % (n + 1)]))
    if mode == "cube":
        n = rng.choice([i for i in range(-9, 10) if i != 0])
        if rng.randint(0, 1):
            return N("%d 的立方根是（　）。" % (n ** 3), n,
                     p3(n, [-n, n + 1, n - 1, 2 * n]))
        return N("若 x³ = %d，则 x = （　）。" % (n ** 3), n,
                 p3(n, [-n, n + 1, n - 1, 2 * n]))
    if mode == "realop":
        k = rng.randint(0, 4)
        if k == 0:
            n = rng.randint(2, 15)
            return N("(√%d)² = （　）。" % n, n, p3(n, [-n, "√%d" % n, 2 * n, n + 1]))
        if k == 1:
            n = rng.randint(1, 15)
            return N("√((-%d)²) = （　）。" % n, n, p3(n, [-n, "±%d" % n, n + 1, -n - 1]))
        if k == 2:
            n = rng.randint(2, 20)
            ans = "-√%d" % n
            return N("√%d 的相反数是（　）。" % n, ans,
                     p3(ans, ["√%d" % n, "-%d" % n, "±√%d" % n]))
        if k == 3:
            a, b = rng.choice(_SQRT_PAIRS)
            v = math.isqrt(a * b)
            return N("√%d × √%d = （　）。" % (a, b), v,
                     p3(v, ["√%d" % (a * b), a + b, v + 1, v - 1]))
        n = rng.randint(2, 40)
        if math.isqrt(n) ** 2 == n:
            return None
        v = math.isqrt(n) + 1
        return N("估计 √%d 在哪两个连续整数之间，较大的那个整数是（　）。" % n, v,
                 p3(v, [math.isqrt(n), v + 1, n]))
    return None


# ---------------- 下册 3：平面直角坐标系 ----------------
def _pt(x, y):
    return "(%d, %d)" % (x, y)


def g_coor(rng, mode):
    if mode == "point":
        k = rng.randint(0, 6)
        x = rng.choice([i for i in range(-9, 10) if i != 0])
        y = rng.choice([i for i in range(-9, 10) if i != 0])
        if k == 0:
            q = ("一" if x > 0 and y > 0 else "二" if x < 0 and y > 0
                 else "三" if x < 0 and y < 0 else "四")
            return N("点 P%s 在第（　）象限。" % _pt(x, y), q,
                     [c for c in ["一", "二", "三", "四"] if c != q])
        if k == 1:
            return N("点 P%s 到 x 轴的距离是（　）。" % _pt(x, y), abs(y),
                     p3(abs(y), [abs(x), abs(x) + abs(y), abs(y) + 1]))
        if k == 2:
            return N("点 P%s 到 y 轴的距离是（　）。" % _pt(x, y), abs(x),
                     p3(abs(x), [abs(y), abs(x) + abs(y), abs(x) + 1]))
        if k == 3:
            return N("点 P%s 关于 x 轴对称的点的坐标是（　）。" % _pt(x, y), _pt(x, -y),
                     p3(_pt(x, -y), [_pt(-x, y), _pt(-x, -y), _pt(y, x)]))
        if k == 4:
            return N("点 P%s 关于原点对称的点的坐标是（　）。" % _pt(x, y), _pt(-x, -y),
                     p3(_pt(-x, -y), [_pt(x, -y), _pt(-x, y), _pt(y, x)]))
        if k == 5:
            a = rng.randint(1, 9)
            return N("把点 P%s 向右平移 %d 个单位长度，得到的点的坐标是（　）。"
                     % (_pt(x, y), a), _pt(x + a, y),
                     p3(_pt(x + a, y), [_pt(x - a, y), _pt(x, y + a), _pt(x - a, y - a)]))
        a = rng.randint(1, 9)
        return N("把点 P%s 向上平移 %d 个单位长度，得到的点的坐标是（　）。"
                 % (_pt(x, y), a), _pt(x, y + a),
                 p3(_pt(x, y + a), [_pt(x, y - a), _pt(x + a, y), _pt(x - a, y + a)]))
    return None


# ---------------- 下册 4：二元一次方程组 ----------------
_FLIP = {">": "<", "<": ">", "≥": "≤", "≤": "≥"}


def g_sys(rng, mode):
    if mode in ("solve", "sub", "add"):
        x0 = rng.randint(-9, 9)
        y0 = rng.randint(-9, 9)
        a1 = rng.randint(-5, 5)
        b1 = rng.randint(-5, 5)
        a2 = rng.randint(-5, 5)
        b2 = rng.randint(-5, 5)
        det = a1 * b2 - a2 * b1
        if det == 0 or a1 == 0 or b1 == 0 or a2 == 0 or b2 == 0:
            return None
        c1 = a1 * x0 + b1 * y0
        c2 = a2 * x0 + b2 * y0
        e1 = _join([(a1, "x"), (b1, "y")])
        e2 = _join([(a2, "x"), (b2, "y")])
        pre = {"solve": "解方程组", "sub": "用代入法解方程组", "add": "用加减法解方程组"}[mode]
        ask = rng.choice(["x", "y"])
        v = x0 if ask == "x" else y0
        stem = "%s：%s = %d，%s = %d，则 %s = （　）。" % (pre, e1, c1, e2, c2, ask)
        return N(stem, v, p3(v, [v + 1, v - 1, -v, (x0 + y0) if ask == "x" else (x0 - y0)]))
    if mode == "word":
        k = rng.randint(0, 5)
        if k == 0 or k == 1:
            heads = rng.randint(5, 30)
            rab = rng.randint(1, heads - 1)
            feet = 2 * heads + 2 * rab
            v = rab if k == 0 else heads - rab
            stem = "鸡兔同笼，共有头 %d 个，脚 %d 只，%s有（　）只。" % (
                heads, feet, "兔" if k == 0 else "鸡")
            return N(stem, v, p3(v, [heads - v, v + 1, v - 1 if v > 1 else v + 2, heads]))
        if k == 2:
            kk = rng.randint(2, 5)
            d = rng.randint(1, 20)
            y0 = rng.randint(1, 20)
            s = (kk + 1) * y0 + d
            v = fs(Fraction(s - d, kk + 1))
            stem = "甲、乙两数之和是 %d，甲数比乙数的 %d 倍多 %d，则乙数是（　）。" % (s, kk, d)
            return N(stem, v, p3(v, [fs(Fraction(s + d, kk + 1)), fs(Fraction(s, kk + 1)),
                                     fs(Fraction(s - d, kk + 1) + 1), fs(Fraction(s - d, kk))]))
        if k == 3:
            pens = rng.randint(2, 5)
            books = rng.randint(2, 5)
            pp = rng.randint(3, 20)
            bp = rng.randint(2, 15)
            total = pens * pp + books * bp
            stem = ("买 %d 支钢笔和 %d 本笔记本共花 %d 元，每支钢笔 %d 元，"
                    "每本笔记本（　）元。" % (pens, books, total, pp))
            return N(stem, bp, p3(bp, [pp, bp + 1, total // books, bp - 1 if bp > 1 else bp + 2]))
        if k == 4:
            v1 = rng.randint(2, 20)
            v2 = rng.randint(2, 20)
            t = rng.randint(1, 12)
            d = (v1 + v2) * t
            stem = ("甲、乙两人相距 %d km，同时出发相向而行，甲的速度是 %d km/时，"
                    "乙的速度是 %d km/时，经过（　）小时相遇。" % (d, v1, v2))
            return N(stem, t, p3(t, [t + 1, t - 1 if t > 1 else t + 2, d // v1]))
        kk = rng.randint(1, 8)
        s = rng.randint(3, 17)
        if (s + kk) % 2 or (s - kk) % 2:
            return None
        a = (s + kk) // 2
        b = (s - kk) // 2
        if a > 9 or a < 1 or b < 0 or b > 9:
            return None
        v = 10 * a + b
        stem = ("一个两位数，十位数字比个位数字大 %d，两个数字之和是 %d，"
                "这个两位数是（　）。" % (kk, s))
        return N(stem, v, p3(v, [10 * b + a, v + 1, v - 1, 10 * a - b]))
    if mode == "tri":
        x0 = rng.randint(-9, 9)
        y0 = rng.randint(-9, 9)
        z0 = rng.randint(-9, 9)
        a = x0 + y0
        b = y0 + z0
        c = x0 + z0
        if rng.randint(0, 1):
            tot = a - b + c
            if tot % 2:
                return None
            v = tot // 2
            stem = "已知 x + y = %d，y + z = %d，x + z = %d，则 x = （　）。" % (a, b, c)
            return N(stem, v, p3(v, [v + 1, v - 1, (a + b + c) // 2, -v]))
        tot = a + b + c
        if tot % 2:
            return None
        v = tot // 2
        stem = "已知 x + y = %d，y + z = %d，x + z = %d，则 x + y + z = （　）。" % (a, b, c)
        return N(stem, v, p3(v, [v + 1, v - 1, a + b + c, -v]))
    return None


# ---------------- 下册 5：不等式与不等式组 ----------------
def g_ineq(rng, mode):
    if mode == "prop":
        k = rng.randint(0, 3)
        c = rng.randint(2, 20)
        if k == 0:
            return N("若 a > b，则 a + %d（　）b + %d。" % (c, c), ">", ["<", "=", "≥"])
        if k == 1:
            return N("若 a > b，则 a - %d（　）b - %d。" % (c, c), ">", ["<", "=", "≤"])
        if k == 2:
            return N("若 a > b，则 %da（　）%db。" % (c, c), ">", ["<", "=", "≤"])
        return N("若 a > b，则 -%da（　）-%db。" % (c, c), "<", [">", "=", "≤"])
    if mode == "solve1":
        a = rng.choice([-9, -8, -7, -6, -5, -4, -3, -2, 2, 3, 4, 5, 6, 7, 8, 9])
        x0 = rng.randint(-12, 12)
        b = rng.randint(1, 30)
        op = rng.choice([">", "<", "≥", "≤"])
        c = a * x0 + b
        rel = op if a > 0 else _FLIP[op]
        ans = "x %s %s" % (rel, fs(Fraction(c - b, a)))
        stem = "不等式 %dx + %d %s %d 的解集是（　）。" % (a, b, op, c)
        cands = ["x %s %s" % (rel, fs(Fraction(c - b, a) + 1)),
                 "x %s %s" % (_FLIP[rel], fs(Fraction(c - b, a))),
                 "x %s %s" % (rel, fs(Fraction(c, a))),
                 "x %s %s" % (_FLIP[rel], fs(Fraction(c - b, a) + 1))]
        return N(stem, ans, p3(ans, cands))
    if mode == "group":
        k = rng.randint(0, 2)
        if k == 0:
            lo = rng.randint(-10, 8)
            hi = lo + rng.randint(1, 10)
            ans = "%d < x < %d" % (lo, hi)
            stem = "不等式组：x > %d，x < %d 的解集是（　）。" % (lo, hi)
            return N(stem, ans, p3(ans, ["x > %d" % lo, "x < %d" % hi, "无解",
                                         "%d < x < %d" % (lo, hi + 1)]))
        if k == 1:
            a = rng.randint(-10, 10)
            b = rng.randint(-10, 10)
            if a == b:
                return None
            ans = "x > %d" % max(a, b)
            stem = "不等式组：x > %d，x > %d 的解集是（　）。" % (a, b)
            return N(stem, ans, p3(ans, ["x > %d" % min(a, b),
                                         "%d < x < %d" % (min(a, b), max(a, b)), "无解",
                                         "x > %d" % (max(a, b) + 1)]))
        lo = rng.randint(-10, 8)
        hi = lo + rng.randint(1, 10)
        ans = "无解"
        stem = "不等式组：x > %d，x < %d 的解集是（　）。" % (hi, lo)
        return N(stem, ans, p3(ans, ["%d < x < %d" % (lo, hi), "x > %d" % hi, "x < %d" % lo,
                                     "%d < x < %d" % (hi, lo + 10)]))
    return None


# ---------------- 下册 6：数据的收集、整理与描述 ----------------
def g_stat(rng, mode):
    if mode == "survey":
        k = rng.randint(0, 2)
        if k == 0:
            total = rng.choice([40, 50, 60, 80, 100, 200])
            part = rng.choice([5, 10, 20, 25, 40, 50])
            if part >= total or (part * 100) % total:
                return None
            v = part * 100 // total
            stem = "全班有 %d 人，从中抽取 %d 人进行调查，抽样率是（　）%%。" % (total, part)
            return N(stem, v, p3(v, [v + 5, part, total // part, 100 - v]))
        if k == 1:
            total = rng.choice([40, 50, 60, 80, 100])
            part = rng.randint(2, total - 2)
            if (part * 100) % total:
                return None
            v = part * 100 // total
            stem = ("某班 %d 人中，喜欢篮球的有 %d 人，喜欢篮球的人数占全班的（　）%%。"
                    % (total, part))
            return N(stem, v, p3(v, [v + 5, 100 - v, part, v + 1]))
        total = rng.choice([10, 20, 25, 50])
        f = rng.randint(1, max(2, total // 2))
        v = r2(Fraction(f, total))
        stem = "一组数据共有 %d 个，其中某一组的频数是 %d，这一组的频率是（　）。" % (total, f)
        return N(stem, v, p3(v, [r2(Fraction(f + 1, total)), r2(Fraction(f, total) + 1),
                                 str(f), r2(Fraction(f, total) + Fraction(1, 10))]))
    if mode == "chart":
        k = rng.randint(0, 2)
        if k == 0:
            p = rng.choice([10, 15, 20, 25, 30, 40, 50, 60, 75])
            v = p * 360 // 100
            stem = ("在扇形统计图中，某部分占总体的 %d%%，它对应的圆心角是（　）°。" % p)
            return N(stem, v, p3(v, [p, 360 - v, v + 30, v - 30 if v > 30 else v + 60]))
        if k == 1:
            a = rng.choice([36, 54, 72, 90, 108, 144, 180])
            v = a * 100 // 360
            stem = ("在扇形统计图中，某部分对应的圆心角是 %d°，它占总体的（　）%%。" % a)
            return N(stem, v, p3(v, [a, 100 - v, v + 5, v + 10]))
        total = rng.choice([200, 300, 400, 500, 800, 1000])
        p = rng.choice([10, 20, 25, 30, 40, 50])
        v = total * p // 100
        stem = ("某校共有学生 %d 人，参加美术小组的人数占 %d%%，"
                "参加美术小组的有（　）人。" % (total, p))
        return N(stem, v, p3(v, [total - v, v + 10, p, v // 2 or 1]))
    if mode == "histo":
        k = rng.randint(0, 2)
        if k == 0:
            lo = rng.randint(10, 60)
            hi = lo + rng.randint(20, 60)
            d = rng.choice([3, 4, 5, 6, 8, 10])
            v = math.ceil((hi - lo) / d)
            stem = ("一组数据中，最大值是 %d，最小值是 %d，若取组距为 %d，"
                    "则应分为（　）组。" % (hi, lo, d))
            return N(stem, v, p3(v, [v + 1, v - 1 if v > 1 else v + 2,
                                     (hi - lo) // d or 1, (hi - lo) // (d + 1) or 1]))
        if k == 1:
            total = rng.choice([20, 25, 50, 100])
            f = rng.randint(1, max(2, total // 3))
            v = r2(Fraction(f, total))
            stem = ("一个频数分布表中，数据总数为 %d，某组的频数是 %d，"
                    "该组的频率是（　）。" % (total, f))
            return N(stem, v, p3(v, [r2(Fraction(f + 1, total)), r2(Fraction(f, total) + 1),
                                     str(f), r2(Fraction(f - 1 if f > 1 else f + 1, total))]))
        total = rng.choice([20, 25, 40, 50, 100])
        fr = rng.choice(["0.1", "0.2", "0.25", "0.3", "0.4", "0.5"])
        raw = Fraction(D(fr)) * total
        if raw.denominator != 1:
            return None
        v = int(raw)
        stem = ("一个频数分布表中，数据总数为 %d，某组的频率是 %s，"
                "该组的频数是（　）。" % (total, fr))
        return N(stem, v, p3(v, [v + 1, v - 1 if v > 1 else v + 2, total - v, v + 2]))
    return None


# ---------------- 自动验算：题干反解重算 ----------------
def expect_g7(stem):
    """按题干反解重算；识别不了（手写概念题）返回 None，verify 会跳过。"""
    s = stem
    m = None

    # ---- 有理数的运算：计算题（整数四则 + 乘方） ----
    m = re.fullmatch(r"计算：(.*) = （　）", s)
    if m and not re.search(r"[a-zA-Z]", m.group(1)):
        try:
            return fs(eval_expr(m.group(1)))
        except (ValueError, ZeroDivisionError, IndexError):
            return None

    # ---- 科学记数法 / 近似数 ----
    m = re.fullmatch(r"把 (\d+\.\d+)×10\^(\d+) 写成原数是（　）。", s)
    if m:
        return str(int(Fraction(D(m.group(1))) * 10 ** int(m.group(2))))
    m = re.fullmatch(r"把 (\d+) 写成 a×10\^n 的形式（1 ≤ a < 10），则 n = （　）。", s)
    if m:
        return len(m.group(1)) - 1
    m = re.fullmatch(r"把 ([\d.]+) 精确到 (0\.1|0\.01|十分位|百分位|个位) 得（　）。", s)
    if m:
        q = {"0.1": "0.1", "0.01": "0.01", "十分位": "0.1", "百分位": "0.01",
             "个位": "1"}[m.group(2)]
        return round_to(m.group(1), q)

    # ---- 相反数 / 绝对值 ----
    m = re.fullmatch(r"(-?\d+) 的相反数是（　）。", s)
    if m:
        return -int(m.group(1))
    m = re.fullmatch(r"\((-?\d+)\) 的相反数是（　）。", s)
    if m:
        return -int(m.group(1))
    m = re.fullmatch(r"-\((\+?-?\d+)\) 化简的结果是（　）。", s)
    if m:
        return -int(m.group(1))
    m = re.fullmatch(r"若 ([a-z]) 与 (-?\d+) 互为相反数，则 \1 = （　）。", s)
    if m:
        return -int(m.group(2))
    m = re.fullmatch(r"\|(-?\d+)\| = （　）。", s)
    if m:
        return abs(int(m.group(1)))
    m = re.fullmatch(r"\|(-?\d+) - (-?\d+)\| = （　）。", s)
    if m:
        return abs(int(m.group(1)) - int(m.group(2)))
    m = re.fullmatch(r"-\|(-?\d+)\| = （　）。", s)
    if m:
        return -abs(int(m.group(1)))
    m = re.fullmatch(r"若 \|x\| = (\d+)，则 x = （　）。", s)
    if m:
        return "±%s" % m.group(1)
    m = re.fullmatch(r"绝对值等于 (\d+) 的数是（　）。", s)
    if m:
        return "±%s" % m.group(1)

    # ---- 正负数表示 ----
    m = re.fullmatch(r"如果(.+?) (\d+) (.+?)记作 \+?\d+ \3，那么(.+?) (\d+) \3记作（　）\3。", s)
    if m:
        return "-%s" % m.group(5)
    m = re.fullmatch(r"如果(.+?) (\d+) (.+?)记作 \+?\d+ \3，那么 -(\d+) \3表示（　）。", s)
    if m:
        if m.group(1) in _PW2NW:
            return "%s %s %s" % (_PW2NW[m.group(1)][0], m.group(4), m.group(3))
        return None
    m = re.fullmatch(r"某次测验班级平均分是 \d+ 分，规定高于平均分记为正，"
                     r"小明比平均分高 \d+ 分记作 \+\d+ 分，小红比平均分低 (\d+) 分记作（　）分。", s)
    if m:
        return "-%s" % m.group(1)

    # ---- 数轴 ----
    m = re.fullmatch(r"数轴上表示 (-?\d+) 的点到原点的距离是（　）。", s)
    if m:
        return abs(int(m.group(1)))
    m = re.fullmatch(r"数轴上与原点相距 (\d+) 个单位长度的点表示的数是（　）。", s)
    if m:
        return "±%s" % m.group(1)
    m = re.fullmatch(r"数轴上点 A 表示 (-?\d+)，把点 A 向右移动 (\d+) 个单位长度后"
                     r"表示的数是（　）。", s)
    if m:
        return int(m.group(1)) + int(m.group(2))
    m = re.fullmatch(r"数轴上点 A 表示 (-?\d+)，把点 A 向左移动 (\d+) 个单位长度后"
                     r"表示的数是（　）。", s)
    if m:
        return int(m.group(1)) - int(m.group(2))
    m = re.fullmatch(r"数轴上点 A 表示 (-?\d+)，点 B 表示 (-?\d+)，"
                     r"则 A、B 两点之间的距离是（　）。", s)
    if m:
        return abs(int(m.group(1)) - int(m.group(2)))

    # ---- 有理数大小比较 ----
    m = re.fullmatch(r"在 (-?\d+) 和 (-?\d+) 中，较大的数是（　）。", s)
    if m:
        return max(int(m.group(1)), int(m.group(2)))
    m = re.fullmatch(r"在 (-?\d+) 和 (-?\d+) 中，较小的数是（　）。", s)
    if m:
        return min(int(m.group(1)), int(m.group(2)))
    m = re.fullmatch(r"把 (-?\d+)、(-?\d+)、(-?\d+)、(-?\d+) 按从大到小的顺序排列，"
                     r"排在第 2 位的是（　）。", s)
    if m:
        return sorted([int(m.group(i)) for i in (1, 2, 3, 4)], reverse=True)[1]
    m = re.fullmatch(r"在 (-?\d+)、(-?\d+)、(-?\d+)、(-?\d+) 中，绝对值最小的数是（　）。", s)
    if m:
        return min([int(m.group(i)) for i in (1, 2, 3, 4)], key=lambda v: abs(v))

    # ---- 代数式 ----
    m = re.fullmatch(r"「比 ([a-z]) 的 (\d+) 倍大 (\d+) 的数」用代数式表示是（　）。", s)
    if m:
        return "%s%s+%s" % (m.group(2), m.group(1), m.group(3))
    m = re.fullmatch(r"「比 ([a-z]) 的 (\d+) 倍小 (\d+) 的数」用代数式表示是（　）。", s)
    if m:
        return "%s%s-%s" % (m.group(2), m.group(1), m.group(3))
    m = re.fullmatch(r"「([a-z]) 与 ([a-z]) 的和的 (\d+) 倍」用代数式表示是（　）。", s)
    if m:
        return "%s(%s+%s)" % (m.group(3), m.group(1), m.group(2))
    m = re.fullmatch(r"「([a-z]) 与 ([a-z]) 的差的 (\d+) 倍」用代数式表示是（　）。", s)
    if m:
        return "%s(%s-%s)" % (m.group(3), m.group(1), m.group(2))
    m = re.fullmatch(r"「([a-z]) 的平方与 ([a-z]) 的 (\d+) 倍的和」用代数式表示是（　）。", s)
    if m:
        return "%s²+%s%s" % (m.group(1), m.group(3), m.group(2))
    m = re.fullmatch(r"「比 ([a-z]) 大 (\d+) 的数的 (\d+) 倍」用代数式表示是（　）。", s)
    if m:
        return "%s(%s+%s)" % (m.group(3), m.group(1), m.group(2))
    m = re.fullmatch(r"当 ([a-z]) = (-?\d+)，([a-z]) = (-?\d+) 时，代数式 (.*) 的值是（　）。", s)
    if m:
        try:
            return fs(eval_expr(m.group(5), {m.group(1): int(m.group(2)),
                                             m.group(3): int(m.group(4))}))
        except (ValueError, ZeroDivisionError):
            return None
    m = re.fullmatch(r"当 ([a-z]) = (-?\d+) 时，代数式 (.*) 的值是（　）。", s)
    if m:
        try:
            return fs(eval_expr(m.group(3), {m.group(1): int(m.group(2))}))
        except (ValueError, ZeroDivisionError):
            return None

    # ---- 整式 ----
    m = re.fullmatch(r"单项式 (\S+) 的系数是（　）。", s)
    if m:
        r = parse_mono(m.group(1))
        return r[0] if r else None
    m = re.fullmatch(r"单项式 (\S+) 的次数是（　）。", s)
    if m:
        r = parse_mono(m.group(1))
        return r[1] if r else None
    m = re.fullmatch(r"多项式 (.*) 的次数是（　）。", s)
    if m:
        ts = parse_poly(m.group(1))
        return max(d for _c, d in ts) if ts else None
    m = re.fullmatch(r"多项式 (.*) 的常数项是（　）。", s)
    if m:
        for c, d in parse_poly(m.group(1)):
            if d == 0:
                return c
        return 0
    m = re.fullmatch(r"多项式 (.*) 一共有（　）项。", s)
    if m:
        return len(parse_poly(m.group(1)))
    m = re.fullmatch(r"合并同类项：(.*) = （　）", s)
    if m:
        return lin_str(parse_lin(m.group(1)))
    m = re.fullmatch(r"去括号：(-?\d*)\((.*)\) = （　）", s)
    if m:
        g1 = m.group(1)
        k = -1 if g1 == "-" else (1 if g1 == "" else int(g1))
        return lin_str(dict((key, v * k) for key, v in parse_lin(m.group(2)).items()))
    m = re.fullmatch(r"化简：\((.*)\) ([+-]) \((.*)\) = （　）", s)
    if m:
        d1, d2 = parse_lin(m.group(1)), parse_lin(m.group(3))
        sgn = 1 if m.group(2) == "+" else -1
        d = {}
        for key in set(d1) | set(d2):
            c = d1.get(key, 0) + sgn * d2.get(key, 0)
            if c:
                d[key] = c
        return lin_str(d)
    m = re.fullmatch(r"化简：(.*) = （　）", s)
    if m:
        return lin_str(parse_lin(m.group(1)))

    # ---- 一元一次方程 ----
    m = re.fullmatch(r"解方程：(-?\d+)x \+ (\d+) = (-?\d+)x \+ (\d+)，则 x = （　）。", s)
    if m:
        return fs(Fraction(int(m.group(4)) - int(m.group(2)),
                           int(m.group(1)) - int(m.group(3))))
    m = re.fullmatch(r"解方程：(-?\d+)x ([+-]) (\d+) = (-?\d+)，则 x = （　）。", s)
    if m:
        a, b, c = int(m.group(1)), int(m.group(3)), int(m.group(4))
        return fs(Fraction(c - b, a) if m.group(2) == "+" else Fraction(c + b, a))
    m = re.fullmatch(r"一个数的 (\d+) 倍加上 (\d+) 等于 (-?\d+)，这个数是（　）。", s)
    if m:
        return fs(Fraction(int(m.group(3)) - int(m.group(2)), int(m.group(1))))
    m = re.fullmatch(r"一个数的 (\d+) 倍减去 (\d+) 等于 (-?\d+)，这个数是（　）。", s)
    if m:
        return fs(Fraction(int(m.group(3)) + int(m.group(2)), int(m.group(1))))
    m = re.fullmatch(r"一个数的 (\d+) 倍比它本身大 (\d+)，这个数是（　）。", s)
    if m:
        return fs(Fraction(int(m.group(2)), int(m.group(1)) - 1))
    m = re.fullmatch(r"甲数是 x，乙数比甲数的 (\d+) 倍少 (\d+)，两数之和是 (-?\d+)，"
                     r"则 x = （　）。", s)
    if m:
        return fs(Fraction(int(m.group(3)) + int(m.group(2)), int(m.group(1)) + 1))
    m = re.fullmatch(r"一个长方形的长是宽的 (\d+) 倍，周长是 (\d+) cm，宽是（　）cm。", s)
    if m:
        return fs(Fraction(int(m.group(2)), 2 * (int(m.group(1)) + 1)))
    m = re.fullmatch(r"一件商品按标价打 (\d+) 折出售，售价是 (\d+) 元，标价是（　）元。", s)
    if m:
        return fs(Fraction(int(m.group(2)) * 10, int(m.group(1))))

    # ---- 几何图形初步：线段 ----
    m = re.fullmatch(r"线段 AB 长 (\d+) cm，点 C 是 AB 的中点，则 AC = （　）cm。", s)
    if m:
        return fs(Fraction(int(m.group(1)), 2))
    m = re.fullmatch(r"已知线段 AB = (\d+) cm，点 C 在线段 AB 上，且 AC = (\d+) cm，"
                     r"则 BC = （　）cm。", s)
    if m:
        return int(m.group(1)) - int(m.group(2))
    m = re.fullmatch(r"点 C 是线段 AB 的中点，AC = (\d+) cm，则 AB = （　）cm。", s)
    if m:
        return 2 * int(m.group(1))
    m = re.fullmatch(r"已知线段 AB = (\d+) cm，延长 AB 到点 C，使 BC = (\d+) cm，"
                     r"则 AC = （　）cm。", s)
    if m:
        return int(m.group(1)) + int(m.group(2))
    m = re.fullmatch(r"点 C、D 是线段 AB 的三等分点，AB = (\d+) cm，则 AC = （　）cm。", s)
    if m:
        return fs(Fraction(int(m.group(1)), 3))

    # ---- 几何图形初步：角 ----
    m = re.fullmatch(r"([\d.]+)° = （　）′", s)
    if m:
        v = D(m.group(1)) * 60
        return str(int(v))
    m = re.fullmatch(r"(\d+)′ = （　）°", s)
    if m:
        return fmt(D(m.group(1)) / 60)
    m = re.fullmatch(r"钟面上 (\d+) 点整，时针与分针的夹角是（　）°。", s)
    if m:
        h = int(m.group(1))
        return min(h * 30, 360 - h * 30)
    m = re.fullmatch(r"把一个周角平均分成 (\d+) 份，每份是（　）°。", s)
    if m:
        return fs(Fraction(360, int(m.group(1))))
    m = re.fullmatch(r"把一个平角平均分成 (\d+) 份，每份是（　）°。", s)
    if m:
        return fs(Fraction(180, int(m.group(1))))
    m = re.fullmatch(r"∠AOB = (\d+)°，射线 OC 平分 ∠AOB，则 ∠AOC = （　）°。", s)
    if m:
        return fs(Fraction(int(m.group(1)), 2))
    m = re.fullmatch(r"∠1 = (\d+)°，∠2 = (\d+)°，则 ∠1 \+ ∠2 = （　）°。", s)
    if m:
        return int(m.group(1)) + int(m.group(2))
    m = re.fullmatch(r"∠AOB = (\d+)°，∠BOC = (\d+)°，射线 OC 在 ∠AOB 的内部，"
                     r"则 ∠AOC = （　）°。", s)
    if m:
        return int(m.group(1)) - int(m.group(2))
    m = re.fullmatch(r"∠AOB = (\d+)°，∠BOC = (\d+)°，射线 OC 在 ∠AOB 的外部，"
                     r"则 ∠AOC = （　）°。", s)
    if m:
        return int(m.group(1)) + int(m.group(2))
    m = re.fullmatch(r"一个角是 (\d+)°，它的余角是（　）°。", s)
    if m:
        return 90 - int(m.group(1))
    m = re.fullmatch(r"一个角是 (\d+)°，它的补角是（　）°。", s)
    if m:
        return 180 - int(m.group(1))
    m = re.fullmatch(r"∠1 与 ∠2 互余，∠1 = (\d+)°，则 ∠2 = （　）°。", s)
    if m:
        return 90 - int(m.group(1))
    m = re.fullmatch(r"∠1 与 ∠2 互补，∠1 = (\d+)°，则 ∠2 = （　）°。", s)
    if m:
        return 180 - int(m.group(1))
    m = re.fullmatch(r"一个角是 (\d+)°，它的补角比它的余角大（　）°。", s)
    if m:
        return 90
    m = re.fullmatch(r"∠1 与 ∠2 互余，且 ∠1 是 ∠2 的 (\d+) 倍，则 ∠2 = （　）°。", s)
    if m:
        return fs(Fraction(90, int(m.group(1)) + 1))

    # ---- 相交线与平行线 ----
    m = re.fullmatch(r"直线 AB、CD 相交于点 O，∠AOC = (\d+)°，则 ∠BOD = （　）°。", s)
    if m:
        return int(m.group(1))
    m = re.fullmatch(r"直线 AB、CD 相交于点 O，∠AOC = (\d+)°，则 ∠BOC = （　）°。", s)
    if m:
        return 180 - int(m.group(1))
    m = re.fullmatch(r"直线 AB、CD 相交于点 O，∠BOC 是 ∠AOC 的 (\d+) 倍，"
                     r"则 ∠AOC = （　）°。", s)
    if m:
        return fs(Fraction(180, int(m.group(1)) + 1))
    m = re.fullmatch(r"点 P 是直线 l 外一点，PO ⊥ l 于点 O，PO = (\d+) cm，"
                     r"则点 P 到直线 l 的距离是（　）cm。", s)
    if m:
        return int(m.group(1))
    m = re.fullmatch(r"直线 AB ⊥ CD 于点 O，射线 OE 在 ∠AOC 的内部，若 ∠AOE = (\d+)°，"
                     r"则 ∠EOC = （　）°。", s)
    if m:
        return 90 - int(m.group(1))
    m = re.fullmatch(r"两直线平行，一对同位角中 ∠1 = (\d+)°，则 ∠2 = （　）°。", s)
    if m:
        return int(m.group(1))
    m = re.fullmatch(r"两直线平行，一对内错角中 ∠1 = (\d+)°，则 ∠2 = （　）°。", s)
    if m:
        return int(m.group(1))
    m = re.fullmatch(r"两直线平行，一对同旁内角中 ∠1 = (\d+)°，则 ∠2 = （　）°。", s)
    if m:
        return 180 - int(m.group(1))
    m = re.fullmatch(r"线段 AB = (\d+) cm，平移后得到线段 A′B′，则 A′B′ = （　）cm。", s)
    if m:
        return int(m.group(1))
    m = re.fullmatch(r"△ABC 平移 (\d+) cm 得到 △A′B′C′，则 AA′ = （　）cm。", s)
    if m:
        return int(m.group(1))
    m = re.fullmatch(r"直线 a、b 被直线 c 所截，同位角 ∠1 = ∠2 = \d+°，则 a 与 b（　）。", s)
    if m:
        return "平行"
    m = re.fullmatch(r"直线 a、b 被直线 c 所截，同旁内角 ∠1 = \d+°，∠2 = \d+°，"
                     r"且 ∠1 \+ ∠2 = 180°，则 a 与 b（　）。", s)
    if m:
        return "平行"

    # ---- 实数 ----
    m = re.fullmatch(r"(\d+) 的算术平方根是（　）。", s)
    if m:
        n = math.isqrt(int(m.group(1)))
        return str(n) if n * n == int(m.group(1)) else None
    m = re.fullmatch(r"(\d+) 的平方根是（　）。", s)
    if m:
        n = math.isqrt(int(m.group(1)))
        return "±%d" % n if n * n == int(m.group(1)) else None
    m = re.fullmatch(r"√(\d+) = （　）。", s)
    if m:
        n = math.isqrt(int(m.group(1)))
        return str(n) if n * n == int(m.group(1)) else None
    m = re.fullmatch(r"√\((\d+)/(\d+)\) = （　）。", s)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        p, q = math.isqrt(a), math.isqrt(b)
        if p * p != a or q * q != b:
            return None
        return fs(Fraction(p, q))
    m = re.fullmatch(r"√(\d+) 的整数部分是（　）。", s)
    if m:
        return math.isqrt(int(m.group(1)))
    m = re.fullmatch(r"若 x² = (\d+)，则 x = （　）。", s)
    if m:
        n = math.isqrt(int(m.group(1)))
        return "±%d" % n if n * n == int(m.group(1)) else None
    m = re.fullmatch(r"(-?\d+) 的立方根是（　）。", s)
    if m:
        return _CUBES.get(int(m.group(1)))
    m = re.fullmatch(r"若 x³ = (-?\d+)，则 x = （　）。", s)
    if m:
        return _CUBES.get(int(m.group(1)))
    m = re.fullmatch(r"\(√(\d+)\)² = （　）。", s)
    if m:
        return int(m.group(1))
    m = re.fullmatch(r"√\(\(-(\d+)\)²\) = （　）。", s)
    if m:
        return int(m.group(1))
    m = re.fullmatch(r"√(\d+) 的相反数是（　）。", s)
    if m:
        return "-√%s" % m.group(1)
    m = re.fullmatch(r"√(\d+) × √(\d+) = （　）。", s)
    if m:
        n = math.isqrt(int(m.group(1)) * int(m.group(2)))
        return str(n) if n * n == int(m.group(1)) * int(m.group(2)) else None
    m = re.fullmatch(r"估计 √(\d+) 在哪两个连续整数之间，较大的那个整数是（　）。", s)
    if m:
        return math.isqrt(int(m.group(1))) + 1

    # ---- 平面直角坐标系 ----
    m = re.fullmatch(r"点 P\((-?\d+), (-?\d+)\) 在第（　）象限。", s)
    if m:
        x, y = int(m.group(1)), int(m.group(2))
        return ("一" if x > 0 and y > 0 else "二" if x < 0 and y > 0
                else "三" if x < 0 and y < 0 else "四")
    m = re.fullmatch(r"点 P\((-?\d+), (-?\d+)\) 到 x 轴的距离是（　）。", s)
    if m:
        return abs(int(m.group(2)))
    m = re.fullmatch(r"点 P\((-?\d+), (-?\d+)\) 到 y 轴的距离是（　）。", s)
    if m:
        return abs(int(m.group(1)))
    m = re.fullmatch(r"点 P\((-?\d+), (-?\d+)\) 关于 x 轴对称的点的坐标是（　）。", s)
    if m:
        return _pt(int(m.group(1)), -int(m.group(2)))
    m = re.fullmatch(r"点 P\((-?\d+), (-?\d+)\) 关于原点对称的点的坐标是（　）。", s)
    if m:
        return _pt(-int(m.group(1)), -int(m.group(2)))
    m = re.fullmatch(r"把点 P\((-?\d+), (-?\d+)\) 向右平移 (\d+) 个单位长度，"
                     r"得到的点的坐标是（　）。", s)
    if m:
        return _pt(int(m.group(1)) + int(m.group(3)), int(m.group(2)))
    m = re.fullmatch(r"把点 P\((-?\d+), (-?\d+)\) 向上平移 (\d+) 个单位长度，"
                     r"得到的点的坐标是（　）。", s)
    if m:
        return _pt(int(m.group(1)), int(m.group(2)) + int(m.group(3)))

    # ---- 二元一次方程组 ----
    m = re.fullmatch(r"(?:解方程组|用代入法解方程组|用加减法解方程组)："
                     r"(.*) = (-?\d+)，(.*) = (-?\d+)，则 (x|y) = （　）。", s)
    if m:
        d1, d2 = parse_lin(m.group(1)), parse_lin(m.group(3))
        a1, b1 = d1.get("x", 0), d1.get("y", 0)
        a2, b2 = d2.get("x", 0), d2.get("y", 0)
        c1, c2 = int(m.group(2)), int(m.group(4))
        det = a1 * b2 - a2 * b1
        if det == 0:
            return None
        return fs(Fraction(c1 * b2 - c2 * b1, det) if m.group(5) == "x"
                  else Fraction(a1 * c2 - a2 * c1, det))
    m = re.fullmatch(r"鸡兔同笼，共有头 (\d+) 个，脚 (\d+) 只，兔有（　）只。", s)
    if m:
        return fs(Fraction(int(m.group(2)) - 2 * int(m.group(1)), 2))
    m = re.fullmatch(r"鸡兔同笼，共有头 (\d+) 个，脚 (\d+) 只，鸡有（　）只。", s)
    if m:
        return int(m.group(1)) - (int(m.group(2)) - 2 * int(m.group(1))) // 2
    m = re.fullmatch(r"甲、乙两数之和是 (\d+)，甲数比乙数的 (\d+) 倍多 (\d+)，"
                     r"则乙数是（　）。", s)
    if m:
        return fs(Fraction(int(m.group(1)) - int(m.group(3)), int(m.group(2)) + 1))
    m = re.fullmatch(r"买 (\d+) 支钢笔和 (\d+) 本笔记本共花 (\d+) 元，每支钢笔 (\d+) 元，"
                     r"每本笔记本（　）元。", s)
    if m:
        return fs(Fraction(int(m.group(3)) - int(m.group(1)) * int(m.group(4)),
                           int(m.group(2))))
    m = re.fullmatch(r"甲、乙两人相距 (\d+) km，同时出发相向而行，甲的速度是 (\d+) km/时，"
                     r"乙的速度是 (\d+) km/时，经过（　）小时相遇。", s)
    if m:
        return fs(Fraction(int(m.group(1)), int(m.group(2)) + int(m.group(3))))
    m = re.fullmatch(r"一个两位数，十位数字比个位数字大 (\d+)，两个数字之和是 (\d+)，"
                     r"这个两位数是（　）。", s)
    if m:
        kk, sm = int(m.group(1)), int(m.group(2))
        return 10 * ((sm + kk) // 2) + (sm - kk) // 2
    m = re.fullmatch(r"已知 x \+ y = (-?\d+)，y \+ z = (-?\d+)，x \+ z = (-?\d+)，"
                     r"则 x = （　）。", s)
    if m:
        v = int(m.group(1)) - int(m.group(2)) + int(m.group(3))
        return fs(Fraction(v, 2))
    m = re.fullmatch(r"已知 x \+ y = (-?\d+)，y \+ z = (-?\d+)，x \+ z = (-?\d+)，"
                     r"则 x \+ y \+ z = （　）。", s)
    if m:
        return fs(Fraction(int(m.group(1)) + int(m.group(2)) + int(m.group(3)), 2))

    # ---- 不等式与不等式组 ----
    m = re.fullmatch(r"若 a > b，则 a \+ \d+（　）b \+ \d+。", s)
    if m:
        return ">"
    m = re.fullmatch(r"若 a > b，则 a - \d+（　）b - \d+。", s)
    if m:
        return ">"
    m = re.fullmatch(r"若 a > b，则 \d+a（　）\d+b。", s)
    if m:
        return ">"
    m = re.fullmatch(r"若 a > b，则 -\d+a（　）-\d+b。", s)
    if m:
        return "<"
    m = re.fullmatch(r"不等式 (-?\d+)x \+ (\d+) (>|<|≥|≤) (-?\d+) 的解集是（　）。", s)
    if m:
        a, b, op, c = int(m.group(1)), int(m.group(2)), m.group(3), int(m.group(4))
        return "x %s %s" % (op if a > 0 else _FLIP[op], fs(Fraction(c - b, a)))
    m = re.fullmatch(r"不等式组：x (>|<) (-?\d+)，x (>|<) (-?\d+) 的解集是（　）。", s)
    if m:
        lo = hi = None
        for i in (0, 2):
            rel, val = m.group(i + 1), int(m.group(i + 2))
            if rel == ">":
                lo = val if lo is None else max(lo, val)
            else:
                hi = val if hi is None else min(hi, val)
        if lo is None and hi is None:
            return None
        if lo is None:
            return "x < %d" % hi
        if hi is None:
            return "x > %d" % lo
        return "%d < x < %d" % (lo, hi) if lo < hi else "无解"

    # ---- 数据的收集、整理与描述 ----
    m = re.fullmatch(r"全班有 (\d+) 人，从中抽取 (\d+) 人进行调查，抽样率是（　）%。", s)
    if m:
        return fs(Fraction(int(m.group(2)) * 100, int(m.group(1))))
    m = re.fullmatch(r"某班 (\d+) 人中，喜欢篮球的有 (\d+) 人，"
                     r"喜欢篮球的人数占全班的（　）%。", s)
    if m:
        return fs(Fraction(int(m.group(2)) * 100, int(m.group(1))))
    m = re.fullmatch(r"一组数据共有 (\d+) 个，其中某一组的频数是 (\d+)，"
                     r"这一组的频率是（　）。", s)
    if m:
        return r2(Fraction(int(m.group(2)), int(m.group(1))))
    m = re.fullmatch(r"在扇形统计图中，某部分占总体的 (\d+)%，它对应的圆心角是（　）°。", s)
    if m:
        return fs(Fraction(int(m.group(1)) * 360, 100))
    m = re.fullmatch(r"在扇形统计图中，某部分对应的圆心角是 (\d+)°，它占总体的（　）%。", s)
    if m:
        return fs(Fraction(int(m.group(1)) * 100, 360))
    m = re.fullmatch(r"某校共有学生 (\d+) 人，参加美术小组的人数占 (\d+)%，"
                     r"参加美术小组的有（　）人。", s)
    if m:
        return fs(Fraction(int(m.group(1)) * int(m.group(2)), 100))
    m = re.fullmatch(r"一组数据中，最大值是 (\d+)，最小值是 (\d+)，若取组距为 (\d+)，"
                     r"则应分为（　）组。", s)
    if m:
        hi, lo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return math.ceil(Fraction(hi - lo, d))
    m = re.fullmatch(r"一个频数分布表中，数据总数为 (\d+)，某组的频数是 (\d+)，"
                     r"该组的频率是（　）。", s)
    if m:
        return r2(Fraction(int(m.group(2)), int(m.group(1))))
    m = re.fullmatch(r"一个频数分布表中，数据总数为 (\d+)，某组的频率是 ([\d.]+)，"
                     r"该组的频数是（　）。", s)
    if m:
        return fs(Fraction(D(m.group(2))) * int(m.group(1)))
    return None


def verify(units):
    """按题干反解重算，与标注答案比对（只查能被反解的题，手写概念题跳过）。"""
    total = 0
    bad = 0
    for uname, lessons in units:
        for lname, _bc, qs in lessons:
            for q in qs:
                stem = q[1]
                ans = str(q[2][0])
                v = expect_g7(stem)
                if v is None:
                    continue
                total += 1
                if str(v) != ans:
                    bad += 1
                    if bad <= 20:
                        print("答案错误: %s | %s | 期望 %s 标注 %s"
                              % (lname, stem[:46], v, ans))
    if bad == 0:
        print("验算 %d/%d 全对" % (total, total))
    else:
        print("验算 %d/%d，错误 %d" % (total - bad, total, bad))
    return 0 if bad == 0 else 1


MODES = [("g_rat", g_rat, ["pos", "axis", "opp", "abs", "cmp"]),
         ("g_rop", g_rop, ["add", "sub", "addsub", "mul", "div", "mix", "pow", "sci",
                           "approx"]),
         ("g_alg", g_alg, ["write", "val"]),
         ("g_poly", g_poly, ["mono", "poly", "comb", "brk", "addsub"]),
         ("g_eq", g_eq, ["solve", "word"]),
         ("g_geo", g_geo, ["seg", "angle", "anglecmp", "comp"]),
         ("g_par", g_par, ["isect", "perp", "parprop", "trans", "parjud"]),
         ("g_real", g_real, ["sqrt", "cube", "realop"]),
         ("g_coor", g_coor, ["point"]),
         ("g_sys", g_sys, ["solve", "sub", "add", "word", "tri"]),
         ("g_ineq", g_ineq, ["prop", "solve1", "group"]),
         ("g_stat", g_stat, ["survey", "chart", "histo"])]


def selftest(n=20, seeds=(20260930, 4242, 777)):
    """抽查每种模式：确认出的题都能被 expect 反解，且重算结果与标注一致。"""
    total = missing = bad = 0
    for name, fn, modes in MODES:
        for mode in modes:
            for seed in seeds:
                try:
                    qs = gen(fn, n, seed, mode)
                except SystemExit as e:
                    print("出题不足：%s/%s seed=%s —— %s" % (name, mode, seed, e))
                    bad += 1
                    continue
                for q in qs:
                    total += 1
                    stem, opts = q[1], q[2]
                    v = expect_g7(stem)
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
    print("本模块只提供给 build_math_g7v1_quiz.py / build_math_g7v2_quiz.py 使用")
