# 自测页生成器

以后新增游戏自测页**只写题库**，不再手写 1000 多行的 HTML 壳。

## 为什么需要它

改造前：424 个旧自测页（grade1 208 + grade2 216）每个文件里都塞着一份
HTML 骨架 + 5.3 KB CSS + 8.9 KB 引擎 JS，合计 1000 多行 —— 而它们
其实只有 **2 种壳**（判断题 / 选择题），归一化换行后指纹完全一致。

逐行 diff 两种壳：CSS **0 行**差异、JS 17 行、HTML 11 行，差异全部
集中在「是否支持判断题（`t==="j"`）」这一个开关。所以**一份模板 +
一个 `HAS_JUDGE` 开关**就能覆盖全部题型。

## 两个文件

| 文件 | 作用 |
|---|---|
| `selftest_shell.py` | 壳模板（CSS + 引擎 JS + HTML 骨架）。**改这个等于改全部页面**，谨慎 |
| `selftest_gen.py` | 生成器：题库 DSL、路径推导、写盘、自检、CLI |

## 快速上手

### 方式一：写 Python（推荐）

```python
import sys
sys.path.insert(0, "tools/gamegen")
import selftest_gen as G

items = [
    G.q("「升国旗」里的「升」是什么意思？",
        ["往上举，往上升", "升高", "升级", "升空"], "A",
        "解析：「升国旗」就是把国旗往上举。"),
    G.judge("见到老师时，应该有礼貌地问好。", True,
          "解析：见到老师要主动问好，用敬语「您」。"),
    G.q("下面用「目」做的事有（　）。",      # 多选题
        ["跑步", "听音乐", "看书", "看黑板"], ["C", "D"],
        "解析：「目」与眼睛有关，看书、看黑板都要用眼睛。"),
]

G.build(grade=1, volume="volume1", subject="chinese",
        unit="02-识字（二）", filename="01-升国旗.html",
        items=items, broadcast="国旗是五星红旗，升起来时要立正行注目礼。")
```

### 方式二：JSON + CLI

```bash
python tools/gamegen/selftest_gen.py --spec my_questions.json
python tools/gamegen/selftest_gen.py --spec my_questions.json --dry-run
```

JSON 格式：

```json
{
  "grade": 1, "volume": "volume1", "subject": "chinese",
  "unit": "02-识字（二）", "lesson": "第4课 升国旗",
  "qtype": "choose", "filename": "01-升国旗.html",
  "broadcast": "今日广播：……",
  "items": [
    {"q": "题干", "o": ["A项", "B项", "C项", "D项"], "a": "B", "e": "解析：……", "t": "s"}
  ]
}
```

## 生成之后

生成器只写**源页**，还要走两步才进 game 目录：

```bash
python scripts/apply_game_grade2_premium.py --build   # 复制源页 → game/ 并注入 SBK2
python scripts/apply_game_kids_enhance.py            # 注入 SBK 增强层
```

## 验收（三道都要过）

```bash
python tools/gamegen/verify_games.py content/primary/pep/game            # 结构与题库
NODE_PATH=... node tools/gamegen/e2e_grade1.js "@list.txt"               # 真实浏览器渲染
NODE_PATH=... node tools/gamegen/e2e_grading.js "@list.txt"              # 判分与题库自洽
```

`@list.txt` 是一个每行一个绝对路径的清单文件（用来绕开 shell 对含空格
路径的分词）。

## 铁律（都是踩过的坑）

1. **零外部依赖**。模板里不能出现 `<link href>` / `<script src>`。游戏页通过
   iframe 以 `/game/raw?key=...` 加载，base URL 在 `/game/` 下，任何相对路径
   （`../../shared/x.css`）会解析到磁盘上不存在的位置；「双击 HTML 就能玩」
   的离线能力也依赖零外链。

2. **注释里不能出现字面量 `const ALL = [`**。`textbook.ParseBank` 用
   `strings.Index` 取**第一个**出现处，写在注释里会被先命中 → 题库解析成 0 题。

3. **答案必须带引号的字母**：`a:["B"]` / `a:["C","D"]`。写成数字或裸标识符
   会被 `ParseBank` 的 `readArray` **静默丢弃整题**。

4. **每题独占一行**。`verify_games.py` 的 `check_bank` 按行解析题库条目。

5. **换行按真实换行符处理**。内容目录 CRLF / LF **混存**（`game/grade1` =
   208 CRLF + 33 LF；`choose`+`judge` 的 1908 个源页 100% CRLF）。
   改内容时读和写都要用 `newline=""`；用通用换行模式读、再原样写回，
   整份 CRLF 文件会被静默改写成 LF。

6. **单元目录必须带题型后缀**（`（选择）` / `（判断）`）。choose 与 judge 的
   单元名完全相同，而 `gameRaw` 路径第 3 段固定是 `game`，无法区分题型。

7. **`unit` 参数不带题型后缀**，生成器自己拼。

## 零漂移自测（改模板后必跑）

模板改动的正确性判据是「重渲染存量源页能否逐字节复现」：

```python
# 读存量源页 → 反推参数 → 用 render() 重渲染 → 与磁盘逐字节比对
# 424 个 grade1/2 语文数学源页全部一致 = 模板无漂移
```

详见 `verify_g12.py` 的做法（反推元信息 + 按引号抠选项，别按逗号裸切）。
