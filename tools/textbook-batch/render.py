"""按 manifest.json 批量预渲染教材图集。

分两个阶段，理由是代价差了两个数量级（实测：本机 283 册共 32151 页）
--------------------------------------------------------------------------
* **低清 + 封面**（默认阶段）：240px WebP，约 0.085s/页 → 全部约 45 分钟、
  约 0.15GB。做完全站 283 册立刻可读、可看缩略图条、首屏只拉当前页。
* **高清**：1400px WebP，约 0.49s/页 → 全部约 4.4 小时、约 5GB。
  因此高清**按需增量**：某一册第一次被打开后，用 ``--hi-only`` 单独补这一册，
  补完前端自动从低清升级到高清（meta.json 的 ``hiReady`` 字段控制）。

用法
----
    # 阶段一：全量封面 + 低清（可随时中断，重跑自动跳过已完成的册）
    python tools/textbook-batch/render.py --manifest data/textbook/manifest.json

    # 只渲染某几册的高清
    python tools/textbook-batch/render.py --hi-only primary-chinese-g4-v1,primary-math-g4-v1

    # 强制重渲某册
    python tools/textbook-batch/render.py --force --only primary-math-g4-v1

断点续跑
--------
每册做完立刻写 meta.json（阶段一结束即写 ``loReady``）。重跑时若该册
``loReady`` 为真且分页图数量齐全，则整册跳过；``--force`` 可强制重来。

源 PDF 更新了怎么办
------------------
``meta.json`` 会记下当时源文件的 ``srcSize`` / ``srcMtime``。重跑时若源文件
的大小或修改时间与记录不一致，说明 PDF 换过版本，这一册会**自动重渲染**，
不需要手动 ``--force``。加 ``--check-source`` 可只做体检、只报告哪些册
需要更新而不动手（更新前先跑一次，看看要动多少册）。
"""

import argparse
import io
import json
import os
import sys
import time

import pymupdf
from PIL import Image

# 渲染优先级：小学 → 初中 → 高中，年级小的先用上。
STAGE_ORDER = {"primary": 0, "middle": 1, "high": 2}


def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return "%.1f%s" % (n, unit)
        n /= 1024.0


def render_page(doc, idx, target_width, quality):
    """渲染第 idx 页为 WebP 字节；返回 (bytes, 宽, 高)。"""
    page = doc[idx]
    w = page.rect.width
    pix = page.get_pixmap(matrix=pymupdf.Matrix(target_width / w, target_width / w))
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=quality, method=4)
    return buf.getvalue(), pix.width, pix.height


def load_manifest(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def book_dir(assets, book):
    return os.path.join(assets, book["key"])


def read_meta(assets, book):
    p = os.path.join(book_dir(assets, book), "meta.json")
    if not os.path.exists(p):
        return {}
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def write_meta(assets, book, meta):
    d = book_dir(assets, book)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def pages_done(assets, book, kind, pages):
    """已渲染的分页图是否齐全（避免半截产物被当成已完成）。"""
    d = os.path.join(book_dir(assets, book), kind)
    if not os.path.isdir(d):
        return 0
    n = len([f for f in os.listdir(d) if f.endswith(".webp")])
    return n >= pages


def src_stamp(path):
    """源 PDF 的轻量指纹：大小 + 修改时间。

    不算 md5 —— 一册 PDF 动辄几十上百 MB，全量算哈希要几分钟；
    仓库里更新教材一定是换了新文件，size/mtime 足够可靠且是 O(1)。
    """
    try:
        st = os.stat(path)
    except OSError:
        return None, None
    return st.st_size, int(st.st_mtime)


def src_changed(meta, path):
    """源 PDF 是否与渲染时记录的版本不同。

    meta 里没有记录（老产物）时返回 True —— 宁可多重渲一册，
    也不能让旧图冒充新教材。
    """
    old_size, old_mtime = meta.get("srcSize"), meta.get("srcMtime")
    if old_size is None or old_mtime is None:
        return True
    size, mtime = src_stamp(path)
    if size is None:
        return False
    return size != old_size or mtime != old_mtime


def render_book(assets, src, book, args, meta):
    """渲染一册的封面 + 指定清晰度；返回更新后的 meta。"""
    key = book["key"]
    base = book_dir(assets, book)
    lo_dir, hi_dir = os.path.join(base, "lo"), os.path.join(base, "hi")
    os.makedirs(lo_dir, exist_ok=True)

    doc = pymupdf.open(src)
    n = doc.page_count
    ratio = round(doc[0].rect.height / doc[0].rect.width, 6)
    doc.close()

    meta.update({
        "key": key,
        "source": os.path.basename(src),
        "title": book["title"],
        "subject": book["subject"],
        "subjectCN": book["subjectCN"],
        "stage": book["stage"],
        "grade": book["grade"],
        "volume": book["volume"],
        "version": book["version"],
        "pages": n,
        "ratio": ratio,
        "hiWidth": args.hi_width,
        "loWidth": args.lo_width,
        "coverWidth": args.cover_width,
        "hiQuality": args.hi_quality,
        "loQuality": args.lo_quality,
    })

    # ---- 封面 ----
    cover_path = os.path.join(base, "cover.webp")
    if args.force or not os.path.exists(cover_path):
        doc = pymupdf.open(src)
        data, cw, ch = render_page(doc, 0, args.cover_width, 88)
        doc.close()
        with open(cover_path, "wb") as f:
            f.write(data)
        meta["coverHeight"] = ch

    # ---- 分页图 ----
    if args.hi:
        os.makedirs(hi_dir, exist_ok=True)
        todo = [i for i in range(n)
                if args.force or not os.path.exists(os.path.join(hi_dir, "p%03d.webp" % (i + 1)))]
        if todo:
            doc = pymupdf.open(src)
            total = 0
            for i in todo:
                data, _, _ = render_page(doc, i, args.hi_width, args.hi_quality)
                with open(os.path.join(hi_dir, "p%03d.webp" % (i + 1)), "wb") as f:
                    f.write(data)
                total += len(data)
            doc.close()
            meta["hiBytes"] = meta.get("hiBytes", 0) + total
        meta["hiReady"] = pages_done(assets, book, "hi", n)

    if not args.hi_only:
        lo_todo = [i for i in range(n)
                   if args.force or not os.path.exists(os.path.join(lo_dir, "p%03d.webp" % (i + 1)))]
        if lo_todo:
            doc = pymupdf.open(src)
            total = 0
            for i in lo_todo:
                data, _, _ = render_page(doc, i, args.lo_width, args.lo_quality)
                with open(os.path.join(lo_dir, "p%03d.webp" % (i + 1)), "wb") as f:
                    f.write(data)
                total += len(data)
            doc.close()
            meta["loBytes"] = meta.get("loBytes", 0) + total
        meta["loReady"] = pages_done(assets, book, "lo", n)
        meta.setdefault("hiReady", False)

    meta["generatedAt"] = time.strftime("%Y-%m-%d %H:%M:%S")
    return meta


def main():
    ap = argparse.ArgumentParser(description="按清单批量预渲染教材图集")
    ap.add_argument("--manifest", default="data/textbook/manifest.json")
    ap.add_argument("--assets", default=None, help="图集根目录，默认取 manifest 所在目录")
    ap.add_argument("--hi", action="store_true", help="渲染高清（默认只渲染封面+低清）")
    ap.add_argument("--hi-only", default="", help="只给这几册补高清，逗号分隔的 key")
    ap.add_argument("--only", default="", help="只处理这几册，逗号分隔的 key")
    ap.add_argument("--stage", default="", help="只处理该学段：primary/middle/high")
    ap.add_argument("--force", action="store_true", help="忽略已有产物，重新渲染")
    ap.add_argument("--check-source", action="store_true",
                    help="只体检：列出源 PDF 已更新、需要重渲染的册，不动手")
    ap.add_argument("--update", action="store_true",
                    help="增量更新：只渲染「源 PDF 已换版本」的册（自动识别）")
    ap.add_argument("--hi-width", type=int, default=1400)
    ap.add_argument("--lo-width", type=int, default=240)
    ap.add_argument("--cover-width", type=int, default=900)
    ap.add_argument("--hi-quality", type=int, default=82)
    ap.add_argument("--lo-quality", type=int, default=35)
    args = ap.parse_args()

    manifest = load_manifest(args.manifest)
    assets = args.assets or os.path.dirname(os.path.abspath(args.manifest))
    root = manifest["root"]

    only = set(x for x in args.only.split(",") if x)
    hi_only = set(x for x in args.hi_only.split(",") if x)
    if hi_only:
        only |= hi_only
        args.hi = True
    args.hi_only = bool(hi_only)

    books = manifest["books"]
    if only:
        books = [b for b in books if b["key"] in only]
    if args.stage:
        books = [b for b in books if b["stage"] == args.stage]
    books.sort(key=lambda b: (STAGE_ORDER.get(b["stage"], 9), b["grade"], b["subject"], b["volume"]))

    total_pages = sum(b.get("pages", 0) for b in books)
    print("待处理 %d 册 / 约 %d 页；阶段：%s"
          % (len(books), total_pages, "高清+低清" if args.hi else "封面+低清"), flush=True)

    t0 = time.time()
    done = skipped = failed = 0
    done_pages = 0
    stale = []            # 源 PDF 已换版本的册
    for i, b in enumerate(books, 1):
        src = os.path.join(root, b["src"].replace("/", os.sep))
        if not os.path.exists(src):
            print("  [%d/%d] 源文件缺失，跳过：%s" % (i, len(books), b["key"]), flush=True)
            failed += 1
            continue

        meta = read_meta(assets, b)
        changed = src_changed(meta, src)
        if changed and not meta.get("srcSize"):
            # 第一次补指纹：老产物没记过，源文件也不是刚动的，视为历史产物而非更新
            size, mtime = src_stamp(src)
            if size is not None and meta.get("pages") == b.get("pages"):
                meta["srcSize"], meta["srcMtime"] = size, mtime
                write_meta(assets, b, meta)
                changed = False
        if changed:
            stale.append((b["key"], b.get("subjectCN", ""), b.get("title", "")))

        need_hi = args.hi and not meta.get("hiReady")
        need_lo = not args.hi_only and not meta.get("loReady")
        if changed:
            # 源 PDF 换版本 → 旧图全部作废，低清和高清都得重来
            need_hi = args.hi or True
            need_lo = not args.hi_only
        if not args.force and not args.update and not need_hi and not need_lo:
            skipped += 1
            done_pages += b.get("pages", 0)
            continue
        if args.update and not changed and not args.force:
            skipped += 1
            done_pages += b.get("pages", 0)
            continue

        try:
            meta = render_book(assets, src, b, args, meta)
            # 记下源文件指纹：下次源 PDF 一换版本就能自动识别出要重渲
            size, mtime = src_stamp(src)
            meta["srcSize"], meta["srcMtime"] = size, mtime
            write_meta(assets, b, meta)
            done += 1
            done_pages += b.get("pages", 0)
        except Exception as e:                      # 单册失败不中断整批
            failed += 1
            print("  [%d/%d] %s 失败：%s" % (i, len(books), b["key"], e), flush=True)
            continue

        if done % 5 == 0 or i == len(books):
            el = time.time() - t0
            rate = done_pages / el if el > 0 else 0
            left = (total_pages - done_pages) / rate if rate > 0 else 0
            print("  进度 %d/%d 册 · 已渲染 %d 页 · 用时 %.0f 分 · 预计剩余 %.0f 分"
                  % (i, len(books), done_pages, el / 60, left / 60), flush=True)

    if args.check_source:
        print()
        if stale:
            print("源 PDF 已换版本、需要重新渲染的册：%d 册" % len(stale))
            for k, sub, title in stale:
                print("   %-36s %s %s" % (k, sub, title[:28]))
            print()
            print("执行下面这条即可增量更新（其余册一律跳过）：")
            print("   python tools/textbook-batch/render.py --update")
        else:
            print("体检通过：283 册源 PDF 与图集版本一致，无需重渲染。")
            print("（首次使用或图集由旧版脚本生成时，这里会列出全部册，"
                  "跑一次 --update 补齐指纹即可）")
        return

    print()
    print("完成：新渲染 %d 册，跳过 %d 册，失败 %d 册，用时 %.1f 分"
          % (done, skipped, failed, (time.time() - t0) / 60))
    if stale:
        print("其中 %d 册因源 PDF 换版本而重渲染" % len(stale))


if __name__ == "__main__":
    main()
