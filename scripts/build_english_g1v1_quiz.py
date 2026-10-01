# -*- coding: utf-8 -*-
"""人教版新起点 一年级上册 英语 —— 全 6 单元 18 课 + 复习 2 课 = 20 课交互自测题库。

输出：content/primary/pep/grade1/volume1/english/<NN-单元名>/<NN-课名>.html
教材目录：第一单元 School / 第二单元 Face / 第三单元 Animals /
         第四单元 Numbers / 第五单元 Colours / 第六单元 Fruit / 复习与检测
每单元 3 课（第1课 核心词汇 / 第2课 句型与对话 / 第3课 综合运用），
「复习与检测」两课：Revision 1（Units 1～3）、Revision 2（Units 4～6）。

用法：
  1) python scripts/build_english_g1v1_quiz.py
  2) python .workbuddy/skills/interactive-quiz-html/scripts/check_units.py scripts/build_english_g1v1_quiz.py
  3) go run ./tools/bankcheck     4) 重启 StudyBuddy 服务

出题原则：只用本单元（含前面单元）的单词与最简单句型，不超纲；
核心词汇课由词表程序化生成（固定随机种子，正确项写在首位、由引擎按题干 MD5 打乱）。
"""
import random

from _quizlib import S, S2, M, run

RNG = random.Random(20260929)


# ---- 1) 本册词表（供程序化出词汇题与拼写题复用）----
W_SCHOOL = [("pencil", "铅笔"), ("book", "书"), ("schoolbag", "书包"),
            ("ruler", "尺子"), ("have", "有"), ("I", "我")]
W_FACE = [("face", "脸"), ("eye", "眼睛"), ("ear", "耳朵"),
          ("nose", "鼻子"), ("mouth", "嘴")]
W_ANIMALS = [("dog", "狗"), ("cat", "猫"), ("bird", "鸟"),
             ("tiger", "老虎"), ("monkey", "猴子")]
W_NUMBERS = [("one", "一"), ("two", "二"), ("three", "三"), ("four", "四"),
             ("five", "五"), ("six", "六"), ("seven", "七"), ("eight", "八"),
             ("nine", "九"), ("ten", "十"), ("how many", "多少")]
W_COLOURS = [("red", "红色的"), ("yellow", "黄色的"), ("blue", "蓝色的"),
             ("green", "绿色的"), ("black", "黑色的"), ("white", "白色的")]
W_FRUIT = [("apple", "苹果"), ("banana", "香蕉"), ("orange", "橙子"),
           ("pear", "梨"), ("peach", "桃子"), ("watermelon", "西瓜")]

ALL_EN = {en.lower() for ws in (W_SCHOOL, W_FACE, W_ANIMALS, W_NUMBERS, W_COLOURS, W_FRUIT)
          for en, _ in ws}


# ---- 2) 程序化出词汇题 ----
def _others(correct, pool, n=3):
    xs = [x for x in pool if x != correct]
    RNG.shuffle(xs)
    out = []
    for x in xs:
        if x not in out:
            out.append(x)
        if len(out) >= n:
            break
    return out


def _pick(stem, ans, pool):
    """从 pool 里取 3 个干扰项（正确项仍在首位，引擎会打乱位置）。"""
    return S(stem, ans, _others(ans, pool))


def en2cn(en, cn, pool_cn):
    """英译中：「apple」的意思是（）"""
    return _pick("「%s」的意思是（　）。" % en, cn, pool_cn)


def cn2en(cn, en, pool_en):
    """中译英（听音辨义）：「铅笔」的英语是（）"""
    return _pick("「%s」的英语是（　）。" % cn, en, pool_en)


def first_letter(en, pool):
    """首字母填空：单词 book 的第一个字母是（）"""
    return _pick("单词「%s」的第一个字母是（　）。" % en, en[0].upper(), pool)


def last_letter(en, pool):
    """末字母：单词 book 的最后一个字母是（）"""
    return _pick("单词「%s」的最后一个字母是（　）。" % en, en[-1].upper(), pool)


def letter_case(up, i):
    """大小写：大写字母 P 的小写形式是（）／小写字母 p 的大写形式是（）。"""
    up = up.upper()
    low = up.lower()
    k = ord(low) - 97
    nxt = [chr((k + 1) % 26 + 97), chr((k + 2) % 26 + 97)]
    if i % 2 == 0:
        return S("大写字母「%s」的小写形式是（　）。" % up, low, [up] + nxt)
    return S("小写字母「%s」的大写形式是（　）。" % low, up, [low] + nxt)


def _mutations(w):
    """给单词造「明显写错」的形式：少字母 / 相邻字母换位 / 多字母。"""
    out = []
    for i in range(1, len(w) - 1):
        out.append(w[:i] + w[i + 1:])
    for i in range(1, len(w) - 2):
        out.append(w[:i] + w[i + 1] + w[i] + w[i + 2:])
    for i in range(1, len(w) - 1):
        out.append(w[:i] + w[i] * 2 + w[i + 1:])
    out.append(w + w[-1])
    out.append(w[0] * 2 + w[1:])
    out.append(w[:-1])
    return out


def spell(cn, en, bad):
    """拼写选择：「铅笔」的英语拼写正确的是（）。"""
    w = en.lower()
    if " " in w or len(w) < 3:
        return None
    cand = []
    for v in _mutations(w):
        if v == w or v in bad or v in cand:
            continue
        cand.append(v)
    if len(cand) < 3:
        return None
    RNG.shuffle(cand)
    return S("「%s」的英语拼写正确的是（　）。" % cn, en, cand[:3])


def vocab_multi(words, label, bad):
    """核心词汇课补 2 道多选题，保证每课至少 2 题多选。"""
    m1 = M("下面英语与中文对应正确的有（　）。",
           ["%s %s" % (e, c) for e, c in words[:4]], ["A", "B", "C", "D"])
    m2 = M("下面单词属于「%s」的有（　）。" % label,
           ["%s %s" % (e, c) for e, c in words[:3]]
           + ["%s %s" % (e, c) for e, c in bad[:1]], ["A", "B", "C"])
    return [m1, m2]


def build_vocab(words, want=20):
    """由词表生成核心词汇课：英译中 + 中译英 + 拼写 + 首字母 + 末字母 + 大小写，
    按题型轮流取题（保证题型均衡），去重后取 want 题。"""
    pool_cn = [c for _, c in words]
    pool_en = [e for e, _ in words]
    lp = sorted({en[0].upper() for en, _ in words if en[0].isalpha()})
    groups = [
        [en2cn(en, cn, pool_cn) for en, cn in words],
        [cn2en(cn, en, pool_en) for en, cn in words],
        [q for q in (spell(cn, en, ALL_EN) for en, cn in words) if q],
        [first_letter(en, lp) for en, _ in words if len(en) > 1],
        [last_letter(en, lp) for en, _ in words if len(en) > 1],
        [letter_case(ch, i) for i, ch in enumerate(lp)],
    ]
    seq = []
    for i in range(max(len(g) for g in groups)):
        for g in groups:
            if i < len(g):
                seq.append(g[i])
    out, seen = [], set()
    for q in seq:
        if q[1] in seen:
            continue
        seen.add(q[1])
        out.append(q)
    RNG.shuffle(out)
    return out[:want]


VOCAB_SCHOOL = build_vocab(W_SCHOOL) + vocab_multi(W_SCHOOL, "文具", [("cat", "猫")])
VOCAB_FACE = build_vocab(W_FACE) + vocab_multi(W_FACE, "脸上的五官", [("book", "书")])
VOCAB_ANIMALS = build_vocab(W_ANIMALS) + vocab_multi(W_ANIMALS, "动物", [("face", "脸")])
VOCAB_NUMBERS = build_vocab(W_NUMBERS) + vocab_multi(W_NUMBERS, "数字", [("dog", "狗")])
VOCAB_COLOURS = build_vocab(W_COLOURS) + vocab_multi(W_COLOURS, "颜色", [("book", "书")])
VOCAB_FRUIT = build_vocab(W_FRUIT) + vocab_multi(W_FRUIT, "水果", [("book", "书")])


# ---- 3) 题库数据 ----
# 每题：(题型, 题干, [A,B,C,D], [答案字母])；正确项写在第一项即可（引擎会打乱）。
UNITS = [

# ===================== 第一单元 School =====================
("第一单元 School", [
    ("第1课 核心词汇",
     "📣 今日广播：本单元要学会说学习用品：pencil 铅笔、book 书、schoolbag 书包、ruler 尺子；还会用 have 说「我有……」。",
     VOCAB_SCHOOL),
    ("第2课 句型与对话",
     "📣 今日广播：问东西用 What's this?，回答 It's a pencil.；说自己有什么用 I have a book.，指认用 This is my schoolbag.",
     [
         S2("「这是什么？」应说（　）。",
            ["What's this?", "What are these?", "How many is it?", "What colour it?"]),
         S2("「它是一支铅笔。」应说（　）。",
            ["It's a pencil.", "It's pencil.", "It a pencil.", "It are a pencil."]),
         S2("「我有一本书。」应说（　）。",
            ["I have a book.", "I has a book.", "I have book.", "I having a book."]),
         S2("「这是我的书包。」应说（　）。",
            ["This is my schoolbag.", "This is I schoolbag.", "This are my schoolbag.", "This my schoolbag."]),
         S2("「这是你的尺子吗？」应说（　）。",
            ["Is this your ruler?", "Is this you ruler?", "This is your ruler?", "Are this your ruler?"]),
         S2("别人问「Is this your ruler?」，你想说是，回答（　）。",
            ["Yes, it is.", "Yes, they are.", "Yes, I am.", "Yes, it does."]),
         S2("别人问「Is this your book?」，你想说不是，回答（　）。",
            ["No, it isn't.", "No, they aren't.", "No, I'm not.", "No, it is."]),
         S2("「看我的新书包！」应说（　）。",
            ["Look at my new schoolbag!", "Look my new schoolbag!", "Look at I new schoolbag!", "See at my new schoolbag!"]),
         S2("早上在学校见到老师，应该说（　）。",
            ["Good morning!", "Good night!", "Goodbye!", "Here you are."]),
         S2("放学了和同学告别，应该说（　）。",
            ["Goodbye!", "Good morning!", "Thank you!", "Sorry!"]),
         S2("「What's this?」这句话是在问（　）。",
            ["这是什么？", "这是谁？", "这是哪儿？", "这是多少个？"]),
         S2("「It's a book.」中 It's 是（　）的缩写。",
            ["it is", "it has", "I is", "it us"]),
         S2("「我有一支铅笔和一把尺子。」应说（　）。",
            ["I have a pencil and a ruler.", "I have a pencil and ruler.",
             "I have pencil and a ruler.", "I has a pencil and a ruler."]),
         S2("「这是我的书包。」中的 my 意思是（　）。",
            ["我的", "你的", "他的", "她的"]),
         S2("「Is this your pencil」这句话句末应该加（　）。",
            ["问号 ?", "句号 .", "感叹号 !", "逗号 ，"]),
         S2("「I have a schoolbag.」的意思是（　）。",
            ["我有一个书包。", "这是我的书包。", "书包在哪里？", "我喜欢书包。"]),
         S2("「This is my new ruler.」的意思是（　）。",
            ["这是我的新尺子。", "这是我的书。", "这是我的书包吗？", "我有一把新尺子。"]),
         S2("想知道别人的书是什么，你会指着书问（　）。",
            ["What's this?", "How are you?", "Good morning!", "I have a book."]),
         M("下面英语与中文对应正确的有（　）。",
           ["pencil 铅笔", "book 书", "schoolbag 书包", "ruler 尺子"], ["A", "B", "C", "D"]),
         M("关于「Yes, it is.」，说法正确的有（　）。",
           ["可以回答 Is this your book?", "意思是「是的，它是」", "是肯定回答", "回答 What's this? 时也用它"],
           ["A", "B", "C"]),
     ]),
    ("第3课 综合运用",
     "📣 今日广播：单词要会拼，句子要会写。记住句子开头的第一个字母要大写，句子末尾别忘了句号或问号。",
     [
         S2("「铅笔」的英语拼写正确的是（　）。",
            ["pencil", "pencel", "pincil", "pencial"]),
         S2("「书包」的英语拼写正确的是（　）。",
            ["schoolbag", "shoolbag", "scoolbag", "schoolbagg"]),
         S2("「尺子」的英语拼写正确的是（　）。",
            ["ruler", "ruller", "rulur", "rular"]),
         S2("「书」的英语拼写正确的是（　）。",
            ["book", "buk", "bok", "boook"]),
         S2("单词 book 的复数形式是（　）。",
            ["books", "bookes", "bookis", "book"]),
         S2("单词 pencil 的复数形式是（　）。",
            ["pencils", "penciles", "pencilies", "pencil"]),
         S2("「两支铅笔」应说（　）。",
            ["two pencils", "two pencil", "two pencilies", "a two pencils"]),
         S2("「三本书」应说（　）。",
            ["three books", "three book", "book three", "three bookes"]),
         S2("单词「I」对应的小写字母是（　）。",
            ["i", "l", "j", "r"]),
         S2("大写字母「S」的小写形式是（　）。",
            ["s", "S", "z", "c"]),
         S2("句首的字母要大写：「___ have a book.」应填（　）。",
            ["I", "i", "l", "me"]),
         S2("「Is this your book」这句话句末应加（　）。",
            ["?", ".", "!", ","]),
         S2("「This is my pencil」这句话句末应加（　）。",
            [".", "?", "!", ","]),
         S2("找出不同类的一个（　）。",
            ["apple", "book", "pencil", "ruler"]),
         S2("找出不同类的一个（　）。",
            ["cat", "book", "schoolbag", "ruler"]),
         S2("「I have a ruler.」的意思是（　）。",
            ["我有一把尺子。", "这是我的尺子。", "尺子在哪里？", "我有两支尺子。"]),
         S2("同学想知道你有几本书，你指着书说「我有一本书。」应说（　）。",
            ["I have a book.", "I have book.", "I has a book.", "This is book."]),
         S2("「It's a schoolbag.」这句话是在（　）。",
            ["告诉别人这是什么", "问别人这是什么", "和别人告别", "向别人道歉"]),
         M("下列关于字母大小写的说法正确的有（　）。",
           ["句子开头的第一个字母要大写", "单词 I（我）永远大写",
            "句末的句号写成 .", "句末的问号写成 ?"], ["A", "B", "C", "D"]),
         M("下面关于复数的说法正确的有（　）。",
           ["book 的复数是 books", "pencil 的复数是 pencils",
            "two 后面用名词复数", "a 后面用名词复数"], ["A", "B", "C"]),
     ]),
]),

# ===================== 第二单元 Face =====================
("第二单元 Face", [
    ("第1课 核心词汇",
     "📣 今日广播：本单元认识脸上的五官：face 脸、eye 眼睛、ear 耳朵、nose 鼻子、mouth 嘴；会说 This is my face.",
     VOCAB_FACE),
    ("第2课 句型与对话",
     "📣 今日广播：指认五官用 This is my nose.，让对方触摸用 Touch your ear.，看东西用 Look at my face.",
     [
         S2("「这是我的脸。」应说（　）。",
            ["This is my face.", "This is I face.", "This are my face.", "This my face."]),
         S2("「摸摸你的鼻子。」应说（　）。",
            ["Touch your nose.", "Touch you nose.", "Touch your noses.", "Touch nose your."]),
         S2("「看我的脸！」应说（　）。",
            ["Look at my face!", "Look my face!", "Look at I face!", "See my face!"]),
         S2("「这是一只眼睛。」应说（　）。",
            ["This is an eye.", "This is a eye.", "This is eye.", "This are an eye."]),
         S2("「我有一个鼻子。」应说（　）。",
            ["I have a nose.", "I has a nose.", "I have nose.", "I have a noses."]),
         S2("「我有两只耳朵。」应说（　）。",
            ["I have two ears.", "I have two ear.", "I has two ears.", "I have a ears."]),
         S2("别人问「What's this?」，你想说「这是我的嘴」，应回答（　）。",
            ["It's my mouth.", "It's my mouths.", "This is my mouth?", "It my mouth."]),
         S2("eye 的复数形式是（　）。",
            ["eyes", "eyies", "eyees", "eye"]),
         S2("ear 的复数形式是（　）。",
            ["ears", "ear", "earies", "earss"]),
         S2("「这是你的鼻子吗？」应说（　）。",
            ["Is this your nose?", "Is this you nose?", "This is your nose?", "Are this your nose?"]),
         S2("别人问「Is this your nose?」，你想说是，回答（　）。",
            ["Yes, it is.", "Yes, they are.", "Yes, I am.", "Yes, this is."]),
         S2("别人问「Is this your ear?」，你想说不是，回答（　）。",
            ["No, it isn't.", "No, they aren't.", "No, it is.", "No, I'm not."]),
         S2("「我的脸」应说