# -*- coding: utf-8 -*-
"""概念/知识点驱动的题库生成器（文科科目通用）。

给「一课一份数据表」的科目用：每课给 11~12 个 (术语, 一句话释义) 条目，
自动生成 22~24 道题（术语→释义、释义→术语 两种问法），选项由同课其他
条目充当干扰项。正确项放首位，引擎会按题干 MD5 自动打乱选项位置。

用法：
    from _concepts import concept_lessons
    qs = concept_lessons([
        ("作者", "朱自清，现代散文家，代表作《背影》"),
        ("体裁", "写景抒情散文"),
        ...
    ])
"""
import random

from _quizlib import S2


def _others(i, entries, rnd, k=3, pick=1):
    """取同课其他条目的第 pick 列作干扰项。"""
    idxs = [j for j in range(len(entries)) if j != i]
    rnd.shuffle(idxs)
    return [entries[j][pick] for j in idxs[:k]]


def concept_lessons(entries, want=24, seed=20261001, both_dir=True, suffix=""):
    """从 [(术语, 释义), ...] 生成题目列表。

    正向：「术语」的含义是（　）。→ 释义
    反向：「释义」指的是（　）。→ 术语
    suffix 可给题干加课内语境前缀，避免跨课撞题干（题干含术语/释义本身
    一般不会撞，除非两课用了同一条目——此时给两课传不同 suffix）。
    """
    assert len(entries) >= 10, "每课至少 10 个概念条目"
    rnd = random.Random(seed)
    qs = []
    made = 0

    order = list(range(len(entries)))
    rnd.shuffle(order)
    for i in order:
        term, defn = entries[i][0], entries[i][1]
        ws = _others(i, entries, rnd, pick=1)
        if defn not in ws:
            qs.append(S2("%s“%s”的含义是（　）。" % (suffix, term), [defn] + ws))
            made += 1

    if both_dir:
        order2 = list(range(len(entries)))
        rnd.shuffle(order2)
        for i in order2:
            if made >= want:
                break
            term, defn = entries[i][0], entries[i][1]
            ts = _others(i, entries, rnd, pick=0)
            if term not in ts:
                qs.append(S2("%s“%s”指的是（　）。" % (suffix, defn), [term] + ts))
                made += 1
    return qs
