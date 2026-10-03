# StudyBuddy 学习助手

面向小学生的**刷题自测 Web 系统**。Golang + Gin + SQLite 单文件部署，内置教材目录自动扫描、
在线答题自动判分、进度追踪、Word 试卷导出与归档。每个学生一个独立数据库，学习数据完全隔离。

---

## 一、功能特性

| 模块 | 能力 |
|------|------|
| 用户注册 | 学生姓名、**性别（我是男生 / 我是女生）**、**学段（小学 / 中学 / 高中）**、**年级与班级（点击弹出滚轮选择：滚轮一格走一行、↑↓ 逐行微调、鼠标可直接拖动、触摸板按距离换行，弹窗内也可直接填数字）**、册别、用户名、密码；**首位注册者自动成为管理员** |
| 学段 / 年级 | 学段决定年级范围（小学 1~6、中学 / 高中 1~3）；年级必填、**班级可选**（不填则只记年级）；年级取值随学段联动校验，课程匹配按 学段 + 年级 + 册别 |
| 主题皮肤 | 内置 6 套主题（清新蓝 / **男生主题** / **女生主题** / 森林绿 / 暖阳橙 / 星空紫），注册按性别自动匹配，顶栏「⚙️ 设置」里随时可换，也支持「按性别自动」 |
| 顶栏与设置 | 顶栏带装饰渐变背景（柔光 + 细点纹理），导航项为玻璃胶囊并**高亮当前所在分区**，右侧显示头像 + 姓名；「⚙️ 设置」下拉把 **外观主题 / 背景壁纸 / 账号（用户管理 · 退出登录）** 集中在一处，支持点面板外面或按 Esc 关闭 |
| 背景壁纸 | 首页按 **学段 + 年级** 匹配 `grade4/wallpaper.webp`（一张图覆盖该年级**上下册**）；进入某学科后才**精准匹配该册该学科图**（如 `g4-v1-chinese.webp`），缺失则逐级回退册别图 → 年级图 → 全局 `default.webp`；设置面板里可用开关一键关掉（写入 `users.wallpaper`）；注册页可实时预览自己该往哪放图 |
| 邀请码 | 系统已有用户后，新用户必须凭有效未作废邀请码注册；管理员可生成 / 作废 |
| 权限体系 | 管理员：邀请码、建号、改角色、设置性别、查看全部用户；普通用户：仅访问自己的数据 |
| 教材导航 | 启动时自动扫描 `content/` 目录树，按 学段→出版社→年级→册别→科目→单元→课 展示 |
| 进度追踪 | 未达标持续针对本课出题；达标（默认 ≥80 分）自动推进到下一课 |
| 在线答题 | 单选 / 多选点选作答，提交即自动判分并给出逐题解析 |
| 试卷导出 | 一键导出 `.docx`，内置 **Word 原生可交互复选框**（Word / WPS 中点一下即可勾选），自动预填姓名、班级、日期 |
| 试卷归档 | 归档到 `archive/{学生ID}/`，可在线查看历史与下载 Word |

---

## 二、目录结构

采用 Go 社区通行的标准布局（`cmd/` + `internal/` + 配套目录）：

```
StudyBuddy/
├── cmd/studybuddy/         ★ 程序入口（main.go）
├── internal/               业务内部包（外部不可引用）
│   ├── config/             配置（路径 / 达标线 / 题量，均可用环境变量覆盖）
│   ├── auth/               bcrypt、Session、鉴权中间件
│   ├── db/                 global.go 全局库 / student.go 学生私有库
│   ├── textbook/           教材内容扫描 + 题库解析
│   ├── quiz/               出题、判分、达标判定
│   ├── docx/               OOXML 试卷生成（Word 原生复选框）
│   └── web/                路由与页面处理器
│       ├── static/         静态资源（随包 go:embed 内嵌）
│       └── templates/      页面模板（随包 go:embed 内嵌）
├── content/                ★ 教材内容树（系统自动扫描，新增内容无需改代码）
│   └── primary/pep/grade4/volume1/{chinese,math,english,morallaw,science}/
├── wallpapers/             ★ 背景壁纸（目录结构与 content/ 同构，放进去刷新即生效）
│   └── primary/pep/grade4/  wallpaper.webp（首页图，四年级上下册共用）
│       ├── volume1/         g4-v1-chinese.webp + g4-v1-math.webp（学科图）
│       └── volume2/         g4-v2-chinese.webp + g4-v2-math.webp
├── deploy/                 容器化：Dockerfile、docker-compose.yml、.dockerignore
├── scripts/                工程脚本与内容工具：build-and-push.sh 一键发布推送、install.sh / uninstall.sh 一键装卸（systemd）、studybuddy_backup.sh / studybuddy_recover.sh 备份还原、start.bat 一键启动、migrate_content.py 内容规范化、_check_wallpaper.sh 壁纸自检、_shot_topbar.sh 顶栏版式自检、_check_picker.sh 年级/班级滚轮自检
├── tools/                  自检：smoke 模块级 / e2e 端到端 / bankcheck 题库与内容命名核对 / unitcheck 单元聚合自洽
├── .workbuddy/skills/      ★ 交互自测网页生成技能 interactive-quiz-html（加新题库用，见「教材目录命名规则」末节）
├── docs/                   文档：CONTENT_LAYOUT.md 教材目录规范
├── data/                   运行时生成：global/global.db + students/{id}.db
├── archive/                运行时生成：archive/{学生ID}/xxx.docx
├── go.mod / go.sum
├── Makefile                跨平台编译（win/linux/darwin × amd64/arm64）
└── README.md
```

### 教材目录命名规则

```
content/<stage>/<publisher>/grade<N>/volume<N>/<subject>/<NN-单元名>/<NN-课名>.html

content/primary/pep/grade4/volume1/chinese/01-自然之美/01-观潮.html
        │       │   │       │        │        │            └─ 课：两位序号 + 课名
        │       │   │       │        │        └─ 单元目录：两位序号 + 单元名（可省略）
        │       │   │       │        └─ 科目：chinese / math / english / morallaw / science
        │       │   │       └─ 册别：volume1 上册 / volume2 下册
        │       │   └─ 年级：grade1 ~ grade12
        │       └─ 出版社：pep（人教社）
        └─ 学段：primary 小学 / middle 初中 / high 高中
```

路径本身即元数据，文件名只保留「序号 + 课名」，不再重复年级册别。

> 后续新增年级 / 册别 / 科目 / 课程，**只需按同样规则放入 HTML 文件，系统自动识别，无需改代码**。
> 不符合规则的目录（如中文命名的占位目录）会被自动忽略。
> 完整规范见 [`docs/CONTENT_LAYOUT.md`](docs/CONTENT_LAYOUT.md)；旧命名文件可用
> `python scripts/migrate_content.py` 一键整理成标准结构。

#### 怎么批量产出这些课程 HTML（加新题库）

课程页不需要手写 —— 项目内置了生成技能 **`.workbuddy/skills/interactive-quiz-html/`**
（把「按单元/课组织的题库」渲染成交互式自测网页，自带明暗模式、🔊 朗读、随机抽题、自动判分、继续测试）。
在本项目里直接这样说即可：

> 用 interactive-quiz-html 技能，补全四年级下册五科（语文、数学、英语、道德与法治、科学）全部单元/课，
> 每课 20~40 题、不超纲，按内容规范写入 `content/primary/pep/grade4/volume2/<科目>/`，
> 命名 `NN-单元名/NN-课名.html`，生成完重启服务。

手工做的话三步：

```bash
# 1. 复制模板（引擎会自动定位项目根与自身）
cp .workbuddy/skills/interactive-quiz-html/scripts/template_subject.py scripts/build_xxx_quiz.py
# 2. 改脚本里「2) 配置」三处：ARCHIVE_REL（科目目录，相对项目根）、SUBJECT、UNITS（题库数据）
# 3. 生成 + 自检 + 重启
python scripts/build_xxx_quiz.py     # 默认 LAYOUT=content，产出 NN-单元名/NN-课名.html
go run ./tools/bankcheck             # 确认系统认了这些课、题数对不对
```

> 输出布局用 `QUIZ_LAYOUT` 切：`content`（默认，进系统）/ `flat`（平铺「四年级XX下册 · 单元 · 课.html」，离线自用）。
> `QUIZ_ARCHIVE` 可覆盖输出目录，试跑时指到临时目录最放心。
> **改完 content/ 必须重启服务**：目录只在进程启动时扫描一次。详细说明见技能里的 `SKILL.md`。

### 背景壁纸命名规则

壁纸放在 **`wallpapers/`**（项目根目录，已在仓库里备好）。**放进去刷新页面即生效，不需要重新编译**。

分两层，对应「你什么时候看到它」：

- **年级通用图** —— **学习主页 / 试卷归档 / 用户管理**等与学科无关的页面用，一张图覆盖该年级**上下册**；
- **学科专属图** —— 进入某学科（**课程页 / 在线自测页 / 自测结果页**）后，才精准匹配到**该册该学科**。

#### 1) 年级通用图：`grade{N}/wallpaper.webp`

**目录结构与 `content/` 教材树刻意保持同构**，首页只到「年级」这一层：

```
content/   primary/pep/grade4/volume1/chinese/01-自然之美/01-观潮.html    ← 教材树还要再往下分册别、学科、单元
wallpapers/primary/pep/grade4/wallpaper.webp                              ← 首页图：四年级通用（上下册同一张）
           │       │   │       └─ 年级：grade1 ~ grade6（中学 / 高中为 grade1 ~ grade3）
           │       │   └─ 出版社：pep（人教社）
           │       └─ 学段：primary 小学 / middle 初中 / high 高中
           └─ 通用图统一叫 wallpaper（扩展名自选）
```

`wallpapers/` 下已经按这套结构把 小学 1~6、中学 1~3、高中 1~3 各年级的目录都建好了，
**你只要把图丢进 `grade{N}/` 目录里、命名成 `wallpaper.webp`**，
该年级**上下册就都用这一张** —— 换上册的图，下册学生的首页也跟着换。

#### 2) 学科专属图：`g{年级}-v{册别}-{科目}.webp`

进入某个学科时才下到册别，图放在**册别目录**里（与同级的 `volume{N}/` 对应）：

```
wallpapers/primary/pep/grade4/
    wallpaper.webp             ← 首页图（四年级通用，上下册共用）
    volume1/
        g4-v1-chinese.webp     ← 四年级上册 · 语文
        g4-v1-math.webp        ← 四年级上册 · 数学
    volume2/
        g4-v2-chinese.webp     ← 四年级下册 · 语文
```

科目名用教材目录名：`chinese`（语文）/ `math`（数学）/ `english`（英语）/
`morallaw`（道德与法治）/ `science`（科学）。

**匹配关系一览（以小学四年级为例）**：

| 页面 | 匹配顺序 |
|---|---|
| 学习主页 / 试卷归档 / 用户管理 | `grade4/wallpaper.webp` → 更宽泛目录 → 全局 `default.webp`（**上册下册同一张**） |
| 四上语文的课程页 / 自测页 | `volume1/g4-v1-chinese.webp` → `volume1/wallpaper.webp` → `grade4/wallpaper.webp` → 更宽泛目录 → 全局 `default.webp` |
| 四上数学的课程页 / 自测页 | `volume1/g4-v1-math.webp` → `volume1/wallpaper.webp` → `grade4/wallpaper.webp` → … |
| 四上英语的课程页 / 自测页 | 没有英语图 → 退到 `volume1/wallpaper.webp`，再退到 `grade4/wallpaper.webp` |
| 四下语文的自测页 | 找 `volume2/g4-v2-chinese.webp` → `volume2/wallpaper.webp` → …（**不会串用上册的图**） |

一句话规则：**首页只到「年级」，学科页才下到「册别 + 学科」**；学科页里**学科图优先于册别通用图**，
同类文件名之间**目录越具体越优先**；年级图缺失时首页会退到册别图（只放了册别图的旧部署不会突然没背景），
最后才走 `wallpapers/` 根目录下的 `default.webp` 全局兜底。

#### 3) 别名写法（少记规则用）

文件名本身也可以「升级」成目录层，越具体越优先：

| 写法 | 含义 |
|---|---|
| `primary/pep/grade4/wallpaper.webp` | **推荐**：首页图，四年级上下册共用同一张 |
| `primary/pep/grade4/g4.webp` | 同目录内的别名（`primary-g4` / `g4` 都认） |
| `primary/grade4/wallpaper.webp` | 省略出版社这一层（只有一个出版社时更省事） |
| `primary/pep/grade4/volume1/wallpaper.webp` | 册别通用图：首页图的回退，也是学科页的第二顺位 |
| `primary/pep/grade4/volume1/g4-v1-chinese.webp` | **推荐的学科图命名** |
| `primary/pep/grade4/g4-v1-chinese.webp` | 学科图放到「年级」层，上下册通用（仍优先于册别通用图） |
| `g4-v1.webp` / `g4-v1-chinese.webp`（放 `wallpapers/` 根下） | 老式平铺写法，**仍然兼容** |
| `.../grade4/volume1/g4-v1.webp` | 同目录内的别名（`primary-g4-v1` / `primary-v1` / `v1` / `default` 都认） |

学科名还会依次尝试 `primary-g4-v1-chinese` → `g4-v1-chinese` → `primary-v1-chinese` →
`v1-chinese` → `wallpaper-chinese` → `chinese`；册别层通用名依次尝试
`wallpaper` → `primary-g4-v1` → `g4-v1` → `primary-v1` → `v1` → `default`；
首页在年级层另用 `wallpaper` → `primary-g4` → `g4`。

目录层顺序 —— 首页：`{学段}/{出版社}/grade{N}/` → `{学段}/grade{N}/` → 再退到册别层（顺序同下）；
学科页：`{学段}/{出版社}/grade{N}/volume{N}/` → `{学段}/grade{N}/volume{N}/`
→ `{学段}/{出版社}/grade{N}/` → `{学段}/grade{N}/` → `{学段}/{出版社}/` → `{学段}/` → 根目录。

扩展名依次尝试 `.webp` → `.png` → `.jpg` → `.jpeg` → `.avif` → `.gif`，所以 `.webp` / `.png` 都能用。

> 匹配顺序就是上面从上到下，**先命中的先用**；一个都没命中就不显示壁纸层，页面与加壁纸前完全一致。
> 学生登录后自动生效，顶栏「⚙️ 设置」面板里有「🖼 背景壁纸」开关，可一键关掉（写入 `users.wallpaper`）；
> **关掉后开关行仍然在**（文案变「背景壁纸已关闭」，开关落到关闭位），再点一下就能开回来 ——
> 显示条件用的是「有没有匹配到图」而不是「当前显示不显示」，所以不会出现「关掉就回不来了」。
> 这一行**只显示开关状态**（「背景壁纸已开启 / 已关闭」），命中位置放在悬停提示里：
> 鼠标移上去会看到是「语文 · primary/pep/grade4/volume1」还是「primary/pep/grade4 · 上下册共用」。
> 一张图都没匹配到时，这一行会显示「未匹配」并给出建议放置路径（不做点了没反应的开关）。
> 注册页底部有实时预览，选哪个年级 / 册别就会告诉你该往哪放图（首页图只到年级层），放之前也能先看效果。
> 想核对实际命中结果：`bash scripts/_check_wallpaper.sh`（用临时库起第二实例，逐页打印命中的壁纸并截图）。
> 想核对顶栏 / 设置面板的版式与配色：`bash scripts/_shot_topbar.sh`（亮色、暗色、窄屏各截一张，并打印几何与颜色探针）。
> 想核对注册页年级 / 班级滚轮的手感：`bash scripts/_check_picker.sh`（用合成事件在真浏览器里逐条验证「一格一行 / 方向键 / 拖拽 / 触摸板」并打印每步结果，再截亮色、暗色、窄屏三张图）。

---

## 三、数据库设计（硬性隔离约束）

| 库 | 路径 | 内容 |
|----|------|------|
| 全局公共库 | `data/global/global.db` | **仅**账号基础信息（用户名 / 姓名 / 学段 / 年级 / 班级 / 性别）、角色、界面主题、壁纸开关、邀请码；禁止存放任何刷题 / 学习进度数据 |
| 学生私有库 | `data/students/{user_id}.db` | 教材进度、自测记录、答题历史、试卷归档记录；每个学生一个独立实例 |
| 归档文件 | `archive/{user_id}/` | 该学生导出的 `.docx` 试卷 |

> **升级说明**：老库在启动时会自动补齐缺失的列（`ALTER TABLE … ADD COLUMN`），**不需要手工迁移**，也不会清数据。
> 目前按此方式陆续补齐过 `gender`（性别）、`skin`（自选主题）、`stage`（学段）、`wallpaper`（壁纸开关）。
> 缺 `stage` 的老账号按「学段不限」处理——课程匹配行为与升级前完全一致；补填学段后即按学段精确匹配。

---

## 四、编译与启动

### 方式一：Windows 一键启动

双击 `start.bat`（自动编译并打开浏览器）。

### 方式二：源码运行

```bash
go run ./cmd/studybuddy
# 或
make run
```

### 方式三：编译静态二进制

```bash
make build      # 当前平台 → dist/studybuddy
make windows    # windows-amd64
make linux      # linux-amd64 + linux-arm64
make dist       # Windows / Linux / macOS × amd64 / arm64
```

静态资源与页面模板均已 `go:embed` 内嵌，**编译出的单个可执行文件可直接运行**，无需携带
`static/`、`templates/`。

> 国内网络建议：`export GOPROXY=https://goproxy.cn,direct`（Makefile 已默认设置）。

启动后访问 <http://localhost:8080>。

---

## 五、Docker 镜像与部署

镜像随发布流水线自动构建（amd64 + arm64 双架构），同时发布到 **Docker Hub** 与 **GHCR**：

```shell
# Docker Hub
docker pull mobufan/studybuddy:latest
docker pull mobufan/studybuddy:v0.0.1

# GHCR
docker pull ghcr.io/meimolihan/studybuddy:latest
docker pull ghcr.io/meimolihan/studybuddy:v0.0.1
```

本地构建与运行：

```bash
# 单架构
docker build -f deploy/Dockerfile -t mobufan/studybuddy:latest .
docker run -d -p 8080:8080 \
  -v ./content:/app/content:ro \
  -v ./data:/app/data \
  -v ./archive:/app/archive \
  mobufan/studybuddy:latest

# 双架构（amd64 + arm64）
docker buildx create --use
make docker-buildx

# 或直接用 compose
docker compose -f deploy/docker-compose.yml up -d
```

`data/`、`archive/`、`content/` 已声明为 `VOLUME`，替换教材无需重建镜像。

---

## 六、邀请码使用说明

1. **系统初始化**（全局库无任何用户）：**首位注册者不需要邀请码**，注册成功后自动成为**管理员**。
2. 系统已有用户后：所有新注册都必须提交**有效且未作废**的邀请码，否则直接拒绝。
3. 管理员在「用户管理」页可：
   - 批量生成邀请码（默认 5 个，最多 50 个）；
   - 作废尚未使用的邀请码（已使用的不可作废）；
   - 直接创建普通用户或管理员账号；
   - 查看全部用户基础信息、调整角色。

---

## 七、环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `STUDYBUDDY_HOME` | 项目根目录（教材 / 数据 / 归档的父目录） | 当前工作目录 |
| `STUDYBUDDY_CONTENT` | 教材内容根目录 | `$HOME/content` |
| `STUDYBUDDY_DATA` | 数据目录 | `$HOME/data` |
| `STUDYBUDDY_ARCHIVE` | 归档目录 | `$HOME/archive` |
| `STUDYBUDDY_PORT` | 监听端口 | `8080` |
| `STUDYBUDDY_PASS` | 达标分数线 | `80` |
| `STUDYBUDDY_PER_ROUND` | 每套题数 | `10` |
| `STUDYBUDDY_SINGLE` / `STUDYBUDDY_MULTI` | 单选 / 多选题数 | `6` / `4` |
| `STUDYBUDDY_TEXTBOOK_ASSETS` | 官方教材图集目录（离线预渲染产物） | `$DATA/textbook` |
| `STUDYBUDDY_TEXTBOOK_DIR` | 源教材 PDF 根目录（供「下载原书 PDF」） | `D:\ChinaTextbook` |

---

## 八、自检工具

```bash
go test ./...                # 单元测试（含教材单元聚合的回归用例）
go run ./tools/smoke      # 教材扫描、题库解析、出题、判分、docx 结构
go run ./tools/e2e        # 进程内 HTTP 全链路：注册→刷题→判分→归档→管理员→导出 docx
go run ./tools/bankcheck  # 教材题库自检：逐课统计题数，查解析不出 / 题量偏少 / 答案不合法 / 题干重复 / 被忽略的文件
go run ./tools/unitcheck  # 单元聚合自洽：查课挂错单元 / 空单元 / 课数不守恒
```

### 官方教材模块（`/textbook`）

官方教材 PDF 采用**离线预渲染**：用脚本把整册 PDF 转成 WebP 分页图后，
服务端只做静态分发，因此 **Windows / fnOS / Docker 都无需安装 poppler、mupdf 之类的渲染依赖**。

```bash
# 1) 生成图集（产物落在 data/textbook/<key>/：cover.webp + hi/ + lo/ + meta.json）
pip install pymupdf pillow
python tools/textbook-prerender/prerender.py \
  --src "D:/ChinaTextbook/小学/语文/统编版/义务教育教科书·语文一年级上册.pdf" \
  --key primary-pep-grade1-volume1-chinese \
  --out data/textbook

# 2) 在 internal/web/textbookres.go 的 tbBooks 里登记这一册（书名、介绍、目录页码）
# 3) 重启服务，学习主页顶部即出现「官方教材」卡片，顶栏出现「教材」入口
```

性能设计：低清缩略图约 4KB/页（懒加载，用于首屏铺底与缩略图条），
高清图约 110KB/页（只加载当前页并预取相邻 2 页），图集带一年强缓存，二次打开零请求。
图集未生成时详情页自动降级为「下载原书 PDF」，不会白屏也不会 500。

这些工具都把数据写到临时目录，不污染项目 `data/` 与 `archive/`。（工具列表见上）
教材图集是运行时产物，放在 `data/textbook/` 下，不入库；换机器重跑上面的脚本即可，
Docker 部署时它随 `./data:/app/data` 挂载一起持久化。

`bankcheck` 用的是系统自己的 `textbook.Scan` + `ParseBank`，所以它说「识别到了」就一定能在页面里刷到；
发现必须修的问题（如 HTML 里没有题库、题数为 0）时退出码为 1，可直接串进脚本：

```bash
go run ./tools/bankcheck -content content -min 10   # -min 调整「题量偏少」的阈值
```

`unitcheck` 核对的是「课有没有挂到名不副实的单元下」：`content/` 里存在同序号但不同名的单元目录
（如 `primary/grade1/volume1/chinese` 下的 `01-我上学了` 与 `01-识字（一）`），运行时按
「序号 + 目录名」复合键并列展示，两者互不吞并（见 `internal/textbook/textbook.go` 的 `buildUnits`，
回归用例在 `internal/textbook/textbook_test.go`）。这类同序号目录会另外列成待整理清单，不计为缺陷。

### 题库内容深度审查（Python，只读）

```bash
python scripts/audit_bank.py       # 扫 content/，写 reports/audit_data.json
python scripts/audit_selftest.py   # 检测器自测：注入式用例，证明「有问题时一定报得出」
```

`audit_bank.py` 出 20 道以上的格式与规范检查（镜像配对、路径命名、题量区间、答案与解析字段、
文件内与跨文件重复题、DOM 模板标记、结构统计、抽样清单）。报告分两栏：

- **问题分类计数（需要修）**——真实缺陷，计数应尽量为 0。
- **待整理项（不致错）**——如上文的同序号单元目录，只提示不影响正确性。

`audit_selftest.py` 是给 `audit_bank.py` 配的保险：它在系统临时目录里造最小课件树，
逐条注入「完全重复题 / 答案越界 / 缺解析 / 题量越界 / 命名违规 / 坏题元组」等缺陷，
断言检测器**一定报出**；同时造干净输入，断言**不误报**。
没有这一层，报告里的「问题 0」无法区分「真的没问题」和「检测器写坏了静默放过」——
历史上就出现过 `questions_total_scanned += 0`（统计恒为 0）与 `naming_dup_unit`
用 `set` 累加导致 `count(n) > 1` 永不成立（检测器永远不报）这两类假阴性。
改动 `audit_bank.py` 的检测逻辑后，请一并跑 `audit_selftest.py`。

---

## 九、说明与边界

- **docx 试卷**：Word 文档中内置的是可勾选的原生复选框控件与**参考答案**（文末），
  得分栏需线下手填；**自动判分与进度更新请使用网页端「在线自测」**（网页提交即判分并推进进度）。
- **出题来源**：系统直接解析课程 HTML 中内置的题库数据，内容均在教材范围内，不超纲。
  出题时**优先抽未做过的题**，整库做完后才回退到已做过的题。
- **题型配比**：默认 6 单选 + 4 多选；若某课多选题本身不足 4 道（如部分英语句型课），
  会自动用单选题补足 10 题，不会出现缺题。
- **密码安全**：bcrypt 加密存储，无明文；Session 校验，未登录无法访问任何业务页面。
- **数据隔离**：学生只能通过自己的会话访问自己的私有库与归档目录，无法访问他人数据。

---

## 十、一键脚本部署（systemd）

适用于直接部署在 Linux 服务器（非 Docker）。脚本默认**优先下载 GitHub Releases 预编译二进制**（无需 Go/git），
自动部署教材内容树与壁纸、注册 systemd 服务、开放防火墙端口，并安装内置命令 `studybuddy`。
安装目录固定约定为 **`/var/lib/StudyBuddy`**（教材、数据、归档均在其下）。

```shell
# 默认端口 8080，安装目录 /var/lib/StudyBuddy
bash scripts/install.sh

# 自定义端口与安装目录，免交互（标准安装命令）
bash scripts/install.sh -p 8080 -d /var/lib/StudyBuddy -y

# 远程一键安装（国内网络自动走加速镜像）
bash -c "$(curl -sSL https://raw.githubusercontent.com/meimolihan/StudyBuddy/main/scripts/install.sh)" -p 8080 -d /var/lib/StudyBuddy
```

说明：

- 可重复执行，**升级等同于重新安装**（覆盖程序与教材并重启服务，`data/`、`archive/` 自动保留）。
- 源码编译方式：本地存在源码仓库或用 `-s` 指定时按源码编译安装（要求 Go >= 1.21）。
- 安装记录写入 `/etc/studybuddy.conf`，备份 / 还原 / 卸载脚本会自动读取。
- 首次使用打开访问地址**注册账号即可：首位注册者自动成为管理员**；后续注册需管理员生成邀请码。

### 内置 CLI 管理命令

安装后可直接使用 `studybuddy` 命令管理服务：

| 命令 | 说明 |
|------|------|
| `studybuddy status` | 查看 systemd 服务状态与访问地址 |
| `studybuddy start` / `stop` / `restart` | 启动 / 停止 / 重启 systemd 服务 |
| `studybuddy version` | 查看版本号（发布流水线经 `-ldflags` 注入） |
| `studybuddy help` | 显示帮助（CLI 用法与环境变量一览） |
| `studybuddy uninstall [-y] [--purge\|--keep-data]` | 停止并移除服务/进程，删除程序与安装记录，可选删除数据目录 |

```shell
# 查看服务状态（含访问地址）
studybuddy status

# 重启服务
sudo studybuddy restart

# 免确认卸载，保留数据目录
sudo studybuddy uninstall -y

# 免确认卸载，并删除数据目录
sudo studybuddy uninstall -y --purge
```

### 备份与还原

systemd 安装方式自带备份/还原脚本，脚本会自动读取 `/etc/studybuddy.conf` 中的 `APP_DIR` / `BACKUP_DIR`，
默认备份目录为 `${APP_DIR}/backup`。本仓库同名脚本位于 `scripts/` 目录，安装后在应用安装目录下亦有副本。

```shell
# 备份（在线打包、不停服，包含 data/ 与 archive/，默认保留最近 6 份）
bash scripts/studybuddy_backup.sh

# 指定备份目录与保留份数（两种传参顺序均可）
bash scripts/studybuddy_backup.sh /data/bak 8
bash scripts/studybuddy_backup.sh 8 /data/bak
```

```shell
# 还原（默认取备份目录中最新一份；还原过程中服务会短暂停止并自动重启）
bash scripts/studybuddy_recover.sh

# 指定备份目录与还原文件（文件名需形如 StudyBuddy-*.tar.gz）
bash scripts/studybuddy_recover.sh /data/bak StudyBuddy-2026-10-02_15-30-00.tar.gz
```

说明：

- 备份产物为 `StudyBuddy-YYYY-MM-DD_HH-MM-SS.tar.gz`，包含数据目录（`data/`，账号库 + 学生私有库）
  与归档目录（`archive/`，历史试卷）；教材 `content/` 属于仓库资产，不参与备份。
- 还原前请确认备份文件仍在对应 `BACKUP_DIR` 内，且安装目录路径与当前服务一致。
- 上述命令需要在运行该系统的服务器上以 root 权限执行。

### 卸载

```shell
# 免确认卸载，保留数据目录（可再次安装恢复）
sudo bash scripts/uninstall.sh -y

# 免确认卸载，并删除数据目录（含账号数据库、归档试卷与教材）
sudo bash scripts/uninstall.sh -y --purge
```

---

## 十一、自动发布流水线（GitHub Actions）

版本发布完全自动化：**本地不编译任何产物**，只负责更新版本号、推送代码、打 `v` 开头 tag；
推送后由 `.github/workflows/release.yml` 链式完成编译、发布与镜像构建。

### 发布命令

```shell
bash scripts/build-and-push.sh v0.0.1 --yes -m "第一个测试版"
```

脚本会依次：校验 tag 格式（`v0.0.1`）→ 清理同名 Release 与 tag → 更新 `VERSION` 版本文件 →
生成 `RELEASE_NOTES.md` 发版备注 → 提交推送 → 打 tag 触发流水线 → 打印流水线运行信息（需 gh CLI）。

### 流水线四阶段

| 阶段 | Job | 内容 |
|------|-----|------|
| 1 | `build-binaries` | Go 交叉编译 linux amd64 / arm64 **静态单文件**（CGO_ENABLED=0），版本号经 `-ldflags "-X main.version=..."` 注入 |
| 2 | `publish-release` | 创建 GitHub Release，附带 `studybuddy_linux_amd64` / `studybuddy_linux_arm64` 两个产物，正文取 `RELEASE_NOTES.md` |
| 3 | `build-docker` | 基于 `deploy/Dockerfile` 构建双架构镜像，推送 **Docker Hub**（`mobufan/studybuddy`）与 **GHCR**（`ghcr.io/meimolihan/studybuddy`），标签 `vX.Y.Z` / `latest` |
| 4 | `sync-cnb` | 同步仓库到 CNB 镜像仓库（未配置 `CNB_ACCESS_TOKEN` 时自动跳过） |

### 前置配置（仓库 Settings → Secrets and variables → Actions）

| Secret | 用途 |
|--------|------|
| `DOCKERHUB_USERNAME` | Docker Hub 用户名（镜像推送） |
| `DOCKERHUB_TOKEN` | Docker Hub 访问令牌 |
| `CNB_ACCESS_TOKEN` | 可选；CNB 仓库同步令牌 |

### 触发方式

- **push tag**：`git push origin vX.Y.Z`（build-and-push.sh 自动完成）；
- **手动触发**：Actions 页面选择 Release Pipeline → Run workflow，输入 tag（如 `v0.0.1`）。

### 本地开发常用命令

```shell
make build          # 当前平台编译 → dist/studybuddy
make run            # 编译并直接运行
go run ./tools/e2e  # 端到端自检
```
