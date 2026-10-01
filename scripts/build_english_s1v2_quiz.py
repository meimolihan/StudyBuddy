# -*- coding: utf-8 -*-
"""人教版高中英语必修第二册（Unit 1~5）全部单元交互自测题生成脚本。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _quizlib import S, S2, M, run  # noqa: E402
from _concepts import concept_lessons  # noqa: E402


def L(entries, seed):
    return concept_lessons(entries, seed=seed)


UNITS = [
    ("Unit 1 Cultural Heritage", [
        ("第1课 Unit 1 Cultural Heritage", "📣 文化遗产是历史留给我们的珍宝。想一想：我们为什么要保护像长城和故宫这样的古迹？", L([
            ("preserve", "保护，保存，使某物保持原有状态不受破坏，如 preserve old buildings"),
            ("promote", "促进，推动，如 promote cultural exchange 促进文化交流"),
            ("heritage", "遗产，传统，指历史流传下来的宝贵财富，如 cultural heritage 文化遗产"),
            ("temple", "寺庙，庙宇，供奉神灵或进行宗教活动的建筑"),
            ("donate", "捐赠，无偿把钱或物品送给需要的人或机构，如 donate books to a library"),
            ("attempt", "尝试，努力，试图做某事，如 make an attempt to do sth"),
            ("ensure", "确保，保证，使某事一定发生或一定完成"),
            ("disappear", "消失，不见，不再存在或再也看不见"),
            ("限制性与非限制性定语从句", "限制性从句是先行词不可缺少的部分，不用逗号；非限制性从句只作补充说明，要用逗号隔开"),
            ("which 指代整个主句", "非限制性定语从句中 which 可以指代前面整句话的内容，如 He was late again, which made the teacher angry"),
            ("非限制性定语从句逗号后不用 that", "逗号之后只能用 which 指物或 who 指人来引导非限制性定语从句，不能换成 that"),
            ("去留判断定语从句类型", "把定语从句去掉后句子仍然完整，说明它是非限制性定语从句；去掉后句意残缺，则是限制性定语从句"),
        ], 20262551)),
    ]),
    ("Unit 2 Wildlife Protection", [
        ("第2课 Unit 2 Wildlife Protection", "📣 地球不只属于人类。想一想：我们能为保护濒危动物做些什么？", L([
            ("endangered", "濒危的，有灭绝危险的，如 endangered animals 濒危动物"),
            ("extinct", "灭绝的，绝种的，指某类生物全部死亡、世上再无一员存活"),
            ("habitat", "栖息地，野生动植物自然生长和生活的环境"),
            ("awareness", "意识，认识，如 raise awareness of wildlife protection 提高野生动物保护意识"),
            ("species", "物种，一类具有共同特征的动植物的总称，单复数形式相同"),
            ("threaten", "威胁，预示可能给某人或某物带来危害"),
            ("reduce", "减少，降低，使数量或程度变小"),
            ("reserve", "自然保护区，为保护动植物而专门划出的区域，如 a nature reserve"),
            ("现在进行时的被动语态", "表示动作正在进行且主语是动作的承受者，结构是 is/are/am being done，如 The bridge is being built"),
            ("现在进行时被动语态的主谓一致", "助动词随主语变化，单数主语用 is being done，复数主语用 are being done"),
            ("现在进行时被动语态的疑问形式", "一般疑问句把 is/are 提到句首，如 Are the trees being cut down?"),
        ], 20262552)),
    ]),
    ("Unit 3 The Internet", [
        ("第3课 Unit 3 The Internet", "📣 网络改变了我们的生活方式。想一想：网络给学习和生活带来了哪些便利？", L([
            ("identity", "身份，一个人是谁的基本特征信息，如 identity card 身份证"),
            ("convenience", "方便，便利，指做事省时省力的好处"),
            ("update", "更新，把内容改成最新的状态，如 update the software 更新软件"),
            ("keep company", "陪伴，陪同，和某人待在一起使其不孤单"),
            ("benefit", "好处，益处；使受益，如 benefit from 受益于"),
            ("access", "使用机会，获取途径，如 have access to the Internet 能使用互联网"),
            ("privacy", "隐私，个人不愿被外人知道的私事或私密信息"),
            ("surf the Internet", "上网，浏览网络信息"),
            ("现在完成时的被动语态", "表示过去发生的动作已经完成并对现在有影响，且主语是承受者，结构是 has/have been done，如 The house has been cleaned"),
            ("现在完成时被动语态的主谓一致", "单数主语或第三人称单数用 has been done，复数主语用 have been done"),
            ("现在完成时被动语态的否定和疑问形式", "否定句在 has/have 后加 not，一般疑问句把 has/have 提到句首，如 Has the work been finished?"),
            ("与一般过去时被动语态的区别", "was/were done 只叙述过去的事实，has/have been done 强调动作对现在造成的影响或结果"),
        ], 20262553)),
    ]),
    ("Unit 4 History and Traditions", [
        ("第4课 Unit 4 History and Traditions", "📣 每个地方都有自己的历史和故事。想一想：你的家乡有哪些流传下来的传统？", L([
            ("confusing", "令人困惑的，难懂的，说明事物本身容易让人搞错，如 a confusing question"),
            ("puzzle", "使困惑，让某人想不明白是怎么回事"),
            ("belong to", "属于，为……所有，是某个团体或家族的成员"),
            ("ancestors", "祖先，祖宗，比自己早许多代的家族前辈"),
            ("surround", "环绕，包围，如 be surrounded by 被……环绕"),
            ("defend", "保卫，防御，抵抗攻击以保护某人或某地"),
            ("achievement", "成就，成绩，经过努力取得的重要成果"),
            ("tradition", "传统，世代相传并保留至今的风俗或做法"),
            ("过去分词作定语", "单个过去分词常放在名词前作定语，表被动或完成，如 a broken window；短语则放名词后，如 the novel written by Lu Xun"),
            ("过去分词作表语", "过去分词放在 be 动词后说明主语的感受或状态，如 We are surprised at the news"),
            ("现在分词与过去分词作定语的区别", "-ing 形式表示主动或进行，-ed 形式表示被动或完成，如 a moving story 与 moved fans"),
            ("过去分词短语相当于定语从句", "名词后的过去分词短语可以改写成一个被动意义的定语从句，如 the languages spoken there = the languages that are spoken there"),
        ], 20262554)),
    ]),
    ("Unit 5 Music", [
        ("第5课 Unit 5 Music", "📣 音乐能给生活增添色彩。想一想：音乐在你难过或开心时起过什么作用？", L([
            ("perform", "表演，演奏，在观众面前展示节目或演唱演奏乐曲"),
            ("award", "奖，奖品；授予，颁发，如 win an award 获得奖项"),
            ("stage", "舞台，供演员或歌手表演的地方"),
            ("talent", "天赋，才能，天生擅长的本领，如 have a talent for music"),
            ("musician", "音乐家，从事音乐创作或演奏的人"),
            ("band", "乐队，由多人组成、共同演奏音乐的团体"),
            ("solo", "独唱，独奏，由一个人单独完成的表演"),
            ("audience", "观众，听众，观看演出或聆听演奏的人，是集合名词"),
            ("动词-ing 形式作主语", "动词-ing 短语可以放在句首作主语，谓语动词用单数，如 Reading aloud is helpful"),
            ("动词-ing 形式作宾语", "动词-ing 短语可以放在动词后作宾语，如 enjoy swimming，注意 enjoy 后不能接不定式"),
            ("只接动词-ing 作宾语的动词", "enjoy、finish、mind、suggest、practise 等动词后面只能接动词-ing 形式，不能接不定式"),
            ("动词-ing 形式作介词宾语", "介词后面的动词一律用 -ing 形式，如 be good at singing、instead of waiting"),
        ], 20262555)),
    ]),
]

if __name__ == "__main__":
    run(r"content/high/pep/grade1/volume2/english", "英语必修第二册", UNITS)
