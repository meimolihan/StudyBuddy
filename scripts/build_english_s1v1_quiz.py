# -*- coding: utf-8 -*-
"""人教版高中英语必修第一册（Welcome Unit + Unit 1~5）全部单元交互自测题生成脚本。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _quizlib import S, S2, M, run  # noqa: E402
from _concepts import concept_lessons  # noqa: E402


def L(entries, seed):
    return concept_lessons(entries, seed=seed)


UNITS = [
    ("Welcome Unit", [
        ("第1课 Welcome Unit", "📣 新学期从好的第一印象开始。想一想：开学第一天怎样做才能给同学和老师留下好印象？", L([
            ("first impression", "第一印象，初次见面时给别人留下的感觉"),
            ("anxious", "焦虑的，不安的，如 be anxious about the results 担心结果"),
            ("frightened", "害怕的，受惊吓的，感到恐惧的"),
            ("concentrate", "集中注意力，专心，如 concentrate on one's study 专心学习"),
            ("explore", "探索，探究，到处查看以了解新环境或新事物"),
            ("campus", "校园，学校范围内的场地"),
            ("outgoing", "外向的，开朗的，喜欢与人交往的"),
            ("confident", "自信的，有信心的，相信自己能做好"),
            ("curious", "好奇的，如 be curious about the world 对世界充满好奇"),
            ("形容词 -ing 与 -ed 的区别", "-ing 形容词说明事物本身的性质，-ed 形容词描述人的感受，如 boring 令人厌烦，bored 感到厌烦"),
            ("make + 宾语 + 形容词", "使役结构，表示使某人处于某种状态，如 make me nervous 使我紧张"),
            ("What if...?", "如果……怎么办，用来提出假设性的疑问，如 What if no one talks to me?"),
        ], 20262501)),
    ]),
    ("Unit 1 Teenage Life", [
        ("第2课 Unit 1 Teenage Life", "📣 青春期的生活丰富多彩。想一想：你想报名参加哪个社团或课外活动？", L([
            ("teenager", "青少年，十三岁到十九岁之间的年轻人"),
            ("volunteer", "志愿者；自愿做，不计报酬地为他人或集体服务"),
            ("debate", "辩论，双方就一个问题各自陈述理由的讨论"),
            ("suitable", "合适的，适宜的，如 be suitable for 适合……"),
            ("extra-curricular", "课外的，如 extra-curricular activities 课外活动"),
            ("sign up for", "报名参加，登记申请加入某个活动或组织"),
            ("prefer...to...", "比起……更喜欢……，两个宾语要用同类词，如 prefer singing to dancing"),
            ("clean up", "打扫干净，把地方或物品清理整洁"),
            ("challenge", "挑战，需要努力和勇气才能完成的困难任务"),
            ("定语从句", "在复合句中修饰名词或代词的从句，被修饰的词叫先行词，从句紧跟在先行词后面"),
            ("关系代词 that/who/which 的选用", "定语从句中先行词指人用 who 或 that，指物用 which 或 that"),
            ("关系代词作宾语可省略", "that/who/which 在定语从句中作宾语时可以省略，如 the book (that) I bought"),
        ], 20262502)),
    ]),
    ("Unit 2 Travelling Around", [
        ("第3课 Unit 2 Travelling Around", "📣 读万卷书也要行万里路。想一想：计划一次旅行要做哪些准备？", L([
            ("pack", "打包，收拾行李，把东西装进箱子或包里"),
            ("credit card", "信用卡，可以先消费后付款的银行卡"),
            ("amazing", "令人惊叹的，了不起的，让人十分惊讶的"),
            ("narrow", "狭窄的，宽度小的，反义词是 wide"),
            ("destination", "目的地，旅行要去的地方"),
            ("flight", "航班，飞机的航程，如 book a flight 订航班"),
            ("apply", "申请，请求得到，如 apply for a visa 申请签证"),
            ("sight", "景色，风景名胜，值得观看的景象"),
            ("arrangement", "安排，筹备，事先把事情计划好"),
            ("take control of", "控制，掌管，负责管理某事物"),
            ("现在进行时表将来", "用 be doing 表示按计划或安排即将发生的动作，如 I am leaving tomorrow"),
            ("will 与 be doing 表将来的区别", "will 表示临时决定或对将来的预测，be doing 表示已经计划安排好的事情"),
        ], 20262503)),
    ]),
    ("Unit 3 Sports and Fitness", [
        ("第4课 Unit 3 Sports and Fitness", "📣 运动让我们更健康更坚强。想一想：你最喜欢哪项运动，它给你带来了什么？", L([
            ("champion", "冠军，比赛中获得第一名的人或队伍"),
            ("medal", "奖牌，奖章，发给比赛获胜者的金属牌"),
            ("honour", "荣誉，尊敬，如 win honour for 为……赢得荣誉"),
            ("glory", "荣耀，光荣，巨大的声誉和赞美"),
            ("failure", "失败，没有做成某事，反义词是 success"),
            ("graceful", "优美的，优雅的，动作自然好看的"),
            ("compete", "比赛，竞争，如 compete in a race 参加赛跑"),
            ("injure", "使受伤，伤害身体，名词形式是 injury"),
            ("give up", "放弃，不再坚持做某事"),
            ("work out", "锻炼身体；计算出，想出解决办法"),
            ("附加疑问句", "在陈述句后面加上简短问句，前面肯定后面就用否定，前面否定后面就用肯定"),
            ("附加疑问句的回答", "回答要按事实来定，事实是肯定的用 yes，是否定的用 no，与汉语习惯不同"),
        ], 20262504)),
    ]),
    ("Unit 4 Natural Disasters", [
        ("第5课 Unit 4 Natural Disasters", "📣 了解灾害才能更好地保护自己。想一想：地震发生时我们应该怎样自救？", L([
            ("disaster", "灾难，灾害，造成重大损失的严重不幸事件"),
            ("quake", "地震，earthquake 的缩略形式"),
            ("rescue", "营救，援救，把人从危险中救出来"),
            ("shelter", "避难所，躲避危险或风雨的地方"),
            ("trap", "使困住，使陷入险境而无法脱身"),
            ("ruin", "毁灭，毁坏，使变成废墟"),
            ("survivor", "幸存者，从灾难或事故中活下来的人"),
            ("power", "电力；力量，如 power cut 停电"),
            ("burst", "爆裂，突然破裂，（水）涌出，如 burst into tears 突然大哭"),
            ("关系代词 whose 引导的定语从句", "whose 表示所属关系，指人和物都可以用，如 the boy whose father is a doctor"),
            ("介词 + 关系代词", "介词后面只能用 which 指物或 whom 指人，如 the house in which I lived"),
            ("限制性与非限制性定语从句", "限制性定语从句是先行词不可缺少的部分，不用逗号；非限制性定语从句作补充说明，要用逗号隔开"),
        ], 20262505)),
    ]),
    ("Unit 5 Languages Around the World", [
        ("第6课 Unit 5 Languages Around the World", "📣 语言是了解世界的窗口。想一想：为什么世界上会有这么多种不同的语言？", L([
            ("symbol", "符号，象征，代表某种意义的记号，如 a symbol of peace 和平的象征"),
            ("dialect", "方言，一个地区特有的语言变体"),
            ("appreciate", "欣赏，感激，重视并理解其价值"),
            ("regard", "看待，认为，如 regard...as... 把……看作……"),
            ("native", "本地的，本国的，如 native speaker 以母语为语言的人"),
            ("variety", "多样性，种类，如 a variety of 各种各样的"),
            ("carve", "雕刻，在木头、石头等材料上刻出图形或文字"),
            ("means", "方式，方法，手段，如 by this means 用这种方法"),
            ("demand", "要求，需要，如 meet the demand 满足需求"),
            ("关系副词 when/where/why 引导的定语从句", "先行词是时间用 when，是地点用 where，是原因用 why，关系词在从句中作状语"),
            ("关系副词与介词+关系代词的转换", "when 可换成 in/on which，where 可换成 in/at which，why 可换成 for which"),
            ("先行词是 way 的定语从句", "the way 后面可以用 that 或 in which 引导定语从句，关系词也常常省略"),
        ], 20262506)),
    ]),
]

if __name__ == "__main__":
    run(r"content/high/pep/grade1/volume1/english", "英语必修第一册", UNITS)
