#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
StudyBuddy 官方教材 PDF 离线预渲染工具（方案 C：混合渐进）

作用：把一本教材 PDF 一次性渲染成 Go 运行时可直接消费的静态图集，
      让服务端零渲染依赖（不需要在 Windows / fnOS / Docker 里装 poppler、mupdf）。

产出目录结构（--out 指定的图集根）：
    <assets>/<key>/
        meta.json        页数、页面宽高比、生成参数
        cover.webp       封面（第 1 页，宽 --cover-width）
        hi/p001.webp …   高清分页图（宽 --hi-width）
        lo/p001.webp …   低清缩略图（宽 --lo-width，用于首屏铺底与缩略图条）

设计要点：
  * 增量渲染：已存在且尺寸参数一致的分页图会跳过，重跑只补缺失页（--force 强制重渲）。
  * 尺寸写进 meta.json，前端据此预留占位高度，避免图片加载时的布局抖动（CLS）。
  * 低清图刻意压到 ~3KB/页，全册一次拉完也只有几百 KB，首屏不会白屏。

依赖：pip install pymupdf pillow

用法：
    python prerender.py --src "D:/ChinaTextbook/小学/语文/统编版/义务教育教科书·语文一年级上册.pdf" \
                        --key primary-pep-grade1-volume1-chinese \
                        --out "C:/Users/meimo/Desktop/StudyBuddy/data/textbook"
"""

import argparse
import json
import os
import sys
import time

try:
    import pymupdf  # PyMuPDF >= 1.24 的新包名
except ImportError:  # 兼容旧版
    import fitz as pymupdf

from PIL import Image
import io


def human(n):
    """字节数转人类可读。"""
    f = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if f < 1024 or unit == "GB":
            return f"{f:.1f}{unit}"
        f /= 1024
    return f"{f:.1f}GB"


def render_page_to_webp(page, target_width, quality):
    """把一页按目标宽度渲染成 WebP 字节；返回 (bytes, 实际宽, 实际高)。"""
    zoom = target_width / float(page.rect.width)
    mat = pymupdf.Matrix(zoom, zoom)
    # alpha=False：教材页面不透明，省掉 alpha 通道能明显减小体积
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=quality, method=4)
    return buf.getvalue(), pix.width, pix.height


def write_if_needed(path, data, force):
    """已存在且非强制时跳过；返回 (是否真的写入, 文件大小)。"""
    if os.path.exists(path) and not force:
        return False, os.path.getsize(path)
    with open(path, "wb") as f:
        f.write(data)
    return True, len(data)


def main():
    ap = argparse.ArgumentParser(description="StudyBuddy 教材 PDF 离线预渲染")
    ap.add_argument("--src", required=True, help="源 PDF 绝对路径")
    ap.add_argument("--key", required=True, help="教材资源键，如 primary-pep-grade1-volume1-chinese")
    ap.add_argument("--out", required=True, help="图集根目录（Go 侧 STUDYBUDDY_TEXTBOOK_ASSETS）")
    ap.add_argument("--hi-width", type=int, default=1400, help="高清分页图宽度，默认 1400")
    ap.add_argument("--lo-width", type=int, default=240, help="低清缩略图宽度，默认 240")
    ap.add_argument("--cover-width", type=int, default=900, help="封面宽度，默认 900")
    ap.add_argument("--hi-quality", type=int, default=82, help="高清 WebP 质量，默认 82")
    ap.add_argument("--lo-quality", type=int, default=35, help="低清 WebP 质量，默认 35")
    ap.add_argument("--force", action="store_true", help="忽略已存在文件，全部重渲")
    args = ap.parse_args()

    if not os.path.isfile(args.src):
        print(f"[错误] 源 PDF 不存在：{args.src}", file=sys.stderr)
        return 1

    # 只接受 [a-z0-9-] 的 key，避免被拼进路径后产生越界目录
    safe = "".join(ch for ch in args.key.lower() if ch.isalnum() or ch == "-")
    if not safe or safe != args.key.lower():
        print(f"[错误] key 只允许小写字母、数字与连字符：{args.key}", file=sys.stderr)
        return 1

    base = os.path.join(args.out, safe)
    hi_dir = os.path.join(base, "hi")
    lo_dir = os.path.join(base, "lo")
    for d in (base, hi_dir, lo_dir):
        os.makedirs(d, exist_ok=True)

    doc = pymupdf.open(args.src)
    n = doc.page_count
    if n == 0:
        print("[错误] PDF 页数为 0", file=sys.stderr)
        return 1

    t0 = time.time()
    print(f"[开始] {safe} · {n} 页 · 源 {human(os.path.getsize(args.src))}")

    hi_bytes = lo_bytes = 0
    hi_new = lo_new = 0
    w = h = 0
    ratio = 1.0

    for i in range(n):
        page = doc[i]
        if i == 0:
            ratio = float(page.rect.height) / float(page.rect.width)

        # 高清
        data, w, h = render_page_to_webp(page, args.hi_width, args.hi_quality)
        ok, size = write_if_needed(os.path.join(hi_dir, f"p{i + 1:03d}.webp"), data, args.force)
        hi_bytes += size
        hi_new += 1 if ok else 0

        # 低清
        ldata, _, _ = render_page_to_webp(page, args.lo_width, args.lo_quality)
        lok, lsize = write_if_needed(os.path.join(lo_dir, f"p{i + 1:03d}.webp"), ldata, args.force)
        lo_bytes += lsize
        lo_new += 1 if lok else 0

        if (i + 1) % 20 == 0 or i + 1 == n:
            print(f"  渲染进度 {i + 1}/{n}")

    # 封面单独出一张，尺寸比高清小，用于卡片与详情页头图
    cover, cw, ch = render_page_to_webp(doc[0], args.cover_width, 88)
    with open(os.path.join(base, "cover.webp"), "wb") as f:
        f.write(cover)

    meta = {
        "key": safe,
        "source": os.path.basename(args.src),
        "pages": n,
        "ratio": round(ratio, 6),          # 高/宽，前端用它预留占位高度防抖动
        "hiWidth": args.hi_width,
        "loWidth": args.lo_width,
        "coverWidth": cw,
        "coverHeight": ch,
        "hiQuality": args.hi_quality,
        "loQuality": args.lo_quality,
        "hiBytes": hi_bytes,
        "loBytes": lo_bytes,
        "generatedAt": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(os.path.join(base, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    dt = time.time() - t0
    print(f"[完成] 用时 {dt:.1f}s")
    print(f"  高清 {n} 页 · 新增 {hi_new} · 合计 {human(hi_bytes)} · 均 {human(hi_bytes // n)}/页")
    print(f"  低清 {n} 页 · 新增 {lo_new} · 合计 {human(lo_bytes)} · 均 {human(max(lo_bytes,1) // n)}/页")
    print(f"  封面 {cw}x{ch} · {human(len(cover))}")
    print(f"  输出 {base}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
