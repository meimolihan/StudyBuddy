# -*- coding: utf-8 -*-
"""人教版初中三年级上册英语（Unit 1~10）全部单元交互自测题生成脚本。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _quizlib import S, S2, M, run  # noqa: E402
from _concepts import concept_lessons  # noqa: E402


def L(entries, seed):
    return concept_lessons(entries, seed=seed)


UNITS = [
    ("第一单元 How can we become good learners?", [
        ("第1课 Unit 1 How can we become good learners?", "📣 学好英语有方法可循。想一想：你平时用什么办法记单词最有效？", L([
            ("textbook", "教科书；课本，上课时用的正式书籍"),
            ("aloud", "大声地；出声地，如 read aloud 朗读"),
            ("sentence", "句子，由单词组成、能表达完整意思的语言单位"),
            ("patient", "有耐心的，如 be patient with sb. 对某人有耐心"),
            ("expression", "表达方式；措辞，也可以指脸上的表情"),
            ("grammar", "语法，把单词组合成句子时要遵守的规则"),
            ("take notes", "做笔记，把重要的内容记录下来"),
            ("ability", "能力，能够做成某事的本领"),
            ("connect", "连接；联系，如 connect...with... 把……和……联系起来"),
            ("by doing sth.", "通过做某事的方式，by 后面接动词的 ing 形式，表示手段或方法"),
            ("the more...the more...", "越……就越……，表示两件事的程度同步增加"),
            ("so...that...", "如此……以至于……，so 后面接形容词或副词，that 后面接结果"),
            ("keep doing sth.", "一直或坚持做某事，表示动作不间断"),
        ], 20262101)),
    ]),
    ("第二单元 I think that mooncakes are delicious!", [
        ("第2课 Unit 2 I think that mooncakes are delicious!", "📣 传统节日承载着家的味道。想一想：中秋节你们家有哪些特别的习俗？", L([
            ("mooncake", "月饼，中秋节吃的圆形带馅甜饼"),
            ("lantern", "灯笼，里面点灯用来照明或装饰的传统用具"),
            ("stranger", "陌生人，自己不认识的人"),
            ("relative", "亲戚，亲属，如 a relative of mine 我的一个亲戚"),
            ("admire", "欣赏；仰慕，因别人优秀而心生敬佩"),
            ("folk", "民间的，如 folk story 民间故事"),
            ("goddess", "女神，神话中女性形象的神"),
            ("dessert", "甜点，正餐之后吃的甜味食品"),
            ("put on weight", "增加体重，长胖，反义说法是 lose weight"),
            ("lay out", "摆放；布置，如 lay out the fruit 摆上水果"),
            ("宾语从句（that 引导）", "放在动词后面作宾语的从句，由 that 引导时 that 本身没有词义，常可省略"),
            ("if/whether 表示“是否”", "引导宾语从句时表示是否，两者常可互换，if 后面不能直接接 or not"),
            ("感叹句（What 和 How）", "What 修饰名词，How 修饰形容词或副词，用来表达强烈的感情"),
        ], 20262102)),
    ]),
    ("第三单元 Could you please tell me where the restrooms are?", [
        ("第3课 Unit 3 Could you please tell me where the restrooms are?", "📣 出门在外会问路很重要。想一想：用英语给外国朋友指路你会怎么说？", L([
            ("restroom", "洗手间，公共厕所的委婉说法"),
            ("stamp", "邮票，寄信时贴在信封上的小票"),
            ("beside", "在……旁边，表示位置紧靠着"),
            ("postcard", "明信片，不用信封就能寄出的卡片"),
            ("rush", "匆忙；仓促，如 rush to do sth. 急着去做某事"),
            ("suggest", "建议，提出自己的意见或想法"),
            ("staff", "员工，一个单位的全体工作人员"),
            ("convenient", "便利的，方便的，做起来不费事"),
            ("polite", "有礼貌的，客气的，反义词是 impolite"),
            ("direction", "方向，方位，如 ask for directions 问路"),
            ("request", "要求，请求，礼貌地向别人提出需要"),
            ("疑问词引导的宾语从句", "由 where/when/how 等疑问词引导作宾语的从句，要用陈述句语序，即连接词+主语+谓语"),
            ("礼貌问路的表达", "常用 Excuse me, could you please tell me how to get to...? 来询问去某地的路"),
        ], 20262103)),
    ]),
    ("第四单元 I used to be afraid of the dark.", [
        ("第4课 Unit 4 I used to be afraid of the dark.", "📣 我们都在悄悄长大和改变。想一想：和三年前相比，你最大的变化是什么？", L([
            ("humorous", "幽默的，滑稽有趣的，能逗人发笑"),
            ("silent", "沉默的，不说话的，如 keep silent 保持沉默"),
            ("helpful", "有帮助的，有用的"),
            ("interview", "面试；采访，通过提问来了解或挑选人"),
            ("deal with", "对付；应付，处理难题或麻烦事"),
            ("dare", "敢，敢于，后面常接 to do sth."),
            ("private", "私人的，私密的，不想让别人知道的"),
            ("speech", "讲话，发言，当众发表的一番话"),
            ("in person", "亲自，本人到场，不通过别人代替"),
            ("used to do sth.", "过去常常做某事，表示过去的习惯或状态，现在不再这样了"),
            ("used to 的疑问和否定", "疑问用 Did you use to...? 否定用 didn't use to do"),
            ("from time to time", "偶尔，不时地，表示有时会做某事"),
        ], 20262104)),
    ]),
    ("第五单元 What are the shirts made of?", [
        ("第5课 Unit 5 What are the shirts made of?", "📣 身边的东西各有来历。想一想：你的书包、鞋子分别是什么材料做的？", L([
            ("chopsticks", "筷子，中国人吃饭用的两根细长木棍"),
            ("coin", "硬币，金属制成的小额货币"),
            ("fork", "餐叉，西方人吃饭用的叉子"),
            ("cotton", "棉；棉花，用来纺线织布的天然材料"),
            ("steel", "钢，铁和碳等炼成的坚硬金属"),
            ("glass", "玻璃，透明易碎的材料，也指玻璃杯"),
            ("fair", "展览会，交易会，展出商品供人参观订货"),
            ("produce", "生产，制造出产品"),
            ("widely", "广泛地，大范围地，如 be widely used 被广泛使用"),
            ("be made of", "由……制成，能看出原材料，如桌子由木头制成"),
            ("be made from", "由……制成，原材料发生变化看不出原样，如纸由木头制成"),
            ("be made in", "在某地制造，后面接产地，如 made in China"),
            ("一般现在时的被动语态", "表示某物被……，结构是 am/is/are + 过去分词，主语是动作的承受者"),
        ], 20262105)),
    ]),
    ("第六单元 When was it invented?", [
        ("第6课 Unit 6 When was it invented?", "📣 小发明改变大世界。想一想：如果能发明一样东西，你想发明什么？", L([
            ("invent", "发明，创造出以前没有的东西"),
            ("inventor", "发明家，发明东西的人"),
            ("electricity", "电，一种能带来光和热的能量"),
            ("style", "样式，款式，如 in a modern style 以现代的样式"),
            ("daily", "每日的，日常的，如 daily life 日常生活"),
            ("website", "网站，互联网上的一组相关网页"),
            ("mention", "提到，说起，如 Don't mention it 别客气"),
            ("by accident", "偶然，意外地，不是故意做的"),
            ("by mistake", "错误地，无意中弄错了"),
            ("divide...into...", "把……分成……，如 divide the class into groups 把班级分成小组"),
            ("一般过去时的被动语态", "表示过去的某物被……，结构是 was/were + 过去分词"),
            ("It is said that...", "据说……，表示消息来源不是说话人自己"),
            ("be used for doing sth.", "被用来做某事，for 后面接动名词，说明物品的用途"),
        ], 20262106)),
    ]),
    ("第七单元 Teenagers should be allowed to choose their own clothes.", [
        ("第7课 Unit 7 Teenagers should be allowed to choose their own clothes.", "📣 成长需要理解与规则。想一想：你觉得中学生应该被允许自己安排周末吗？", L([
            ("license", "执照，证书，如 driver's license 驾驶执照"),
            ("safety", "安全，不受危险伤害的状态"),
            ("regret", "后悔，遗憾，对做过的事感到懊悔"),
            ("achieve", "达到，实现，通过努力获得目标"),
            ("support", "支持，赞同并帮助别人"),
            ("manage", "设法做到，完成困难的事情"),
            ("chance", "机会，做某事的可能性或时机"),
            ("get in the way of", "妨碍，挡……的路，影响某事进行"),
            ("be strict with sb.", "对某人要求严格"),
            ("should be allowed to do sth.", "应该被允许做某事，情态动词后面接 be allowed to 表示许可"),
            ("含情态动词的被动语态", "结构是情态动词+be+过去分词，如 must be finished 必须被完成"),
            ("keep...away from...", "使……远离……，不让靠近危险的东西"),
        ], 20262107)),
    ]),
    ("第八单元 It must belong to Carla.", [
        ("第8课 Unit 8 It must belong to Carla.", "📣 合理的推测离不开细心观察。想一想：发现一样不明物品时，你会怎样推理它的主人？", L([
            ("whose", "谁的，用来询问物品的归属"),
            ("truck", "卡车，运货用的大型车辆"),
            ("picnic", "野餐，如 have a picnic 去野餐"),
            ("attend", "出席，参加，如 attend a meeting 参加会议"),
            ("valuable", "贵重的，值钱的，很有价值"),
            ("noise", "噪音，喧闹声，指让人不舒服的声音"),
            ("sleepy", "困倦的，想睡觉的"),
            ("laboratory", "实验室，做科学实验的地方"),
            ("belong to", "属于，后面接名词或人称代词的宾格，如 belong to me"),
            ("must 表推测", "must be 表示很有把握的肯定推测，意思是“一定是”"),
            ("might/could 表推测", "表示可能性较小的推测，意思是“可能是”，语气不如 must 肯定"),
            ("can't 表推测", "表示有把握的否定推测，意思是“不可能是”"),
        ], 20262108)),
    ]),
    ("第九单元 I like music that I can dance to.", [
        ("第9课 Unit 9 I like music that I can dance to.", "📣 音乐和电影点亮课余生活。想一想：介绍一部你喜欢的电影，说说它好在哪里。", L([
            ("prefer", "更喜欢，宁愿选择，后接名词或动名词"),
            ("lyrics", "歌词，歌曲里唱的文字"),
            ("electronic", "电子的，用电子元件工作的，如 electronic music 电子音乐"),
            ("suppose", "推断，料想，如 I suppose 我认为大概如此"),
            ("smooth", "悦耳的；光滑的，平滑不粗糙"),
            ("spare", "空闲的，如 spare time 空余时间"),
            ("documentary", "纪录片，真实记录人物或事件的影片"),
            ("director", "导演，指挥拍摄电影或戏剧的人"),
            ("case", "情况，实例，如 in that case 在那种情况下"),
            ("war", "战争，国家或集团之间的大规模武装冲突"),
            ("定语从句", "在复合句中修饰名词或代词的从句，被修饰的词叫先行词"),
            ("that/who 引导的定语从句", "先行词指物时常用 that，指人时常用 who，在从句中作主语或宾语"),
            ("prefer A to B", "比起 B 更喜欢 A，A 和 B 要用同类词，如 prefer singing to dancing"),
        ], 20262109)),
    ]),
    ("第十单元 You're supposed to shake hands.", [
        ("第10课 Unit 10 You're supposed to shake hands.", "📣 入乡随俗是基本的礼貌。想一想：中外见面的礼节有哪些不同？", L([
            ("custom", "习俗，风俗，一个地方长期形成的习惯"),
            ("bow", "鞠躬，弯腰行礼表示敬意"),
            ("kiss", "亲吻，用嘴唇接触表示亲热或礼节"),
            ("greet", "问候，打招呼，迎接别人"),
            ("relaxed", "放松的，不紧张的，感到轻松自在"),
            ("value", "重视，珍视，认为很有价值"),
            ("drop by", "顺便拜访，不事先约好就去看望"),
            ("after all", "毕竟，终究，用来引出有说服力的理由"),
            ("shake hands with sb.", "与某人握手，常见的见面礼节"),
            ("be supposed to do sth.", "应该做某事，表示按照习俗或规则理应如此，如 You are supposed to shake hands"),
            ("be expected to do sth.", "被期望做某事，别人希望你去做，语气比 should 委婉"),
            ("make...feel at home", "使某人感到宾至如归，让客人舒服自在"),
        ], 20262110)),
    ]),
]

if __name__ == "__main__":
    run(r"content/middle/pep/grade3/volume1/english", "英语上册", UNITS)
