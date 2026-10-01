# -*- coding: utf-8 -*-
"""交互版自测 HTML 批量生成器（通用引擎）

把「按单元/课组织的题库」批量生成为可交互的自测网页，学生可用电脑/平板点选作答、自动判分。
内置一份「人教版四年级上册科学」19 课题库作为示例。

特性：
  - 点选作答（单选互斥、多选可多选）
  - 自动判分（每题 10 分，满分 100），错项红✘ / 正确项绿✔ + 答案解析
  - 明暗模式切换（默认跟随系统，按钮可切明亮/暗黑，localStorage 记忆）
  - 每课从题库每轮最多抽取 min(10, 题库) 题
  - 「重做一遍」（同一批）/「继续测试」（优先出从未做过的题，整库刷完才重洗，不重复）
  - 分数按本批实际题数动态计算（每题 10 分，满分随本批题数）
  - 固定学生姓名、自动填写当天日期、「今日广播小提示」

用法（在 StudyBuddy 项目里请走模板，不要直接改本文件）：
  python build_quiz_html.py     # 自测引擎用：把内置四年级科学示例题库渲染到技能目录下的 out/
可配置（环境变量）：
  QUIZ_ARCHIVE   输出目录（缺省：本技能目录下的 out/，不会写进 content/）
  QUIZ_STUDENT   学生姓名（缺省：郭奕凡）
正式加题库：复制 template_subject.py → 改 ARCHIVE_REL / SUBJECT / UNITS → 运行 → 重启服务。
"""
import os
import random
import re

# 直接运行本文件只是「自测引擎」：产物落到技能目录下的 out/，刻意不指向 content/，
# 免得内置的示例题库被当成正式课程混进刷题系统。正式题库请用 template_subject.py。
_SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
ARCHIVE = os.environ.get("QUIZ_ARCHIVE", os.path.join(os.path.dirname(_SKILL_DIR), "out"))
STUDENT_NAME = os.environ.get("QUIZ_STUDENT", "郭奕凡")

# ====================== 题库数据 ======================
# 每课: (课名, 广播小提示, [(题型 s/m, 题干, [选项], [答案字母]), ...])

UNITS = [
("第一单元 动植物的繁殖", [
  ("第1课 植物的种子",
   "📣 今日广播：种子虽小本领大！种皮保护、胚是‘植物宝宝’、子叶当‘粮仓’，回家看看豆子也能发芽。",
   [
    ("s","菜豆种子最外面一层起保护作用的结构是（　）。",["种皮","果肉","果皮","绿叶"],["A"]),
    ("s","种子里最重要的部分，将来能发育成一株新的植物的是（　）。",["种皮","胚","子叶","土壤"],["B"]),
    ("s","观察种子的内部结构前，一般先把种子泡在水里一段时间，主要目的是（　）。",["让种皮变软，容易剥开","让种子变得更大","给种子消毒","把种子洗干净"],["A"]),
    ("s","菜豆种子里储存营养物质、供胚生长发育的结构是（　）。",["胚芽","胚根","子叶","种皮"],["C"]),
    ("s","农民伯伯一般把大豆种在春天的土壤里，是因为（　）。",["春天的风比较大","春天温度适宜、雨水较多，适合种子萌发","春天学校放假","种子只有在阳光下才能看见"],["B"]),
    ("s","关于植物种子的样子，下列说法正确的是（　）。",["所有种子都一样大","种子的大小、形状和颜色多种多样","种子都是圆形的","种子都是绿色的"],["B"]),
    ("m","下面观察种子的做法中，正确的有（　）。",["先用水浸泡，让种皮变软","用放大镜观察种子的细微结构","轻轻剥开种皮，观察里面","用舌头尝一尝味道"],["A","B","C"]),
    ("m","下列关于种子用途的说法，正确的有（　）。",["许多种子可以做食物，比如豆类","种子可以用来繁殖植物","有些种子可以榨油，比如花生","所有种子都可以当糖果随便吃"],["A","B","C"]),
    ("m","种子萌发需要的条件有（　）。",["水分","空气","适宜的温度","放进冰箱冷冻"],["A","B","C"]),
    ("m","菜豆种子的结构包括（　）。",["种皮","胚根","子叶","果皮"],["A","B","C"]),
    ("s","种子萌发时，最先突破种皮向下生长、将来变成根的部分是（　）。",["胚根","胚芽","子叶","种皮"],["A"]),
    ("s","种子中将来发育成茎和叶的部分是（　）。",["胚芽","胚根","子叶","种皮"],["A"]),
    ("s","我们吃黄豆芽时，看到的白色‘豆瓣’其实是黄豆种子的（　）。",["子叶","胚根","种皮","果皮"],["A"]),
    ("s","把浸泡后的蚕豆种子剥开、用放大镜观察，里面白色的小芽是（　）。",["胚","果实","叶子","根"],["A"]),
    ("s","播种前挑选饱满、完整的种子，主要是因为（　）。",["饱满的种子储存营养多，更容易发芽","饱满的种子更好看","饱满的种子更便宜","饱满的种子更轻"],["A"]),
    ("s","关于种子萌发，下列说法正确的是（　）。",["种子萌发时通常先长出根","种子萌发时先长出叶子","种子不需要喝水就能发芽","种子放在冰箱里长得更快"],["A"]),
    ("m","菜豆种子的胚由哪些部分组成？（　）",["胚芽","胚根","子叶","果皮"],["A","B","C"]),
    ("m","在实验室观察种子结构时，安全正确的做法有（　）。",["用放大镜仔细观察","绝不把种子放进嘴里尝","观察后认真洗手","把种子扔到同学身上玩"],["A","B","C"]),
    ("m","下面哪些植物是用种子来繁殖后代的？（　）",["大豆","玉米","马铃薯（用块茎繁殖）","蘑菇（靠孢子繁殖）"],["A","B"]),
    ("m","关于种子的说法，正确的有（　）。",["种子里藏着新植物的幼体——胚","种皮能保护种子","子叶能为胚提供营养","所有种子都能在石头上发芽"],["A","B","C"]),
    ("s","把种到土里的种子用黑布盖住、完全不见光，种子（　）。",["不能发芽","仍然能够萌发发芽","会变绿","会立刻死掉"],["B"]),
    ("s","菜豆种子有两片子叶，而玉米种子只有一片子叶，这说明（　）。",["不同植物的种子结构不完全相同","所有种子都一样","玉米没有胚","菜豆不能发芽"],["A"]),
    ("m","下面属于‘种子’而不是‘果实’的有（　）。",["蚕豆（豆荚里的豆粒）","花生仁","葡萄","桃子"],["A","B"]),
    ("m","安全观察种子时，可以用到的工具有（　）。",["放大镜","水（浸泡软化）","镊子（轻轻剥开）","用嘴巴尝味道"],["A","B","C"]),
    ("s","种子萌发时各部分的生长顺序一般是（　）。",["先长根，再长茎和叶","先长叶，再长根","根和叶同时长出来","只长根不长叶"],["A"]),
    ("m","关于种子的大小，下列说法正确的有（　）。",["不同植物的种子大小差别很大","芝麻的种子很小","蚕豆的种子比较大","所有种子都一般大"],["A","B","C"]),
    ("s","一粒健康的种子种到合适的环境中，将来可以长成（　）。",["一株新的植物","一朵花就结束","一片单独的叶子","一块石头"],["A"]),
    ("s","保存粮食种子时，一般应放在（　）。",["潮湿闷热的地方","干燥、通风的地方","火炉旁边烤着","长期泡在水里"],["B"]),
    ("m","下列生物中靠种子繁殖后代的有（　）。",["白菜","小麦","金鱼（动物）","向日葵"],["A","B","D"]),
    ("s","种子萌发时，最先需要吸收的条件是（　）。",["水分","阳光","肥料","音乐声音"],["A"]),
   ]),

  ("第2课 种子的传播",
   "📣 今日广播：蒲公英乘风去远方，苍耳挂毛衣去旅行，植物的种子各有妙招传播后代！",
   [
    ("s","蒲公英的种子轻、带绒毛，主要靠（　）传播。",["风力","水力","动物","自身弹射"],["A"]),
    ("s","苍耳果实表面有钩刺，容易挂在动物皮毛上，这是利用（　）传播。",["动物","风力","水力","阳光"],["A"]),
    ("s","莲蓬和椰子能漂在水面，靠（　）传播种子。",["水力","风力","动物","自身弹射"],["A"]),
    ("s","豌豆成熟后豆荚会炸裂，把种子弹出去，这是（　）传播。",["自身弹射","风力","水力","动物"],["A"]),
    ("s","下面靠风力传播种子的是（　）。",["蒲公英","苍耳","椰子","豌豆"],["A"]),
    ("s","番茄、野葡萄的果实鲜美，被鸟兽吃掉后种子随粪便排出，这是（　）传播。",["动物","风力","水力","自身弹射"],["A"]),
    ("m","下列靠动物传播种子或果实的有（　）。",["苍耳","鬼针草","番茄","蒲公英"],["A","B","C"]),
    ("m","下列靠风力传播的有（　）。",["蒲公英","柳树的种子（柳絮）","槭树（翅果）","椰子"],["A","B","C"]),
    ("m","下列靠水力传播的有（　）。",["莲蓬","椰子","蒲公英","苍耳"],["A","B"]),
    ("m","下列属于种子“自身弹射”传播的有（　）。",["凤仙花","豌豆","油菜","蒲公英"],["A","B","C"]),
    ("s","种子传播的意义主要是（　）。",["让植物在更大范围生长，繁衍后代","让种子更好看","让动物有食物","让风更大"],["A"]),
    ("s","槭树（枫树）的种子长有“翅膀”（翅果），有利于（　）。",["随风飘远","沉入水底","被动物吃掉","弹射"],["A"]),
    ("m","关于种子传播，下列说法正确的有（　）。",["不同植物传播方式不同","风力传播的多轻小带毛或翅","水力传播的多能浮水","所有种子都靠风"],["A","B","C"]),
    ("s","下列靠自身弹射传播、果实会炸裂的是（　）。",["凤仙花","蒲公英","莲蓬","苍耳"],["A"]),
   ]),

  ("第3课 植物的繁殖",
   "📣 今日广播：花开→传粉→结果，植物靠种子和扦插嫁接繁衍，大自然真奇妙！",
   [
    ("s","植物繁殖后代主要依靠（　）。",["花、果实和种子","根和茎","叶子","土壤"],["A"]),
    ("s","花谢后，子房会慢慢发育成（　）。",["果实","叶子","根","种子外的毛"],["A"]),
    ("s","依靠昆虫（如蜜蜂）帮忙传粉的植物，花通常（　）。",["鲜艳、有香味和花蜜","很小、无味","全是绿色","只在晚上开"],["A"]),
    ("s","玉米、水稻等靠（　）传粉。",["风","昆虫","水流","人工"],["A"]),
    ("s","把一段月季枝条插进土里长成新植株，这种繁殖方式叫（　）。",["扦插","嫁接","压条","播种"],["A"]),
    ("s","把一种植物的枝条接到另一种植物上，叫（　）。",["嫁接","扦插","播种","压条"],["A"]),
    ("s","红薯、马铃薯等用茎或块根繁殖，属于（　）。",["营养繁殖（不用种子）","种子繁殖","孢子繁殖","嫁接"],["A"]),
    ("s","农民给果树进行人工辅助授粉，主要为了（　）。",["提高结果率","让花更香","减少叶子","改变颜色"],["A"]),
    ("m","下列用“种子”繁殖的植物有（　）。",["大豆","向日葵","苹果（种子）","马铃薯（块茎）"],["A","B","C"]),
    ("m","下列用“营养繁殖”（不用种子）的方式有（　）。",["扦插月季","嫁接果树","马铃薯用块茎","水稻播种"],["A","B","C"]),
    ("m","关于传粉，下列说法正确的有（　）。",["花分雄蕊和雌蕊","昆虫和风都能传粉","传粉后才能结出果实种子","所有花都靠水传粉"],["A","B","C"]),
    ("s","桃花里有雄蕊和雌蕊，其中（　）将来发育成果实。",["雌蕊的子房","雄蕊","花瓣","花柄"],["A"]),
    ("m","关于植物的繁殖，正确的有（　）。",["开花结果用种子繁殖","扦插嫁接属于营养繁殖","传粉是结果的前提","植物只能靠种子繁殖"],["A","B","C"]),
   ]),

  ("第4课 动物的繁殖",
   "📣 今日广播：鸡鸭卵生、猫狗胎生，卵里有卵黄卵白养胚胎，生命各有办法延续。",
   [
    ("s","鸡、鸭、鹅繁殖后代的方式是（　）。",["卵生","胎生","分裂","出芽"],["A"]),
    ("s","猫、狗、牛、羊繁殖后代的方式是（　）。",["胎生","卵生","孢子","出芽"],["A"]),
    ("s","下列动物中，由妈妈直接生下来、吃妈妈奶长大的是（　）。",["猫","鸡","青蛙","乌龟"],["A"]),
    ("s","鸡蛋里能为胚胎发育提供营养的主要是（　）。",["卵黄和卵白","蛋壳","气室","卵壳膜"],["A"]),
    ("s","鸡蛋孵化成小鸡，主要需要的外部条件是（　）。",["适宜的温度","强光","大量水","风吹"],["A"]),
    ("s","青蛙的繁殖方式是（　）。",["卵生","胎生","哺乳","分裂"],["A"]),
    ("s","鸟的蛋外面有坚硬的（　）保护。",["卵壳","羽毛","皮肤","鳞片"],["A"]),
    ("m","下列动物中属于卵生的有（　）。",["鸡","青蛙","乌龟","猫"],["A","B","C"]),
    ("m","下列动物中属于胎生、哺乳的有（　）。",["牛","羊","鲸","鸡"],["A","B","C"]),
    ("m","关于鸡蛋的结构，下列说法正确的有（　）。",["卵壳保护","卵白提供水分和营养","卵黄提供主要营养","气室储存空气供呼吸"],["A","B","C","D"]),
    ("s","哺乳动物最主要的特征是（　）。",["胎生、用乳汁哺育幼崽","卵生","用鳃呼吸","会飞"],["A"]),
    ("m","关于动物繁殖，下列说法正确的有（　）。",["许多动物用卵繁殖","哺乳动物胎生哺乳","鸟的卵有硬壳保护","所有动物都胎生"],["A","B","C"]),
    ("s","青蛙的幼体是蝌蚪，生活在水中用鳃呼吸，成体可上陆地，它属于（　）。",["两栖动物","鱼类","爬行动物","哺乳动物"],["A"]),
   ]),
]),

("第二单元 多样的动物", [
  ("第5课 昆虫",
   "📣 今日广播：昆虫身体分头胸腹、有三对足，蚂蚁蜜蜂蝴蝶都是它，蜘蛛不是哦！",
   [
    ("s","昆虫的身体一般分为（　）三部分。",["头、胸、腹","头、身、尾","上、中、下","根、茎、叶"],["A"]),
    ("s","昆虫通常有几对足？（　）",["3对（6只）","2对","4对","1对"],["A"]),
    ("s","下列动物中，属于昆虫的是（　）。",["蚂蚁","蜘蛛","蚯蚓","蜗牛"],["A"]),
    ("s","下列动物中，不属于昆虫的是（　）。",["蜘蛛（8条腿）","蜜蜂","蝴蝶","蜻蜓"],["A"]),
    ("s","昆虫头上有一对（　）用来感觉和寻找食物。",["触角","翅膀","尾巴","鳞片"],["A"]),
    ("s","蜜蜂、蝴蝶身体上有（　），能飞行。",["翅膀","鱼鳍","鳞片","蹄子"],["A"]),
    ("s","蝗虫、蜻蜓、苍蝇都属于（　）。",["昆虫","鱼类","鸟类","哺乳动物"],["A"]),
    ("s","蚯蚓没有足、身体分节，它（　）昆虫。",["不是","是","可能是","一定是"],["A"]),
    ("m","下列属于昆虫的有（　）。",["蚂蚁","蚊子","蜜蜂","蜘蛛"],["A","B","C"]),
    ("m","下列身体分头胸腹、有3对足的动物有（　）。",["蝴蝶","蜻蜓","蝗虫","螃蟹"],["A","B","C"]),
    ("m","下列关于昆虫的说法，正确的有（　）。",["大多有1对触角","一般3对足","身体分头胸腹","蜘蛛也是昆虫"],["A","B","C"]),
    ("s","瓢虫能吃掉蚜虫，对人类（　）。",["有益","有害","没用","是害虫"],["A"]),
    ("s","昆虫一般都有（　）对足，这是区分它和蜘蛛（8足）的关键。",["3","4","2","8"],["A"]),
   ]),

  ("第6课 鸟和哺乳动物",
   "📣 今日广播：鸟儿披羽毛卵生，蝙蝠和鲸却是哺乳动物——会飞不等于鸟！",
   [
    ("s","鸟类身体表面覆盖（　），前肢变成翼。",["羽毛","鳞片","皮毛","甲"],["A"]),
    ("s","鸟类繁殖后代的方式是（　）。",["卵生","胎生","分裂","出芽"],["A"]),
    ("s","下列动物中，属于鸟类的是（　）。",["鸽子","蝙蝠","蝴蝶","鲸"],["A"]),
    ("s","蝙蝠会飞，但它属于（　）。",["哺乳动物","鸟类","昆虫","鱼类"],["A"]),
    ("s","哺乳动物繁殖和哺育的方式是（　）。",["胎生、哺乳","卵生","孵蛋","产卵"],["A"]),
    ("s","下列动物中，属于哺乳动物的是（　）。",["鲸","鲨鱼","乌龟","鳄鱼"],["A"]),
    ("s","鸟用（　）啄食，一般没有牙齿。",["喙","牙齿","舌头","爪子"],["A"]),
    ("s","哺乳动物一般体表（　）。",["被毛","有羽毛","有鳞片","光滑无覆盖"],["A"]),
    ("m","下列动物中属于鸟类的有（　）。",["麻雀","鸡","鸭子","蝙蝠"],["A","B","C"]),
    ("m","下列动物中属于哺乳动物的有（　）。",["狗","猫","大象","鸽子"],["A","B","C"]),
    ("m","下列关于鸟类的说法，正确的有（　）。",["体表有羽毛","卵生","有翼会飞","都用乳汁喂幼鸟"],["A","B","C"]),
    ("s","鸟和哺乳动物都用（　）呼吸。",["肺","鳃","皮肤","不用呼吸"],["A"]),
    ("s","下列动物中，既会飞又属于哺乳动物的是（　）。",["蝙蝠","鸽子","麻雀","蜻蜓"],["A"]),
   ]),

  ("第7课 动物的分类",
   "📣 今日广播：动物按有无脊椎分两大类，鱼鸟猫是脊椎动物，昆虫蚯蚓不是。",
   [
    ("s","根据体内有无脊椎骨，动物可分为（　）两大类。",["脊椎动物和无脊椎动物","大动物和小动物","飞的和不飞的","家养和野生"],["A"]),
    ("s","下列动物中，属于脊椎动物的是（　）。",["鱼","昆虫","蚯蚓","蜗牛"],["A"]),
    ("s","下列动物中，属于无脊椎动物的是（　）。",["蚂蚁","鱼","青蛙","蛇"],["A"]),
    ("s","鲫鱼、草鱼等生活在水中、用鳃呼吸的是（　）。",["鱼类","两栖类","鸟类","哺乳类"],["A"]),
    ("s","青蛙小时候是蝌蚪生活在水中、长大后可上陆地，属于（　）。",["两栖动物","鱼类","爬行动物","鸟类"],["A"]),
    ("s","蛇、乌龟、鳄鱼身体表面有鳞片或甲，用肺呼吸，属于（　）。",["爬行动物","鱼类","两栖动物","鸟类"],["A"]),
    ("m","下列动物中属于脊椎动物的有（　）。",["鱼","鸟","猫","蚂蚁"],["A","B","C"]),
    ("m","下列动物中属于无脊椎动物的有（　）。",["昆虫","蚯蚓","蜗牛","鱼"],["A","B","C"]),
    ("m","脊椎动物一般包括（　）。",["鱼类","两栖动物","爬行动物","鸟类、哺乳动物"],["A","B","C","D"]),
    ("s","给动物分类时，常用的依据是（　）。",["身体结构和特征","颜色好看与否","个头大小","会不会叫"],["A"]),
    ("m","关于动物分类，下列说法正确的有（　）。",["可以按有无脊椎分","可以按繁殖方式分","可以按生活环境分","分类没有依据随便分"],["A","B","C"]),
    ("s","鲸、蝙蝠虽然生活习性不同，但都靠（　）繁殖哺育，属于哺乳动物。",["胎生哺乳","卵生","产卵","分裂"],["A"]),
   ]),

  ("第8课 我国的珍稀动物",
   "📣 今日广播：大熊猫、朱鹮、扬子鳄是我国的珍宝，保护栖息地就是保护它们。",
   [
    ("s","我国特有的“国宝”动物，爱吃竹子的是（　）。",["大熊猫","金丝猴","朱鹮","藏羚羊"],["A"]),
    ("s","被称为“活化石”的我国珍稀爬行动物是（　）。",["扬子鳄","大熊猫","丹顶鹤","藏羚羊"],["A"]),
    ("s","朱鹮是一种珍稀的（　）。",["鸟","鱼","哺乳动物","昆虫"],["A"]),
    ("s","中华鲟是一种珍稀的（　）。",["鱼","鸟","爬行动物","哺乳动物"],["A"]),
    ("s","藏羚羊主要生活在（　）高原。",["青藏","东北","海南","长江"],["A"]),
    ("s","保护珍稀动物最有效的办法之一是建立（　）。",["自然保护区","动物园随便养","捕来卖了","不管它"],["A"]),
    ("s","我国通过（　）来保护珍稀动物不被非法捕猎。",["制定法律","鼓励捕猎","砍伐森林","填湖"],["A"]),
    ("m","下列我国的珍稀动物有（　）。",["大熊猫","金丝猴","朱鹮","扬子鳄"],["A","B","C","D"]),
    ("m","保护珍稀动物，我们可以做的是（　）。",["保护它们的栖息地","不购买野生动物制品","宣传保护知识","去抓来养"],["A","B","C"]),
    ("m","关于珍稀动物，下列说法正确的有（　）。",["数量很少、濒临灭绝","需要人类保护","我国有不少特有种","不需要管它们"],["A","B","C"]),
    ("s","金丝猴属于（　）动物。",["哺乳动物","鸟类","鱼类","爬行动物"],["A"]),
    ("s","为了保护珍稀动物，我们应该（　）。",["不伤害、不买卖、保护家园","去野外抓来养","买卖皮毛","破坏栖息地"],["A"]),
   ]),
]),

("第三单元 水的变化与分布", [
  ("第9课 蒸发与凝结",
   "📣 今日广播：湿衣变干是蒸发，玻璃水珠是凝结，水在空气中变戏法！",
   [
    ("s","水在平常温度下慢慢变成水蒸气散发到空气中，叫（　）。",["蒸发","沸腾","结冰","凝结"],["A"]),
    ("s","洗过的湿衣服晾干，是因为水（　）。",["蒸发成水蒸气","结冰","被太阳吃掉","凝结"],["A"]),
    ("s","下列做法中，能加快水蒸发的是（　）。",["把水放在阳光下、摊开","把水盖紧放阴凉处","把水冻成冰","把水倒进密封瓶"],["A"]),
    ("s","夏天扇扇子感到凉快，与（　）有关。",["加快蒸发带走热量","风是冷的","扇子有水","气温下降"],["A"]),
    ("s","冬天窗户玻璃上的小水珠，是空气中的水蒸气（　）形成的。",["遇冷凝结","蒸发","沸腾","结冰"],["A"]),
    ("s","清晨草叶上的露珠，是水蒸气（　）形成的。",["遇冷凝结","蒸发","沸腾","升华"],["A"]),
    ("s","蒸发是水从（　）变成（　）。",["液态到气态","气态到液态","固态到液态","液态到固态"],["A"]),
    ("s","凝结一般发生在水蒸气（　）的时候。",["遇冷","受热","被风吹","见光"],["A"]),
    ("m","下列属于蒸发现象的有（　）。",["湿头发被风吹干","地面上的积水变干","用酒精棉擦手后手变干","水烧开冒白气（这是凝结）"],["A","B","C"]),
    ("m","下列现象属于凝结的有（　）。",["冬天玻璃上的水珠","清晨的露珠","从冰箱拿出的饮料瓶外壁出水珠","水洼变干"],["A","B","C"]),
    ("m","生活中可以加快蒸发的办法有（　）。",["加热","通风","把液体摊开","把液体密封"],["A","B","C"]),
    ("s","水在（　）温度下都能蒸发，而沸腾需要达到特定温度。",["任何（平常）","只在100℃","只在0℃","只在阳光下"],["A"]),
   ]),

  ("第10课 水的沸腾",
   "📣 今日广播：水烧到约100℃会沸腾翻滚，沸腾时温度不再升高。",
   [
    ("s","水加热到一定温度（约100℃）时剧烈翻滚冒泡，这叫（　）。",["沸腾","蒸发","凝结","结冰"],["A"]),
    ("s","在标准情况下，水沸腾时的温度大约是（　）。",["100℃","0℃","50℃","37℃"],["A"]),
    ("s","水沸腾时，温度会（　）。",["保持不变","一直升高","一直降低","突然变0"],["A"]),
    ("s","水沸腾前，温度（　）。",["不断上升","不变","下降","随机"],["A"]),
    ("s","水沸腾时产生的大量“白气”其实是（　）。",["水蒸气遇冷凝结的小水滴","纯水蒸气","烟","二氧化碳"],["A"]),
    ("s","水沸腾变成水蒸气，是（　）现象。",["汽化","液化","凝固","熔化"],["A"]),
    ("s","加热水时，我们用（　）测量水温。",["温度计","尺子","天平","放大镜"],["A"]),
    ("m","下列关于沸腾的说法，正确的有（　）。",["沸腾需要加热到沸点","沸腾时剧烈冒泡","沸腾时温度保持不变","任何温度都能沸腾"],["A","B","C"]),
    ("m","水从液态变成气态的方式有（　）。",["蒸发","沸腾","凝结","结冰"],["A","B"]),
    ("s","水烧开后继续加热，水温（　）。",["保持在100℃左右","继续升高超过100℃","降到0℃","立即结冰"],["A"]),
    ("s","水沸腾时和沸腾前相比，相同点是（　）。",["都在汽化（变水蒸气）","温度都不变","都不冒泡","都结冰"],["A"]),
   ]),

  ("第11课 水的结冰",
   "📣 今日广播：0℃水结冰、冰受热融化，水有固液气三态来回变。",
   [
    ("s","液态的水在（　）时会结成冰。",["0℃或更低（受冷）","100℃","50℃","任何温度"],["A"]),
    ("s","水结成冰，是水从（　）变成（　）。",["液态到固态","气态到液态","液态到气态","固态到液态"],["A"]),
    ("s","冰在受热后会（　）成水。",["融化","凝固","蒸发","升华"],["A"]),
    ("s","冰融化时要（　）。",["吸收热量","放出热量","不吸热也不放热","结冰"],["A"]),
    ("s","冰是水的（　）形态。",["固态","液态","气态","等离子态"],["A"]),
    ("s","水在自然界常见的三种形态是（　）。",["固态、液态、气态","红、黄、蓝","固、液、电","冷、热、温"],["A"]),
    ("s","冬天湖面结冰，冰浮在水面上，说明冰比水（　）。",["轻（密度小）","重","一样重","更热"],["A"]),
    ("m","下列关于水和冰的说法，正确的有（　）。",["冰是固态的水","冰融化吸热","0℃时水可能结冰","冰比水重"],["A","B","C"]),
    ("m","水的三态变化包括（　）。",["蒸发/沸腾（液→气）","凝结（气→液）","凝固（液→固）","融化（固→液）"],["A","B","C","D"]),
    ("s","冰融化变成水，状态变化是（　）。",["固态到液态","液态到固态","液态到气态","气态到液态"],["A"]),
    ("s","水、冰、水蒸气是（　）的三种不同形态。",["同一种物质（水）","三种不同物质","空气","石头"],["A"]),
   ]),

  ("第12课 地球上的水资源",
   "📣 今日广播：地球大多水是咸的海水，淡水很少，请节约每一滴水！",
   [
    ("s","地球上水量最多的是（　）。",["海洋（咸水）","河流","湖泊","冰川"],["A"]),
    ("s","人类生活和生产主要使用的是（　）。",["淡水","海水","咸水","盐水"],["A"]),
    ("s","下列水中，不能直接饮用的是（　）。",["海水（咸）","干净的淡水","开水","矿泉水"],["A"]),
    ("s","缓解淡水短缺，我们可以（　）。",["节约用水、循环利用","随便浪费","污染河流","抽干地下水"],["A"]),
    ("s","自然界中，可以直接利用的淡水资源（　）。",["很少，要珍惜","取之不尽","比海水多","用不完"],["A"]),
    ("s","冰川和深层地下水属于（　），一般难以直接利用。",["淡水但难利用","咸水","污水","海水"],["A"]),
    ("m","下列属于淡水来源的有（　）。",["河流","湖泊","地下水","海洋"],["A","B","C"]),
    ("m","保护水资源，我们可以（　）。",["随手关水龙头","一水多用","不往河里倒垃圾","长流水洗东西"],["A","B","C"]),
    ("m","关于地球水资源，下列说法正确的有（　）。",["海洋水占绝大部分且是咸水","淡水比例小","可利用淡水更少","水资源取之不尽"],["A","B","C"]),
    ("s","为了保护和节约水，我们应该（　）。",["节约用水、保护水环境","多用水没关系","污染没关系","抽干湖泊"],["A"]),
    ("s","下列做法有利于保护水资源的是（　）。",["污水处理后排放","直接排工业废水","围湖造田","滥砍水源林"],["A"]),
   ]),
]),

("第四单元 声音", [
  ("第13课 声音的产生",
   "📣 今日广播：敲鼓弹弦喉咙颤，声音都是‘振动’变出来的！",
   [
    ("s","声音是由物体（　）产生的。",["振动","静止","发光","发热"],["A"]),
    ("s","拨动琴弦会发声，是因为琴弦在（　）。",["振动","发光","变长","变冷"],["A"]),
    ("s","用力敲鼓，鼓面在（　），从而发出声音。",["振动","静止","发光","膨胀"],["A"]),
    ("s","物体停止振动，声音会（　）。",["消失","变大","变小但不停","变高"],["A"]),
    ("s","说话时，我们用手摸喉咙能感到（　），说明声带在振动。",["振动","凉","硬","疼"],["A"]),
    ("s","下列现象说明声音由振动产生的是（　）。",["弹拨橡皮筋会动并发声","石头不动也响","关灯有声音","睡觉有声音"],["A"]),
    ("m","下列能说明“声音由振动产生”的有（　）。",["敲鼓鼓面振动","弹琴弦振动","喉咙发声时声带振动","敲击后物体不动也有声"],["A","B","C"]),
    ("m","关于声音的产生，下列说法正确的有（　）。",["物体在振动","振动停止声音消失","不同物体发声振动方式不同","不振动也能发声"],["A","B","C"]),
    ("s","用橡皮筋做实验，拉紧并拨动它，会看到它在（　）并发出“嗡嗡”声。",["振动","旋转","燃烧","溶解"],["A"]),
    ("s","停止弹拨琴弦后声音很快消失，说明（　）。",["振动停止声音就停止","声音会一直响","弦变长了","空气变少了"],["A"]),
    ("m","下列物体发声时都在振动的有（　）。",["被敲的鼓","被拨的橡皮筋","发声的锣","静止的桌子"],["A","B","C"]),
   ]),

  ("第14课 声音的传播",
   "📣 今日广播：声音要靠空气、水、木头传播，真空里可传不了声。",
   [
    ("s","声音不能在（　）中传播。",["真空","空气","水","木头"],["A"]),
    ("s","我们能听见别人说话，主要是因为声音通过（　）传到耳朵。",["空气","真空","太阳光","磁场"],["A"]),
    ("s","把耳朵贴在铁轨上能更早听到远处火车声，说明（　）传声较快。",["固体（铁轨）","真空","气体","光"],["A"]),
    ("s","钓鱼时说话大声会吓跑鱼，说明声音能在（　）中传播。",["水（液体）","真空","只有空气","火"],["A"]),
    ("s","耳朵中负责收集声音的是（　）。",["耳廓（外耳）","鼓膜","听小骨","耳蜗"],["A"]),
    ("s","声音引起（　）振动，再传到内耳产生听觉。",["鼓膜","头发","牙齿","舌头"],["A"]),
    ("m","声音可以在（　）中传播。",["固体","液体","气体","真空"],["A","B","C"]),
    ("m","关于声音传播，下列说法正确的有（　）。",["需要介质","真空不能传声","固体液体气体都能传","光也能传声"],["A","B","C"]),
    ("s","月球上（真空）宇航员面对面也听不见，必须用电台，因为（　）。",["真空不能传声","太远","月球安静","戴了头盔"],["A"]),
    ("s","游泳时在水中能听到岸上拍水声，说明声音能在（　）中传播。",["液体（水）","真空","只有空气","金属"],["A"]),
   ]),

  ("第15课 声音的变化",
   "📣 今日广播：弦紧细短声音高，用力敲声音响，声音有高低和大小。",
   [
    ("s","声音有高有低，叫（　）。",["音调","音量","响度","颜色"],["A"]),
    ("s","同样材质，琴弦越紧、越细、越短，发出的声音越（　）。",["高","低","大","小"],["A"]),
    ("s","敲鼓用力越大，鼓声越（　）。",["大（响）","小","高","低"],["A"]),
    ("s","声音的大小（强弱）叫（　）。",["音量（响度）","音调","音色","频率"],["A"]),
    ("s","用同样力敲大鼓和小鼓，大鼓声音更低沉，主要因为振动更（　）。",["慢（频率低）","快","轻","高"],["A"]),
    ("s","伸出钢尺越长，拨动时振动越慢，声音越（　）。",["低","高","大","小"],["A"]),
    ("m","下列关于声音变化的说法，正确的有（　）。",["物体振动快音调高","振动慢音调低","用力大声音响","细短紧的弦音调高"],["A","B","C","D"]),
    ("m","能使声音变大（响度大）的做法有（　）。",["用力敲","靠近声源","用扩音器","捂住耳朵"],["A","B","C"]),
    ("s","不同的人说话声音不同，我们常能分辨，主要因为（　）。",["音色不同","个子不同","衣服不同","年龄"],["A"]),
    ("s","琴弦越松、越长、越粗，发出的声音越（　）。",["低","高","大","小"],["A"]),
   ]),

  ("第16课 噪声与保护听力",
   "📣 今日广播：刺耳轰鸣是噪声，伤听力又扰眠，戴耳塞远离它。",
   [
    ("s","使人烦躁、影响健康的难听声音叫（　）。",["噪声","乐音","音调","回声"],["A"]),
    ("s","下列声音中，属于噪声的是（　）。",["刺耳的机器轰鸣","优美的音乐","鸟叫","流水声"],["A"]),
    ("s","长时间用很大音量听耳机，最容易伤害（　）。",["听力","视力","味觉","嗅觉"],["A"]),
    ("s","在嘈杂环境中保护听力，可以（　）。",["戴耳塞或远离声源","大声喊叫","凑近声源","不保护"],["A"]),
    ("s","为了减小噪声，下列做法合理的是（　）。",["给机器加消声罩","随意按喇叭","深夜施工不控制","大喊大叫"],["A"]),
    ("m","下列可能造成噪声的有（　）。",["汽车喇叭","工厂机器","施工电锯","轻音乐"],["A","B","C"]),
    ("m","噪声会危害人的（　）。",["听力","睡眠","身心健康","视力（间接）"],["A","B","C"]),
    ("m","保护听力我们可以（　）。",["不用大音量耳机","远离强噪声","戴护耳器","长时间大声煲电话"],["A","B","C"]),
    ("s","遇到燃放鞭炮等巨响时，最好（　）。",["张嘴或捂耳保护","凑近听","不理它","大声回喊"],["A"]),
    ("s","下列做法有利于保护听力的是（　）。",["不在嘈杂处久留","长时间最大音量听歌","用耳勺使劲掏耳","靠近喇叭"],["A"]),
   ]),
]),

("第五单元 制作简易乐器", [
  ("第17课 认识乐器",
   "📣 今日广播：鼓靠敲、琴靠弦、笛靠空气柱，乐器发声各有门道。",
   [
    ("s","鼓、锣、三角铁靠敲击振动发声，属于（　）乐器。",["打击","弦","管（吹）","电子"],["A"]),
    ("s","二胡、小提琴靠（　）振动发声。",["琴弦","鼓面","空气","屏幕"],["A"]),
    ("s","笛子、箫靠（　）振动发声。",["管内空气柱","琴弦","鼓皮","金属片"],["A"]),
    ("s","钢琴按下琴键，是里面的（　）被敲击振动发声。",["琴弦","空气","水","塑料"],["A"]),
    ("s","一般管子越长、空气柱越长，吹出的声音越（　）。",["低","高","大","小"],["A"]),
    ("s","下列靠空气柱振动发声的乐器是（　）。",["笛子","鼓","锣","木琴"],["A"]),
    ("m","下列属于弦乐器的有（　）。",["二胡","小提琴","古筝","笛子"],["A","B","C"]),
    ("m","下列属于打击乐器的有（　）。",["鼓","锣","三角铁","笛子"],["A","B","C"]),
    ("m","关于乐器发声，下列说法正确的有（　）。",["打击乐靠敲击振动","弦乐靠弦振动","管乐靠空气柱振动","所有乐器都靠电子"],["A","B","C"]),
    ("s","编钟、磬靠敲击金属或石头发声，属于（　）乐器。",["打击","弦","管","电子"],["A"]),
    ("s","吉他、古筝拨动后会发声，关键是（　）在振动。",["琴弦","琴身外壳","空气","琴头"],["A"]),
   ]),

  ("第18课 设计简易乐器",
   "📣 今日广播：水杯装水多少变音高，皮筋松紧也能调，动手设计乐器吧！",
   [
    ("s","用几个相同的杯子装不同高度的水，敲出不同声音，这是（　）。",["水杯琴","鼓","笛","锣"],["A"]),
    ("s","水杯里水越多，敲击时声音越（　）。",["低（振动慢）","高","大","小"],["A"]),
    ("s","用纸盒和橡皮筋做“吉他”，皮筋越紧声音越（　）。",["高","低","大","小"],["A"]),
    ("s","设计简易乐器时，首先要考虑（　）。",["用什么材料、怎么让它发声","涂什么颜色","叫什么名字","卖给谁"],["A"]),
    ("s","用吸管剪成长短不一做成排箫，短的吹出声音较（　）。",["高","低","大","小"],["A"]),
    ("m","下列能改变自制乐器音高的方法有（　）。",["改变水多少","改变皮筋松紧","改变管长短","只换颜色"],["A","B","C"]),
    ("m","设计制作简易乐器一般步骤包括（　）。",["确定方案","选择材料","制作调试","直接买"],["A","B","C"]),
    ("m","关于水杯琴，下列说法正确的有（　）。",["水不同音高不同","靠敲击杯体振动发声","是简易打击乐","水多少不影响声音"],["A","B","C"]),
    ("s","想让橡皮筋“吉他”声音更低，可以（　）。",["把皮筋调松或加长","调紧","剪短","涂胶水"],["A"]),
    ("s","自制排箫能吹出不同音高，是因为吸管（　）不同。",["长短","颜色","粗细相同","材料"],["A"]),
   ]),

  ("第19课 制作与展示",
   "📣 今日广播：画好图、做出声、敢改进、会展示，小小工程师就是你！",
   [
    ("s","制作简易乐器时，发现不响，应该先检查（　）。",["是否真的在振动发声","颜色好不好","名字好不好听","放在哪"],["A"]),
    ("s","展示作品时，应该（　）。",["介绍材料、做法和原理","什么都不说","只给看","藏起来"],["A"]),
    ("s","对自己做的乐器不满意，可以（　）。",["改进调试","扔掉重买","不管","不展示"],["A"]),
    ("s","小组合作做乐器，最重要的是（　）。",["分工合作、互相配合","各干各的","一人全做","吵架"],["A"]),
    ("m","评价一件自制乐器，可以看（　）。",["能否发声","音高是否能变化","是否牢固美观","只要贵就好"],["A","B","C"]),
    ("m","制作与展示过程中，我们应该（　）。",["动手实践","敢于改进","学会交流","怕失败不试"],["A","B","C"]),
    ("m","下列做法有利于做好简易乐器的是（　）。",["先画设计图","反复调试","听取建议改进","一次成型不调整"],["A","B","C"]),
    ("s","吸管排箫能吹出不同音高，是因为（　）。",["管子长短不同，空气柱振动快慢不同","颜色不同","粗细相同","材料不同"],["A"]),
    ("s","做完乐器后，发现某根吸管不响，合理的做法是（　）。",["检查是否通畅、调整吹奏","直接丢掉","不管它","换名字"],["A"]),
    ("m","展示交流时可以（　）。",["讲清楚做法","演示发声","回答同学提问","不说话"],["A","B","C"]),
    ("s","制作乐器前先画设计图，有助于（　）。",["明确做法、少走弯路","浪费时间","不用动手做","直接买成品"],["A"]),
   ]),
]),
]

# ====================== 交互引擎 ======================
def shuffle_options(questions):
    """把每题的选项位置打乱，并同步重排答案字母。

    题库数据里正确答案往往集中在 A（写题时习惯把正确项放第一个），
    直接生成的话孩子「全选 A」也能拿高分，失去练习意义。
    这里按题干哈希做**确定性**打乱：同一份题库每次生成结果完全一致，
    便于复查和重新生成，同时让正确答案均匀分布在 A/B/C/D。
    """
    import hashlib
    out = []
    for t, q, o, a in questions:
        seed = int(hashlib.md5(q.encode("utf-8")).hexdigest()[:8], 16)
        idx = list(range(len(o)))
        random.Random(seed).shuffle(idx)
        new_o = [o[i] for i in idx]                       # 打乱后的选项
        old2new = {old: new for new, old in enumerate(idx)}
        new_a = sorted("ABCD"[old2new["ABCD".index(x)]] for x in a)
        out.append((t, q, new_o, new_a))
    return out

def js_array(questions):
    questions = shuffle_options(questions)
    parts = []
    for t, q, o, a in questions:
        opts = ", ".join('"%s"' % x.replace('"', '\\"') for x in o)
        ans = ", ".join('"%s"' % x for x in a)
        parts.append(' {t:"%s",q:%s,o:[%s],a:[%s]}' % (
            t, '"%s"' % q.replace('"', '\\"').replace("\n", ""), opts, ans))
    return "[" + ",\n".join(parts) + "]"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>__GRADE____SUBJECT__ 自测 · __SUBTITLE__</title>
<style>
  :root{
    --bg:#eef2f7; --card:#ffffff; --ink:#1f2937; --muted:#5b6b7b;
    --brand:#1565c0; --brand-soft:#e6f0fb; --ok:#2e7d32; --ok-soft:#e9f6ea;
    --bad:#d32f2f; --bad-soft:#fdecec; --line:#e3e8ef; --warn:#e65100;
    --head1:#1565c0; --head2:#7b1fa2; --btn-sec:#78909c;
  }
  @media (prefers-color-scheme: dark){
    :root:not([data-theme="light"]){
      --bg:#0f1620; --card:#1a2533; --ink:#e6edf3; --muted:#9fb0c0;
      --brand:#4ea1ff; --brand-soft:#16273c; --ok:#5fbf6a; --ok-soft:#15301c;
      --bad:#ff6b6b; --bad-soft:#3a1a1a; --line:#2a3a4a; --warn:#ffa040;
      --head1:#1e3a5f; --head2:#3a1f5f; --btn-sec:#54677a;
    }
  }
  [data-theme="dark"]{
    --bg:#0f1620; --card:#1a2533; --ink:#e6edf3; --muted:#9fb0c0;
    --brand:#4ea1ff; --brand-soft:#16273c; --ok:#5fbf6a; --ok-soft:#15301c;
    --bad:#ff6b6b; --bad-soft:#3a1a1a; --line:#2a3a4a; --warn:#ffa040;
    --head1:#1e3a5f; --head2:#3a1f5f; --btn-sec:#54677a;
  }
  *{box-sizing:border-box;}
  body{margin:0;background:var(--bg);color:var(--ink);
    font-family:"Microsoft YaHei","PingFang SC","微软雅黑",sans-serif;line-height:1.6;
    transition:background .25s ease,color .25s ease;}
  .wrap{max-width:760px;margin:0 auto;padding:20px 16px 60px;}
  .head{background:linear-gradient(135deg,var(--head1),var(--head2));color:#fff;
    border-radius:16px;padding:18px 20px;box-shadow:0 6px 18px rgba(0,0,0,.12);}
  .topbar{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;}
  .head h1{margin:0;font-size:21px;color:#fff;letter-spacing:.5px;}
  .themebtn{background:rgba(255,255,255,.18);color:#fff;border:1px solid rgba(255,255,255,.4);
    border-radius:20px;padding:6px 14px;font-size:13px;cursor:pointer;white-space:nowrap;
    transition:.15s ease;}
  .themebtn:hover{background:rgba(255,255,255,.32);}
  .sub{color:rgba(255,255,255,.88);font-size:14px;margin:10px 0 14px;}
  .meta{display:flex;flex-wrap:wrap;gap:10px;font-size:14px;}
  .meta .box{background:rgba(255,255,255,.92);border-radius:8px;padding:6px 12px;color:#0d47a1;}
  .meta .box b{color:#1565c0;}
  .meta #score.done{background:#fff3e0;color:#e65100;}
  .bank{font-size:13px;color:#1f2937;background:rgba(255,255,255,.88);border-radius:8px;
    padding:8px 12px;margin-top:12px;}
  .tip{background:rgba(255,255,255,.92);border-left:4px solid #ffb300;border-radius:8px;
    padding:10px 14px;font-size:13px;color:#5d4037;margin-top:12px;}
  .q{background:var(--card);border:1px solid var(--line);border-radius:14px;
    padding:16px 18px;margin-top:16px;box-shadow:0 1px 6px rgba(0,0,0,.04);transition:.2s;}
  .q.correct{border-color:var(--ok);background:var(--ok-soft);}
  .q.wrong{border-color:var(--bad);background:var(--bad-soft);}
  .qtop{display:flex;align-items:center;gap:8px;margin-bottom:8px;}
  .badge{font-size:12px;font-weight:700;color:#fff;border-radius:6px;padding:2px 8px;}
  .badge.s{background:var(--brand);}
  .badge.m{background:var(--warn);}
  .qno{font-weight:700;}
  .qtop{display:flex;align-items:center;gap:8px;flex-wrap:wrap;}
  .qspk{margin-left:auto;}
  .spk{flex:0 0 auto;display:inline-flex;align-items:center;justify-content:center;
    width:28px;height:28px;border:none;background:var(--brand-soft);color:var(--brand);
    border-radius:50%;cursor:pointer;font-size:14px;line-height:1;transition:.15s;}
  .spk:hover{background:var(--brand);color:#fff;}
  .spk.playing{background:var(--brand);color:#fff;}
  .otext{margin-right:auto;}
  .stem{font-size:16px;margin-bottom:10px;}
  .opt{display:flex;align-items:center;gap:10px;border:1px solid var(--line);
    border-radius:10px;padding:10px 12px;margin:8px 0;cursor:pointer;
    font-size:15px;background:var(--card);transition:border-color .15s,background .15s,box-shadow .15s;user-select:none;}
  .opt:hover{border-color:var(--brand);background:var(--brand-soft);}
  .opt.sel{border-color:var(--brand);background:var(--brand-soft);font-weight:600;}
  .opt .tick{width:22px;height:22px;border:2px solid #90a4ae;border-radius:6px;
    flex:0 0 auto;display:flex;align-items:center;justify-content:center;font-size:15px;color:#fff;}
  .opt.sel .tick{background:var(--brand);border-color:var(--brand);}
  .opt.ok{border-color:var(--ok);background:var(--ok-soft);}
  .opt.ok .tick{background:var(--ok);border-color:var(--ok);}
  .opt.no{border-color:var(--bad);background:var(--bad-soft);}
  .opt.no .tick{background:var(--bad);border-color:var(--bad);}
  .answer{font-size:13px;color:#37474f;margin-top:8px;display:none;}
  .q.done .answer{display:block;}
  .btn{display:block;width:100%;margin:22px 0 0;padding:14px;border:none;border-radius:12px;
    background:var(--brand);color:#fff;font-size:17px;font-weight:700;cursor:pointer;transition:.15s;}
  .btn:hover{background:#0d47a1;}
  .btn.sec{background:#90a4ae;margin-top:10px;}
  .btn.sec:hover{background:#78909c;}
  .result{background:var(--card);border-radius:14px;padding:16px 20px;margin-top:18px;
    border:1px solid var(--line);display:none;text-align:center;}
  .result.show{display:block;}
  .result .big{font-size:40px;font-weight:800;color:var(--brand);}
  .bar{height:10px;border-radius:6px;background:#eeeeee;overflow:hidden;margin:10px 0;}
  .bar > i{display:block;height:100%;background:var(--ok);}
  .foot{color:#9e9e9e;font-size:12px;text-align:center;margin-top:24px;}
</style>
</head>
<body>
<div class="wrap">
  <div class="head">
    <div class="topbar">
      <h1>__GRADE____SUBJECT__ · 自测卷（人教版）</h1>
      <button class="themebtn" id="themeBtn" onclick="toggleTheme()" title="切换主题：跟随系统 / 明亮 / 暗黑">🔄 跟随系统</button>
    </div>
    <div class="sub">__SUBTITLE__</div>
    <div class="meta">
      <div class="box">姓名：<b>__NAME__</b></div>
      <div class="box">日期：<b id="date">—</b></div>
      <div class="box" id="score">得分：<b>待评定</b></div>
    </div>
    <div class="bank">📚 题库共 <b>__NBANK__</b> 题，每次最多抽取 <b>__PERROUND__</b> 题 · <span id="batch">第 1 批</span></div>
    <div class="tip" id="broadcast">__BROADCAST__</div>
  </div>

  <div id="quiz"></div>

  <button class="btn" id="submit" onclick="grade()">✅ 提交自测（自动判分）</button>
  <button class="btn sec" id="reset" onclick="resetAll()" style="display:none;">🔄 重做一遍（同一批）</button>
  <button class="btn sec" id="continue" onclick="continueTest()" style="display:none;">➡️ 继续测试（换一批新题）</button>

  <div class="result" id="result">
    <div>本次自测得分</div>
    <div class="big" id="scoreBig">0</div>
    <div class="bar"><i id="barFill" style="width:0%"></i></div>
    <div id="resultText"></div>
  </div>

  <div class="foot">人教版__GRADE____SUBJECT__ · 每题 10 分，满分 = 本批题数 × 10</div>
</div>

<script>
const ALL = __DATA__;
const PER_ROUND = __PERROUND__;
const quiz = document.getElementById("quiz");
let Q = [];
let seen = new Set();
let batch = 0;

const THEMES = ["auto", "light", "dark"];
const THEME_ICON = { auto: "🔄 跟随系统", light: "☀️ 明亮模式", dark: "🌙 暗黑模式" };
function applyTheme(t){
  if(t === "dark") document.documentElement.setAttribute("data-theme", "dark");
  else if(t === "light") document.documentElement.setAttribute("data-theme", "light");
  else document.documentElement.removeAttribute("data-theme");
}
function updateThemeBtn(){
  const t = localStorage.getItem("sci_theme") || "auto";
  const btn = document.getElementById("themeBtn");
  if(btn) btn.textContent = THEME_ICON[t];
}
function toggleTheme(){
  const cur = localStorage.getItem("sci_theme") || "auto";
  const next = THEMES[(THEMES.indexOf(cur) + 1) % 3];
  localStorage.setItem("sci_theme", next);
  applyTheme(next);
  updateThemeBtn();
}

function shuffle(a){
  for(let i=a.length-1;i>0;i--){
    const j=Math.floor(Math.random()*(i+1));
    [a[i],a[j]]=[a[j],a[i]];
  }
  return a;
}
function pickRound(){
  // 优先抽取从未做过的题；整库做完后才重新洗牌，保证“续测不重复刷完”
  let pool = ALL.map((_,i)=>i).filter(i=>!seen.has(i));
  if(pool.length === 0){ seen = new Set(); pool = ALL.map((_,i)=>i); }
  shuffle(pool);
  const n = Math.min(PER_ROUND, pool.length);
  const chosen = pool.slice(0, n);
  chosen.forEach(i=>seen.add(i));
  return chosen.map(i=>{ const o=Object.assign({},ALL[i]); o.pick=[]; return o; });
}
function speak(text, btn){
  if(!('speechSynthesis' in window)){
    alert('当前浏览器不支持朗读，请用 Chrome 或 Edge 打开。'); return;
  }
  try{ window.speechSynthesis.cancel(); }catch(e){}
  document.querySelectorAll('.spk.playing').forEach(function(b){b.classList.remove('playing');});
  const u=new SpeechSynthesisUtterance(String(text));
  u.lang='__LANG__'; u.rate=0.9; u.pitch=1;
  if(btn){
    btn.classList.add('playing');
    u.onend=function(){ btn.classList.remove('playing'); };
    u.onerror=function(){ btn.classList.remove('playing'); };
  }
  window.speechSynthesis.speak(u);
}
function render(){
  quiz.innerHTML="";
  Q.forEach((item,i)=>{
    const wrap=document.createElement("div");
    wrap.className="q"; wrap.id="q"+i;
    const qtop=document.createElement("div"); qtop.className="qtop";
    const badge=document.createElement("span");
    badge.className="badge "+(item.t==="s"?"s":"m");
    badge.textContent=item.t==="s"?"单选题":"多选题";
    const qno=document.createElement("span"); qno.className="qno"; qno.textContent="第 "+(i+1)+" 题";
    const qspk=document.createElement("button"); qspk.className="spk qspk"; qspk.type="button";
    qspk.title="读题（朗读题目与选项）"; qspk.textContent="🔊";
    const full=item.q+"。"+item.o.map((o,j)=>"ABCD"[j]+"："+o).join("，")+"。"
      +(item.t==="s"?"这是单选题，请选一个答案。":"这是多选题，可以选多个答案。");
    qspk.addEventListener("click",function(){ speak(full, qspk); });
    qtop.appendChild(badge); qtop.appendChild(qno); qtop.appendChild(qspk);
    const stem=document.createElement("div"); stem.className="stem"; stem.textContent=item.q;
    wrap.appendChild(qtop); wrap.appendChild(stem);
    item.o.forEach(function(o,j){
      const opt=document.createElement("div"); opt.className="opt"; opt.id="o"+i+"_"+j;
      opt.addEventListener("click",function(){ pick(i,j); });
      const tick=document.createElement("span"); tick.className="tick"; tick.id="tk"+i+"_"+j; tick.textContent="○";
      const otext=document.createElement("span"); otext.className="otext"; otext.textContent="ABCD"[j]+". "+o;
      const spk=document.createElement("button"); spk.className="spk"; spk.type="button";
      spk.title="读出来"; spk.textContent="🔊";
      spk.addEventListener("click",function(e){ e.stopPropagation(); speak(o, spk); });
      opt.appendChild(tick); opt.appendChild(otext); opt.appendChild(spk);
      wrap.appendChild(opt);
    });
    const ans=document.createElement("div"); ans.className="answer"; ans.id="ans"+i;
    wrap.appendChild(ans);
    quiz.appendChild(wrap);
  });
  document.getElementById("batch").textContent = "第 "+batch+" 批";
}
function newRound(){
  if(window.speechSynthesis){ try{ window.speechSynthesis.cancel(); }catch(e){} }
  batch++;
  Q = pickRound();
  render();
  const sc=document.getElementById("score");
  sc.innerHTML='得分：<b>待评定</b>'; sc.classList.remove("done");
  document.getElementById("result").classList.remove("show");
  document.getElementById("reset").style.display="none";
  document.getElementById("continue").style.display="none";
  const sb=document.getElementById("submit"); sb.textContent="✅ 提交自测（自动判分）"; sb.disabled=false;
  window.scrollTo({top:0,behavior:"smooth"});
}
function pick(i,j){
  const item=Q[i];
  const el=document.getElementById("o"+i+"_"+j);
  if(item.t==="s"){
    for(let k=0;k<item.o.length;k++){
      document.getElementById("o"+i+"_"+k).classList.remove("sel");
      document.getElementById("tk"+i+"_"+k).textContent="○";
    }
    el.classList.add("sel"); document.getElementById("tk"+i+"_"+j).textContent="✔";
    item.pick=["ABCD"[j]];
  }else{
    if(el.classList.contains("sel")){
      el.classList.remove("sel"); document.getElementById("tk"+i+"_"+j).textContent="○";
      item.pick=(item.pick||[]).filter(x=>x!=="ABCD"[j]);
    }else{
      el.classList.add("sel"); document.getElementById("tk"+i+"_"+j).textContent="✔";
      item.pick=item.pick||[]; if(!item.pick.includes("ABCD"[j])) item.pick.push("ABCD"[j]);
    }
  }
}
function grade(){
  let score=0; let answered=0;
  Q.forEach((item,i)=>{
    const sel=(item.pick||[]).slice().sort();
    const ans=item.a.slice().sort();
    const right = sel.length===ans.length && sel.every((v,k)=>v===ans[k]);
    const box=document.getElementById("q"+i);
    box.classList.add("done");
    if(sel.length>0) answered++;
    if(right){ score+=10; box.classList.add("correct"); }
    else{
      box.classList.add("wrong");
      item.a.forEach(L=>{const idx="ABCD".indexOf(L);document.getElementById("o"+i+"_"+idx).classList.add("ok");
        document.getElementById("tk"+i+"_"+idx).textContent="✔";});
      (item.pick||[]).forEach(L=>{if(!item.a.includes(L)){const idx="ABCD".indexOf(L);
        document.getElementById("o"+i+"_"+idx).classList.add("no");
        document.getElementById("tk"+i+"_"+idx).textContent="✘";}});
    }
    document.getElementById("ans"+i).innerHTML =
      "<b>正确答案："+item.a.join("、")+"</b>" + (right?" ✓ 你答对啦！":"（本题你未答对）");
  });
  const maxScore = Q.length * 10;
  const sc=document.getElementById("score");
  sc.innerHTML='得分：<b>'+score+'</b> / '+maxScore; sc.classList.add("done");
  document.getElementById("scoreBig").textContent=score;
  document.getElementById("barFill").style.width=(maxScore?score/maxScore*100:0)+"%";
  const msg = score>=80 ? "🎉 通过！可推进到下一节。"
            : score>=60 ? "⚠️ 部分掌握，建议再巩固一下。"
            : "❌ 未通过，需重新学习本节。";
  document.getElementById("resultText").innerHTML =
    (answered<Q.length?"（注意：有 "+(Q.length-answered)+" 题未作答）<br>":"")+msg;
  document.getElementById("result").classList.add("show");
  document.getElementById("reset").style.display="block";
  document.getElementById("continue").style.display="block";
  document.getElementById("submit").textContent="已提交 ✔";
  document.getElementById("submit").disabled=true;
  window.scrollTo({top:document.getElementById("result").offsetTop-20,behavior:"smooth"});
}
function resetAll(){
  if(window.speechSynthesis){ try{ window.speechSynthesis.cancel(); }catch(e){} }
  Q.forEach(it=>it.pick=[]);
  document.querySelectorAll(".opt").forEach(o=>{o.classList.remove("sel","ok","no");
    o.querySelector(".tick").textContent="○";});
  document.querySelectorAll(".q").forEach(q=>q.classList.remove("done","correct","wrong"));
  document.querySelectorAll(".answer").forEach(a=>a.innerHTML="");
  const sc=document.getElementById("score");sc.innerHTML='得分：<b>待评定</b>';sc.classList.remove("done");
  document.getElementById("result").classList.remove("show");
  document.getElementById("reset").style.display="none";
  document.getElementById("continue").style.display="none";
  const sb=document.getElementById("submit");sb.textContent="✅ 提交自测（自动判分）";sb.disabled=false;
  window.scrollTo({top:0,behavior:"smooth"});
}
function continueTest(){ newRound(); }
(function(){
  const d=new Date();
  const pad=n=>String(n).padStart(2,"0");
  document.getElementById("date").textContent=`${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`;
  applyTheme(localStorage.getItem("sci_theme") || "auto");
  updateThemeBtn();
  newRound();
})();
</script>
</body>
</html>
"""

import sys

_CN_NUM = ["零", "一", "二", "三", "四", "五", "六", "七", "八", "九"]


def grade_label(out_path, default="四年级"):
    """按输出路径推断年级，如 .../grade5/volume2/... → 五年级。

    只返回年级（册别由 subject 自带，如「语文上册」），避免「五年级上册语文上册」这类重复。
    路径里没有 gradeN 时退回 default（老式平铺目录保持原样）。
    """
    p = str(out_path).replace("\\", "/")
    m = re.search(r"/grade(\d+)/", p)
    if not m:
        return default
    n = int(m.group(1))
    # 学段不同叫法不同：初中 grade1/2/3 → 七/八/九年级；高中 → 高一/高二/高三
    if "/middle/" in p or "/middle-school/" in p:
        mid = {1: "七", 2: "八", 3: "九"}.get(n)
        if mid:
            return "%s年级" % mid
    if "/high/" in p or "/high-school/" in p:
        hi = {1: "高一", 2: "高二", 3: "高三"}.get(n)
        if hi:
            return hi
    name = _CN_NUM[n] if 0 <= n < len(_CN_NUM) else str(n)
    return "%s年级" % name


def build(subtitle, questions, broadcast, out_path, subject="科学上册", lang=None):
    if lang is None:
        lang = "en-US" if "英语" in subject else "zh-CN"
    per_round = min(10, len(questions))
    html = (HTML_TEMPLATE
            .replace("__SUBTITLE__", subtitle)
            .replace("__NAME__", STUDENT_NAME)
            .replace("__BROADCAST__", broadcast)
            .replace("__NBANK__", str(len(questions)))
            .replace("__PERROUND__", str(per_round))
            .replace("__SUBJECT__", subject)
            .replace("__LANG__", lang)
            .replace("__GRADE__", grade_label(out_path))
            .replace("__DATA__", js_array(questions)))
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return out_path

def main():
    DEFAULT_SUBJECT = "科学上册"
    os.makedirs(ARCHIVE, exist_ok=True)
    total = 0
    for unit, lessons in UNITS:
        for lesson, broadcast, qs in lessons:
            subtitle = unit + " · " + lesson
            out = os.path.join(ARCHIVE, "四年级" + DEFAULT_SUBJECT + " · " + subtitle + ".html")
            build(subtitle, qs, broadcast, out, DEFAULT_SUBJECT)
            total += 1
            print("生成 %2d | %s | %2d 题" % (total, subtitle, len(qs)))
    print("完成：共生成 %d 个 HTML 文件，目录：%s" % (total, ARCHIVE))

if __name__ == "__main__":
    main()
