# -*- coding: utf-8 -*-
"""人教版（2026 新教材）初中二年级下册英语全部单元交互自测题生成脚本。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _quizlib import S, S2, M, run  # noqa: E402
from _concepts import concept_lessons  # noqa: E402


def L(entries, seed):
    return concept_lessons(entries, seed=seed)


UNITS = [
    ("第一单元 Time to Relax", [
        ("第1课 Unit 1 Time to Relax", "📣 忙碌的学习之余要学会放松。想一想：你平时最喜欢用哪种方式放松自己？", L([
            ("rest", "休息，放松，如 have a good rest 好好休息一下"),
            ("hobby", "业余爱好，闲暇时喜欢做的活动，如 reading 是一种 hobby"),
            ("relax oneself", "放松自己，让自己从紧张的状态中缓过来"),
            ("used to do sth.", "过去常常做某事，表示以前习惯性的动作，现在不再做了"),
            ("spare time", "空闲时间，业余时间，如 in my spare time 在我的空闲时间"),
            ("collect stamps", "集邮，把邮票收集起来作为爱好"),
            ("go fishing", "去钓鱼，一种常见的休闲活动"),
            ("play chess", "下棋，一种益智的休闲活动"),
            ("be fond of", "喜欢，喜爱，后面接名词或动名词"),
            ("in one's free time", "在某人的空闲时间里，用来谈论休闲活动的时间"),
            ("What do you do to relax?", "用一般现在时询问对方如何放松自己，回答常用 I relax by doing..."),
            ("instead of doing sth.", "而不是做某事，代替做某事，of 后面接动名词"),
            ("be good for", "对……有好处，如 resting is good for your health"),
        ], 20261681)),
    ]),
    ("第二单元 Stay Healthy", [
        ("第1课 Unit 2 Stay Healthy", "📣 健康是学习和生活的本钱。想一想：感冒发烧时我们应该注意什么？", L([
            ("fever", "发烧，发热，如 have a fever 表示发烧了"),
            ("cough", "咳嗽，既可作动词也可作名词，如 have a bad cough 咳嗽得厉害"),
            ("take one's temperature", "量体温，用体温计测量身体的温度"),
            ("stomachache", "胃痛，肚子痛，如 have a stomachache"),
            ("headache", "头痛，如 have a headache 表示头痛"),
            ("have a cold", "感冒，着凉，如 catch a cold 也表示感冒"),
            ("lie down", "躺下，休息，如 lie down and rest 躺下休息"),
            ("take medicine", "吃药，服药，medicine 是不可数名词"),
            ("should", "应该，表示建议或劝告，后面接动词原形，如 You should drink more water"),
            ("had better", "最好，表示建议，后面接动词原形，否定形式是 had better not do"),
            ("see a doctor", "看医生，就医，身体不舒服时应该 see a doctor"),
            ("It's important to do sth.", "做某事很重要，it 是形式主语，如 It's important to exercise every day"),
            ("brush teeth", "刷牙，保持口腔卫生的好习惯，如 brush your teeth twice a day"),
        ], 20261682)),
    ]),
    ("第三单元 Growing Up", [
        ("第1课 Unit 3 Growing Up", "📣 成长的路上有欢笑也有泪水。想一想：和小时候相比你有了哪些变化？", L([
            ("memory", "记忆，回忆，复数形式是 memories，如 sweet memories 甜蜜的回忆"),
            ("childhood", "童年，孩童时期，如 in my childhood 在我的童年"),
            ("be used to doing sth.", "习惯于做某事，to 是介词，后面接动名词"),
            ("stop doing sth.", "停止做某事，表示不再做原来在做的事情"),
            ("grow up", "长大，成长，如 What do you want to be when you grow up?"),
            ("used to be", "过去曾经是，如 He used to be short 他过去个子矮"),
            ("be afraid of", "害怕，畏惧，后面接名词或动名词"),
            ("deal with", "处理，应对，如 learn to deal with problems 学会处理问题"),
            ("in the past", "在过去，与一般过去时连用"),
            ("at first", "起初，一开始，表示事情开始的时候"),
            ("no longer", "不再，如 I am no longer a child 我不再是小孩子了"),
            ("remember doing sth.", "记得做过某事，表示事情已经做过了"),
            ("change a lot", "变化很大，形容人或事物与以前大不相同"),
        ], 20261683)),
    ]),
    ("第四单元 The Wonders of Nature", [
        ("第1课 Unit 4 The Wonders of Nature", "📣 大自然充满令人惊叹的奇观。想一想：你去过哪些美丽的自然景点？", L([
            ("waterfall", "瀑布，水从高处倾泻而下的自然景观"),
            ("desert", "沙漠，降雨很少、植被稀少的干旱地带"),
            ("jungle", "丛林，热带地区树木茂密的地方"),
            ("canyon", "峡谷，两侧陡峭、幽深的山谷"),
            ("mountain", "山，高山，如 climb the mountain 爬山"),
            ("amazing", "令人惊叹的，形容事物好得让人惊讶"),
            ("natural", "自然的，天然的，名词 nature 的形容词形式"),
            ("be famous for", "因……而闻名，如 Guilin is famous for its mountains and rivers"),
            ("thousands of", "成千上万的，表示数量非常多，后面接可数名词复数"),
            ("as tall as", "和……一样高，两个 as 之间用形容词原级"),
            ("in the south of", "在……的南部，表示方位"),
            ("at the foot of", "在……的脚下，如 a village at the foot of the mountain"),
            ("What a wonderful view!", "感叹句，What 加形容词加名词，赞美眼前的景色"),
        ], 20261684)),
    ]),
    ("第五单元 Nature's Temper", [
        ("第1课 Unit 5 Nature's Temper", "📣 极端天气提醒我们敬畏自然。想一想：遇到暴雨或台风时应该怎样保护自己？", L([
            ("storm", "暴风雨，伴有大风大雨的恶劣天气"),
            ("flood", "洪水，水灾，如 The flood washed away many houses"),
            ("drought", "干旱，旱灾，长期不下雨造成的灾害"),
            ("typhoon", "台风，发生在西太平洋地区的强热带风暴"),
            ("heavy rain", "大雨，暴雨，形容雨下得很大"),
            ("strong wind", "大风，强风，风刮得很猛"),
            ("rain heavily", "下大雨，heavily 是副词修饰动词 rain"),
            ("at that time", "在那时，过去进行时常与这个时间状语连用"),
            ("过去进行时 was/were doing", "表示过去某一时刻正在进行的动作，was 用于第一、三人称单数，were 用于其余人称"),
            ("While it was raining", "while 引导的时间状语从句，从句用过去进行时表示正在进行"),
            ("when it began to rain", "when 引导的从句表示当……的时候，常与过去进行时主句连用"),
            ("stay at home", "待在家里，极端天气来临时最安全的做法之一"),
            ("in the rain", "在雨中，如 He was walking in the rain"),
        ], 20261685)),
    ]),
    ("第六单元 Crossing Cultures", [
        ("第1课 Unit 6 Crossing Cultures", "📣 了解不同文化才能更好地沟通。想一想：中西方餐桌礼仪有哪些不同？", L([
            ("custom", "习俗，风俗，一个国家或民族长期形成的习惯"),
            ("tradition", "传统，世代相传的风俗和做法"),
            ("be supposed to do sth.", "应该做某事，被期望做某事，表示按照习俗或规定应该这样做"),
            ("table manners", "餐桌礼仪，吃饭时应有的礼貌和规矩"),
            ("greet", "问候，打招呼，如 greet each other 互相问候"),
            ("chopsticks", "筷子，中国人吃饭用的餐具，常用复数形式"),
            ("point at", "指着，用手指向某人或某物，是不礼貌的行为"),
            ("polite", "有礼貌的，如 It's polite to wait for everyone to start eating"),
            ("modal verbs", "情态动词，如 can, may, must, should，后面接动词原形，表示能力、许可或建议"),
            ("must", "必须，一定，表示必要或义务，否定式 mustn't 表示禁止"),
            ("You are not supposed to...", "你不应该……，用来委婉地指出对方不合习俗的行为"),
            ("be different from", "与……不同，用于比较不同文化之间的差异"),
            ("pay attention to", "注意，留心，to 是介词，后面接名词或动名词"),
        ], 20261686)),
    ]),
    ("第七单元 A Good Read", [
        ("第1课 Unit 7 A Good Read", "📣 读一本好书就是和许多高尚的人谈话。想一想：你最近读完了哪本书？", L([
            ("novel", "小说，一种长篇的叙事文学作品"),
            ("poem", "诗，诗歌，复数形式是 poems，写诗的人叫 poet"),
            ("classic", "经典作品，名著，如 read the classics 阅读经典名著"),
            ("author", "作者，作家，写书的人"),
            ("page", "页，书的一页，如 turn to page 25 翻到第 25 页"),
            ("be full of", "充满，装满，如 The book is full of interesting stories"),
            ("can't put it down", "爱不释手，形容书太好看，舍不得放下"),
            ("borrow...from...", "从……借来……，如 borrow books from the library"),
            ("现在完成时 have/has done", "表示过去发生的动作对现在造成的影响或结果，have 用于复数主语，has 用于第三人称单数"),
            ("for two years", "for 加时间段，表示持续了多久，常与现在完成时连用"),
            ("since 2020", "since 加时间点，表示自从……以来，常与现在完成时连用"),
            ("have finished reading", "已经读完了，现在完成时表示动作已完成，finish 后接动名词"),
            ("have kept it for a week", "keep 是延续性动词，可与 for 时间段连用，表示借了并保持了多久"),
        ], 20261687)),
    ]),
    ("第八单元 Making a Difference", [
        ("第1课 Unit 8 Making a Difference", "📣 小小的善举也能改变世界。想一想：你能为社区或身边的人做些什么？", L([
            ("volunteer", "志愿者；做志愿者，如 work as a volunteer 担任志愿者"),
            ("donate", "捐赠，捐献，如 donate books to children 给孩子们捐书"),
            ("raise money", "筹款，募捐，为需要帮助的人筹集资金"),
            ("charity", "慈善机构，慈善事业，复数形式是 charities"),
            ("clean up", "打扫干净，清理，如 clean up the park 把公园打扫干净"),
            ("cheer up", "使振奋，使高兴起来，如 cheer up the sick kids"),
            ("give out", "分发，发放，如 give out food and clothes"),
            ("help out", "帮助……摆脱困难，分担工作"),
            ("动词不定式作宾语", "want, hope, decide, plan 等动词后面接 to do 不定式作宾语，如 decide to help others"),
            ("decide to do sth.", "决定做某事，to 后面接动词原形"),
            ("plan to do sth.", "计划做某事，表示已经想好并打算去做"),
            ("It's meaningful to do sth.", "做某事很有意义，it 是形式主语，如 It's meaningful to volunteer"),
            ("care for", "照顾，关心，如 care for the old people 关心老人"),
        ], 20261688)),
    ]),
]

if __name__ == "__main__":
    run(r"content/middle/pep/grade2/volume2/english", "英语下册", UNITS)
