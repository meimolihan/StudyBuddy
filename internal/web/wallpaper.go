package web

import (
	"io/fs"
	"net/http"
	"os"
	"path"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"

	"github.com/gin-gonic/gin"

	"studybuddy/internal/auth"
	"studybuddy/internal/textbook"
)

// 背景壁纸系统：首页按「学段 + 年级」匹配一张背景图（同一张图上下册共用）；
// 进入某个学科（课程页 / 在线自测页 / 自测结果页）时，才按「学段 + 年级 + 册别 + 学科」
// 精准匹配该册该学科的专属图。
//
// 放置位置（两处都认，运行时目录优先、同名覆盖内置）：
//
//  1. <项目根>/wallpapers/              推荐：放进去刷新页面即生效，无需重新编译
//  2. internal/web/static/wallpapers/   会随 go:embed 打进二进制，改动后必须重新编译
//
// 目录结构刻意与教材内容树 content/ 保持一致（学段 → 出版社 → 年级 → 册别），
// 「年级层」放首页通用图（该年级上下册共用一张），「册别层」放学科图。
// 两者对照着看，一眼就能知道该往哪儿放：
//
//	content/primary/pep/grade4/volume1/chinese/01-…/01-….html
//	wallpapers/primary/pep/grade4/wallpaper.webp               ← 四年级通用（首页用，上下册共用）
//	wallpapers/primary/pep/grade4/volume1/g4-v1-chinese.webp   ← 四年级上册 · 语文（自测页用）
//	wallpapers/primary/pep/grade4/volume1/g4-v1-math.webp      ← 四年级上册 · 数学
//	wallpapers/primary/pep/grade4/volume2/g4-v2-chinese.webp   ← 四年级下册 · 语文
//
// 高考复习专题（content 里 grade{N}/review/ 目录的课）的壁纸放在 review 目录里，
// 命名用 h{N}-{学科}（高中）或 g{N}-review-{学科}：
//
//	content/high/pep/grade3/review/chinese/01-….html
//	wallpapers/high/pep/grade3/review/h3-chinese.webp          ← 高三高考复习 · 语文
//	wallpapers/high/pep/grade3/review/wallpaper.webp           ← 高考复习通用图（回退）
//	wallpapers/high/pep/grade3/wallpaper.webp                  ← 年级通用图（再回退）
//
// 高中的学科图也支持 h{N} 简写：h3-v1-chinese.webp 等价于 g3-v1-chinese.webp。
//
// 匹配规则（一句话：首页只到「年级」这一层，学科页才下到「册别 + 学科」）：
//
//	学习主页 / 试卷归档 / 用户管理等页面  →  用年级层通用图 grade4/wallpaper.webp
//	                                       （同一年级上下册共用同一张）；
//	                                       该文件缺失时，回退到册别图（兼容旧部署），
//	                                       最后才走全局兜底（default.webp）
//	课程页 / 在线自测页 / 结果页         →  先试该册该学科的专属图（g4-v1-chinese），
//	                                       没有再退回同一册的通用图（volume1/wallpaper.webp），
//	                                       再退到年级通用图（grade4/wallpaper.webp），
//	                                       最后才走全局兜底（default.webp）
//
// 即四年级上册语文的自测页依次找：
//
//	…/grade4/volume1/g4-v1-chinese.webp   指定学科图（推荐命名：g{年级}-v{册别}-{学科}）
//	…/grade4/volume1/wallpaper.webp       该册通用图
//	…/grade4/wallpaper.webp               该年级通用图（首页那张）
//	…（更宽泛的目录层，规则同上，学科名仍然优先）
//	wallpapers/default.webp               全局兜底（根目录）
//
// 文件名本身也可以「升级」成目录层，越具体越优先：
//
//	wallpapers/primary/pep/grade4/wallpaper.webp           ← 首页图：推荐
//	wallpapers/primary/pep/grade4/g4.webp                  ← 同目录内的别名
//	wallpapers/primary/grade4/wallpaper.webp               ← 省略出版社这一层
//	wallpapers/primary/pep/grade4/volume1/wallpaper.webp   ← 学科页的册别图：推荐
//	wallpapers/primary/pep/grade4/volume1/g4-v1.webp       ← 同目录内的别名
//	wallpapers/g4-v1.webp                                  ← 老式平铺写法，仍然兼容
//
// 查找顺序（首页：先「年级层 × 通用名」再「册别层 × 通用名」再根目录平铺；
// 学科页：先「学科名 × 全部目录层」，再「通用名 × 全部目录层」。
// 学科名依次尝试 primary-g4-v1-chinese → g4-v1-chinese → primary-v1-chinese →
// v1-chinese → wallpaper-chinese → chinese，通用名依次尝试 wallpaper →
// primary-g4-v1 → g4-v1 → primary-v1 → v1 → default，年级层另用
// wallpaper → primary-g4 → g4；
// 扩展名依次尝试 .webp / .png / .jpg / .jpeg / .avif / .gif）：
//
//	首页（与学科无关）：           学科页：
//	{学段}/{出版社}/grade{N}/        {学段}/{出版社}/grade{N}/volume{N}/   最精确
//	{学段}/grade{N}/                 {学段}/grade{N}/volume{N}/
//	{学段}/{出版社}/grade{N}/volume{N}/（回退）  {学段}/{出版社}/grade{N}/
//	{学段}/grade{N}/volume{N}/（回退）  {学段}/grade{N}/
//	{学段}/{出版社}/                 {学段}/{出版社}/
//	{学段}/                          {学段}/
//	（wallpapers/ 根目录，即老式平铺写法；两侧相同）
//
// 其中 N 是「学段内序号」：小学 1~6、中学 / 高中 1~3；册别 1 = 上册、2 = 下册。
// 学科名取教材目录名：chinese / math / english / morallaw / science。
const (
	wallpaperRuntimeDir = "wallpapers"        // 运行时目录名（相对项目根）
	wallpaperEmbedDir   = "static/wallpapers" // 内置资源目录（相对 static）
	wallpaperURLPrefix  = "/wallpapers/"      // 对外 URL 前缀

	// wallpaperMaxDepth 相对路径的最大层数：primary/pep/grade4/volume1/wallpaper.webp 正好 5 层。
	wallpaperMaxDepth = 5

	// wallpaperDefaultPublisher 目录树里一个出版社目录都没有时，提示语里默认带的出版社。
	wallpaperDefaultPublisher = "pep"

	// WallpaperOff 壁纸开关的持久化取值："" = 显示，WallpaperOff = 关闭。
	WallpaperOff = "off"
)

// wallpaperExts 依次尝试的图片扩展名。
var wallpaperExts = []string{".webp", ".png", ".jpg", ".jpeg", ".avif", ".gif"}

// 目录名 / 文件名白名单：必须以字母或数字开头，只含字母 / 数字 / 点 / 下划线 / 连字符。
// 从根上杜绝 "../" 之类的路径穿越（"." 与 ".." 都不满足「字母数字开头」）。
var wallpaperNameOK = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9._-]*$`)

// wallpaperStage 归一化学段；留空时按小学处理（与注册表单的默认值保持一致）。
func wallpaperStage(stage string) string {
	if s := textbook.NormalizeStage(stage); s != "" {
		return s
	}
	return textbook.StagePrimary
}

// normalizeVolume 册别归一化：2 表示下册，VolReview 表示高考复习，其余一律按上册。
func normalizeVolume(volume int) int {
	if volume == 2 || volume == textbook.VolReview {
		return volume
	}
	return 1
}

// clampWallpaper 把年级 / 册别夹到合法范围（小学 6 个年级、中学 / 高中 3 个）。
func clampWallpaper(stage string, grade, volume int) (int, int) {
	if grade < 1 {
		grade = 1
	}
	if n := textbook.GradeCount(stage); n > 0 && grade > n {
		grade = n
	}
	return grade, normalizeVolume(volume)
}

// wallpaperImageExt 判断是否为受支持的图片扩展名（目录里的其它文件一律忽略）。
func wallpaperImageExt(name string) bool {
	ext := strings.ToLower(filepath.Ext(name))
	for _, e := range wallpaperExts {
		if e == ext {
			return true
		}
	}
	return false
}

// ---- 目录扫描 ----

// walkWallpapers 递归遍历壁纸目录，把每个图片文件的相对路径交给 add（/ 分隔）。
// override 为真时（运行时目录）允许覆盖已登记的同名项。
func walkWallpapers(fsys fs.FS, add func(rel string, override bool), override bool) {
	var walk func(prefix string, depth int)
	walk = func(prefix string, depth int) {
		if depth >= wallpaperMaxDepth {
			return // 再深就不可能是壁纸了，不往下走
		}
		dir := "."
		if prefix != "" {
			dir = prefix
		}
		ents, err := fs.ReadDir(fsys, dir)
		if err != nil {
			return
		}
		for _, e := range ents {
			name := e.Name()
			if !wallpaperNameOK.MatchString(name) {
				continue
			}
			rel := name
			if prefix != "" {
				rel = prefix + "/" + name
			}
			if e.IsDir() {
				walk(rel, depth+1)
				continue
			}
			if wallpaperImageExt(name) {
				add(rel, override)
			}
		}
	}
	walk("", 0)
}

// wallpaperIndex 扫描全部可用壁纸，返回「小写相对路径 → 真实相对路径」。
// 运行时目录优先，同名时覆盖内置资源。
func (a *App) wallpaperIndex() map[string]string {
	idx := map[string]string{}
	add := func(rel string, override bool) {
		segs := strings.Split(rel, "/")
		if len(segs) == 0 || len(segs) > wallpaperMaxDepth {
			return
		}
		for _, s := range segs {
			if !wallpaperNameOK.MatchString(s) {
				return
			}
		}
		key := strings.ToLower(rel)
		if _, dup := idx[key]; dup && !override {
			return
		}
		idx[key] = rel
	}

	if dir := a.wallpaperDir(); dir != "" {
		walkWallpapers(os.DirFS(dir), add, true)
	}
	if a.assets != nil {
		if sub, err := fs.Sub(a.assets, wallpaperEmbedDir); err == nil {
			walkWallpapers(sub, add, false)
		}
	}
	return idx
}

// wallpaperDir 运行时壁纸目录的绝对路径；无法确定时返回空串。
func (a *App) wallpaperDir() string {
	if a.Cfg == nil || a.Cfg.BaseDir == "" {
		return ""
	}
	return filepath.Join(a.Cfg.BaseDir, wallpaperRuntimeDir)
}

// wallpaperPublishers 列出某学段下已存在的「出版社」目录名（镜像 content/ 的第二层）。
// 账号里并不存出版社，所以这里按目录实际存在的名字依次尝试；只有一个时结果唯一。
func (a *App) wallpaperPublishers(stage string) []string {
	seen := map[string]bool{}
	grab := func(fsys fs.FS) {
		ents, err := fs.ReadDir(fsys, stage)
		if err != nil {
			return // 该学段目录还不存在，正常
		}
		for _, e := range ents {
			if e.IsDir() && wallpaperNameOK.MatchString(e.Name()) {
				seen[e.Name()] = true
			}
		}
	}
	if dir := a.wallpaperDir(); dir != "" {
		grab(os.DirFS(dir))
	}
	if a.assets != nil {
		if sub, err := fs.Sub(a.assets, wallpaperEmbedDir); err == nil {
			grab(sub)
		}
	}
	out := make([]string, 0, len(seen))
	for k := range seen {
		out = append(out, k)
	}
	sort.Strings(out) // 多个出版社时结果稳定，不随目录遍历顺序变化
	return out
}

// ---- 匹配 ----

// wallpaperGenericAliases 通用文件名（不含扩展名），与学科无关。
// 顺序即优先级：推荐的 wallpaper 在最前，其余依次放宽。
// 高中额外支持 h{N} 简写（h3-v1 = 高三上册，与实际放置习惯一致）。
func wallpaperGenericAliases(st, gs, vs string) []string {
	out := []string{
		"wallpaper",
		st + "-g" + gs + "-v" + vs,
		"g" + gs + "-v" + vs,
	}
	if st == textbook.StageHigh {
		out = append(out, "h"+gs+"-v"+vs)
	}
	return append(out, st+"-v"+vs, "v"+vs, "default")
}

// wallpaperGradeAliases 年级层（不含册别）的通用文件名，顺序即优先级。
// 首页只用这一组名字，所以放在 grade{N}/ 目录里的图天然上下册共用。
func wallpaperGradeAliases(st, gs string) []string {
	out := []string{
		"wallpaper",
		st + "-g" + gs,
		"g" + gs,
	}
	if st == textbook.StageHigh {
		out = append(out, "h"+gs)
	}
	return out
}

// wallpaperSubjectAliases 学科专用文件名（不含扩展名），仅当 subject 合法时返回。
// 推荐命名是 g{N}-v{V}-{学科}，如 g4-v1-chinese.webp；高中另支持 h{N} 简写
// （h3-v1-chinese.webp），与用户实际放置习惯一致。
func wallpaperSubjectAliases(st, gs, vs, subject string) []string {
	if subject == "" || !wallpaperNameOK.MatchString(subject) {
		return nil
	}
	out := []string{
		st + "-g" + gs + "-v" + vs + "-" + subject, // primary-g4-v1-chinese
		"g" + gs + "-v" + vs + "-" + subject,       // g4-v1-chinese ← 推荐
	}
	if st == textbook.StageHigh {
		out = append(out, "h"+gs+"-v"+vs+"-"+subject) // h3-v1-chinese（高中简写）
	}
	return append(out,
		st+"-v"+vs+"-"+subject, // primary-v1-chinese
		"v"+vs+"-"+subject,     // v1-chinese
		"wallpaper-"+subject,   // wallpaper-chinese
		subject,                // chinese
	)
}

// wallpaperReviewDirs 高考复习专题（grade{N}/review 层）的候选目录，由具体到宽泛：
// 出版社/年级/review → 年级/review → 出版社/年级 → 年级 → 出版社 → 学段。
// 年级及更宽泛的层用来回退到通用图（grade{N}/wallpaper.webp 等）。
func (a *App) wallpaperReviewDirs(st, gs string) []string {
	gDir := "grade" + gs
	pubs := a.wallpaperPublishersOf(st)
	dirs := make([]string, 0, len(pubs)*4+4)
	withPub := func(parts ...string) {
		for _, p := range pubs {
			dirs = append(dirs, strings.Join(append([]string{st, p}, parts...), "/"))
		}
	}
	withPub(gDir, "review")
	dirs = append(dirs, st+"/"+gDir+"/review")
	withPub(gDir)
	dirs = append(dirs, st+"/"+gDir)
	withPub()
	dirs = append(dirs, st)
	return dirs
}

// wallpaperReviewSubjectAliases 高考复习专题的学科文件名（不含扩展名）。
// 推荐命名 h{N}-{学科}（如 h3-chinese.webp，放在 grade{N}/review/ 目录里）；
// 也兼容带 review 的全写形式。
func wallpaperReviewSubjectAliases(st, gs, subject string) []string {
	if subject == "" || !wallpaperNameOK.MatchString(subject) {
		return nil
	}
	out := []string{
		st + "-g" + gs + "-review-" + subject, // high-g3-review-chinese
		"g" + gs + "-review-" + subject,       // g3-review-chinese
	}
	if st == textbook.StageHigh {
		out = append(out,
			"h"+gs+"-review-"+subject, // h3-review-chinese
			"h"+gs+"-"+subject,        // h3-chinese ← 推荐
		)
	}
	return append(out,
		"wallpaper-"+subject, // wallpaper-chinese
		subject,              // chinese
	)
}

// wallpaperReviewGenericAliases 高考复习专题的通用文件名（不含扩展名）。
func wallpaperReviewGenericAliases(st, gs string) []string {
	out := []string{
		"wallpaper",
		st + "-g" + gs + "-review",
		"g" + gs + "-review",
		st + "-g" + gs,
		"g" + gs,
	}
	if st == textbook.StageHigh {
		out = append(out, "h"+gs+"-review", "h"+gs)
	}
	return append(out, "default")
}

// wallpaperPublishersOf 列出可用的出版社目录名；一个都没有（目录还没建）时给出标准答案，
// 这样「推荐路径」仍然能完整地提示到 {学段}/{出版社}/grade{N}/…。
func (a *App) wallpaperPublishersOf(st string) []string {
	pubs := a.wallpaperPublishers(st)
	if len(pubs) == 0 {
		return []string{wallpaperDefaultPublisher}
	}
	return pubs
}

// wallpaperDirs 含册别的目录层，由具体到宽泛（镜像 content/：学段 / 出版社 / 年级 / 册别）。
func (a *App) wallpaperDirs(st, gs, vs string) []string {
	gDir, vDir := "grade"+gs, "volume"+vs
	pubs := a.wallpaperPublishersOf(st)
	dirs := make([]string, 0, len(pubs)*3+3)
	withPub := func(parts ...string) {
		for _, p := range pubs {
			dirs = append(dirs, strings.Join(append([]string{st, p}, parts...), "/"))
		}
	}
	withPub(gDir, vDir)
	dirs = append(dirs, st+"/"+gDir+"/"+vDir)
	withPub(gDir)
	dirs = append(dirs, st+"/"+gDir)
	withPub()
	dirs = append(dirs, st)
	return dirs
}

// wallpaperGradeDirs 只到「年级」这一层（不含册别）的目录层，由具体到宽泛。
// 首页用这一组目录：同一年级上下册共用同一张图。
func (a *App) wallpaperGradeDirs(st, gs string) []string {
	gDir := "grade" + gs
	pubs := a.wallpaperPublishersOf(st)
	dirs := make([]string, 0, len(pubs)+2)
	for _, p := range pubs {
		dirs = append(dirs, st+"/"+p+"/"+gDir)
	}
	return append(dirs, st+"/"+gDir)
}

// WallpaperCandidates 返回按优先级排列的候选相对路径（不含扩展名），供排查问题时使用。
func (a *App) WallpaperCandidates(stage string, grade, volume int) []string {
	return a.WallpaperCandidatesFor(stage, grade, volume, "")
}

// WallpaperCandidatesFor 生成候选相对路径（不含扩展名）。
//
// subject 为空（学习主页 / 试卷归档 / 用户管理等与学科无关的页面）时走「年级优先」：
// 先试年级层（grade4/wallpaper.webp，上下册共用同一张），命不中再回退册别层，
// 保证只放了册别图的旧部署不会突然没有背景。
//
// subject 非空（课程页 / 在线自测页 / 结果页）时走「学科优先」：先把学科名 × 全部目录层
// （含册别）走完，再走通用名 × 全部目录层 —— 于是学科图永远优先于册别通用图
// （哪怕学科图放在更宽泛的目录里，也仍然优先），而同类之间目录越具体越优先。
//
// 两者都以根目录的老式平铺名（g4-v1 / default）收尾。
func (a *App) WallpaperCandidatesFor(stage string, grade, volume int, subject string) []string {
	grade, volume = clampWallpaper(stage, grade, volume)
	st := wallpaperStage(stage)
	gs, vs := strconv.Itoa(grade), strconv.Itoa(volume)

	subject = strings.ToLower(strings.TrimSpace(subject))
	if !wallpaperNameOK.MatchString(subject) {
		subject = "" // 非法学科名直接忽略，避免拼出奇怪的候选路径
	}
	if volume == textbook.VolReview {
		return a.wallpaperCandidatesReview(st, gs, subject)
	}
	subNames := wallpaperSubjectAliases(st, gs, vs, subject)
	genNames := wallpaperGenericAliases(st, gs, vs)
	if len(subNames) == 0 {
		return a.wallpaperCandidatesGrade(st, gs, vs, genNames)
	}

	dirs := a.wallpaperDirs(st, gs, vs)
	out := make([]string, 0, (len(dirs)*2+2)*(len(subNames)+len(genNames)))
	// 第一轮：学科专用名 —— 目录层由具体到宽泛，最后是根目录的平铺学科名。
	for _, d := range dirs {
		for _, n := range subNames {
			out = append(out, d+"/"+n)
		}
	}
	// 根目录（老式平铺写法）：这里没有年级信息，故不接受裸学科名（chinese.webp），
	// 避免出现语义不明的「全局语文图」；带年级 / 册别的平铺名（g4-v1-chinese）仍然认。
	for _, n := range subNames {
		if n != subject {
			out = append(out, n)
		}
	}
	// 第二轮：通用名 —— 同样目录层由具体到宽泛，最后是根目录的平铺通用名。
	for _, d := range dirs {
		for _, n := range genNames {
			out = append(out, d+"/"+n)
		}
	}
	// 根目录不接受裸的 "wallpaper"，全局兜底统一用 default。
	for _, n := range genNames[1:] {
		out = append(out, n)
	}
	return out
}

// wallpaperCandidatesReview 高考复习专题（grade{N}/review 目录）的候选顺序，
// 与学科页一致：先「学科名 × 目录层」（review 层 → 年级层），再「通用名 × 目录层」，
// 最后是根目录平铺（不带裸学科名 / 裸 wallpaper）。
func (a *App) wallpaperCandidatesReview(st, gs, subject string) []string {
	subNames := wallpaperReviewSubjectAliases(st, gs, subject)
	genNames := wallpaperReviewGenericAliases(st, gs)
	dirs := a.wallpaperReviewDirs(st, gs)
	out := make([]string, 0, (len(dirs)+1)*(len(subNames)+len(genNames)))
	// 第一轮：学科专用名 —— 目录层由具体到宽泛。
	for _, d := range dirs {
		for _, n := range subNames {
			out = append(out, d+"/"+n)
		}
	}
	// 根目录平铺：这里没有年级信息，不接受裸学科名。
	for _, n := range subNames {
		if n != subject {
			out = append(out, n)
		}
	}
	// 第二轮：通用名 —— 依次回退到年级通用图（gradeN/wallpaper.webp）。
	for _, d := range dirs {
		for _, n := range genNames {
			out = append(out, d+"/"+n)
		}
	}
	// 根目录不接受裸的 "wallpaper"，全局兜底统一用 default。
	for _, n := range genNames[1:] {
		out = append(out, n)
	}
	return out
}

// wallpaperCandidatesGrade 首页（无学科）的候选顺序：年级层 → 册别层（回退）→ 根目录平铺。
func (a *App) wallpaperCandidatesGrade(st, gs, vs string, genNames []string) []string {
	gradeNames := wallpaperGradeAliases(st, gs)
	out := make([]string, 0, 16)
	for _, d := range a.wallpaperGradeDirs(st, gs) {
		for _, n := range gradeNames {
			out = append(out, d+"/"+n)
		}
	}
	for _, d := range a.wallpaperDirs(st, gs, vs) {
		for _, n := range genNames {
			out = append(out, d+"/"+n)
		}
	}
	// 根目录不接受裸的 "wallpaper"，全局兜底统一用 default。
	for _, n := range genNames[1:] {
		out = append(out, n)
	}
	return out
}

// WallpaperName 返回匹配到的壁纸相对路径（含扩展名，/ 分隔）；未匹配到返回空串。
func (a *App) WallpaperName(stage string, grade, volume int) string {
	return a.WallpaperNameFor(stage, grade, volume, "")
}

// WallpaperNameFor 同上，但可指定学科：学科图优先，缺失时自动退回通用图与全局兜底。
func (a *App) WallpaperNameFor(stage string, grade, volume int, subject string) string {
	idx := a.wallpaperIndex()
	if len(idx) == 0 {
		return ""
	}
	for _, base := range a.WallpaperCandidatesFor(stage, grade, volume, subject) {
		for _, ext := range wallpaperExts {
			if real, ok := idx[strings.ToLower(base+ext)]; ok {
				return real
			}
		}
	}
	return ""
}

// WallpaperURL 匹配到则返回可直接放进 <img src> 的站内路径，否则空串。
func (a *App) WallpaperURL(stage string, grade, volume int) string {
	return a.WallpaperURLFor(stage, grade, volume, "")
}

// WallpaperURLFor 同上，学科专用版本。
func (a *App) WallpaperURLFor(stage string, grade, volume int, subject string) string {
	if name := a.WallpaperNameFor(stage, grade, volume, subject); name != "" {
		return wallpaperURLPrefix + name
	}
	return ""
}

// WallpaperSuggest 返回该组合「推荐使用」的相对路径（含扩展名），用于界面提示与文档。
func (a *App) WallpaperSuggest(stage string, grade, volume int) string {
	return a.WallpaperSuggestFor(stage, grade, volume, "")
}

// WallpaperSuggestFor 同上；带学科时推荐 g{年级}-v{册别}-{学科}.webp（放在册别目录里），
// 不带学科时推荐年级目录下的 wallpaper.webp —— 首页图不分上下册，整个年级共用一张。
func (a *App) WallpaperSuggestFor(stage string, grade, volume int, subject string) string {
	grade, volume = clampWallpaper(stage, grade, volume)
	st := wallpaperStage(stage)

	pub := ""
	switch pubs := a.wallpaperPublishers(st); {
	case len(pubs) == 1:
		pub = pubs[0]
	case len(pubs) == 0:
		pub = wallpaperDefaultPublisher // 目录还没建时，按教材的出版社给个标准答案
	}

	parts := []string{st}
	if pub != "" {
		parts = append(parts, pub)
	}
	gs, vs := strconv.Itoa(grade), strconv.Itoa(volume)
	if s := strings.ToLower(strings.TrimSpace(subject)); wallpaperNameOK.MatchString(s) {
		if volume == textbook.VolReview {
			// 高考复习学科图放在 review 目录里：…/grade3/review/h3-chinese.webp
			name := "g" + gs + "-review-" + s
			if st == textbook.StageHigh {
				name = "h" + gs + "-" + s // 高中简写：h3-chinese
			}
			parts = append(parts, "grade"+gs, "review", name+".webp")
			return strings.Join(parts, "/")
		}
		// 学科图放在册别目录里：…/grade4/volume1/g4-v1-chinese.webp
		parts = append(parts, "grade"+gs, "volume"+vs, "g"+gs+"-v"+vs+"-"+s+".webp")
		return strings.Join(parts, "/")
	}
	// 首页图只到年级这一层：…/grade4/wallpaper.webp（上下册共用同一张）
	parts = append(parts, "grade"+gs, "wallpaper.webp")
	return strings.Join(parts, "/")
}

// wallpaperDirHasVolume 判断目录层里是否带册别（volume{N}），
// 用来区分「年级通用图（上下册共用）」与「册别图」。
func wallpaperDirHasVolume(dir string) bool {
	for _, seg := range strings.Split(dir, "/") {
		if strings.HasPrefix(seg, "volume") {
			return true
		}
	}
	return false
}

// wallpaperPanelLabel 顶栏主题面板里显示的简短说明：
//   - 年级通用图（wallpaper.webp 且目录里没有册别）显示「所在目录 · 上下册共用」；
//   - 册别通用图只显示所在目录，一眼看出是哪一册；
//   - 学科图显示「学科 · 所在目录」，一眼看出是哪一册哪个学科；
//   - 其它自定义文件名显示文件名本身。
func wallpaperPanelLabel(rel, subjectCN string) string {
	if rel == "" {
		return ""
	}
	slash := filepath.ToSlash(rel)
	dir, base := path.Dir(slash), path.Base(slash)
	if dir == "." {
		return base
	}
	if subjectCN != "" {
		return subjectCN + " · " + dir
	}
	if strings.HasPrefix(strings.ToLower(base), "wallpaper.") {
		if !wallpaperDirHasVolume(dir) {
			return dir + " · 上下册共用"
		}
		return dir
	}
	return base
}

// ---- 路由处理 ----

// wallpaperFile 提供壁纸图片：先查运行时目录，再回退内置资源。
// 只允许提供「索引里登记过的相对路径」，因此不可能读到壁纸目录之外的任何文件。
func (a *App) wallpaperFile(c *gin.Context) {
	rel := strings.Trim(c.Param("path"), "/")
	segs := strings.Split(rel, "/")
	if rel == "" || len(segs) > wallpaperMaxDepth {
		c.Status(http.StatusNotFound)
		return
	}
	for _, s := range segs {
		if !wallpaperNameOK.MatchString(s) {
			c.Status(http.StatusNotFound) // "../" 之类在这里就被挡掉
			return
		}
	}
	real, ok := a.wallpaperIndex()[strings.ToLower(rel)]
	if !ok {
		c.Status(http.StatusNotFound)
		return
	}

	if dir := a.wallpaperDir(); dir != "" {
		if base, err := filepath.Abs(dir); err == nil {
			p := filepath.Join(base, filepath.FromSlash(real))
			// 双保险：索引只收录扫描到的相对路径，这里再确认一次没跑出壁纸目录。
			if strings.HasPrefix(p, base+string(filepath.Separator)) {
				if st, err2 := os.Stat(p); err2 == nil && !st.IsDir() {
					c.Header("Content-Type", wallpaperContentType(real))
					c.Header("Cache-Control", "public, max-age=600")
					http.ServeFile(c.Writer, c.Request, p)
					return
				}
			}
		}
	}
	if a.assets != nil {
		if b, err := fs.ReadFile(a.assets, wallpaperEmbedDir+"/"+real); err == nil {
			c.Header("Cache-Control", "public, max-age=600")
			c.Data(http.StatusOK, wallpaperContentType(real), b)
			return
		}
	}
	c.Status(http.StatusNotFound)
}

// wallpaperContentType 按扩展名给出 MIME（Go 内置表不一定认识 webp / avif）。
func wallpaperContentType(name string) string {
	switch strings.ToLower(filepath.Ext(name)) {
	case ".webp":
		return "image/webp"
	case ".png":
		return "image/png"
	case ".jpg", ".jpeg":
		return "image/jpeg"
	case ".avif":
		return "image/avif"
	case ".gif":
		return "image/gif"
	default:
		return "application/octet-stream"
	}
}

// wallpaperLookup 给前端用（注册页实时预览）：按当前选的学段 / 年级 / 册别查匹配结果。
// 可选 subject（chinese / math / …）：带上时按学科图优先匹配，行为与自测页一致；
// 不带时按首页规则查（只到年级这一层，上下册共用同一张图）。
func (a *App) wallpaperLookup(c *gin.Context) {
	stage := c.Query("stage")
	grade, _ := strconv.Atoi(c.Query("grade"))
	volume, _ := strconv.Atoi(c.Query("volume"))
	if grade < 1 {
		grade = 1
	}
	if grade > 12 {
		grade = 12
	}
	grade, vol := clampWallpaper(stage, grade, volume)
	subject := strings.ToLower(strings.TrimSpace(c.Query("subject")))
	if !wallpaperNameOK.MatchString(subject) {
		subject = ""
	}
	name := a.WallpaperNameFor(stage, grade, vol, subject)
	url := ""
	if name != "" {
		url = wallpaperURLPrefix + name
	}
	c.Header("Cache-Control", "no-store")
	c.JSON(http.StatusOK, gin.H{
		"matched": name != "",
		"name":    name,
		"url":     url,
		"want":    a.WallpaperSuggestFor(stage, grade, vol, subject),
		"stage":   wallpaperStage(stage),
		"grade":   grade,
		"volume":  vol,
		"subject": subject,
		"label":   wallpaperLabelCN(stage, grade, vol),
	})
}

// setWallpaperOnOff 学生自行开关背景壁纸（背景太花时可一键关掉，也可以再点一下开回来）。
// 开关状态存在 users.wallpaper，并同步写回内存会话，当前请求之后立即生效。
func (a *App) setWallpaperOnOff(c *gin.Context) {
	s := auth.Current(c)
	if s == nil {
		// 会话过期后又点了设置面板里的开关：回登录页，不要在这里 500。
		c.Redirect(http.StatusSeeOther, "/login")
		return
	}
	val := ""
	if c.Query("on") == "0" {
		val = WallpaperOff
	}
	if err := a.Global.SetWallpaper(s.UserID, val); err == nil {
		s.Wallpaper = val // 同步内存会话，当前请求后立刻生效
	}
	back := c.Query("back")
	if !strings.HasPrefix(back, "/") || strings.HasPrefix(back, "//") {
		back = "/study" // 防开放重定向：只接受站内相对路径
	}
	c.Redirect(http.StatusSeeOther, back)
}

// wallpaperLabelCN 生成「小学 · 四年级 · 上册」这类可读描述。
func wallpaperLabelCN(stage string, grade, volume int) string {
	parts := []string{}
	switch wallpaperStage(stage) {
	case textbook.StagePrimary:
		parts = append(parts, "小学")
	case textbook.StageMiddle:
		parts = append(parts, "中学")
	case textbook.StageHigh:
		parts = append(parts, "高中")
	}
	if g := textbook.GradeLabel(stage, grade); g != "" {
		parts = append(parts, g)
	}
	if volume == textbook.VolReview {
		parts = append(parts, "高考复习")
	} else if normalizeVolume(volume) == 2 {
		parts = append(parts, "下册")
	} else {
		parts = append(parts, "上册")
	}
	return strings.Join(parts, " · ")
}

// resolveWallpaperFor 由会话（+ 可选的当前课程）推导当前生效的壁纸。
//
// lesson 非空表示当前页面属于某个具体学科（课程页 / 在线自测页 / 自测结果页），
// 此时按该课的「学段 + 年级 + 册别 + 学科」精准匹配，学科图缺失会逐级退回该册通用图、
// 该年级通用图、全局兜底；lesson 为空（学习主页、试卷归档、用户管理等）则只按学籍的
// 「学段 + 年级」匹配年级通用图 —— 同一年级上下册共用同一张背景。
// 关闭开关（WallpaperOff）时一律不输出。
func (a *App) resolveWallpaperFor(s *auth.Session, lesson *textbook.Lesson) (url, name, want string, off bool) {
	if s == nil {
		return "", "", "", false
	}
	off = s.Wallpaper == WallpaperOff

	stage, grade, volume, subject := s.Stage, s.Grade, s.Volume, ""
	if lesson != nil {
		// 以课程自身携带的学段 / 年级 / 册别 / 学科为准，比学生学籍更精确。
		if textbook.NormalizeStage(lesson.Stage) != "" {
			stage = lesson.Stage
		}
		if lesson.Grade > 0 {
			grade = lesson.Grade
		}
		if lesson.Volume > 0 {
			volume = lesson.Volume
		}
		subject = lesson.Subject
	}

	name = a.WallpaperNameFor(stage, grade, volume, subject)
	want = a.WallpaperSuggestFor(stage, grade, volume, subject)
	if name != "" && !off {
		url = wallpaperURLPrefix + name
	}
	return url, name, want, off
}
