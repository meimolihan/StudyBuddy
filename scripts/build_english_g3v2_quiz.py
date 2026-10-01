# -*- coding: utf-8 -*-
"""三年级下册英语（人教版 PEP 2025 春）全部单元自测题生成脚本。"""
import sys
import random
from pathlib import Path


def _find_project_root(start):
    p = start
    for _ in range(6):
        if (p / "content").is_dir():
            return p
        p = p.parent
    raise SystemExit("找不到项目根目录（content/）")


def _find_engine_dir(root):
    for cand in (Path(__file__).resolve().parent,
                 root / ".workbuddy" / "skills" / "interactive-quiz-html" / "scripts"):
        if (cand / "build_quiz_html.py").exists():
            return cand
    raise SystemExit("找不到引擎 build_quiz_html.py")


PROJECT_ROOT = _find_project_root(Path(__file__).resolve().parent)
sys.path.insert(0, str(_find_engine_dir(PROJECT_ROOT)))
from build_quiz_html import build as engine_build  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _quizlib import S, S2, M, run  # noqa: E402

RNG = random.Random(20260301)


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
    letters = ["A", "B", "C", "D", "E", "F", "G", "H", "K", "L", "M", "N", "P", "R", "S", "T"]
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
    ("第一单元 Meeting new people 结识新朋友", [
        ("第1课 核心词汇", "📣 Today's words: China / UK / USA / Canada / new / friend。认识新朋友，先说 nationality！", build_vocab([
            ("China", "中国"), ("UK", "英国"), ("USA", "美国"), ("Canada", "加拿大"),
            ("new", "新的"), ("friend", "朋友"), ("teacher", "老师"), ("student", "学生"),
            ("welcome", "欢迎"), ("today", "今天"),
        ])),
        ("第2课 句型与对话", "📣 Sentences: Where are you from? / I'm from … / We have two new friends. 大方介绍自己吧！", [
            Q("询问「你来自哪里？」说（　）。", "Where are you from?", "What's your name?", "How old are you?", "Who is he?"),
            Q("「I'm from China.」的意思是（　）。", "我来自中国。", "我喜欢中国。", "我去中国。", "中国很大。"),
            Q("介绍新朋友可以说（　）。", "We have a new friend.", "I have a pen.", "This is my book.", "Open the door."),
            Q("欢迎新同学，说（　）。", "Welcome!", "Goodbye!", "Thank you!", "Sorry!"),
            Q("「Where are you from?」的正确回答是（　）。", "I'm from Canada.", "I'm nine.", "I'm fine.", "I like cats."),
            Q("「UK」指的是（　）。", "英国", "美国", "中国", "加拿大"),
            Q("「USA」指的是（　）。", "美国", "英国", "法国", "日本"),
            Q("「Canada」的意思是（　）。", "加拿大", "中国", "英国", "美国"),
            Q("见到新朋友打招呼说（　）。", "Nice to meet you.", "Nice to eat you.", "How do you do it?", "See you soon."),
            Q("「teacher」的意思是（　）。", "老师", "学生", "医生", "司机"),
            Q("「student」的意思是（　）。", "学生", "老师", "警察", "农民"),
            M("国家名有（　）。", ["China", "Canada", "UK", "banana"], ["A", "B", "C"]),
            M("介绍自己时可以说（　）。", ["I'm from China.", "My name is Li Ming.", "Nice to meet you.", "Close the window."], ["A", "B", "C"]),
            Q("「new」的意思是（　）。", "新的", "旧的", "好的", "大的"),
            Q("「friend」的意思是（　）。", "朋友", "家人", "同学桌", "邻居"),
            Q("和外国朋友交换信息，可以问（　）。", "Where are you from?", "How much is it?", "What time is it?", "What colour is it?"),
            Q("「welcome」作动词的意思是（　）。", "欢迎", "等待", "追赶", "帮助"),
            Q("「today」的意思是（　）。", "今天", "明天", "昨天", "每天"),
            Q("第一次见面，礼貌的说法是（　）。", "Nice to meet you.", "See you later.", "Good night.", "Long time no see!"),
            Q("介绍别人时用（　）。", "This is …", "I am …", "You are …", "It is …"),
            Q("「We have two new friends today.」的意思是（　）。", "今天我们有两名新朋友。", "我们今天去买东西。", "我们有两个苹果。", "明天有新朋友来。"),
            Q("与朋友告别时说（　）。", "Goodbye!", "Hello!", "Welcome!", "Come in!"),
            S2("本单元你学会了（　）。", ["用英语介绍自己和来自的国家", "做数学题", "背古诗", "画画"]),
        ]),
        ("第3课 综合运用", "📣 综合练习：国家名认读、问答搭配、字母复习。继续加油！", [
            Q("「China」的第一个字母是（　）。", "C", "K", "G", "D"),
            Q("选择正确的问答搭配：（　）。", "Where are you from? — I'm from the UK.", "Where are you from? — I'm fine.", "Where are you from? — I'm nine.", "Where are you from? — Thank you."),
            Q("「Canada」里有两个（　）。", "n", "a 有两个", "c 有两个", "d 有两个"),
            Q("下列哪个是国家名？（　）。", "USA", "apple", "cat", "book"),
            M("打招呼或问候的句子有（　）。", ["Nice to meet you.", "Good morning.", "Welcome!", "I'm hungry."], ["A", "B", "C"]),
            Q("「I'm a new student.」的意思是（　）。", "我是一名新学生。", "我是一名老师。", "我是新来的老师。", "我认识新学生。"),
            Q("「She is my friend.」的意思是（　）。", "她是我的朋友。", "他是我的朋友。", "她是我的老师。", "它是我朋友。"),
            Q("介绍来自英国的朋友：He is from（　）。", "the UK", "the USA", "China", "Canada"),
            Q("「welcome back」的意思是（　）。", "欢迎回来", "欢迎光临", "快回来", "再见"),
            Q("「make friends」的意思是（　）。", "交朋友", "做手工", "见家人", "问问题"),
            M("表达友好的做法有（　）。", ["主动打招呼", "微笑", "介绍自己", "不理不睬"], ["A", "B", "C"]),
            Q("「Where is he from?」问的是（　）。", "他来自哪里", "他是谁", "他几岁", "他喜欢什么"),
            Q("回答「He is from the USA.」的意思是（　）。", "他来自美国。", "他去了美国。", "他喜欢美国。", "他在美国工作。"),
            Q("「classmate」的意思是（　）。（拓展）", "同学", "老师", "家人", "朋友"),
            Q("「Hi, I'm Amy. I'm from the UK.」说了两件事：名字和（　）。", "来自的国家", "年龄", "爱好", "学校"),
            Q("字母 Cc 的大小写是（　）。", "C c", "G c", "C k", "O c"),
            Q("按字母表顺序，B 的后面是（　）。", "C", "A", "D", "E"),
            Q("「friend」的第一个字母是（　）。", "f", "p", "b", "t"),
            Q("新同学介绍完自己，你可以说（　）。", "Welcome to our class!", "Sit down and be quiet!", "Go away!", "I don't know you."),
            Q("「nationality」的意思是（　）。（拓展）", "国籍", "名字", "年龄", "爱好"),
            Q("「We are good friends.」的意思是（　）。", "我们是好朋友。", "我们去看朋友。", "我们是同学。", "我们要做朋友吗？"),
            S2("本单元你学会了（　）。", ["结交新朋友并介绍来自哪里", "写日记", "算数", "唱歌考级"]),
        ]),
    ]),
    ("第二单元 Expressing yourself 表达自己", [
        ("第1课 核心词汇", "📣 Today's words: big / small / long / short / fat / thin。学会用形容词描述身边事物！", build_vocab([
            ("big", "大的"), ("small", "小的"), ("long", "长的"), ("short", "短的；矮的"),
            ("fat", "胖的"), ("thin", "瘦的"), ("tall", "高的"), ("body", "身体"),
            ("tail", "尾巴"), ("ear", "耳朵"),
        ])),
        ("第2课 句型与对话", "📣 Sentences: It has a long tail. / Look at … 用形容词把事物描述得更生动！", [
            Q("「It has a long tail.」的意思是（　）。", "它有一条长尾巴。", "它很胖。", "它有大耳朵。", "它是长的。"),
            Q("描述大象鼻子长，说（　）。", "The elephant has a long nose.", "The elephant is long nose.", "Elephant like long.", "Nose, elephant, long!"),
            Q("「big」的反义词是（　）。", "small", "long", "fat", "tall"),
            Q("「long」的反义词是（　）。", "short", "big", "thin", "small"),
            Q("「fat」的意思是（　）。", "胖的", "瘦的", "高的", "矮的"),
            Q("「thin」的意思是（　）。", "瘦的", "胖的", "新的", "旧的"),
            Q("描述小老鼠，可以说（　）。", "It is small.", "It is big and fat.", "It is very tall.", "It is a horse."),
            Q("「Look at the monkey!」的意思是（　）。", "看那只猴子！", "摸那只猴子。", "喂那只猴子。", "抓住猴子！"),
            Q("描述长颈鹿很高，说（　）。", "The giraffe is tall.", "The giraffe is short.", "The giraffe has big ears.", "The giraffe is fat."),
            Q("「body」的意思是（　）。", "身体", "头", "脚", "手"),
            Q("「tail」的意思是（　）。", "尾巴", "耳朵", "鼻子", "嘴巴"),
            M("形容词有（　）。", ["big", "long", "thin", "banana"], ["A", "B", "C"]),
            M("It has a … 可以描述（　）。", ["long tail", "big body", "small nose", "run fast"], ["A", "B", "C"]),
            Q("「short」可以形容（　）。", "短的或矮的", "只有长的", "只有高的", "胖的"),
            Q("描述自己，可以说（　）。", "I am tall.", "I tall.", "Me tall is.", "Tall I am go."),
            Q("「ear」的意思是（　）。", "耳朵", "眼睛", "鼻子", "嘴巴"),
            Q("兔子尾巴短，说（　）。", "The rabbit has a short tail.", "The rabbit tail long.", "Rabbit short is tail.", "The rabbit is a tail."),
            Q("「has」用在（　）后面。", "he / she / it", "I", "you", "they"),
            Q("「It has big ears.」的意思是（　）。", "它有大耳朵。", "它有大眼睛。", "它耳朵小。", "它有个包。"),
            Q("描述事物先说（　）再补充细节更好。", "整体特征（大小、高矮）", "随便乱说", "只说颜色", "什么也不说"),
            Q("「fat cat」的意思是（　）。", "胖猫", "帽子", "旧猫", "花猫"),
            Q("表达自己的喜好可以说（　）。", "I like …", "I has …", "I am … over.", "Me like go."),
            S2("本单元你学会了（　）。", ["用形容词描述人和动物的外形", "数数到 100", "写作文", "背课文"]),
        ]),
        ("第3课 综合运用", "📣 综合练习：形容词配对、描述顺序、It has 句型。小试身手！", [
            Q("「big」的第一个字母是（　）。", "b", "d", "p", "g"),
            Q("选择正确的句子：（　）。", "The elephant has a long nose.", "The elephant long a has nose.", "The elephant have long nose.", "Elephant the has long nose."),
            Q("「tall」的意思是（　）。", "高的", "矮的", "长的", "短的"),
            Q("与「thin」意思相近的描述是（　）。", "not fat", "very fat", "very tall", "very big"),
            M("描述外貌的词有（　）。", ["tall", "fat", "small", "apple"], ["A", "B", "C"]),
            Q("「The mouse is small.」的意思是（　）。", "老鼠很小。", "老鼠很大。", "老鼠很胖。", "老鼠很高。"),
            Q("「long」的第一个字母是（　）。", "l", "r", "n", "s"),
            Q("描写动物顺序更合理的是（　）。", "先说整体（大小），再说部位（尾巴、耳朵）", "先说尾巴再说名字", "想到什么说什么", "不说"),
            Q("「It has a big body.」的意思是（　）。", "它身体很大。", "它尾巴很大。", "它身体小。", "它有身体。"),
            Q("he 后面用（　）。", "has", "have", "had 不学", "having"),
            Q("「short hair」的意思是（　）。（拓展）", "短发", "长头发", "帽子", "围巾"),
            Q("「My tail is long.」换成 It has 句型是（　）。", "It has a long tail.", "It have a long tail.", "It is long tail.", "It long tail."),
            Q("描述爸爸，可以说（　）。", "My father is tall and thin.", "My father tall thin is.", "Father my is tall thin.", "Tall my father thin."),
            M("以下说法正确的有（　）。", ["The cat is fat.", "It has big ears.", "I am thin.", "Banana has a long book."], ["A", "B", "C"]),
            Q("「small」的第一个字母是（　）。", "s", "c", "z", "w"),
            Q("「Look at my tail!」的意思是（　）。", "看我的尾巴！", "摸我的尾巴。", "我的尾巴疼。", "尾巴给我。"),
            Q("大象的特征是（　）。（常识）", "长鼻子、大身体", "长脖子", "短尾巴、大耳朵像扇子也是大象", "小个子、跑得快"),
            Q("「thin」和「fat」是一对（　）。", "反义词", "同义词", "数字", "颜色"),
            Q("下列句子正确的是（　）。", "The giraffe is tall.", "The giraffe tall is.", "Giraffe the tall is.", "The giraffe am tall."),
            Q("描述朋友让他开心，可以说（　）。", "You are so tall!", "You are bad!", "Go away!", "I don't like you."),
            S2("本单元你学会了（　）。", ["用形容词大方表达和描述", "做算术", "写生字", "背单词表"]),
        ]),
    ]),
    ("第三单元 Learning better 更好地学习", [
        ("第1课 核心词汇", "📣 Today's words: see / hear / smell / taste / touch。五感并用，学习更高效！", build_vocab([
            ("see", "看见"), ("hear", "听见"), ("smell", "闻"), ("taste", "尝"),
            ("touch", "摸"), ("eye", "眼睛"), ("nose", "鼻子"), ("mouth", "嘴巴"),
            ("hand", "手"), ("learn", "学习"),
        ])),
        ("第2课 句型与对话", "📣 Sentences: I see with my eyes. / I hear with my ears. 用五感探索世界！", [
            Q("「I see with my eyes.」的意思是（　）。", "我用眼睛看。", "我用耳朵听。", "我用手摸。", "我用鼻子闻。"),
            Q("「I hear with my ears.」的意思是（　）。", "我用耳朵听。", "我用眼睛看。", "我用嘴巴尝。", "我用手摸。"),
            Q("用鼻子做的是（　）。", "smell", "see", "taste", "touch"),
            Q("用手做的是（　）。", "touch", "hear", "see", "smell"),
            Q("用嘴巴做的是（　）。", "taste", "hear", "touch", "see"),
            Q("「eye」的意思是（　）。", "眼睛", "耳朵", "鼻子", "嘴巴"),
            Q("「mouth」的意思是（　）。", "嘴巴", "鼻子", "手", "脚"),
            Q("闻花香用（　）。", "nose", "eye", "ear", "hand"),
            Q("听音乐用（　）。", "ears", "eyes", "hands", "nose"),
            Q("「learn」的意思是（　）。", "学习", "玩", "睡觉", "跑步"),
            M("感官动词有（　）。", ["see", "hear", "touch", "jump"], ["A", "B", "C"]),
            M("I taste with my mouth. 可以尝（　）。", ["apple", "candy", "rice", "colour"], ["A", "B", "C"]),
            Q("「smell」的意思是（　）。", "闻", "看", "听", "摸"),
            Q("「touch」的意思是（　）。", "摸", "闻", "听", "看"),
            Q("上课认真听讲，用（　）。", "ears", "nose", "hands", "feet"),
            Q("看书用（　）。", "eyes", "ears", "nose", "mouth"),
            Q("「I touch with my hands.」的意思是（　）。", "我用手摸。", "我用手看。", "我用手听。", "我用手闻。"),
            Q("尝味道要注意（　）。", "先问过大人再尝", "什么都直接吃", "随便闻", "闭眼乱摸"),
            Q("「with」的意思是（　）。", "用；以", "和……一起玩", "有", "没有"),
            Q("保护眼睛，应该（　）。", "看书姿势端正、少看屏幕", "躺着看书", "摸黑看书", "一直玩手机"),
            Q("「I smell with my nose.」的意思是（　）。", "我用鼻子闻。", "我用鼻子看。", "我鼻子很大。", "我用嘴闻。"),
            Q("五感帮我们（　）。", "更好地认识世界", "长得更高", "跑得更快", "什么都不做"),
            S2("本单元你学会了（　）。", ["用英语说五感和它们的用处", "写日记", "背古诗", "画画"]),
        ]),
        ("第3课 综合运用", "📣 综合练习：感官与器官配对、句型操练。越练越棒！", [
            Q("「see」的第一个字母是（　）。", "s", "c", "z", "x"),
            Q("配对正确的是（　）。", "ears — hear", "ears — see", "eyes — hear", "nose — touch"),
            Q("「hear」的第一个字母是（　）。", "h", "n", "l", "t"),
            Q("下列器官和感官配对错误的是（　）。", "hand — smell", "nose — smell", "eye — see", "mouth — taste"),
            M("学习时可以（　）。", ["眼看", "耳听", "动手写", "只睡觉"], ["A", "B", "C"]),
            Q("「What do you see?」的正确回答是（　）。", "I see a bird.", "I hear a bird.", "I taste a bird.", "I smell nice."),
            Q("「I hear a dog.」的意思是（　）。", "我听到狗叫声。", "我看见一只狗。", "我摸到狗了。", "我闻到狗了。"),
            Q("「nose」里有一个（　）。", "o", "两个 o", "a", "e 开头"),
            Q("「mouth」的第一个字母是（　）。", "m", "n", "w", "h"),
            Q("「hand」的意思是（　）。", "手", "头", "脚", "腿"),
            Q("「eye」的复数是（　）。（拓展）", "eyes", "eye", "eyeses", "eyes'"),
            Q("摸东西前要注意（　）。", "是否安全、干净", "摸什么都行", "越烫越好", "不用看"),
            Q("「I see with my eyes.」中 with 后面是（　）。", "工具（身体部位）", "颜色", "数字", "动物"),
            Q("「hear」和「see」都是（　）。", "感官动词", "颜色词", "数字词", "国家名"),
            Q("尝出甜味，可以说（　）。", "It tastes sweet.", "It sees sweet.", "It hears sweet.", "It smells foot."),
            Q("「sweet」的意思是（　）。（拓展）", "甜的", "苦的", "酸的", "辣的"),
            Q("学英语要多（　）。", "听、说、读、写", "只看不听", "只写不说", "不学也行"),
            Q("「I learn English every day.」的意思是（　）。", "我每天学英语。", "我教英语。", "我讨厌英语。", "我买英语书。"),
            Q("「touch」的第一个字母是（　）。", "t", "d", "p", "b"),
            Q("感官让我们（　）。", "感知世界、学到更多", "变高", "变胖", "睡得香"),
            S2("本单元你学会了（　）。", ["五感与器官的英语表达及用法", "算数", "写生字", "背课文"]),
        ]),
    ]),
    ("第四单元 Healthy food 健康食物", [
        ("第1课 核心词汇", "📣 Today's words: rice / noodles / fish / egg / milk。吃得健康，长得棒棒！", build_vocab([
            ("rice", "米饭"), ("noodles", "面条"), ("fish", "鱼"), ("egg", "鸡蛋"),
            ("milk", "牛奶"), ("vegetable", "蔬菜"), ("fruit", "水果"), ("bread", "面包"),
            ("healthy", "健康的"), ("eat", "吃"),
        ])),
        ("第2课 句型与对话", "📣 Sentences: I like … / Have some … / They are healthy. 学会用英语聊食物！", [
            Q("「I like rice.」的意思是（　）。", "我喜欢米饭。", "我讨厌米饭。", "我在吃米饭。", "米饭很好。"),
            Q("请别人吃鸡蛋，说（　）。", "Have some eggs.", "Have some milk.", "I like eggs.", "Eggs are red."),
            Q("「They are healthy.」的意思是（　）。", "它们很健康。", "它们很贵。", "它们很大。", "它们是热的。"),
            Q("「noodles」的意思是（　）。", "面条", "米饭", "面包", "蛋糕"),
            Q("「vegetable」的意思是（　）。", "蔬菜", "水果", "肉", "零食"),
            Q("「milk」的意思是（　）。", "牛奶", "水", "果汁", "茶"),
            Q("「fruit」的意思是（　）。", "水果", "蔬菜", "米饭", "肉"),
            Q("早餐喝牛奶可以说（　）。", "I drink milk.", "I eat milk.", "I see milk.", "I hear milk."),
            Q("「bread」的意思是（　）。", "面包", "米饭", "鸡蛋", "鱼"),
            Q("「eat」的意思是（　）。", "吃", "喝", "睡", "跑"),
            M("健康的食物有（　）。", ["vegetables", "fruit", "fish", "candy 每天一大包"], ["A", "B", "C"]),
            M("I like … 可以说（　）。", ["I like eggs.", "I like fruit.", "I like rice.", "I like junk food only."], ["A", "B", "C"]),
            Q("「fish」的意思是（　）。", "鱼", "鸡", "鸭", "牛"),
            Q("「rice」的第一个字母是（　）。", "r", "l", "n", "m"),
            Q("挑食的坏处是（　）。", "营养不均衡", "长得更高", "更聪明", "没有坏处"),
            Q("「egg」的意思是（　）。", "鸡蛋", "鸭蛋", "蛋白粉", "面包"),
            Q("「healthy food」的意思是（　）。", "健康食物", "垃圾食品", "热食", "快餐"),
            Q("吃饭前应该（　）。", "洗手", "跑步", "睡觉", "看电视"),
            Q("「Have some fruit.」的意思是（　）。", "吃点水果吧。", "水果在哪？", "我不吃水果。", "水果很贵。"),
            Q("「like」的意思是（　）。", "喜欢", "讨厌", "看见", "听见"),
            Q("健康饮食建议（　）。", "荤素搭配、多吃蔬果", "只吃肉", "只吃糖", "不吃早饭"),
            Q("「I don't like …」的意思是（　）。（拓展）", "我不喜欢……", "我很喜欢……", "我有一点喜欢……", "我讨厌自己。"),
            S2("本单元你学会了（　）。", ["用英语说食物并懂得健康饮食", "算账", "写日记", "背单词表"]),
        ]),
        ("第3课 综合运用", "📣 综合练习：食物分类、点餐对话、健康习惯。做得不错！", [
            Q("「rice」和「noodles」都是（　）。", "主食", "水果", "饮料", "蔬菜"),
            Q("「milk」的第一个字母是（　）。", "m", "n", "w", "k"),
            Q("配对正确的是（　）。", "egg — protein 蛋白质", "egg — 水果", "milk — 蔬菜", "rice — 饮料"),
            M("早餐可以吃（　）。", ["eggs", "milk", "bread", "石头"], ["A", "B", "C"]),
            Q("「Have some bread.」的正确回答是（　）。", "Thank you!", "You're welcome to eat.", "No eat!", "Bread is run."),
            Q("「vegetable」的第一个字母是（　）。", "v", "w", "f", "b"),
            Q("下列哪种是不健康的习惯？（　）。", "天天喝碳酸饮料", "每天吃水果", "按时吃饭", "多吃蔬菜"),
            Q("「I like noodles.」的意思是（　）。", "我喜欢面条。", "我做面条。", "我买面条。", "面条喜欢我。"),
            Q("「healthy」的第一个字母是（　）。", "h", "j", "l", "n"),
            Q("「drink」的意思是（　）。（拓展）", "喝", "吃", "睡", "跑"),
            Q("水果和蔬菜富含（　）。（常识）", "维生素", "塑料", "沙子", "石头"),
            Q("「They are healthy.」中 they 指（　）。", "前面提到的食物（复数）", "一个人", "动物们", "颜色"),
            Q("「Have some rice.」的意思是（　）。", "吃点米饭吧。", "米饭没了。", "煮米饭。", "米饭很香。"),
            Q("「I have an egg.」的意思是（　）。", "我有一个鸡蛋。", "我吃掉鸡蛋。", "我讨厌鸡蛋。", "鸡蛋是我的。"),
            Q("「food」的意思是（　）。", "食物", "脚", "好的", "木头"),
            Q("挑食的孩子应该（　）。", "各种食物都尝一尝", "只吃零食", "不吃饭", "只吃肉"),
            M("礼貌用餐的说法有（　）。", ["Thank you!", "It's yummy.", "Have some more.", "把菜倒地上"], ["A", "B", "C"]),
            Q("「yummy」的意思是（　）。（拓展）", "好吃的", "难吃的", "烫的", "冷的"),
            Q("「eat」的第一个字母是（　）。", "e", "a", "i", "t"),
            Q("一日三餐要（　）。", "按时吃", "想起来才吃", "不吃早饭", "睡前大吃"),
            S2("本单元你学会了（　）。", ["食物类单词与健康饮食习惯", "写代码", "背古诗", "画画"]),
        ]),
    ]),
    ("第五单元 Old toys 旧玩具", [
        ("第1课 核心词汇", "📣 Today's words: toy / ball / doll / boat / car。旧玩具也有新玩法，位置词要记牢！", build_vocab([
            ("toy", "玩具"), ("ball", "球"), ("doll", "玩具娃娃"), ("boat", "小船"),
            ("car", "小汽车"), ("kite", "风筝"), ("old", "旧的"), ("new", "新的"),
            ("under", "在……下面"), ("chair", "椅子"),
        ])),
        ("第2课 句型与对话", "📣 Sentences: Where is my toy? / It's under the chair. 学会用英语找东西！", [
            Q("询问「我的玩具在哪里？」说（　）。", "Where is my toy?", "What is my toy?", "Who is my toy?", "How is my toy?"),
            Q("「It's under the chair.」的意思是（　）。", "它在椅子下面。", "它在椅子上面。", "它是椅子。", "椅子在下面。"),
            Q("「ball」的意思是（　）。", "球", "娃娃", "风筝", "船"),
            Q("「doll」的意思是（　）。", "玩具娃娃", "球", "汽车", "狗"),
            Q("「boat」的意思是（　）。", "小船", "火车", "飞机", "自行车"),
            Q("「kite」的意思是（　）。", "风筝", "球", "船", "汽车"),
            Q("「toy」的意思是（　）。", "玩具", "工具", "食物", "衣服"),
            Q("「old」的反义词是（　）。", "new", "big", "small", "long"),
            Q("「under」的意思是（　）。", "在……下面", "在……上面", "在……里面", "在……旁边"),
            Q("球在桌子上，说（　）。", "The ball is on the desk.", "The ball is under the desk.", "The ball is a desk.", "Desk the ball is."),
            M("玩具类单词有（　）。", ["ball", "doll", "kite", "rice"], ["A", "B", "C"]),
            M("Where is …? 的正确回答有（　）。", ["It's on the desk.", "It's under the bed.", "It's in the box.", "It's nine."], ["A", "B", "C"]),
            Q("「in the box」的意思是（　）。", "在盒子里", "在盒子下", "在盒子上", "盒子没了"),
            Q("「chair」的意思是（　）。", "椅子", "桌子", "床", "门"),
            Q("分享旧玩具，可以说（　）。", "Let's play with my old toys.", "My toys are yours only not.", "Go buy new ones!", "I don't share."),
            Q("「car」的意思是（　）。", "小汽车", "飞机", "船", "风筝"),
            Q("「on」的意思是（　）。", "在……上面", "在……下面", "在……里面", "不"),
            Q("「Where is my kite? — It's in your room.」的意思是（　）。", "风筝在你的房间里。", "风筝在房间外。", "风筝坏了。", "我没有风筝。"),
            Q("整理玩具应该（　）。", "玩完放回原处", "随便乱扔", "塞床底下", "给别人家扔"),
            Q("「bed」的意思是（　）。（拓展）", "床", "椅子", "桌子", "柜子"),
            Q("「old toys」的意思是（　）。", "旧玩具", "新玩具", "旧衣服", "老朋友"),
            Q("找不到东西时先（　）。", "回忆放在哪里再找", "大哭", "怪别人", "不找了"),
            S2("本单元你学会了（　）。", ["玩具类单词和位置问答", "算数", "写日记", "背课文"]),
        ]),
        ("第3课 综合运用", "📣 综合练习：位置介词、问答操练、物主代词入门。继续加油！", [
            Q("「ball」的第一个字母是（　）。", "b", "d", "p", "g"),
            Q("「under」的第一个字母是（　）。", "u", "a", "o", "e"),
            Q("「The doll is on the bed.」的意思是（　）。", "娃娃在床上。", "娃娃在床下。", "娃娃在椅子下。", "床在娃娃上。"),
            Q("选择正确的问答：（　）。", "Where is my ball? — It's under the bed.", "Where is my ball? — It's a ball.", "Where is my ball? — Yes, it is.", "Where is my ball? — I'm nine."),
            M("位置词有（　）。", ["on", "in", "under", "ball"], ["A", "B", "C"]),
            Q("「It's in the desk.」的意思是（　）。", "它在桌子里。", "它在桌子上。", "它在桌子下。", "它是桌子。"),
            Q("「toy」的复数是（　）。（拓展）", "toys", "toies", "toy", "toyss"),
            Q("「boat」的第一个字母是（　）。", "b", "d", "c", "k"),
            Q("和「old」意思相对的是（　）。", "new", "young 拓展", "tall", "fat"),
            Q("「Let's play!」的意思是（　）。", "我们玩吧！", "我们走吧！", "我们吃吧！", "我们睡吧！"),
            Q("「kite」的发音第一个音是（　）。", "/k/", "/g/", "/s/", "/t/"),
            Q("玩具车在地上（desk 下），说（　）。", "The toy car is under the desk.", "The toy car is on the desk.", "The toy car is the desk.", "Toy car desk is under."),
            Q("「share」的意思是（　）。（拓展）", "分享", "独自玩", "扔掉", "藏起来"),
            Q("「car」的发音第一个音是（　）。", "/k/", "/g/", "/s/", "/d/"),
            Q("「My kite is old.」的意思是（　）。", "我的风筝旧了。", "我的风筝新。", "我的风筝高。", "风筝是我。"),
            M("爱惜物品的做法有（　）。", ["玩完收拾好", "不乱扔", "坏了自己先修或请人修", "故意摔坏"], ["A", "B", "C"]),
            Q("「Where」问的是（　）。", "地点", "时间", "人物", "数量"),
            Q("「desk」的意思是（　）。", "书桌", "椅子", "床", "门"),
            Q("「The ball is not on the chair. It's（　）the chair.」（图：球在椅下）", "under", "on", "in", "at"),
            Q("「put away」的意思是（　）。（拓展）", "放好；收起来", "拿出来", "扔掉", "卖掉"),
            Q("整理房间时可以说（　）。", "Let me put my toys away.", "Let me throw my toys.", "Toys, go away!", "I don't clean."),
            S2("本单元你学会了（　）。", ["玩具与位置的表达、整理好习惯", "做算术", "写生字", "背单词表"]),
        ]),
    ]),
    ("第六单元 Numbers in life 生活中的数字", [
        ("第1课 核心词汇", "📣 Today's words: eleven / twelve / thirteen / fourteen / fifteen。数字王国再进五城！", build_vocab([
            ("eleven", "十一"), ("twelve", "十二"), ("thirteen", "十三"), ("fourteen", "十四"),
            ("fifteen", "十五"), ("number", "数字"), ("count", "数；计算"), ("how many", "多少"),
            ("many", "许多"), ("use", "使用"),
        ])),
        ("第2课 句型与对话", "📣 Sentences: How many …? / I have twelve …. 数字让生活更方便！", [
            Q("「eleven」的意思是（　）。", "十一", "十二", "十", "二十"),
            Q("「twelve」的意思是（　）。", "十二", "十一", "十三", "二十"),
            Q("「thirteen」的意思是（　）。", "十三", "三十", "十四", "十五"),
            Q("「fifteen」的意思是（　）。", "十五", "五十", "十四", "十三"),
            Q("「How many books?」问的是（　）。", "多少本书", "什么书", "谁的书", "哪本书"),
            Q("「I have fourteen crayons.」的意思是（　）。", "我有十四支蜡笔。", "我有四支蜡笔。", "我有四十支蜡笔。", "我要十四支蜡笔。"),
            Q("「count」的意思是（　）。", "数；计算", "数学习题不", "唱歌", "画画"),
            Q("7 + 6 = （　），用英语说是（　）。", "thirteen", "twelve", "fourteen", "fifteen"),
            Q("「number」的意思是（　）。", "数字", "字母", "颜色", "名字"),
            Q("「how many」后面接（　）。", "可数名词复数", "单数", "动词原形", "形容词"),
            M("数字词有（　）。", ["eleven", "thirteen", "fifteen", "egg"], ["A", "B", "C"]),
            M("生活中用到数字的地方有（　）。", ["门牌号", "电话号码", "车牌", "颜色"], ["A", "B", "C"]),
            Q("「ten」+「three」=（　）。", "thirteen", "twelve", "eleven", "fourteen"),
            Q("「twelve」的第一个字母是（　）。", "t", "s", "f", "e"),
            Q("「fourteen」的意思是（　）。", "十四", "四十", "十五", "十三"),
            Q("按顺序：eleven, twelve, （　）。", "thirteen", "ten", "fifteen", "fourteen"),
            Q("「I count from one to fifteen.」的意思是（　）。", "我从一数到十五。", "我数了一十五个。", "我十五岁。", "我不会数数。"),
            Q("「many」的意思是（　）。", "许多", "很少", "没有", "一点"),
            Q("「use」的意思是（　）。", "使用", "有用", "旧的", "我们的"),
            Q("超市小票上的数字表示（　）。", "价格和数量", "颜色", "名字", "天气"),
            Q("「How many pens do you have?」的正确回答是（　）。", "I have twelve pens.", "I like pens.", "Pens are red.", "Yes, I do."),
            Q("「Numbers are useful.」的意思是（　）。", "数字很有用。", "数字很多。", "数字很难。", "数字很好看。"),
            S2("本单元你学会了（　）。", ["11~15 的数字表达和 How many 问答", "写作文", "背古诗", "画画"]),
        ]),
        ("第3课 综合运用", "📣 综合练习：数字认读、加减表达、生活应用。alphabet 后再冲数字关！", [
            Q("「eleven」的第一个字母是（　）。", "e", "a", "i", "l"),
            Q("「thirteen」里有两个（　）。", "e", "t", "c", "r"),
            Q("8 + 7 = （　）。", "fifteen", "thirteen", "twelve", "fourteen"),
            Q("「fifteen」和「fifty」的意思（　）。（辨析）", "分别是 15 和 50，不同", "一样", "都是 5", "无法比较"),
            M("11~15 的词有（　）。", ["eleven", "twelve", "fourteen", "ten"], ["A", "B", "C"]),
            Q("「How many apples?」的正确回答是（　）。", "Twelve apples.", "Apple is red.", "I like apples.", "Apples are fruit."),
            Q("「count」的第一个字母是（　）。", "c", "k", "s", "g"),
            Q("5 + 9 = （　）。", "fourteen", "fifteen", "thirteen", "twelve"),
            Q("「eleven」的发音开头是（　）。", "/i/", "/e/", "/a/", "/o/"),
            Q("「How many days in a week?」回答（　）。", "Seven.", "Eleven.", "Twelve.", "Fifteen."),
            Q("「thirteen」的构成：three + （　）。", "-teen", "-ty", "-tion", "-ing"),
            Q("「fifteen」的构成：（　）+ teen。", "fif", "five", "fiv", "fifty"),
            Q("4 + 8 = （　）。", "twelve", "thirteen", "eleven", "fourteen"),
            Q("「How many seasons in a year?」回答（　）。（常识）", "Four.", "Fourteen.", "Twelve.", "Fifteen."),
            Q("「useful」的意思是（　）。（拓展）", "有用的", "用过的", "用吧", "无用的"),
            Q("10 + 2 = （　）。", "twelve", "thirteen", "eleven", "fourteen"),
            Q("「How many」和「How much」的区别（　）。（拓展）", "how many 问可数数量，how much 问不可数量或价格", "一样", "都是问价格", "都是问年龄"),
            Q("「I see fifteen birds.」的意思是（　）。", "我看见十五只鸟。", "我看见五只鸟。", "我看见五十只鸟。", "鸟看见我。"),
            Q("「many」的第一个字母是（　）。", "m", "n", "a", "h"),
            Q("「Numbers in life」的意思是（　）。", "生活中的数字", "数字游戏", "数字书", "数学生活"),
            Q("数东西时要（　）。", "不重不漏、按顺序数", "随便数", "只数一半", "数字说啥都行"),
            S2("本学期你学会了（　）。", ["字母表、问候、描述、五感、食物、玩具和 11~15 的数字", "微积分", "写作文", "物理"]),
        ]),
    ]),
    ("复习与检测", [
        ("第1课 Revision 1（Units 1~3）", "📣 复习时间：结识新朋友、表达自己、五感学习三个单元大盘点。看看你记住了多少！", build_vocab([
            ("China", "中国"), ("friend", "朋友"), ("welcome", "欢迎"), ("big", "大的"),
            ("small", "小的"), ("long", "长的"), ("short", "短的；矮的"), ("see", "看见"),
            ("hear", "听见"), ("learn", "学习"),
        ])),
        ("第2课 Revision 2（Units 4~6）", "📣 复习时间：健康食物、旧玩具、数字三个单元大盘点。加油，期末冲刺！", build_vocab([
            ("rice", "米饭"), ("noodles", "面条"), ("milk", "牛奶"), ("healthy", "健康的"),
            ("toy", "玩具"), ("ball", "球"), ("under", "在……下面"), ("chair", "椅子"),
            ("eleven", "十一"), ("fifteen", "十五"),
        ])),
    ]),
]


if __name__ == "__main__":
    run(r"content/primary/pep/grade3/volume2/english", "英语下册", UNITS)
