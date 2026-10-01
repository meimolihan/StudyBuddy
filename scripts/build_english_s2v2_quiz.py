# -*- coding: utf-8 -*-
"""人教版高中英语选择性必修第二册（Unit 1~5）全部单元交互自测题生成脚本。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _quizlib import S, S2, M, run  # noqa: E402
from _concepts import concept_lessons  # noqa: E402


def L(entries, seed):
    return concept_lessons(entries, seed=seed)


UNITS = [
    ("Unit 1 Science and Scientists", [
        ("第1课 Unit 1 Science and Scientists", "📣 科学发现源于严谨的观察和大胆的追问。想一想：科学家面对质疑时最需要什么品质？", L([
            ("subscribe", "订阅（报刊）；定期捐款；赞同，如 subscribe to a magazine 订阅一本杂志"),
            ("blame", "责备，指责，如 be to blame for 对……负有责任，该受责备"),
            ("decrease", "减少，降低，既可作动词也可作名词，如 decrease by 10% 减少了百分之十"),
            ("defend", "防御，保卫；为……辩护，如 defend the country 保卫国家"),
            ("in charge of", "负责，主管，如 The doctor is in charge of the ward"),
            ("epidemic", "流行病，（流行病的）爆发与蔓延"),
            ("multiple", "数量多的，多种多样的；倍数"),
            ("pump", "用泵抽送；泵，抽水机，如 pump water 抽水"),
            ("link...to...", "把……与……连接或联系起来，如 Scientists linked the disease to polluted water"),
            ("表语从句", "从句放在系动词后面作表语，说明主语的内容，如 The question is who can solve the problem"),
            ("so...that 引导结果状语从句", "so + 形容词/副词 + that 从句，表示如此……以至于，如 The water was so dirty that nobody dared to drink it"),
            ("强调句 It is...that/who", "用 It is/was + 被强调部分 + that/who + 其余部分来强调句子成分，如 It was John who helped me，强调人时可用 who"),
        ], 20262951)),
    ]),
    ("Unit 2 Bridging Cultures", [
        ("第2课 Unit 2 Bridging Cultures", "📣 走出国门，既要拥抱世界也要传递家乡的声音。想一想：留学在外最先要克服的困难是什么？", L([
            ("adaptation", "适应；改写本，改编，如 adaptation to the new environment 对新环境的适应"),
            ("participation", "参加，参与，如 participation in class activities 参加课堂活动"),
            ("engage", "参与，从事，如 engage in 从事，参与；吸引住（注意力）"),
            ("expense", "费用，花费，开支，如 at the expense of 以……为代价"),
            ("deny", "否认，拒绝承认，如 deny doing sth 否认做过某事"),
            ("participate", "参加，参与，常与 in 连用，相当于 take part in"),
            ("homesick", "想家的，思乡的，如 feel homesick 感到想家"),
            ("motivation", "动力，积极性，动机，如 stay motivated 保持积极性"),
            ("It is the first time that... 句型", "表示某人第一次做某事，that 从句用现在完成时，如 It is the first time that I have visited Beijing"),
            ("名词性从句复习", "在句中起名词作用的从句，包括主语从句、宾语从句、表语从句和同位语从句，从句一律用陈述语序"),
            ("宾语从句的连接词", "that 无实际意义常可省略；whether/if 表是否；what、who、when 等连接代词副词要在从句中充当成分"),
            ("同位语从句与定语从句的区别", "同位语从句说明名词的具体内容，that 不作成分；定语从句修饰名词，that 在从句中作主语或宾语"),
        ], 20262952)),
    ]),
    ("Unit 3 Food and Culture", [
        ("第3课 Unit 3 Food and Culture", "📣 一方水土养一方人，餐桌上的习惯藏着文化的密码。想一想：中国各地饮食差异反映了什么？", L([
            ("cuisine", "菜肴，烹饪风格，如 Sichuan cuisine 四川菜"),
            ("pepper", "胡椒，辣椒"),
            ("recipe", "食谱，烹饪方法，如 follow a recipe 按照食谱做菜"),
            ("prior", "在先的，优先的，常用 prior to 表示在……之前"),
            ("consist of", "由……组成，构成，如 The team consists of ten members，注意不用被动语态"),
            ("bean curd", "豆腐，等于 tofu"),
            ("onion", "洋葱，如 a piece of onion 一片洋葱"),
            ("chew", "咀嚼，咬，如 chew food slowly 细细咀嚼食物"),
            ("canteen", "食堂，小卖部，如 the school canteen 学校食堂"),
            ("过去完成时", "had + 过去分词，表示在过去某一时间或动作之前已发生的动作，即过去的过去，如 By the time he arrived, the meeting had ended"),
            ("过去完成时的被动形式", "had been done，表示过去某一时刻之前已被完成的动作，如 The bridge had been built before 1990"),
            ("过去完成时与一般过去时的区别", "过去完成时强调动作发生在过去某个动作或时间之前；一般过去时只陈述过去发生的事，不强调先后关系"),
            ("by the time", "到……时候为止，引导时间状语从句，从句用一般过去时时，主句常用过去完成时"),
        ], 20262953)),
    ]),
    ("Unit 4 Journey Across a Vast Land", [
        ("第4课 Unit 4 Journey Across a Vast Land", "📣 坐上火车横穿山川湖泊，旅行是最好的地理课。想一想：旅途中最难忘的风景是什么样的？", L([
            ("literal", "字面意义的，逐字的，与 figurative（比喻意义的）相对"),
            ("anticipate", "预期，预料，期待，如 anticipate doing sth 预料到将做某事"),
            ("fascinating", "迷人的，有极大吸引力的，如 a fascinating story 一个迷人的故事"),
            ("departure", "离开，出发，启程，反义词是 arrival，如 departure time 出发时间"),
            ("envelope", "信封，封皮，如 write an address on the envelope 在信封上写地址"),
            ("scenery", "风景，景色，指一个地区自然风光的总称，不可数"),
            ("vast", "辽阔的，巨大的，如 a vast land 广袤的大地"),
            ("duration", "期间，持续时间，如 for the duration of the trip 在旅行期间"),
            ("breathtaking", "激动人心的，惊人的，美得令人屏息的，如 breathtaking scenery 美得惊人的风景"),
            ("过去分词作状语", "过去分词短语作状语，表示被动或完成的动作，可表时间、原因、伴随等，如 Seen from the hill, the town looks beautiful"),
            ("过去分词作原因状语", "过去分词短语说明主句动作发生的原因，如 Tired and hungry, he went straight to bed"),
            ("过去分词与现在分词作状语的区别", "现在分词表示主动或进行，与主语是逻辑上的主谓关系；过去分词表示被动或完成，与主语是逻辑上的动宾关系"),
        ], 20262954)),
    ]),
    ("Unit 5 First Aid", [
        ("第5课 Unit 5 First Aid", "📣 掌握急救知识，关键时刻能挽救生命。想一想：遇到有人突然晕倒，我们应该先做什么？", L([
            ("choke", "（使）窒息，噎住，如 choke on food 被食物噎住"),
            ("symptom", "症状，征兆，如 the symptoms of a cold 感冒的症状"),
            ("urgent", "紧急的，急迫的，如 an urgent call 紧急电话"),
            ("unconscious", "失去知觉的，无意识的，反义词是 conscious"),
            ("interrupt", "打断，中断，插话，如 interrupt the conversation 打断谈话"),
            ("aid", "帮助，援助，如 first aid 急救；in aid of 为了帮助……"),
            ("bleed", "流血，出血，过去式和过去分词是 bled"),
            ("poison", "毒药，毒物；使中毒，毒害"),
            ("swallow", "吞下，咽下；吞没，如 swallow the medicine 把药咽下去"),
            ("省略 to 的不定式", "感官动词 see、hear、watch 和使役动词 make、let、have 后的宾语补足语省略 to，如 I saw him cross the street，变被动语态时要还原 to"),
            ("动词-ing 的被动式", "being done 表示该动作正在进行且与逻辑主语是被动关系，如 The problem being discussed is important"),
            ("动词-ing 的被动完成式", "having been done 表示该动作先于谓语动词发生且与逻辑主语是被动关系，如 Having been told many times, he still forgot"),
        ], 20262955)),
    ]),
]

if __name__ == "__main__":
    run(r"content/high/pep/grade2/volume2/english", "英语选择性必修第二册", UNITS)
