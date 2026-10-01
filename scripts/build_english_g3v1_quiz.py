# -*- coding: utf-8 -*-
"""人教版 PEP 三年级上册（2024 秋版）英语 —— 全 6 单元 + Revision 交互自测生成器。

输出：content/primary/pep/grade3/volume1/english/<NN-单元名>/<NN-课名>.html
每个单元拆 3 课（核心词汇 / 句型与对话 / 综合运用），Revision 1 课。
"""
import os
import random
import sys
from pathlib import Path


def _find_project_root(start):
    for p in [start] + list(start.parents):
        if (p / "go.mod").is_file():
            return p
    return start


def _find_engine_dir(root):
    for cand in (Path(__file__).resolve().parent,
                 root / ".workbuddy" / "skills" / "interactive-quiz-html" / "scripts"):
        if (cand / "build_quiz_html.py").is_file():
            return cand
    raise SystemExit("找不到引擎 build_quiz_html.py")


PROJECT_ROOT = _find_project_root(Path(__file__).resolve().parent)
sys.path.insert(0, str(_find_engine_dir(PROJECT_ROOT)))
from build_quiz_html import build as engine_build  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _quizlib import S, S2, M, run  # noqa: E402

RNG = random.Random(20260930)


def _others(correct, pool, n=3):
    xs = [x for x in pool if x != correct]
    RNG.shuffle(xs)
    return xs[:n]


def en2cn(en, cn, pool_cn):
    return ("s", "「%s」的意思是（　）。" % en, [cn] + _others(cn, pool_cn), ["A"])


def cn2en(cn, en, pool_en):
    return ("s", "「%s」用英语说是（　）。" % cn, [en] + _others(en, pool_en), ["A"])


def first_letter(en, pool_letters):
    a = en[0].upper()
    return ("s", "单词「%s」的第一个字母是（　）。" % en, [a] + _others(a, pool_letters), ["A"])


def letter_case(letter):
    up, low = letter.upper(), letter.lower()
    return ("s", "大写字母「%s」的小写形式是（　）。" % up,
            [low, up, chr((ord(low) - 97 + 1) % 26 + 97), chr((ord(low) - 97 + 2) % 26 + 97)], ["A"])


def build_vocab(words, want=22):
    """词汇课：英译中 + 中译英 + 首字母 + 大小写。"""
    pool_cn = [c for _, c in words]
    pool_en = [e for e, _ in words]
    letters = ["A", "B", "C", "D", "E", "G", "H", "K", "L", "M", "N", "P", "R", "S", "T", "W"]
    qs = []
    for en, cn in words:
        qs.append(en2cn(en, cn, pool_cn))
        qs.append(cn2en(cn, en, pool_en))
        if len(en) >= 3:
            qs.append(first_letter(en, letters))
    for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        qs.append(letter_case(ch))
    seen, out = set(), []
    for q in qs:
        if q[1] in seen:
            continue
        seen.add(q[1])
        out.append(q)
    RNG.shuffle(out)
    return out[:want]


def Q(stem, ans, *ws):
    return S(stem, ans, [str(w) for w in ws])


UNITS = [
    ("第一单元 Making friends 交朋友", [
        ("第1课 核心词汇", "📣 Today's words: hello / I / am / name / friend / goodbye。见到新朋友，大声说 Hello 吧！", build_vocab([
            ("hello", "你好"), ("I", "我"), ("am", "是"), ("name", "名字"),
            ("friend", "朋友"), ("goodbye", "再见"), ("hi", "嗨"), ("you", "你；你们"),
            ("my", "我的"), ("your", "你的"),
        ])),
        ("第2课 句型与对话", "📣 Sentences: Hello! I'm … / What's your name? / Nice to meet you! 学会用英语介绍自己。", [
            Q("「你好！」用英语说是（　）。", "Hello!", "Goodbye!", "Thank you!", "Sorry!"),
            Q("介绍自己的名字，应该说（　）。", "I'm Sarah.", "You are Sarah.", "This is Sarah.", "Bye, Sarah."),
            Q("询问对方的名字，应该说（　）。", "What's your name?", "What's this?", "How are you?", "Who are you?"),
            Q("「My name is Bill.」的意思是（　）。", "我的名字叫比尔。", "你是比尔吗？", "他是比尔。", "再见，比尔。"),
            Q("初次见面表示很高兴，说（　）。", "Nice to meet you!", "Good night!", "See you!", "Excuse me!"),
            Q("回答 Nice to meet you! 应该说（　）。", "Nice to meet you, too.", "I'm fine.", "No, thanks.", "You're wrong."),
            Q("和朋友告别时说（　）。", "Goodbye!", "Hello!", "Nice to meet you!", "What's your name?"),
            Q("「I am a student.」的意思是（　）。", "我是一名学生。", "你是一名学生。", "他是老师。", "我们是朋友。"),
            Q("早上见到老师问好，说（　）。", "Good morning!", "Good night!", "Goodbye!", "Good evening!"),
            Q("「This is my friend.」的意思是（　）。", "这是我的朋友。", "那是你的朋友。", "我在找朋友。", "朋友再见。"),
            M("见面问候语有（　）。", ["Hello!", "Hi!", "Good morning!", "Goodbye!"], ["A", "B", "C"]),
            M("表示礼貌的用语有（　）。", ["Thank you.", "Sorry.", "Please.", "Shut up!"], ["A", "B", "C"]),
            Q("别人帮助了你，应该说（　）。", "Thank you!", "You're welcome.", "I'm sorry.", "Goodbye!"),
            Q("「Nice to meet you!」中文意思是（　）。", "很高兴见到你！", "你好吗？", "再见！", "你叫什么？"),
            Q("下课时和老师说（　）。", "Goodbye, Miss Li.", "Hello, Miss Li.", "What's your name?", "I'm fine."),
            Q("你想知道新同学的名字，应该问（　）。", "What's your name?", "How old are you?", "Where is it?", "What colour?"),
            Q("自我介绍时先说（　）。", "Hello! I'm …", "Goodbye!", "Sorry!", "Thanks!"),
            M("做自我介绍时可以介绍自己的（　）。", ["名字", "年龄", "喜欢的事物", "以上全都不行"], ["A", "B", "C"]),
            Q("听到「Hi!」可以回应（　）。", "Hi!", "Bye!", "Sorry!", "No!"),
            Q("「What's your name?」的正确回答是（　）。", "My name is Mike.", "I'm nine.", "It's a cat.", "Yes, it is."),
            Q("和朋友相处要（　）。", "友好、互相帮助", "打架", "骂人", "不理人"),
        ]),
        ("第3课 综合运用", "📣 综合练习：字母 Aa~Dd 的认读与书写、本单元单词的听音辨义。练一练，基础更扎实！", [
            Q("大写字母「A」的小写是（　）。", "a", "e", "d", "c"),
            Q("字母表的前三个字母是（　）。", "A B C", "A B D", "A C D", "B C D"),
            Q("「bc」的大写是（　）。", "BC", "BCD", "ABC", "bc"),
            Q("下列大小写配对正确的是（　）。", "D-d", "B-p", "A-e", "C-o"),
            Q("单词「hello」的第一个字母是（　）。", "h", "H 后面——l", "e", "o"),
            Q("单词「friend」里有几个字母？（　）", "6", "5", "7", "4"),
            Q("按字母表顺序，B 的后面是（　）。", "C", "D", "A", "E"),
            Q("「am」是「我是」中的（　）。", "是（动词）", "我", "名字", "朋友"),
            M("字母 Dd 的朋友（含 Dd 的单词）有（　）。", ["dog", "dad", "goodbye", "apple"], ["A", "B", "C"]),
            M("本单元学过的单词有（　）。", ["hello", "name", "friend", "elephant"], ["A", "B", "C"]),
            Q("「I am」的缩写形式是（　）。", "I'm", "Im", "I am not", "Am I"),
            Q("What is 的缩写是（　）。", "What's", "Whats", "What is not", "Is what"),
            Q("书写字母 A 时占（　）。", "上两格（中格和上格）", "只占上格", "下两格", "四格"),
            Q("名字 Sarah 是一个（　）。", "人名（首字母大写）", "动物", "颜色", "数字"),
            Q("英语句子的第一个单词首字母要（　）。", "大写", "小写", "划线", "圈起来"),
            Q("「hello」和「hi」的意思（　）。", "基本相同（都是你好）", "完全不同", "hello 是再见", "hi 是谢谢"),
            Q("字母表中共有（　）个字母。", "26", "24", "25", "27"),
            Q("「goodbye」的缩略说法是（　）。", "Bye!", "Hi!", "Hey!", "Oh!"),
            Q("听音辨义：「这是我的朋友。」对应的句子是（　）。", "This is my friend.", "This is my bag.", "I am a boy.", "Good night."),
            Q("学英语要先学会（　）。", "大胆开口说", "默写单词全部", "只听不说", "只看书"),
            S2("单元小结：本单元我们学会了（　）。", ["问候与自我介绍", "数数到 100", "唱歌跳舞", "写作文"]),
        ]),
    ]),
    ("第二单元 Different families 不同的家庭", [
        ("第1课 核心词汇", "📣 Today's words: family / father / mother / brother / sister / grandmother。家家有本温暖的字典！", build_vocab([
            ("family", "家庭"), ("father", "爸爸"), ("mother", "妈妈"), ("brother", "哥哥；弟弟"),
            ("sister", "姐姐；妹妹"), ("grandmother", "奶奶；外婆"), ("grandfather", "爷爷；外公"),
            ("who", "谁"), ("this", "这；这个"), ("he", "他"), ("she", "她"),
        ])),
        ("第2课 句型与对话", "📣 Sentences: Who lives with you? / This is my father. / How are families different? 介绍你的家人吧！", [
            Q("「This is my mother.」的意思是（　）。", "这是我的妈妈。", "这是我的爸爸。", "那是我的家。", "我有妈妈。"),
            Q("询问「谁和你住在一起？」应该说（　）。", "Who lives with you?", "Who are you?", "What is this?", "How are you?"),
            Q("爸爸的英语是（　）。", "father", "mother", "brother", "sister"),
            Q("「She is my sister.」中 she 指（　）。", "她", "他", "它", "你"),
            Q("介绍爷爷应该说（　）。", "This is my grandfather.", "This is my grandmother.", "This is my sister.", "This is my teacher."),
            Q("he 和 she 的区别是（　）。", "he 指男性，she 指女性", "一样", "he 指女性", "she 指动物"),
            Q("「I love my family.」的意思是（　）。", "我爱我的家。", "我的家很大。", "家人爱我。", "家在哪里？"),
            Q("你的哥哥用英语说是（　）。", "my brother", "my sister", "my mother", "my father"),
            Q("询问照片上的人是谁，说（　）。", "Who's this?", "What's this?", "Where is it?", "How many?"),
            S2("家庭成员一般包括（　）。", ["爸爸、妈妈、孩子", "只有我一个人", "只有宠物", "同学"]),
            M("Family members 有（　）。", ["father", "mother", "grandmother", "classmate"], ["A", "B", "C"]),
            M("介绍家人时可以说（　）。", ["This is my father.", "She is my sister.", "He is my brother.", "This is my school."], ["A", "B", "C"]),
            Q("「parents」指的是（　）。", "父母", "祖父母", "兄弟姐妹", "朋友"),
            Q("grandparents 指的是（　）。", "祖父母（爷爷奶奶外公外婆）", "父母", "舅舅", "老师"),
            Q("你和哥哥是（　）。", "brothers/siblings（兄弟）", "parents", "cousins", "strangers"),
            Q("向朋友介绍全家福，先说（　）。", "This is my family photo.", "Goodbye.", "What's this?", "I'm hungry."),
            Q("「How are families different?」问的是（　）。", "家庭有什么不同", "家在哪里", "家庭多大", "家庭多远"),
            Q("对不同家庭的尊重表现为（　）。", "不嘲笑别人的家庭", "比较谁家有钱", "取笑同学", "不理睬"),
            Q("回答 Who lives with you? 可以说（　）。", "My father, mother and brother.", "I'm nine.", "It's a dog.", "Red."),
            Q("家人之间要（　）。", "互相爱护、互相帮助", "吵架", "冷战", "攀比"),
            Q("「My sister is cute.」的意思是（　）。", "我的妹妹很可爱。", "我的妹妹很凶。", "我有妹妹。", "妹妹在唱歌。"),
        ]),
        ("第3课 综合运用", "📣 综合练习：字母 Ee~Hh、he/she 的用法、单词听辨。继续加油！", [
            Q("大写字母「E」的小写是（　）。", "e", "f", "a", "c"),
            Q("按字母表顺序，F 的后面是（　）。", "G", "E", "H", "D"),
            Q("「she」指的是（　）。", "她", "他", "你", "它"),
            Q("用 he 还是 she：My mother —（　）is kind.（　）", "she", "he", "it", "you"),
            Q("用 he 还是 she：My father —（　）is tall.（　）", "he", "she", "it", "we"),
            Q("「family」的第一个字母是（　）。", "f", "F 后面——g", "m", "y"),
            Q("grandmother 里含有（　）。", "mother", "father", "brother", "teacher"),
            Q("下列单词中指男性的是（　）。", "father", "mother", "sister", "grandmother"),
            M("以字母 Hh 开头的单词有（　）。", ["hello", "hi", "have", "egg"], ["A", "B", "C"]),
            M("本单元单词有（　）。", ["family", "mother", "grandfather", "apple"], ["A", "B", "C"]),
            Q("「brother」和「sister」的区别是（　）。", "brother 男性，sister 女性", "没区别", "sister 年长", "brother 年幼"),
            Q("书写字母 Gg 时注意（　）。", "大写 G 有横，小写 g 下格带圈", "一样写", "不用规范", "只写一半"),
            Q("介绍家人时 face 表情应该（　）。", "微笑", "生气", "大哭", "瞪眼"),
            Q("「grand」在 grandmother 里的意思是（　）。", "隔一代的（祖辈）", "大的", "好的", "奶奶专有"),
            Q("英语中人名的首字母要（　）。", "大写", "小写", "加粗", "标红"),
            Q("听音辨义：「他是我的爷爷。」对应的句子是（　）。", "He is my grandfather.", "She is my grandmother.", "This is my father.", "I love grandma."),
            Q("「parents」= father and（　）。", "mother", "brother", "teacher", "sister only"),
            Q("介绍全家福时的顺序可以是（　）。", "从长辈到晚辈依次介绍", "随便乱指", "只说一个", "不说"),
            Q("家庭作业：用英语介绍一位家人，开头说（　）。", "This is my …", "Goodbye …", "What's …", "How many …"),
            Q("「 Who's this?」的正确回答是（　）。", "She is my mother.", "I'm fine.", "It's red.", "Ten."),
            Q("本单元最重要的话（　）。", "我爱我的家——Family means love.", "背单词最难", "字母最多", "句子最长"),
        ]),
    ]),
    ("第三单元 Amazing animals 神奇的动物", [
        ("第1课 核心词汇", "📣 Today's words: cat / dog / bird / fish / rabbit / panda。动物朋友们来报到！", build_vocab([
            ("cat", "猫"), ("dog", "狗"), ("bird", "鸟"), ("fish", "鱼"),
            ("rabbit", "兔子"), ("panda", "熊猫"), ("animal", "动物"), ("cute", "可爱的"),
            ("big", "大的"), ("small", "小的"),
        ])),
        ("第2课 句型与对话", "📣 Sentences: What pets do you know? / I have a cat. / What wild animals do you know? 聊聊你喜欢的动物。", [
            Q("「I have a cat.」的意思是（　）。", "我有一只猫。", "我想要一只猫。", "猫是我的。", "这是一只猫。"),
            Q("询问「你知道哪些宠物？」应该说（　）。", "What pets do you know?", "What's your name?", "Where is the cat?", "How are you?"),
            Q("熊猫的英语是（　）。", "panda", "pencil", "plant", "pig"),
            Q("「The panda is black and white.」的意思是（　）。", "熊猫是黑白色的。", "熊猫很大。", "熊猫爱吃竹子。", "熊猫会游泳。"),
            Q("告诉别人你有一只狗，说（　）。", "I have a dog.", "I am a dog.", "This is a dog food.", "Dog, go!"),
            Q("「cute」的意思是（　）。", "可爱的", "危险的", "巨大的", "难看的"),
            Q("兔子的英语是（　）。", "rabbit", "rubber", "robot", "rain"),
            Q("「Look at the bird!」的意思是（　）。", "看那只鸟！", "喂那只鸟。", "鸟飞走了。", "鸟在唱歌。"),
            Q("宠物和野生动物的区别是（　）。", "宠物在家养，野生动物在大自然", "一样", "野生动物更小", "宠物会说话"),
            Q("「fish」的复数一般说（　）。", "fish", "fishes 只在少数情况", "fishes 一定", "fishes 一定不用——常见 fish"),
            M("Pets 有（　）。", ["cat", "dog", "fish", "panda（野生动物）"], ["A", "B", "C"]),
            M("Wild animals 有（　）。", ["panda", "tiger", "elephant", "pet cat"], ["A", "B", "C"]),
            Q("「Do you have a pet?」的正确回答是（　）。", "Yes, I have a dog.", "Yes, it is red.", "I'm fine.", "Ten."),
            Q("爱护动物要（　）。", "不打扰、不伤害它们", "投喂零食都行", "捉回家", "吓唬它们"),
            Q("「The rabbit has long ears.」的意思是（　）。", "兔子有长耳朵。", "兔子有短尾巴。", "兔子爱吃萝卜。", "兔子跑得快。"),
            Q("问别人宠物的名字，说（　）。", "What's your pet's name?", "Who are you?", "What colour is it?", "How old are you?"),
            Q("描述动物外形可以说（　）。", "It's big. / It's small. / It's cute.", "只说数字", "不说", "唱出来"),
            Q("「amazing」的意思是（　）。", "神奇的、令人惊叹的", "可怕的", "普通的", "难过的"),
            Q("保护大熊猫，我们应该（　）。", "保护竹林和它们的家园", "抓一只养", "扔垃圾", "砍竹子"),
            Q("「I like animals.」的意思是（　）。", "我喜欢动物。", "我有一只动物。", "动物喜欢我。", "动物在哪里？"),
            Q("去动物园要（　）。", "遵守规则，不投喂、不拍打玻璃", "随便喂食", "大喊大叫", "翻越围栏"),
        ]),
        ("第3课 综合运用", "📣 综合练习：字母 Ii~Ll、a/an 的用法、单词听辨。小试身手！", [
            Q("大写字母「I」的小写是（　）。", "i", "l", "j", "1"),
            Q("按字母表顺序，J 的后面是（　）。", "K", "I", "L", "M"),
            Q("「an apple」用 an 是因为 apple 以（　）开头。", "元音音素 a", "辅音", "数字", "大写"),
            Q("a cat 还是 an cat？（　）", "a cat", "an cat", "an a cat", "cat a"),
            Q("用 a/an 填空：（　）dog。（　）", "a", "an", "the 一定", "不填"),
            Q("「bird」的第一个字母是（　）。", "b", "p", "d", "g"),
            Q("rabbit 和 rubber 的区别是（　）。", "rabbit 是兔子，rubber 是橡皮", "一样", "都是兔子", "都是橡皮"),
            Q("下列单词以 L 开头的是（　）。", "look", "book", "cook", "hook"),
            M("含字母 i 的单词有（　）。", ["fish", "big", "panda", "run"], ["A", "B"]),
            M("本单元动物词有（　）。", ["cat", "bird", "rabbit", "banana"], ["A", "B", "C"]),
            Q("「It's a small fish.」的意思是（　）。", "它是一条小鱼。", "它是一只大鸟。", "鱼很小吗？", "鱼在哪里？"),
            Q("英语句子末尾要加（　）。", "标点（. ! ?）", "逗号都行", "什么不加", "加中文句号"),
            Q("「I have a/an …」后面接（　）。", "事物名词", "动词原形 alone", "形容词 only", "数字 only"),
            Q("听音辨义：「熊猫是黑白色的。」对应的句子是（　）。", "The panda is black and white.", "The panda is big.", "I have a panda.", "Pandas eat bamboo."),
            Q("字母 Kk 的大小写是（　）。", "K k", "K J", "R k", "X k"),
            Q("dog 反义（类别）对应的字母开头是（　）——猫。（　）", "c（cat）", "d", "b", "f"),
            Q("书写小写 a、c、e 时占（　）。", "中格", "上两格", "下两格", "三格"),
            Q("「It is」的缩写是（　）。", "It's", "Its", "It is not", "Is it"),
            Q("爱护动物的宣传语可以是（　）。", "Animals are our friends.", "Kill them.", "Eat them all.", "Go away!"),
            S2("本单元你学会了（　）。", ["用英语说动物名和介绍宠物", "写日记", "唱歌跳舞", "乘法"]),
            Q("描述动物顺序建议（　）。", "先说大小颜色，再说本领", "乱说一气", "只说名字", "不描述"),
        ]),
    ]),
    ("第四单元 Plants around us 我们身边的植物", [
        ("第1课 核心词汇", "📣 Today's words: plant / tree / flower / grass / seed。身边的花草树木，用英语说出来！", build_vocab([
            ("plant", "植物"), ("tree", "树"), ("flower", "花"), ("grass", "草"),
            ("seed", "种子"), ("leaf", "叶子"), ("tall", "高的"), ("green", "绿色的"),
            ("garden", "花园"), ("water", "浇水；水"),
        ])),
        ("第2课 句型与对话", "📣 Sentences: What do we get from plants? / How can we help plants? 植物是我们的好朋友。", [
            Q("「Plants are our friends.」的意思是（　）。", "植物是我们的朋友。", "植物很多。", "我们种植物。", "植物能吃。"),
            Q("询问「我们从植物那里得到什么？」说（　）。", "What do we get from plants?", "What's this?", "How are you?", "Who is he?"),
            S2("我们从植物得到的食物有（　）。", ["水果、蔬菜、大米", "石头", "塑料", "金属"]),
            Q("「The tree is tall.」的意思是（　）。", "这棵树很高。", "这棵树很矮。", "树在开花。", "树需要水。"),
            Q("帮助植物，我们可以（　）。", "浇水、不摘花、不踩草", "拔草都拔光", "折树枝", "扔垃圾"),
            Q("「Don't pick the flowers!」的意思是（　）。", "不要摘花！", "摘花吧！", "花很美。", "花开了。"),
            Q("花的英语是（　）。", "flower", "floor", "food", "four"),
            Q("「I water the plant every day.」的意思是（　）。", "我每天给植物浇水。", "我每天看植物。", "植物每天长大。", "我种了一棵树。"),
            Q("种子发芽需要（　）。", "水、阳光和土壤", "只有水", "黑暗", "冰箱"),
            M("Plants include 有（　）。", ["tree", "flower", "grass", "dog"], ["A", "B", "C"]),
            M("We get from plants 有（　）。", ["apples", "rice", "cotton（棉花）", "milk"], ["A", "B", "C"]),
            Q("爱护草坪，应该（　）。", "不踩踏、走小路", "在上面踢球", "躺上面打滚", "拔草玩"),
            Q("「How can we help plants?」的正确回答是（　）。", "We can water them.", "I'm fine.", "It's green.", "Ten."),
            S2("树的作用有（　）。", ["净化空气、遮阴、结果实", "只好看", "只能砍", "没用"]),
            Q("「The flowers are beautiful.」的意思是（　）。", "这些花很美。", "花开了吗？", "花要谢了。", "别碰花。"),
            Q("观察植物可以说它（　）。", "是高是矮、开什么颜色的花", "只数数量", "不说", "闻一闻就够"),
            Q("植树节在（　）月。", "3", "4", "5", "9"),
            Q("植物生长需要（　）。", "阳光、水分、空气、土壤", "只有阳光", "只有黑暗", "巧克力"),
            Q("「green」的意思是（　）。", "绿色的", "红色的", "蓝色的", "黄色的"),
            Q("保护植物就是保护（　）。", "我们共同的家园", "别人", "金钱", "玩具"),
        ]),
        ("第3课 综合运用", "📣 综合练习：字母 Mm~Pp、单复数入门、单词听辨。做得不错！", [
            Q("大写字母「M」的小写是（　）。", "m", "n", "w", "h"),
            Q("按字母表顺序，N 的后面是（　）。", "O", "M", "P", "L"),
            Q("「plant」的第一个字母是（　）。", "p", "b", "d", "t"),
            Q("flower 和 floor 的区别是（　）。", "flower 是花，floor 是地板", "一样", "都是花", "都是地板"),
            Q("一棵树用（　）：one（　）。", "tree", "two trees only", "trees", "leaf"),
            Q("tree 的第一个字母是（　）。", "t", "d", "p", "f"),
            M("以 P 开头的单词有（　）。", ["plant", "panda", "pig", "cat"], ["A", "B", "C"]),
            M("本单元单词有（　）。", ["tree", "flower", "seed", "yellow"], ["A", "B", "C"]),
            Q("「grass」的意思是（　）。", "草", "玻璃", "绿色", "花盆"),
            Q("leaf 的意思是（　）。", "叶子", "离开", "生活", "树叶人"),
            Q("听音辨义：「不要摘花！」对应的句子是（　）。", "Don't pick the flowers!", "Water the flowers.", "The flowers are red.", "I like flowers."),
            Q("书写字母 Pp 时注意（　）。", "大写 P 两笔完成要规范", "几笔都行", "不用规范", "写反也对"),
            Q("英语中「不要……」常用（　）开头。", "Don't", "Do", "Does", "Did"),
            Q("「water」作动词的意思是（　）。", "浇水", "喝水", "游泳", "下雨"),
            Q("植物单元给我们的启示是（　）。", "人与自然和谐相处", "植物无用", "随意采摘", "不关心"),
            Q("「The garden is beautiful.」的意思是（　）。", "花园很美。", "花园很大。", "花园很远。", "花园关门了。"),
            Q("单词 tall 的反义词是（　）。（本册接触）", "short（短的；矮的）", "taller", "long", "big"),
            Q("「I can see a green tree.」的意思是（　）。", "我能看见一棵绿树。", "我看不见树。", "树是红色的。", "我在树上。"),
            Q(" protecting plants 就是（　）。", "保护植物", "砍伐植物", "买卖植物", "吃掉植物"),
            S2("本单元你学会了（　）。", ["用英语说常见植物并爱护它们", "做手工", "写生字", "背古诗"]),
        ]),
    ]),
    ("第五单元 The colourful world 多彩世界", [
        ("第1课 核心词汇", "📣 Today's words: colour / red / yellow / blue / green / orange。世界因色彩而美丽！", build_vocab([
            ("colour", "颜色"), ("red", "红色"), ("yellow", "黄色"), ("blue", "蓝色"),
            ("green", "绿色"), ("orange", "橙色；橙子"), ("purple", "紫色"), ("white", "白色"),
            ("black", "黑色"), ("brown", "棕色"),
        ])),
        ("第2课 句型与对话", "📣 Sentences: What colours do you see? / I see … / How do colours help us? 睁大眼睛看世界。", [
            Q("「What colours do you see?」的意思是（　）。", "你看到了哪些颜色？", "你在哪里？", "你几岁？", "你喜欢什么？"),
            Q("回答看到了红色，说（　）。", "I see red.", "I am red.", "It is I.", "Red, go!"),
            Q("「red」的意思是（　）。", "红色", "绿色", "蓝色", "黄色"),
            Q("天空的颜色可以说（　）。", "The sky is blue.", "The sky is red.", "The sky is yellow.", "The sky is brown."),
            Q("香蕉的颜色是（　）。", "yellow", "blue", "purple", "black"),
            Q("「I like orange.」可以指（　）。", "我喜欢橙色（或橙子）", "我只喜欢数字", "我讨厌橙色", "橙色是我的敌人"),
            Q("snow 的颜色是（　）。", "white", "black", "green", "red"),
            Q("夜空的颜色是（　）。", "black", "white", "pink", "yellow"),
            Q("「What colour is it?」的正确回答是（　）。", "It's green.", "It's a cat.", "I'm nine.", "Yes, it is."),
            M("颜色词有（　）。", ["red", "blue", "green", "apple"], ["A", "B", "C"]),
            M("冷暖搭配正确说出的颜色有（　）。", ["red", "yellow", "blue", "book"], ["A", "B", "C"]),
            Q("「How do colours help us?」问的是（　）。", "颜色如何帮助我们", "什么颜色好看", "颜色多重", "颜色多少个"),
            Q("红绿灯中红色表示（　）。", "停止（别走）", "通行", "慢行", "倒车"),
            Q("红绿灯中绿色表示（　）。", "通行", "停止", "转弯", "鸣笛"),
            Q("「The banana is yellow.」的意思是（　）。", "香蕉是黄色的。", "香蕉是绿色的。", "香蕉好吃。", "香蕉在哪？"),
            S2("彩虹的颜色包括（　）。", ["红橙黄绿蓝靛紫", "只有红色", "只有黑色白色", "没有颜色"]),
            Q("「brown」的意思是（　）。", "棕色", "蓝色", "灰色", "粉色"),
            Q("描述小猫颜色，说（　）。", "The cat is white.", "The cat is two.", "The cat is run.", "Cat, cat!"),
            Q("traffic lights 有（　）种颜色。", "3", "2", "4", "5"),
            Q("「black and white」的意思是（　）。", "黑白相间", "黑或白", "黑色白色都不要", "灰"),
            Q("发现生活中的颜色能（　）。", "培养观察力和美感", "浪费时间", "没有用", "代替学习"),
        ]),
        ("第3课 综合运用", "📣 综合练习：字母 Qq~Tt、颜色词听辨、It's 的用法。越练越棒！", [
            Q("大写字母「R」的小写是（　）。", "r", "p", "q", "v"),
            Q("按字母表顺序，Q 的后面是（　）。", "R", "P", "S", "O"),
            Q("「orange」的第一个字母是（　）。", "o", "a", "p", "e"),
            Q("red 的第一个字母是（　）。", "r", "l", "b", "d"),
            Q("「It's」= （　）。", "It is", "It has", "It was", "Its"),
            Q("「It's a yellow banana.」的意思是（　）。", "它是一根黄香蕉。", "它是一根绿香蕉。", "香蕉好吃。", "香蕉在哪？"),
            M("以 S 开头的颜色相关词有（　）。", ["sky（天空）", "see（看见）", "sun（太阳）", "pen"], ["A", "B", "C"]),
            M("本单元颜色词有（　）。", ["purple", "brown", "white", "water"], ["A", "B", "C"]),
            Q("blue 的第一个字母是（　）。", "b", "d", "p", "g"),
            Q("yellow 里有两个（　）。", "l", "e 只有一个", "o 三个", "y 两个"),
            Q("「I see with my eyes.」的意思是（　）。", "我用眼睛看。", "我用耳朵听。", "我看见眼睛。", "眼睛在头上。"),
            Q("听音辨义：「你看不到哪些颜色？」——不对，原句：What colours do you see? 对应中文（　）。", "你看到哪些颜色？", "你喜欢什么？", "这是红色吗？", "颜色有什么用？"),
            Q("书写字母 Tt 时注意（　）。", "大写 T 两笔规范书写", "随意", "写反也行", "不写"),
            Q("「purple」读的时候第一个音是（　）。", "/p/", "/b/", "/f/", "/v/"),
            Q("颜色三原色是（　）。", "红、黄、蓝", "黑、白、灰", "紫、绿、橙", "金、银、铜"),
            Q("「The apple is red.」的意思是（　）。", "苹果是红色的。", "苹果是绿色的。", "苹果好吃。", "苹果在哪？"),
            Q("红色 + 黄色调出（　）。（生活常识）", "橙色", "绿色", "紫色", "黑色"),
            Q("黄色 + 蓝色调出（　）。（生活常识）", "绿色", "橙色", "紫色", "灰色"),
            S2("本单元你学会了（　）。", ["用英语说颜色并描述事物", "计算题", "写生字", "背课文"]),
            Q("色彩让世界（　）。", "丰富多彩", "单调", "黑暗", "混乱"),
        ]),
    ]),
    ("第六单元 Useful numbers 有用的数字", [
        ("第1课 核心词汇", "📣 Today's words: one / two / three / four / five / six / seven / eight / nine / ten。数一数，真有趣！", build_vocab([
            ("one", "一"), ("two", "二"), ("three", "三"), ("four", "四"),
            ("five", "五"), ("six", "六"), ("seven", "七"), ("eight", "八"),
            ("nine", "九"), ("ten", "十"), ("number", "数字"), ("how many", "多少"),
        ])),
        ("第2课 句型与对话", "📣 Sentences: When do we use numbers? / How many …? 数字在生活中真有用！", [
            Q("「How many books?」的意思是（　）。", "有多少本书？", "这本书多少钱？", "书在哪里？", "这是你的书吗？"),
            Q("回答有 3 本书，说（　）。", "Three books.", "Book three.", "Third.", "Book, book."),
            Q("「five」的意思是（　）。", "五", "四", "六", "十五"),
            Q("3 + 2 = 5 用英语说结果：（　）。", "five", "four", "six", "two"),
            Q("「When do we use numbers?」问的是（　）。", "我们什么时候用到数字", "数字多大", "数字好看吗", "数字在哪"),
            M("生活中用数字的地方有（　）。", ["电话号码", "车牌", "门牌", "颜色"], ["A", "B", "C"]),
            M("数字词有（　）。", ["one", "two", "ten", "cat"], ["A", "B", "C"]),
            Q("「nine」和「ten」之间的大小（　）。", "nine < ten", "nine > ten", "相等", "无法比"),
            Q("你的座位号、学号都是（　）。", "数字（编码）", "颜色", "动物", "食物"),
            Q("「I have ten fingers.」的意思是（　）。", "我有十根手指。", "我有两只手。", "手指疼。", "数手指。"),
            Q("问有几支铅笔，说（　）。", "How many pencils?", "How much pencil?", "What pencil?", "Who pencil?"),
            Q("「seven」的发音开头是（　）。", "/s/", "/f/", "/e/", "/n/"),
            Q("6 的英语是（　）。", "six", "sex 不对——six", "sixteen", "sixty"),
            Q("「Two and three is five.」的意思是（　）。", "二加三等于五。", "二乘三等于六。", "五减三。", "三除二。"),
            Q("电梯里的数字表示（　）。", "楼层", "重量", "速度", "颜色"),
            Q("「eight」的发音和「ate（吃，eat 的过去式）」（　）。", "同音", "不同", "反义", "无关"),
            Q("电话号码 110 是（　）电话。", "报警", "火警 119", "急救 120", "查号 114"),
            Q("火警电话是（　）。", "119", "110", "120", "122"),
            Q("「How many days in a week?」的正确回答是（　）。", "Seven.", "Six.", "Ten.", "One."),
            Q("数字让生活（　）。", "有序、方便", "混乱", "复杂", "无聊"),
        ]),
        ("第3课 综合运用", "📣 综合练习：字母 Uu~Zz、数字 1~10 的听辨与书写。 alphabet 马上集齐啦！", [
            Q("大写字母「U」的小写是（　）。", "u", "v", "n", "w"),
            Q("按字母表顺序，X 的后面是（　）。", "Y", "W", "Z", "V"),
            Q("字母表最后一个字母是（　）。", "Z", "A", "Y", "M"),
            Q("「eight」的第一个字母是（　）。", "e", "a", "i", "h"),
            Q("「three」里有（　）个 e。", "2", "1", "3", "0"),
            Q("10 的英语是（　）。", "ten", "nine", "eleven", "one"),
            Q("「five」和「nine」的第一个字母（　）。", "都是 f——five 是 f，nine 是 n，不同", "相同", "一个是元音一个不是——f/n 都是辅音，不同", "无法比较"),
            M("元音字母有（　）。", ["a", "e", "i", "b"], ["A", "B", "C"]),
            M("数字 1~5 有（　）。", ["one", "two", "three", "six"], ["A", "B", "C"]),
            Q("「seven」的意思是（　）。", "七", "十一", "十七", "七十"),
            Q("听音辨义：「我有 9 支铅笔。」对应的句子是（　）。", "I have nine pencils.", "I have ten pencils.", "I have nine books.", "Pencils are nine."),
            Q("书写数字相关的单词时（　）。", "字母规范、间距均匀", "越大越好", "连笔最快", "不用写"),
            Q("「 Z z」的大小写组合正确的是（　）。", "Z z", "Z s", "X z", "Z i"),
            Q("按顺序填空：eight, nine, （　）。", "ten", "seven", "eleven", "one"),
            Q("「six」反着拼是（　）。（趣味）", "xis（不是单词）", "six", "xis 是 six 的镜像拼写练习", "没有反拼"),
            Q("alphabet 的意思是（　）。", "字母表", "字母歌", "单词表", "课本"),
            Q("26 个字母中元音字母有（　）个。", "5", "4", "6", "21"),
            S2("本学期我们学习了（　）。", ["26 个字母和 1~10 的数字", "1000 个单词", "写作文", "阅读长文"]),
            Q("「Let's count from one to ten.」的意思是（　）。", "让我们从一数到十。", "让我们唱歌。", "从十数到一。", "写字。"),
            Q("数字和字母是英语学习的（　）。", "基础", "全部", "最难的部分", "不重要的"),
            Q("下学期我们将学习（　）。（展望）", "更多单词和日常对话", "大学内容", "古诗", "微积分"),
        ]),
    ]),
    ("复习与检测", [
        ("第1课 Revision 1（Units 1~3）", "📣 复习时间：交朋友、家庭、动物三个单元的单词和句型大盘点。看看你记住了多少！", build_vocab([
            ("hello", "你好"), ("friend", "朋友"), ("family", "家庭"), ("mother", "妈妈"),
            ("father", "爸爸"), ("cat", "猫"), ("dog", "狗"), ("bird", "鸟"),
            ("cute", "可爱的"), ("goodbye", "再见"), ("sister", "姐姐；妹妹"), ("rabbit", "兔子"),
        ])),
        ("第2课 Revision 2（Units 4~6）", "📣 复习时间：植物、颜色、数字三个单元大盘点。加油，期末冲刺！", build_vocab([
            ("tree", "树"), ("flower", "花"), ("red", "红色"), ("blue", "蓝色"),
            ("green", "绿色"), ("one", "一"), ("two", "二"), ("three", "三"),
            ("yellow", "黄色"), ("ten", "十"), ("plant", "植物"), ("five", "五"),
        ])),
    ]),
]

if __name__ == "__main__":
    run(r"content/primary/pep/grade3/volume1/english", "英语上册", UNITS)
