# -*- coding: utf-8 -*-
"""英语高考复习专题训练题库生成脚本（flat 平铺布局，专题名直接入文件名）。"""
import os
import sys
from pathlib import Path


def _find_project_root(start):
    p = start
    for _ in range(6):
        if (p / "content").is_dir():
            return p
        p = p.parent
    raise SystemExit("找不到项目根目录（content/）")


def _find_engine_dir(root):
    for cand in (Path(__file__).resolve().parent,
                 root / ".workbuddy" / "skills" / "interactive-quiz-html" / "scripts"):
        if (cand / "build_quiz_html.py").exists():
            return cand
    raise SystemExit("找不到引擎 build_quiz_html.py")


PROJECT_ROOT = _find_project_root(Path(__file__).resolve().parent)
sys.path.insert(0, str(_find_engine_dir(PROJECT_ROOT)))
from build_quiz_html import build as engine_build  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _quizlib import S, S2, M, run  # noqa: E402
from _concepts import concept_lessons  # noqa: E402


def L(entries, seed):
    return concept_lessons(entries, seed=seed)


UNITS = [
    ("专题1 核心词汇", [
        ("专项自测", "📣 高分阅读从核心词汇开始。想一想：一个单词在语境里还能有几个意思？", L([
            ("acquire", "获得，取得，如 acquire knowledge 获取知识"),
            ("potential", "潜力，潜能；潜在的，如 realize one's potential 发挥潜能"),
            ("adequate", "足够的，充分的，数量或质量上满足需要的"),
            ("genuine", "真正的，真诚的，非伪造或假装的"),
            ("significant", "重要的，意义重大的；数量上显著的"),
            ("abundant", "丰富的，充裕的，数量多得足够的"),
            ("essential", "必不可少的，极其重要的；本质的"),
            ("evaluate", "评价，评估，仔细判断事物的价值或效果"),
            ("maintain", "维持，保持；保养；坚持认为"),
            ("demonstrate", "证明，证实；示范，演示"),
            ("contribute", "贡献，捐献；投稿，如 contribute to 有助于，促成"),
            ("fundamental", "基本的，根本的，构成基础的"),
        ], 20263511)),
    ]),
    ("专题2 核心短语与搭配", [
        ("专项自测", "📣 短语搭配是句子的黏合剂。想一想：同一个动词配上不同介词意思差多少？", L([
            ("take on", "承担（工作、责任）；呈现，呈现出（样子、特征）"),
            ("come up with", "想出，提出（主意、计划、办法等）"),
            ("be committed to", "致力于，承诺做某事，to 为介词后接名词或 -ing 形式"),
            ("account for", "解释，说明（原因）；占（比例）"),
            ("in terms of", "就……而言，在……方面"),
            ("turn out", "结果是，证明是；后来发生，如 It turned out that..."),
            ("result in", "导致，引起，造成某种结果"),
            ("cope with", "应对，处理（困难的事情或局面）"),
            ("on behalf of", "代表……，为了……的利益"),
            ("make up for", "弥补，补偿（失去的东西或过错）"),
            ("be accustomed to", "习惯于，to 为介词后接名词或 -ing 形式"),
            ("put up with", "忍受，容忍（不愉快的事情）"),
        ], 20263512)),
    ]),
    ("专题3 动词时态与语态", [
        ("专项自测", "📣 时态是英语的时间轴。想一想：一句话的动作发生在哪个时间点上？", L([
            ("一般现在时", "表示经常性习惯性动作或客观事实，主语三单时动词加 s，常与 often、every day 连用"),
            ("一般过去时", "表示过去发生的动作或状态，动词用过去式，常与 yesterday、ago 连用"),
            ("现在进行时", "am/is/are doing 表示此刻或现阶段正在进行的动作"),
            ("过去进行时", "was/were doing 表示过去某时正在进行的动作"),
            ("一般将来时", "will do 或 be going to do 表示将来发生的动作或打算"),
            ("过去将来时", "would do 表示从过去看将要发生的动作，常用于宾语从句"),
            ("现在完成时", "have/has done 表示动作已完成并对现在有影响，常与 already、yet、since 连用"),
            ("过去完成时", "had done 表示过去某时之前已完成的动作，即过去的过去"),
            ("现在完成进行时", "have/has been doing 表示动作从过去持续到现在且可能继续"),
            ("将来完成时", "will have done 表示将来某时之前将已完成的动作，常与 by + 将来时间连用"),
            ("被动语态", "be + 过去分词表示主语是动作的承受者，时态变化体现在 be 上"),
            ("被动语态的完成式", "have/has been done 表示动作已完成且主语是承受者，如 The work has been done"),
        ], 20263513)),
    ]),
    ("专题4 从句与句式结构", [
        ("专项自测", "📣 从句让句子表达更丰富。想一想：这个从句在句中充当什么成分？", L([
            ("限制性定语从句", "紧跟先行词、对先行词起限定作用的定语从句，去掉后句意不完整"),
            ("非限制性定语从句", "用逗号与主句隔开、起补充说明作用的定语从句，不能用 that 引导"),
            ("关系副词", "when、where、why 分别引导表时间、地点、原因的定语从句"),
            ("宾语从句", "从句在句中作宾语，用陈述语序，如 I wonder what he wants"),
            ("whether 与 if 的区别", "两者都可引导宾语从句，但介词后、不定式前和句首只能用 whether"),
            ("状语从句", "在句中作状语的从句，表示时间、条件、原因、让步等"),
            ("时间状语从句", "由 when、while、as soon as 等引导，主将从现，如 When he comes, I will call you"),
            ("让步状语从句", "由 although、though、even if 等引导表示让步，不能与 but 连用"),
            ("条件状语从句", "由 if、unless 等引导，主句用将来时从句用一般现在时"),
            ("倒装句", "谓语或助动词放在主语前面的语序，如 Never have I seen such a beautiful place"),
            ("部分倒装", "只把助动词提到主语前的倒装，用于否定词开头、only 开头等场合"),
            ("强调句", "It is/was + 被强调部分 + that/who 的句型，去掉后句子仍完整"),
        ], 20263514)),
    ]),
    ("专题5 完形填空与阅读高频词", [
        ("专项自测", "📣 完形阅读靠语感和词汇双重发力。想一想：熟词生义你踩过几次坑？", L([
            ("however", "然而，可是，表转折关系的逻辑连接词，后面常加逗号"),
            ("therefore", "因此，所以，表因果关系的逻辑连接词"),
            ("in addition", "此外，另外，表递进补充的逻辑连接词"),
            ("on the contrary", "相反，与此相反，用于引出与上文相反的情况"),
            ("熟词生义", "常见单词在特定语境中的生僻含义，如 address 表示处理问题"),
            ("address", "除地址、演说外，作动词还可表示处理、对付（问题）"),
            ("novel", "除小说外，作形容词表示新颖的、新奇的"),
            ("sound", "除声音外，作形容词表示健全的、完好的、合理的"),
            ("appreciate", "除感激、欣赏外，还可表示意识到、充分理解"),
            ("observe", "除观察外，还可表示遵守（规则、法律）"),
            ("figure out", "弄清楚，想明白，通过思考理解或算出"),
            ("turn to", "转向，求助于，如 turn to sb for help 向某人求助"),
        ], 20263515)),
    ]),
    ("专题6 应用文写作句型", [
        ("专项自测", "📣 应用文写作贵在格式与得体。想一想：这封信的语气适合写给谁？", L([
            ("I am writing to invite you to...", "邀请信开头句型，我写信是想邀请你……，直接点明写信目的"),
            ("We would feel honored if...", "邀请信表达诚意的句型，如果……我们将深感荣幸，用虚拟语气"),
            ("You'd better...", "建议信句型，你最好……，语气直接，用于熟悉的人"),
            ("It would be beneficial to...", "建议信句型，做……是有益的，语气委婉礼貌"),
            ("Why not...", "建议信句型，为什么不……呢，后接动词原形，语气亲切"),
            ("I suggest that you (should)...", "建议信句型，我建议你……，从句用虚拟语气 should + 动词原形"),
            ("I sincerely apologize for...", "道歉信句型，我真诚地为……道歉，for 后接名词或 -ing 形式"),
            ("Please accept my sincere apology", "道歉信结尾句型，请接受我诚挚的歉意"),
            ("I am terribly sorry that...", "道歉信开头句型，我非常抱歉……，terribly 加强歉意语气"),
            ("Thank you for your invitation", "回复邀请信的致谢句型，感谢你的邀请"),
            ("I look forward to your reply", "各类书信通用结尾句型，期待你的回复，to 为介词后接名词或 -ing 形式"),
            ("Thank you for your consideration", "书信结尾礼貌用语，感谢您的考虑，常用于申请信、建议信"),
        ], 20263516)),
    ]),
]

ARCHIVE_REL = r"content/high/review/grade3/volume1/english"


def _rename_topics(subject, units):
    """flat 布局生成的「subject · 专题N xxx · 专项自测.html」改为「NN-专题名.html」。"""
    import re
    archive = PROJECT_ROOT / ARCHIVE_REL
    for (unit, lessons) in units:
        m = re.match(r"专题(\d+)\s+(.*)", unit)
        dst = archive / ("%02d-%s.html" % (int(m.group(1)), m.group(2).strip()))
        for (lesson, _, _) in lessons:
            src = archive / ("%s · %s · %s.html" % (subject, unit, lesson))
            os.replace(src, dst)
            print("重命名 %s -> %s" % (src.name, dst.name))


if __name__ == "__main__":
    run(ARCHIVE_REL, "英语高考复习", UNITS, layout="flat")
    _rename_topics("英语高考复习", UNITS)
