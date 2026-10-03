# -*- coding: utf-8 -*-
"""库页筛选实测（登录态）：统计各筛选条件下的卡片数与选中态。
用法: python tools/lib_check.py [base_url]
"""
import sys
import http.cookiejar
import urllib.parse
import urllib.request
import urllib.error
import re

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8666"

cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(
    urllib.request.ProxyHandler({}),
    urllib.request.HTTPCookieProcessor(cj),
)


def safe(path, data=None):
    body = None
    headers = {}
    if data is not None:
        body = urllib.parse.urlencode(data).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    try:
        r = op.open(urllib.request.Request(BASE + path, data=body,
                                           headers=headers), timeout=30)
        return r.getcode(), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return -1, "ERR %s" % e


# 登录（表单字段 username / password；先 GET 一次注册页保证同源 cookie）
USER, PWD = "tbcheck", "tbcheck123"
safe("/register")
c, b = safe("/login", {"username": USER, "password": PWD})
_c, _b = safe("/textbook")
if "教材库" not in _b:
    print("登录未成功:", c, b[:200])
    raise SystemExit(1)

CASES = [
    ("全库（全年级全学科）", "/textbook?stage=&grade=&subject="),
    ("仅小学", "/textbook?stage=primary&grade=&subject="),
    ("小学四年级语文", "/textbook?stage=primary&grade=4&subject=chinese"),
    ("初中数学", "/textbook?stage=middle&grade=&subject=math"),
    ("高中全部", "/textbook?stage=high&grade=&subject="),
    ("非法参数应被忽略", "/textbook?stage=&grade=99&subject=math"),
]

print("=" * 66)
print("%-22s %-6s %-7s %s" % ("筛选", "卡片", "库标题", "选中态"))
print("=" * 66)
for label, url in CASES:
    code, body = safe(url)
    cards = body.count('class="tb-lb"')
    on = re.findall(r'class="tb-chip is-on"[^>]*>([^<]+)<', body)
    print("%-22s %-6d %-7s %s" % (label, cards, "教材库" in body,
                                   " / ".join(x.strip() for x in on)))
print("=" * 66)
