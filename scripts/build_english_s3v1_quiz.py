# -*- coding: utf-8 -*-
"""人教版高中英语选择性必修第三册（Unit 1~5）全部单元交互自测题生成脚本。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _quizlib import S, S2, M, run  # noqa: E402
from _concepts import concept_lessons  # noqa: E402


def L(entries, seed):
    return concept_lessons(entries, seed=seed)


UNITS = [
    ("Unit 1 Art", [
        ("第1课 Unit 1 Art", "📣 走进西方绘画艺术的殿堂。想一想：同一幅画为什么在不同人眼里有不同的美？", L([
            ("western painting", "西方绘画，欧美传统绘画艺术的总称，包括油画、水彩画等多种形式"),
            ("auction", "拍卖，公开竞价出售物品或艺术品的方式"),
            ("perspective", "透视法，绘画中表现物体远近和空间关系的技法"),
            ("exhibition", "展览，展出绘画等艺术作品供人参观的活动"),
            ("precise", "精确的，准确的，注重细节的"),
            ("dimension", "维度，尺寸；（事物的）方面，如 add a new dimension 增添新的层面"),
            ("masterpiece", "杰作，代表作，某位艺术家最出色的作品"),
            ("sculpture", "雕塑，雕刻作品；雕刻这门艺术"),
            ("gallery", "美术馆，画廊，陈列和展出艺术作品的场所"),
            ("动词不定式作表语", "不定式放在系动词后面说明主语的内容，如 My dream is to become a painter"),
            ("动词不定式作定语", "不定式放在名词后面作修饰语，如 I have a lot of homework to do"),
            ("疑问词 + 不定式", "疑问词后面接不定式构成的短语可作宾语，如 I don't know what to say"),
            ("动词不定式作状语", "不定式短语作状语表示目的或结果，如 He ran fast to catch the bus"),
        ], 20263251)),
    ]),
    ("Unit 2 Healthy Lifestyle", [
        ("第2课 Unit 2 Healthy Lifestyle", "📣 好习惯是健康生活的基石。想一想：你最想改掉的一个坏习惯是什么？", L([
            ("alcohol", "酒，酒精，含酒精的饮料"),
            ("dominate", "支配，控制，在……中占主导地位"),
            ("repeatedly", "反复地，再三地，一次又一次地"),
            ("comprise", "包含，由……组成，如 be comprised of 由……构成"),
            ("cigarette", "香烟，卷烟"),
            ("abuse", "滥用；虐待，如 drug abuse 药物滥用"),
            ("reward", "奖励，回报；报答，给某人以酬谢"),
            ("discipline", "自律，纪律；训练，管教"),
            ("动词不定式作主语", "不定式短语放在句首或在谓语前作主语，如 To give up smoking is difficult"),
            ("it 作形式主语", "真正主语较长时用 it 代替并后置，如 It is important to exercise every day"),
            ("动词不定式的完成式", "to have done 表示不定式动作发生在谓语动作之前，如 He is said to have left"),
            ("动词不定式的被动式", "to be done 表示不定式的逻辑主语是动作的承受者，如 The work needs to be finished"),
        ], 20263252)),
    ]),
    ("Unit 3 Environmental Protection", [
        ("第3课 Unit 3 Environmental Protection", "📣 地球的气候正在敲响警钟。想一想：你的日常生活会产生多少碳足迹？", L([
            ("emission", "排放物，排放，如 carbon emission 碳排放"),
            ("fossil fuel", "化石燃料，煤、石油、天然气等由古代生物形成的燃料"),
            ("dioxide", "二氧化物，如 carbon dioxide 二氧化碳"),
            ("carbon footprint", "碳足迹，一个人或活动直接和间接产生的二氧化碳总量"),
            ("greenhouse effect", "温室效应，大气层吸收热量使地球变暖的现象"),
            ("seal", "海豹，一种生活在海洋中的鳍足哺乳动物"),
            ("release", "释放，排放；发行，发布，如 release carbon dioxide 排放二氧化碳"),
            ("restrict", "限制，约束，把数量或范围控制在一定限度内"),
            ("直接引语和间接引语", "直接引语原样转述别人的话并加引号，间接引语用自己的话转述且不加引号"),
            ("间接引语的时态呼应", "主句为过去时态时，间接引语中的时态要相应后移，如 said 后 is 变 was"),
            ("if/whether 引导的间接问句", "一般疑问句变为间接引语时用 if 或 whether 引导并改陈述语序"),
            ("疑问词引导的间接问句", "特殊疑问句变为间接引语时保留疑问词并改陈述语序，如 where he lives"),
        ], 20263253)),
    ]),
    ("Unit 4 Adversity and Courage", [
        ("第4课 Unit 4 Adversity and Courage", "📣 逆境淬炼真正的勇气。想一想：面对困难时是什么支撑你坚持下去？", L([
            ("adversity", "逆境，困境，不利的处境"),
            ("perseverance", "毅力，坚持不懈，不惧困难坚持做下去的品质"),
            ("furnace", "火炉，熔炉，取暖或熔炼金属用的炉子"),
            ("abandon", "放弃，抛弃，中止进行中的计划或活动"),
            ("supplement", "补充，增补；补充物，如 vitamin supplements 维生素补充剂"),
            ("expedition", "探险，远征，为特定目的进行的长途考察活动"),
            ("endurance", "耐力，忍耐力，长时间承受艰苦的能力"),
            ("crew", "全体船员，全体机组人员，一起工作的团队"),
            ("现在完成进行时", "have/has been doing 表示动作从过去开始持续到现在且可能继续，如 I have been waiting for two hours"),
            ("过去完成进行时", "had been doing 表示动作在过去某时之前一直持续，如 He had been working all day"),
            ("将来完成时", "will have done 表示将来某时之前已完成的动作，如 By 2030 we will have graduated"),
            ("现在完成时的持续用法", "have/has done 表示动作从过去持续到现在，常与 for 或 since 连用，如 I have lived here since 2020"),
        ], 20263254)),
    ]),
    ("Unit 5 Poems", [
        ("第5课 Unit 5 Poems", "📣 诗歌用最凝练的语言倾诉深情。想一想：哪一句诗曾打动了你？", L([
            ("recite", "背诵，朗诵，凭记忆当众说出诗文"),
            ("rhyme", "押韵，韵脚，诗行末尾读音相同或相近的现象"),
            ("sorrow", "悲伤，悲痛，内心深处的忧愁与痛苦"),
            ("drama", "戏剧，话剧；戏剧性事件"),
            ("motive", "动机，目的，促使人做某事的内在原因"),
            ("verse", "诗节，诗句，诗的一段或一行"),
            ("prose", "散文，散文体，不押韵的普通书面语言"),
            ("rhythm", "节奏，韵律，声音按一定规律交替出现的节拍"),
            ("定语从句复习", "由关系代词或关系副词引导、修饰名词的从句，先行词是人用 who/that，是物用 which/that"),
            ("非限制性定语从句", "用逗号与主句隔开的定语从句，起补充说明作用，不能用 that 引导，如 Beijing, which is the capital of China, is beautiful"),
            ("介词 + 关系代词", "定语从句中介词提前到关系代词前的结构，关系代词指物用 which、指人用 whom，如 the house in which I lived"),
            ("关系副词", "when、where、why 分别在定语从句中代替表时间、地点、原因的先行词"),
        ], 20263255)),
    ]),
]

if __name__ == "__main__":
    run(r"content/high/pep/grade3/volume1/english", "英语选择性必修第三册", UNITS)
