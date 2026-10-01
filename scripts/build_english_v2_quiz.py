# -*- coding: utf-8 -*-
"""人教版 PEP 四年级下册 英语 —— 全 6 单元 18 课交互自测生成器。

输出（默认）：
  content/primary/pep/grade4/volume2/english/<NN-单元名>/<NN-课名>.html
每个单元拆成 3 课（核心词汇 / 句型与对话 / 综合运用），与上册 english/ 保持一致。

课本版本：义务教育教科书 英语（PEP）四年级 下册，人民教育出版社。
用法：
  1) python scripts/build_english_v2_quiz.py
  2) python .workbuddy/skills/interactive-quiz-html/scripts/check_units.py scripts/build_english_v2_quiz.py
  3) go run ./tools/bankcheck
  4) 重启 StudyBuddy 服务

注意：核心词汇课由词表程序化生成（固定随机种子，答案首位、由引擎打乱）；
      句型与对话 / 综合运用为手工题库。朗读语言由引擎按 SUBJECT 含「英语」自动切 en-US。
"""
import os
import random
import re
import sys
from pathlib import Path


# ---- 1) 定位项目根与引擎 ----
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
    raise SystemExit("找不到引擎 build_quiz_html.py，请确认技能目录完整")


PROJECT_ROOT = _find_project_root(Path(__file__).resolve().parent)
sys.path.insert(0, str(_find_engine_dir(PROJECT_ROOT)))
from build_quiz_html import build as engine_build  # noqa: E402


# ---- 2) 配置 ----
ARCHIVE_REL = r"content/primary/pep/grade4/volume2/english"
SUBJECT = "英语下册"
STUDENT = os.environ.get("QUIZ_STUDENT", "郭奕凡")

LAYOUT = os.environ.get("QUIZ_LAYOUT", "content")
ARCHIVE = os.environ.get("QUIZ_ARCHIVE") or (
    ARCHIVE_REL if os.path.isabs(ARCHIVE_REL) else str(PROJECT_ROOT / ARCHIVE_REL)
)

RNG = random.Random(20260929)


# ---- 3) 程序化出题工具 ----
def _others(correct, pool, n=3):
    xs = [x for x in pool if x != correct]
    RNG.shuffle(xs)
    return xs[:n]


def en2cn(en, cn, pool_cn):
    """英译中：「apple」的意思是（）"""
    return ("s", "「%s」的意思是（　）。" % en, [cn] + _others(cn, pool_cn), ["A"])


def cn2en(cn, en, pool_en):
    """中译英：「图书馆」用英语怎么说？"""
    return ("s", "「%s」用英语说是（　）。" % cn, [en] + _others(en, pool_en), ["A"])


def first_letter(en, pool_letters):
    """首字母题：单词 library 的第一个字母是（）"""
    a = en[0].lower()
    return ("s", "单词「%s」的第一个字母是（　）。" % en, [a.upper()] + _others(a.upper(), pool_letters), ["A"])


def letter_case(letter):
    up = letter.upper()
    low = letter.lower()
    return ("s", "大写字母「%s」的小写形式是（　）。" % up,
            [low, up, low if low != "a" else "b", chr((ord(low) - 97 + 2) % 26 + 97)], ["A"])


def build_vocab(words, letters, want=26):
    """由词表生成核心词汇课：英译中 + 中译英 + 首字母，去重后截取 want 题。"""
    pool_cn = [c for _, c in words]
    pool_en = [e for e, _ in words]
    qs = []
    for en, cn in words:
        qs.append(en2cn(en, cn, pool_cn))
    for en, cn in words:
        qs.append(cn2en(cn, en, pool_en))
    for en, _ in words:
        if len(en) >= 4:
            qs.append(first_letter(en, letters))
    for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        qs.append(letter_case(ch))
    # 去重（题干唯一），保序
    seen, out = set(), []
    for q in qs:
        if q[1] in seen:
            continue
        seen.add(q[1])
        out.append(q)
    RNG.shuffle(out)
    return out[:want]


# ---- 4) 题库数据 ----
# 每题：(题型, 题干, [A,B,C,D], [答案字母])；正确项写在第一项即可（引擎会打乱）。
UNITS = [

# ===================== 第一单元 My school 我的学校 =====================
("第一单元 My school 我的学校", [
    ("第1课 核心词汇",
     "📣 今日广播：本单元要学会说学校的各个地方：library 图书馆、playground 操场、teachers' office 教师办公室；序数词 first 第一、second 第二、third 第三。",
     build_vocab([
         ("school", "学校"), ("classroom", "教室"), ("library", "图书馆"),
         ("playground", "操场"), ("garden", "花园"), ("teachers' office", "教师办公室"),
         ("art room", "美术教室"), ("music room", "音乐教室"), ("computer room", "计算机房"),
         ("first", "第一"), ("second", "第二"), ("third", "第三"),
         ("welcome", "欢迎"), ("homework", "作业"),
     ], ["B", "C", "D", "F", "G", "H", "L", "M", "P", "S", "T", "W"])),
    ("第2课 句型与对话",
     "📣 今日广播：问路用 Where is the library? 答 It's on the second floor.；确认用 Is this the teachers' office? 答 Yes, it is.",
     [
         ("s", "问「图书馆在哪里？」，应该说（　）。",
          ["Where is the library?", "How is the library?", "What is the library?", "Who is the library?"], ["A"]),
         ("s", "「图书馆在二楼。」应说（　）。",
          ["The library is on the second floor.", "The library is in the second floor.",
           "The library are on the second floor.", "The library on second floor."], ["A"]),
         ("s", "「Is this the teachers' office?」肯定回答是（　）。",
          ["Yes, it is.", "Yes, they are.", "Yes, I am.", "Yes, it does."], ["A"]),
         ("s", "「Is that the music room?」否定回答是（　）。",
          ["No, it isn't.", "No, they aren't.", "No, I'm not.", "No, it don't."], ["A"]),
         ("s", "「Do you have a library?」肯定回答是（　）。",
          ["Yes, we do.", "Yes, we are.", "Yes, we have.", "Yes, I do."], ["A"]),
         ("s", "「Do you have an art room?」否定回答是（　）。",
          ["No, we don't.", "No, we aren't.", "No, I don't.", "No, we haven't."], ["A"]),
         ("s", "「Welcome to our school!」的意思是（　）。",
          ["欢迎来到我们学校！", "这是我们的学校。", "我们学校在哪里？", "我们喜欢学校。"], ["A"]),
         ("s", "「The library is next to the art room.」中 next to 的意思是（　）。",
          ["紧邻；在……旁边", "在……下面", "在……后面", "在……对面"], ["A"]),
         ("s", "「这是我们的操场。」应说（　）。",
          ["This is our playground.", "This are our playground.",
           "This is we playground.", "These is our playground."], ["A"]),
         ("s", "想知道「你们有多少间教室？」，应问（　）。",
          ["How many classrooms do you have?", "How much classrooms do you have?",
           "How many classroom you have?", "How old are your classrooms?"], ["A"]),
         ("s", "「美术教室在三楼。」应说（　）。",
          ["The art room is on the third floor.", "The art room is on the three floor.",
           "The art room is in third floor.", "The art room on the third floor."], ["A"]),
         ("s", "别人问「Where is the playground?」，合适的回答是（　）。",
          ["It's next to the garden.", "It's a playground.", "Yes, it is.", "I like it."], ["A"]),
         ("s", "「Excuse me.」在这里的作用是（　）。",
          ["礼貌地引起别人注意", "表示道歉", "表示告别", "表示感谢"], ["A"]),
         ("s", "「Let's go to the music room.」的意思是（　）。",
          ["我们去音乐教室吧。", "音乐教室在哪里？", "这是音乐教室。", "我喜欢音乐教室。"], ["A"]),
         ("s", "「That is the computer room.」变为疑问句是（　）。",
          ["Is that the computer room?", "That is the computer room?",
           "Is that computer room?", "That the computer room is?"], ["A"]),
         ("m", "关于学校场所，下列英语说法正确的有（　）。",
          ["library 图书馆", "playground 操场", "garden 花园", "classroom 教室"], ["A", "B", "C", "D"]),
         ("m", "下列序数词与中文对应正确的有（　）。",
          ["first 第一", "second 第二", "third 第三", "fourth 第四"], ["A", "B", "C", "D"]),
         ("m", "「图书馆在二楼。」这句话用到的词有（　）。",
          ["the library", "on", "second floor", "under"], ["A", "B", "C"]),
         ("s", "「Is this your classroom?」中 this 指的是（　）。",
          ["离说话人较近的教室", "离说话人较远的教室", "很多教室", "自己的家"], ["A"]),
         ("s", "「That is the garden.」中 that 指的是（　）。",
          ["离说话人较远的花园", "离说话人较近的花园", "我的花园", "这个花园"], ["A"]),
     ]),
    ("第3课 综合运用",
     "📣 今日广播：把单词放进句子里才是真会。注意 on the first floor（在一楼）、next to（紧邻）、two libraries（两座图书馆）这些常见搭配。",
     [
         ("s", "「我们学校有两座图书馆。」应说（　）。",
          ["We have two libraries in our school.", "We have two library in our school.",
           "We has two libraries in our school.", "We have two librariss in our school."], ["A"]),
         ("s", "「操场在一楼。」应说（　）。",
          ["The playground is on the first floor.", "The playground is on the one floor.",
           "The playground on the first floor.", "The playground are on the first floor."], ["A"]),
         ("s", "「教师办公室紧邻音乐教室。」应说（　）。",
          ["The teachers' office is next to the music room.", "The teachers' office next to the music room.",
           "The teachers' office is next the music room.", "The teachers' office are next to music room."], ["A"]),
         ("s", "「这是我的教室，它在一楼。」最恰当的英语是（　）。",
          ["This is my classroom. It's on the first floor.",
           "This is my classroom. It's in the first floor.",
           "This is me classroom. It's on first floor.",
           "This are my classroom on first floor."], ["A"]),
         ("s", "下列哪句适合在介绍学校时说（　）。",
          ["Welcome to our school!", "Goodbye, everyone!", "How old are you?", "I'm sorry."], ["A"]),
         ("s", "别人带你参观校园，他介绍完后你可以说（　）。",
          ["Thank you. Your school is nice!", "No, it isn't.", "I don't know.", "It's a library."], ["A"]),
         ("s", "school 前用 a 还是 an？（　）",
          ["a school", "an school", "不填冠词", "the school 只能这样用"], ["A"]),
         ("s", "「There is a library.」与「There are two ___ .」第二条横线应填（　）。",
          ["libraries", "library", "librarys", "a library"], ["A"]),
         ("s", "词形变化：classroom 的复数形式是（　）。",
          ["classrooms", "classroomes", "classroomies", "classroom"], ["A"]),
         ("s", "词形变化：library 的复数形式是（　）。",
          ["libraries", "librarys", "libraryes", "libraris"], ["A"]),
         ("s", "「first floor」在英国英语里指（　）。",
          ["二楼（英国说法）", "一楼", "三楼", "地下室"], ["A"]),
         ("s", "「The library is ___ the art room.」（紧邻）",
          ["next to", "next", "next for", "to next"], ["A"]),
         ("s", "「How many ___ do you have?」填 playground 的正确形式是（　）。",
          ["playgrounds", "playground", "playgroundes", "playgroundies"], ["A"]),
         ("s", "找出与 school 同类的一组词（　）。",
          ["classroom, library", "chair, desk", "red, blue", "run, jump"], ["A"]),
         ("s", "「Where is the garden?」的答语不可能是（　）。",
          ["Yes, it is.", "It's next to the art room.", "It's on the first floor.", "It's over there."], ["A"]),
         ("s", "「操场」的英语拼写正确的是（　）。",
          ["playground", "playgroun", "plaground", "playgrond"], ["A"]),
         ("s", "「图书馆」的英语拼写正确的是（　）。",
          ["library", "libary", "librery", "libray"], ["A"]),
         ("s", "「教室」的英语拼写正确的是（　）。",
          ["classroom", "classrom", "clasroom", "classroome"], ["A"]),
         ("m", "下列单词中含有字母组合「oo」的有（　）。",
          ["school", "classroom", "afternoon", "balloon"], ["A", "B", "C", "D"]),
         ("m", "下列关于本校场所的说法正确的有（　）。",
          ["library 是借阅图书的地方", "playground 是运动玩耍的地方",
           "computer room 里有电脑", "art room 用来上美术课"], ["A", "B", "C", "D"]),
     ]),
]),

# ===================== 第二单元 What time is it? =====================
("第二单元 What time is it? 现在几点了", [
    ("第1课 核心词汇",
     "📣 今日广播：本单元要会说时间：breakfast 早餐、lunch 午餐、dinner 晚餐；以及 get up 起床、go to school 上学、go home 回家、go to bed 睡觉。",
     build_vocab([
         ("breakfast", "早餐"), ("lunch", "午餐"), ("dinner", "晚餐"),
         ("English class", "英语课"), ("music class", "音乐课"), ("PE class", "体育课"),
         ("get up", "起床"), ("go to school", "去上学"), ("go home", "回家"),
         ("go to bed", "上床睡觉"), ("o'clock", "……点钟"), ("time", "时间"),
         ("hurry up", "快点"), ("ready", "准备好的"), ("now", "现在"), ("kid", "小孩"),
     ], ["B", "C", "D", "E", "G", "H", "K", "L", "M", "N", "P", "T"])),
    ("第2课 句型与对话",
     "📣 今日广播：问时间用 What time is it? 答 It's 9 o'clock.；「该做某事」用 It's time for + 名词，或 It's time to + 动词。",
     [
         ("s", "问「现在几点了？」，应该说（　）。",
          ["What time is it?", "What is time?", "How time is it?", "Where is the time?"], ["A"]),
         ("s", "「It's 8 o'clock.」的意思是（　）。",
          ["八点了。", "八个小时。", "第八个。", "八点了吗？"], ["A"]),
         ("s", "「该上英语课了。」应说（　）。",
          ["It's time for English class.", "It's time to English class.",
           "It's time English class.", "It's times for English class."], ["A"]),
         ("s", "「该上床睡觉了。」应说（　）。",
          ["It's time to go to bed.", "It's time for go to bed.",
           "It's time go to bed.", "It's times to bed."], ["A"]),
         ("s", "「It's time for lunch.」中 lunch 是（　）。",
          ["名词，所以用 for", "动词，所以用 for", "名词，所以用 to", "形容词"], ["A"]),
         ("s", "「It's time to go home.」中 to 后面接（　）。",
          ["动词短语 go home", "名词 home 的复数", "形容词", "介词"], ["A"]),
         ("s", "「School is over.」的意思是（　）。",
          ["放学了。", "学校结束了。", "学校在上面。", "开学了。"], ["A"]),
         ("s", "催别人「快点！」，应说（　）。",
          ["Hurry up!", "Just a minute!", "Over there!", "Come in!"], ["A"]),
         ("s", "别人催你，你想说「等一下！」，应说（　）。",
          ["Just a minute!", "Hurry up!", "Of course!", "Thank you!"], ["A"]),
         ("s", "「Let's go home.」的意思是（　）。",
          ["我们回家吧。", "我们去学校吧。", "让我回家。", "我要回家吗？"], ["A"]),
         ("s", "「Ready?」的意思是（　）。",
          ["准备好了吗？", "已经好了。", "读一读。", "真的吗？"], ["A"]),
         ("s", "「What time is it?」的答语是（　）。",
          ["It's 7 o'clock.", "It's a clock.", "I'm seven.", "At school."], ["A"]),
         ("s", "「现在六点半。」最恰当的英语是（　）。",
          ["It's six thirty.", "It's six o'clock.", "It's half six.", "It's thirty six."], ["A"]),
         ("s", "「It's 12 o'clock. It's time for ___ .」（午餐）",
          ["lunch", "lunchs", "the lunch", "a lunch"], ["A"]),
         ("s", "「I get up at 6 o'clock.」的意思是（　）。",
          ["我六点起床。", "我六点睡觉。", "我六点吃饭。", "我六点上学。"], ["A"]),
         ("s", "「What time is it now?」与「What time is it?」相比，多了 now 表示（　）。",
          ["强调「现在」", "表示过去", "表示将来", "没有区别"], ["A"]),
         ("m", "下列英语与中文对应正确的有（　）。",
          ["breakfast 早餐", "lunch 午餐", "dinner 晚餐", "PE class 体育课"], ["A", "B", "C", "D"]),
         ("m", "下面属于「一天中的活动」的短语有（　）。",
          ["get up", "go to school", "go home", "go to bed"], ["A", "B", "C", "D"]),
         ("m", "「It's time to ...」后面可以接的有（　）。",
          ["go to school", "go home", "go to bed", "get up"], ["A", "B", "C", "D"]),
         ("m", "「It's time for ...」后面可以接的有（　）。",
          ["English class", "lunch", "dinner", "breakfast"], ["A", "B", "C", "D"]),
     ]),
    ("第3课 综合运用",
     "📣 今日广播：读时间要说整点 o'clock、半点 thirty；「该做某事」用 It's time for + 名词、It's time to + 动词。多读几遍就顺口了。",
     [
         ("s", "「7:00」读作（　）。",
          ["seven o'clock", "seven thirty", "seven ten", "seventh o'clock"], ["A"]),
         ("s", "「8:30」读作（　）。",
          ["eight thirty", "eight o'clock", "thirty eight", "eight thirteen"], ["A"]),
         ("s", "「It's time for music class.」可以改写成（　）。",
          ["It's time to have music class.", "It's time to music class.",
           "It's time for have music class.", "It's time music class."], ["A"]),
         ("s", "「It's time to get up.」可以改写成（　）。",
          ["It's time for getting up.", "It's time for get up.",
           "It's time for up.", "It's time get up."], ["A"]),
         ("s", "妈妈叫你吃早饭，最可能说（　）。",
          ["It's time for breakfast.", "It's time for bed.", "Hurry up, it's late for school.", "School is over."], ["A"]),
         ("s", "同学问你几点了，你手表显示 10:00，回答（　）。",
          ["It's 10 o'clock.", "It's 10 thirty.", "It's ten to ten.", "I'm ten."], ["A"]),
         ("s", "「Hurry up! It's time for school.」的意思是（　）。",
          ["快点！该上学了。", "快点！学校关门了。", "慢点！该上学了。", "快点！放学了。"], ["A"]),
         ("s", "「___ is it? — It's 9 o'clock.」横线处填（　）。",
          ["What time", "What colour", "How many", "Where"], ["A"]),
         ("s", "「I go to bed ___ 9 o'clock.」填（　）。",
          ["at", "in", "on", "for"], ["A"]),
         ("s", "「I get up ___ the morning.」填（　）。",
          ["in", "at", "on", "for"], ["A"]),
         ("s", "「Let's ___ football.」填（　）。",
          ["play", "plays", "playing", "to play"], ["A"]),
         ("s", "「Just a minute!」的意思是（　）。",
          ["等一下！", "一分钟！", "马上走！", "还有一分钟！"], ["A"]),
         ("s", "「Time for bed, kids!」中 kids 的意思是（　）。",
          ["孩子们", "朋友们", "同学们", "老师们"], ["A"]),
         ("s", "「It's 6 o'clock. Time to get up, Sam!」这句话可能是谁说的？（　）",
          ["妈妈", "老师", "同学", "医生"], ["A"]),
         ("s", "下列句子中表达正确的一句是（　）。",
          ["It's time for dinner.", "It's time for dinner to.", "It's time dinner.", "It time for dinner."], ["A"]),
         ("s", "「What time is it?」中的 it 指（　）。",
          ["时间", "天气", "某个人", "某个东西"], ["A"]),
         ("s", "「早餐」的英语拼写正确的是（　）。",
          ["breakfast", "breakfest", "brekfast", "breckfast"], ["A"]),
         ("s", "「……点钟」的英语拼写正确的是（　）。",
          ["o'clock", "oclock", "o'clok", "oc'lock"], ["A"]),
         ("s", "「晚餐」的英语拼写正确的是（　）。",
          ["dinner", "diner", "dinne", "dinnner"], ["A"]),
         ("m", "下列时间表达正确的有（　）。",
          ["7 o'clock", "9:30 读作 nine thirty", "6:00 读作 six o'clock", "12 o'clock"], ["A", "B", "C", "D"]),
         ("m", "下面句子表示「该做某事了」的有（　）。",
          ["It's time for lunch.", "It's time to go home.", "It's time for English class.", "It's time to get up."], ["A", "B", "C", "D"]),
     ]),
]),

# ===================== 第三单元 Weather 天气 =====================
("第三单元 Weather 天气", [
    ("第1课 核心词汇",
     "📣 今日广播：天气词要记牢：cold 冷、cool 凉爽、warm 暖和、hot 热、sunny 晴朗、windy 有风、cloudy 多云、snowy 下雪、rainy 下雨。",
     build_vocab([
         ("cold", "寒冷的"), ("cool", "凉爽的"), ("warm", "暖和的"), ("hot", "炎热的"),
         ("sunny", "晴朗的"), ("windy", "有风的"), ("cloudy", "多云的"), ("snowy", "下雪的"),
         ("rainy", "下雨的"), ("weather", "天气"), ("degree", "度"), ("world", "世界"),
         ("outside", "外面"), ("umbrella", "雨伞"), ("jacket", "夹克衫"),
     ], ["B", "C", "D", "F", "G", "H", "J", "K", "L", "S", "U", "W"])),
    ("第2课 句型与对话",
     "📣 今日广播：问天气用 What's the weather like? 答 It's rainy.；征求许可用 Can I go outside now? 答 Yes, you can. / No, you can't.",
     [
         ("s", "问「北京的天气怎么样？」，应该说（　）。",
          ["What's the weather like in Beijing?", "How is the weather like in Beijing?",
           "What the weather is in Beijing?", "What's weather in Beijing like?"], ["A"]),
         ("s", "「It's rainy today.」的意思是（　）。",
          ["今天下雨。", "今天很热。", "今天有风。", "今天下雪。"], ["A"]),
         ("s", "「It's cold outside.」的意思是（　）。",
          ["外面很冷。", "里面很冷。", "今天很冷。", "外面很热。"], ["A"]),
         ("s", "「Can I go outside now?」的肯定回答是（　）。",
          ["Yes, you can.", "Yes, I can.", "Yes, we can.", "Yes, you do."], ["A"]),
         ("s", "「Can I go outside now?」的否定回答是（　）。",
          ["No, you can't.", "No, I can't.", "No, we can't.", "No, you don't."], ["A"]),
         ("s", "「Can I wear my new shirt today?」的否定回答是（　）。",
          ["No, you can't.", "No, I can't.", "No, you aren't.", "No, you won't."], ["A"]),
         ("s", "「What's the weather like in Shanghai? — ___」合适的是（　）。",
          ["It's cloudy.", "It's a cloudy day book.", "Yes, it is.", "I like cloudy."], ["A"]),
         ("s", "下雨天出门，妈妈会说（　）。",
          ["Take your umbrella.", "Take your sunglasses.", "Put on your shorts.", "Have some ice cream."], ["A"]),
         ("s", "「It's sunny and warm.」的意思是（　）。",
          ["天气晴朗又暖和。", "天气晴朗又寒冷。", "天气多云又暖和。", "天气晴朗又炎热。"], ["A"]),
         ("s", "「Put on your jacket.」的意思是（　）。",
          ["穿上你的夹克衫。", "脱下你的夹克衫。", "这是你的夹克衫。", "你的夹克衫在哪里？"], ["A"]),
         ("s", "「This is the world weather report.」的意思是（　）。",
          ["这是世界天气预报。", "这是今天的天气。", "这是世界的世界。", "这是天气报告吗？"], ["A"]),
         ("s", "「How about Beijing?」的意思是（　）。",
          ["北京怎么样？", "北京在哪里？", "北京是什么？", "北京有多大？"], ["A"]),
         ("s", "「It's 26 degrees.」的意思是（　）。",
          ["26 度。", "26 个。", "26 年。", "第 26 度。"], ["A"]),
         ("s", "「It's cool.」中 cool 指天气（　）。",
          ["凉爽", "寒冷", "炎热", "闷热"], ["A"]),
         ("s", "「Be careful!」的意思是（　）。",
          ["小心！", "别动！", "快走！", "好的！"], ["A"]),
         ("s", "「It's snowy.」对应的景象是（　）。",
          ["雪花飘落，地上白茫茫", "太阳很大", "下起了雨", "刮大风"], ["A"]),
         ("m", "下列属于天气描述的单词有（　）。",
          ["sunny", "windy", "rainy", "cloudy"], ["A", "B", "C", "D"]),
         ("m", "下列英语与中文对应正确的有（　）。",
          ["cold 寒冷的", "hot 炎热的", "warm 暖和的", "cool 凉爽的"], ["A", "B", "C", "D"]),
         ("m", "下雨天可以做的准备有（　）。",
          ["take an umbrella", "put on a raincoat", "wear boots", "wear sunglasses at night"], ["A", "B", "C"]),
         ("m", "关于「Can I ...?」的用法，正确的有（　）。",
          ["表示请求许可", "肯定回答 Yes, you can.", "否定回答 No, you can't.",
           "后接动词原形"], ["A", "B", "C", "D"]),
     ]),
    ("第3课 综合运用",
     "📣 今日广播：天气 + 穿衣 + 活动连起来才是真会用。读完题目先想「什么天气、穿什么、能不能出门」，答案自然就出来了。",
     [
         ("s", "「It's rainy. What should you take?」最合适的回答是（　）。",
          ["An umbrella.", "A pair of sunglasses.", "A fan.", "A swimsuit."], ["A"]),
         ("s", "「It's cold and snowy.」你应该（　）。",
          ["Put on a coat and a hat.", "Put on shorts and a T-shirt.",
           "Wear sunglasses.", "Go swimming outside."], ["A"]),
         ("s", "「It's hot.」时最不可能发生的是（　）。",
          ["People wear coats.", "People eat ice cream.", "People swim.", "People use a fan."], ["A"]),
         ("s", "「It's windy.」时适合的活动是（　）。",
          ["Fly a kite.", "Make a snowman.", "Swim in the lake.", "Read under the umbrella."], ["A"]),
         ("s", "「It's cold. Put on your ___ .」最合适的是（　）。",
          ["sweater", "shorts", "sandals", "sunglasses"], ["A"]),
         ("s", "「It's sunny and hot. Don't forget your ___ .」（防晒）",
          ["sunglasses", "gloves", "scarf", "boots"], ["A"]),
         ("s", "「What's the weather like today? — It's ___ . I need an umbrella.」（　）",
          ["rainy", "sunny", "windy", "snowy"], ["A"]),
         ("s", "「The weather report says it's sunny in Beijing.」这句话来自（　）。",
          ["天气预报", "菜单", "课程表", "故事书"], ["A"]),
         ("s", "「It's 30 degrees.」说明天气（　）。",
          ["很热", "很冷", "凉爽", "下雪"], ["A"]),
         ("s", "「It's -5 degrees.」说明天气（　）。",
          ["很冷", "很热", "凉爽", "多云"], ["A"]),
         ("s", "「Can I go outside? — No, you can't. It's ___ .」（大雨）",
          ["rainy", "sunny", "warm", "cool"], ["A"]),
         ("s", "「It's cool in autumn.」autumn 指（　）。",
          ["秋天", "春天", "夏天", "冬天"], ["A"]),
         ("s", "把「It is cold.」缩写为（　）。",
          ["It's cold.", "Its cold.", "It cold.", "It's cold"], ["A"]),
         ("s", "下列句子中没有错误的是（　）。",
          ["What's the weather like today?", "What's weather like today?",
           "How's the weather like today?", "What weather like today?"], ["A"]),
         ("s", "「It's warm in spring.」spring 指（　）。",
          ["春天", "夏天", "秋天", "冬天"], ["A"]),
         ("s", "「It's snowy.」与「It's rainy.」的共同点是（　）。",
          ["都是形容词，描述天气", "都表示热", "都表示风大", "都是名词"], ["A"]),
         ("s", "「天气」的英语拼写正确的是（　）。",
          ["weather", "wether", "wheather", "weathr"], ["A"]),
         ("s", "「雨伞」的英语拼写正确的是（　）。",
          ["umbrella", "umbrela", "umbralla", "umbrellla"], ["A"]),
         ("s", "「晴朗的」的英语拼写正确的是（　）。",
          ["sunny", "suny", "sunney", "sunnny"], ["A"]),
         ("m", "下列句子中表达正确的有（　）。",
          ["It's rainy today.", "It's cold outside.", "It's sunny and warm.", "It's windy today."], ["A", "B", "C", "D"]),
         ("m", "下面哪些是「冷天」的穿衣搭配（　）。",
          ["coat", "scarf", "gloves", "shorts"], ["A", "B", "C"]),
     ]),
]),

# ===================== 第四单元 At the farm 在农场 =====================
("第四单元 At the farm 在农场", [
    ("第1课 核心词汇",
     "📣 今日广播：农场里有什么？tomato 西红柿、potato 土豆、carrot 胡萝卜、green beans 青豆；动物有 horse 马、cow 奶牛、sheep 绵羊、hen 母鸡。",
     build_vocab([
         ("tomato", "西红柿"), ("potato", "土豆"), ("carrot", "胡萝卜"),
         ("green beans", "青豆"), ("horse", "马"), ("cow", "奶牛"),
         ("sheep", "绵羊"), ("hen", "母鸡"), ("duck", "鸭子"),
         ("farm", "农场"), ("vegetable", "蔬菜"), ("animal", "动物"),
         ("garden", "菜园；花园"), ("delicious", "美味的"),
     ], ["B", "C", "D", "H", "P", "S", "T", "V", "D", "G", "F", "M"])),
    ("第2课 句型与对话",
     "📣 今日广播：近处的多个东西用 these，远处用 those；提问 What are these? 答 They're tomatoes.；确认 Are these carrots? 答 Yes, they are.",
     [
         ("s", "问「这些是什么？」，应该说（　）。",
          ["What are these?", "What is these?", "What are this?", "What these are?"], ["A"]),
         ("s", "问「那些是什么？」，应该说（　）。",
          ["What are those?", "What is those?", "What are that?", "What those are?"], ["A"]),
         ("s", "「What are these? — ___ tomatoes.」（　）",
          ["They're", "It's", "These is", "There"], ["A"]),
         ("s", "「Are these carrots?」的肯定回答是（　）。",
          ["Yes, they are.", "Yes, it is.", "Yes, these are.", "Yes, they do."], ["A"]),
         ("s", "「Are these carrots?」的否定回答是（　）。",
          ["No, they aren't.", "No, it isn't.", "No, these aren't.", "No, they don't."], ["A"]),
         ("s", "「Are they hens? — ___ They're ducks.」（　）",
          ["No, they aren't.", "Yes, they are.", "No, it isn't.", "Yes, it is."], ["A"]),
         ("s", "「How many horses do you have? — Seventeen.」这句话问的是（　）。",
          ["马有多少匹", "马在哪里", "马好不好", "马是什么颜色"], ["A"]),
         ("s", "「These are tomatoes.」变为疑问句是（　）。",
          ["Are these tomatoes?", "These are tomatoes?", "Is these tomatoes?", "Do these tomatoes?"], ["A"]),
         ("s", "「Those are sheep.」变为疑问句是（　）。",
          ["Are those sheep?", "Those are sheep?", "Is those sheep?", "Do those sheep?"], ["A"]),
         ("s", "「Look at the vegetables.」的意思是（　）。",
          ["看这些蔬菜。", "这是蔬菜。", "蔬菜在哪里？", "我喜欢蔬菜。"], ["A"]),
         ("s", "「They're so big!」的意思是（　）。",
          ["它们真大呀！", "它们太小了！", "它们是什么？", "它们是大的吗？"], ["A"]),
         ("s", "「What are these?」中 these 指（　）。",
          ["离说话人较近的多个东西", "离说话人较远的东西", "单数的一个东西", "看不见的东西"], ["A"]),
         ("s", "「What are those?」中 those 指（　）。",
          ["离说话人较远的多个东西", "离说话人较近的东西", "一个东西", "我的东西"], ["A"]),
         ("s", "「on the farm」的意思是（　）。",
          ["在农场里", "在花园里", "在上面", "在农场上空"], ["A"]),
         ("s", "「Are these potatoes? — Yes, ___」（　）",
          ["they are", "these are", "it is", "those are"], ["A"]),
         ("s", "「How many ___ do you have?」填 tomato 的正确形式是（　）。",
          ["tomatoes", "tomatos", "tomato", "tomatoies"], ["A"]),
         ("m", "下列属于蔬菜的单词有（　）。",
          ["tomato", "potato", "carrot", "green beans"], ["A", "B", "C", "D"]),
         ("m", "下列属于动物的单词有（　）。",
          ["horse", "cow", "sheep", "hen"], ["A", "B", "C", "D"]),
         ("m", "关于「these / those」，说法正确的有（　）。",
          ["these 指近处的复数", "those 指远处的复数", "回答常用 they", "these 是单数"], ["A", "B", "C"]),
         ("m", "下列关于复数形式变化正确的有（　）。",
          ["tomato → tomatoes", "potato → potatoes", "horse → horses", "sheep → sheep"], ["A", "B", "C", "D"]),
     ]),
    ("第3课 综合运用",
     "📣 今日广播：注意 tomato、potato 的复数是加 -es；sheep 单复数同形；问数量用 How many + 复数。",
     [
         ("s", "「这些是土豆。」应说（　）。",
          ["These are potatoes.", "These are potatos.", "This are potatoes.", "These is potatoes."], ["A"]),
         ("s", "「那些是马。」应说（　）。",
          ["Those are horses.", "Those are horse.", "That are horses.", "Those is horses."], ["A"]),
         ("s", "「这些是胡萝卜吗？」应说（　）。",
          ["Are these carrots?", "Are this carrots?", "Is these carrots?", "These are carrots?"], ["A"]),
         ("s", "「农场里有十七只母鸡。」应说（　）。",
          ["There are seventeen hens on the farm.", "There is seventeen hens on the farm.",
           "There are seventeen hen on the farm.", "There have seventeen hens on the farm."], ["A"]),
         ("s", "「How many ___ ?」后面必须接（　）。",
          ["名词复数", "名词单数", "动词", "形容词"], ["A"]),
         ("s", "「I like tomatoes. They're ___ .」（美味）",
          ["delicious", "deliciously", "delight", "deliciousness"], ["A"]),
         ("s", "「___ are these? — They're carrots.」填（　）。",
          ["What", "Who", "Where", "How"], ["A"]),
         ("s", "「___ horses are there? — Five.」填（　）。",
          ["How many", "How much", "How old", "How"], ["A"]),
         ("s", "「These ___ green beans.」填（　）。",
          ["are", "is", "am", "be"], ["A"]),
         ("s", "「That ___ a cow.」填（　）。",
          ["is", "are", "am", "be"], ["A"]),
         ("s", "名词变复数：hen →（　）",
          ["hens", "henes", "hen", "hennies"], ["A"]),
         ("s", "名词变复数：sheep →（　）",
          ["sheep", "sheeps", "sheepes", "sheepen"], ["A"]),
         ("s", "名词变复数：cow →（　）",
          ["cows", "cowes", "cowies", "cow"], ["A"]),
         ("s", "「Look at the ___ . They're so big!」（西红柿）",
          ["tomatoes", "tomato", "a tomato", "tomatos"], ["A"]),
         ("s", "在农场里看到一群白色的绵羊，你可以说（　）。",
          ["Look! Those are sheep.", "Look! Those is sheep.", "Look! That are sheeps.", "Look! Those are sheeps."], ["A"]),
         ("s", "「Are these ducks? — No, ___ .」（　）",
          ["they aren't", "it isn't", "they don't", "these aren't"], ["A"]),
         ("s", "「土豆」的英语拼写正确的是（　）。",
          ["potato", "patato", "potatoe", "pottato"], ["A"]),
         ("s", "「胡萝卜」的英语拼写正确的是（　）。",
          ["carrot", "carot", "carrit", "carrott"], ["A"]),
         ("s", "「蔬菜」的英语拼写正确的是（　）。",
          ["vegetable", "vegatble", "vegtable", "vegitable"], ["A"]),
         ("m", "下列关于农场的话，说法正确的有（　）。",
          ["农场里可以种蔬菜", "农场里可以养动物", "farm 是农场", "vegetable 是水果"], ["A", "B", "C"]),
         ("m", "下面句子语法正确的有（　）。",
          ["These are tomatoes.", "Are these carrots?", "Those are horses.", "How many hens?"], ["A", "B", "C", "D"]),
     ]),
]),

# ===================== 第五单元 My clothes 我的衣服 =====================
("第五单元 My clothes 我的衣服", [
    ("第1课 核心词汇",
     "📣 今日广播：衣服单词要分清：jacket 夹克、shirt 衬衫、skirt 短裙、dress 连衣裙、sweater 毛衣、T-shirt T 恤、shorts 短裤、socks 袜子、trousers 长裤。",
     build_vocab([
         ("jacket", "夹克衫"), ("shirt", "衬衫"), ("skirt", "短裙"),
         ("dress", "连衣裙"), ("sweater", "毛衣"), ("T-shirt", "T 恤衫"),
         ("shorts", "短裤"), ("socks", "袜子"), ("trousers", "长裤"),
         ("hat", "帽子"), ("coat", "外套"), ("clothes", "衣服"),
         ("whose", "谁的"), ("mine", "我的"), ("yours", "你的"),
     ], ["B", "C", "D", "J", "S", "T", "H", "W", "M", "Y", "G", "P"])),
    ("第2课 句型与对话",
     "📣 今日广播：问归属用 Whose shirt is this? 答 It's mine. 或 It's my sister's.；穿脱用 Put on your jacket. / Take off your coat.",
     [
         ("s", "问「这是谁的衬衫？」，应该说（　）。",
          ["Whose shirt is this?", "Who shirt is this?", "Whose shirt are this?", "What shirt is this?"], ["A"]),
         ("s", "「It's mine.」的意思是（　）。",
          ["它是我的。", "它是你的。", "它是他的。", "它是谁的？"], ["A"]),
         ("s", "「Whose dress is that? — It's my sister's.」说明这条连衣裙是（　）。",
          ["姐姐（妹妹）的", "我的", "妈妈的", "老师的"], ["A"]),
         ("s", "「Is this your sweater?」的否定回答是（　）。",
          ["No, it isn't.", "No, they aren't.", "No, I'm not.", "No, it don't."], ["A"]),
         ("s", "「Is this your sweater? — No, it isn't. It's my ___ .」（我的夹克）",
          ["jacket", "jackets", "a jacket", "the jacket"], ["A"]),
         ("s", "「Put on your jacket.」的意思是（　）。",
          ["穿上你的夹克衫。", "脱下你的夹克衫。", "洗你的夹克衫。", "挂好你的夹克衫。"], ["A"]),
         ("s", "「Take off your coat.」的意思是（　）。",
          ["脱下你的外套。", "穿上你的外套。", "拿走我的外套。", "这是你的外套。"], ["A"]),
         ("s", "「These are my socks.」变为一般疑问句是（　）。",
          ["Are these your socks?", "These are my socks?", "Is these my socks?", "Do these my socks?"], ["A"]),
         ("s", "「Whose ___ are these?」填（　）。",
          ["shorts", "short", "a short", "the short"], ["A"]),
         ("s", "「It's yours.」的意思是（　）。",
          ["它是你的。", "它是我的。", "它是我们的。", "它是他们的。"], ["A"]),
         ("s", "「Wash your clothes, please.」的意思是（　）。",
          ["请洗你的衣服。", "请穿你的衣服。", "请买你的衣服。", "你的衣服在哪里？"], ["A"]),
         ("s", "「Put on your hat.」中的 put on 与下列哪个意思相反？（　）",
          ["take off", "look at", "go on", "put down"], ["A"]),
         ("s", "「This is my T-shirt.」换成物主代词应说（　）。",
          ["This T-shirt is mine.", "This T-shirt is my.", "This T-shirt is me.", "This T-shirt is I."], ["A"]),
         ("s", "「They are our socks.」换成物主代词应说（　）。",
          ["These socks are ours.", "These socks are our.", "These socks are us.", "These socks are we."], ["A"]),
         ("s", "「Whose is this?」中 whose 的意思是（　）。",
          ["谁的", "什么", "哪个", "哪里"], ["A"]),
         ("s", "「These are my shoes.」中 shoes 的意思是（　）。",
          ["鞋", "袜子", "帽子", "裤子"], ["A"]),
         ("m", "下列单词表示「衣服」的有（　）。",
          ["jacket", "sweater", "trousers", "socks"], ["A", "B", "C", "D"]),
         ("m", "下列物主代词与中文对应正确的有（　）。",
          ["mine 我的", "yours 你的", "his 他的", "hers 她的"], ["A", "B", "C", "D"]),
         ("m", "关于「Put on / Take off」，说法正确的有（　）。",
          ["put on 表示穿上", "take off 表示脱下", "后面接衣物名词", "put on 表示脱下"], ["A", "B", "C"]),
         ("m", "下列句子正确的有（　）。",
          ["Whose shirt is this?", "It's mine.", "Put on your jacket.", "These are my socks."], ["A", "B", "C", "D"]),
     ]),
    ("第3课 综合运用",
     "📣 今日广播：注意 shorts、trousers、socks、shoes 这几个词总是用复数形式，说「一条短裤」也要用 a pair of shorts。",
     [
         ("s", "「一条短裤」应说（　）。",
          ["a pair of shorts", "a shorts", "a short", "one shorts"], ["A"]),
         ("s", "「一条长裤」应说（　）。",
          ["a pair of trousers", "a trousers", "a trouser", "one trouser"], ["A"]),
         ("s", "「一双袜子」应说（　）。",
          ["a pair of socks", "a sock", "a socks", "one sock"], ["A"]),
         ("s", "下列单词中通常只用复数的是（　）。",
          ["shorts", "shirt", "skirt", "dress"], ["A"]),
         ("s", "「Is this your skirt? — Yes, ___ .」（　）",
          ["it is", "they are", "these are", "I am"], ["A"]),
         ("s", "「Are these your trousers? — Yes, ___ .」（　）",
          ["they are", "it is", "these are", "I am"], ["A"]),
         ("s", "「___ bag is this? — It's Amy's.」填（　）。",
          ["Whose", "Who", "What", "Where"], ["A"]),
         ("s", "「These are my ___ .」（袜子）",
          ["socks", "sock", "a sock", "sockes"], ["A"]),
         ("s", "「Whose coat is this? — It's ___ .」（我的）",
          ["mine", "my", "me", "I"], ["A"]),
         ("s", "「Whose skirt is this? — It's ___ .」（她的）",
          ["hers", "her", "she", "she's"], ["A"]),
         ("s", "「Whose T-shirt is this? — It's ___ .」（他的）",
          ["his", "he", "him", "he's"], ["A"]),
         ("s", "「Put on your coat. It's cold outside.」这句话的语境是（　）。",
          ["天冷出门前", "天热回家后", "洗衣服时", "买衣服时"], ["A"]),
         ("s", "「Take off your shoes, please.」最可能出现在（　）。",
          ["进别人家时", "上体育课时", "吃饭时", "上学时"], ["A"]),
         ("s", "「I like my new sweater.」的意思是（　）。",
          ["我喜欢我的新毛衣。", "这是我的新毛衣。", "我的新毛衣在哪里？", "这是一件毛衣吗？"], ["A"]),
         ("s", "把「This is her dress.」换成物主代词应说（　）。",
          ["This dress is hers.", "This dress is her.", "This dress is she.", "This dress is she's."], ["A"]),
         ("s", "「长裤」的英语拼写正确的是（　）。",
          ["trousers", "trouserss", "trouses", "troasers"], ["A"]),
         ("s", "「毛衣」的英语拼写正确的是（　）。",
          ["sweater", "sweather", "sweatre", "sweeter"], ["A"]),
         ("s", "「衣服」的英语拼写正确的是（　）。",
          ["clothes", "cloths", "clothese", "clotth"], ["A"]),
         ("m", "下列关于衣服的说法正确的有（　）。",
          ["shirt 是衬衫", "skirt 是短裙", "dress 是连衣裙", "jacket 是袜子"], ["A", "B", "C"]),
         ("m", "下面通常以复数形式出现的单词有（　）。",
          ["shorts", "trousers", "socks", "shoes"], ["A", "B", "C", "D"]),
     ]),
]),

# ===================== 第六单元 Shopping 购物 =====================
("第六单元 Shopping 购物", [
    ("第1课 核心词汇",
     "📣 今日广播：购物必备词：gloves 手套、scarf 围巾、umbrella 雨伞、sunglasses 太阳镜、size 尺码、expensive 昂贵的、cheap 便宜的、pretty 漂亮的。",
     build_vocab([
         ("gloves", "手套"), ("scarf", "围巾"), ("umbrella", "雨伞"),
         ("sunglasses", "太阳镜"), ("size", "尺码；大小"), ("expensive", "昂贵的"),
         ("cheap", "便宜的"), ("pretty", "漂亮的"), ("colour", "颜色"),
         ("yuan", "元（人民币）"), ("shop", "商店；购物"), ("money", "钱"),
         ("nice", "好看的"), ("much", "许多；多少"),
     ], ["B", "C", "D", "G", "S", "U", "E", "P", "Y", "M", "N", "K"])),
    ("第2课 句型与对话",
     "📣 今日广播：营业员问「Can I help you?」，顾客答「Yes, please.」；问价「How much is this skirt? It's 89 yuan.」",
     [
         ("s", "「Can I help you?」的意思是（　）。",
          ["需要我帮忙吗？（您想买点什么？）", "我能帮你吗？我可以帮忙搬东西。",
           "你能帮我吗？", "你在帮我吗？"], ["A"]),
         ("s", "营业员问「Can I help you?」，顾客想买东西时应说（　）。",
          ["Yes, please.", "No, thanks.", "You're welcome.", "That's OK."], ["A"]),
         ("s", "问「这条短裙多少钱？」，应该说（　）。",
          ["How much is this skirt?", "How many is this skirt?",
           "How much this skirt?", "How is this skirt much?"], ["A"]),
         ("s", "「It's 89 yuan.」的意思是（　）。",
          ["89 元。", "89 个。", "89 元吗？", "第 89 元。"], ["A"]),
         ("s", "「How much are they?」说明要问的东西是（　）。",
          ["多个", "一个", "看不见的", "别人的"], ["A"]),
         ("s", "「Can I try them on?」的意思是（　）。",
          ["我可以试穿一下吗？", "我可以把它们拿走吗？", "我可以买它们吗？", "它们好穿吗？"], ["A"]),
         ("s", "顾客问「Can I try them on?」，营业员同意时说（　）。",
          ["Of course.", "No, you can't.", "You're welcome.", "Goodbye."], ["A"]),
         ("s", "「They're too expensive.」的意思是（　）。",
          ["它们太贵了。", "它们太便宜了。", "它们太大了。", "它们太旧了。"], ["A"]),
         ("s", "「How do you like this skirt? — It's very pretty.」这句话在（　）。",
          ["评价衣服的样子", "问价格", "问尺码", "问颜色"], ["A"]),
         ("s", "「What size?」是在问（　）。",
          ["什么尺码", "什么颜色", "什么价格", "什么样子"], ["A"]),
         ("s", "「They're too small for me.」的意思是（　）。",
          ["对我来说太小了。", "它们很小。", "它们太短了。", "它们太多了。"], ["A"]),
         ("s", "「I'll take it.」的意思是（　）。",
          ["我买了。", "我拿走了。", "我试试。", "我不要了。"], ["A"]),
         ("s", "问「这双鞋多少钱？」，应说（　）。",
          ["How much are these shoes?", "How much is these shoes?",
           "How many are these shoes?", "How much these shoes?"], ["A"]),
         ("s", "「It's cheap.」中 cheap 的意思是（　）。",
          ["便宜的", "昂贵的", "漂亮的", "大的"], ["A"]),
         ("s", "「Thank you. — ___」合适的是（　）。",
          ["You're welcome.", "Yes, please.", "Of course not.", "No, thank you."], ["A"]),
         ("s", "「Do you have any gloves?」的意思是（　）。",
          ["你们有手套吗？", "这是手套吗？", "手套多少钱？", "你们想要手套吗？"], ["A"]),
         ("m", "下列属于可以在商店买到的物品的有（　）。",
          ["gloves", "scarf", "umbrella", "sunglasses"], ["A", "B", "C", "D"]),
         ("m", "顾客买衣服时可能用到的句子有（　）。",
          ["How much is it?", "Can I try it on?", "It's too expensive.",
           "It's too small for me."], ["A", "B", "C", "D"]),
         ("m", "关于「How much」，说法正确的有（　）。",
          ["问价格", "问不可数名词的量", "后接单数用 is", "后接复数用 are"], ["A", "B", "C", "D"]),
         ("m", "下面哪些单词是形容词（　）。",
          ["expensive", "cheap", "pretty", "nice"], ["A", "B", "C", "D"]),
     ]),
    ("第3课 综合运用",
     "📣 今日广播：买东西要会「三部曲」——问价（How much...?）、试穿（Can I try it on?）、表态（I'll take it. / It's too expensive.）。",
     [
         ("s", "「How much ___ this scarf?」填（　）。",
          ["is", "are", "am", "be"], ["A"]),
         ("s", "「How much ___ these gloves?」填（　）。",
          ["are", "is", "am", "be"], ["A"]),
         ("s", "「How much is ___ umbrella?」（一把）",
          ["an", "a", "the an", "不填"], ["A"]),
         ("s", "原文「It's 50 yuan.」问句应该是（　）。",
          ["How much is it?", "How many is it?", "What is it?", "Where is it?"], ["A"]),
         ("s", "营业员说「The red one is 40 yuan, the blue one is 60 yuan.」红伞比蓝伞（　）。",
          ["便宜 20 元", "贵 20 元", "便宜 40 元", "一样贵"], ["A"]),
         ("s", "「This dress is 80 yuan. That one is 120 yuan.」两件共（　）元。",
          ["200", "180", "160", "40"], ["A"]),
         ("s", "「I have 100 yuan. The shirt is 90 yuan.」买完后还剩（　）元。",
          ["10", "20", "90", "190"], ["A"]),
         ("s", "「The gloves are 15 yuan each.」买两副要（　）元。",
          ["30", "15", "45", "17"], ["A"]),
         ("s", "「Can I try ___ on?」（这条短裙）",
          ["it", "them", "they", "its"], ["A"]),
         ("s", "「Can I try ___ on?」（这些手套）",
          ["them", "it", "they", "their"], ["A"]),
         ("s", "顾客嫌贵，最合适的说法是（　）。",
          ["It's too expensive. Do you have a cheaper one?",
           "It's too cheap. I want a dearer one.", "I don't like shopping.", "How are you?"], ["A"]),
         ("s", "商店里问「What size do you want?」，这是在问（　）。",
          ["要什么尺码", "要什么颜色", "要多少钱的", "要几件"], ["A"]),
         ("s", "「I want the big one.」的意思是（　）。",
          ["我要大的那件。", "我要一件。", "这是大的。", "大的多少钱？"], ["A"]),
         ("s", "「昂贵的」的英语拼写正确的是（　）。",
          ["expensive", "expencive", "expensiv", "expansive"], ["A"]),
         ("s", "「太阳镜」的英语拼写正确的是（　）。",
          ["sunglasses", "sunglass", "sunglases", "sunglaasses"], ["A"]),
         ("s", "「围巾」的英语拼写正确的是（　）。",
          ["scarf", "scarfe", "scraf", "scarff"], ["A"]),
         ("s", "「three hundred yuan」写作数字是（　）。",
          ["300", "3000", "30", "30000"], ["A"]),
         ("s", "「¥5.50」用英语读作（　）。",
          ["five yuan fifty", "five point fifty yuan", "fifty yuan five", "five yuan five"], ["A"]),
         ("m", "下列关于购物对话的说法正确的有（　）。",
          ["Can I help you? 是营业员说的", "Yes, please. 是顾客说的",
           "Thank you. 后常答 You're welcome.", "How much...? 用来问价格"], ["A", "B", "C", "D"]),
         ("m", "下列句子中表达正确的有（　）。",
          ["How much is this skirt?", "How much are they?", "Can I try them on?",
           "They're too expensive."], ["A", "B", "C", "D"]),
     ]),
]),
]


# ---- 5) 生成 ----
UNIT_PREFIX = re.compile(r"^第[一二三四五六七八九十]+单元\s*")
LESSON_PREFIX = re.compile(r"^第(\d+)课\s*(.*)$")

CN_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
          "七": 7, "八": 8, "九": 9, "十": 10}

# Windows 文件名非法字符：能换全角的换全角（保留可读性），不能换的删掉。
# 例：「What time is it? 现在几点了」→「What time is it？ 现在几点了」
_SAFE_MAP = {ord("\\"): None, ord("/"): None, ord("*"): 0xFF0A,
             ord("?"): 0xFF1F, ord('"'): 0x201D, ord("<"): 0xFF1C,
             ord(">"): 0xFF1E, ord("|"): 0xFF5C, ord(":"): 0xFF1A}


def _safe(name):
    return name.translate(_SAFE_MAP).strip()


def _unit_dir(unit):
    m = UNIT_PREFIX.match(unit)
    name = unit[m.end():].strip() if m else unit.strip()
    no = CN_NUM.get(m.group(0)[1], 0) if m else 0
    return _safe("%02d-%s" % (no, name or unit.strip()))


def _lesson_file(lesson):
    m = LESSON_PREFIX.match(lesson)
    if not m:
        raise SystemExit("课名必须写成「第N课 名字」：%s" % lesson)
    return _safe("%02d-%s.html" % (int(m.group(1)), m.group(2).strip() or lesson))


if __name__ == "__main__":
    os.makedirs(ARCHIVE, exist_ok=True)
    total = 0
    for unit, lessons in UNITS:
        udir = _unit_dir(unit)
        for lesson, broadcast, qs in lessons:
            subtitle = unit + " · " + lesson
            if LAYOUT == "content":
                out = os.path.join(ARCHIVE, udir, _lesson_file(lesson))
                os.makedirs(os.path.dirname(out), exist_ok=True)
            else:
                out = os.path.join(ARCHIVE, "四年级" + SUBJECT + " · " + subtitle + ".html")
            engine_build(subtitle, qs, broadcast, out, SUBJECT)
            total += 1
            print("生成 %2d | %-40s | %2d 题 | %s" %
                  (total, subtitle, len(qs), os.path.relpath(out, ARCHIVE)))
    print("完成：共生成 %d 个 HTML 文件（布局 %s）" % (total, LAYOUT))
    print("目录：%s" % ARCHIVE)
    if LAYOUT == "content":
        print("下一步：重启 StudyBuddy（content/ 只在启动时扫描一次），再刷新页面")
        print("        自检：go run ./tools/bankcheck")
