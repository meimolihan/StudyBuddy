# -*- coding: utf-8 -*-
"""人教版初中三年级下册英语（Unit 11~14）全部单元交互自测题生成脚本。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _quizlib import S, S2, M, run  # noqa: E402
from _concepts import concept_lessons  # noqa: E402


def L(entries, seed):
    return concept_lessons(entries, seed=seed)


UNITS = [
    ("第十一单元 Sad movies make me cry.", [
        ("第1课 Unit 11 Sad movies make me cry.", "📣 情绪像天气一样会变化。想一想：看电影让你哭过的经历还记得吗？", L([
            ("sleepy", "困倦的，想睡觉的，如 feel sleepy 感到犯困"),
            ("examine", "检查；检验，仔细查看以了解情况，如 examine the patient"),
            ("palace", "王宫；宫殿，国王和王室成员居住的豪华建筑"),
            ("power", "权力；力量，支配或影响别人的能力"),
            ("prime minister", "首相；大臣，一个国家政府里的最高行政官员"),
            ("courage", "勇气，敢于面对困难或危险的精神"),
            ("pull together", "齐心协力，大家团结一致把事情做好"),
            ("importance", "重要性，如 the importance of learning English 学英语的重要性"),
            ("friendship", "友谊，朋友之间真诚相待的感情"),
            ("make sb. do sth.", "使某人做某事，make 后面的动词用原形，如 make me cry 让我哭泣"),
            ("make sb. + 形容词", "使某人处于某种状态，如 make me happy 让我快乐，make him sleepy 让他犯困"),
            ("It is...who...", "强调句型，把要强调的部分放在 It is 后面，如 It is you who make me smile 强调是你"),
            ("would rather do sth.", "宁愿做某事，表示更愿意选择这样做，如 I would rather stay at home"),
        ], 20262151)),
    ]),
    ("第十二单元 Life is full of the unexpected.", [
        ("第2课 Unit 12 Life is full of the unexpected.", "📣 生活里总有措手不及的时刻。想一想：你有没有因为睡过头而迟到的经历？", L([
            ("unexpected", "出乎意料的，没有预料到会发生的事情"),
            ("oversleep", "睡过头，睡过了本来计划的时间，过去式是 overslept"),
            ("till", "直到……为止，和 until 意思相同，如 wait till he comes"),
            ("stare", "盯着看，凝视，如 stare at sb. 盯着某人看"),
            ("disbelief", "不信；怀疑，觉得难以相信的心情"),
            ("alive", "活着的，还活在世上的，常作表语，如 stay alive"),
            ("cancel", "取消，把安排好的活动撤掉，如 cancel the meeting"),
            ("hoax", "骗局；恶作剧，故意编造出来骗人的假消息"),
            ("fool", "愚弄；傻瓜，作动词指骗人上当，如 April Fool's Day 愚人节"),
            ("show up", "露面，到场，如 He didn't show up 他没有出现"),
            ("过去完成时（had done）", "表示过去某一时间或动作之前已经发生的动作，结构是 had + 过去分词"),
            ("by the time...", "到……的时候为止，引导时间状语从句，主句常用过去完成时，如 By the time I got up, my brother had left"),
            ("Life is full of the unexpected.", "生活充满了意外，full of 表示充满，the unexpected 指意外的事情"),
        ], 20262152)),
    ]),
    ("第十三单元 We're trying to save the earth!", [
        ("第3课 Unit 13 We're trying to save the earth!", "📣 保护地球人人有责。想一想：你平时做过哪些对环保有用的小事？", L([
            ("pollute", "污染，把脏东西带进空气、水或土地使其变脏"),
            ("recycle", "回收利用，把用过的东西加工后重新使用"),
            ("industry", "工业，制造产品的生产部门，如 heavy industry 重工业"),
            ("advantage", "优点，有利之处，反义词是 disadvantage"),
            ("ugly", "丑陋的，难看的，让人看着不舒服的"),
            ("litter", "垃圾；乱扔杂物，作动词指随手扔垃圾"),
            ("plastic", "塑料；塑料的，一种人造的轻便材料"),
            ("cruel", "残酷的，残忍的，如 be cruel to animals 对动物残忍"),
            ("harmful", "有害的，会造成伤害的，如 harmful gases 有害气体"),
            ("be harmful to", "对……有害，如 Smoking is harmful to your health 吸烟有害健康"),
            ("现在进行时", "表示此刻正在进行的动作，结构是 am/is/are + 动词的 ing 形式，如 We're trying to save the earth"),
            ("被动语态复习", "表示主语是动作的承受者，一般现在时用 am/is/are + 过去分词，一般过去时用 was/were + 过去分词"),
            ("现在完成时", "表示过去发生的动作对现在有影响，结构是 have/has + 过去分词，如 I have finished my homework"),
        ], 20262153)),
    ]),
    ("第十四单元 I remember meeting all of you in Grade 7.", [
        ("第4课 Unit 14 I remember meeting all of you in Grade 7.", "📣 毕业是回忆也是新的开始。想一想：初中三年你最难忘的一件事是什么？", L([
            ("graduate", "毕业，读完一个学习阶段，如 graduate from school 从学校毕业"),
            ("thankful", "感谢的，感激的，心怀感恩的"),
            ("ahead", "在前面，向前，如 the road ahead 前方的路"),
            ("survey", "调查，收集信息了解情况，如 do a survey 做调查"),
            ("standard", "标准，水平，衡量事物的准则"),
            ("overcome", "克服，战胜困难或恐惧，过去式是 overcame"),
            ("congratulate", "祝贺，向别人道喜，如 congratulate sb. on his success"),
            ("separate", "分开，分离，如 separate from 与……分开"),
            ("responsible", "有责任的，尽责的，如 a responsible student 有责任感的学生"),
            ("remember doing sth.", "记得做过某事，事情已经发生，如 I remember meeting you in Grade 7"),
            ("remember to do sth.", "记得要去做某事，事情还没有发生，如 Remember to close the window"),
            ("be responsible for", "对……负责，如 be responsible for your own study 对自己的学习负责"),
            ("look forward to doing sth.", "期待做某事，这里的 to 是介词，后面接动名词，如 I look forward to seeing you"),
        ], 20262154)),
    ]),
]

if __name__ == "__main__":
    run(r"content/middle/pep/grade3/volume2/english", "英语下册", UNITS)
