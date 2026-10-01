# -*- coding: utf-8 -*-
"""人教版 PEP 五年级下册英语全部单元交互自测题生成脚本。"""
import random

from _quizlib import S, S2, M, run


RNG = random.Random(20261001)


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
    ("第一单元 My day", [
        ("第1课 核心词汇", "Today's phrases: eat breakfast / have English class / play sports / eat dinner。用英语介绍一天的作息。", build_vocab([
            ("when", "什么时候；何时"), ("eat breakfast", "吃早饭"),
            ("have English class", "上英语课"), ("play sports", "进行体育运动"),
            ("eat dinner", "吃晚饭"), ("do morning exercises", "做早操"),
            ("clean my room", "打扫我的房间"), ("go for a walk", "散步"),
            ("go shopping", "去买东西；购物"), ("take a dancing class", "上舞蹈课"),
        ])),
        ("第2课 句型与对话", "Sentences: When do you eat breakfast? / What do you do on the weekend? 谈论日常作息和周末活动。", [
            Q("询问“你什么时候吃早饭？”应该说（　）。", "When do you eat breakfast?", "What do you eat for breakfast?", "Where do you eat breakfast?", "Do you eat breakfast?"),
            Q("回答“When do you get up?”可以说（　）。", "At 6:30.", "I get up.", "It's breakfast.", "Yes, I do."),
            Q("“I usually eat dinner at 7 o'clock.”的意思是（　）。", "我通常七点吃晚饭。", "我通常七点吃早饭。", "我七点上英语课。", "我每天七点起床。"),
            Q("询问“你周末做什么？”应该说（　）。", "What do you do on the weekend?", "When is the weekend?", "What do you have on weekends?", "Do you like the weekend?"),
            Q("回答“What do you do on the weekend?”可以说（　）。", "I often clean my room.", "At eight o'clock.", "It's Saturday.", "Yes, I am."),
            Q("“I sometimes go shopping with my mum.”的意思是（　）。", "我有时和妈妈去购物。", "我总是独自购物。", "妈妈每天去散步。", "我和妈妈上舞蹈课。"),
            Q("表示“我经常进行体育运动”应说（　）。", "I often play sports.", "I often have sports.", "I am often sports.", "I plays sports often."),
            Q("表示具体钟点前通常用介词（　）。", "at", "on", "in", "for"),
            Q("“usually”的意思是（　）。", "通常地；惯常地", "从不", "现在", "很少"),
            Q("“sometimes”的意思是（　）。", "有时", "总是", "从不", "每天"),
            Q("“I go for a walk after dinner.”的意思是（　）。", "我晚饭后去散步。", "我散步后吃晚饭。", "我晚饭后去购物。", "我早饭前去散步。"),
            Q("询问同伴几点上英语课，可以说（　）。", "When do you have English class?", "What do you have English class?", "Where is English class?", "Do you English class?"),
            M("日常作息活动有（　）。", ["eat breakfast", "have class", "eat dinner", "January"], ["A", "B", "C"]),
            M("周末可以合理安排的活动有（　）。", ["clean my room", "go shopping", "take a dancing class", "stay up all night"], ["A", "B", "C"]),
            Q("补全对话：— When do you play sports? —（　）", "At 4:30 p.m.", "I play sports.", "On the playground.", "Yes, I do."),
            Q("补全句子：I（　）morning exercises at 7:00.", "do", "does", "am", "doing"),
            Q("“Why are you shopping today?”中的 why 用来询问（　）。", "原因", "时间", "地点", "人物"),
            Q("“That sounds like a lot of fun.”的意思是（　）。", "那听起来很有趣。", "那听起来很累。", "那看起来很远。", "那是一节课。"),
            Q("“I often watch TV, too.”中 too 表示（　）。", "也", "但是", "从不", "首先"),
            Q("询问作息时间时，回答要包含（　）。", "具体时间", "季节", "月份", "物主代词"),
            S2("描述自己的作息，正确的句子是（　）。", ["I get up at 7 o'clock.", "I gets up at 7 o'clock.", "I get up on 7 o'clock.", "I am get up at 7."]),
        ]),
        ("第3课 综合运用", "综合练习：作息时间、频率词和周末安排。读懂日程表并养成规律生活习惯。", [
            Q("日程表写着“7:00 eat breakfast”，应说（　）。", "I eat breakfast at 7:00.", "I eat dinner at 7:00.", "I have breakfast on 7:00.", "At breakfast I seven."),
            Q("“At 9:30 p.m.”最可能回答（　）。", "When do you go to bed?", "What do you do on Sundays?", "Where is your bed?", "Do you sleep?"),
            Q("选择正确的问答搭配（　）。", "When do you eat dinner? — At 6:30.", "When do you eat dinner? — Rice.", "What do you do on Sundays? — At 9:00.", "Do you play sports? — On Monday."),
            Q("把“I play sports at 4:00.”改为一般疑问句，应为（　）。", "Do you play sports at 4:00?", "Are you play sports at 4:00?", "Can you playing sports at 4:00?", "Do you plays sports at 4:00?"),
            Q("“I always get up early.”中 always 表示（　）。", "总是", "有时", "通常", "从不"),
            Q("“I often clean my room on Saturdays.”包含的信息是（　）。", "活动、频率和时间", "只有活动", "只有时间", "只有地点"),
            Q("选择语序正确的句子（　）。", "What do you do on the weekend?", "What you do on the weekend?", "What do on the weekend you?", "On the weekend what you do?"),
            Q("想说“我周日上舞蹈课”，应选（　）。", "I take a dancing class on Sundays.", "I take dancing class at Sundays.", "I am a dancing class Sunday.", "I takes a dancing class on Sunday."),
            Q("“go for a walk”适合安排在（　）。", "饭后休息时", "上课考试时", "深夜不睡时", "吃饭过程中"),
            Q("“clean my room”中的 my 表示（　）。", "我的", "你的", "他的", "我们的"),
            M("下列句子语法正确的有（　）。", ["I eat breakfast at 7:00.", "I often play sports.", "When do you get up?", "I gets up early."], ["A", "B", "C"]),
            M("健康的作息习惯有（　）。", ["get up on time", "eat breakfast", "play sports", "go to bed very late every day"], ["A", "B", "C"]),
            Q("“On Sundays, I usually go shopping.”句首 On Sundays 后用逗号是为了（　）。", "分开时间状语和主句", "表示疑问", "表示所有格", "替代句号"),
            Q("在第三人称“She often ...”中，clean 要变为（　）。", "cleans", "clean", "cleaning", "cleaned"),
            Q("“My weekend is busy.”的意思是（　）。", "我的周末很忙碌。", "我的工作日很忙。", "我周末很无聊。", "我没有周末。"),
            Q("如果 8:00 上课，合理做法是（　）。", "提前起床并吃好早饭", "8:00 才起床", "不吃早饭", "一直看电视"),
            Q("“What do you do?”有时询问活动，而“When do you do it?”询问（　）。", "活动发生的时间", "活动地点", "活动原因", "活动人物"),
            Q("想表达两个周末活动，可以用（　）连接。", "and", "at", "when", "whose"),
            Q("制定作息表的作用是（　）。", "合理安排学习、运动和休息", "把所有时间用来玩", "取消睡眠", "每天安排完全不同"),
            Q("下列哪句同时含时间点和活动？（　）", "I do morning exercises at 6:30.", "I like mornings.", "It's 6:30.", "Morning exercises are good."),
            S2("本单元主要学会了（　）。", ["询问和介绍日常作息与周末活动", "谈论季节", "询问节日月份", "描述物品归属"]),
        ]),
    ]),
    ("第二单元 My favourite season", [
        ("第1课 核心词汇", "Today's words: spring / summer / autumn / winter / season，以及不同季节的典型活动。", build_vocab([
            ("spring", "春天"), ("summer", "夏天"), ("autumn", "秋天"), ("winter", "冬天"),
            ("season", "季节"), ("pick apples", "摘苹果"), ("go swimming", "去游泳"),
            ("make a snowman", "堆雪人"), ("go on a picnic", "去野餐"), ("plant flowers", "种花"),
        ])),
        ("第2课 句型与对话", "Sentences: Which season do you like best? / Why? Because I like summer vacation. 谈谈最喜欢的季节。", [
            Q("询问“你最喜欢哪个季节？”应该说（　）。", "Which season do you like best?", "What is the season?", "When is your season?", "Do you have seasons?"),
            Q("回答“Which season do you like best?”可以说（　）。", "I like spring best.", "It is spring now.", "Spring is warm.", "Yes, I like."),
            Q("询问喜欢某季节的原因，可以说（　）。", "Why?", "When?", "Where?", "Whose?"),
            Q("回答“Why do you like summer?”可以说（　）。", "Because I can go swimming.", "So I like summer.", "At summer.", "Summer is July."),
            Q("“I like autumn best.”的意思是（　）。", "我最喜欢秋天。", "我也喜欢秋天。", "秋天最好吗？", "我最喜欢春天。"),
            Q("“Because the colours are pretty.”的意思是（　）。", "因为颜色很漂亮。", "因为天气很冷。", "因为可以游泳。", "因为有许多雪。"),
            Q("春天常见的活动是（　）。", "plant flowers", "make a snowman", "pick apples", "play in the snow"),
            Q("夏天常见的活动是（　）。", "go swimming", "make a snowman", "pick apples", "plant trees in snow"),
            Q("秋天常见的活动是（　）。", "pick apples", "go swimming in ice", "make a snowman", "wear a winter coat"),
            Q("冬天常见的活动是（　）。", "make a snowman", "go swimming outdoors every day", "pick spring flowers", "eat autumn apples only"),
            Q("“What's the weather like in spring?”可以回答（　）。", "It's warm.", "It's spring.", "I like spring.", "Because it's pretty."),
            Q("“There are beautiful flowers everywhere.”的意思是（　）。", "到处都有美丽的花。", "花都凋谢了。", "这里有很多雪。", "花只在房间里。"),
            M("属于季节名称的有（　）。", ["spring", "summer", "winter", "January"], ["A", "B", "C"]),
            M("可以回答“Why do you like autumn?”的有（　）。", ["Because the weather is cool.", "Because I can pick apples.", "Because the colours are pretty.", "Autumn is a season."], ["A", "B", "C"]),
            Q("补全对话：— Which season do you like best? —（　）", "Winter.", "Because of snow.", "It's cold.", "In December."),
            Q("补全句子：I like summer（　）。", "best", "good", "better is", "very bestest"),
            Q("“I can sleep all day.”中的 can 表示（　）。", "能够；可以", "正在", "必须", "过去"),
            Q("“Good job!”用于（　）。", "表扬对方做得好", "询问工作", "表示拒绝", "催促离开"),
            Q("想表达“因为我喜欢雪”，应说（　）。", "Because I like snow.", "Why I like snow.", "So snow I like.", "Because snow like me."),
            Q("“Which”用于（　）。", "在有限范围内选择", "询问原因", "询问时间", "询问所属"),
            S2("谈论最喜欢的季节，正确的句子是（　）。", ["I like winter best because I like snow.", "I best like winter because snow.", "Winter I like best why snow.", "I like winter because best snow."]),
        ]),
        ("第3课 综合运用", "综合练习：季节、天气、活动和原因表达。根据情境说明自己的选择。", [
            Q("天气温暖、花朵开放，最可能是（　）。", "spring", "summer", "autumn", "winter"),
            Q("天气炎热、适合游泳，最可能是（　）。", "summer", "spring", "autumn", "winter"),
            Q("天气凉爽、树叶变色，最可能是（　）。", "autumn", "spring", "summer", "winter"),
            Q("天气寒冷、可能下雪，最可能是（　）。", "winter", "spring", "summer", "autumn"),
            Q("选择正确的问答搭配（　）。", "Why do you like spring? — Because there are flowers.", "Why do you like spring? — Spring.", "Which season do you like? — Because it's warm.", "What's summer like? — I like winter."),
            Q("“I like summer because of summer vacation.”中 because of 后接（　）。", "名词或名词短语", "完整问句", "动词原形作谓语", "人称代词主格加谓语"),
            Q("选择语序正确的句子（　）。", "Which season do you like best?", "Which do you like season best?", "Season which you best like?", "You like best which season?"),
            Q("“The leaves fall in autumn.”的意思是（　）。", "秋天树叶落下。", "春天花朵开放。", "夏天树叶变绿。", "冬天树叶生长。"),
            Q("“I often go on a picnic with my family.”的意思是（　）。", "我经常和家人去野餐。", "我经常和家人游泳。", "我独自去摘苹果。", "我和家人堆雪人。"),
            Q("“snowman”的复数形式是（　）。", "snowmen", "snowmans", "snowmanes", "snowman"),
            M("描述 spring 的内容可以有（　）。", ["warm weather", "beautiful flowers", "plant flowers", "make a snowman"], ["A", "B", "C"]),
            M("描述 winter 的内容可以有（　）。", ["cold weather", "snow", "make a snowman", "pick apples"], ["A", "B", "C"]),
            Q("“Which season do you like best?”中的 best 表示（　）。", "最；最喜欢", "更", "也", "不"),
            Q("“Because”开头的答句是在说明（　）。", "原因", "地点", "日期", "所属"),
            Q("喜欢秋天并说明原因，可以说（　）。", "I like autumn best because I can pick apples.", "I like autumn when pick apples.", "Because autumn I best.", "Autumn is pick apples me."),
            Q("喜欢夏天但天气很热，可以说（　）。", "I like summer, but it's hot.", "I like summer because but hot.", "Summer I hot like.", "I like hot is summer."),
            Q("一年有（　）个季节。", "four", "three", "five", "twelve"),
            Q("澳大利亚的季节与中国大致相反，这说明季节还与（　）有关。", "所在的半球", "星期", "课程表", "物主代词"),
            Q("选择季节活动时，应该（　）。", "结合天气并注意安全", "冬天到薄冰上玩", "雷雨天去游泳", "酷暑时长时间暴晒"),
            Q("下列哪句同时包含季节和原因？（　）", "I like spring because it's warm.", "Spring is warm.", "I like flowers.", "Which season do you like?"),
            S2("本单元主要学会了（　）。", ["谈论喜爱的季节并说明原因", "介绍每日作息", "询问活动月份", "表达物品归属"]),
        ]),
    ]),
    ("第三单元 My school calendar", [
        ("第1课 核心词汇", "Today's words: January to October。月份首字母要大写，November 和 December 也会在后续练习中出现。", build_vocab([
            ("January", "一月"), ("February", "二月"), ("March", "三月"), ("April", "四月"),
            ("May", "五月"), ("June", "六月"), ("July", "七月"), ("August", "八月"),
            ("September", "九月"), ("October", "十月"),
        ])),
        ("第2课 句型与对话", "Sentences: When is the school trip? / It's in May. 学会询问节日和学校活动所在月份。", [
            Q("询问“学校旅行在什么时候？”应该说（　）。", "When is the school trip?", "Where is the school trip?", "What is the school trip?", "Do you like the school trip?"),
            Q("回答“When is the sports meet?”可以说（　）。", "It's in April.", "It's April 4th.", "It's on the playground.", "Yes, it is."),
            Q("月份前通常使用介词（　）。", "in", "on", "at", "for"),
            Q("“New Year's Day is in January.”的意思是（　）。", "元旦在一月。", "元旦在十二月。", "春节在一月。", "一月是新年。"),
            Q("“Tree Planting Day is in March.”的意思是（　）。", "植树节在三月。", "植树节在五月。", "三月有儿童节。", "植树节在春季每一天。"),
            Q("儿童节所在的月份是（　）。", "June", "May", "July", "September"),
            Q("教师节所在的月份是（　）。", "September", "October", "August", "November"),
            Q("中国国庆节所在的月份是（　）。", "October", "September", "November", "December"),
            Q("Christmas 所在的月份是（　）。", "December", "November", "October", "January"),
            Q("美国感恩节通常在（　）。", "November", "October", "December", "September"),
            Q("November 的意思是（　）。", "十一月", "十二月", "十月", "九月"),
            Q("December 的意思是（　）。", "十二月", "十一月", "一月", "十月"),
            M("春季月份有（　）。", ["March", "April", "May", "December"], ["A", "B", "C"]),
            M("学校活动可以有（　）。", ["sports meet", "school trip", "singing contest", "winter"], ["A", "B", "C"]),
            Q("补全对话：— When is the singing contest? —（　）", "It's in May.", "It's May.", "At the music room.", "Yes, it is."),
            Q("补全句子：The summer vacation is（　）July and August.", "in", "on", "at", "from only"),
            Q("月份单词的首字母应该（　）。", "大写", "小写", "大小写均可", "省略"),
            Q("“We have a few fun things in spring.”的意思是（　）。", "春天我们有一些有趣的事情。", "春天我们没有活动。", "我们只有一件春装。", "春天有几个月？"),
            Q("想知道派对在哪个月举行，可以问（　）。", "When is the party?", "Where is the party?", "Whose party is it?", "What do you do at the party?"),
            Q("“It's in May.”中的 It 可以指前面提到的（　）。", "节日或活动", "许多月份", "一群学生", "所有课程"),
            S2("谈论活动月份，正确的句子是（　）。", ["The English party is in April.", "The English party is on April.", "The English party are in April.", "In April is English party the."]),
        ]),
        ("第3课 综合运用", "综合练习：十二个月、节日活动和 calendar 信息。按时间顺序读懂学校日历。", [
            Q("一年中的第一个月是（　）。", "January", "February", "December", "March"),
            Q("一年中的最后一个月是（　）。", "December", "November", "January", "October"),
            Q("February 后面的月份是（　）。", "March", "January", "April", "May"),
            Q("August 前面的月份是（　）。", "July", "June", "September", "October"),
            Q("选择正确的问答搭配（　）。", "When is the school trip? — It's in October.", "When is the school trip? — In the park.", "Where is the sports meet? — It's in April.", "What is May? — Yes, it is."),
            Q("“The sports meet is in April.”改成问句应为（　）。", "When is the sports meet?", "Where is the sports meet?", "Is the sports meet fun?", "What do you do in April?"),
            Q("选择月份排序正确的一组（　）。", "September, October, November, December", "September, November, October, December", "October, September, December, November", "December, November, October, September"),
            Q("“January”常用缩写是（　）。", "Jan.", "Jau.", "Jny.", "Jr."),
            Q("“September”常用缩写是（　）。", "Sept.", "Sepm.", "Set.", "Sptm."),
            Q("“calendar”的意思是（　）。", "日历；日程表", "季节", "课程", "生日蛋糕"),
            M("含有 31 天的月份有（　）。", ["January", "March", "May", "April"], ["A", "B", "C"]),
            M("通常属于暑假的月份有（　）。", ["July", "August", "summer months", "February"], ["A", "B", "C"]),
            Q("学校日历写“English party — April”，应表达为（　）。", "The English party is in April.", "The English party is on April.", "April has English party is.", "English party are April."),
            Q("“Autumn is my favourite season. I like September.”中 September 属于（　）。", "autumn", "spring", "summer", "winter"),
            Q("在中国，winter vacation 常在（　）。", "January or February", "July or August", "May or June", "September or October"),
            Q("“When is Mother's Day?”可以回答（　）。", "It's in May.", "It's on Sunday every week.", "It's a gift.", "I love my mother."),
            Q("“When is Father's Day?”可以回答（　）。", "It's in June.", "It's in May.", "It's in September.", "It's in December."),
            Q("安排活动时先查看 calendar 可以帮助我们（　）。", "避免时间冲突", "改变月份顺序", "减少一年月份", "决定天气"),
            Q("下列哪句同时包含活动和月份？（　）", "The singing contest is in May.", "May is warm.", "I like singing.", "When is the contest?"),
            Q("十二个月按顺序循环，December 之后是（　）。", "January", "November", "February", "October"),
            S2("本单元主要学会了（　）。", ["询问并回答节日或活动所在月份", "介绍作息时间", "谈论最喜欢的季节", "描述物品归属"]),
        ]),
    ]),
    ("第四单元 When is the art show", [
        ("第1课 核心词汇", "Today's words: first / second / third / fourth / fifth / twelfth / twentieth 等序数词。学会读写日期。", build_vocab([
            ("first", "第一（的）"), ("second", "第二（的）"), ("third", "第三（的）"),
            ("fourth", "第四（的）"), ("fifth", "第五（的）"), ("twelfth", "第十二（的）"),
            ("twentieth", "第二十（的）"), ("twenty-first", "第二十一（的）"),
            ("twenty-third", "第二十三（的）"), ("thirtieth", "第三十（的）"),
        ])),
        ("第2课 句型与对话", "Sentences: When is the art show? / It's on May 1st. 用序数词询问和表达具体日期。", [
            Q("询问“美术展是哪天？”应该说（　）。", "When is the art show?", "Where is the art show?", "What is the art show?", "Do you like the art show?"),
            Q("回答“When is the art show?”可以说（　）。", "It's on May 1st.", "It's in May.", "It's at school.", "Yes, it is."),
            Q("具体日期前通常使用介词（　）。", "on", "in", "at", "for"),
            Q("May 1st 中 1st 读作（　）。", "first", "one", "second", "fourth"),
            Q("May 2nd 中 2nd 读作（　）。", "second", "two", "third", "twelfth"),
            Q("May 3rd 中 3rd 读作（　）。", "third", "three", "thirtieth", "fourth"),
            Q("May 4th 中 4th 读作（　）。", "fourth", "four", "fifth", "first"),
            Q("May 5th 中 5th 读作（　）。", "fifth", "five", "fourth", "fifteen"),
            Q("“The reading festival is on May 5th.”的意思是（　）。", "阅读节在五月五日。", "阅读节在五月。", "美术展在五月五日。", "阅读节有五天。"),
            Q("询问同伴生日日期，可以说（　）。", "When is your birthday?", "Where is your birthday?", "What is your birthday gift?", "Do you have a birthday?"),
            Q("“My birthday is on April 4th.”的意思是（　）。", "我的生日是四月四日。", "我的生日在四月。", "我四岁。", "四月有我的生日礼物。"),
            Q("12th 的完整拼写是（　）。", "twelfth", "twelveth", "twelve", "twentieth"),
            M("正确的序数词有（　）。", ["first", "second", "third", "three"], ["A", "B", "C"]),
            M("正确的日期写法有（　）。", ["May 1st", "June 2nd", "April 3rd", "March 4rd"], ["A", "B", "C"]),
            Q("补全对话：— When is China's National Day? —（　）", "It's on October 1st.", "It's in October 1st.", "It's at October.", "It's October one."),
            Q("补全句子：The English test is（　）November 2nd.", "on", "in", "at", "to"),
            Q("“What will you do for your mum?”中的 will 表示（　）。", "将要", "正在", "已经", "能够"),
            Q("生日当天祝福别人可以说（　）。", "Happy birthday!", "Happy New Year!", "Good morning!", "Season greetings!"),
            Q("“Both of you”表示（　）。", "你们两个都", "你们所有人", "只有你", "他们两个"),
            Q("“There are some special days in April.”的意思是（　）。", "四月有一些特别的日子。", "四月每天都特殊。", "特殊日子在五月。", "四月没有活动。"),
            S2("表达具体日期，正确的句子是（　）。", ["The art show is on May 1st.", "The art show is in May 1st.", "The art show are on May first.", "On May 1st art show is the."]),
        ]),
        ("第3课 综合运用", "综合练习：序数词、日期读写和生日活动。读懂日期表并准确表达。", [
            Q("June 12th 应读作（　）。", "June twelfth", "June twelve", "twelfth June month", "June twentieth"),
            Q("April 20th 应读作（　）。", "April twentieth", "April twenty", "April twelfth", "April twenty-first"),
            Q("August 21st 应读作（　）。", "August twenty-first", "August twenty-one", "August twentieth-one", "August twenty-second"),
            Q("November 23rd 应读作（　）。", "November twenty-third", "November twenty-three", "November twentieth-third", "November twenty-second"),
            Q("September 30th 应读作（　）。", "September thirtieth", "September thirty", "September thirteenth", "September twentieth"),
            Q("选择正确的问答搭配（　）。", "When is your birthday? — It's on July 2nd.", "When is your birthday? — I am ten.", "What day is it? — On May 5th.", "Where is the party? — It's on June 1st."),
            Q("把“The art show is on May 1st.”改成问句，应为（　）。", "When is the art show?", "Where is the art show?", "Is the art show May?", "What does the art show do?"),
            Q("选择语序正确的句子（　）。", "My birthday is on December 3rd.", "My birthday on is December 3rd.", "On December my birthday 3rd is.", "My is birthday December 3rd."),
            Q("基数词 one 对应的序数词是（　）。", "first", "oneth", "second", "once"),
            Q("基数词 two 对应的序数词是（　）。", "second", "twoth", "twelfth", "third"),
            M("拼写发生明显变化的序数词有（　）。", ["first", "second", "third", "fourth"], ["A", "B", "C"]),
            M("下列日期中的序数词后缀正确的有（　）。", ["1st", "2nd", "3rd", "5rd"], ["A", "B", "C"]),
            Q("“The kittens can walk on April 3rd.”中的 on 用于（　）。", "具体日期", "月份", "钟点", "季节"),
            Q("日期 April 5th 中月份是（　）。", "April", "May", "fifth", "Sunday"),
            Q("日期 May 4th 中序数词是（　）。", "fourth", "May", "four", "Friday"),
            Q("如果活动在五月三日，应写作（　）。", "May 3rd", "May 3th", "May 3st", "May third day on"),
            Q("同一天有两项活动时，可以说（　）。", "Both activities are on May 1st.", "Both activity is in May 1st.", "Two activities on May one is.", "Activities both at May."),
            Q("记录生日时最需要确认（　）。", "月份和日期", "季节和天气", "星期课程", "物品归属"),
            Q("为家人准备生日惊喜时，应（　）。", "表达祝福并尊重对方喜好", "忘记日期", "取笑礼物", "打扰别人休息"),
            Q("下列哪句同时包含事件和具体日期？（　）", "The maths test is on June 4th.", "June is warm.", "I have a test.", "When is the test?"),
            S2("本单元主要学会了（　）。", ["用序数词询问和表达具体日期", "介绍一天作息", "说明季节原因", "使用物主代词"]),
        ]),
    ]),
    ("第五单元 Whose dog is it", [
        ("第1课 核心词汇", "Today's words: mine / yours / his / hers / ours / theirs，以及 climbing / eating / playing / jumping。", build_vocab([
            ("mine", "我的"), ("yours", "你（们）的"), ("his", "他的"), ("hers", "她的"),
            ("ours", "我们的"), ("theirs", "他们的；她们的；它们的"),
            ("climbing", "（正在）攀登；攀爬"), ("eating", "（正在）吃"),
            ("playing", "（正在）玩耍"), ("jumping", "（正在）跳"),
        ])),
        ("第2课 句型与对话", "Sentences: Whose dog is it? It's mine. / The yellow picture is mine. 学会询问和说明物品归属。", [
            Q("询问“这是谁的狗？”应该说（　）。", "Whose dog is it?", "Who is the dog?", "Where is the dog?", "What is the dog doing?"),
            Q("回答“Whose book is it?”可以说（　）。", "It's mine.", "It's me.", "I am book.", "It's my."),
            Q("“The yellow picture is mine.”的意思是（　）。", "那幅黄色的画是我的。", "那幅黄色的画是你的。", "我喜欢黄色的画。", "这幅画是黄色的。"),
            Q("“It's hers.”的意思是（　）。", "它是她的。", "它是他的。", "它是我们的。", "它是你的。"),
            Q("“The dog is his.”的意思是（　）。", "这只狗是他的。", "这只狗是她的。", "他是一只狗。", "狗在他旁边。"),
            Q("“These books are ours.”的意思是（　）。", "这些书是我们的。", "这些书是他们的。", "这是我的书。", "我们有一本书。"),
            Q("“Those bags are theirs.”的意思是（　）。", "那些包是他们的。", "那些包是我们的。", "那个包是她的。", "他们在包里。"),
            Q("my 对应的名词性物主代词是（　）。", "mine", "my", "me", "I"),
            Q("your 对应的名词性物主代词是（　）。", "yours", "your", "you", "ours"),
            Q("her 对应的名词性物主代词是（　）。", "hers", "her", "she", "his"),
            Q("our 对应的名词性物主代词是（　）。", "ours", "our", "us", "theirs"),
            Q("their 对应的名词性物主代词是（　）。", "theirs", "their", "them", "yours"),
            M("名词性物主代词有（　）。", ["mine", "yours", "hers", "my"], ["A", "B", "C"]),
            M("正确的所属表达有（　）。", ["It's mine.", "The pen is yours.", "These are theirs.", "It's my."], ["A", "B", "C"]),
            Q("补全对话：— Whose storybook is this? — It's（　）。", "hers", "her", "she", "hers book"),
            Q("补全句子：The blue bike is（　）bike.", "my", "mine", "I", "me"),
            Q("“Whose”用于询问（　）。", "所属关系", "人物身份", "地点", "时间"),
            Q("mine 后面通常（　）。", "不再接名词", "必须接名词", "接动词-ing", "接月份"),
            Q("my 后面通常接（　）。", "名词", "完整句子", "序数词", "介词"),
            Q("想确认物品是不是对方的，可以问（　）。", "Is it yours?", "Is it your?", "Does it yours?", "Are it you?"),
            S2("说明物品归属，正确的句子是（　）。", ["This English book is mine.", "This English book is my.", "This is mine English book.", "This English book mine is."]),
        ]),
        ("第3课 综合运用", "综合练习：物主代词、whose 问句和动物正在做的动作。根据情境判断归属与行为。", [
            Q("Amy 的书可以说（　）。", "The book is hers.", "The book is her.", "The book is she.", "The book is his."),
            Q("John 的球可以说（　）。", "The ball is his.", "The ball is he.", "The ball is hims.", "The ball is hers."),
            Q("你和同伴共有的教室可以说（　）。", "The classroom is ours.", "The classroom is our.", "The classroom is us.", "The classroom is theirs."),
            Q("对方的钢笔可以说（　）。", "The pen is yours.", "The pen is your.", "The pen is you.", "The pen is mine."),
            Q("选择正确的问答搭配（　）。", "Whose dog is it? — It's his.", "Whose dog is it? — It's playing.", "What is the dog doing? — It's mine.", "Is it yours? — It's a dog."),
            Q("“What is the dog doing?”的合适回答是（　）。", "It's sleeping.", "It's mine.", "It's a dog.", "Yes, it is."),
            Q("“The monkey is climbing.”的意思是（　）。", "猴子正在攀爬。", "猴子会攀爬。", "猴子喜欢树。", "猴子正在跳。"),
            Q("“The rabbit is jumping.”的意思是（　）。", "兔子正在跳。", "兔子正在吃。", "兔子正在睡。", "兔子是我的。"),
            Q("“The dog is eating.”中的 eating 表示（　）。", "正在吃", "正在喝", "正在玩", "正在爬"),
            Q("“They're playing with each other.”的意思是（　）。", "它们正在互相玩耍。", "它们属于彼此。", "它们正在吃东西。", "它们正在睡觉。"),
            M("名词性物主代词后不必再接名词的有（　）。", ["mine", "hers", "ours", "my"], ["A", "B", "C"]),
            M("表示正在进行动作的词有（　）。", ["climbing", "eating", "jumping", "mine"], ["A", "B", "C"]),
            Q("把“This is my picture.”换成同义表达，应为（　）。", "This picture is mine.", "This picture is my.", "This is mine picture.", "Mine is this my picture."),
            Q("把“These are their books.”换成同义表达，应为（　）。", "These books are theirs.", "These books are their.", "These are theirs books.", "Their books is theirs."),
            Q("选择语序正确的句子（　）。", "Whose carrots are these?", "Whose are these carrots are?", "These carrots whose?", "Who carrots are these?"),
            Q("“Is he drinking water?”的肯定回答是（　）。", "Yes, he is.", "Yes, he does.", "Yes, it is.", "Yes, he can."),
            Q("“Are these all ours?”的意思是（　）。", "这些全都是我们的吗？", "这些都是他们的吗？", "这是我们的吗？", "这些在我们旁边吗？"),
            Q("发现不确定归属的物品时，应该（　）。", "先询问主人再处理", "直接拿走", "藏起来", "随意丢弃"),
            Q("“each other”表示（　）。", "互相", "每一个物品", "其他地方", "所有人的"),
            Q("下列哪句同时包含动物和正在进行的动作？（　）", "The elephant is drinking water.", "The elephant is mine.", "I like elephants.", "Whose elephant is it?"),
            S2("本单元主要学会了（　）。", ["询问物品归属并描述正在发生的动作", "介绍每日作息", "询问活动日期", "谈论季节原因"]),
        ]),
    ]),
    ("第六单元 Work quietly", [
        ("第1课 核心词汇", "Today's phrases: keep to the right / keep your desk clean / talk quietly / take turns，以及正在进行的活动。", build_vocab([
            ("keep to the right", "靠右"), ("keep your desk clean", "保持你的课桌干净"),
            ("talk quietly", "小声讲话"), ("take turns", "按顺序来"),
            ("eat lunch", "吃午饭"), ("read a book", "看书"), ("listen to music", "听音乐"),
            ("do morning exercises", "做早操"), ("have an English class", "上英语课"),
            ("write an email", "写电子邮件"),
        ])),
        ("第2课 句型与对话", "Sentences: What are you doing? I'm reading a book. / Keep your desk clean. 学会询问正在进行的活动并遵守规则。", [
            Q("询问“你正在做什么？”应该说（　）。", "What are you doing?", "What do you do?", "What can you do?", "When do you do it?"),
            Q("回答“What are you doing?”可以说（　）。", "I'm reading a book.", "I read books every day.", "I can read.", "Yes, I am."),
            Q("询问“他正在做什么？”应该说（　）。", "What is he doing?", "What does he do?", "What can he do?", "What he is doing?"),
            Q("回答“What is she doing?”可以说（　）。", "She is listening to music.", "She listens to music.", "She can music.", "Yes, she does."),
            Q("“They are eating lunch.”的意思是（　）。", "他们正在吃午饭。", "他们每天吃午饭。", "他们吃过午饭了。", "他们想吃晚饭。"),
            Q("在图书馆应该（　）。", "talk quietly", "talk loudly", "run quickly", "sing loudly"),
            Q("在楼梯或通道行走时应该（　）。", "keep to the right", "keep to the left everywhere", "jump in line", "run fast"),
            Q("在教室里应该（　）。", "keep your desk clean", "leave rubbish on the desk", "draw on the desk", "hide books under rubbish"),
            Q("多人使用同一物品时应该（　）。", "take turns", "push others", "take it forever", "shout loudly"),
            Q("“Work quietly!”的意思是（　）。", "安静地学习（工作）！", "快点工作！", "停止学习！", "一起大声说话！"),
            Q("“No eating!”的意思是（　）。", "禁止吃东西！", "没有食物！", "快吃吧！", "不要喝水！"),
            Q("“Keep your desk clean.”属于（　）。", "祈使句", "一般疑问句", "特殊疑问句", "感叹问句"),
            M("公共场所的文明规则有（　）。", ["talk quietly", "take turns", "keep to the right", "push others"], ["A", "B", "C"]),
            M("表示正在进行活动的句子有（　）。", ["I'm reading.", "She is listening to music.", "They are eating lunch.", "I read every day."], ["A", "B", "C"]),
            Q("补全对话：— What are they doing? — They（　）morning exercises.", "are doing", "do", "is doing", "doing"),
            Q("补全句子：Chen Jie is（　）an English class.", "having", "have", "has", "haves"),
            Q("“Shh. Talk quietly.”中的 Shh 用来提醒（　）。", "保持安静", "加快速度", "开始吃饭", "排队靠左"),
            Q("“Can we use your crayons?”的礼貌回答可以是（　）。", "OK. Take turns.", "No, go away.", "Crayons are colours.", "I am using."),
            Q("“Anything else?”的意思是（　）。", "还有别的事吗？", "这是谁的东西？", "你在做什么？", "还要多久？"),
            Q("现在进行时常用结构是（　）。", "be + 动词-ing", "do + 动词原形", "can + 动词-ing", "have + 名词"),
            S2("描述正在进行的活动，正确的句子是（　）。", ["We are having an English class.", "We having an English class.", "We are have an English class.", "We is having an English class."]),
        ]),
        ("第3课 综合运用", "综合练习：现在进行时、祈使句和公共规则。根据不同场所选择恰当表达。", [
            Q("图中孩子正在看书，应描述为（　）。", "He is reading a book.", "He reads a book every day.", "He can read a book.", "He reading book is."),
            Q("图中同学们正在做早操，应描述为（　）。", "They are doing morning exercises.", "They do morning exercises now is.", "They is doing morning exercises.", "They are do morning exercises."),
            Q("选择正确的问答搭配（　）。", "What is Amy doing? — She is writing an email.", "What is Amy doing? — She writes every day.", "What are they doing? — Yes, they are.", "Are you reading? — I'm a book."),
            Q("把“I am listening to music.”改成一般疑问句，应为（　）。", "Are you listening to music?", "Do you listening to music?", "Is you listening to music?", "Are you listen to music?"),
            Q("“Is he eating lunch?”的否定回答是（　）。", "No, he isn't.", "No, he doesn't.", "No, he can't.", "No, it isn't."),
            Q("选择语序正确的句子（　）。", "What are the students doing?", "What the students are doing?", "What doing are the students?", "The students what are doing?"),
            Q("动词 write 变现在分词应为（　）。", "writing", "writeing", "writting", "writes"),
            Q("动词 have 变现在分词应为（　）。", "having", "haveing", "havving", "hasing"),
            Q("动词 run 变现在分词应为（　）。", "running", "runing", "runs", "run"),
            Q("“Talk quietly.”中的 quietly 修饰（　）。", "talk", "人", "课桌", "右边"),
            M("下列现在进行时句子正确的有（　）。", ["I am reading.", "He is eating.", "They are playing.", "She are writing."], ["A", "B", "C"]),
            M("图书馆中应该做到（　）。", ["talk quietly", "walk quietly", "take turns", "play loud music"], ["A", "B", "C"]),
            Q("在学校食堂排队时，最合适的提示是（　）。", "Take turns.", "Talk loudly.", "Run fast.", "Keep your desk clean only."),
            Q("在楼梯上看到同学靠左逆行，可以提醒（　）。", "Keep to the right.", "Take turns with food.", "Work quietly at your desk.", "No eating in class."),
            Q("看到同桌桌面很乱，可以提醒（　）。", "Keep your desk clean.", "Keep to the right.", "Talk quietly.", "Take turns."),
            Q("“Please take turns.”加上 please 使语气更（　）。", "礼貌", "生气", "命令且粗鲁", "疑惑"),
            Q("“I am doing my homework now.”中的 now 提示动作（　）。", "正在发生", "每天发生", "昨天发生", "将来发生"),
            Q("遵守公共规则的意义是（　）。", "让大家安全、有序地学习生活", "只让自己方便", "限制所有活动", "可以不用礼貌"),
            Q("使用公共物品时，应（　）。", "按顺序使用并爱护物品", "抢先占用", "用完不归还", "故意损坏"),
            Q("下列哪句同时包含正在进行的动作和地点？（　）", "They are reading in the library.", "They read every day.", "The library is quiet.", "Where are they?"),
            S2("本单元主要学会了（　）。", ["询问正在进行的活动并使用规则提示语", "介绍日常作息", "询问具体日期", "表达物品归属"]),
        ]),
    ]),
    ("复习与检测", [
        ("第1课 Revision 1", "Revision 1: Units 1–3。复习日常作息、季节活动和学校日历。", build_vocab([
            ("eat breakfast", "吃早饭"), ("play sports", "进行体育运动"),
            ("clean my room", "打扫我的房间"), ("spring", "春天"), ("winter", "冬天"),
            ("pick apples", "摘苹果"), ("January", "一月"), ("March", "三月"),
            ("September", "九月"), ("December", "十二月"),
        ])),
        ("第2课 Revision 2", "Revision 2: Units 4–6。复习日期、物品归属、正在进行的活动和公共规则。", build_vocab([
            ("first", "第一（的）"), ("twelfth", "第十二（的）"), ("twentieth", "第二十（的）"),
            ("mine", "我的"), ("hers", "她的"), ("theirs", "他们的；她们的；它们的"),
            ("talk quietly", "小声讲话"), ("take turns", "按顺序来"),
            ("keep to the right", "靠右"), ("read a book", "看书"),
        ])),
    ]),
]


if __name__ == "__main__":
    run(r"content/primary/pep/grade5/volume2/english", "英语下册", UNITS)
