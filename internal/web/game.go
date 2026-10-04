package web

// 游戏题模块：把 content/<学段>/<出版社>/game/ 下的独立 HTML 小游戏挂到站点上。
//
// 设计原则（与教材模块一致，避免牵一发动全身）：
//  1. **完全独立的目录扫描器**。刷题用的 textbook.Tree 只认 choose / judge，
//     把 game 塞进 parseLesson 会牵动导航、归档、首页所有按题型分支的逻辑，
//     违反「不改动原有业务逻辑」的约束。这里另起一套解析（gameScan），
//     与 textbook 包零耦合：删掉整个 game.go，游戏功能消失，其它模块毫无影响。
//  2. **游戏本体仍是磁盘上的静态 HTML**，运行时只做原样分发（gameRaw），
//     不解析、不改写、不注入脚本逻辑。因此新增/修改游戏只需改文件 + 重启，
//     不需要重新编译；游戏作者也能脱离站点单独双击 HTML 调试。
//  3. **用 iframe 承载**（game.html 里的 <iframe>）。游戏 HTML 自带 body 背景与
//     全屏布局，若直接内联进主页面会被 StudyBuddy 的页头/页脚/壁纸搅乱；
//     iframe 给出干净的独立视口，同时主页面仍能提供统一的返回按钮与页脚。
//  4. **空状态不报错**。目录不存在 / 该年级册别没有游戏 / 单个文件损坏，
//     一律降级为一句友好的说明，页面其余部分照常工作。
//
// 目录规范（与 choose / judge 同构，只是把题型层换成 game）：
//
//	<学段>/<出版社>/game/grade<N>/volume<M>/<学科>/<单元>/<游戏名>.html
//	例：primary/pep/game/grade1/volume1/chinese/01-识字（一）/01-天地人.html

import (
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"sync"

	"github.com/gin-gonic/gin"

	"studybuddy/internal/auth"
	"studybuddy/internal/textbook"
)

// gameQType 游戏题的「题型」标识。刻意不复用 textbook.QTypeChoose /
// QTypeJudge：那两个常量被解析器用来决定课程进不进刷题树，混用会让
// 「游戏是一道题」还是「游戏是一个独立应用」这个边界彻底糊掉。
const gameQType = "game"

// gameStageOK 学段白名单。
//
// 为什么不直接问 textbook：NormalizeStage / StageCN 遇到不认识的值都原样返回
// （「保持未知值可透传」是它们的既定语义，刷题侧靠私有 stageCN 表兜底），
// 拿它们的返回值当判据等于没校验。这里显式列出三个学段，
// 初中 / 高中的新命名（junior / senior）已在 NormalizeStage 里归一化过了。
var gameStages = map[string]bool{
	textbook.StagePrimary: true,
	textbook.StageMiddle:  true,
	textbook.StageHigh:    true,
}

func gameStageOK(s string) bool { return s != "" && gameStages[s] }

// gameSeg 游戏目录的固定层数：学段/ 出版社/ game/ grade<N>/ volume<M>/ 学科/ 单元/ 文件。
const gameSeg = 8

// Game 一个游戏资源。
type Game struct {
	Key   string // 唯一键：相对教材内容根的路径（/ 分隔）
	Title string // 游戏名（文件名去扩展名）
	Path  string // 绝对路径

	Stage     string
	Publisher string
	Grade     int
	Volume    int
	Subject   string
	SubjectCN string
	Unit      string
	UnitNo    int
}

// Label 该游戏的一句话描述，用在列表页副标题上。
func (g *Game) Label() string {
	return fmt.Sprintf("%s · %s · %s", textbook.GradeLabel(g.Stage, g.Grade), volumeLabel(g.Volume), g.Unit)
}

// gameTitleRe 匹配游戏 HTML 的 <title>，取其中作为展示名。
//
// 为什么要读文件而不是直接用文件名：任务要求「每个单元创建**同名**游戏 html」，
// 于是文件名 = 单元名（01-识字（一）.html），剥掉课序前缀后仍是「识字（一）」——
// 列表页已经按单元分组显示了，同一个名字会出现两遍（分组标题 + 卡片），
// 而且「语文（上）01-识字（一）」单元下清一色叫「识字（一）」，看不出区别。
// 游戏内部已经写好了玩法名（<title>生字大挑战</title>），直接用它当展示名，
// 既区分得开，又不用在站点侧维护第二份名字表。
var gameTitleRe = regexp.MustCompile(`(?is)<title[^>]*>(.*?)</title>`)

// gameTitleRE 内部缓存：文件名 → <title> 内容。
var (
	gameTitleMu    sync.RWMutex
	gameTitleCache = map[string]string{}
)

// DisplayTitle 返回该游戏适合展示的名字（取自 HTML 的 title）。
//
// 读不到 <title>（文件损坏 / 不是 HTML）时回落到文件名 —— 宁可显示
// 一个笨拙但正确的名字，也不要让整张列表页因一个坏文件而崩。
func (g *Game) DisplayTitle() string {
	gameTitleMu.RLock()
	if v, ok := gameTitleCache[g.Key]; ok {
		gameTitleMu.RUnlock()
		return v
	}
	gameTitleMu.RUnlock()

	name := ""
	if b, err := os.ReadFile(g.Path); err == nil {
		if m := gameTitleRe.FindSubmatch(b); m != nil {
			name = strings.TrimSpace(string(m[1]))
		}
	}
	if name == "" {
		name = g.Title
	}

	gameTitleMu.Lock()
	gameTitleCache[g.Key] = name
	gameTitleMu.Unlock()
	return name
}

// GameIndex 某个「学段+年级+册别」下的游戏索引，按学科与单元分组。
type GameIndex struct {
	Stage   string
	Grade   int
	Volume  int
	Title   string // 一年级 · 上册
	HasAny  bool   // 该年级册别是否存在游戏（区分「没有这门学科」和「整个册别都没有」）
	Subject []*GameSubject
}

// GameSubject 一个学科下的游戏（按单元分组）。
type GameSubject struct {
	Key   string
	Name  string
	Units []*GameUnit
}

// GameUnit 一个单元下的游戏。
type GameUnit struct {
	No   int
	Name string
	// Games 每个游戏带 Show 展示名（取自 HTML 的 <title>，通常与文件名不同）。
	Games []*GameView
}

// GameView 列表页用的游戏视图：把 *Game 与展示名打包，
// 免得模板里到处调方法（模板不该关心名字的来源）。
type GameView struct {
	*Game
	Show string // 展示名，来自 <title>
}

// GameStore 游戏资源索引。
//
// 只在启动后首次访问时扫描一次，之后常驻内存：游戏文件是离线产物、
// 运行期不会增删，与教材图集的处理方式一致。mu 保护并发首访。
type GameStore struct {
	mu   sync.Mutex
	once sync.Once
	root string
	byID map[string]map[int]map[int][]*Game // stage → grade → volume → games
	all  []*Game
}

var games = &GameStore{}

// gameRoot 返回扫描起点：教材内容根（content/）。
//
// 游戏目录 content/<学段>/<出版社>/game/ 与 choose / judge 是**同级**关系，
// 所以扫描起点就是内容根，由 parseGamePath 靠第三段 == "game" 把它们筛出来。
// 这样新增游戏只需按现有目录习惯放文件，不必另配一个根目录；
// 需要把游戏放到别处（如共享盘）时用 STUDYBUDDY_GAME_DIR 覆盖。
func gameRoot() string {
	if v := strings.TrimSpace(os.Getenv("STUDYBUDDY_GAME_DIR")); v != "" {
		return v
	}
	return contentRootPath
}

// contentRootPath 教材内容根，由 cmd 层在启动时通过 SetContentRoot 注入一次。
// 本包不直接依赖 config，避免 web ← config 的额外耦合。
var contentRootPath = ""

// SetContentRoot 注入教材内容根。cmd 层在 New() 之前调用。
func SetContentRoot(p string) { contentRootPath = p }

// load 首次访问时扫描目录。
func (s *GameStore) load() {
	s.once.Do(func() {
		// 已经在构造时指定了根目录（测试注入临时目录）就尊重它，
		// 只有留空时才回落到全局 gameRoot()。
		// 反过来写会把测试目录冲成 ""，于是 Index 空、页面"没有游戏"。
		if s.root == "" {
			s.root = filepath.Clean(gameRoot())
		}
		s.byID = map[string]map[int]map[int][]*Game{}
		if s.root == "" || s.root == "." {
			return
		}
		if _, err := os.Stat(s.root); err != nil {
			return // 目录不存在：整站照常，只是没有游戏
		}
		_ = filepath.Walk(s.root, func(path string, info os.FileInfo, err error) error {
			if err != nil || info == nil || info.IsDir() {
				return nil
			}
			if !strings.EqualFold(filepath.Ext(path), ".html") {
				return nil
			}
			rel, err := filepath.Rel(s.root, path)
			if err != nil {
				return nil
			}
			g := parseGamePath(filepath.ToSlash(rel))
			if g == nil {
				return nil
			}
			g.Key = filepath.ToSlash(rel)
			g.Path = path
			if s.byID[g.Stage] == nil {
				s.byID[g.Stage] = map[int]map[int][]*Game{}
			}
			if s.byID[g.Stage][g.Grade] == nil {
				s.byID[g.Stage][g.Grade] = map[int][]*Game{}
			}
			s.byID[g.Stage][g.Grade][g.Volume] = append(s.byID[g.Stage][g.Grade][g.Volume], g)
			s.all = append(s.all, g)
			return nil
		})
		for _, m := range s.byID {
			for _, vm := range m {
				for _, list := range vm {
					sortGames(list)
				}
			}
		}
	})
}

// sortGames 排序：学科 → 单元号 → 课序，保证列表页顺序稳定。
func sortGames(list []*Game) {
	sort.SliceStable(list, func(i, j int) bool {
		a, b := list[i], list[j]
		if a.Subject != b.Subject {
			return subjectOrder(a.Subject) < subjectOrder(b.Subject)
		}
		if a.UnitNo != b.UnitNo {
			return a.UnitNo < b.UnitNo
		}
		if a.Unit != b.Unit {
			return a.Unit < b.Unit
		}
		return a.Title < b.Title
	})
}

// subjectOrder 学科展示顺序：语文 → 数学 → 其余按键名。
func subjectOrder(s string) int {
	switch s {
	case "chinese":
		return 0
	case "math":
		return 1
	case "english":
		return 2
	}
	return 9
}

// parseGamePath 解析 content/<stage>/<publisher>/game/grade<N>/volume<M>/<subject>/<unit>/<file>.html。
// 不符合规范返回 nil（交由上层忽略）。
//
// 这里**刻意不复用** textbook.parseLesson：那个函数的第三段是题型开关，
// 只认 choose / judge，且长度校验是 6~7 段；游戏是 8 段且第三段固定为 game。
// 复用它等于给刷题树塞进一个新题型，导航 / 归档 / 首页全要跟着改。
func parseGamePath(rel string) *Game {
	parts := strings.Split(rel, "/")
	if len(parts) != gameSeg {
		return nil
	}
	stage := textbook.NormalizeStage(parts[0])
	// NormalizeStage 与 StageCN 对无法识别的学段都是**原样返回**
	// （刷题侧靠私有 stageCN 表二次把关，那是包内细节、外部拿不到）。
	// 所以这里必须自己持有一份白名单，否则 content/weird/… 这类脏目录
	// 也会被扫进游戏索引，页面上出现一个没人认领的年级分组。
	if !gameStageOK(stage) {
		return nil
	}
	if !strings.EqualFold(parts[2], gameQType) {
		return nil // 只认 game 层，choose/judge 目录一概不理
	}
	publisher := strings.ToLower(parts[1])
	if publisher == "" {
		return nil
	}
	grade, ok := parseGameInt(parts[3], "grade")
	if !ok || grade < 1 {
		return nil
	}
	volume, ok := parseGameInt(parts[4], "volume")
	if !ok || volume < 1 {
		return nil
	}
	subject := strings.ToLower(parts[5])
	subjectCN := textbook.SubjectCN(subject)
	if subjectCN == "" {
		return nil
	}
	unitNo, unit := splitGameSeqName(parts[6])
	if unit == "" {
		return nil
	}
	// 文件名同样可能带课序前缀（"01-天地人.html"）。列表页已经在分组标题上
	// 显示了单元与课序，卡片里再带一遍就成了「01-识字（一） › 01-天地人」，
	// 序号重复两遍，所以这里把 NN- 剥掉，只留名字。
	_, title := splitGameSeqName(baseGameName(parts[7]))
	title = strings.TrimSpace(strings.ReplaceAll(title, "_", " "))
	if title == "" {
		return nil
	}
	return &Game{
		Stage: stage, Publisher: publisher, Grade: grade, Volume: volume,
		Subject: subject, SubjectCN: subjectCN, Unit: unit, UnitNo: unitNo,
		Title: title,
	}
}

// parseGameInt 解析 grade<N> / volume<M>，只接受「前缀 + 正整数」，
// 避免 strconv 的宽松解析把 "grade4x" 之类的脏目录也算成合法年级。
func parseGameInt(seg, prefix string) (int, bool) {
	if !strings.HasPrefix(strings.ToLower(seg), prefix) {
		return 0, false
	}
	rest := seg[len(prefix):]
	n, err := strconv.Atoi(rest)
	if err != nil || n <= 0 {
		return 0, false
	}
	return n, true
}

// splitGameSeqName 把 "01-识字（一）" 拆成序号 1 与名称 "识字（一）"。
// 没有 "数字-" 前缀时（如某些自定义目录）序号为 0、名称取整段。
//
// 判定前缀用「首个 - 之前是否全是数字」而不是固定看前两位：
// 游戏名里本身可能带短横（如 "数一数-比多少"），固定两位会把它误切。
func splitGameSeqName(seg string) (int, string) {
	seg = strings.TrimSpace(seg)
	i := strings.Index(seg, "-")
	if i <= 0 {
		return 0, seg
	}
	if n, err := strconv.Atoi(seg[:i]); err == nil {
		return n, strings.TrimSpace(seg[i+1:])
	}
	return 0, seg
}

// baseGameName 去掉扩展名。
func baseGameName(p string) string { return strings.TrimSuffix(p, filepath.Ext(p)) }

// volumeLabel 册别中文名。
func volumeLabel(v int) string {
	if v == 2 {
		return "下册"
	}
	return "上册"
}

// List 取某学段年级册别下的游戏索引（按学科 / 单元分组）。
func (s *GameStore) List(stage string, grade, volume int) *GameIndex {
	s.load()
	idx := &GameIndex{Stage: stage, Grade: grade, Volume: volume}
	idx.Title = textbook.GradeLabel(stage, grade) + " · " + volumeLabel(volume)
	if s.byID[stage] == nil {
		return idx
	}
	if s.byID[stage][grade] == nil {
		return idx
	}
	list := s.byID[stage][grade][volume]
	if len(list) == 0 {
		return idx
	}
	idx.HasAny = true

	// 学科 → 单元 → 游戏 三层聚合，保持 sortGames 已排好的顺序。
	type unitKey struct {
		no int
		nm string
	}
	subjOrder := []string{}
	subjSeen := map[string]*GameSubject{}
	unitSeen := map[string]map[unitKey]*GameUnit{}
	for _, g := range list {
		gs, ok := subjSeen[g.Subject]
		if !ok {
			gs = &GameSubject{Key: g.Subject, Name: g.SubjectCN}
			subjSeen[g.Subject] = gs
			unitSeen[g.Subject] = map[unitKey]*GameUnit{}
			subjOrder = append(subjOrder, g.Subject)
		}
		k := unitKey{g.UnitNo, g.Unit}
		gu, ok := unitSeen[g.Subject][k]
		if !ok {
			gu = &GameUnit{No: g.UnitNo, Name: g.Unit}
			unitSeen[g.Subject][k] = gu
			gs.Units = append(gs.Units, gu)
		}
		gu.Games = append(gu.Games, &GameView{Game: g, Show: g.DisplayTitle()})
	}
	sort.Strings(subjOrder)
	for _, k := range subjOrder {
		idx.Subject = append(idx.Subject, subjSeen[k])
	}
	return idx
}

// Find 按 key 取单个游戏。
func (s *GameStore) Find(key string) *Game {
	s.load()
	key = strings.TrimSpace(key)
	if key == "" {
		return nil
	}
	// 遍历而非建二级索引：游戏总量在百级，一次线性扫完全无压力，
	// 换来的是不必维护 key 规范化（大小写 / 斜杠 / 相对前缀）的两套逻辑。
	for _, g := range s.all {
		if g.Key == key {
			return g
		}
	}
	return nil
}

// Count 该学段下所有册别的游戏总数（供入口卡片显示）。
func (s *GameStore) Count(stage string, grade int) int {
	s.load()
	n := 0
	for _, list := range s.byID[stage][grade] {
		n += len(list)
	}
	return n
}

// HasAnyStage 该学段年级是否**任何册别**都有游戏。
// 入口卡片的「暂未收录」提示只看这个，避免学生在下册看不到游戏时
// 误以为整个年级都没有 —— 列表页里还有「切换学期」的入口。
func (s *GameStore) HasAnyStage(stage string, grade int) bool {
	return s.Count(stage, grade) > 0
}

// gamesFor 按指定根目录建一个独立的索引实例（测试用）。
// 线上走全局 games 单例；测试需要指向临时目录，所以留一个注入口。
func gamesFor(stage string, grade, volume int, root string) *GameIndex {
	if root == "" {
		return games.List(stage, grade, volume)
	}
	s := &GameStore{root: filepath.Clean(root), byID: map[string]map[int]map[int][]*Game{}}
	s.load()
	return s.List(stage, grade, volume)
}

// ---------------------------------------------------------------------------
// 路由
// ---------------------------------------------------------------------------

// gameNavGradeVolume 决定游戏列表页看哪个年级册别。
//
// 口径：URL 显式参数 > 用户档案 > 回落到一年级上册。
// 与 resolveNav 的差别是这里**不做「该册别没数据就顺延」**——
// 游戏是可选资源，顺延会让学生在「二年级上册」的标题下看到一年级内容，
// 反而困惑。找不到就如实显示空状态。
func (a *App) gameNavGradeVolume(s *auth.Session, c *gin.Context) (string, int, int) {
	stage := textbook.NormalizeStage(s.Stage)
	if stage == "" {
		stage = textbook.StagePrimary
	}
	grade, volume := s.Grade, s.Volume
	if qg, err := strconv.Atoi(c.Query("grade")); err == nil && qg > 0 {
		grade = qg
	}
	if qv, err := strconv.Atoi(c.Query("volume")); err == nil && qv > 0 {
		volume = qv
	}
	if grade <= 0 {
		grade = 1
	}
	if volume <= 0 {
		volume = 1
	}
	return stage, grade, volume
}

// gamesPage 游戏列表页：按当前学生年级学期列出全部游戏。
func (a *App) gamesPage(c *gin.Context) {
	s := auth.Current(c)
	stage, grade, volume := a.gameNavGradeVolume(s, c)
	idx := games.List(stage, grade, volume)

	// 同学期可切换的册别：只有真实存在游戏的册别才出现在切换器里。
	avail := []gin.H{}
	for v := 1; v <= 2; v++ {
		if n := len(games.List(stage, grade, v).Subject); n > 0 {
			avail = append(avail, gin.H{"No": v, "Name": volumeLabel(v)})
		}
	}
	otherGrade := games.Count(stage, grade) - len(idx.Subject)

	a.html(c, "games.html", gin.H{
		"Title":      "游戏题",
		"Nav":        "study",
		"Index":      idx,
		"Volumes":    avail,
		"OtherCount": otherGrade,
		"GradeLabel": textbook.GradeLabel(stage, grade),
		"Grade":      grade,
		"Volume":     volume,
	})
}

// gamePage 游戏容器页：统一的返回按钮 + iframe 承载游戏本体。
func (a *App) gamePage(c *gin.Context) {
	s := auth.Current(c)
	g := games.Find(c.Query("key"))
	if g == nil {
		// 游戏文件被删 / 改名 / key 打错：回到列表页并带一句说明，
		// 而不是甩一个 500 或白屏。
		a.html(c, "games.html", gin.H{
			"Title":      "游戏题",
			"Nav":        "study",
			"Index":      games.List(textbook.NormalizeStage(s.Stage), 1, 1),
			"NotFound":   "这个游戏已经不在了，可能被移动或删除。",
			"GradeLabel": textbook.GradeLabel(textbook.NormalizeStage(s.Stage), 1),
			"Grade":      1,
			"Volume":     1,
		})
		return
	}
	a.html(c, "game.html", gin.H{
		"Title":  g.Title,
		"Nav":    "study",
		"Game":   g,
		"Lesson": nil, // 不给壁纸按学科匹配，走通用壁纸逻辑
	})
}

// gameRaw 原样输出游戏 HTML。
//
// 三件事，都很克制：
//  1. 路径白名单：key 必须命中已索引的游戏，绝不接受任意路径参数，
//     杜绝 ../ 穿越读取项目里的其它文件。
//  2. 注入主题：游戏 HTML 是离线产物，不会知道 StudyBuddy 当前是深色还是浅色。
//     这里在 </head> 前插一小段 <style>，把父页面的 data-theme 值
//     以 CSS 变量的形式喂给游戏，游戏侧只需写 var(--g-bg) 即可自动跟随。
//  3. 注入返回条的游戏侧样式：返回按钮由主页面提供（iframe 外层），
//     但游戏内也要有一致的配色变量，否则浅色游戏放进深色页面会很刺眼。
func (a *App) gameRaw(c *gin.Context) {
	g := games.Find(c.Query("key"))
	if g == nil {
		c.Status(http.StatusNotFound)
		return
	}
	b, err := os.ReadFile(g.Path)
	if err != nil {
		c.Status(http.StatusNotFound)
		return
	}
	html := string(b)
	theme := themeModeFromCookie(c)
	if css := gameThemeBridgeCSS(theme); css != "" {
		html = injectBeforeHead(html, "<style id=\"sb-theme-bridge\">\n"+css+"\n</style>")
	}
	html = injectHTMLAttr(html, "data-theme", theme)
	c.Header("Content-Type", "text/html; charset=utf-8")
	// 游戏是离线静态产物，但开发时会反复改：no-cache 让刷新即见新版。
	c.Header("Cache-Control", "private, no-cache")
	c.String(http.StatusOK, html)
}

// injectHTMLAttr 给文档的 <html> 标签写入一个属性。
//
// 为什么必须写属性而不只是给 CSS 变量：游戏是 iframe 里的**独立文档**，
// 拿不到父页面的 data-theme。若只注入变量、规则写成 [data-theme="dark"]，
// 手动切到深色时游戏就永远匹配不上；而写属性后，媒体查询与属性选择器
// 两条路都通，游戏作者用哪种写法都能跟随。
//
// theme 为空（跟随系统）时不写属性：此时 HTML 上没有 data-theme，
// 游戏内的 @media (prefers-color-scheme: dark) 与 html:not([data-theme="light"])
// 会自然跟随系统，与父页面行为一致。
func injectHTMLAttr(html, name, val string) string {
	if val == "" {
		return html
	}
	// 只看文档里第一个 <html ...>；用正则而不是逐个解析，因为游戏文件都是
	// 手写模板，标签形态不统一（有无换行、有无其它属性都可能）。
	i := strings.Index(strings.ToLower(html), "<html")
	if i < 0 {
		return html
	}
	j := strings.IndexAny(html[i:], ">")
	if j < 0 {
		return html
	}
	tag := html[i : i+j]
	if strings.Contains(strings.ToLower(tag), name+"=") {
		return html // 已有该属性（游戏自己写了），不覆盖
	}
	return html[:i] + tag + " " + name + `="` + val + `"` + html[i+j:]
}

// gameThemeBridgeCSS 生成主题桥接样式。
//
// 只给变量、不写选择器：游戏作者在 CSS 里写 var(--g-bg, #fff) 即可，
// 有 fallback 意味着即使这份桥接没注入（直接双击 HTML 打开）也能正常显示。
func gameThemeBridgeCSS(theme string) string {
	if theme != "dark" && theme != "light" {
		// 跟随系统：桥接只声明「跟随系统」的那一套，由 iframe 内的媒体查询决定。
		return "@media (prefers-color-scheme: dark){:root{" +
			"--g-bg:#151a21;--g-card:#1c222b;--g-ink:#e7ecf3;--g-muted:#9aa7b6;--g-line:#2a323d;" +
			"--g-brand:#4ea1ff;--g-brand-soft:#16273c;--g-ok:#5fbf6a;--g-bad:#ff6b6b;--g-warn:#ffa040;}}"
	}
	if theme == "light" {
		return ":root{" +
			"--g-bg:#f4f7fb;--g-card:#ffffff;--g-ink:#1f2937;--g-muted:#6b7a8d;--g-line:#e3e9f1;" +
			"--g-brand:#2f6fd0;--g-brand-soft:#e8f1fd;--g-ok:#2e9e5b;--g-bad:#d64545;--g-warn:#e08b00;}"
	}
	return ":root{" +
		"--g-bg:#151a21;--g-card:#1c222b;--g-ink:#e7ecf3;--g-muted:#9aa7b6;--g-line:#2a323d;" +
		"--g-brand:#4ea1ff;--g-brand-soft:#16273c;--g-ok:#5fbf6a;--g-bad:#ff6b6b;--g-warn:#ffa040;}"
}

// injectBeforeHead 在 </head> 前插入一段 HTML；找不到 </head> 时追加到文档末尾。
//
// 用 strings.LastIndex 而不是 Replace：游戏 HTML 可能含多个 </head>（复制粘贴的片段），
// 只替换最后一个能保证样式在文档结构里处于它该在的位置。
func injectBeforeHead(html, inject string) string {
	if i := strings.LastIndex(strings.ToLower(html), "</head>"); i >= 0 {
		return html[:i] + inject + "\n" + html[i:]
	}
	return html + "\n" + inject
}
