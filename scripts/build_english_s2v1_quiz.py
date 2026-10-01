# -*- coding: utf-8 -*-
"""人教版高中英语选择性必修第一册（Unit 1~5）全部单元交互自测题生成脚本。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _quizlib import S, S2, M, run  # noqa: E402
from _concepts import concept_lessons  # noqa: E402


def L(entries, seed):
    return concept_lessons(entries, seed=seed)


UNITS = [
    ("Unit 1 People of Achievement", [
        ("第1课 Unit 1 People of Achievement", "📣 杰出人物用坚持改变世界。想一想：你最敬佩的科学家是谁，他身上有什么品质？", L([
            ("commitment", "承诺，投入；奉献"),
            ("graduate", "毕业；毕业生，如 graduate from university 大学毕业"),
            ("policy", "政策，方针，政府或机构制定的行动准则"),
            ("insight", "洞察力，深刻见解，如 have an insight into 对……有深刻了解"),
            ("remarkable", "非凡的，卓越的，值得注意的"),
            ("potential", "潜力，潜能；潜在的，如 realize one's potential 发挥潜能"),
            ("evaluate", "评价，评估，仔细判断事物的价值或效果"),
            ("acknowledge", "承认，答谢，如 acknowledge one's mistake 承认错误"),
            ("come up with", "想出，提出（主意、计划等）"),
            ("主谓一致", "谓语动词在人称和数上必须与主语保持一致，如 The books are on the desk"),
            ("就近原则", "either...or、neither...nor、not only...but also 连接主语时，谓语动词与靠近它的主语一致"),
            ("主语从句复习", "从句作句子主语，如 What he said is true，此时谓语动词通常用单数"),
            ("同位语从句", "说明名词具体内容的从句，常用 that 引导，如 the news that we won the game"),
        ], 20262941)),
    ]),
    ("Unit 2 Looking into the Future", [
        ("第2课 Unit 2 Looking into the Future", "📣 未来掌握在今天的手中。想一想：二十年后的生活会因为科技发生哪些变化？", L([
            ("predict", "预测，预言，预先说出将要发生的事情"),
            ("occupation", "职业，工作；占领"),
            ("oppose", "反对，如 be opposed to doing sth 反对做某事"),
            ("absence", "缺席，不在，反义词是 presence，如 in the absence of 在缺乏……的情况下"),
            ("emphasis", "强调，重点，如 put emphasis on 强调……"),
            ("forecast", "预报，预测，如 weather forecast 天气预报"),
            ("current", "当前的，现在的；水流，电流"),
            ("resist", "抵制，抵抗，抗拒，如 resist the temptation 抵制诱惑"),
            ("keep in touch with", "与……保持联系"),
            ("动词不定式作宾语", "不定式跟在及物动词后面作宾语，如 I hope to travel abroad，常用于 want, hope, decide 等词后"),
            ("动词不定式作表语", "不定式放在系动词后面说明主语的内容，如 My dream is to become a doctor"),
            ("动词不定式作宾语补足语", "不定式放在宾语后面补充说明宾语的动作，如 The teacher asked us to hand in our homework"),
            ("将来进行时", "will be doing 表示将来某一时刻正在进行的动作，如 This time tomorrow I will be flying to Beijing"),
        ], 20262942)),
    ]),
    ("Unit 3 Fascinating Parks", [
        ("第3课 Unit 3 Fascinating Parks", "📣 公园里有自然的奇妙与设计的智慧。想一想：如果让你设计一个主题公园，它是什么样的？", L([
            ("amusement", "娱乐，消遣，如 amusement park 游乐园"),
            ("unique", "独特的，独一无二的，如 a unique experience 一次独特的经历"),
            ("sponsor", "赞助，主办；赞助者，出资支持活动的人或机构"),
            ("extend", "延伸，延长，扩展，如 extend the deadline 延长截止日期"),
            ("adore", "热爱，喜爱，非常喜欢"),
            ("entertain", "使娱乐，使快乐；招待，款待"),
            ("theme", "主题，题目，如 theme park 主题公园"),
            ("preserve", "保护，保存，维护，使不受破坏"),
            ("be modelled after", "根据……模仿，仿造，如 The park is modelled after a fairy tale"),
            ("动词-ing 形式作状语", "-ing 短语作状语表示伴随、原因或结果，如 Walking along the street, I met an old friend"),
            ("动词-ing 形式作表语", "-ing 形式放在系动词后说明主语的内容或特征，如 His hobby is collecting stamps"),
            ("-ing 短语的逻辑主语", "-ing 短语的逻辑主语应与句子主语一致，如 Entering the room, she found everything in order"),
            ("动词-ing 的完成式", "having done 表示该动作发生在谓语动词之前，如 Having finished his work, he went home"),
        ], 20262943)),
    ]),
    ("Unit 4 Body Language", [
        ("第4课 Unit 4 Body Language", "📣 有时一个手势胜过千言万语。想一想：哪些肢体动作在不同国家含义不同？", L([
            ("gesture", "手势，姿势，用手部动作表达意思"),
            ("interact", "交流，互动，如 interact with 与……交流互动"),
            ("unspoken", "未说出口的，无声的，如 unspoken rules 不成文的规定"),
            ("barrier", "障碍，屏障，如 a cultural barrier 文化障碍"),
            ("trip", "绊倒，使摔倒；旅行，如 trip over 被绊倒"),
            ("vary", "不同，变化，如 vary from culture to culture 因文化而异"),
            ("stare at", "凝视，盯着看，长时间注视"),
            ("embarrassed", "尴尬的，难为情的，感到不好意思的"),
            ("动词-ing 形式作定语", "-ing 短语放在名词后面修饰名词，相当于定语从句，如 the girl standing there = the girl who is standing there"),
            ("动词-ing 作前置定语", "单个 -ing 形式直接放在名词前面修饰名词，如 sleeping baby 熟睡的婴儿，exciting news 令人兴奋的消息"),
            ("省略", "为避免重复省掉句中相同的部分，使句子简洁，如 He can swim better than I (can swim)"),
            ("状语从句中的省略", "当从句主语与主句主语相同且从句含 be 动词时，可省略主语和 be，如 While walking, I met him"),
        ], 20262944)),
    ]),
    ("Unit 5 Working the Land", [
        ("第5课 Unit 5 Working the Land", "📣 一粥一饭来之不易。想一想：袁隆平爷爷的贡献给我们的生活带来了什么改变？", L([
            ("yield", "产量；产出，出产，如 a high yield of rice 水稻的高产量"),
            ("celebrity", "名人，名声，广为人知的著名人物"),
            ("devote", "献身，致力，如 devote oneself to 致力于"),
            ("strain", "压力，负担；（身体）拉伤，如 put a strain on 给……造成压力"),
            ("conventional", "传统的，常规的，按惯例进行的"),
            ("output", "产量，输出，如 grain output 粮食产量"),
            ("decade", "十年，十年期，如 in the past decade 在过去十年里"),
            ("be suited to", "适合于，如 The job is suited to his abilities"),
            ("主语从句", "从句在句中作主语，如 Whether he will come is unknown，谓语动词用单数"),
            ("表语从句", "从句放在系动词后面作表语，如 The problem is that we lack money"),
            ("it 作形式主语", "主语从句较长时用 it 代替并后置真正主语，如 It is important that we learn English"),
            ("It is said that... 句型", "it 作形式主语的常见表达，据说……，如 It is said that he is a good teacher"),
        ], 20262945)),
    ]),
]

if __name__ == "__main__":
    run(r"content/high/pep/grade2/volume1/english", "英语选择性必修第一册", UNITS)
