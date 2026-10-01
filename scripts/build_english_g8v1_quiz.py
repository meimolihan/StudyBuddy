# -*- coding: utf-8 -*-
"""人教版（2025 新教材）初中二年级上册英语全部单元交互自测题生成脚本。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _quizlib import S, S2, M, run  # noqa: E402
from _concepts import concept_lessons  # noqa: E402


def L(entries, seed):
    return concept_lessons(entries, seed=seed)


UNITS = [
    ("第一单元 Happy Holiday", [
        ("第1课 Unit 1 Happy Holiday", "📣 假期总是让人期待。想一想：用英语说说你假期去了哪里、做了什么。", L([
            ("sightseeing", "游览观光，常搭配 go sightseeing 表示去观光"),
            ("seaside", "海边，海滨，如 spend the summer at the seaside 在海边过夏天"),
            ("souvenir", "纪念品，人们在旅行中买来留作纪念的物品"),
            ("memorable", "难忘的，值得记住的，如 a memorable trip 一次难忘的旅行"),
            ("take photos", "拍照，摄影，如 take photos of the beautiful scenery 拍下美丽的风景"),
            ("have a picnic", "去野餐，带食物到户外一起吃"),
            ("go camping", "去野营，在户外搭帐篷度过假期"),
            ("visit the museum", "参观博物馆，观看里面的各种展品"),
            ("went", "go 的过去式，表示过去去了某地，如 went to Beijing 去了北京"),
            ("ate", "eat 的过去式，表示过去吃了某物，如 ate delicious food 吃了美味的食物"),
            ("一般过去时的构成", "主语+动词的过去式，表示过去发生的动作或存在的状态"),
            ("Where did you go on vacation?", "用一般过去时询问对方假期去了哪里，回答常用 I went to..."),
        ], 20261671)),
    ]),
    ("第二单元 Home Sweet Home", [
        ("第1课 Unit 2 Home Sweet Home", "📣 家是我们温暖的港湾。想一想：你能用英语说出几件家务活？", L([
            ("chore", "家务活，家里需要做的日常杂事"),
            ("sweep the floor", "扫地，把地板打扫干净"),
            ("take out the rubbish", "倒垃圾，把垃圾拿出去扔掉"),
            ("make the bed", "整理床铺，把被子铺平整"),
            ("do the dishes", "洗碗，饭后清洗餐具"),
            ("fold the clothes", "叠衣服，把洗好的衣服叠整齐"),
            ("clean the living room", "打扫客厅，让客厅干净整洁"),
            ("water the plants", "给植物浇水，照顾家里的花草"),
            ("Could you please do sth.?", "礼貌地请求别人做某事的句型，语气比用 can 更委婉"),
            ("have to", "不得不，表示客观条件要求必须做某事"),
            ("stay out late", "在外面待到很晚才回家"),
            ("in a mess", "乱七八糟，形容房间或物品又脏又乱"),
        ], 20261672)),
    ]),
    ("第三单元 Same or Different?", [
        ("第1课 Unit 3 Same or Different?", "📣 每个人都是独一无二的。想一想：你和好朋友有哪些相同和不同之处？", L([
            ("taller", "更高的，tall 的比较级，表示两者中一方比另一方高"),
            ("friendlier", "更友好的，friendly 的比较级，变 y 为 i 再加 er"),
            ("more hard-working", "更勤奋的，多音节形容词前面加 more 构成比较级"),
            ("funnier", "更有趣的，funny 的比较级，表示比另一个人更有趣"),
            ("quieter", "更安静的，quiet 的比较级，表示比另一方更文静"),
            ("more outgoing", "更外向的，多音节形容词加 more，形容人更爱交际"),
            ("smarter", "更聪明的，smart 的比较级，表示比另一方更机灵"),
            ("stronger", "更强壮的，strong 的比较级，表示身体更强健"),
            ("形容词比较级的构成", "单音节词一般末尾加 er，多音节词前面加 more，两者进行比较时使用"),
            ("both...and...", "表示两者都，连接两个并列的成分，谓语动词用复数"),
            ("the same as", "与……相同，表示两个事物在某方面一样"),
            ("be different from", "与……不同，表示两个事物之间存在差异"),
        ], 20261673)),
    ]),
    ("第四单元 Amazing Plants and Animals", [
        ("第1课 Unit 4 Amazing Plants and Animals", "📣 自然界的动植物充满奇迹。想一想：你认为世界上最大的动物是什么？", L([
            ("cheetah", "猎豹，陆地上跑得最快的动物"),
            ("blue whale", "蓝鲸，世界上最大的动物"),
            ("giraffe", "长颈鹿，脖子很长的动物，是陆地上最高的动物"),
            ("bamboo", "竹子，熊猫最爱吃的植物，生长速度很快"),
            ("the biggest", "最大的，big 的最高级，表示三者及以上中最大"),
            ("the fastest", "最快的，fast 的最高级，表示速度排第一"),
            ("the most amazing", "最令人惊叹的，多音节形容词前加 the most 构成最高级"),
            ("the most beautiful", "最美丽的，多音节形容词加 the most，表示美丽程度最高"),
            ("the heaviest", "最重的，heavy 的最高级，变 y 为 i 再加 est"),
            ("形容词最高级的构成", "三者及以上比较用最高级，一般词尾加 est 或前面加 the most，前面要加 the"),
            ("one of the + 最高级", "表示最……之一，后面的名词要用复数形式"),
            ("as...as", "与……一样，两个 as 之间用形容词原级，表示程度相同"),
        ], 20261674)),
    ]),
    ("第五单元 What a Delicious Meal!", [
        ("第1课 Unit 5 What a Delicious Meal!", "📣 美食让人心情愉快。想一想：做一道菜一般要按什么顺序进行？", L([
            ("delicious", "美味的，可口的，形容食物好吃"),
            ("sugar", "糖，一种常见的调味品，是不可数名词"),
            ("salt", "盐，做菜时用来调味的白色颗粒，是不可数名词"),
            ("cheese", "奶酪，用牛奶制成的食品，是不可数名词"),
            ("add...to...", "把……加到……里，如 add some sugar to the tea 往茶里加点糖"),
            ("cut up", "切碎，把食物切成小块，如 cut up the tomatoes 把西红柿切碎"),
            ("mix...together", "把……混合在一起，如 mix the flour and the eggs together"),
            ("pour...into...", "把……倒进……里，如 pour the milk into the bowl 把牛奶倒进碗里"),
            ("boil", "煮沸，把水或食物加热到沸腾"),
            ("how many", "提问可数名词的数量，后面接可数名词的复数形式"),
            ("how much", "提问不可数名词的量，也可以用来询问物品的价格"),
            ("first...next...then...finally", "表示做事情的先后顺序：首先、接下来、然后、最后"),
            ("recipe", "食谱，介绍做某道菜所需材料和步骤的说明"),
        ], 20261675)),
    ]),
    ("第六单元 Plan for Yourself", [
        ("第1课 Unit 6 Plan for Yourself", "📣 有计划才有行动。想一想：新学期你打算学会什么新本领？", L([
            ("make a plan", "制定计划，提前想好要做的事情和安排"),
            ("be going to do sth.", "将要去做某事，表示事先计划或打算好的动作，后面接动词原形"),
            ("plan to do sth.", "计划做某事，表示已经想好并打算去做"),
            ("hope to do sth.", "希望做某事，表示心里盼望着实现"),
            ("want to be", "想要成为，后面接表示职业的名词，如 I want to be a pilot"),
            ("take up", "开始学着做，开始从事一项新的爱好"),
            ("New Year's resolution", "新年决心，新的一年里下决心要做到的事情"),
            ("dream", "梦想，心里非常想实现的愿望"),
            ("practice doing sth.", "练习做某事，practice 后面要用动名词形式"),
            ("keep on doing sth.", "继续或坚持做某事，表示不放弃"),
            ("to-do list", "待办事项清单，把要做的事情一件件列出来"),
            ("promise to do sth.", "承诺做某事，答应别人自己一定会去做"),
        ], 20261676)),
    ]),
    ("第七单元 When Tomorrow Comes", [
        ("第1课 Unit 7 When Tomorrow Comes", "📣 未来充满无限可能。想一想：20 年后的生活会是什么样子？", L([
            ("will", "将要，用于构成一般将来时，后面接动词原形"),
            ("won't", "will not 的缩写形式，表示将不会发生某事"),
            ("robot", "机器人，能自动完成工作的机器"),
            ("prediction", "预言，预测，对将来会发生什么的推测"),
            ("future", "未来，将来，如 in the future 表示在将来"),
            ("in the future", "在将来，指从现在往后的时间里"),
            ("space station", "空间站，宇航员在太空中工作和生活的地方"),
            ("astronaut", "宇航员，乘坐飞船到太空执行任务的人"),
            ("planet", "行星，围绕恒星运行的天体，地球就是一颗行星"),
            ("一般将来时", "表示将来发生的动作或存在的状态，常用 will 加动词原形构成"),
            ("there will be", "将来将有……，是 there be 句型的一般将来时形式"),
            ("live to be", "活到多少岁，如 live to be 200 years old 活到两百岁"),
        ], 20261677)),
    ]),
    ("第八单元 Let's Communicate!", [
        ("第1课 Unit 8 Let's Communicate!", "📣 会沟通才能交到好朋友。想一想：朋友闹矛盾了，你会怎么劝？", L([
            ("communicate", "交流，沟通，人与人之间传递信息和想法"),
            ("maybe", "也许，大概，表示可能性，常放在句首"),
            ("should", "应该，表示建议或劝告，后面接动词原形"),
            ("could", "可以，表示委婉地向别人提出建议或请求"),
            ("argument", "争论，争吵，因意见不同而发生的争执"),
            ("give sb. some advice", "给某人提一些建议，advice 是不可数名词"),
            ("Why don't you do sth.?", "你为什么不……呢，用来向别人提出建议"),
            ("How/What about doing sth.?", "做……怎么样，about 后面接动名词，用来提出建议或征求对方意见"),
            ("talk with sb.", "与某人交谈，通过谈话交流彼此的想法"),
            ("write...down", "把……写下来，记录下来"),
            ("get on well with sb.", "与某人相处融洽，关系友好"),
            ("It's important to do sth.", "做某事很重要，it 是形式主语，真正的主语是后面的不定式"),
        ], 20261678)),
    ]),
]

if __name__ == "__main__":
    run(r"content/middle/pep/grade2/volume1/english", "英语上册", UNITS)
