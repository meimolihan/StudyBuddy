# -*- coding: utf-8 -*-
"""由选择题库（choose）镜像生成判断题库（judge）。

规则：
  - 目录完全镜像：content/<stage>/pep/choose/...  →  content/<stage>/pep/judge/...
    同一课的 HTML 文件名与 choose 完全一致，靠上层 choose / judge 目录区分题型。
  - 判断题仅两个选项：【正确】【错误】，题型标记 "j"，答案 A=正确 / B=错误。
  - 每道题必带解析（写在题库的 e 字段，结果页与离线页面提交后可见）。
  - 题量：每课 20~40 题，全部由本课的原始选择题严格派生，不引入超纲内容。

派生方式（把选择题的「空」填上内容，变成一句可判断的陈述）：
  - 正确项填空 → 陈述正确；错误项填空 → 陈述错误；
  - 多选题把正确项全填 → 正确；把其中一项换成干扰项 → 错误；
  - 多空题（如「6 里面有（　）个 2，6 是 2 的（　）倍」）按选项中的顿号/逗号拆分逐空填入。
"""
import importlib.util
import json
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "content")
ENGINE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      ".workbuddy", "skills", "interactive-quiz-html", "scripts", "build_quiz_html.py")

# 新规范：primary / junior / senior；middle / high 为改名过渡期的旧目录名，
# 生成出来的 judge 会随 migrate_stage.py 一起被搬到 junior / senior。
STAGES = ["primary", "junior", "senior", "middle", "high"]

SUBJECT_CN = {
    "chinese": "语文", "math": "数学", "english": "英语", "morallaw": "道德与法治",
    "science": "科学", "history": "历史", "geography": "地理", "biology": "生物",
    "physics": "物理", "chemistry": "化学", "politics": "思想政治",
}

# 题干里的填空括号：（　）（）( ) 等
BLANK = re.compile(r"（[　\s]*）|\([　\s]*\)")
SPLIT = re.compile(r"[，、,;；]")


def load_engine():
    spec = importlib.util.spec_from_file_location("quiz_engine", ENGINE)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def read_bank(path):
    """从课件 HTML 里读出内嵌题库（const ALL = [...]）。

    少数旧课件的题干里带有未转义的双引号（如 `第一节课 "8":30 上课`），
    直接按 JSON 解析会失败，这里退回「按 ,o:[ / ,a:[ 定位的容错解析」。
    """
    s = open(path, encoding="utf-8").read()
    i = s.find("const ALL = [")
    if i < 0:
        return []
    i += len("const ALL = [")
    end = s.find("];", i)
    if end < 0:
        return []
    body = s[i:end]
    txt = "[" + body + "]"
    txt = re.sub(r'(\w+):', r'"\1":', txt)
    try:
        return json.loads(txt)
    except Exception:
        return read_bank_tolerant(body)


def split_js_array(raw):
    """切分 JS 字符串数组内容：元素间可能是 `", "` 或 `","`（生成器版本不同）。"""
    parts = re.split(r'",\s*"', raw.strip())
    out = []
    for p in parts:
        p = p.strip().strip('"').replace('\\"', '"')
        if p:
            out.append(p)
    return out


def read_bank_tolerant(body):
    """容错解析：题干以紧邻 `,o:[` 的那个引号为结尾，选项/答案按数组边界切分。"""
    out = []
    for m in re.finditer(r'\{t:"([smj])",q:"', body):
        typ = m.group(1)
        q_start = m.end()
        o_pos = body.find(',o:[', q_start)
        if o_pos < 0 or o_pos <= q_start:
            continue
        stem = body[q_start:o_pos - 1].replace('\\"', '"')
        a_pos = body.find('],a:[', o_pos)
        if a_pos < 0:
            continue
        opts_raw = body[o_pos + 4:a_pos]
        end_pos = body.find(']', a_pos + 5)
        if end_pos < 0:
            continue
        ans_raw = body[a_pos + 5:end_pos]
        opts = split_js_array(opts_raw)
        ans = [x.strip('"') for x in split_js_array(ans_raw)]
        if stem and opts and ans:
            out.append({"t": typ, "q": stem, "o": opts, "a": ans})
    return out


def meta_from_html(path, rel_parts):
    """取原件的 sub / broadcast，并拼出学科展示名（如「语文上册」）。"""
    s = open(path, encoding="utf-8").read()
    sub = ""
    m = re.search(r'<div class="sub">(.*?)</div>', s, re.S)
    if m:
        sub = m.group(1).strip()
    bc = ""
    m = re.search(r'<div class="tip" id="broadcast">(.*?)</div>', s, re.S)
    if m:
        bc = m.group(1).strip()

    subject, vol = "", ""
    for p in rel_parts:
        low = p.lower()
        if low in SUBJECT_CN and not subject:
            subject = low
        if low.startswith("volume"):
            vol = low
        if low == "review":
            vol = "review"
    label = SUBJECT_CN.get(subject, subject)
    if vol == "review":
        label += "高考复习"
    elif vol.endswith("2"):
        label += "下册"
    else:
        label += "上册"
    return sub, bc, label


def fill(stem, texts):
    """把 texts 依次填进题干的空中；无法匹配时返回 None。"""
    blanks = list(BLANK.finditer(stem))
    if not blanks or not texts:
        return None
    if len(texts) == len(blanks):
        out, last = [], 0
        for m, t in zip(blanks, texts):
            out.append(stem[last:m.start()])
            out.append(t.strip().rstrip("。"))
            last = m.end()
        out.append(stem[last:])
        return "".join(out).strip()
    if len(blanks) == 1:
        return BLANK.sub("、".join(x.strip().rstrip("。") for x in texts), stem, count=1).strip()
    return None


def split_opt(text, n):
    """多空题：把选项按顿号/逗号拆成 n 段；拆不出就返回 None。"""
    if n <= 1:
        return [text]
    parts = [p.strip() for p in SPLIT.split(text) if p.strip()]
    if len(parts) == n:
        return parts
    return None


def derive(bank):
    """把选择题派生为判断题候选：[(陈述, 是否正确, 解析), ...]"""
    trues, falses = [], []
    for q in bank:
        stem = q.get("q", "")
        opts = q.get("o", [])
        ans = q.get("a", [])
        if not stem or len(opts) < 2 or not ans:
            continue
        idxs = ["ABCD".index(x) for x in ans if x in "ABCD"]
        if not idxs or max(idxs) >= len(opts):
            continue
        correct = [opts[i] for i in idxs]
        wrong = [opts[i] for i in range(len(opts)) if i not in idxs]
        nblank = len(BLANK.findall(stem))
        if nblank == 0 or not wrong:
            continue

        # 正确陈述：把正确项填进空里
        if nblank > 1:
            pieces = split_opt(correct[0], nblank)
            if pieces is None:
                pieces = split_opt(wrong[0], nblank)  # 先试能否拆分，保证多空题可用
            if pieces is None:
                continue
            t_stmt = fill(stem, pieces)
            w_pieces = split_opt(wrong[0], nblank)
            f_stmt = fill(stem, w_pieces) if w_pieces else None
        else:
            if q.get("t") == "m":
                t_stmt = fill(stem, correct)
                mix = correct[:-1] + [wrong[0]] if len(correct) >= 2 else [wrong[0]]
                f_stmt = fill(stem, mix)
            else:
                t_stmt = fill(stem, [correct[0]])
                f_stmt = fill(stem, [wrong[0]])
        if not t_stmt:
            continue
        ok_txt = "、".join(x.strip().rstrip("。") for x in correct)
        trues.append((t_stmt, True,
                      "解析：本句说法正确。教材对应内容就是「%s」，与本课所学一致。" % ok_txt))
        if f_stmt:
            bad = wrong[0].strip().rstrip("。")
            falses.append((f_stmt, False,
                           "解析：本句说法错误。正确内容应为「%s」，而不是「%s」。" % (ok_txt, bad)))
    return trues, falses


def pick(trues, falses, want_min=20, want_max=40):
    """交替取正确/错误陈述，凑够 20~40 题且大致对错各半。"""
    out, seen = [], set()
    i = j = 0
    turn = 0
    while len(out) < want_max and (i < len(trues) or j < len(falses)):
        pool = trues if turn % 2 == 0 else falses
        k = i if turn % 2 == 0 else j
        if k < len(pool):
            item = pool[k]
            if item[0] not in seen:
                seen.add(item[0])
                out.append(item)
            if turn % 2 == 0:
                i += 1
            else:
                j += 1
        turn += 1
        if turn > 4 * (len(trues) + len(falses) + 4):
            break
    # 题量不足时把剩下的补齐（优先补够 20 题）
    if len(out) < want_min:
        for item in list(trues) + list(falses):
            if len(out) >= want_min:
                break
            if item[0] not in seen:
                seen.add(item[0])
                out.append(item)
    return out[:want_max]


def main():
    engine = load_engine()
    total_files = total_q = 0
    skipped = []
    for stage in STAGES:
        src_root = os.path.join(ROOT, stage, "pep", "choose")
        if not os.path.isdir(src_root):
            print("跳过（不存在）：%s" % src_root)
            continue
        dst_root = os.path.join(ROOT, stage, "pep", "judge")
        for dirpath, _dirs, files in os.walk(src_root):
            for fn in sorted(files):
                if not fn.lower().endswith(".html"):
                    continue
                src = os.path.join(dirpath, fn)
                rel = os.path.relpath(src, src_root)
                dst = os.path.join(dst_root, rel)
                bank = read_bank(src)
                if not bank:
                    skipped.append(rel + "（无法解析题库）")
                    continue
                trues, falses = derive(bank)
                items = pick(trues, falses)
                if len(items) < 20:
                    skipped.append("%s（仅派生出 %d 题）" % (rel, len(items)))
                    continue
                sub, bc, subject = meta_from_html(src, rel.split(os.sep))
                qs = []
                for stmt, ok, exp in items:
                    qs.append(("j", stmt, ["正确", "错误"], ["A"] if ok else ["B"], exp))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                sub_txt = sub or rel.replace(os.sep, " · ")
                engine.build(sub_txt + " · 判断题", qs,
                             bc or "📣 今日广播：判断对错要抓关键词，说法与教材一致才判正确。",
                             dst, subject)
                total_files += 1
                total_q += len(qs)
    print("完成：生成判断题课件 %d 个，共 %d 题；跳过 %d 个" % (total_files, total_q, len(skipped)))
    for s in skipped[:15]:
        print("   跳过：", s)
    if len(skipped) > 15:
        print("   …… 其余 %d 个" % (len(skipped) - 15))


if __name__ == "__main__":
    sys.exit(main())
