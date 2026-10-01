# -*- coding: utf-8 -*-
"""人教版 PEP 六年级下册英语全部单元交互自测题生成脚本。"""
import random

from _quizlib import S, S2, M, run


RNG = random.Random(20260902)


def _others(correct, pool, n=3):
    xs = [x for x in pool if x != correct]
    RNG.shuffle(xs)
    return xs[:n]


def en2cn(en, cn, pool_cn):
    return ("s", "「%s」的意思是（　）。" % en, [cn] + _others(cn, pool_cn), ["A"])


def cn2en(cn, en, pool_en):
    return ("s", "「%s」用英语说是（　）。" % cn, [en] + _others(en, pool_en), ["A"])


def first_letter(en, pool_letters):
    answer = en[0].upper()
    return ("s", "单词或短语「%s」的第一个字母是（　）。" % en,
            [answer] + _others(answer, pool_letters), ["A"])


def letter_case(letter):
    up, low = letter.upper(), letter.lower()
    return ("s", "大写字母「%s」的小写形式是（　）。" % up,
            [low, up, chr((ord(low) - 97 + 1) % 26 + 97),
             chr((ord(low) - 97 + 2) % 26 + 97)], ["A"])


def build_vocab(words, want=22):
    """词汇课：英译中 + 中译英 + 首字母 + 大小写。"""
    pool_cn = [cn for _, cn in words]
    pool_en = [en for en, _ in words]
    letters = list("ABCDEFGHIJKLMNOPQRSTW")
    questions = []
    for en, cn in words:
        questions.append(en2cn(en, cn, pool_cn))
        questions.append(cn2en(cn, en, pool_en))
        if len(en) >= 3:
            questions.append(first_letter(en, letters))
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        questions.append(letter_case(letter))
    seen, result = set(), []
    for question in questions:
        if question[1] in seen:
            continue
        seen.add(question[1])
        result.append(question)
    RNG.shuffle(result)
    return result[:want]


def Q(stem, ans, *wrong):
    return S(stem, ans, [str(item) for item in wrong])


UNITS = [
    ("第一单元 How tall are you", [
        ("第1课 核心词汇", "Today's words: taller / shorter / older / younger / stronger / heavier。学会用形容词比较级描述身高和体型。", build_vocab([
            ("taller", "更高的"), ("shorter", "更矮的；更短的"), ("older", "更年长的"),
            ("younger", "更年轻的"), ("stronger", "更强壮的"), ("heavier", "更重的"),
            ("bigger", "更大的"), ("smaller", "更小的"), ("thinner", "更瘦的"),
            ("longer", "更长的"), ("dinosaur", "恐龙"), ("kilogram", "千克"),
        ])),
        ("第2课 句型与对话", "Sentences: How tall are you? / I'm 1.65 metres. / Who is taller than you? 学会比较身高、年龄和体型。", [
            Q("询问“你有多高？”应该说（　）。", "How tall are you?", "How old are you?", "How heavy are you?", "How many are you?"),
            Q("回答“How tall are you?”可以说（　）。", "I'm 1.65 metres.", "I'm twelve.", "I'm 40 kilograms.", "I'm fine."),
            Q("询问“他比你高吗？”应该说（　）。", "Is he taller than you?", "Is he taller you?", "Does he taller than you?", "Is he tall than you?"),
            Q("询问体重应该说（　）。", "How heavy are you?", "How long are you?", "How high are you?", "How big are you?"),
            Q("回答“How heavy are you?”可以说（　）。", "I'm 42 kilograms.", "I'm 1.5 metres.", "I'm eleven.", "I'm a student."),
            Q("形容词 tall 的比较级是（　）。", "taller", "tall", "tallest", "more tall"),
            Q("形容词 heavy 的比较级是（　）。", "heavier", "heavyer", "heaviest", "more heavy"),
            Q("形容词 thin 的比较级是（　）。", "thinner", "thiner", "thinnest", "more thin"),
            Q("形容词 big 的比较级是（　）。", "bigger", "biger", "biggest", "more big"),
            Q("两者相比时，比较级后面用（　）。", "than", "then", "that", "this"),
            Q("metre 的意思是（　）。", "米", "千克", "厘米的倍数", "步长"),
            Q("kilogram 的常用缩写是（　）。", "kg", "km", "g", "mg"),
            Q("“I'm taller than you.”中 than 后面可以用（　）。", "me 或 you 等人称", "只接名词", "只接动词-ing", "只接月份"),
            Q("“My brother is older than me.”的意思是（　）。", "我哥哥比我年长。", "我哥哥比我高。", "我比我哥哥胖。", "我哥哥很聪明。"),
            M("属于形容词比较级的有（　）。", ["taller", "heavier", "stronger", "tall"], ["A", "B", "C"]),
            M("可以用来表达身高的句子有（　）。", ["I'm 1.62 metres.", "I'm taller than my sister.", "He is 1.7 metres tall.", "I'm ten years old."], ["A", "B", "C"]),
            Q("补全对话：— How tall are you? —（　）", "I'm 1.58 metres.", "I'm 45 kilograms.", "I'm twelve years old.", "Yes, I am."),
            Q("补全句子：My bag is（　）than yours.", "heavier", "heavy", "heaviest", "more heavy"),
            Q("比较同学身高时，应该（　）。", "用数据说话并互相尊重", "嘲笑个子矮的同学", "凭感觉随便猜", "只看衣服"),
            Q("“size 38”通常用来表示（　）。", "鞋码", "身高", "体重", "年龄"),
            Q("longer 的反义词（在长短意义上）是（　）。", "shorter", "taller", "bigger", "stronger"),
            S2("描述身高，正确的句子是（　）。", ["I'm 1.65 metres. I'm taller than you.", "I'm 1.65 metre. I taller than you.", "I'm 1.65 metres. I'm tall than you.", "I 1.65 metres taller than you."]),
        ]),
        ("第3课 综合运用", "综合练习：形容词比较级、身高体重数据和数据对比。读懂调查表并进行比较描述。", [
            Q("1.70 m 比 1.60 m（　）。", "taller", "shorter", "heavier", "younger"),
            Q("50 kg 比 40 kg（　）。", "heavier", "thinner", "taller", "older"),
            Q("“Who is taller than you?”询问的是（　）。", "谁比你高", "你有多高", "你有多重", "你几岁"),
            Q("把“I am 1.6 metres.”改成问句，应为（　）。", "How tall are you?", "How heavy are you?", "How old are you?", "How many are you?"),
            Q("把“He is taller than me.”改成一般疑问句，应为（　）。", "Is he taller than you?", "Does he taller than you?", "Is he tall than you?", "He is taller than you?"),
            Q("选择语序正确的句子（　）。", "How heavy is your brother?", "How heavy your brother is?", "How your brother heavy is?", "Your brother how heavy is?"),
            Q("形容词 short 变比较级要（　）。", "直接加 -er", "双写再加 -er", "改 y 为 i 加 -er", "加 -est"),
            Q("形容词 funny 的比较级是（　）。", "funnier", "funnyier", "more funny", "funnyer"),
            Q("单音节形容词变比较级时，通常（　）。", "在词尾加 -er", "在词尾加 -ing", "在词尾加 -s", "在词尾加 -ed"),
            Q("婴儿比成人（　）。", "younger", "older", "heavier", "taller"),
            Q("想要长得强壮，应该（　）。", "合理饮食并坚持锻炼", "只吃零食", "熬夜打游戏", "从不做运动"),
            Q("调查表记录身高时通常使用的单位是（　）。", "metre", "kilogram", "year", "size"),
            Q("“I'm the tallest in my class.”中 tallest 是（　）。", "最高级", "比较级", "原级", "副词"),
            Q("比较两人的身高或体重数据时，应该（　）。", "先确认单位是否相同", "忽略单位直接比较", "只看名字长短", "凭空估算"),
            M("比较级句子正确的有（　）。", ["I'm older than my brother.", "She is thinner than me.", "This box is bigger than that one.", "He is tall than me."], ["A", "B", "C"]),
            M("可以用 kilograms 计量的有（　）。", ["the boy's weight", "the bag of rice", "the box of books", "the height of the door"], ["A", "B", "C"]),
            Q("补全对话：— Who is heavier than you? —（　）", "My brother. He's 50 kilograms.", "My brother is 1.7 metres.", "I'm fine.", "Yes, he does."),
            Q("你的好朋友比你矮，你可以说（　）。", "I'm taller than my friend.", "My friend is taller than I.", "I taller than friend.", "My friend taller is than me."),
            Q("看到身高或体重的比较结果后，正确的态度是（　）。", "了解差异并健康成长", "嘲笑别人", "因此感到自卑", "拒绝参加测量"),
            Q("下列哪句同时包含两个人物的比较？（　）", "Tom is stronger than Jim.", "Tom is strong.", "How tall is Tom?", "Tom likes sports."),
            Q("健康地长高需要注意（　）。", "充足睡眠、均衡营养和适度运动", "只喝饮料", "天天熬夜", "从不运动"),
            S2("本单元主要学会了（　）。", ["用形容词比较级比较身高、体重和年龄", "讲述上周末做过的事", "描述旅行经历", "谈论学校的变化"]),
        ]),
    ]),
    ("第二单元 Last weekend", [
        ("第1课 核心词汇", "Today's phrases: cleaned my room / washed my clothes / stayed at home / watched TV。学会用动词过去式讲述上周末。", build_vocab([
            ("cleaned my room", "打扫我的房间"), ("washed my clothes", "洗我的衣服"),
            ("stayed at home", "待在家里"), ("watched TV", "看电视"), ("read a book", "读书"),
            ("saw a film", "看电影"), ("had a cold", "感冒"), ("slept", "睡觉（过去式）"),
            ("cooked the food", "做饭"), ("yesterday", "昨天"), ("last weekend", "上周末"),
            ("magazine", "杂志"),
        ])),
        ("第2课 句型与对话", "Sentences: What did you do last weekend? / Did you read a book? Yes, I did. 学会询问过去做过的事。", [
            Q("询问“你上周末做了什么？”应该说（　）。", "What did you do last weekend?", "What do you do last weekend?", "What are you doing last weekend?", "What will you do last weekend?"),
            Q("回答“What did you do last weekend?”可以说（　）。", "I cleaned my room.", "I clean my room.", "I'm cleaning my room.", "Yes, I did."),
            Q("询问“你看书了吗？”应该说（　）。", "Did you read a book?", "Do you read a book?", "Are you read a book?", "Did you readed a book?"),
            Q("“Did you see a film?”的肯定回答是（　）。", "Yes, I did.", "Yes, I do.", "Yes, I was.", "Yes, I am."),
            Q("“Did you watch TV yesterday?”的否定回答是（　）。", "No, I didn't.", "No, I don't.", "No, I wasn't.", "No, I am not."),
            Q("clean 的过去式是（　）。", "cleaned", "cleanned", "cleant", "clean"),
            Q("watch 的过去式是（　）。", "watched", "watches", "watchd", "watching"),
            Q("wash 的过去式是（　）。", "washed", "washd", "washt", "washes"),
            Q("stay 的过去式是（　）。", "stayed", "staied", "stays", "staying"),
            Q("see 的过去式是（　）。", "saw", "seed", "seen", "seeing"),
            Q("have 的过去式是（　）。", "had", "haved", "havied", "have"),
            Q("sleep 的过去式是（　）。", "slept", "sleeped", "sleept", "sleeps"),
            Q("read 的过去式拼写仍为 read，但读音（　）。", "发生变化", "完全相同", "被省略", "变成 /rid/"),
            Q("“last weekend”的意思是（　）。", "上周末", "下周末", "这周末每天", "周末之前"),
            Q("yesterday 的意思是（　）。", "昨天", "明天", "今天早上", "前天"),
            M("动词过去式形式正确的有（　）。", ["cleaned", "washed", "watched", "watch"], ["A", "B", "C"]),
            M("可以回答“What did you do yesterday?”的有（　）。", ["I read a book.", "I saw a film.", "I cooked the food.", "I am reading a book."], ["A", "B", "C"]),
            Q("补全对话：— Did you clean your room? —（　）", "Yes, I did.", "Yes, I clean.", "Yes, I am.", "Yes, I was."),
            Q("补全句子：I（　）my clothes last night.", "washed", "wash", "washing", "washes"),
            Q("周末合理安排时间应该（　）。", "先完成作业再做其他事", "整夜看电视", "一刻不停地玩手机", "不睡觉"),
            Q("“I had a cold yesterday.”的意思是（　）。", "我昨天感冒了。", "我昨天很热。", "我昨天很冷。", "我昨天发烧住院。"),
            S2("讲述上周末，正确的句子是（　）。", ["I stayed at home and watched TV last weekend.", "I stay at home and watch TV last weekend.", "I stayed at home and watch TV last weekend.", "I staying at home watched TV last weekend."]),
        ]),
        ("第3课 综合运用", "综合练习：动词过去式、一般过去时疑问句和周末日记。读懂活动记录表并讲述自己的周末。", [
            Q("“yesterday”所在的句子通常用（　）。", "一般过去时", "一般现在时", "现在进行时", "一般将来时"),
            Q("把“I watched TV last night.”改成否定句，应为（　）。", "I didn't watch TV last night.", "I don't watch TV last night.", "I wasn't watch TV last night.", "I didn't watched TV last night."),
            Q("把“She read a book yesterday.”改成一般疑问句，应为（　）。", "Did she read a book yesterday?", "Does she read a book yesterday?", "Did she reads a book yesterday?", "Was she read a book yesterday?"),
            Q("选择语序正确的句子（　）。", "What did you do last weekend?", "What you did do last weekend?", "What did you did last weekend?", "Last weekend what did you do it?"),
            Q("在 did 引导的疑问句中，主要动词要用（　）。", "原形", "过去式", "-ing 形式", "第三人称单数"),
            Q("“I didn't sleep well yesterday.”的意思是（　）。", "我昨天没睡好。", "我昨天睡得很香。", "我昨天在睡觉。", "我昨天起床很早。"),
            Q("“have a cold”的正确过去式表达是（　）。", "had a cold", "haved a cold", "had cold", "having a cold"),
            Q("写一篇周末日记，通常按（　）顺序写。", "时间先后", "倒序随意", "只写结果", "只写心情"),
            Q("magazine 的意思是（　）。", "杂志", "漫画书", "报纸摊位", "日记本"),
            Q("“I cooked the food with my mother.”中的 with 表示（　）。", "和……一起", "在……之后", "为了", "关于"),
            Q("上周日在家看书，应记录为（　）。", "I read a book at home last Sunday.", "I read a book at home next Sunday.", "I am reading a book at home last Sunday.", "I reads a book at home last Sunday."),
            M("属于过去时间状语的有（　）。", ["yesterday", "last weekend", "last night", "tomorrow"], ["A", "B", "C"]),
            M("表示家务劳动的短语有（　）。", ["cleaned my room", "washed my clothes", "cooked the food", "took pictures"], ["A", "B", "C"]),
            Q("补全对话：— How was your weekend? —（　）", "It was great. I saw a film.", "It's Monday.", "Yes, I am.", "I'm fine, thanks."),
            Q("同学生病了，你可以建议（　）。", "see a doctor and have a good rest", "run in the rain", "stay up all night", "drink ice water only"),
            Q("做家务的意义是（　）。", "分担家庭责任并锻炼自理能力", "只是大人的事", "耽误学习", "没有任何作用"),
            Q("动词 do 的过去式是（　）。", "did", "doed", "done", "does"),
            Q("“I was busy last weekend.”中的 was 是（　）。", "am/is 的过去式", "are 的过去式", "将来时的形式", "动词原形"),
            Q("下列哪句同时包含过去时间和活动？（　）", "I cleaned my room last Saturday.", "I clean my room every day.", "Cleaning is fun.", "Last Saturday is coming."),
            Q("回顾上周末时，最值得记录的是（　）。", "有意义的活动和收获", "全部时间点起床记录", "别人的隐私", "无关的广告"),
            S2("本单元主要学会了（　）。", ["用一般过去时讲述上周末的活动", "比较身高和体重", "描述过去到过的旅行地", "介绍学校的新旧变化"]),
        ]),
    ]),
    ("第三单元 Where did you go", [
        ("第1课 核心词汇", "Today's phrases: went camping / went fishing / rode a horse / took pictures。学会用过去式讲述假期活动。", build_vocab([
            ("went camping", "去野营"), ("went fishing", "去钓鱼"), ("rode a horse", "骑马"),
            ("rode a bike", "骑自行车"), ("took pictures", "照相"), ("bought gifts", "买礼物"),
            ("ate fresh food", "吃新鲜的食物"), ("fell off", "摔倒；跌落"),
            ("hurt my foot", "弄伤了我的脚"), ("Labour Day", "劳动节"), ("beach", "海滩"),
            ("basket", "篮子"),
        ])),
        ("第2课 句型与对话", "Sentences: Where did you go? / How did you go there? / What did you do? 学会询问旅行经历。", [
            Q("询问“你去哪儿了？”应该说（　）。", "Where did you go?", "Where do you go?", "Where are you going?", "Where did you went?"),
            Q("回答“Where did you go?”可以说（　）。", "I went to Turpan.", "I will go to Turpan.", "I'm going to Turpan.", "Yes, I did."),
            Q("询问“你怎么去那儿的？”应该说（　）。", "How did you go there?", "How do you go there?", "What did you go there?", "When did you go there?"),
            Q("询问“你在那里做了什么？”应该说（　）。", "What did you do there?", "What do you do there?", "Where did you go?", "Who did you go with?"),
            Q("go 的过去式是（　）。", "went", "goed", "gone", "goes"),
            Q("ride 的过去式是（　）。", "rode", "rided", "rided not", "ridden"),
            Q("take 的过去式是（　）。", "took", "taked", "taken", "takes"),
            Q("buy 的过去式是（　）。", "bought", "buyed", "buied", "buying"),
            Q("eat 的过去式是（　）。", "ate", "eated", "eaten", "eats"),
            Q("fall 的过去式是（　）。", "fell", "falled", "fallen", "falls"),
            Q("hurt 的过去式是（　）。", "hurt", "hurted", "hurts", "hurting"),
            Q("“I rode a bike in the park.”的意思是（　）。", "我在公园里骑自行车了。", "我在公园里骑马了。", "我在公园里跑步了。", "我在公园里买礼物了。"),
            Q("“I took many pictures.”的意思是（　）。", "我拍了很多照片。", "我买了很多照片。", "我画了很多画。", "我看了很多照片。"),
            Q("Labour Day 通常在（　）。", "May", "January", "August", "October"),
            Q("beach 的意思是（　）。", "海滩", "山峰", "森林", "沙漠"),
            M("属于户外活动短语的有（　）。", ["went camping", "went fishing", "rode a horse", "watched a match at home"], ["A", "B", "C"]),
            M("谈论一次旅行会用到的问句有（　）。", ["Where did you go?", "How did you go there?", "What did you do there?", "How tall are you?"], ["A", "B", "C"]),
            Q("补全对话：— Where did you go last holiday? —（　）", "I went to Xinjiang.", "I go to Xinjiang.", "I will go to Xinjiang.", "Yes, I did."),
            Q("补全句子：We（　）camping last summer.", "went", "go", "going", "goes"),
            Q("外出旅行时应该（　）。", "注意安全并保护环境卫生", "独自去陌生水域游泳", "随意丢弃垃圾", "攀爬危险的山崖"),
            Q("“I bought some gifts for my friends.”中的 for 表示（　）。", "给；为了", "从哪里", "在……之前", "在……之上"),
            S2("讲述旅行，正确的句子是（　）。", ["I went fishing and took many pictures there.", "I go fishing and take many pictures there.", "I went fishing and take many pictures there.", "I going fishing took pictures there."]),
        ]),
        ("第3课 综合运用", "综合练习：旅行经历、不规则动词过去式和安全意识。读懂旅行日记并讲述自己的假期。", [
            Q("“Where did you go last summer holiday?”回答时必须包含（　）。", "地点", "身高", "体重", "鞋码"),
            Q("把“I went to Beijing.”改成问句，应为（　）。", "Where did you go?", "Where do you go?", "Did you went to Beijing?", "Where you did go?"),
            Q("把“We went there by train.”改成问句，应为（　）。", "How did you go there?", "What did you go there?", "When did you go there?", "Who did you go there?"),
            Q("选择语序正确的句子（　）。", "What did you do in Turpan?", "What you did do in Turpan?", "What did you did in Turpan?", "In Turpan what did you went?"),
            Q("“I fell off my bike and hurt my foot.”的意思是（　）。", "我从自行车上摔下来弄伤了脚。", "我在自行车上安装了篮子。", "我骑车去了海滩。", "我买了一辆新自行车。"),
            Q("受伤后第一时间应该（　）。", "告诉家长并及时处理伤口", "继续骑车不理会", "用脏手揉伤口", "向别人炫耀"),
            Q("到海边游玩时可以做的事是（　）。", "collect shells on the beach", "climb trees in the sea", "buy fish in the supermarket", "ride a horse on the water"),
            Q("动词 swim 的过去式是（　）。", "swam", "swimed", "swum", "swims"),
            Q("动词 sing 的过去式是（　）。", "sang", "singed", "sung", "sings"),
            Q("“I ate lots of fresh food there.”中的 lots of 表示（　）。", "许多", "很少", "只有两个", "从不"),
            Q("写一篇旅行日记通常要写清（　）。", "时间、地点、交通方式和活动", "只需要写天气", "只需要写名字", "只需要写心情"),
            M("不规则动词过去式正确的有（　）。", ["went", "rode", "ate", "goed"], ["A", "B", "C"]),
            M("旅行中可能发生的事有（　）。", ["took pictures", "bought gifts", "ate fresh food", "went to school every day"], ["A", "B", "C"]),
            Q("补全对话：— How did you go to Beijing? —（　）", "By train.", "Last year.", "With my parents only.", "Yes, we did."),
            Q("给朋友讲旅行故事时，要注意（　）。", "按时间顺序说清楚", "只说结果不说过程", "夸大虚构经历", "随意编造地名"),
            Q("“Turpan”以盛产水果闻名，它属于（　）。", "Xinjiang", "Beijing", "Shanghai", "Hainan"),
            Q("在野外露营时应该（　）。", "选择安全地点并注意防火", "独自深入密林", "随意生火玩要", "随手乱丢垃圾"),
            Q("动词 see 的过去式是（　）。", "saw", "seed", "seen", "sees"),
            Q("下列哪句同时包含地点和活动？（　）", "I rode a horse in Xinjiang.", "I rode a horse.", "Xinjiang is far.", "Where is Xinjiang?"),
            Q("旅行结束后整理照片和日记的意义是（　）。", "留下美好回忆并分享给他人", "炫耀去过的地方", "证明不需要学习", "增加行李重量"),
            S2("本单元主要学会了（　）。", ["用一般过去时询问并讲述旅行经历", "比较身高体重", "介绍职业", "说明交通规则"]),
        ]),
    ]),
    ("第四单元 Then and now", [
        ("第1课 核心词汇", "Today's words: dining hall / grass / gym / ago / cycling / ice-skate。学会描述学校和生活的变化。", build_vocab([
            ("dining hall", "饭厅"), ("grass", "草坪"), ("gym", "体育馆"),
            ("ago", "……以前"), ("cycling", "骑自行车运动"), ("ice-skate", "滑冰"),
            ("badminton", "羽毛球运动"), ("Internet", "互联网"), ("different", "不同的"),
            ("active", "活跃的"), ("star", "星"), ("race", "赛跑"),
        ])),
        ("第2课 句型与对话", "Sentences: Before, I was quiet. Now I'm active. / There was no gym in my school. 学会对比过去与现在。", [
            Q("表达“以前我很安静，现在我很活跃”应说（　）。", "Before, I was quiet. Now I'm active.", "Before, I am quiet. Now I was active.", "Before I quiet, now I active.", "Now, I was quiet. Before I'm active."),
            Q("表示“很久以前”可以说（　）。", "a long time ago", "a long time now", "next week ago", "in the future ago"),
            Q("ago 通常放在时间词语（　）。", "之后", "之前", "中间省略", "句首单独使用"),
            Q("“There was no gym in my old school.”的意思是（　）。", "我的旧学校里没有体育馆。", "我的旧学校里有两个体育馆。", "我的学校现在没有体育馆。", "体育馆在老学校旁边。"),
            Q("表示过去“有”用（　）。", "there was / there were", "there is / there are", "there will be", "there has"),
            Q("there was 后面接（　）。", "单数名词或不可数名词", "可数名词复数", "动词-ing", "形容词"),
            Q("there were 后面接（　）。", "可数名词复数", "单数名词", "动词原形", "介词短语"),
            Q("gym 的意思是（　）。", "体育馆", "饭厅", "图书馆", "实验室"),
            Q("dining hall 的意思是（　）。", "饭厅", "操场", "宿舍", "礼堂"),
            Q("grass 的意思是（　）。", "草坪", "花园的全部", "大树", "花坛里的水"),
            Q("badminton 是一项（　）。", "球类运动", "水上运动", "棋类游戏", "冬季滑冰项目"),
            Q("“I couldn't ride a bike before.”中 couldn't 是（　）。", "can 的过去式否定形式", "can 的将来式", "must 的过去式", "do 的过去式"),
            Q("“Now I go cycling every day.”的意思是（　）。", "现在我每天骑自行车。", "现在我每天滑冰。", "我以前每天骑车。", "我明天要去骑车。"),
            Q("表达过去不会做某事，应说（　）。", "I couldn't do it before.", "I can't do it now.", "I don't do it ago.", "I won't do it before."),
            M("描述过去状态可以用到的词有（　）。", ["before", "ago", "was", "now"], ["A", "B", "C"]),
            M("学校里可以有的设施有（　）。", ["dining hall", "gym", "grass", "mountain"], ["A", "B", "C"]),
            Q("补全句子：There（　）no library in my school ten years ago.", "was", "were", "is", "are"),
            Q("补全对话：— What was your school like before? —（　）", "It was small and old.", "It is big and new.", "Yes, it was.", "I like my school."),
            Q("学校越来越好，我们应该（　）。", "珍惜并爱护校园设施", "随意刻画桌椅", "在草坪上乱跑", "浪费粮食"),
            Q("“Everything is different now.”中 different 表示（　）。", "不同的", "相同的", "古老的", "安静的"),
            S2("对比过去与现在，正确的句子是（　）。", ["There was no dining hall before, but there is one now.", "There were no dining hall before, but there is one now.", "There was no dining hall now, but there was one before.", "There is no dining hall before, but there was one now."]),
        ]),
        ("第3课 综合运用", "综合练习：there be 句型的过去式、before/now 对比和个人成长变化。读懂学校变化图并介绍变化。", [
            Q("十年前的学校设施少，应说（　）。", "There was no gym ten years ago.", "There is no gym ten years ago.", "There were no gym ten years ago.", "There will be no gym ago."),
            Q("现在学校有了新饭厅，应说（　）。", "There is a new dining hall now.", "There was a new dining hall now.", "There were a new dining hall now.", "There had a dining hall ago."),
            Q("把“There was a small building.”改成否定句，应为（　）。", "There wasn't a small building.", "There isn't a small building.", "There weren't a small building.", "There not was a small building."),
            Q("把“There were some trees.”改成一般疑问句，应为（　）。", "Were there any trees?", "Was there any trees?", "Are there any trees ago?", "Did there were any trees?"),
            Q("选择语序正确的句子（　）。", "There were many students before.", "There was many students before.", "There were many student before.", "There had many students before."),
            Q("“I'm taller and stronger than before.”中 before 表示（　）。", "以前", "以后", "现在", "立刻"),
            Q("十年前不会游泳，现在会了，应说（　）。", "I couldn't swim before, but I can now.", "I can't swim before, but I could now.", "I could swim before, and I can now.", "I couldn't swam before, but I can now."),
            Q("“People looked things up in books.”中的 looked up 表示（　）。", "查阅", "向上看", "丢失", "购买"),
            Q("现在我们用 Internet 查资料，Internet 的意思是（　）。", "互联网", "图书馆里的一切书", "电视机", "邮局"),
            Q("“I'm very active in class now.”中 active 表示（　）。", "活跃的；积极的", "安静的", "困倦的", "害羞的"),
            Q("描述自己的成长变化，最好从（　）几方面说。", "外貌、能力和爱好", "只说身高", "只说天气", "只说别人的事"),
            M("可以用来开头描述过去的词有（　）。", ["before", "ago", "in the past", "next year"], ["A", "B", "C"]),
            M("学校可能发生的变化有（　）。", ["There is a new gym.", "There are more computer rooms.", "The playground is bigger.", "The moon is nearer."], ["A", "B", "C"]),
            Q("补全句子：There（　）twenty students in my class last year.", "were", "was", "is", "be"),
            Q("“I didn't like sports before.”中 didn't 是（　）。", "过去时的否定助动词", "一般现在时否定", "将来时否定", "情态动词"),
            Q("从安静变成积极，说明（　）。", "人会随着学习和锻炼不断成长", "性格永远不会改变", "只有年龄在变大", "爱好必须完全相同"),
            Q("下列哪句同时包含过去和现在？（　）", "Before I was short, but now I'm tall.", "I am tall.", "I was short.", "My school is big."),
            Q("介绍学校新变化时，应（　）。", "用对比的方式说明", "只说过去", "只说未来", "不说任何数据"),
            Q("“We have a race every spring.”中 race 的意思是（　）。", "赛跑；比赛", "草坪上的游戏", "饭厅的名字", "星星的名字"),
            S2("本单元主要学会了（　）。", ["用 before / now 和 there was / were 描述今昔变化", "比较身高体重", "讲述假期旅行", "介绍家人的职业"]),
        ]),
    ]),
    ("第五单元 Recycle Mike's happy days", [
        ("第1课 Recycle 1 综合复习", "Recycle 1：复习 Units 1–2。综合运用比较级、过去式和一般疑问句的问答。", [
            Q("询问身高应该说（　）。", "How tall are you?", "How heavy are you?", "How old are you?", "How many are you?"),
            Q("回答身高“我1.62米”，应说（　）。", "I'm 1.62 metres.", "I'm 1.62 kilograms.", "I'm twelve metres.", "I'm the 1.62."),
            Q("两者比较时要用（　）。", "形容词比较级和 than", "形容词原级", "最高级加 the", "动词-ing"),
            Q("heavy 的比较级是（　）。", "heavier", "heavyer", "more heavy", "heaviest"),
            Q("“I'm stronger than my brother.”的意思是（　）。", "我比我哥哥强壮。", "我比我哥哥年长。", "我哥哥比我强壮。", "我和哥哥一样强壮。"),
            Q("询问“你上周末做了什么？”应说（　）。", "What did you do last weekend?", "What do you do last weekend?", "What are you doing last weekend?", "What will you do last weekend?"),
            Q("clean 的过去式是（　）。", "cleaned", "cleanned", "cleant", "cleans"),
            Q("see 的过去式是（　）。", "saw", "seed", "seen", "seeing"),
            Q("“Did you watch TV yesterday?”的否定回答是（　）。", "No, I didn't.", "No, I don't.", "No, I wasn't.", "No, I am not."),
            Q("在 did 引导的问句中，主要动词用（　）。", "原形", "过去式", "-ing 形式", "第三人称单数"),
            M("属于形容词比较级的有（　）。", ["taller", "bigger", "thinner", "tall"], ["A", "B", "C"]),
            M("属于动词过去式的有（　）。", ["washed", "slept", "had", "wash"], ["A", "B", "C"]),
            Q("补全对话：— How heavy are you? —（　）", "I'm 45 kilograms.", "I'm 1.6 metres.", "I'm eleven years old.", "Yes, I am."),
            Q("补全句子：Mike is（　）than his sister.", "older", "old", "oldest", "more old"),
            Q("“I had a cold last weekend.”的意思是（　）。", "我上周末感冒了。", "我上周末很忙。", "我上周末去游泳了。", "我上周末感冒了三天才去看电影。"),
            Q("写一篇周末日记，通常要说清（　）。", "时间和做过的事情", "只写天气情况", "只写明天的计划", "只写别人的事"),
            Q("比较数据前要先（　）。", "确认单位是否相同", "忽略单位", "随便估测", "只看数字大小"),
            S2("综合运用 U1–U2，正确的句子是（　）。", ["I was busy last weekend, and I'm taller than before.", "I am busy last weekend, and I taller than before.", "I were busy last weekend, and I'm tall than before.", "I busied last weekend, and I'm more tall than before."]),
            Q("健康成长的习惯包括（　）。", "早睡早起、均衡饮食和坚持锻炼", "天天熬夜打游戏", "只吃零食", "从不上体育课"),
            Q("回顾自己的变化时，应该（　）。", "既看到进步也制定新目标", "只和别人比较", "完全不在意数据", "否定自己的努力"),
            Q("下列哪句同时包含过去的活动和现在的比较？（　）", "I cleaned my room last weekend, and now I'm stronger than before.", "I clean my room every day.", "My room is clean.", "Cleaning is my hobby."),
        ]),
        ("第2课 Recycle 2 综合复习", "Recycle 2：复习 Units 3–4。综合运用旅行经历、今昔变化和 there be 过去式。", [
            Q("询问“你去哪里了？”应说（　）。", "Where did you go?", "Where do you go?", "Where are you going?", "Where did you went?"),
            Q("go 的过去式是（　）。", "went", "goed", "gone", "goes"),
            Q("ride 的过去式是（　）。", "rode", "rided", "ridden", "rides"),
            Q("buy 的过去式是（　）。", "bought", "buyed", "buied", "buying"),
            Q("“I took many pictures there.”的意思是（　）。", "我在那里拍了很多照片。", "我在那里买了礼物。", "我在那里钓鱼了。", "我在那里骑马了。"),
            Q("询问“你怎么去那儿的？”应说（　）。", "How did you go there?", "What did you go there?", "Who did you go there?", "When did you there?"),
            Q("表示过去“有”应用（　）。", "there was / there were", "there is / there are", "there has", "there will"),
            Q("there were 后面接（　）。", "可数名词复数", "单数名词", "动词原形", "形容词"),
            Q("“There was no dining hall in my school before.”的意思是（　）。", "我的学校以前没有饭厅。", "我的学校现在没有饭厅。", "我的饭厅以前很小。", "饭厅在体育馆旁边。"),
            Q("ago 通常放在时间短语的（　）。", "后面", "前面并加逗号", "中间省略不写", "句子末尾成独立句"),
            M("旅行中会用到的过去式有（　）。", ["went", "took", "ate", "go"], ["A", "B", "C"]),
            M("可以用来描述过去的词有（　）。", ["before", "ago", "yesterday", "tomorrow"], ["A", "B", "C"]),
            Q("补全句子：There（　）no gym in my school ten years ago.", "was", "were", "is", "are"),
            Q("补全对话：— What did you do in Turpan? —（　）", "I rode a horse and ate fresh food.", "I ride horses every day.", "It's very far.", "Yes, I did."),
            Q("把“There were some trees.”改成否定句，应为（　）。", "There weren't any trees.", "There wasn't any trees.", "There aren't any trees ago.", "There not were any trees."),
            Q("“I couldn't swim before, but I can now.”中 couldn't 表示（　）。", "过去不会", "现在不会", "将来不会", "永远不能"),
            Q("旅行时最重要的是（　）。", "安全第一并遵守当地规定", "独自前往陌生水域", "随意攀爬危险山崖", "乱丢垃圾"),
            Q("介绍家乡或学校变化时，应（　）。", "用从前和现在做对比", "只描述颜色", "只谈未来计划", "只说别人的评价"),
            Q("下列哪句同时包含旅行和活动？（　）", "I went camping and took pictures in Xinjiang.", "I like Xinjiang.", "Xinjiang is big.", "Where is Xinjiang?"),
            S2("综合运用 U3–U4，正确的句子是（　）。", ["I went to Xinjiang last year, and there are many new buildings there now.", "I go to Xinjiang last year, and there were many new buildings there now.", "I went Xinjiang last year, and there is many new buildings there now.", "I going to Xinjiang last year, and there was many new buildings there now."]),
        ]),
    ]),
]


if __name__ == "__main__":
    run(r"content/primary/pep/grade6/volume2/english", "英语下册", UNITS)
