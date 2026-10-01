# -*- coding: utf-8 -*-
"""人教版 PEP 六年级上册英语全部单元交互自测题生成脚本。"""
import random

from _quizlib import S, S2, M, run


RNG = random.Random(20260901)


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
    ("第一单元 How can I get there", [
        ("第1课 核心词汇", "Today's words: science museum / post office / bookstore / cinema / hospital / crossing。学会说地点和方向。", build_vocab([
            ("science museum", "科学博物馆"), ("post office", "邮局"), ("bookstore", "书店"),
            ("cinema", "电影院"), ("hospital", "医院"), ("crossing", "十字路口"),
            ("turn left", "左转"), ("turn right", "右转"), ("go straight", "直走"),
            ("next to", "与……相邻"), ("near", "在……附近"), ("far", "远的"),
        ])),
        ("第2课 句型与对话", "Sentences: Where is the cinema? / It's next to the bookstore. / How can I get there? 学会礼貌地问路与指路。", [
            Q("询问“电影院在哪里？”应该说（　）。", "Where is the cinema?", "What is the cinema?", "Who is in the cinema?", "Is the cinema new?"),
            Q("回答“Where is the bookstore?”可以说（　）。", "It's next to the post office.", "It's a bookstore.", "I read books.", "Yes, it is."),
            Q("询问“我们怎么到那儿？”应该说（　）。", "How can I get there?", "Where can I get there?", "Who can get there?", "Do I get there?"),
            Q("给别人指路时可以说（　）。", "Go straight and turn left.", "Yes, please.", "It's Monday.", "Thank you very much."),
            Q("“Turn left at the hospital.”的意思是（　）。", "在医院处左转。", "医院在左边。", "左转就是医院。", "从医院出来。"),
            Q("“The cinema is next to the bookstore.”中 next to 表示（　）。", "与……相邻", "在……前面", "远离", "在……对面"),
            Q("“Go straight for five minutes.”中 straight 的意思是（　）。", "笔直地", "弯曲地", "慢慢地", "向左"),
            Q("想在邮局向右转，应说（　）。", "Turn right at the post office.", "Turn left at the post office.", "Go right straight.", "Right is the post office."),
            Q("表示“在某处转弯”，地点前常用介词（　）。", "at", "in", "of", "from"),
            Q("陌生人问路时，开头常用礼貌语（　）。", "Excuse me.", "Good night.", "See you.", "Happy birthday."),
            Q("得到别人的帮助后应该说（　）。", "Thank you.", "Excuse me.", "Sorry.", "Goodbye, go away."),
            Q("“Is it far from here?”的否定回答是（　）。", "No, it isn't.", "No, it doesn't.", "No, I'm not.", "Yes, it is."),
            Q("crossing 的意思是（　）。", "十字路口", "建筑物", "停车场", "人行天桥"),
            Q("想去买一本书，应该去（　）。", "bookstore", "hospital", "cinema", "post office"),
            Q("生病了要去看医生，应该去（　）。", "hospital", "bookstore", "science museum", "cinema"),
            Q("想寄一封信，应该去（　）。", "post office", "cinema", "hospital", "bookstore"),
            Q("想看电影，应该去（　）。", "cinema", "post office", "bookstore", "hospital"),
            Q("补全对话：— How can I get to the museum? —（　）", "Turn left at the crossing.", "It's a museum.", "I like museums.", "Yes, I can."),
            Q("补全句子：The hospital is（　）the park.", "near", "next", "far of", "at front"),
            M("属于地点名称的有（　）。", ["bookstore", "hospital", "cinema", "turn"], ["A", "B", "C"]),
            M("可以用来问路的句子有（　）。", ["Where is the museum?", "How can I get there?", "Is it far from here?", "Thank you very much."], ["A", "B", "C"]),
            S2("问路时正确的英语表达是（　）。", ["Excuse me. How can I get to the science museum?", "Excuse me. How I can get to science museum?", "Excuse me. Where can I get the science museum?", "Excuse me. How can I get science museum the?"]),
        ]),
        ("第3课 综合运用", "综合练习：地点、方位和指路。能根据路线图说清方向和位置。", [
            Q("It's next to the bookstore. 描述的是它的（　）。", "位置", "大小", "颜色", "价格"),
            Q("“Turn right at the cinema, then go straight.”中 then 表示（　）。", "然后", "但是", "因为", "之前"),
            Q("把“The cinema is near the park.”改成问句，应为（　）。", "Where is the cinema?", "What is the cinema?", "Who is near the park?", "Is the cinema a park?"),
            Q("选择语序正确的句子（　）。", "Turn right at the hospital.", "Turn at hospital right.", "Right turn the hospital at.", "At hospital right turn."),
            Q("north / south / east / west 属于（　）。", "方位词", "交通工具", "职业名称", "序数词"),
            Q("“The post office is on Dongfang Street.”中的 on 用于（　）。", "某条街道", "某个月份", "某个节日", "某个时刻"),
            Q("想知道目的地是否很远，可以问（　）。", "Is it far from here?", "Is it here?", "Who is far?", "How old are you?"),
            Q("“It's in front of the school.”中 in front of 表示（　）。", "在……前面", "在……后面", "在……左边", "在……下面"),
            Q("描述路线时，最好按（　）说。", "先后顺序", "从最后一步倒着说", "随机顺序", "只说终点"),
            Q("选择正确的问答搭配（　）。", "Where is the museum shop? — It's near the door.", "Where is the museum shop? — It's near Monday.", "What is the museum shop? — It's near the door.", "How much is the shop? — It's near the door."),
            Q("“Go straight for ten minutes.”的意思是（　）。", "直走十分钟。", "右转十分钟。", "等十分钟。", "走十分钟就到了书店。"),
            Q("到十字路口时，应该（　）。", "看清交通信号再走", "闭着眼睛跑过去", "一直低头看书", "随意穿行"),
            Q("地图上方通常表示的方向是（　）。", "north", "south", "west", "middle"),
            Q("补全对话：— Excuse me. Where is the bookstore? —（　）", "It's next to the hospital.", "I read a book.", "It's a bookstore.", "Yes, please."),
            Q("“Turn left at the crossing.”中的 crossing 是（　）。", "十字路口", "公交车站", "交通灯", "公园大门"),
            Q("别人给你指完路后，你应该（　）。", "表示感谢", "转身就走不理会", "大声抱怨", "假装没听见"),
            Q("“I'm looking for the science museum.”的意思是（　）。", "我正在找科学博物馆。", "我讨厌科学博物馆。", "我住在科学博物馆旁边。", "科学博物馆关门了。"),
            Q("用英语说“它在邮局附近”，应为（　）。", "It's near the post office.", "It's on the post office.", "It's far the post office.", "It near post office."),
            M("可以用来描述位置的有（　）。", ["next to", "in front of", "near", "go straight"], ["A", "B", "C"]),
            M("问去书店的路会用到的句子有（　）。", ["Where is the bookstore?", "How can I get to the bookstore?", "Is it far from here?", "I like reading books."], ["A", "B", "C"]),
            S2("本单元主要学会了（　）。", ["问路、指路并描述地点位置", "介绍自己的爱好", "谈论交通方式", "表达情绪和建议"]),
        ]),
    ]),
    ("第二单元 Ways to go to school", [
        ("第1课 核心词汇", "Today's phrases: on foot / by bus / by plane / by taxi / by ship / by subway / by train / by bike，以及交通灯与安全规则。", build_vocab([
            ("on foot", "步行"), ("by bus", "乘公共汽车"), ("by plane", "乘飞机"),
            ("by taxi", "乘出租车"), ("by ship", "乘船"), ("by subway", "乘地铁"),
            ("by train", "乘火车"), ("by bike", "骑自行车"), ("traffic lights", "交通信号灯"),
            ("traffic rules", "交通规则"), ("slow down", "慢下来"), ("helmet", "头盔"),
        ])),
        ("第2课 句型与对话", "Sentences: How do you come to school? / I come on foot. / Stop and wait at a red light. 学会谈论出行方式并遵守交通规则。", [
            Q("询问“你怎么来上学？”应该说（　）。", "How do you come to school?", "What do you come to school?", "Where do you come to school?", "Who comes to school?"),
            Q("回答“How do you come to school?”可以说（　）。", "I come on foot.", "I come from China.", "It's Monday.", "Yes, I do."),
            Q("表示“乘公共汽车”应说（　）。", "by bus", "by the bus", "with bus", "in bus"),
            Q("表示“步行”应说（　）。", "on foot", "by foot", "with foot", "in foot"),
            Q("“Slow down and stop at a yellow light.”的意思是（　）。", "黄灯时减速停下。", "绿灯时可以通行。", "红灯时快速通过。", "任何灯都要等待。"),
            Q("“Stop and wait at a red light.”的意思是（　）。", "红灯停下等待。", "绿灯停下等待。", "红灯可以快速过。", "红灯可以骑车通过。"),
            Q("绿灯亮时应该（　）。", "go", "stop", "wait", "sleep"),
            Q("“Pay attention to the traffic lights!”的意思是（　）。", "注意交通信号灯！", "请走斑马线！", "欢迎乘坐地铁！", "请系好安全带！"),
            Q("表示“乘地铁”应说（　）。", "by subway", "by the subway", "with subway", "in subway"),
            Q("“The bus is coming!”的意思是（　）。", "公共汽车来了！", "公共汽车走了！", "我要坐地铁。", "公共汽车晚点了。"),
            Q("必须做某事时用情态动词（　）。", "must", "can't", "doesn't", "isn't"),
            Q("禁止做某事时用（　）。", "don't", "do", "does", "must"),
            Q("在美国，孩子骑车时必须戴头盔，头盔的英语是（　）。", "helmet", "seat belt only", "gloves", "school bag"),
            Q("询问“我怎么去动物园？”可以说（　）。", "How can I get to the zoo?", "Who can get to the zoo?", "What can I get to the zoo?", "Do I get to the zoo?"),
            M("属于交通方式的有（　）。", ["by bike", "by train", "on foot", "by book"], ["A", "B", "C"]),
            M("红灯时应该（　）。", ["stop", "wait", "look at the traffic lights", "go quickly"], ["A", "B", "C"]),
            Q("补全对话：— How do you come to school? —（　）", "I come by bike.", "I come from Beijing.", "It's very far.", "Yes, I can."),
            Q("补全句子：I go to Shanghai（　）train.", "by", "on", "with", "at"),
            Q("距离很近时，最环保的出行方式是（　）。", "on foot or by bike", "by plane", "by taxi every day", "by ship"),
            Q("过马路时应该（　）。", "走人行横道并看红绿灯", "低头玩手机", "追赶同学", "在车流中穿行"),
            S2("谈论出行方式，正确的句子是（　）。", ["I usually come to school by bus.", "I usually come to school by the bus.", "I usually by bus come to school.", "I am usually come to school bus."]),
        ]),
        ("第3课 综合运用", "综合练习：交通方式、交通规则和安全习惯。根据不同的距离与情境选择出行方式。", [
            Q("家离学校很近，最适合（　）。", "on foot", "by plane", "by ship", "by train"),
            Q("从中国去美国，最可能（　）。", "by plane", "by bike", "on foot", "by subway"),
            Q("下列哪一个是交通方式短语？（　）。", "by train", "at home", "in the morning", "on the desk"),
            Q("“How do you come to school?”询问的是（　）。", "出行方式", "出发日期", "同行人数", "书包颜色"),
            Q("把“I come to school by bike.”改成问句，应为（　）。", "How do you come to school?", "Who comes to school?", "Do you come school?", "When do you come school?"),
            Q("选择语序正确的句子（　）。", "I come to school on foot.", "I on foot come to school.", "I come to school by the foot.", "On foot I to school come."),
            Q("在城市里，通常最快的公共交通之一是（　）。", "subway", "ship", "bike", "ferry across the sea"),
            Q("坐出租车出行，正确的说法是（　）。", "by taxi", "by a taxi", "with taxi", "in taxi"),
            Q("红灯正在闪烁时，我们应该（　）。", "stop and wait", "run across quickly", "close our eyes", "ride faster"),
            Q("“traffic rules”的意思是（　）。", "交通规则", "交通地图", "交通拥堵", "交通警察"),
            Q("骑行前应该先检查（　）。", "车闸、车铃和轮胎", "书包里的课本数量", "同桌的作业", "教室的窗户"),
            Q("爸爸开车送你上学，你们系安全带，这属于（　）。", "遵守交通规则", "浪费时间", "多余的担心", "只为交警而做"),
            Q("补全对话：— How can I get to the museum? —（　）", "You can take the No. 5 bus.", "It's a nice museum.", "I like museums.", "Yes, please."),
            Q("补全句子：We must（　）at a red light.", "stop", "go", "run", "turn"),
            Q("“Don't run on the ferry!”的意思是（　）。", "别在渡船上奔跑！", "请快点上渡船！", "渡船来了！", "渡船停在那里！"),
            Q("选择绿色出行方式的意义是（　）。", "节约能源并减少污染", "一定最快到达", "能不用遵守规则", "可以随意停车"),
            M("出行要注意的安全事项有（　）。", ["wear a helmet", "follow the traffic rules", "pay attention to the traffic lights", "run across the street"], ["A", "B", "C"]),
            M("属于交通方式的短语有（　）。", ["by ship", "by subway", "by plane", "by heart"], ["A", "B", "C"]),
            Q("下列哪句同时包含出行方式和目的地？（　）", "I go to the park by bike.", "I like my bike.", "The bus is red.", "How do you do?"),
            S2("本单元主要学会了（　）。", ["谈论出行方式并遵守交通规则", "描述地点位置", "介绍笔友的爱好", "表达自己的情绪"]),
        ]),
    ]),
    ("第三单元 My weekend plan", [
        ("第1课 核心词汇", "Today's phrases: visit my grandparents / see a film / take a trip / go to the supermarket，以及时间与读物类单词。", build_vocab([
            ("visit my grandparents", "看望祖父母"), ("see a film", "看电影"), ("take a trip", "去旅行"),
            ("go to the supermarket", "去超市"), ("tomorrow", "明天"), ("tonight", "今晚"),
            ("next week", "下周"), ("dictionary", "词典"), ("comic book", "漫画书"),
            ("word book", "单词本"), ("postcard", "明信片"),
        ])),
        ("第2课 句型与对话", "Sentences: What are you going to do? / I'm going to see a film. 学会用 be going to 谈论周末计划。", [
            Q("询问“你打算做什么？”应该说（　）。", "What are you going to do?", "What do you do?", "What did you do?", "Where are you going to do?"),
            Q("回答“What are you going to do this weekend?”可以说（　）。", "I'm going to visit my grandparents.", "I visited my grandparents.", "I visit every Sunday.", "Yes, I am."),
            Q("“I'm going to see a film tonight.”的意思是（　）。", "我今晚打算看电影。", "我昨晚看了电影。", "我喜欢看电影。", "我正在电影院工作。"),
            Q("be going to 通常表示（　）。", "打算；将要", "正在发生", "过去发生", "每天发生"),
            Q("表示“明天”的单词是（　）。", "tomorrow", "tonight", "yesterday", "now"),
            Q("表示“今晚”的单词是（　）。", "tonight", "tomorrow", "morning", "last night"),
            Q("“next week”的意思是（　）。", "下周", "上周", "这周每天", "周末"),
            Q("想买一本词典，应该说（　）。", "I'm going to buy a dictionary.", "I buyed a dictionary.", "I going buy dictionary.", "I am buy a dictionary."),
            Q("postcard 的意思是（　）。", "明信片", "邮票", "信封", "报纸"),
            Q("comic book 的意思是（　）。", "漫画书", "教科书", "杂志架", "笔记本"),
            Q("补全句子：I'm going（　）visit my grandparents tomorrow.", "to", "too", "two", "of"),
            Q("询问对方打算什么时候去，可以说（　）。", "When are you going?", "What are you going?", "Where are you going to?", "Who is going to?"),
            Q("“What are you going to do this evening?”的同义时间词可以是（　）。", "tonight", "tomorrow morning", "next week", "yesterday"),
            Q("回答“When are you going?”可以说（　）。", "This afternoon.", "To the cinema.", "I'm going to read.", "Yes, I do."),
            Q("“Sounds great!”用于（　）。", "赞同对方的计划", "询问时间", "表达歉意", "告别"),
            M("周末活动可以有（　）。", ["see a film", "take a trip", "visit my grandparents", "have a maths test"], ["A", "B", "C"]),
            M("表示将来时间的词有（　）。", ["tomorrow", "tonight", "next week", "yesterday"], ["A", "B", "C"]),
            Q("“I'm going to the supermarket.”中的 supermarket 是（　）。", "超市", "博物馆", "车站", "图书馆"),
            Q("制定周末计划时应（　）。", "先安排重要的事再安排娱乐", "只玩不休息", "完全不做安排", "临时熬夜完成"),
            Q("“This weekend is going to be busy.”的意思是（　）。", "这个周末会很忙碌。", "这个周末很清闲。", "上周很忙碌。", "周末已经结束了。"),
            S2("谈论周末计划，正确的句子是（　）。", ["I'm going to take a trip next week.", "I going to take trip next week.", "I am take a trip next week.", "I'm going take a trip next week."]),
        ]),
        ("第3课 综合运用", "综合练习：be going to 句型、时间状语和周末活动安排。读懂日程并合理安排时间。", [
            Q("“I'm going to read a comic book tonight.”中的 going to 表示（　）。", "打算", "正在", "已经", "每天"),
            Q("be going to 后面通常接（　）。", "动词原形", "动词过去式", "动词-ing", "名词复数"),
            Q("把“I'm going to see a film.”改成问句，应为（　）。", "What are you going to do?", "What do you do?", "Did you see a film?", "How are you going to do?"),
            Q("选择语序正确的句子（　）。", "I'm going to visit my grandparents tomorrow.", "I going to tomorrow visit my grandparents.", "I'm going visit my grandparents to tomorrow.", "Tomorrow I'm going visit to grandparents."),
            Q("“What are you going to do next week?”询问的是（　）。", "将来的计划", "过去的经历", "现在的动作", "别人的爱好"),
            Q("今天周五，说“tomorrow”指的是（　）。", "Saturday", "Thursday", "Monday", "Sunday"),
            Q("想表达“我打算明天去超市”，应选（　）。", "I'm going to the supermarket tomorrow.", "I go supermarket tomorrow.", "I'm going supermarket at tomorrow.", "I tomorrow going to supermarket."),
            Q("买了一本词典，可能打算（　）。", "查单词学习英语", "寄给远方的朋友做礼物", "当作电影票", "记录交通规则"),
            Q("给朋友写明信片时需要注意（　）。", "写清地址并贴邮票", "只写自己的名字", "不使用邮政编码", "随便丢进河里"),
            Q("“I have to do my homework first.”中的 first 表示（　）。", "首先", "最后", "一次", "第一的"),
            Q("下列哪句同时包含活动和将来时间？（　）", "I'm going to take a trip next week.", "I take a trip every year.", "The trip is fun.", "Next week is far."),
            Q("制定计划时，应该把作业安排在（　）。", "娱乐活动之前", "娱乐活动之后", "深夜才做", "完全不做"),
            Q("补全对话：— What are you going to do tonight? —（　）", "I'm going to see a film.", "I saw a film.", "I like films.", "Yes, I am."),
            Q("补全句子：She is going to buy a word book（　）", "tomorrow.", "yesterday.", "last week.", "ago."),
            Q("“Have a good time!”用于（　）。", "祝对方玩得愉快", "询问对方去向", "请求对方帮忙", "表达歉意"),
            Q("word book 最适合用来（　）。", "积累英语单词", "看漫画故事", "写明信片", "查公交线路"),
            M("可以和 this weekend 搭配的计划有（　）。", ["I'm going to see a film.", "I'm going to visit my grandparents.", "I'm going to take a trip.", "I saw a film yesterday."], ["A", "B", "C"]),
            M("属于将来时间状语的有（　）。", ["tomorrow", "tonight", "next week", "last night"], ["A", "B", "C"]),
            Q("“My weekend plan is full.”的意思是（　）。", "我的周末安排很满。", "我的周末很空。", "我的计划取消了。", "我不喜欢周末。"),
            S2("本单元主要学会了（　）。", ["用 be going to 谈论周末计划和安排", "问路与指路", "描述他人的职业", "表达自己的情绪和建议"]),
        ]),
    ]),
    ("第四单元 I have a pen pal", [
        ("第1课 核心词汇", "Today's words: dancing / singing / reading stories / playing football / doing kung fu，以及第三人称单数形式的爱好表达。", build_vocab([
            ("dancing", "跳舞"), ("singing", "唱歌"), ("reading stories", "读故事"),
            ("playing football", "踢足球"), ("doing kung fu", "练功夫"),
            ("cooks Chinese food", "做中国菜"), ("studies Chinese", "学习汉语"),
            ("does word puzzles", "猜字谜"), ("goes hiking", "去远足"),
            ("hobby", "爱好"), ("pen pal", "笔友"), ("lives in", "住在"),
        ])),
        ("第2课 句型与对话", "Sentences: What's your hobby? / I like reading stories. / Does he live in Shanghai? Yes, he does. 学会介绍爱好并了解他人。", [
            Q("询问“你的爱好是什么？”应该说（　）。", "What's your hobby?", "What do you have?", "Who is your hobby?", "Where is your hobby?"),
            Q("回答“What's your hobby?”可以说（　）。", "I like reading stories.", "I have a hobby.", "It's a story.", "Yes, I like."),
            Q("“I like playing football.”的意思是（　）。", "我喜欢踢足球。", "我正在踢足球。", "我有足球。", "足球是我的。"),
            Q("like 后面常接（　）。", "动词-ing 形式", "动词过去式", "序数词", "介词短语"),
            Q("询问“他住在上海吗？”应该说（　）。", "Does he live in Shanghai?", "Do he live in Shanghai?", "Is he live in Shanghai?", "Does he lives in Shanghai?"),
            Q("“Does he live in Shanghai?”的肯定回答是（　）。", "Yes, he does.", "Yes, he is.", "Yes, he do.", "Yes, he live."),
            Q("“Does she teach English?”的否定回答是（　）。", "No, she doesn't.", "No, she isn't.", "No, she don't.", "No, she not."),
            Q("动词 study 的第三人称单数形式是（　）。", "studies", "studys", "study", "studied"),
            Q("动词 go 的第三人称单数形式是（　）。", "goes", "gos", "going", "goed"),
            Q("动词 do 的第三人称单数形式是（　）。", "does", "dos", "doing", "doed"),
            Q("dancing 的原形是（　）。", "dance", "danced", "dances", "dancing more"),
            Q("pen pal 的意思是（　）。", "笔友", "钢笔", "网友的城市", "表兄弟"),
            Q("hobby 的复数形式是（　）。", "hobbies", "hobbys", "hobbyes", "hobby"),
            Q("给外国笔友写信时，可能会提到（　）。", "my hobbies and my city", "my taxi number", "my health record", "my bank card"),
            M("可以回答“What's your hobby?”的有（　）。", ["I like singing.", "I like doing kung fu.", "I like reading stories.", "I am ten years old."], ["A", "B", "C"]),
            M("第三人称单数形式正确的有（　）。", ["studies", "does", "goes", "study"], ["A", "B", "C"]),
            Q("补全对话：— What's your hobby? —（　）", "I like playing football.", "I play football yesterday.", "It's a football.", "Yes, I do."),
            Q("补全句子：He（　）in Beijing.", "lives", "live", "living", "lived in"),
            Q("了解他人爱好时，应该（　）。", "认真倾听并互相尊重", "嘲笑不同的爱好", "强迫别人改变", "只谈自己的爱好"),
            Q("“I like writing emails to my pen pal.”的意思是（　）。", "我喜欢给笔友写电子邮件。", "我喜欢收到明信片。", "笔友给我打电话。", "我在学写汉字。"),
            S2("介绍爱好，正确的句子是（　）。", ["My hobby is reading stories.", "My hobby reading stories.", "My hobby is read stories.", "My hobby are reading stories."]),
        ]),
        ("第3课 综合运用", "综合练习：爱好表达、第三人称单数和一般现在时疑问句。读懂人物介绍并进行问答。", [
            Q("“She likes singing.”中的 likes 是因为主语是（　）。", "第三人称单数", "第一人称", "复数人称", "过去时间"),
            Q("“They like doing kung fu.”中的 like 用原形是因为主语是（　）。", "复数", "第三人称单数", "不可数名词", "单数不可数"),
            Q("把“I like reading stories.”改成否定句，应为（　）。", "I don't like reading stories.", "I not like reading stories.", "I doesn't like reading stories.", "I am not like reading stories."),
            Q("把“He likes playing football.”改成疑问句，应为（　）。", "Does he like playing football?", "Do he like playing football?", "Is he like playing football?", "Does he likes playing football?"),
            Q("选择语序正确的句子（　）。", "What is your hobby?", "What your hobby is?", "Your hobby what is?", "Is what your hobby?"),
            Q("“My pen pal goes hiking every weekend.”中的 every weekend 表示（　）。", "经常性动作", "过去的一次动作", "将来的计划", "正在进行的动作"),
            Q("动词 swim 变 -ing 形式应为（　）。", "swimming", "swiming", "swims", "swam"),
            Q("动词 make 变 -ing 形式应为（　）。", "making", "makeing", "makes", "made"),
            Q("“My hobby is cooking Chinese food.”中的 cooking 是（　）。", "动名词", "过去式", "第三人称单数", "序数词"),
            Q("小张喜欢踢足球，用英语应说（　）。", "He likes playing football.", "He like playing football.", "He likes play football.", "He is like football."),
            Q("想知道对方是否喜欢练功夫，可以问（　）。", "Do you like doing kung fu?", "Are you like doing kung fu?", "Does you like doing kung fu?", "You like doing kung fu?"),
            Q("“I also like reading.”中 also 表示（　）。", "也", "但是", "从不", "只有"),
            M("爱好类活动可以有（　）。", ["singing", "dancing", "reading stories", "turning left"], ["A", "B", "C"]),
            M("下列句子语法正确的有（　）。", ["He studies Chinese.", "She goes hiking.", "My hobby is drawing.", "He study Chinese."], ["A", "B", "C"]),
            Q("给笔友介绍自己时，通常包括（　）。", "姓名、年龄、爱好和居住地", "银行卡号和密码", "他人的隐私", "别人的家庭住址"),
            Q("结交笔友的意义是（　）。", "了解不同文化并提高英语", "炫耀物品", "打听别人秘密", "逃避学习"),
            Q("“We have the same hobby.”的意思是（　）。", "我们有相同的爱好。", "我们有相同的年龄。", "我们住在同一个城市。", "我们喜欢互相争吵。"),
            Q("写英文自我介绍时，应该（　）。", "语句简短真实", "夸大虚构经历", "泄露家庭隐私", "随意抄写他人信息"),
            Q("下列哪句同时包含主语和爱好？（　）", "My pen pal likes reading stories.", "Reading stories is fun.", "I have a pen pal.", "Where is your pen pal?"),
            S2("本单元主要学会了（　）。", ["介绍爱好并用第三人称单数谈论他人", "问路和指路", "制定周末计划", "说明交通规则"]),
        ]),
    ]),
    ("第五单元 What does he do", [
        ("第1课 核心词汇", "Today's words: factory worker / postman / businessman / police officer / fisherman / scientist / pilot / coach。学会说常见职业。", build_vocab([
            ("factory worker", "工厂工人"), ("postman", "邮递员"), ("businessman", "商人"),
            ("police officer", "警察"), ("fisherman", "渔民"), ("scientist", "科学家"),
            ("pilot", "飞行员"), ("coach", "教练"), ("head teacher", "校长"),
            ("university", "大学"), ("country", "国家"), ("sea", "大海"),
        ])),
        ("第2课 句型与对话", "Sentences: What does he do? / He's a businessman. / Where does she work? 学会询问职业和工作地点。", [
            Q("询问“他是做什么的？”应该说（　）。", "What does he do?", "What is he do?", "What do he does?", "Who does he do?"),
            Q("回答“What does he do?”可以说（　）。", "He's a businessman.", "He's my uncle.", "He is tall.", "Yes, he does."),
            Q("询问“她在哪里工作？”应该说（　）。", "Where does she work?", "Where she works?", "What does she work?", "Where does she works?"),
            Q("police officer 的意思是（　）。", "警察", "邮递员", "消防员", "司机"),
            Q("每天在大海上捕鱼的人是（　）。", "fisherman", "postman", "coach", "pilot"),
            Q("在实验室做研究的人是（　）。", "scientist", "businessman", "postman", "worker"),
            Q("开飞机的人是（　）。", "pilot", "coach", "fisherman", "police officer"),
            Q("在工厂里工作的人是（　）。", "factory worker", "head teacher", "postman", "scientist"),
            Q("负责一所学校的人是（　）。", "head teacher", "businessman", "pilot", "fisherman"),
            Q("送信件和报纸的人是（　）。", "postman", "coach", "scientist", "police officer"),
            Q("教运动员训练的人是（　）。", "coach", "postman", "fisherman", "businessman"),
            Q("“My mother is a police officer.”的意思是（　）。", "我妈妈是警察。", "我爸爸经商。", "我妈妈在学校工作。", "我妈妈喜欢警察局。"),
            Q("补全句子：What（　）your father do?", "does", "do", "is", "are"),
            Q("介绍男性的父亲时，人称代词要用（　）。", "he", "she", "it", "they"),
            M("属于职业名称的有（　）。", ["scientist", "pilot", "coach", "bookstore"], ["A", "B", "C"]),
            M("可以回答“Where does she work?”的有（　）。", ["She works in a hospital.", "She works at a university.", "She works at sea.", "She is a doctor."], ["A", "B", "C"]),
            Q("补全对话：— What does your uncle do? —（　）", "He's a pilot.", "He flies.", "He's my father's brother.", "Yes, he is."),
            Q("“I want to be a scientist.”的意思是（　）。", "我想成为一名科学家。", "我想去大学。", "我喜欢科学课。", "我有一本科学书。"),
            Q("谈论父母职业时应（　）。", "尊重每一种劳动", "比较职业高低贵贱", "嫌弃体力劳动", "隐瞒不说"),
            Q("“He works very hard.”中 hard 表示（　）。", "努力地", "坚硬地", "困难的问题", "几乎不"),
            S2("询问职业，正确的句子是（　）。", ["What does your mother do?", "What do your mother do?", "What does your mother does?", "What your mother does do?"]),
        ]),
        ("第3课 综合运用", "综合练习：职业名称、第三人称单数疑问句和工作地点。读懂人物卡片并介绍家人。", [
            Q("在医院工作、照顾病人的可能是（　）。", "doctor or nurse", "pilot", "fisherman", "postman"),
            Q("“My father works at sea.”他最可能是（　）。", "fisherman", "head teacher", "businessman", "coach"),
            Q("把“He is a coach.”改成问句，应为（　）。", "What does he do?", "What is he do?", "Where does he do?", "Does he do what?"),
            Q("把“She works in a university.”改成问句，应为（　）。", "Where does she work?", "What does she work?", "When does she work?", "Who does she work?"),
            Q("选择语序正确的句子（　）。", "What does your aunt do?", "What your aunt does do?", "What does your aunt does?", "Does what your aunt do?"),
            Q("一般现在时第三人称单数的助动词是（　）。", "does", "do", "did", "is"),
            Q("在“Does she work here?”中，动词 work 要用（　）。", "原形", "第三人称单数形式", "过去式", "-ing 形式"),
            Q("“Head teacher”在学校里负责（　）。", "管理全校工作", "只负责送报纸", "只在食堂做饭", "驾驶校车"),
            Q("想成为飞行员，需要（　）。", "学好知识并保持身体健康", "每天睡懒觉", "害怕乘飞机", "从不上课"),
            Q("“My mother is a businesswoman.”中的 businesswoman 指（　）。", "女商人", "女警察", "女教师", "女医生"),
            Q("worker 是在动词 work 后面加上（　）构成的。", "-er", "-or", "-ing", "-ed"),
            M("描述职业的句子正确的有（　）。", ["He is a scientist.", "She works in a hospital.", "My uncle is a fisherman.", "He are a pilot."], ["A", "B", "C"]),
            M("属于工作地点或场所的有（　）。", ["university", "factory", "sea", "homework"], ["A", "B", "C"]),
            Q("介绍家庭成员职业时，一般先说（　）。", "家人称谓和职业名称", "银行存款", "同事的电话", "别人的住址"),
            Q("补全对话：— Where does your father work? —（　）", "He works in a factory.", "He's a worker.", "It's a factory.", "Yes, he does."),
            Q("各种职业的共同点是（　）。", "都在为社会作贡献", "都必须天天出差", "都需要开飞机", "都只在白天工作"),
            Q("“What do you want to be?”的意思是（　）。", "你将来想做什么？", "你现在在做什么？", "你昨天做了什么？", "你住在哪儿？"),
            Q("选择职业时主要应考虑（　）。", "兴趣、能力与社会需要", "只看收入多少", "只看是否轻松", "盲从他人"),
            Q("下列哪句同时包含职业和工作地点？（　）", "My aunt is a scientist, and she works in a university.", "My aunt likes science.", "Science is interesting.", "Where is the university?"),
            Q("劳动教育告诉我们，每一份职业都（　）。", "值得尊重", "有贵贱之分", "不需要学习", "只能由成年人做"),
            S2("本单元主要学会了（　）。", ["询问并介绍职业及工作地点", "介绍爱好", "问路和指路", "表达情绪和建议"]),
        ]),
    ]),
    ("第六单元 How do you feel", [
        ("第1课 核心词汇", "Today's words: angry / afraid / sad / worried / happy，以及调节情绪的建议类短语。", build_vocab([
            ("angry", "生气的"), ("afraid", "害怕的"), ("sad", "难过的"),
            ("worried", "担心的"), ("happy", "高兴的"), ("wear warm clothes", "穿暖和的衣服"),
            ("take a deep breath", "深深吸一口气"), ("see a doctor", "看病"),
            ("do more exercise", "多锻炼"), ("chase", "追赶"), ("mouse", "老鼠"), ("should", "应该"),
        ])),
        ("第2课 句型与对话", "Sentences: How do you feel? / Why? Because … / You should take a deep breath. 学会表达情绪并给出建议。", [
            Q("询问“你感觉怎么样？”应该说（　）。", "How do you feel?", "What do you feel?", "Who are you feel?", "Where do you feel?"),
            Q("回答“How do you feel?”可以说（　）。", "I'm happy.", "I'm ten.", "It's a cat.", "Yes, I do."),
            Q("询问原因应该说（　）。", "Why?", "When?", "Where?", "Whose?"),
            Q("回答“Why are you sad?”可以说（　）。", "Because I lost my book.", "So I'm sad.", "Yes, I am.", "At school."),
            Q("angry 的意思是（　）。", "生气的", "害怕的", "高兴的", "疲倦的"),
            Q("afraid 的意思是（　）。", "害怕的", "生气的", "忙碌的", "安静的"),
            Q("worried 的意思是（　）。", "担心的", "快乐的", "强壮的", "饥饿的"),
            Q("给别人提建议时常用情态动词（　）。", "should", "does", "did", "will not"),
            Q("“Take a deep breath.”的意思是（　）。", "深深吸一口气。", "快一点跑。", "把手举起来。", "大声唱歌。"),
            Q("“You should see a doctor.”的意思是（　）。", "你应该去看病。", "你应该去上班。", "你应该多吃饭。", "你应该多喝水才对。"),
            Q("天气很冷时，朋友会建议你（　）。", "wear warm clothes", "take off your coat", "drink ice water", "run in the rain"),
            Q("身体虚弱时，医生可能建议（　）。", "do more exercise", "eat more candy only", "sleep all day every day", "watch TV all night"),
            Q("“Don't be afraid.”的意思是（　）。", "别害怕。", "别生气。", "别难过。", "别担心钱包。"),
            Q("because 用来说明（　）。", "原因", "时间", "地点", "人物"),
            M("属于情绪感受的词有（　）。", ["angry", "afraid", "worried", "taxi"], ["A", "B", "C"]),
            M("感冒或生病时可以的建议有（　）。", ["see a doctor", "drink more water", "have a good rest", "run in the rain"], ["A", "B", "C"]),
            Q("补全对话：— I'm angry. What should I do? —（　）", "Take a deep breath and count to ten.", "Go to bed at midnight.", "Eat more ice cream.", "Run away quickly."),
            Q("补全句子：He is（　）of the dog.", "afraid", "happy about", "angry at", "worried to"),
            Q("朋友感到难过时，你应该（　）。", "安慰并询问原因", "嘲笑他的情绪", "不理不睬", "学他一起哭叫"),
            Q("“How does she feel?”的回答是（　）。", "She feels worried.", "She feel worried.", "She is feel sad.", "She does worried."),
            S2("表达情绪与建议，正确的句子是（　）。", ["I feel sad. What should I do?", "I feel sad. What I should do?", "I am feel sad. What should I?", "Sad I feel, should what do?"]),
        ]),
        ("第3课 综合运用", "综合练习：情绪表达、原因说明和调节建议。根据具体情境选择合适的表达与做法。", [
            Q("考试没考好，可能感到（　）。", "sad", "happy", "excited about everything", "hungry only"),
            Q("被同学误会时，可能感到（　）。", "angry", "afraid of nothing", "sleepy", "taller"),
            Q("夜里听到奇怪的声音，可能感到（　）。", "afraid", "happy", "worried about food", "strong"),
            Q("“Why are you worried?”的最合适回答是（　）。", "Because I have a maths test tomorrow.", "Because it is yesterday.", "So I am ten.", "At the zoo."),
            Q("把“I feel angry.”改成疑问句，应为（　）。", "How do you feel?", "What do you feel?", "Do you feel how?", "How you do feel?"),
            Q("选择语序正确的句子（　）。", "You should take a deep breath.", "You should takes a deep breath.", "You should taking deep breath.", "You to should take deep breath."),
            Q("想劝同伴不要担心，可以说（　）。", "Don't worry.", "Don't worried.", "Not worry.", "Doesn't worry."),
            Q("“My mother is ill. I'm worried.”中 worried 表示（　）。", "担心", "生气", "害羞", "骄傲"),
            Q("生气时比较好的做法是（　）。", "深呼吸并冷静沟通", "大喊大叫", "摔东西", "迁怒别人"),
            Q("天冷容易感冒，可以预防的办法是（　）。", "wear warm clothes", "wear a T-shirt only", "play in the rain", "drink cold water only"),
            Q("long face、cry 等常常说明一个人（　）。", "不开心", "很兴奋", "很健康", "很忙碌"),
            Q("“Do more exercise, and you'll be strong.”中的 strong 表示（　）。", "强壮的", "聪明的", "年轻的", "安静的"),
            Q("好朋友一直很担心，你可以说（　）。", "Don't worry. Everything will be fine.", "Go away.", "It's none of my business.", "Worry more, please."),
            M("有助于保持愉快心情的做法有（　）。", ["do more exercise", "listen to music", "talk with friends", "shout at everyone"], ["A", "B", "C"]),
            M("你觉得冷时可以做的有（　）。", ["wear warm clothes", "drink some hot water", "close the window", "take off the coat"], ["A", "B", "C"]),
            Q("补全对话：— You look worried. What's wrong? —（　）", "I can't find my dog.", "I am ten years old.", "It's Monday.", "Yes, I can."),
            Q("别人向你倾诉烦恼时，首先应该（　）。", "认真倾听", "马上打断", "到处传播", "冷嘲热讽"),
            Q("情绪没有好坏之分，关键是（　）。", "用合理的方式表达和调节", "完全忍住不说", "随意发泄给别人", "永远假装没事"),
            Q("下列哪句同时包含情绪和建议？（　）", "I'm ill. I should see a doctor.", "I'm ill today.", "Doctors are busy.", "Where is the hospital?"),
            S2("本单元主要学会了（　）。", ["表达情绪、说明原因并给出合理建议", "介绍职业和工作地点", "问路和指路", "谈论爱好"]),
        ]),
    ]),
    ("复习与检测", [
        ("第1课 Revision 1", "Revision 1: Units 1–3。复习地点指路、交通方式和周末计划。", build_vocab([
            ("science museum", "科学博物馆"), ("post office", "邮局"), ("turn right", "右转"),
            ("on foot", "步行"), ("by subway", "乘地铁"), ("traffic lights", "交通信号灯"),
            ("see a film", "看电影"), ("take a trip", "去旅行"), ("tomorrow", "明天"),
            ("postcard", "明信片"),
        ])),
        ("第2课 Revision 2", "Revision 2: Units 4–6。复习爱好、职业、情绪表达与建议。", build_vocab([
            ("reading stories", "读故事"), ("does word puzzles", "猜字谜"), ("pen pal", "笔友"),
            ("scientist", "科学家"), ("police officer", "警察"), ("university", "大学"),
            ("afraid", "害怕的"), ("worried", "担心的"), ("see a doctor", "看病"),
            ("do more exercise", "多锻炼"),
        ])),
    ]),
]


if __name__ == "__main__":
    run(r"content/primary/pep/grade6/volume1/english", "英语上册", UNITS)
