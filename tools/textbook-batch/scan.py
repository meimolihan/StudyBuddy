"""批量扫描教材资源目录，生成教材清单 manifest.json。

用途
----
把 ``D:\\ChinaTextbook`` 下的人教版 / 统编版教科书逐条登记成可被服务读取的清单，
避免在 Go 运行时全盘扫描（1905 个 PDF，遍历 + 打开页数要数秒，会拖慢启动）。

过滤规则
--------
1. 只保留学段为 小学 / 初中 / 高中 的目录（跳过「大学」「学数学最重要的刷题在这里」
   与「小学（五•四学制）」「初中（五•四学制）」这两套学制不同的目录）。
2. 只保留路径中出现「人教 / 统编 / 部编」的版本目录，其余版本（苏教、沪教、
   青岛版、北师大……）一律不登记。
3. 版本目录名清洗：去掉出版社后缀与「（主编：xxx）」，只留版本名本身。

输出
----
``<out>/manifest.json``：``{"generatedAt", "root", "stageNames", "books": [...]}``
每条 book 含 key / stage / grade / bankGrade / volume / subject / subjectCN /
version / title / subTitle / src / pages。

key 规则（全小写 ASCII，满足 Go 侧 ``^[a-z0-9][a-z0-9-]*$`` 白名单）
------------------------------------------------------------
``<stage>-<subject>-g<grade>-v<volume>``，册别不分上下的（体育与健康全一册、
高中必修/选择性必修等）用 ``-v0``；同一 key 出现多份时按「版本名最简者优先 +
文件名短者优先」择一，其余记入 duplicates 供人工复核。

用法
----
    python tools/textbook-batch/scan.py --root "D:/ChinaTextbook" --out data/textbook
"""

import argparse
import collections
import datetime
import hashlib
import json
import os
import re
import sys

# ---------------------------------------------------------------------------
# 过滤与映射表
# ---------------------------------------------------------------------------

# 只处理这三个学段目录；「（五•四学制）」是另一套学制，不并入。
STAGE_DIRS = {"小学": "primary", "初中": "middle", "高中": "high"}

# 版本目录命中任一关键字即视为官方版（人民教育出版社 / 教育部统编）。
VERSION_KEEP = ("人教", "统编", "部编")

# 学科中文名 → 题库学科键。题库（content/<stage>/pep/**）用的就是这些英文键，
# 主页「官方教材」卡片要按当前学生的学科过滤，两边必须对得上。
SUBJECT_KEYS = {
    "语文": "chinese",
    "数学": "math",
    "英语": "english",
    "道德与法治": "morallaw",
    "科学": "science",
    "物理": "physics",
    "化学": "chemistry",
    "生物学": "biology",
    "生物": "biology",
    "地理": "geography",
    "历史": "history",
    # 地理图册 / 人文地理是独立教材，不能和「地理」共用一个键，
    # 否则同年级同册别会被当成同一本书而互相顶掉。
    "地理图册": "atlas",
    "人文地理": "human-geo",
    "思想政治": "politics",
    "政治": "politics",
    "音乐": "music",
    "美术": "art",
    "艺术": "art",
    "体育与健康": "pe",
    "信息技术": "it",
    "通用技术": "technology",
    "俄语": "russian",
    "日语": "japanese",
    "书法练习指导": "calligraphy",
    "语文·书法练习指导": "calligraphy",
}

# 小学 1~6 年级；初中七/八/九年级在题库里是 grade1~3，故另存 bankGrade。
CN_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
          "七": 7, "八": 8, "九": 9, "十": 10, "十一": 11, "十二": 12}

# 核心学科：用于「无遗漏」校验——这些格子缺了才算真问题。
CORE_SUBJECTS = ("chinese", "math", "english")


def clean_version(name):
    """「人教版（A版）（主编：章建跃&李增沪）-人民教育出版社」→「人教版（A版）」。"""
    v = re.split(r"[-–—]", name)[0]          # 砍掉出版社后缀
    v = re.sub(r"（[^）]*）|\([^)]*\)", "", v)  # 砍掉（主编：xxx）等括注
    return v.strip() or name.strip()


def subject_key(cn):
    """学科中文名 → ASCII 键；未登记的学科用名称哈希兜底，保证键稳定唯一。"""
    cn = cn.strip()
    if cn in SUBJECT_KEYS:
        return SUBJECT_KEYS[cn]
    h = hashlib.sha1(cn.encode("utf-8")).hexdigest()[:8]
    return "sub-" + h


def num_of(s):
    """「三」→3、「3」→3；认不出返回 0。"""
    if s.isdigit():
        return int(s)
    return CN_NUM.get(s, 0)


def parse_grade_volume(stage, filename, path_segs):
    """解析 (grade, bankGrade, volume, subTitle)。

    grade     真实年级：小学 1~6、初中 7~9、高中 10~12
    bankGrade 题库年级：小学同 grade；初中七/八/九 → 1/2/3；高中高一/高二/高三 → 1/2/3
    volume    册别：上册 1、下册 2；全一册 / 必修 / 选择性必修等不分上下的记 0
    subTitle  展示用的副标题

    年级有两个来源：文件名（「语文七年级上册」）与目录名
    （``初中/人文地理/统编版-人民教育出版社/七年级/…人文地理上册.pdf`` 只有目录带年级），
    两处都要认，否则这批书会被解析成「年级未知」而互相顶掉。
    """
    base = os.path.splitext(filename)[0]

    # ---- 年级：先文件名，再目录 ----
    # 文件名里「（一年级起点）」「（PEP）」「（精通）」这类标记本身含「一年级」，
    # 直接正则会把它当成年级，必须先剥掉；剥完取最后一个「X年级」（紧挨上/下册那个）。
    grade = 0
    cleaned = re.sub(r"（[^）]*(?:起点|PEP|精通)[^）]*）", "", base)
    found = re.findall(r"([一二三四五六七八九十]+)年级", cleaned)
    if found:
        grade = num_of(found[-1])
    if grade == 0:
        for seg in path_segs:
            m = re.fullmatch(r"([一二三四五六七八九十]+)年级", seg)
            if m:
                grade = num_of(m.group(1))
                break

    # ---- 册别 ----
    volume, sub = 0, ""
    m = re.search(r"([一二三四五六七八九十\d]+)至([一二三四五六七八九十\d]+)年级", base)
    if m:
        if grade == 0:
            grade = num_of(m.group(1))     # 「1至2年级」→ 起始年级 1
        sub = "%s至%s年级 全一册" % (m.group(1), m.group(2))
    elif "上册" in base:
        volume, sub = 1, "上册"
    elif "下册" in base:
        volume, sub = 2, "下册"
    elif "全一册" in base:
        sub = "全一册"
    else:
        # 高中册名有五种写法：「必修 第一册」「必修1 分子与细胞」「必修 美术鉴赏」
        # 「选择性必修 第二册」「选择性必修3 雕塑」，册号可中文可阿拉伯、可有可无。
        m = re.search(r"选择性必修\s*第?\s*([一二三四五六七八九十\d]+)", base)
        if m:
            n = num_of(m.group(1))
            sub = "选择性必修 %s" % m.group(1)
            grade, volume = (11 if n <= 2 else 12), 0
        else:
            m = re.search(r"必修\s*第?\s*([一二三四五六七八九十\d]+)", base)
            if m:
                n = num_of(m.group(1))
                sub = "必修 %s" % m.group(1)
                # 必修 1~2 高一，3~4 高二，5+ 高三
                grade, volume = (10 if n <= 2 else (11 if n <= 4 else 12)), 0
            elif "必修" in base:
                sub = "必修"          # 没写册号（如「美术必修 美术鉴赏」），年级待定

    # ---- 题库年级 ----
    bank = grade
    if stage == "middle":
        bank = grade - 6                      # 七/八/九 → 1/2/3
    elif stage == "high":
        # 年级没解析出来时保持 0（未定年级），不能默认成高三，否则会把一堆
        # 没写册号的书（如「美术必修 美术鉴赏」）错分到高三。
        bank = {10: 1, 11: 2, 12: 3}.get(grade, 0)

    if sub in ("上册", "下册"):
        cn = {1: "一", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六",
              7: "七", 8: "八", 9: "九", 10: "十", 11: "十一", 12: "十二"}.get(grade, "")
        if cn:
            sub = "%s年级 %s" % (cn, sub)
    return grade, bank, volume, sub


def page_count(path):
    """读 PDF 页数；打不开就返回 0，由渲染阶段补齐。"""
    try:
        import pymupdf
    except ImportError:
        return 0
    try:
        d = pymupdf.open(path)
        n = d.page_count
        d.close()
        return n
    except Exception:
        return 0


def scan(root, out_dir, with_pages=True):
    books = []
    skipped_stage = collections.Counter()
    skipped_ver = collections.Counter()

    for dirpath, dirnames, filenames in os.walk(root):
        pdfs = [f for f in filenames if f.lower().endswith(".pdf")]
        if not pdfs:
            continue
        rel = os.path.relpath(dirpath, root).split(os.sep)
        stage = STAGE_DIRS.get(rel[0])
        if stage is None:
            skipped_stage[rel[0]] += len(pdfs)
            continue

        # 版本目录：路径里任意一段命中官方版关键字即算；学科目录 = 第一段非版本段。
        ver_seg = next((s for s in rel[1:] if any(k in s for k in VERSION_KEEP)), None)
        if ver_seg is None:
            skipped_ver[rel[1]] += len(pdfs)
            continue
        subject_cn = rel[1]
        version = clean_version(ver_seg)

        for f in pdfs:
            g, bank, vol, sub = parse_grade_volume(stage, f, rel[2:])
            src_rel = "/".join(rel + [f])
            books.append({
                "stage": stage,
                "stageCN": rel[0],
                "grade": g,
                "bankGrade": bank,
                "volume": vol,
                "subject": subject_key(subject_cn),
                "subjectCN": subject_cn,
                "version": version,
                "title": os.path.splitext(f)[0],
                "subTitle": sub,
                "src": src_rel,
                "abs": os.path.join(dirpath, f),
            })

    # ---- 去重：同一 (学段, 学科, 年级, 册别) 下可能有多套不同教材
    # （如音乐的五线谱版与简谱版、地理与地理图册）。它们都是真实存在的教材，
    # 不能择一丢掉，只能给 key 加稳定后缀区分开，键保持唯一。
    def rank(b):
        # 版本目录名越短越「标准」（如「统编版」优于「统编版-人民教育出版社」）
        return (len(b["version"]), len(b["title"]), b["src"])

    by_key = collections.defaultdict(list)
    for b in books:
        key = "%s-%s-g%d-v%d" % (b["stage"], b["subject"], b["grade"], b["volume"])
        b["key"] = key
        by_key[key].append(b)

    final, variants = [], []
    for key, group in by_key.items():
        group.sort(key=rank)
        for i, b in enumerate(group):
            if i:                       # 第 2 册起加 -2 / -3 后缀
                b["key"] = "%s-%d" % (key, i + 1)
                variants.append({"key": b["key"], "base": key, "src": b["src"]})
            final.append(b)

    final.sort(key=lambda b: (b["stage"], b["grade"], b["subject"], b["volume"], b["title"]))

    if with_pages:
        for i, b in enumerate(final, 1):
            b["pages"] = page_count(b["abs"])
            if i % 40 == 0:
                print("  读取页数 %d/%d" % (i, len(final)), flush=True)

    for b in final:
        b.pop("abs", None)
        b.pop("stageCN", None)

    # ---- 无遗漏校验：核心学科 × 年级 的格子 ----
    cells = collections.defaultdict(set)
    for b in final:
        cells[(b["stage"], b["grade"], b["subject"])].add(b["volume"])
    missing = []
    ranges = {"primary": range(1, 7), "middle": range(7, 10)}
    for stage, grades in ranges.items():
        for g in grades:
            for subj in CORE_SUBJECTS:
                vols = cells.get((stage, g, subj), set())
                if not vols:
                    missing.append("%s/%d年级/%s 完全缺失" % (stage, g, subj))
                elif not ({1, 2} & vols) and 0 not in vols:
                    # volume 0 = 全一册，一册覆盖全年，算齐备
                    missing.append("%s/%d年级/%s 缺上/下册（现有 %s）"
                                   % (stage, g, subj, sorted(vols)))

    manifest = {
        "generatedAt": datetime.datetime.now().isoformat(timespec="seconds"),
        "root": os.path.abspath(root),
        "stageNames": {"primary": "小学", "middle": "初中", "high": "高中"},
        "books": final,
    }
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)

    return manifest, variants, missing, skipped_stage, skipped_ver


def main():
    ap = argparse.ArgumentParser(description="扫描教材目录，生成 manifest.json")
    ap.add_argument("--root", default="D:/ChinaTextbook", help="教材资源根目录")
    ap.add_argument("--out", default="data/textbook", help="图集根目录（manifest 输出位置）")
    ap.add_argument("--no-pages", action="store_true", help="跳过页数读取（更快）")
    args = ap.parse_args()

    if not os.path.isdir(args.root):
        sys.exit("教材根目录不存在：%s" % args.root)

    print("扫描 %s ..." % args.root, flush=True)
    manifest, variants, missing, skip_stage, skip_ver = scan(args.root, args.out, not args.no_pages)
    books = manifest["books"]

    print()
    print("登记教材 %d 册" % len(books))
    c = collections.Counter((b["stage"], b["subjectCN"]) for b in books)
    for stage, cn in manifest["stageNames"].items():
        subs = sorted({k[1] for k in c if k[0] == stage})
        print("  [%s] %3d 册 / %2d 学科：%s"
              % (cn, sum(v for k, v in c.items() if k[0] == stage), len(subs), "、".join(subs)))
    print()
    print("跳过：非目标学段 %d 册、非官方版本 %d 册" % (sum(skip_stage.values()), sum(skip_ver.values())))
    print("同年级同册别的多版本教材 %d 册（已用 -2/-3 后缀区分，键唯一）" % len(variants))
    for v in variants[:8]:
        print("   %-34s %s" % (v["key"], v["src"]))
    print()
    if missing:
        print("核心学科缺口 %d 处：" % len(missing))
        for m in missing:
            print("   ", m)
    else:
        print("核心学科（语文/数学/英语）小学与初中全年级齐备")

    nopages = sum(1 for b in books if not b.get("pages"))
    if nopages:
        print()
        print("注意：%d 册未读到页数（PDF 打不开或未装 pymupdf），渲染阶段会补" % nopages)
    print()
    print("清单已写入 %s" % os.path.join(args.out, "manifest.json"))


if __name__ == "__main__":
    main()
