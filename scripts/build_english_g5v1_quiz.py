# -*- coding: utf-8 -*-
"""人教版 PEP 五年级上册英语全部单元交互自测题生成脚本。"""
import random

from _quizlib import S, S2, M, run


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
    ("第一单元 What is he like", [
        ("第1课 核心词汇", "Today's words: old / young / funny / kind / strict。用恰当的形容词介绍老师和朋友。", build_vocab([
            ("old", "年老的"), ("young", "年轻的"), ("funny", "滑稽的；可笑的"),
            ("kind", "体贴的；慈祥的"), ("strict", "要求严格的；严厉的"),
            ("polite", "有礼貌的"), ("hard-working", "工作努力的；辛勤的"),
            ("helpful", "有用的；愿意帮忙的"), ("clever", "聪明的"), ("shy", "羞怯的；腼腆的"),
        ])),
        ("第2课 句型与对话", "Sentences: What's he like? He's kind. / Is he strict? Yes, he is. 学会询问和描述人物。", [
            Q("询问“他什么样？”应该说（　）。", "What's he like?", "What does he like?", "Who is he?", "Where is he?"),
            Q("回答“What's he like?”可以说（　）。", "He's kind.", "He likes apples.", "He's Mr Li.", "He's in the classroom."),
            Q("“Is he strict?”的肯定回答是（　）。", "Yes, he is.", "Yes, she is.", "Yes, he does.", "Yes, I am."),
            Q("“Is she funny?”的否定回答是（　）。", "No, she isn't.", "No, he isn't.", "No, she doesn't.", "No, I am not."),
            Q("“He's young.”的意思是（　）。", "他很年轻。", "他很年老。", "他很严厉。", "他很害羞。"),
            Q("描述一位愿意帮助人的同学，应选（　）。", "She is helpful.", "She is strict.", "She is old.", "She is shy."),
            Q("“Our Chinese teacher is very kind.”的意思是（　）。", "我们的语文老师很和蔼。", "我们的语文老师很年轻。", "我们的英语老师很和蔼。", "我们的老师很聪明。"),
            Q("询问女老师是否严厉，应该说（　）。", "Is she strict?", "Does she strict?", "Is he strict?", "What she strict?"),
            Q("“He is hard-working.”描述的是（　）。", "他很勤奋。", "他很滑稽。", "他很有礼貌。", "他很腼腆。"),
            Q("“She is polite.”的意思是（　）。", "她很有礼貌。", "她很聪明。", "她很严格。", "她很年轻。"),
            Q("想知道新老师是谁，可以问（　）。", "Who is your new teacher?", "What's your new teacher like?", "Is your teacher kind?", "Where is your teacher?"),
            Q("“Who's your English teacher?”的合适回答是（　）。", "Ms Wang.", "She's kind.", "Yes, she is.", "I like English."),
            M("可以用来赞美同学的词有（　）。", ["helpful", "hard-working", "clever", "desk"], ["A", "B", "C"]),
            M("下列是描述人物性格的句子有（　）。", ["He is funny.", "She is kind.", "They are polite.", "It is a book."], ["A", "B", "C"]),
            Q("“What's she like?”中 she 指（　）。", "女性", "男性", "地点", "物品"),
            Q("补全对话：— Is Mr Jones young? — Yes,（　）。", "he is", "she is", "he does", "it is"),
            Q("补全句子：My maths teacher（　）strict.", "is", "are", "am", "be"),
            Q("“He is funny but strict.”的意思是（　）。", "他很有趣，但很严格。", "他既不有趣也不严格。", "他很友好而且年轻。", "他只会讲笑话。"),
            Q("描述两位老师都很友好，可以说（　）。", "They are kind.", "He is kind.", "She are kind.", "They is kind."),
            Q("“Is your art teacher young?”问的是（　）。", "你的美术老师年轻吗？", "你的美术老师是谁？", "你喜欢美术老师吗？", "美术老师在哪里？"),
            S2("介绍人物时，正确的表达是（　）。", ["My teacher is kind and helpful.", "My teacher kind helpful.", "My is teacher kind.", "Teacher my are kind."]),
        ]),
        ("第3课 综合运用", "综合练习：人物特征、问答搭配和 be 动词。根据情境选出最恰当的表达。", [
            Q("看到同学总主动帮忙，可以评价他（　）。", "helpful", "shy", "old", "strict"),
            Q("老师要求大家按时完成作业，可以说老师很（　）。", "strict", "funny", "young", "shy"),
            Q("见到长辈主动问好说明你很（　）。", "polite", "clever", "old", "funny"),
            Q("同学每天认真学习，可以描述为（　）。", "hard-working", "shy", "young", "strict"),
            Q("“My brother can answer the difficult question.”说明他很（　）。", "clever", "old", "strict", "shy"),
            Q("选择正确的问答搭配（　）。", "What's Amy like? — She's shy.", "What's Amy like? — She likes tea.", "Is Amy shy? — She's Amy.", "Who is Amy? — Yes, she is."),
            Q("句子“He's very kind.”中的 He's 是（　）的缩写。", "He is", "He has", "He does", "He can"),
            Q("句子“She isn't strict.”表示（　）。", "她不严厉。", "她很严厉。", "他不严厉。", "她不聪明。"),
            Q("选择语序正确的句子（　）。", "What is your music teacher like?", "What your music teacher is like?", "What like is your music teacher?", "Your music teacher what like?"),
            Q("想确认校长是否年老，可以问（　）。", "Is the head teacher old?", "Does the head teacher old?", "Is the head teacher kind?", "Who is the head teacher old?"),
            M("下列问答搭配正确的有（　）。", ["Is he funny? — Yes, he is.", "Is she kind? — No, she isn't.", "What's he like? — He's clever.", "Who's she? — She's helpful."], ["A", "B", "C"]),
            M("描述一位好同伴可以用（　）。", ["kind", "helpful", "polite", "behind"], ["A", "B", "C"]),
            Q("“Robin is short but strong.”中 but 表示（　）。", "但是", "并且", "因为", "所以"),
            Q("“They are helpful at school.”的意思是（　）。", "他们在学校乐于助人。", "他们在学校很害羞。", "他们喜欢学校。", "他们帮助学校搬家。"),
            Q("把“He is strict.”改成一般疑问句，应为（　）。", "Is he strict?", "Does he strict?", "He is strict?", "What is he strict?"),
            Q("对“Is your sister shy?”作肯定回答，应说（　）。", "Yes, she is.", "Yes, he is.", "Yes, she does.", "Yes, I am."),
            Q("下列哪句是在询问人物特点？（　）", "What's your father like?", "What does your father like?", "Where is your father?", "Who is your father?"),
            Q("“What does he like?”和“What's he like?”的区别是（　）。", "前者问喜好，后者问人物特点", "两句都问人物特点", "两句都问喜好", "前者问地点，后者问时间"),
            Q("班里新来一位同学，介绍她可说（　）。", "She is clever and polite.", "She clever and polite.", "Her is clever polite.", "She are clever."),
            Q("判断人物特征时，最合适的做法是（　）。", "根据日常表现客观描述", "只看外表随意评价", "给同学起难听的外号", "嘲笑别人的性格"),
            S2("本单元主要学会了（　）。", ["询问并描述人物的外貌和性格", "询问星期和课程", "谈论食物味道", "描述房间位置"]),
        ]),
    ]),
    ("第二单元 My week", [
        ("第1课 核心词汇", "Today's words: Monday to Sunday, do homework, watch TV, read books。安排好每周学习与活动。", build_vocab([
            ("Monday", "星期一"), ("Tuesday", "星期二"), ("Wednesday", "星期三"),
            ("Thursday", "星期四"), ("Friday", "星期五"), ("Saturday", "星期六"),
            ("Sunday", "星期日"), ("do homework", "做作业"), ("watch TV", "看电视"),
            ("read books", "看书"),
        ])),
        ("第2课 句型与对话", "Sentences: What do you have on Thursdays? / Do you often read books? 谈谈课程与周末活动。", [
            Q("询问“星期四你有什么课？”应该说（　）。", "What do you have on Thursdays?", "What do you do on Thursdays?", "Do you like Thursdays?", "When is Thursday?"),
            Q("回答“What do you have on Mondays?”可以说（　）。", "I have Chinese, English and maths.", "It is Monday.", "I often read books.", "Yes, I do."),
            Q("“Do you often play sports?”的肯定回答是（　）。", "Yes, I do.", "Yes, I am.", "Yes, I can.", "Yes, it is."),
            Q("“Do you often watch TV?”的否定回答是（　）。", "No, I don't.", "No, I am not.", "No, I can't.", "No, it isn't."),
            Q("“What do you do on the weekend?”的意思是（　）。", "你周末做什么？", "你周末有什么课？", "周末是星期几？", "你喜欢周末吗？"),
            Q("“I often read books on Sundays.”的意思是（　）。", "我经常在星期日看书。", "我经常在星期日写书。", "我星期日有阅读课。", "我只在星期六看书。"),
            Q("表示“我星期六做作业”应说（　）。", "I do homework on Saturdays.", "I have homework Saturdays.", "I am homework on Saturday.", "I do Saturday homework on."),
            Q("“What day is it today?”的合适回答是（　）。", "It's Wednesday.", "I have maths.", "I play sports.", "It's sunny."),
            Q("星期五后面是（　）。", "Saturday", "Thursday", "Sunday", "Monday"),
            Q("星期二前面是（　）。", "Monday", "Wednesday", "Thursday", "Friday"),
            Q("“I have PE on Fridays.”中 PE 指（　）。", "体育课", "音乐课", "美术课", "科学课"),
            Q("询问同伴是否常看书，可以说（　）。", "Do you often read books?", "Are you often read books?", "Can you often books?", "What you read books?"),
            M("适合周末进行的活动有（　）。", ["read books", "play sports", "do homework", "have Monday"], ["A", "B", "C"]),
            M("正确的星期单词有（　）。", ["Monday", "Thursday", "Sunday", "homework"], ["A", "B", "C"]),
            Q("“on Thursdays”表示（　）。", "在每个星期四", "在星期四早晨一次", "星期四之前", "星期四之后"),
            Q("补全对话：— Do you often play football? — No,（　）。", "I don't", "I do", "I'm not", "I can't"),
            Q("补全句子：We（　）English on Wednesdays.", "have", "has", "are", "do"),
            Q("“I often wash my clothes.”中 often 的意思是（　）。", "经常", "从不", "现在", "昨天"),
            Q("“Sometimes I watch TV.”的意思是（　）。", "有时我看电视。", "我总是看电视。", "我从不看电视。", "我正在看电视。"),
            Q("询问星期一的课程，关键词应使用（　）。", "have", "like", "can", "is"),
            S2("描述一周安排，正确的句子是（　）。", ["I have art on Tuesdays.", "I has art on Tuesdays.", "I have art in Tuesdays.", "I am art on Tuesday."]),
        ]),
        ("第3课 综合运用", "综合练习：星期、课程表、频率词和周末活动。读懂日程并作出正确选择。", [
            Q("课程表显示 Thursday 有 music，应说（　）。", "We have music on Thursdays.", "We do music on Thursday.", "We are music on Thursdays.", "We have Thursday on music."),
            Q("“I often play sports after school.”的意思是（　）。", "我放学后经常运动。", "我上学前经常运动。", "我放学后看电视。", "我有体育课。"),
            Q("选择正确的问答搭配（　）。", "What do you have on Fridays? — I have science.", "What do you have on Fridays? — It's Friday.", "Do you read books? — I have English.", "What day is it? — I play football."),
            Q("周末通常指（　）。", "Saturday and Sunday", "Monday and Tuesday", "Thursday and Friday", "Wednesday and Thursday"),
            Q("把“I often read books.”改成一般疑问句，应为（　）。", "Do you often read books?", "Are you often read books?", "Can you often read books?", "Do often you read books?"),
            Q("“No, I don't.”可以回答（　）。", "Do you often watch TV?", "What do you have today?", "What day is it?", "What do you do?"),
            Q("想表达周日有时踢足球，应说（　）。", "Sometimes I play football on Sundays.", "I sometimes have football Sundays.", "Sometimes I am football Sunday.", "I play Sundays sometimes football."),
            Q("“Wednesday”对应（　）。", "星期三", "星期二", "星期四", "星期五"),
            Q("“Thursday”拼写正确的是（　）。", "Thursday", "Thusday", "Thurday", "Thirsday"),
            Q("“What do you do on Saturdays?”问的是（　）。", "星期六进行的活动", "星期六上的课程", "星期六的日期", "星期六的天气"),
            M("下列句子语法正确的有（　）。", ["I have maths on Mondays.", "I often do homework.", "Do you play sports?", "She have English."], ["A", "B", "C"]),
            M("良好的周末安排可以包括（　）。", ["finish homework", "read books", "play sports", "watch TV all day"], ["A", "B", "C"]),
            Q("“I have a cooking class with your grandma.”中 with 表示（　）。", "和……一起", "在……上面", "因为", "但是"),
            Q("星期单词首字母应该（　）。", "大写", "小写", "大小写均可", "不写首字母"),
            Q("“on Monday”中表示具体星期要用介词（　）。", "on", "in", "at", "to"),
            Q("如果今天是 Friday，明天是（　）。", "Saturday", "Thursday", "Sunday", "Monday"),
            Q("如果昨天是 Sunday，今天是（　）。", "Monday", "Saturday", "Tuesday", "Friday"),
            Q("“Do you often clean your room?”回答“是的”应为（　）。", "Yes, I do.", "Yes, I am.", "Yes, I have.", "Yes, I often."),
            Q("安排学习和休息时，正确做法是（　）。", "按时完成作业并适量运动", "整天看电视", "从不阅读", "每天熬夜"),
            Q("下列哪句同时包含活动和时间？（　）", "I read books on Saturdays.", "I like books.", "It's Saturday.", "Reading is fun."),
            S2("本单元主要学会了（　）。", ["谈论每周课程和日常活动", "描述人物性格", "询问食物喜好", "描述自然公园"]),
        ]),
    ]),
    ("第三单元 What would you like", [
        ("第1课 核心词汇", "Today's words: sandwich / salad / hamburger / ice cream / tea，以及描述食物味道与品质的词。", build_vocab([
            ("sandwich", "三明治"), ("salad", "蔬菜沙拉；混合沙拉"), ("hamburger", "汉堡包"),
            ("ice cream", "冰激凌"), ("tea", "茶；茶水"), ("fresh", "新鲜的"),
            ("healthy", "健康的"), ("delicious", "美味的；可口的"), ("hot", "辣的；辛辣的"),
            ("sweet", "含糖的；甜的"),
        ])),
        ("第2课 句型与对话", "Sentences: What would you like to eat? I'd like a sandwich. / What's your favourite food? 学会礼貌点餐。", [
            Q("询问“你想吃什么？”应该说（　）。", "What would you like to eat?", "What do you eat now?", "What can you eat?", "Where do you eat?"),
            Q("“What would you like to drink?”的合适回答是（　）。", "I'd like some tea.", "I like sandwiches.", "It's delicious.", "Yes, please."),
            Q("“I'd like a hamburger.”的意思是（　）。", "我想要一个汉堡包。", "我喜欢做汉堡包。", "我有一个汉堡包。", "这个汉堡包很好吃。"),
            Q("I'd 是（　）的缩写。", "I would", "I do", "I had", "I can"),
            Q("询问对方最喜欢的食物，可以说（　）。", "What's your favourite food?", "What food do you have?", "Would you drink food?", "Where is your food?"),
            Q("回答“What's your favourite food?”可以说（　）。", "Noodles. They're delicious.", "I'd like some water.", "Yes, I do.", "It's on the table."),
            Q("“The vegetables are fresh.”的意思是（　）。", "这些蔬菜很新鲜。", "这些蔬菜很辣。", "这些水果很甜。", "这些蔬菜不健康。"),
            Q("“The salad is healthy.”的意思是（　）。", "沙拉很健康。", "沙拉很甜。", "沙拉很烫。", "沙拉很贵。"),
            Q("描述冰激凌的味道，可以用（　）。", "sweet", "strict", "shy", "helpful"),
            Q("“This fish is delicious.”的意思是（　）。", "这条鱼很美味。", "这条鱼很新鲜吗？", "这条鱼很辣。", "我想要鱼。"),
            Q("礼貌接受食物，可以说（　）。", "Yes, please.", "No food.", "Give me now.", "I don't care."),
            Q("礼貌拒绝食物，可以说（　）。", "No, thanks.", "No way!", "Take it away!", "I hate it!"),
            M("可以作为饮品的有（　）。", ["tea", "water", "milk", "salad"], ["A", "B", "C"]),
            M("可以描述食物的词有（　）。", ["fresh", "healthy", "delicious", "polite"], ["A", "B", "C"]),
            Q("“What would you like?”比“Give me ...”更（　）。", "礼貌", "严厉", "随意", "错误"),
            Q("补全对话：— What would you like? —（　）", "I'd like some salad.", "I am salad.", "I can salad.", "Salad likes me."),
            Q("补全句子：My favourite food（　）fish.", "is", "are", "am", "be"),
            Q("“I love beef noodles.”中的 favourite food 可以是（　）。", "beef noodles", "tea", "fresh", "eat"),
            Q("想要一份三明治和茶，应说（　）。", "I'd like a sandwich and some tea.", "I like sandwich with tea is.", "Give sandwich tea.", "A sandwich are tea."),
            Q("“They're hot.”中的 They 指代（　）。", "前面提到的复数食物", "一个人", "一种饮料", "一个汉堡包"),
            S2("在餐厅点餐时，正确表达是（　）。", ["I'd like some noodles, please.", "I noodles like please.", "Noodles give me!", "I'd noodles some."]),
        ]),
        ("第3课 综合运用", "综合练习：点餐问答、食物分类和味道描述。根据菜单与情境完成选择。", [
            Q("服务员问“What would you like to eat?”，应回答（　）。", "A sandwich, please.", "Some tea, please.", "I'm hungry.", "It's fresh."),
            Q("服务员问“What would you like to drink?”，应回答（　）。", "Some water, please.", "A hamburger, please.", "Some salad, please.", "I like rice."),
            Q("选择正确的问答搭配（　）。", "What's your favourite drink? — Tea.", "What would you like to eat? — Water.", "What's salad like? — A sandwich.", "Would you like tea? — I am tea."),
            Q("“The ice cream is sweet.”中 sweet 描述（　）。", "味道", "人物", "星期", "地点"),
            Q("刚从菜园摘下的蔬菜可以描述为（　）。", "fresh", "old", "strict", "shy"),
            Q("选择语序正确的句子（　）。", "What would you like to drink?", "What you would like drink?", "What would like you to drink?", "You would what like drink?"),
            Q("把“I would like some tea.”缩写，应为（　）。", "I'd like some tea.", "I'll like some tea.", "I'm like some tea.", "I've like some tea."),
            Q("“My favourite food is salad.”的意思是（　）。", "我最喜欢的食物是沙拉。", "我想要一份沙拉。", "沙拉是健康的。", "我不喜欢沙拉。"),
            Q("hot 在本单元描述食物时通常表示（　）。", "辣的", "温度高的", "新鲜的", "甜的"),
            Q("“They are healthy and delicious.”可描述（　）。", "fresh vegetables", "a strict teacher", "a school week", "a big bed"),
            M("较健康的食物选择有（　）。", ["fresh fruit", "salad", "vegetables", "ice cream for every meal"], ["A", "B", "C"]),
            M("礼貌点餐时可以说（　）。", ["What would you like?", "I'd like some rice, please.", "Thank you.", "Give me food!"], ["A", "B", "C"]),
            Q("“Would you like some tea?”的肯定回答是（　）。", "Yes, please.", "Yes, I would tea.", "Yes, it is.", "Yes, I do tea."),
            Q("“Would you like some salad?”的礼貌否定回答是（　）。", "No, thanks.", "No, I am not.", "No salad!", "No, it isn't."),
            Q("一份均衡午餐更适合选择（　）。", "rice, fish and vegetables", "only ice cream", "only hamburgers", "only sweet food"),
            Q("菜单上“sandwich”属于（　）。", "食物", "饮料", "形容词", "星期"),
            Q("菜单上“tea”属于（　）。", "饮料", "主食", "形容词", "人物特点"),
            Q("“The tomatoes are fresh.”中 be 动词用 are 是因为 tomatoes 是（　）。", "复数", "单数", "饮料", "不可数名词"),
            Q("同学请你品尝食物，你觉得好吃，可以说（　）。", "It's delicious!", "It's strict!", "He's helpful!", "It's Thursday!"),
            Q("选择食物时更合理的做法是（　）。", "注意营养均衡，不过量吃甜食", "每顿只吃冰激凌", "从不吃蔬菜", "只按颜色选食物"),
            S2("本单元主要学会了（　）。", ["礼貌询问饮食需求并描述食物", "谈论星期课程", "描述人物性格", "询问公园景物"]),
        ]),
    ]),
    ("第四单元 What can you do", [
        ("第1课 核心词汇", "Today's phrases: sing English songs / do kung fu / play the pipa / draw cartoons。展示你的本领。", build_vocab([
            ("sing English songs", "唱英文歌曲"), ("do kung fu", "练武术"),
            ("play the pipa", "弹琵琶"), ("draw cartoons", "画漫画"), ("cook", "烹调；烹饪"),
            ("swim", "游泳"), ("speak English", "说英语"), ("dance", "跳舞"),
            ("play basketball", "打篮球"), ("play ping-pong", "打乒乓球"),
        ])),
        ("第2课 句型与对话", "Sentences: What can you do? I can draw cartoons. / Can you swim? Yes, I can. 大胆介绍本领。", [
            Q("询问“你会做什么？”应该说（　）。", "What can you do?", "What do you have?", "What are you doing?", "What do you like?"),
            Q("回答“What can you do?”可以说（　）。", "I can cook.", "I am cooking.", "I like cook.", "Yes, I do."),
            Q("“Can you swim?”的肯定回答是（　）。", "Yes, I can.", "Yes, I do.", "Yes, I am.", "Yes, it is."),
            Q("“Can you play the pipa?”的否定回答是（　）。", "No, I can't.", "No, I don't.", "No, I'm not.", "No, it isn't."),
            Q("“I can sing English songs.”的意思是（　）。", "我会唱英文歌。", "我喜欢英文歌。", "我正在唱英文歌。", "我会说英语。"),
            Q("表达“我会画漫画”应说（　）。", "I can draw cartoons.", "I draw can cartoons.", "I can cartoons draw.", "I am draw cartoons."),
            Q("询问同伴会不会武术，可以说（　）。", "Can you do kung fu?", "Do you can kung fu?", "Are you do kung fu?", "What kung fu you can?"),
            Q("“She can dance.”的意思是（　）。", "她会跳舞。", "她正在跳舞。", "她喜欢跳舞。", "她不会跳舞。"),
            Q("can 后面的动词要用（　）。", "原形", "过去式", "第三人称单数", "动词-ing"),
            Q("“He can cook.”改为一般疑问句是（　）。", "Can he cook?", "Does he can cook?", "Is he cook?", "Can he cooks?"),
            Q("“Can Sarah speak English?”的合适回答是（　）。", "Yes, she can.", "Yes, he can.", "Yes, she does.", "Yes, Sarah is."),
            Q("“I can't swim.”中 can't 表示（　）。", "不会；不能", "会", "喜欢", "正在"),
            M("文艺表演中可以展示的才艺有（　）。", ["sing English songs", "dance", "play the pipa", "read Monday"], ["A", "B", "C"]),
            M("体育活动有（　）。", ["swim", "play basketball", "play ping-pong", "cook"], ["A", "B", "C"]),
            Q("补全对话：— Can you draw cartoons? — Yes,（　）。", "I can", "I do", "I am", "I draw"),
            Q("补全句子：Mike can（　）English.", "speak", "speaks", "speaking", "to speak"),
            Q("学校派对上询问伙伴能表演什么，可以说（　）。", "What can you do for the party?", "What do you have for the party?", "Where is the party?", "Do you like the party can?"),
            Q("“Wonderful!”在对方展示本领后表示（　）。", "太棒了！", "太难了！", "别做了！", "我不会。"),
            Q("想表达“我会打乒乓球，但不会游泳”应说（　）。", "I can play ping-pong, but I can't swim.", "I play ping-pong but swim.", "I can ping-pong and no swim.", "I can't play ping-pong but can swim."),
            Q("“Can you cook?”问的是（　）。", "你会做饭吗？", "你正在做饭吗？", "你喜欢食物吗？", "你想吃什么？"),
            S2("介绍自己的能力，正确的句子是（　）。", ["I can play basketball.", "I can plays basketball.", "I am can play basketball.", "I can playing basketball."]),
        ]),
        ("第3课 综合运用", "综合练习：can/can't、才艺调查和活动安排。根据真实能力礼貌交流。", [
            Q("才艺调查表中 Amy 的 swim 栏打勾，应说（　）。", "Amy can swim.", "Amy can't swim.", "Amy is swim.", "Amy can swims."),
            Q("才艺调查表中 John 的 cook 栏打叉，应说（　）。", "John can't cook.", "John doesn't can cook.", "John isn't cook.", "John can't cooks."),
            Q("选择正确的问答搭配（　）。", "Can you dance? — Yes, I can.", "Can you dance? — Yes, I do.", "What can you do? — Yes, I can.", "Can he cook? — He is cook."),
            Q("“What can Robin do?”的合适回答是（　）。", "He can speak English.", "Yes, he can.", "He likes English.", "He is helpful?"),
            Q("选择语序正确的句子（　）。", "Can you play the pipa?", "You can play the pipa?", "Can play you the pipa?", "Play the pipa can you?"),
            Q("“She can sing and dance.”表示她会（　）。", "唱歌和跳舞", "唱歌但不会跳舞", "只会跳舞", "不会唱歌也不会跳舞"),
            Q("“I can help you.”的意思是（　）。", "我能帮助你。", "你能帮助我。", "我需要帮助。", "我不会帮你。"),
            Q("把“He can play basketball.”改成否定句，应为（　）。", "He can't play basketball.", "He doesn't can play basketball.", "He not can play basketball.", "He can't plays basketball."),
            Q("can 对所有人称的形式（　）。", "都不变", "只对 he 变成 cans", "只对 I 变成 am can", "复数要变成 are can"),
            Q("“Can your brother cook?”中的主语是（　）。", "your brother", "cook", "can", "you"),
            M("下列句子正确的有（　）。", ["I can swim.", "She can dance.", "Can he cook?", "He can cooks."], ["A", "B", "C"]),
            M("在英语派对上可能用到的句子有（　）。", ["What can you do?", "I can sing.", "Wonderful!", "There is a river."], ["A", "B", "C"]),
            Q("想请同学一起练武术，可以说（　）。", "Let's do kung fu together.", "Let's doing kung fu.", "We kung fu now.", "Can together kung fu?"),
            Q("同学不会某项活动时，合适的回应是（　）。", "I can help you learn it.", "You are bad.", "Don't try again.", "Everyone must laugh."),
            Q("“play the pipa”中乐器前通常使用（　）。", "the", "a", "an", "不填"),
            Q("“play basketball”中球类运动前通常（　）。", "不加 the", "一定加 the", "一定加 an", "只能加 a"),
            Q("根据情境“我会说英语”选择（　）。", "I can speak English.", "I can say English songs.", "I speak can English.", "I can English speaking."),
            Q("根据情境“他会画漫画吗？”选择（　）。", "Can he draw cartoons?", "Does he draw cartoons can?", "Is he draw cartoons?", "Can he draws cartoons?"),
            Q("想参加篮球活动，应先确认自己的（　）。", "兴趣和能力", "食物喜好", "星期拼写", "房间位置"),
            Q("学习新本领时，正确态度是（　）。", "多练习并互相鼓励", "一次不会就放弃", "嘲笑初学者", "不听指导"),
            S2("本单元主要学会了（　）。", ["询问和表达会做或不会做的事情", "描述人物外貌", "谈论饮食", "询问物品位置"]),
        ]),
    ]),
    ("第五单元 There is a big bed", [
        ("第1课 核心词汇", "Today's words: clock / plant / bottle / bike / photo，以及 in front of / between / above / beside / behind。", build_vocab([
            ("clock", "时钟；钟"), ("plant", "植物"), ("bottle", "瓶子"), ("bike", "自行车；脚踏车"),
            ("photo", "照片；相片"), ("in front of", "在……前面"), ("between", "在……中间"),
            ("above", "在（或向）……上面"), ("beside", "在旁边（附近）"), ("behind", "在（或向）……后面"),
        ])),
        ("第2课 句型与对话", "Sentences: There is a big bed. / There are many pictures. / Where is the plant? 描述房间与位置。", [
            Q("“There is a big bed.”的意思是（　）。", "有一张大床。", "床上有一张照片。", "那里是大床。", "这张床很小。"),
            Q("表示“有许多照片”应该说（　）。", "There are many photos.", "There is many photos.", "There are a photo.", "They are many photo."),
            Q("询问“植物在哪里？”应该说（　）。", "Where is the plant?", "What is the plant?", "Is there a plant?", "Where are the plant?"),
            Q("“It's beside the window.”的意思是（　）。", "它在窗户旁边。", "它在窗户后面。", "它在窗户上方。", "它在窗户前面。"),
            Q("“The clock is above the desk.”的意思是（　）。", "时钟在书桌上方。", "时钟在书桌下面。", "时钟在书桌里面。", "书桌在时钟上方。"),
            Q("“The bike is behind the door.”的意思是（　）。", "自行车在门后面。", "自行车在门前面。", "自行车在门旁边。", "门在自行车后面。"),
            Q("两个物品中间用（　）。", "between", "above", "behind", "beside"),
            Q("一个物品旁边用（　）。", "beside", "between", "above", "in front of"),
            Q("“There is”后面通常接（　）。", "单数名词", "复数名词", "两个以上名词", "动词原形"),
            Q("“There are”后面通常接（　）。", "复数名词", "单数名词", "一个不可数物品", "形容词"),
            Q("房间里有一辆自行车，应说（　）。", "There is a bike in the room.", "There are a bike in the room.", "It has bike room.", "A bike there are."),
            Q("墙上有三幅画，应说（　）。", "There are three pictures on the wall.", "There is three pictures on the wall.", "There are three picture on wall.", "Three pictures is wall."),
            M("房间内可能出现的物品有（　）。", ["clock", "plant", "photo", "river"], ["A", "B", "C"]),
            M("表示位置的短语有（　）。", ["in front of", "beside", "behind", "delicious"], ["A", "B", "C"]),
            Q("补全句子：There（　）a photo on the wall.", "is", "are", "am", "be"),
            Q("补全句子：There（　）two plants near the desk.", "are", "is", "am", "be"),
            Q("“My room is really nice.”的意思是（　）。", "我的房间真的很漂亮。", "我的房间很大。", "我的房间里有床。", "我喜欢打扫房间。"),
            Q("想知道书在哪里，可以问（　）。", "Where is the book?", "Is there a book?", "What is the book?", "Where are the book?"),
            Q("“The ball is in front of the dog.”中在前面的是（　）。", "the ball", "the dog", "两者都不是", "无法判断"),
            Q("“The dog is between the boxes.”表示盒子数量至少是（　）。", "两个", "一个", "零个", "只能三个"),
            S2("描述房间时，正确的句子是（　）。", ["There is a desk beside the bed.", "There are a desk beside the bed.", "There is desk beside bed are.", "A desk there beside the bed."]),
        ]),
        ("第3课 综合运用", "综合练习：there be 句型、单复数和方位关系。观察房间布局完成表达。", [
            Q("图中床边有一张书桌，应描述为（　）。", "There is a desk beside the bed.", "There is a desk behind the bed only.", "There are a desk beside the bed.", "The desk is a bed."),
            Q("图中墙上有一个时钟，应描述为（　）。", "There is a clock on the wall.", "There are a clock on the wall.", "There is clock under the wall.", "A wall is on the clock."),
            Q("选择正确的问答搭配（　）。", "Where is the bike? — It's behind the door.", "Where is the bike? — There are two.", "Is there a bike? — Behind the door.", "Where are the bike? — Yes, it is."),
            Q("把“There is a photo.”改为复数，应为（　）。", "There are photos.", "There is photos.", "There are photo.", "They is photos."),
            Q("“There are some flowers.”的否定形式是（　）。", "There aren't any flowers.", "There isn't any flowers.", "There don't flowers.", "There are no a flower."),
            Q("“Is there a plant?”的肯定回答是（　）。", "Yes, there is.", "Yes, it is.", "Yes, there are.", "Yes, there does."),
            Q("“Are there any pictures?”的否定回答是（　）。", "No, there aren't.", "No, there isn't.", "No, they isn't.", "No, it doesn't."),
            Q("选择语序正确的句子（　）。", "There is a bottle on the desk.", "There a bottle is on the desk.", "A bottle there on desk is.", "On the desk is there bottle a."),
            Q("“The photo is above the bed.”中 above 可替换为意思相近的（　）。", "over", "behind", "beside", "between"),
            Q("“The chair is in front of the desk.”反向关系可说（　）。", "The desk is behind the chair.", "The desk is above the chair.", "The desk is beside the chair.", "The desk is between the chair."),
            M("下列 there be 句子正确的有（　）。", ["There is a bed.", "There are two chairs.", "There is a clock on the wall.", "There are a bike."], ["A", "B", "C"]),
            M("可以回答“Where is the plant?”的有（　）。", ["It's beside the window.", "It's behind the door.", "It's on the desk.", "There are two plants."], ["A", "B", "C"]),
            Q("bottle 的复数形式是（　）。", "bottles", "bottlees", "bottls", "bottle"),
            Q("photo 的复数形式是（　）。", "photos", "photoes", "photo's", "photoss"),
            Q("“There are lots of flowers.”中 lots of 表示（　）。", "许多", "一个", "没有", "少量且只有一个"),
            Q("想介绍自己的房间，开头可以说（　）。", "This is my room.", "What's your room?", "Where are me?", "I can room."),
            Q("描述物品位置时，要先找准（　）。", "参照物", "星期", "食物", "人物性格"),
            Q("“There is a computer here.”中 here 表示（　）。", "这里", "那里", "上面", "后面"),
            Q("保持房间整洁，应该（　）。", "物品分类摆放并及时整理", "把东西随处乱放", "把垃圾藏在床后", "从不打扫"),
            Q("下列哪句同时说明数量和位置？（　）", "There are two books on the desk.", "The books are nice.", "I have books.", "Where are the books?"),
            S2("本单元主要学会了（　）。", ["用 there be 和方位词描述房间", "询问人物性格", "谈论一周课程", "表达会做的事情"]),
        ]),
    ]),
    ("第六单元 In a nature park", [
        ("第1课 核心词汇", "Today's words: forest / river / lake / mountain / hill / tree / bridge / building / village / house。走进自然公园。", build_vocab([
            ("forest", "森林；林区"), ("river", "河；江"), ("lake", "湖；湖泊"),
            ("mountain", "高山；山岳"), ("hill", "山丘；小山"), ("tree", "树；树木"),
            ("bridge", "桥"), ("building", "建筑物；房子；楼房"), ("village", "村庄；村镇"),
            ("house", "房屋；房子；住宅"),
        ])),
        ("第2课 句型与对话", "Sentences: Is there a river in the park? / Are there any tall buildings? 询问自然景物。", [
            Q("询问“公园里有河吗？”应该说（　）。", "Is there a river in the park?", "Are there a river in the park?", "Where is the river park?", "Does the park river?"),
            Q("“Is there a lake?”的肯定回答是（　）。", "Yes, there is.", "Yes, it is.", "Yes, there are.", "Yes, there does."),
            Q("“Is there a forest?”的否定回答是（　）。", "No, there isn't.", "No, it isn't.", "No, there aren't.", "No, there doesn't."),
            Q("询问“有一些高楼吗？”应该说（　）。", "Are there any tall buildings?", "Is there any tall buildings?", "Are there a tall building?", "Do there tall buildings?"),
            Q("“Are there any houses?”的肯定回答是（　）。", "Yes, there are.", "Yes, there is.", "Yes, they are houses.", "Yes, it is."),
            Q("“Are there any bridges?”的否定回答是（　）。", "No, there aren't.", "No, there isn't.", "No, they don't.", "No, it isn't."),
            Q("“There is a river near the village.”的意思是（　）。", "村庄附近有一条河。", "河里有一个村庄。", "村庄里有一座桥。", "河离村庄很远。"),
            Q("“There are many trees in the forest.”的意思是（　）。", "森林里有许多树。", "树旁边有森林。", "森林里有一棵树。", "山上没有树。"),
            Q("描述“湖前面有一座小山”应说（　）。", "There is a hill in front of the lake.", "There are a hill in front of the lake.", "The lake is a hill.", "There is hill behind lake are."),
            Q("“The nature park is so quiet.”的意思是（　）。", "自然公园真安静。", "自然公园很热闹。", "自然公园很小。", "自然公园有高楼。"),
            Q("自然景物 river 表示（　）。", "河流", "湖泊", "高山", "森林"),
            Q("人工建筑 bridge 表示（　）。", "桥", "村庄", "房屋", "高楼"),
            M("自然景物有（　）。", ["forest", "river", "mountain", "building"], ["A", "B", "C"]),
            M("人们建造的事物有（　）。", ["bridge", "building", "house", "lake"], ["A", "B", "C"]),
            Q("补全句子：There（　）some boats on the lake.", "are", "is", "am", "be"),
            Q("补全对话：— Is there a mountain? — No,（　）。", "there isn't", "there aren't", "it isn't", "there doesn't"),
            Q("“some”常用于肯定句，“any”常用于（　）。", "疑问句或否定句", "所有肯定句", "祈使句", "感叹句"),
            Q("询问村庄里是否有房屋，可以说（　）。", "Are there any houses in the village?", "Is there houses in the village?", "Where are any houses village?", "Does village have are houses?"),
            Q("“Let's go boating.”的意思是（　）。", "我们去划船吧。", "我们去爬山吧。", "我们去游泳吧。", "我们去村庄吧。"),
            Q("“The water is clean.”的意思是（　）。", "水很干净。", "水很深。", "水很热。", "水很多。"),
            S2("询问公园景物，正确的句子是（　）。", ["Are there any trees beside the lake?", "Is there any trees beside the lake?", "Are there a tree beside the lake?", "Do there trees beside lake?"]),
        ]),
        ("第3课 综合运用", "综合练习：自然与人文景物、there be 疑问句和环保行为。读懂公园导览信息。", [
            Q("导览图显示公园中有一个湖，应说（　）。", "There is a lake in the park.", "There are a lake in the park.", "The park is a lake.", "There is lake are park."),
            Q("导览图显示村庄里有许多房子，应说（　）。", "There are many houses in the village.", "There is many houses in the village.", "There are many house in village.", "Many houses is village."),
            Q("选择正确的问答搭配（　）。", "Are there any trees? — Yes, there are.", "Are there any trees? — Yes, there is.", "Is there a bridge? — Yes, there are.", "Where is the lake? — No, there isn't."),
            Q("把“There is a river.”改成一般疑问句，应为（　）。", "Is there a river?", "Are there a river?", "Does there a river?", "Is a river there is?"),
            Q("把“There are some mountains.”改成一般疑问句，应为（　）。", "Are there any mountains?", "Is there any mountains?", "Are there some mountain?", "Do there mountains?"),
            Q("选择语序正确的句子（　）。", "There is a bridge over the river.", "There a bridge is over river.", "A bridge over is the river there.", "Over river there bridge a."),
            Q("“The village is between two hills.”的意思是（　）。", "村庄在两座小山之间。", "村庄在山上。", "两座小山在村庄里。", "村庄旁边有一座山。"),
            Q("mountain 和 hill 的区别通常是（　）。", "mountain 较高大，hill 较低小", "两者完全相反且无关", "hill 是河流", "mountain 是房屋"),
            Q("river 和 lake 的区别是（　）。", "river 是河流，lake 是湖泊", "两者都是高山", "river 是建筑，lake 是村庄", "两者意思完全相同"),
            Q("“There aren't any tall buildings.”表示（　）。", "没有高楼", "有许多高楼", "只有一座高楼", "高楼很漂亮"),
            M("下列句子结构正确的有（　）。", ["Is there a lake?", "Are there any houses?", "There are many trees.", "There is two bridges."], ["A", "B", "C"]),
            M("保护自然公园的做法有（　）。", ["take rubbish away", "protect trees", "keep water clean", "pick flowers freely"], ["A", "B", "C"]),
            Q("“Are there any fish in the river?”中的 fish 在这里表示（　）。", "鱼（复数形式仍可用 fish）", "一种植物", "一座桥", "一间房屋"),
            Q("“Yes, there is one.”中的 one 可指代前面的（　）。", "单数名词", "复数名词", "动词", "形容词"),
            Q("自然公园里看见美景，可以说（　）。", "The nature park is beautiful.", "The nature park can cook.", "The park is a teacher.", "There are beautiful."),
            Q("想问桥的位置，可以说（　）。", "Where is the bridge?", "Is there a bridge?", "What is the bridge?", "Where are bridge?"),
            Q("公园中若有两条河，应该使用（　）。", "There are two rivers.", "There is two rivers.", "There are two river.", "There be rivers two."),
            Q("游览自然公园时应（　）。", "遵守规则并爱护环境", "随意丢垃圾", "在树上刻字", "捕捉野生动物"),
            Q("“The air is fresh.”中的 fresh 描述（　）。", "空气清新", "食物甜", "人物勤奋", "星期安排"),
            Q("读公园地图时，方位词能帮助我们（　）。", "确定景物之间的位置", "判断食物味道", "描述人物性格", "安排每周课程"),
            S2("本单元主要学会了（　）。", ["询问并描述自然公园中的景物", "询问饮食需求", "介绍人物特点", "表达个人本领"]),
        ]),
    ]),
    ("复习与检测", [
        ("第1课 Revision 1", "Revision 1: Units 1–3。复习人物特点、每周安排和饮食表达。", build_vocab([
            ("kind", "体贴的；慈祥的"), ("strict", "要求严格的；严厉的"),
            ("helpful", "有用的；愿意帮忙的"), ("Thursday", "星期四"),
            ("do homework", "做作业"), ("read books", "看书"), ("sandwich", "三明治"),
            ("tea", "茶；茶水"), ("healthy", "健康的"), ("delicious", "美味的；可口的"),
        ])),
        ("第2课 Revision 2", "Revision 2: Units 4–6。复习能力、房间方位和自然公园景物。", build_vocab([
            ("do kung fu", "练武术"), ("draw cartoons", "画漫画"), ("swim", "游泳"),
            ("clock", "时钟；钟"), ("in front of", "在……前面"), ("behind", "在……后面"),
            ("forest", "森林；林区"), ("river", "河；江"), ("bridge", "桥"), ("village", "村庄；村镇"),
        ])),
    ]),
]


if __name__ == "__main__":
    run(r"content/primary/pep/grade5/volume1/english", "英语上册", UNITS)
