// 官方教材资源模块：教科书 PDF 的注册、图集服务与阅读入口。
//
// 设计原则（与项目其它模块一致，避免牵一发动全身）：
//  1. 独立文件、独立路由前缀 /textbook，不触碰刷题用的 textbook.Tree；
//  2. 页面渲染完全复用 a.html（顶栏 / 壁纸 / 明暗模式 / 开屏动画自动生效）；
//  3. 图集是离线预渲染产物（tools/textbook-prerender），运行时只做静态分发，
//     所以 Windows / fnOS / Docker 都无需安装 poppler、mupdf 之类的渲染依赖；
//  4. 图集缺失时不报错，详情页自动降级为「下载原 PDF」，不会出现白屏。
package web

import (
	"encoding/json"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
)

// ---------------------------------------------------------------------------
// 教材注册表
// ---------------------------------------------------------------------------

// tbLesson 目录里的一课（或一次口语交际 / 语文园地）。
type tbLesson struct {
	No    string `json:"no"`    // 课程序号，园地之类没有序号时为空
	Title string `json:"title"` // 标题
	Page  int    `json:"page"`  // 起始页（PDF 页码，1 起）
}

// tbUnit 一个单元，含若干课。
//
// 这两个类型现在有两个用途，所以 JSON tag 是必需的：
//  1. 反序列化离线提取的 curric.json（Python 侧输出小写字段名）；
//  2. 序列化给 /textbook/toc 接口，字段名要与模板及前端约定一致。
type tbUnit struct {
	Name    string     `json:"name"`
	Start   int        `json:"start"`   // 单元起始页（PDF 页码）
	Lessons []tbLesson `json:"lessons"` // 该单元下的课；单元内无子条目时为空
}

// tbBook 一本教材。字段与 data/textbook/manifest.json 中的一条记录对应。
type tbBook struct {
	Key        string `json:"key"`       // 资源键，同时是图集目录名，只允许 [a-z0-9-]
	Stage      string `json:"stage"`     // primary / middle / high
	Grade      int    `json:"grade"`     // 真实年级：小学 1~6、初中 7~9、高中 10~12；解析不出为 0
	BankGrade  int    `json:"bankGrade"` // 题库年级：小学同 Grade，初中/高中 1~3
	Volume     int    `json:"volume"`    // 册别：1 上册 2 下册 0 不分上下（全一册 / 必修）
	Subject    string `json:"subject"`   // 学科键：chinese / math / english …
	SubjectCN  string `json:"subjectCN"`
	Version    string `json:"version"` // 版本：人教版 / 统编版 …
	Title      string `json:"title"`
	SubTitle   string `json:"subTitle"`
	SourcePath string `json:"src"` // 源 PDF 相对路径（/ 分隔）

	// 以下字段仅教材详情页用得到；清单里没有，运行时按需补。
	Publisher string
	Series    string
	Editor    string
	Intro     string
	Units     []tbUnit
}

// ---------------------------------------------------------------------------
// 教材清单
// ---------------------------------------------------------------------------

// tbManifest 清单结构。清单由离线工具 tools/textbook-batch/scan.py 生成，
// 运行时只读不写：D:/ChinaTextbook 下 1905 个 PDF，全盘遍历 + 逐个开页数要数秒，
// 放在启动路径上会拖慢开机，所以扫描与预渲染都放在离线工具里做。
type tbManifest struct {
	GeneratedAt string            `json:"generatedAt"`
	Root        string            `json:"root"`
	StageNames  map[string]string `json:"stageNames"`
	Books       []*tbBook         `json:"books"`
}

// tbCurricBook 人工整理的补充信息。清单只回答「有哪些书」，教材介绍与课文目录
// 得手写，按 key 挂进来；清单里没有的书，详情页自动只显示阅读器。
type tbCurricBook struct {
	Publisher string
	Series    string
	Editor    string
	Intro     string
	Units     []tbUnit
}

// ---------------------------------------------------------------------------
// 教材介绍与目录（curric.json）
// ---------------------------------------------------------------------------

// tbCurricFile 是离线提取工具产出的介绍/目录文件。
//
// 为什么单独一个文件、而不是塞进 manifest.json：
//
//  1. 体量。283 册教材的目录合计约 3 万条课目，好几 MB。塞进 manifest 会让
//     每次启动的清单解析都背上这份负担。
//  2. 更新频率。介绍与目录只在「重新提取教材」时变，教材增减才动 manifest。
//     分开两个文件，扫描和提取互不覆盖。
//  3. 懒加载。目录走独立接口按需取，首屏 HTML 不含课目。
type tbCurricFile struct {
	GeneratedAt string                     `json:"generatedAt"`
	Books       map[string]*tbCurricRecord `json:"books"`
}

// tbCurricRecord 一册教材的介绍与目录。
type tbCurricRecord struct {
	Publisher  string   `json:"publisher"`
	Editor     string   `json:"editor"`
	Intro      string   `json:"intro"`
	Confidence float64  `json:"confidence"`
	Units      []tbUnit `json:"units"`
}

var (
	curMu       sync.Mutex
	curCache    map[string]*tbCurricRecord
	curCacheMod time.Time
	curCacheOK  bool
)

// curric 读取介绍与目录文件。带 mtime 缓存：重新提取后刷新页面即可生效，
// 不用重启服务（与 books() 的热重载策略一致）。
func (a *App) curric() map[string]*tbCurricRecord {
	p := filepath.Join(a.tbAssetsDir(), "curric.json")
	st, err := os.Stat(p)
	if err != nil {
		return nil
	}
	curMu.Lock()
	defer curMu.Unlock()
	if curCacheOK && st.ModTime().Equal(curCacheMod) {
		return curCache
	}
	raw, err := os.ReadFile(p)
	if err != nil {
		return curCache
	}
	var f tbCurricFile
	if json.Unmarshal(raw, &f) != nil {
		return curCache
	}
	// 目录数据来自自动提取：置信度太低且没有目录的不上架，
	// 避免页面上出现错页链接。介绍文案即使置信度低也保留。
	out := make(map[string]*tbCurricRecord, len(f.Books))
	for k, v := range f.Books {
		if v == nil || !tbKeyOK.MatchString(k) {
			continue
		}
		if len(v.Units) == 0 && v.Intro == "" {
			continue
		}
		// 二次保险。提取阶段已经过「页码抽查命中率 ≥ 60%」的闸门
		//（见 extract_curric.py 的 verify_units），能进这份文件的目录基本可用。
		// 这里只拦统计置信度明显异常的，避免旧版文件或手工编辑把错目录带上线。
		if len(v.Units) > 0 && v.Confidence > 0 && v.Confidence < 0.35 {
			continue
		}
		out[k] = v
	}
	curCache, curCacheMod, curCacheOK = out, st.ModTime(), true
	return out
}

// curricOf 取一册的介绍与目录；没有则返回 nil。
func (a *App) curricOf(key string) *tbCurricRecord {
	m := a.curric()
	if m == nil {
		return nil
	}
	return m[key]
}

// applyCurric 把介绍与目录挂到教材上。人工整理的 tbCurric 优先级最高：
// 那是逐条核对过的，自动提取只在没有手写数据时补位。
func (a *App) applyCurric(b *tbBook) {
	if r := a.curricOf(b.Key); r != nil {
		if b.Publisher == "" {
			b.Publisher = r.Publisher
		}
		if b.Editor == "" {
			b.Editor = r.Editor
		}
		if b.Intro == "" {
			b.Intro = r.Intro
		}
		// 目录只在没有手写数据时才用提取结果，避免同一册出现两套目录
		if len(b.Units) == 0 {
			b.Units = r.Units
		}
	}
	if c, ok := tbCurric[b.Key]; ok {
		b.Publisher, b.Series = c.Publisher, c.Series
		b.Editor, b.Intro, b.Units = c.Editor, c.Intro, c.Units
	}
}

// tocUnits 返回一册最终生效的目录。必须与 applyCurric 的优先级一致，
// 否则详情页内联的是手写目录、/textbook/toc 返回的是提取目录，同一页两种内容。
func (a *App) tocUnits(key string) []tbUnit {
	if c, ok := tbCurric[key]; ok && len(c.Units) > 0 {
		return c.Units
	}
	if r := a.curricOf(key); r != nil {
		return r.Units
	}
	return nil
}

// tocWeight 估算目录内联进 HTML 的体积（粗略按字符数）。
// 超过阈值就走懒加载：目录再长也不该拖慢首屏。
// 阈值 2000 是实测定的：26 课的目录内联后详情页约 42 KB，超出后每册都在
// 首屏背上几 KB 纯文本，而访客大多只翻正文、不会展开目录。
func tocWeight(units []tbUnit) int {
	n := 0
	for _, u := range units {
		n += len(u.Name) + 24
		for _, l := range u.Lessons {
			n += len(l.No) + len(l.Title) + 32
		}
	}
	return n
}

// textbookToc 目录懒加载接口。只返回目录数据，不带教材元信息。
//
// 为什么要独立接口：283 册 × 平均 100 课 ≈ 3 万条，详情页首屏就内联这些会让
// HTML 涨到几百 KB，而多数访客只翻正文、不会展开整个目录。前端在页面加载后
// 异步拉这里，首屏只多一条几百字节的请求。
func (a *App) textbookToc(c *gin.Context) {
	key := strings.TrimSpace(c.Query("key"))
	if key == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "缺少 key"})
		return
	}
	// 必须是已登记的教材，否则这接口就成了任意 key 的探测入口
	if a.findBook(key) == nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "未找到这本教材"})
		return
	}
	units := a.tocUnits(key)
	if units == nil {
		units = []tbUnit{}
	}
	c.JSON(http.StatusOK, gin.H{"key": key, "units": units})
}

// tbCurric 已整理的介绍与目录。key 与 manifest.json 一致。
var tbCurric = map[string]tbCurricBook{
	"primary-chinese-g1-v1": {
		Publisher: "人民教育出版社",
		Series:    "统编版",
		Editor:    "教育部组织编写 · 总主编 温儒敏",
		Intro: "本册为教育部组织编写、人民教育出版社出版的统编版语文教科书，获全国优秀教材特等奖。" +
			"全书以「我上学了」开启入学教育，随后依次安排两个识字单元、两个汉语拼音单元与四个课文单元，" +
			"穿插口语交际、语文园地与快乐读书吧，循序渐进地培养识字写字、拼音拼读、朗读背诵与口语表达能力。" +
			"书末附有识字表、写字表、常用笔画名称表与常用偏旁名称表，便于随时查阅。",
		// 目录页码为「教材标注页码 + 5」换算成的 PDF 页码（本册目录页占 PDF 第 4~6 页，
		// 正文「我上学了」自 PDF 第 7 页起，故偏移量恒为 5；换书时需重新核对）。
		Units: []tbUnit{
			{Name: "我上学了", Start: 7, Lessons: []tbLesson{
				{Title: "我是中国人", Page: 8},
				{Title: "我是小学生", Page: 9},
				{Title: "我爱学语文", Page: 10},
			}},
			{Name: "第一单元 · 识字", Start: 11, Lessons: []tbLesson{
				{No: "1", Title: "天地人", Page: 11},
				{No: "2", Title: "金木水火土", Page: 12},
				{No: "3", Title: "口耳目", Page: 14},
				{No: "4", Title: "日月水火", Page: 16},
				{No: "5", Title: "对韵歌", Page: 18},
				{Title: "口语交际：我说你做", Page: 19},
				{Title: "语文园地一", Page: 20},
				{Title: "快乐读书吧：读书真快乐", Page: 24},
			}},
			{Name: "第二单元 · 汉语拼音", Start: 25, Lessons: []tbLesson{
				{No: "1", Title: "a o e", Page: 25},
				{No: "2", Title: "i u ü y w", Page: 27},
				{No: "3", Title: "b p m f", Page: 29},
				{No: "4", Title: "d t n l", Page: 31},
				{No: "5", Title: "g k h", Page: 33},
				{No: "6", Title: "j q x", Page: 35},
				{No: "7", Title: "z c s", Page: 37},
				{No: "8", Title: "zh ch sh r", Page: 39},
				{Title: "语文园地二", Page: 41},
			}},
			{Name: "第三单元 · 汉语拼音", Start: 45, Lessons: []tbLesson{
				{No: "9", Title: "ai ei ui", Page: 45},
				{No: "10", Title: "ao ou iu", Page: 47},
				{No: "11", Title: "ie üe er", Page: 49},
				{No: "12", Title: "an en in un ün", Page: 51},
				{No: "13", Title: "ang eng ing ong", Page: 53},
				{Title: "语文园地三", Page: 56},
			}},
			{Name: "第四单元 · 课文", Start: 59, Lessons: []tbLesson{
				{No: "1", Title: "秋天", Page: 59},
				{No: "2", Title: "小小的船", Page: 61},
				{No: "3", Title: "江南", Page: 63},
				{No: "4", Title: "四季", Page: 65},
				{Title: "口语交际：我们做朋友", Page: 67},
				{Title: "语文园地四", Page: 68},
			}},
			{Name: "第五单元 · 识字", Start: 72, Lessons: []tbLesson{
				{No: "6", Title: "画", Page: 72},
				{No: "7", Title: "大小多少", Page: 73},
				{No: "8", Title: "小书包", Page: 75},
				{No: "9", Title: "日月明", Page: 77},
				{No: "10", Title: "升国旗", Page: 79},
				{Title: "语文园地五", Page: 81},
			}},
			{Name: "第六单元 · 课文", Start: 85, Lessons: []tbLesson{
				{No: "5", Title: "影子", Page: 85},
				{No: "6", Title: "比尾巴", Page: 87},
				{No: "7", Title: "青蛙写诗", Page: 89},
				{No: "8", Title: "雨点儿", Page: 92},
				{Title: "口语交际：用多大的声音", Page: 94},
				{Title: "语文园地六", Page: 95},
			}},
			{Name: "第七单元 · 课文", Start: 98, Lessons: []tbLesson{
				{No: "9", Title: "明天要远足", Page: 98},
				{No: "10", Title: "大还是小", Page: 101},
				{No: "11", Title: "项链", Page: 103},
				{Title: "口语交际：小兔运南瓜", Page: 106},
				{Title: "语文园地七", Page: 108},
			}},
			{Name: "第八单元 · 课文", Start: 109, Lessons: []tbLesson{
				{No: "12", Title: "雪地里的小画家", Page: 109},
				{No: "13", Title: "乌鸦喝水", Page: 111},
				{No: "14", Title: "小蜗牛", Page: 113},
				{Title: "口语交际：小兔运南瓜", Page: 116},
				{Title: "语文园地八", Page: 117},
			}},
			{Name: "附录", Start: 120, Lessons: []tbLesson{
				{Title: "识字表", Page: 120},
				{Title: "写字表", Page: 123},
				{Title: "常用笔画名称表", Page: 124},
				{Title: "常用偏旁名称表", Page: 125},
			}},
		},
	},
}

// tbKeyOK 资源键白名单：只允许小写字母、数字与连字符，杜绝被拼进路径后越界。
var tbKeyOK = regexp.MustCompile(`^[a-z0-9][a-z0-9-]*$`)

// tbAssetOK 图集内允许访问的文件：封面 + 高清 / 低清分页图，其余一律 404。
var tbAssetOK = regexp.MustCompile(`^(cover\.webp|(hi|lo)/p\d{3}\.webp)$`)

// tbStageOrder 学段展示顺序。
var tbStageOrder = map[string]int{"primary": 0, "middle": 1, "high": 2}

var (
	tbMu       sync.Mutex
	tbCache    []*tbBook
	tbCacheMod time.Time
	tbCacheOK  bool
)

// books 读取教材清单。结果在内存里缓存，只在 manifest.json 的修改时间变化时重载，
// 因此离线工具补完图集后刷新页面即可看到新册，不必重启服务。
func (a *App) books() []*tbBook {
	p := filepath.Join(a.tbAssetsDir(), "manifest.json")
	st, err := os.Stat(p)
	if err != nil {
		return nil
	}

	tbMu.Lock()
	defer tbMu.Unlock()
	if tbCacheOK && st.ModTime().Equal(tbCacheMod) {
		return tbCache
	}

	raw, err := os.ReadFile(p)
	if err != nil {
		return tbCache // 读失败先沿用上次结果，避免清单 momentary 不可读就清空教材库
	}
	var mf tbManifest
	if json.Unmarshal(raw, &mf) != nil {
		return tbCache
	}
	books := make([]*tbBook, 0, len(mf.Books))
	for _, b := range mf.Books {
		if b == nil || !tbKeyOK.MatchString(b.Key) {
			continue // 键不合白名单的直接丢弃，绝不拿去拼路径
		}
		// 清单缓存里**只挂简介**（几 KB），不挂目录：283 册的目录合计 3 万条，
		// 全塞进 books() 缓存会让常驻内存平白多几 MB。目录由详情页与
		// /textbook/toc 按需取，见 applyCurric / textbookToc。
		if r := a.curricOf(b.Key); r != nil {
			b.Publisher, b.Editor, b.Intro = r.Publisher, r.Editor, r.Intro
		}
		books = append(books, b)
	}
	sort.SliceStable(books, func(i, j int) bool {
		x, y := books[i], books[j]
		if tbStageOrder[x.Stage] != tbStageOrder[y.Stage] {
			return tbStageOrder[x.Stage] < tbStageOrder[y.Stage]
		}
		if x.Grade != y.Grade {
			return x.Grade < y.Grade
		}
		if x.Subject != y.Subject {
			return x.Subject < y.Subject
		}
		if x.Volume != y.Volume {
			return x.Volume < y.Volume
		}
		return x.Title < y.Title
	})

	tbCache, tbCacheMod, tbCacheOK = books, st.ModTime(), true
	return books
}

// findBook 按资源键查教材。
func (a *App) findBook(key string) *tbBook {
	if !tbKeyOK.MatchString(key) {
		return nil
	}
	for _, b := range a.books() {
		if b.Key == key {
			return b
		}
	}
	return nil
}

// booksFor 取某学段 + 题库年级下的教材。subject 非空时再按学科收窄；
// volume 为 0 表示不限册别，而「全一册 / 必修」类教材（Volume==0）任何册别都算数。
func (a *App) booksFor(stage string, bankGrade, volume int, subject string) []*tbBook {
	out := make([]*tbBook, 0, 8)
	for _, b := range a.books() {
		if b.Stage != stage || b.BankGrade != bankGrade {
			continue
		}
		if subject != "" && b.Subject != subject {
			continue
		}
		if volume > 0 && b.Volume != 0 && b.Volume != volume {
			continue
		}
		out = append(out, b)
	}
	return out
}

// bookPageCount 教材总页数：优先用图集 meta，没有图集时按目录最后一项往后兜底。
func (b *tbBook) pageCount(dir string) int {
	if m, ok := b.loadMeta(dir); ok {
		return m.Pages
	}
	last := 0
	for _, u := range b.Units {
		if u.Start > last {
			last = u.Start
		}
		for _, l := range u.Lessons {
			if l.Page > last {
				last = l.Page
			}
		}
	}
	return last
}

// ---------------------------------------------------------------------------
// 图集 meta
// ---------------------------------------------------------------------------

// tbMeta 预渲染产物的描述（tools/textbook-prerender 生成）。
type tbMeta struct {
	Pages      int     `json:"pages"`
	Ratio      float64 `json:"ratio"` // 高/宽，前端据此预留占位高度，避免加载时布局抖动
	HiWidth    int     `json:"hiWidth"`
	LoWidth    int     `json:"loWidth"`
	CoverWidth int     `json:"coverWidth"`
	HiBytes    int64   `json:"hiBytes"`
	LoBytes    int64   `json:"loBytes"`
	LoReady    bool    `json:"loReady"` // 低清分页图是否齐全（首屏与缩略图条靠它）
	HiReady    bool    `json:"hiReady"` // 高清是否齐全；未就绪时前端只用低清，不发无效请求
}

// assetsDir 图集根目录（可用 STUDYBUDDY_TEXTBOOK_ASSETS 覆盖）。
func (a *App) tbAssetsDir() string {
	if v := os.Getenv("STUDYBUDDY_TEXTBOOK_ASSETS"); v != "" {
		return v
	}
	return filepath.Join(a.Cfg.DataDir, "textbook")
}

// sourceDir 源 PDF 根目录（可用 STUDYBUDDY_TEXTBOOK_DIR 覆盖）。
func (a *App) tbSourceDir() string {
	if v := os.Getenv("STUDYBUDDY_TEXTBOOK_DIR"); v != "" {
		return v
	}
	if a.Cfg.BaseDir != "" {
		// 开发机默认指向教材盘；部署到 fnOS 时用环境变量改指向即可。
		return `D:\ChinaTextbook`
	}
	return ""
}

// loadMeta 读取图集 meta.json；图集不存在或解析失败时返回 false（详情页据此降级）。
func (b *tbBook) loadMeta(dir string) (*tbMeta, bool) {
	if dir == "" || !tbKeyOK.MatchString(b.Key) {
		return nil, false
	}
	raw, err := os.ReadFile(filepath.Join(dir, b.Key, "meta.json"))
	if err != nil {
		return nil, false
	}
	var m tbMeta
	if json.Unmarshal(raw, &m) != nil || m.Pages <= 0 {
		return nil, false
	}
	return &m, true
}

// tbHasAssets 图集是否可用（分页图已生成）。
func (a *App) tbHasAssets(b *tbBook) bool {
	_, ok := b.loadMeta(a.tbAssetsDir())
	return ok
}

// ---------------------------------------------------------------------------
// 阅读进度（cookie）
// ---------------------------------------------------------------------------

// tbProgressCookie 生成进度 cookie 名，避免与其它 cookie 冲突。
func tbProgressCookie(key string) string { return "tbp_" + key }

// tbReadProgress 读阅读进度 cookie；返回 0 表示没有记录。
func tbReadProgress(c *gin.Context, key string) int {
	v, err := c.Cookie(tbProgressCookie(key))
	if err != nil {
		return 0
	}
	n, err := strconv.Atoi(v)
	if err != nil || n <= 0 {
		return 0
	}
	return n
}

// ---------------------------------------------------------------------------
// 页面与路由
// ---------------------------------------------------------------------------

// textbookPage 教材页。带 key 进详情页（封面 + 介绍 + 阅读器），不带 key 进教材库
// （全学段全年级全学科，可按学段/年级/学科筛选）。
func (a *App) textbookPage(c *gin.Context) {
	key := strings.TrimSpace(c.Query("key"))
	if key == "" {
		a.textbookLibrary(c)
		return
	}
	b := a.findBook(key)
	if b == nil {
		c.String(http.StatusNotFound, "未找到这本教材")
		return
	}

	assets := a.tbAssetsDir()
	meta, hasAssets := b.loadMeta(assets)
	pages := b.pageCount(assets)
	if pages <= 0 {
		pages = 1
	}

	// 起始页：URL 指定 > cookie 记忆 > 第 1 页。
	start := 1
	if n, _ := strconv.Atoi(c.Query("p")); n > 0 {
		start = n
	} else if n := tbReadProgress(c, b.Key); n > 0 {
		start = n
	}
	if start > pages {
		start = pages
	}

	ratio := 1.414 // 兜底高宽比（16 开约 1.413）
	if meta != nil && meta.Ratio > 0 {
		ratio = meta.Ratio
	}

	// 简介随首屏渲染（很短）；目录只在「有且仅有一条目录」时内联，
	// 其余情况由前端异步拉 /textbook/toc。模板里两者渲染同一套结构。
	a.applyCurric(b)
	hasToc := len(b.Units) > 0
	inlineToc := hasToc && tocWeight(b.Units) <= 2000

	a.html(c, "textbook.html", gin.H{
		"Title":     b.Title + " " + b.SubTitle,
		"Book":      b,
		"Meta":      meta,
		"HasAssets": hasAssets,
		// 低清齐备即可读；高清没渲染完时前端不发 hi 请求，避免刷一串 404。
		"LoReady":   meta != nil && meta.LoReady,
		"HiReady":   meta != nil && meta.HiReady,
		"Pages":     pages,
		"StartPage": start,
		"Ratio":     ratio,
		"AssetBase": "/textbook/asset/" + b.Key,
		"Progress":  tbReadProgress(c, b.Key),
		// 目录懒加载：TocURL 给前端，HasToc 决定是否渲染占位，
		// InlineToc 为真时直接用服务端已渲染好的 .Book.Units。
		"HasToc":    hasToc,
		"InlineToc": inlineToc,
		"TocURL":    "/textbook/toc?key=" + b.Key,
	})
}

// textbookLibrary 教材库页：一次列出清单里全部教材，封面懒加载。
//
// 性能：283 张封面全部交给浏览器会打 283 个请求，因此首屏只渲染筛选条与前 24 张卡片，
// 其余在滚动进入视口时由 IntersectionObserver 追加（老浏览器降级为「加载更多」按钮）。
func (a *App) textbookLibrary(c *gin.Context) {
	all := a.books()
	stage := strings.TrimSpace(c.Query("stage"))
	subject := strings.TrimSpace(c.Query("subject"))
	grade, _ := strconv.Atoi(c.Query("grade"))
	if stage != "primary" && stage != "middle" && stage != "high" {
		stage = ""
	}

	// 三个维度的可选项都从「当前学段内的全量清单」统计，避免筛出空选项。
	pool := make([]*tbBook, 0, len(all))
	for _, b := range all {
		if stage == "" || b.Stage == stage {
			pool = append(pool, b)
		}
	}

	stageSet := map[string]bool{}
	gradeSet := map[int]bool{}
	subjectSet := map[string]string{} // 学科键 → 中文名
	for _, b := range pool {
		stageSet[b.Stage] = true
		gradeSet[b.Grade] = true
		subjectSet[b.Subject] = b.SubjectCN
	}
	stageList := []string{}
	for _, k := range []string{"primary", "middle", "high"} {
		if stageSet[k] {
			stageList = append(stageList, k)
		}
	}
	gradeList := make([]int, 0, len(gradeSet))
	for g := range gradeSet {
		gradeList = append(gradeList, g)
	}
	sort.Ints(gradeList)
	subjectList := make([]string, 0, len(subjectSet))
	for k := range subjectSet {
		subjectList = append(subjectList, k)
	}
	sort.Slice(subjectList, func(i, j int) bool {
		if subjectSet[subjectList[i]] != subjectSet[subjectList[j]] {
			return subjectSet[subjectList[i]] < subjectSet[subjectList[j]]
		}
		return subjectList[i] < subjectList[j]
	})

	// 逐条按筛选条件过滤。学科未登记（点「全部学科」外的空值）时不做学科过滤。
	shown := make([]gin.H, 0, 64)
	for _, b := range pool {
		if grade > 0 && b.Grade != grade {
			continue
		}
		if subject != "" && b.Subject != subject {
			continue
		}
		meta, hasAssets := b.loadMeta(a.tbAssetsDir())
		pages := b.pageCount(a.tbAssetsDir())
		read := tbReadProgress(c, b.Key)
		shown = append(shown, gin.H{
			"Key":      b.Key,
			"Title":    b.Title,
			"Sub":      tbSubLabel(b),
			"Subject":  b.SubjectCN,
			"Stage":    b.Stage,
			"StageCN":  tbStageNames[b.Stage],
			"Grade":    b.Grade,
			"Version":  b.Version,
			"Cover":    "/textbook/asset/" + b.Key + "/cover.webp",
			"HasAsset": hasAssets,
			// 高清是否已渲染完：没完的先显示低清，不往浏览器发注定 404 的高清请求
			"HiReady":  meta != nil && meta.HiReady,
			"Pages":    pages,
			"ReadPage": read,
		})
	}

	stageCN := map[string]string{"primary": "小学", "middle": "初中", "high": "高中"}
	a.html(c, "textbooks.html", gin.H{
		"Title":       "教材库",
		"Books":       shown,
		"Total":       len(all),
		"Stage":       stage,
		"StageCN":     stageCN[stage],
		"Grade":       grade,
		"Subject":     subject,
		"StageList":   stageList,
		"StageName":   stageCN,
		"GradeList":   gradeList,
		"SubjectList": subjectList,
		"SubjectName": subjectSet,
	})
}

// tbStageNames 学段中文名。
var tbStageNames = map[string]string{"primary": "小学", "middle": "初中", "high": "高中"}

// tbSubLabel 生成卡片上的年级册别标签；年级解析不出来的（高中「必修」类）只显示册别。
func tbSubLabel(b *tbBook) string {
	switch {
	case b.Grade > 0 && b.SubTitle != "":
		return b.SubTitle
	case b.Grade > 0:
		return tbGradeLabel(b.Stage, b.Grade)
	default:
		if b.SubTitle != "" {
			return b.SubTitle
		}
		return "全一册"
	}
}

// tbGradeLabel 年级中文标签：小学一~六、初中七~九、高中高一~高三。
func tbGradeLabel(stage string, grade int) string {
	if stage == "high" {
		switch grade {
		case 10:
			return "高一"
		case 11:
			return "高二"
		case 12:
			return "高三"
		}
	}
	cn := []string{"", "一", "二", "三", "四", "五", "六", "七", "八", "九"}
	if grade >= 1 && grade <= 9 {
		return cn[grade] + "年级"
	}
	return ""
}

// textbookAsset 分发图集文件：/textbook/asset/<key>/<cover.webp|hi/pNNN.webp|lo/pNNN.webp>
//
// 安全策略沿用壁纸模块的思路并收紧：资源键必须命中注册表、文件名必须命中白名单正则、
// 拼接后的绝对路径再次确认仍在图集根内，三重校验后才落盘读取。
func (a *App) textbookAsset(c *gin.Context) {
	rel := strings.Trim(c.Param("path"), "/")
	segs := strings.Split(rel, "/")
	if len(segs) < 2 {
		c.Status(http.StatusNotFound)
		return
	}
	key, name := segs[0], strings.Join(segs[1:], "/")
	if !tbKeyOK.MatchString(key) || a.findBook(key) == nil || !tbAssetOK.MatchString(name) {
		c.Status(http.StatusNotFound)
		return
	}

	root, err := filepath.Abs(a.tbAssetsDir())
	if err != nil {
		c.Status(http.StatusNotFound)
		return
	}
	p := filepath.Join(root, key, filepath.FromSlash(name))
	if !strings.HasPrefix(p, root+string(filepath.Separator)) {
		c.Status(http.StatusNotFound) // 双保险：确认没跑出图集目录
		return
	}
	st, err := os.Stat(p)
	if err != nil || st.IsDir() {
		c.Status(http.StatusNotFound)
		return
	}

	// 图集是内容寻址的生成物，重渲后文件名不变但内容不常变，给一年强缓存：二次打开零请求。
	c.Header("Cache-Control", "public, max-age=31536000, immutable")
	c.Header("Content-Type", "image/webp")
	http.ServeFile(c.Writer, c.Request, p)
}

// textbookRaw 源 PDF 直出（图集未生成时的兜底入口，http.ServeFile 自带 Range 支持）。
func (a *App) textbookRaw(c *gin.Context) {
	b := a.findBook(strings.TrimSpace(c.Query("key")))
	if b == nil {
		c.Status(http.StatusNotFound)
		return
	}
	root, err := filepath.Abs(a.tbSourceDir())
	if err != nil || root == "" {
		c.Status(http.StatusNotFound)
		return
	}
	p := filepath.Join(root, filepath.FromSlash(b.SourcePath))
	if !strings.HasPrefix(p, root+string(filepath.Separator)) {
		c.Status(http.StatusNotFound)
		return
	}
	if st, err := os.Stat(p); err != nil || st.IsDir() {
		c.Status(http.StatusNotFound)
		return
	}
	c.Header("Content-Type", "application/pdf")
	c.Header("Cache-Control", "private, max-age=3600")
	http.ServeFile(c.Writer, c.Request, p)
}

// tbHomeCards 学习主页「官方教材」封面墙的数据。
//
// 筛选口径：**当前登录学生所在年级 + 当前学期**（上册 / 下册）下的全部教材，学科不限。
// 绝不跨年级、也不跨学期：学生这学期在读上册，就不该在下册的封面堆里翻找。
//
// volume 的处理有个重要细节：booksFor 对「全一册 / 必修」类教材（Volume==0）
// 本就按「任何册别都算数」处理，所以初中 / 高中那些没有上下册概念的教材不会被
// 学期过滤误杀——这正是我们想要的。volume 传 0（学生档案没填学期）时不过滤册别，
// 退化为该年级全部教材，避免整块空掉。
//
// 排序按学科的中小学习惯（语文→数学→英语→科学→道德与法治→音乐→美术…），
// 不分册别的排在同科末尾。
// 返回空切片表示该年级该学期暂无教材，模板据此渲染友好空状态而不是白屏。
func (a *App) tbHomeCards(stage string, bankGrade, volume int) []gin.H {
	books := a.booksFor(stage, bankGrade, volume, "")
	if len(books) == 0 {
		return nil
	}
	// books() 内部已按 stage/grade/subject/volume/title 排好序，这里只在副本上重排，
	// 不动全局缓存，免得影响教材库页（/textbooks）的既有顺序。
	sorted := make([]*tbBook, len(books))
	copy(sorted, books)
	sort.SliceStable(sorted, func(i, j int) bool {
		x, y := sorted[i], sorted[j]
		if xi, yi := tbSubjectOrder[x.Subject], tbSubjectOrder[y.Subject]; xi != yi {
			return xi < yi
		}
		// Volume==0（全一册 / 必修）排在本学科有册别的教材之后
		if (x.Volume == 0) != (y.Volume == 0) {
			return y.Volume == 0
		}
		if x.Volume != y.Volume {
			return x.Volume < y.Volume
		}
		return x.Title < y.Title
	})

	// 同学科同册别可能收录多册（英语 PEP / 精通、音乐五线谱 / 简谱），
	// 光靠「学科 · 册别」用户根本分不清，所以要给每册补一个可区分的短后缀。
	// 候选按优先级逐个尝试，**先到先得**：源目录版本 → 标题括注 → 序号。
	//
	// 源目录版本排在标题括注**前面**，因为它是真正稳定的区分依据：
	// 标题括注可能是「三年级起点」这种两册共有的无效信息（英语下册 PEP / 精通
	// 标题完全一样），而源目录写的是「人教版（PEP）」「人教版（精通）」，一看就懂。
	// 音乐这类标题括注已经够用（五线谱 / 简谱）的，取到的值与源目录一致，无副作用。
	// 必须逐级回退：同标题的两册第一候选会撞车，此时要能退到第二候选而不是直接跳序号。
	// 全部候选都被占满才用序号兜底——宁可名字丑一点，也不能两本书同名。
	groups := make(map[string]int) // 「学科/册别」→ 该组册数
	used := make(map[string]map[string]bool)
	candidates := func(b *tbBook) []string {
		var out []string
		add := func(s string) {
			if s == "" {
				return
			}
			for _, e := range out {
				if e == s {
					return
				}
			}
			out = append(out, s)
		}
		add(tbSrcNote(b.SourcePath))
		add(tbParenNote(b.Title))
		return out
	}
	for _, b := range sorted {
		groups[b.Subject+"/"+strconv.Itoa(b.Volume)]++
	}
	nameOf := func(b *tbBook) string {
		base := b.SubjectCN + " · " + tbVolumeLabel(b.Volume)
		k := b.Subject + "/" + strconv.Itoa(b.Volume)
		if groups[k] < 2 {
			return base // 该学科该册别只有一册，保持干净短名
		}
		if used[k] == nil {
			used[k] = map[string]bool{}
		}
		for _, s := range candidates(b) {
			if !used[k][s] {
				used[k][s] = true
				return base + "（" + s + "）"
			}
		}
		// 候选全被占（同一本书被重复收录），用序号兜底保证唯一
		for i := 1; ; i++ {
			s := "第" + strconv.Itoa(i) + "版"
			if !used[k][s] {
				used[k][s] = true
				return base + "（" + s + "）"
			}
		}
	}

	assets := a.tbAssetsDir()
	out := make([]gin.H, 0, len(sorted))
	for _, b := range sorted {
		_, ok := b.loadMeta(assets)
		name := nameOf(b)
		out = append(out, gin.H{
			"Key":   b.Key,
			"Name":  name,
			"Alt":   name + " 封面",
			"Cover": "/textbook/asset/" + b.Key + "/cover.webp",
			// 图集未预渲染时不发图片请求，直接渲染占位块，避免一排 404
			"HasAssets": ok,
		})
	}
	return out
}

// tbSrcNote 从源路径的目录名里取版本括注，如
// 「小学/英语/人教版（PEP）（三年级起点）（主编：吴欣）/xxx.pdf」→「PEP」。
// 标题本身撞车时（同标题不同册）靠它区分，比页数可靠得多。
func tbSrcNote(src string) string {
	dir := src
	if i := strings.LastIndex(dir, "/"); i >= 0 {
		dir = dir[:i]
	} else if i := strings.LastIndex(dir, "\\"); i >= 0 {
		dir = dir[:i]
	}
	// 目录里可能有多个括注，取第一个非「主编 / 主编：xxx」类的版本说明
	rest := dir
	for {
		i := strings.Index(rest, "（")
		if i < 0 {
			return ""
		}
		rest = rest[i+len("（"):]
		j := strings.Index(rest, "）")
		if j <= 0 {
			return ""
		}
		note := strings.TrimSpace(rest[:j])
		rest = rest[j+len("）"):]
		if strings.HasPrefix(note, "主编") || strings.HasPrefix(note, "年级") {
			continue
		}
		return note
	}
}

// tbParenNote 取出标题里第一个「（…）」中的内容，深度只一层，够用且不会误吃嵌套内容。
func tbParenNote(title string) string {
	i := strings.Index(title, "（")
	if i < 0 {
		return ""
	}
	rest := title[i+len("（"):]
	j := strings.Index(rest, "）")
	if j <= 0 {
		return ""
	}
	return strings.TrimSpace(rest[:j])
}

// tbSubjectOrder 学科展示顺序（数字小的在前）。未登记的学科统一排最后，
// 保证以后新增学科时首页顺序依然稳定，不会插到语文前面去。
var tbSubjectOrder = map[string]int{
	"chinese": 0, "math": 1, "english": 2, "science": 3, "morallaw": 4,
	"music": 5, "art": 6, "pe": 7, "history": 8, "geography": 9,
	"politics": 10, "physics": 11, "chemistry": 12, "biology": 13,
	"technology": 14, "information": 15,
}

// tbVolumeLabel 册别中文名。0 表示不分上下册（全一册 / 必修）。
func tbVolumeLabel(v int) string {
	switch v {
	case 1:
		return "上册"
	case 2:
		return "下册"
	default:
		return "全一册"
	}
}
