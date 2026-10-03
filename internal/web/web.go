// Package web 路由层：登录注册、管理员、教材导航、在线刷题、试卷归档。
package web

import (
	"embed"
	"fmt"
	"html/template"
	"io/fs"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/gin-gonic/gin"

	"studybuddy/internal/auth"
	"studybuddy/internal/config"
	"studybuddy/internal/db"
	sbdbx "studybuddy/internal/docx"
	"studybuddy/internal/quiz"
	"studybuddy/internal/textbook"
)

// 静态资源与页面模板随包内嵌（go:embed 路径相对于本包目录），
// 因此单文件二进制无需任何外部文件即可运行。
//
//go:embed all:static all:templates
var assetsFS embed.FS

// App 应用上下文。
type App struct {
	Cfg     *config.Config
	Global  *db.Global
	Tree    *textbook.Tree
	Sess    *auth.Store
	assets  fs.FS // 内嵌资源根（含 static/ 与 templates/）
	tmpl    *template.Template
	mu      sync.Mutex
	studs   map[int64]*db.Student
	funcMap template.FuncMap
}

// New 构建应用并注册路由。
func New(cfg *config.Config, g *db.Global, tree *textbook.Tree) (*App, error) {
	tmpl, err := template.New("").Funcs(newFuncMap()).ParseFS(assetsFS, "templates/*.html")
	if err != nil {
		return nil, fmt.Errorf("解析模板失败: %w", err)
	}
	a := &App{
		Cfg: cfg, Global: g, Tree: tree, assets: assetsFS,
		Sess: auth.NewStore(12 * time.Hour),
		tmpl: tmpl, studs: map[int64]*db.Student{},
	}
	return a, nil
}

// newFuncMap 模板自定义函数集。
//
// 独立成包级函数（而不是写在 New 里），是为了让测试能拿到**与线上完全一致**的
// 这份函数集去单独解析模板——手抄一份近似的会漏函数，测试就成假绿。
func newFuncMap() template.FuncMap {
	return template.FuncMap{
		"stageCN":     textbook.StageCN,
		"publisherCN": textbook.PublisherCN,
		"add":         func(a, b int) int { return a + b },
		// dict 构造一个 map，供 partial 参数化传参使用。
		// Go 模板没有具名参数，多值入参的标准做法就是 dict：
		//   {{template "password_field" dict "Label" "密码" "Autocomplete" "current-password"}}
		// 参数为 key/value 交替的字符串列表；个数为奇数时忽略末尾那个孤立的 key。
		// 只接受 string 值——目前所有 partial 参数都是文案，不引入反射。
		"dict": func(kv ...any) map[string]string {
			m := make(map[string]string, len(kv)/2)
			for i := 0; i+1 < len(kv); i += 2 {
				k, ok1 := kv[i].(string)
				v, ok2 := kv[i+1].(string)
				if !ok1 || !ok2 {
					continue
				}
				m[k] = v
			}
			return m
		},
		"letter":      func(i int) string { return string(rune('A' + i)) },
		"chr":         func(i int) string { return string(rune('A' + i)) },
		"mul10":       func(i int) int { return i * 10 },
		"add1":        func(i int) int { return i + 1 },
		"join":        func(a []string, sep string) string { return strings.Join(a, sep) },
		// initial 取名字首字，用于顶栏名字旁的圆形头像（中文取第一个汉字，英文取首字母）。
		"initial": func(s string) string {
			r := []rune(strings.TrimSpace(s))
			if len(r) == 0 {
				return "?"
			}
			return strings.ToUpper(string(r[0]))
		},
		// 主题相关：模板里需要把性别/主题键转成中文，或标记选中态。
		"genderCN":  GenderCN,
		"skinName":  func(key string) string { return skinName(key) },
		"skinValid": SkinValid,
		// 学段 / 年级 / 班级相关。
		"stageName":    StageNameCN,
		"gradeLabel":   textbook.GradeLabel,
		"classNoLabel": ClassNoLabel,
		"classNo":      ParseClassNo,
		// seq 生成 1..n，模板里用于渲染班级下拉与刻度。
		"seq": func(n int) []int {
			out := make([]int, 0, n)
			for i := 1; i <= n; i++ {
				out = append(out, i)
			}
			return out
		},
		// splashVerse 每次渲染随机抽一句《唐诗三百首》诗句，用于学习主页开屏动画。
		"splashVerse": func() SplashVerse { return RandomSplashVerse() },
	}
}

// st 取（并缓存）某学生的私有库。
func (a *App) st(u *db.User) (*db.Student, error) {
	a.mu.Lock()
	defer a.mu.Unlock()
	if s, ok := a.studs[u.ID]; ok {
		return s, nil
	}
	s, err := db.OpenStudent(a.Cfg.StudentDBPath(u.ID), u.ID)
	if err != nil {
		return nil, err
	}
	a.studs[u.ID] = s
	return s, nil
}

// ---- 注册路由 ----

func (a *App) Routes() *gin.Engine {
	r := gin.New()
	r.Use(gin.Logger(), gin.Recovery())
	r.Use(auth.Mount(a.Sess))

	// 静态资源（内嵌，单文件可直接运行）。
	// Cache-Control: no-cache —— 样式/脚本改动后浏览器立即取新版（本地单机应用，代价可忽略）。
	sub, _ := fs.Sub(a.assets, "static")
	staticFS := http.StripPrefix("/static/", http.FileServer(http.FS(sub)))
	r.GET("/static/*filepath", func(c *gin.Context) {
		c.Header("Cache-Control", "no-cache")
		staticFS.ServeHTTP(c.Writer, c.Request)
	})
	r.GET("/favicon.svg", func(c *gin.Context) {
		b, err := fs.ReadFile(a.assets, "static/favicon.svg")
		if err != nil {
			c.Status(http.StatusNotFound)
			return
		}
		c.Data(http.StatusOK, "image/svg+xml", b)
	})

	r.GET("/", func(c *gin.Context) {
		if auth.Current(c) == nil {
			c.Redirect(http.StatusSeeOther, "/login")
			return
		}
		c.Redirect(http.StatusSeeOther, "/study")
	})

	r.GET("/login", a.loginPage)
	r.POST("/login", a.loginPost)
	r.GET("/register", a.registerPage)
	r.POST("/register", a.registerPost)
	r.POST("/logout", a.logout)

	// 背景壁纸：图片本身与「按学段/年级/册别查匹配结果」都对未登录开放，
	// 这样注册页就能在提交前实时预览自己该放哪张图。
	// 壁纸按 content/ 同构的目录树存放，所以图片路由必须是可吃多级路径的 catch-all。
	r.GET("/wallpapers/*path", a.wallpaperFile)
	r.GET("/api/wallpaper", a.wallpaperLookup)
	r.GET("/theme/mode", a.setThemeMode) // 明暗模式：写 cookie，未登录也能切

	auth2 := r.Group("", auth.RequireLogin())
	{
		auth2.GET("/study", a.studyPage)
		auth2.GET("/lesson", a.lessonPage)
		// 官方教材：详情页 + 图集分发 + 源 PDF 兜底（图集未预渲染时可下载原书）
		auth2.GET("/textbook", a.textbookPage)
		auth2.GET("/textbook/asset/*path", a.textbookAsset)
		auth2.GET("/textbook/raw", a.textbookRaw)
		// 目录懒加载：详情页首屏不内联 3 万条课目，改由前端按需拉这个接口
		auth2.GET("/textbook/toc", a.textbookToc)
		auth2.GET("/quiz", a.quizPage)
		auth2.POST("/quiz/submit", a.quizSubmit)
		auth2.GET("/result", a.resultPage)
		auth2.POST("/lesson/docx", a.lessonDocx)
		auth2.GET("/archive", a.archivePage)
		auth2.GET("/archive/view", a.archiveView)
		auth2.GET("/archive/docx", a.archiveDocx)
		auth2.POST("/archive/delete", a.archiveDelete)
		auth2.POST("/study/current", a.setCurrent)
		auth2.GET("/theme", a.setTheme)
		auth2.GET("/wallpaper/toggle", a.setWallpaperOnOff) // 开关要落库到 users.wallpaper，必须登录
		auth2.GET("/avatar/me", a.avatarMe)                 // 当前用户头像（未上传 404，前端回退首字徽标）
		auth2.POST("/profile/avatar", a.avatarUpload)       // 上传裁剪后的头像
	}

	admin := r.Group("/admin", auth.RequireAdmin())
	{
		admin.GET("", a.adminPage)
		admin.POST("/invite/create", a.inviteCreate)
		admin.POST("/invite/revoke", a.inviteRevoke)
		admin.POST("/user/create", a.userCreate)
		admin.POST("/user/role", a.userRole)
		admin.POST("/user/gender", a.userGender)
		admin.POST("/user/update", a.userUpdate)
	}
	return r
}

// ---- 登录 / 注册 ----

func (a *App) loginPage(c *gin.Context) {
	if auth.Current(c) != nil {
		c.Redirect(http.StatusSeeOther, "/study")
		return
	}
	a.html(c, "login.html", gin.H{"Title": "登录"})
}

func (a *App) loginPost(c *gin.Context) {
	username := strings.TrimSpace(c.PostForm("username"))
	password := c.PostForm("password")
	u, err := a.Global.ByUsername(username)
	if err != nil || u == nil || !auth.CheckPassword(u.PasswordHash(), password) {
		a.html(c, "login.html", gin.H{"Title": "登录", "Error": "用户名或密码不正确", "Username": username})
		return
	}
	tok, err := a.Sess.Create(&auth.Session{
		UserID: u.ID, Username: u.Username, Name: u.Name, Role: u.Role,
		Stage: u.Stage, Grade: u.Grade, Volume: u.Volume, Class: u.Class,
		Gender: u.Gender, Skin: u.Skin, Wallpaper: u.Wallpaper,
	})
	if err != nil {
		c.String(http.StatusInternalServerError, "创建会话失败")
		return
	}
	auth.SetCookie(c, tok, 12*3600)
	c.Redirect(http.StatusSeeOther, "/study")
}

func (a *App) logout(c *gin.Context) {
	if tok, err := c.Cookie(auth.CookieName); err == nil {
		a.Sess.Delete(tok)
	}
	auth.SetCookie(c, "", -1)
	c.Redirect(http.StatusSeeOther, "/login")
}

func (a *App) registerPage(c *gin.Context) {
	if auth.Current(c) != nil {
		c.Redirect(http.StatusSeeOther, "/study")
		return
	}
	n, _ := a.Global.CountUsers()
	a.html(c, "register.html", gin.H{
		"Title":      "注册",
		"NeedInvite": n > 0, // 系统初始化（无任何用户）时首个注册者免邀请码
	})
}

func (a *App) registerPost(c *gin.Context) {
	sess := auth.Current(c)
	username := strings.TrimSpace(c.PostForm("username"))
	name := strings.TrimSpace(c.PostForm("name"))
	password := c.PostForm("password")
	invite := strings.TrimSpace(c.PostForm("invite"))
	gender := normalizeGender(c.PostForm("gender"))
	volume := 1
	if c.PostForm("volume") == "2" {
		volume = 2
	}

	// 学段 + 年级 + 班级（班级选填）：前端为弹窗滚轮选择，也允许直接填数字。
	stage, grade, classNo, classText := parseSchoolInfo(
		c.PostForm("stage"), c.PostForm("grade"), c.PostForm("class_no"), c.PostForm("class"))

	n, _ := a.Global.CountUsers()

	fail := func(msg string) {
		fs := stage
		if fs == "" {
			fs = textbook.StagePrimary
		}
		fg := grade
		if fg < 1 {
			fg = 1
		}
		a.html(c, "register.html", gin.H{
			"Title": "注册", "Error": msg, "Username": username,
			"Name": name, "Gender": gender,
			"FormStage": fs, "FormGrade": fg, "FormClass": classNo,
			"FormVolume": volume,
			"NeedInvite": n > 0,
		})
	}

	if username == "" || name == "" || password == "" {
		fail("用户名、学生姓名、密码均为必填")
		return
	}
	if stage == "" {
		fail("请选择学段（小学 / 中学 / 高中）")
		return
	}
	if grade < 1 || grade > textbook.GradeCount(stage) {
		fail("请选择年级")
		return
	}
	if gender == "" {
		fail("请选择性别，我们会据此为你匹配主题")
		return
	}
	if len(password) < 6 {
		fail("密码至少 6 位")
		return
	}
	if _, err := a.Global.ByUsername(username); err == nil {
		fail("该用户名已被注册")
		return
	}

	if n > 0 {
		// 系统已存在用户：必须提交有效未作废邀请码
		if invite == "" {
			fail("系统已启用邀请码注册，请填写邀请码")
			return
		}
		if !a.Global.InviteValid(invite) {
			fail("邀请码无效、已使用或已作废")
			return
		}
	}

	role := "user"
	if n == 0 {
		role = "admin" // 首位注册者自动成为管理员
	}
	hash, err := auth.HashPassword(password)
	if err != nil {
		fail("密码加密失败")
		return
	}
	u := &db.User{
		Username: username, Name: name, Role: role,
		Stage: stage, Grade: grade, Volume: volume, Class: classText,
		Gender: gender,
		// 首次注册即按性别匹配主题；学生之后可在界面里自行修改。
		Skin: SkinForGender(gender),
	}
	if err := a.Global.CreateUser(u, hash); err != nil {
		fail("注册失败：" + err.Error())
		return
	}
	if n > 0 {
		_ = a.Global.UseInvite(invite, u.ID)
	}
	if _, err := a.st(u); err != nil {
		fail("初始化学习库失败：" + err.Error())
		return
	}
	if sess != nil {
		// 管理员在线时创建账号的场景：不挤掉自己的登录
		c.Redirect(http.StatusSeeOther, "/admin")
		return
	}
	tok, err := a.Sess.Create(&auth.Session{
		UserID: u.ID, Username: u.Username, Name: u.Name, Role: u.Role,
		Stage: u.Stage, Grade: u.Grade, Volume: u.Volume, Class: u.Class,
		Gender: u.Gender, Skin: u.Skin, Wallpaper: u.Wallpaper,
	})
	if err == nil {
		auth.SetCookie(c, tok, 12*3600)
	}
	c.Redirect(http.StatusSeeOther, "/study")
}

// normalizeGender 归一化性别取值，非法值一律视为未填写。
func normalizeGender(v string) string {
	switch strings.ToLower(strings.TrimSpace(v)) {
	case GenderMale, "男", "男生", "boy", "m":
		return GenderMale
	case GenderFemale, "女", "女生", "girl", "f":
		return GenderFemale
	default:
		return ""
	}
}

// extractGrade 从班级文本中提取年级数字，如「三年级二班」→ 3。
func extractGrade(class string) int {
	for _, r := range class {
		if r >= '0' && r <= '9' {
			return int(r - '0')
		}
	}
	cn := map[rune]int{'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9}
	for _, r := range class {
		if v, ok := cn[r]; ok {
			return v
		}
	}
	return 0
}

// ---- 学习主页 ----

func (a *App) studyPage(c *gin.Context) {
	s := auth.Current(c)
	u, _ := a.Global.ByID(s.UserID)
	st, err := a.st(u)
	if err != nil {
		c.String(http.StatusInternalServerError, "打开学习库失败")
		return
	}

	// 题型：choose 选择题（默认） / judge 判断题
	qt := normalizeQType(c.Query("qt"))
	cur := a.currentLesson(st, u, qt)
	total, passed, avg, _ := st.Stats()
	prog, _ := st.ListProgress()
	pmap := map[string]*db.Progress{}
	for _, p := range prog {
		pmap[p.LessonKey] = p
	}
	subjCards := a.subjectCards(st, u, qt, pmap)
	recent, _ := st.ListExams(5)

	// 教材导航主视图：URL 显式参数 > 用户档案 > 当前课位置 > 兜底（resolveNav 内部处理）。
	// 只把选中的年级册别传给模板，其他年级不进 HTML（性能：不渲染不隐藏）。
	qGrade, _ := strconv.Atoi(c.Query("grade"))
	qVolume, _ := strconv.Atoi(c.Query("volume"))
	nav := resolveNav(a.Tree, s, cur, qGrade, qVolume, qt)
	var menu []swStage
	if nav != nil {
		menu = buildNavMenu(a.Tree)
	}

	// 官方教材封面墙：只给「当前导航视图的学段 / 年级 / 学期」下的教材——
	// 学生这学期在读上册就只给上册，下册同理，学科不限、不跨年级、不铺全库。
	// nav 为 nil（连年级都定不出来）时 TbGrade / TbVolume 都为空，模板据此走
	// 空状态提示而不是整块消失，也不报错。volume 传 0 时 tbHomeCards 退化为
	// 该年级全部教材，不会因为学期缺失就整块空掉。
	var tbCards []gin.H
	tbGrade, tbVolume := "", ""
	if nav != nil {
		tbCards = a.tbHomeCards(nav.Stage, nav.Grade, nav.Volume)
		tbGrade = textbook.GradeLabel(nav.Stage, nav.Grade)
		// 学期没定出来（档案缺 volume）时留空，标题就不写「全一册」这种
		// 对学生没意义的词，直接只显示年级。
		if nav.Volume > 0 {
			tbVolume = tbVolumeLabel(nav.Volume)
		}
	}

	a.html(c, "study.html", gin.H{
		"Title":        "学习主页",
		"Tree":         a.Tree,
		"User":         u,
		"Session":      s,
		"Current":      cur,
		"SubjectCards": subjCards,
		"Prog":         pmap,
		"Total":        total,
		"Passed":       passed,
		"Avg":          avg,
		"Recent":       recent,
		"Pass":         a.Cfg.PassScore,
		"QT":           qt,
		"QTCN":         textbook.QTypeCN(qt),
		"CurTwin":      twinOf(a.Tree, cur),
		"NavView":      nav,
		"NavMenu":      menu,
		"TbCards":      tbCards,
		"TbGrade":      tbGrade,
		"TbVolume":     tbVolume,
	})
}

// normalizeQType 规范题型参数：只认 choose / judge，其余（含空）按选择题。
func normalizeQType(q string) string {
	switch strings.ToLower(strings.TrimSpace(q)) {
	case textbook.QTypeJudge:
		return textbook.QTypeJudge
	}
	return textbook.QTypeChoose
}

// twinOf 取同一门课在另一题型下的镜像课（不存在返回 nil）。
func twinOf(t *textbook.Tree, l *textbook.Lesson) *textbook.Lesson {
	if l == nil || t == nil {
		return nil
	}
	k := l.TwinKey()
	if k == "" {
		return nil
	}
	if x, ok := t.Lessons[k]; ok {
		return x
	}
	return nil
}

// currentLesson 决定当前应学的课：优先学生库中的位置，否则按其学段 + 年级 + 册别取第一课。
// qt 为题型（choose / judge，空值按 choose）：只在同题型的课里挑；
// 学生库里记住的是另一题型时，自动换到它的镜像课。
func (a *App) currentLesson(st *db.Student, u *db.User, qt string) *textbook.Lesson {
	if qt == "" {
		qt = textbook.QTypeChoose
	}
	if k := st.GetState("current_lesson"); k != "" {
		if l, ok := a.Tree.Lessons[k]; ok {
			if l.QType == qt {
				return l
			}
			if tk := l.TwinKey(); tk != "" {
				if t, ok := a.Tree.Lessons[tk]; ok && t.QType == qt {
					return t
				}
			}
		}
	}
	// 三级回退：学段+年级+册别精确匹配 → 同学段第一课 → 全库第一课（均限定题型）。
	pick := func(qtype string) *textbook.Lesson {
		var first, stageFirst, match *textbook.Lesson
		for _, g := range a.Tree.Grades {
			stageOK := sameStage(g.Stage, u.Stage)
			for _, v := range g.Volumes {
				for _, s := range v.Subjects {
					for _, l := range s.Lessons {
						if qtype != "" && l.QType != qtype {
							continue
						}
						if first == nil {
							first = l
						}
						if !stageOK {
							continue
						}
						if stageFirst == nil {
							stageFirst = l
						}
						if match == nil && l.Grade == u.Grade && l.Volume == u.Volume {
							match = l
						}
					}
				}
			}
		}
		if match != nil {
			return match
		}
		if stageFirst != nil {
			return stageFirst
		}
		return first
	}
	if l := pick(qt); l != nil {
		return l
	}
	return pick("") // 该题型下还没有课（如 judge 尚未生成）时不限题型回退
}

// subjectCard 学习主页「当前进度」区的一张学科卡片：该科从哪一课继续、练到什么程度。
type subjectCard struct {
	Key    string           // 学科 key（chinese / math / …）
	Name   string           // 学科中文名
	Lesson *textbook.Lesson // 继续点课程（全部达标时为该科第一课，仅作入口）
	Status string           // learning 练习中 / new 未开始 / done 全部达标
	Best   int              // 继续点课程的最高分（0 = 还没考过）
	Done   int              // 该科已达标课数
	Total  int              // 该科总课数（当前题型）
}

// subjectCards 逐学科计算「继续学习点」：
//  1. 学生库中「设为当前」的显式指针（current_lesson:<题型>:<学科>）优先，
//     但该课已达标时不再停留，顺延到下一门未达标课；
//  2. 无指针时按课程顺序取第一门未达标课（练习中 / 未开始均可）；
//  3. 全部达标 → done，入口链接指回该科第一课。
//
// 只统计学生档案（学段 / 年级 / 册别）所在视图、且当前题型下的课。
func (a *App) subjectCards(st *db.Student, u *db.User, qt string, pmap map[string]*db.Progress) []*subjectCard {
	if qt == "" {
		qt = textbook.QTypeChoose
	}
	// 定位学生档案所在的册别视图；年级未设置时取该学段第一个年级。
	var vol *textbook.Volume
	for _, g := range a.Tree.Grades {
		if !sameStage(g.Stage, u.Stage) {
			continue
		}
		if u.Grade > 0 && g.No != u.Grade {
			continue
		}
		for _, v := range g.Volumes {
			if v.No == u.Volume {
				vol = v
				break
			}
		}
		if vol != nil {
			break
		}
	}
	if vol == nil {
		return nil
	}
	stat := func(p *db.Progress) string {
		if p != nil && p.Status == "learning" {
			return "learning"
		}
		return "new"
	}
	best := func(p *db.Progress) int {
		if p == nil {
			return 0
		}
		return p.BestScore
	}
	out := make([]*subjectCard, 0, len(vol.Subjects))
	for _, s := range vol.Subjects {
		var lessons []*textbook.Lesson
		for _, l := range s.Lessons {
			if l.QType == qt {
				lessons = append(lessons, l)
			}
		}
		if len(lessons) == 0 {
			continue
		}
		c := &subjectCard{Key: s.Key, Name: s.Name, Total: len(lessons)}
		for _, l := range lessons {
			if p := pmap[l.Key]; p != nil && p.Status == "passed" {
				c.Done++
			}
		}
		// 1) 显式指针优先（未达标时才生效）
		if k := st.GetState("current_lesson:" + qt + ":" + s.Key); k != "" {
			if l, ok := a.Tree.Lessons[k]; ok && l.QType == qt {
				if p := pmap[l.Key]; p == nil || p.Status != "passed" {
					c.Lesson, c.Status, c.Best = l, stat(p), best(p)
				}
			}
		}
		// 2) 按课程顺序取第一门未达标课
		if c.Lesson == nil {
			for _, l := range lessons {
				if p := pmap[l.Key]; p == nil || p.Status != "passed" {
					c.Lesson, c.Status, c.Best = l, stat(p), best(p)
					break
				}
			}
		}
		// 3) 全部达标
		if c.Lesson == nil {
			c.Lesson, c.Status, c.Done = lessons[0], "done", len(lessons)
		}
		out = append(out, c)
	}
	return out
}

// sameStage 判断课程学段是否匹配学生学段；学生未设置学段（旧数据）时视为不限。
func sameStage(lessonStage, userStage string) bool {
	u := textbook.NormalizeStage(userStage)
	if u == "" {
		return true
	}
	return textbook.NormalizeStage(lessonStage) == u
}

func (a *App) setCurrent(c *gin.Context) {
	s := auth.Current(c)
	u, _ := a.Global.ByID(s.UserID)
	st, _ := a.st(u)
	key := c.PostForm("key")
	if l, ok := a.Tree.Lessons[key]; ok {
		_ = st.SetState("current_lesson", key) // 全局指针：教材导航定位沿用
		// 各科进度卡片的「继续点」：按 题型:学科 记忆，语文 / 数学 / 英语互不干扰
		_ = st.SetState("current_lesson:"+l.QType+":"+l.Subject, key)
	}
	// 回跳保留来源视图（题型/年级/册别）：「设为当前」后停留在原视图并直接看到新课高亮。
	// 表单未带这些字段时（旧入口）维持原行为，回 /study。
	back := "/study"
	q := url.Values{}
	if raw := strings.TrimSpace(c.PostForm("qt")); raw != "" {
		q.Set("qt", normalizeQType(raw))
	}
	if g, err := strconv.Atoi(c.PostForm("grade")); err == nil && g > 0 {
		q.Set("grade", strconv.Itoa(g))
	}
	if v, err := strconv.Atoi(c.PostForm("volume")); err == nil && v > 0 {
		q.Set("volume", strconv.Itoa(v))
	}
	if len(q) > 0 {
		back += "?" + q.Encode()
	}
	c.Redirect(http.StatusSeeOther, back)
}

// ---- 教材导航主视图（study.html 的「教材导航」卡片） ----

// navStageOrder 切换年级菜单的学段分组顺序。
var navStageOrder = []string{"primary", "middle", "high"}

// navView 教材导航卡片的主视图：整棵树里只渲染这一个年级册别。
type navView struct {
	Stage  string           // primary / middle / high
	Grade  int              // 学段内年级序号（小学 1~6，初高中 1~3）
	Volume int              // 1 / 2 / textbook.VolReview(9)
	Title  string           // 卡片标题，如「一年级 · 上册」「高三 · 高考复习」
	G      *textbook.Grade  // 年级节点
	V      *textbook.Volume // 册别节点
}

// swGrade / swStage 「切换年级」菜单的视图模型：服务端组装好，模板只做展示。
type swGrade struct {
	Stage   string // 学段（用于模板判断当前项高亮）
	No      int    // 学段内年级序号
	Label   string // 展示名，如「一年级」「高一」
	Volumes []*textbook.Volume
}

type swStage struct {
	Label  string // 小学 / 初中 / 高中
	Grades []swGrade
}

// gradeNode 在树里找学段+年级节点；找不到返回 nil。
func gradeNode(t *textbook.Tree, stage string, grade int) *textbook.Grade {
	if t == nil || stage == "" || grade <= 0 {
		return nil
	}
	for _, g := range t.Grades {
		if textbook.NormalizeStage(g.Stage) == stage && g.No == grade {
			return g
		}
	}
	return nil
}

// volumeHasQT 判断某册别下是否存在指定题型的课。
func volumeHasQT(v *textbook.Volume, qt string) bool {
	if v == nil {
		return false
	}
	for _, s := range v.Subjects {
		if s.CountOf(qt) > 0 {
			return true
		}
	}
	return false
}

// resolveNav 解析教材导航主视图。优先级从高到低：
//  1. URL 显式参数 ?grade=N&volume=M（非法值忽略；N 为学段内序号，不能超过该学段年级数）
//  2. 用户档案 Session.Stage/Grade/Volume
//  3. 当前课所在位置（currentLesson 已做过「档案→同学段→全库」三级回退，保证有数据）
//  4. 同学段第一个有数据的年级册别 → 全库第一个
//
// 每一步都要求目标位置确实存在当前题型的课；年级匹配但册别无数据时，先在该年级内
// 换一个有数据的册别再顺延。全部落空返回 nil（模板走「未识别到课程」分支，不报错）。
func resolveNav(t *textbook.Tree, s *auth.Session, cur *textbook.Lesson, qGrade, qVolume int, qt string) *navView {
	if t == nil || len(t.Grades) == 0 {
		return nil
	}
	// 基础值来自用户档案；档案缺失（老用户 Stage==""/Grade==0）时以当前课为准
	stage := textbook.NormalizeStage(s.Stage)
	grade, volume := s.Grade, s.Volume
	if cur != nil {
		cs := textbook.NormalizeStage(cur.Stage)
		if stage == "" {
			stage = cs
		}
		if cs == stage {
			if grade <= 0 {
				grade = cur.Grade
			}
			if volume <= 0 && grade == cur.Grade {
				volume = cur.Volume
			}
		}
	}
	// URL 显式参数最优先
	if stage != "" {
		if n := textbook.GradeCount(stage); qGrade > 0 && qGrade <= n {
			grade = qGrade
		}
		if qVolume > 0 {
			volume = qVolume
		}
	}

	build := func(g *textbook.Grade, v *textbook.Volume) *navView {
		return &navView{
			Stage: textbook.NormalizeStage(g.Stage), Grade: g.No, Volume: v.No,
			Title: strings.TrimSpace(textbook.GradeLabel(g.Stage, g.No) + " · " + v.Name),
			G:     g, V: v,
		}
	}
	// 在一个年级里挑册别：优先指定册别（且需有当前题型的课），否则取第一个有数据的册别
	pickIn := func(g *textbook.Grade, volume int) *navView {
		if g == nil {
			return nil
		}
		for _, v := range g.Volumes {
			if v.No == volume && volumeHasQT(v, qt) {
				return build(g, v)
			}
		}
		for _, v := range g.Volumes {
			if volumeHasQT(v, qt) {
				return build(g, v)
			}
		}
		return nil
	}

	// 1) 首选：URL 参数 / 用户档案组合
	if grade > 0 {
		if nv := pickIn(gradeNode(t, stage, grade), volume); nv != nil {
			return nv
		}
	}
	// 2) 当前课所在位置
	if cur != nil {
		if nv := pickIn(gradeNode(t, textbook.NormalizeStage(cur.Stage), cur.Grade), cur.Volume); nv != nil {
			return nv
		}
	}
	// 3) 同学段第一个有数据的；4) 全库第一个
	for _, g := range t.Grades {
		if stage == "" || textbook.NormalizeStage(g.Stage) == stage {
			if nv := pickIn(g, 0); nv != nil {
				return nv
			}
		}
	}
	for _, g := range t.Grades {
		if nv := pickIn(g, 0); nv != nil {
			return nv
		}
	}
	return nil
}

// buildNavMenu 组装「切换年级」菜单：按 小学/初中/高中 分组，只列树中实际存在的年级与册别
// （含高考复习虚拟册别 VolReview）。
func buildNavMenu(t *textbook.Tree) []swStage {
	if t == nil {
		return nil
	}
	byStage := map[string][]swGrade{}
	for _, g := range t.Grades {
		st := textbook.NormalizeStage(g.Stage)
		byStage[st] = append(byStage[st], swGrade{
			Stage: st, No: g.No,
			Label:   textbook.GradeLabel(g.Stage, g.No),
			Volumes: g.Volumes,
		})
	}
	var out []swStage
	for _, st := range navStageOrder {
		if gs := byStage[st]; len(gs) > 0 {
			out = append(out, swStage{Label: textbook.StageCN(st), Grades: gs})
		}
	}
	return out
}

// ---- 主题切换 ----

// setTheme 保存学生手动选择的主题并返回原页面。
//
// 入口在顶栏的「主题」下拉里，形如 /theme?skin=girl&back=%2Fstudy。
// 选择「按性别自动」时 skin=auto，等价于清空 users.skin，
// 之后若性别未变则仍然得到与首次注册一致的主题。
func (a *App) setTheme(c *gin.Context) {
	s := auth.Current(c)
	skin := strings.TrimSpace(c.Query("skin"))
	if skin == "auto" {
		skin = "" // 交回按性别推导
	} else if !SkinValid(skin) {
		skin = SkinDefault
	}
	if err := a.Global.SetSkin(s.UserID, skin); err == nil {
		s.Skin = skin // 同步内存会话，当前请求后立刻生效
	}
	back := c.Query("back")
	if !strings.HasPrefix(back, "/") || strings.HasPrefix(back, "//") {
		back = "/study" // 防开放重定向：只接受站内相对路径
	}
	c.Redirect(http.StatusSeeOther, back)
}

// ---- 明暗模式 ----

// themeCookie 明暗模式偏好：dark / light；不存在或为其它值 = 跟随系统。
const themeCookie = "sb_theme"

// themeModeFromCookie 读取用户手动选择的明暗模式。
//
// 返回 "dark" / "light" 表示用户手动锁定；返回空串表示「跟随系统」——
// 首次访问（无 cookie）、cookie 值为 auto、以及任何非法值都属于这种情况。
// 空串时模板不会输出 data-theme 属性，配色完全交给 CSS 的
// @media (prefers-color-scheme: dark) 决定，因此首次打开即自动跟随系统，
// 且系统切换时无需刷新即可生效。
func themeModeFromCookie(c *gin.Context) string {
	v, err := c.Cookie(themeCookie)
	if err != nil {
		return "" // 首次访问：跟随系统
	}
	switch strings.ToLower(strings.TrimSpace(v)) {
	case "dark":
		return "dark"
	case "light":
		return "light"
	}
	return "" // auto 或非法值：跟随系统
}

// setThemeMode 手动切换明暗模式：写入长期 cookie 后回跳原页面。
// mode=dark / light 为强制模式，mode=auto 或其它值表示交回「跟随系统」。
func (a *App) setThemeMode(c *gin.Context) {
	m := strings.ToLower(strings.TrimSpace(c.Query("mode")))
	if m != "dark" && m != "light" {
		m = ""
	}
	if m == "" {
		c.SetCookie(themeCookie, "", -1, "/", "", false, true) // 删除 cookie = 跟随系统
	} else {
		c.SetCookie(themeCookie, m, 365*24*3600, "/", "", false, true)
	}
	back := c.Query("back")
	if !strings.HasPrefix(back, "/") || strings.HasPrefix(back, "//") {
		back = "/study" // 防开放重定向：只接受站内相对路径
	}
	c.Redirect(http.StatusSeeOther, back)
}

// ---- 课程 / 刷题 ----

func (a *App) lessonPage(c *gin.Context) {
	s := auth.Current(c)
	u, _ := a.Global.ByID(s.UserID)
	st, _ := a.st(u)
	key := c.Query("key")
	l, ok := a.Tree.Lessons[key]
	if !ok {
		c.Redirect(http.StatusSeeOther, "/study")
		return
	}
	bank, _ := l.Bank()
	p := st.GetProgress(key)
	a.html(c, "lesson.html", gin.H{
		"Title":    l.Title,
		"Lesson":   l,
		"Bank":     len(bank),
		"Progress": p,
		"Pass":     a.Cfg.PassScore,
		"Session":  s,
		"Twin":     twinOf(a.Tree, l), // 同课的另一种题型（选择题 ↔ 判断题互跳）
		"QT":       l.QType,
	})
}

func (a *App) quizPage(c *gin.Context) {
	s := auth.Current(c)
	u, _ := a.Global.ByID(s.UserID)
	st, _ := a.st(u)
	key := c.Query("key")
	l, ok := a.Tree.Lessons[key]
	if !ok {
		c.Redirect(http.StatusSeeOther, "/study")
		return
	}
	bank, err := l.Bank()
	if err != nil || len(bank) == 0 {
		a.html(c, "lesson.html", gin.H{
			"Title": l.Title, "Lesson": l, "Bank": 0, "Session": s,
			"Error": "该课程暂未解析到题库，请确认 HTML 中含题目数据。",
		})
		return
	}
	paper := quiz.BuildPaper(l, bank, st.SeenStems(key), a.Cfg.Single, a.Cfg.Multi)
	renderQuiz(a, c, paper, st, u)
}

func renderQuiz(a *App, c *gin.Context, paper *quiz.Paper, st *db.Student, u *db.User) {
	key := paper.Lesson.Key
	_ = st.SetState("current_lesson", key)
	_ = st.SetState("paper_"+key, strings.Join(stemsOf(paper.Questions), "\x1e"))

	type optView struct {
		Idx  int
		Text string
	}
	type view struct {
		Idx     int
		TypeCN  string
		Stem    string
		Options []optView
	}
	var qs []view
	for i, q := range paper.Questions {
		t := "单选"
		if q.IsMulti() {
			t = "多选"
		} else if q.Type == "j" {
			t = "判断"
		}
		v := view{Idx: i, TypeCN: t, Stem: q.Stem}
		for j, o := range q.Options {
			v.Options = append(v.Options, optView{Idx: j, Text: o})
		}
		qs = append(qs, v)
	}
	a.html(c, "quiz.html", gin.H{
		"Title":   paper.Lesson.Title,
		"Lesson":  paper.Lesson,
		"Qs":      qs,
		"Session": auth.Current(c),
	})
}

func stemsOf(qs []textbook.Question) []string {
	out := make([]string, 0, len(qs))
	for _, q := range qs {
		out = append(out, q.Stem)
	}
	return out
}

func (a *App) quizSubmit(c *gin.Context) {
	s := auth.Current(c)
	u, _ := a.Global.ByID(s.UserID)
	st, _ := a.st(u)
	key := c.PostForm("key")
	l, ok := a.Tree.Lessons[key]
	if !ok {
		c.Redirect(http.StatusSeeOther, "/study")
		return
	}
	// 还原本次试卷（按提交时的题面重新取回，保证与展示一致）
	raw := st.GetState("paper_" + key)
	stems := strings.Split(raw, "\x1e")
	bank, _ := l.Bank()
	byStem := map[string]textbook.Question{}
	for _, q := range bank {
		byStem[q.Stem] = q
	}
	var qs []textbook.Question
	for _, s2 := range stems {
		if q, ok2 := byStem[s2]; ok2 {
			qs = append(qs, q)
		}
	}
	if len(qs) == 0 {
		qs = bank
		if len(qs) > a.Cfg.PerRound {
			qs = qs[:a.Cfg.PerRound]
		}
	}

	_ = c.Request.ParseForm()
	picked := map[int][]int{}
	for i := range qs {
		for _, v := range c.Request.Form["q"+strconv.Itoa(i)] {
			if n, err := strconv.Atoi(v); err == nil && n >= 0 && n < len(qs[i].Options) {
				picked[i] = append(picked[i], n)
			}
		}
	}

	res := quiz.Grade(qs, picked, a.Cfg.PassScore)
	title := l.FullLabel()
	exam := &db.Exam{LessonKey: key, Title: title, Total: res.Total, Score: res.Score,
		Passed: res.Passed, Source: "online"}
	id, err := st.CreateExam(exam)
	if err != nil {
		c.String(http.StatusInternalServerError, "保存成绩失败")
		return
	}
	_ = st.AddAnswers(id, key, res.Answers)

	// 更新进度：达标则推进到下一课，未达标则继续本课
	p := st.GetProgress(key)
	p.Subject, p.Unit, p.Title = l.SubjectCN, l.UnitLabel(), l.LessonLabel()
	p.Attempts++
	p.LastAt = time.Now().Format("2006-01-02 15:04:05")
	if res.Score > p.BestScore {
		p.BestScore = res.Score
	}
	if res.Passed {
		p.Status = "passed"
		if nxt := a.nextLesson(l); nxt != nil {
			_ = st.SetState("current_lesson", nxt.Key)
		}
	} else {
		p.Status = "learning"
		_ = st.SetState("current_lesson", key)
	}
	_ = st.SaveProgress(p)

	c.Redirect(http.StatusSeeOther, "/result?id="+strconv.FormatInt(id, 10))
}

// nextLesson 按目录顺序取下一课（同学段、同科目内）。
func (a *App) nextLesson(l *textbook.Lesson) *textbook.Lesson {
	for _, g := range a.Tree.Grades {
		if g.No != l.Grade || textbook.NormalizeStage(g.Stage) != textbook.NormalizeStage(l.Stage) {
			continue
		}
		for _, v := range g.Volumes {
			if v.No != l.Volume {
				continue
			}
			for _, s := range v.Subjects {
				if s.Key != l.Subject {
					continue
				}
				for i, x := range s.Lessons {
					if x.Key != l.Key {
						continue
					}
					// choose / judge 两套镜像课混在同一列表里，下一课必须沿用同一题型
					for _, y := range s.Lessons[i+1:] {
						if y.QType == l.QType {
							return y
						}
					}
					return nil
				}
			}
		}
	}
	return nil
}

func (a *App) resultPage(c *gin.Context) {
	s := auth.Current(c)
	u, _ := a.Global.ByID(s.UserID)
	st, _ := a.st(u)
	id, _ := strconv.ParseInt(c.Query("id"), 10, 64)
	e, err := st.Exam(id)
	if err != nil {
		c.Redirect(http.StatusSeeOther, "/archive")
		return
	}
	as, _ := st.Answers(id)
	l := a.Tree.Lessons[e.LessonKey]
	var nxt *textbook.Lesson
	if e.Passed && l != nil {
		nxt = a.nextLesson(l)
	}
	// 解析按题干从当课题库里取（判断题每题都带解析），无需改动答卷表结构。
	explain := map[string]string{}
	if l != nil {
		if b, err := l.Bank(); err == nil {
			for _, q := range b {
				if q.Explain != "" {
					explain[q.Stem] = q.Explain
				}
			}
		}
	}
	a.html(c, "result.html", gin.H{
		"Title":   "自测结果",
		"Exam":    e,
		"Ans":     as,
		"Lesson":  l,
		"Next":    nxt,
		"Full":    e.Total * 10,
		"Pass":    a.Cfg.PassScore,
		"Session": s,
		"Explain": explain,
	})
}

// ---- docx 导出与归档 ----

func (a *App) lessonDocx(c *gin.Context) {
	s := auth.Current(c)
	u, _ := a.Global.ByID(s.UserID)
	st, _ := a.st(u)
	key := c.PostForm("key")
	l, ok := a.Tree.Lessons[key]
	if !ok {
		c.Redirect(http.StatusSeeOther, "/study")
		return
	}
	bank, _ := l.Bank()
	paper := quiz.BuildPaper(l, bank, st.SeenStems(key), a.Cfg.Single, a.Cfg.Multi)

	var qs []sbdbx.Q
	for i, q := range paper.Questions {
		t := "单选"
		if q.IsMulti() {
			t = "多选"
		} else if q.Type == "j" {
			t = "判断"
		}
		var ans []string
		for _, x := range q.AnswerIdx() {
			if x < len(q.Options) {
				ans = append(ans, q.Options[x])
			}
		}
		qs = append(qs, sbdbx.Q{No: i + 1, Type: t, Stem: q.Stem, Options: q.Options, Answers: ans})
	}

	title := l.FullLabel() + " 自测卷"
	ex := sbdbx.Exam{
		Title: title, Student: u.Name, Class: u.Class,
		Date:     time.Now().Format("2006年01月02日"),
		Lesson:   l.FullLabel(),
		BankSize: len(bank), Questions: qs,
		Tip: "提示：认真读题，单选选一个，多选可选多个。做完请对照文末参考答案核对。",
	}

	dir := a.Cfg.StudentArchiveDir(u.ID)
	if err := os.MkdirAll(dir, 0o755); err != nil {
		c.String(http.StatusInternalServerError, "创建归档目录失败")
		return
	}
	name := fmt.Sprintf("%s_%s.docx", safeName(l.Title), time.Now().Format("20060102-150405"))
	out := filepath.Join(dir, name)
	f, err := os.Create(out)
	if err != nil {
		c.String(http.StatusInternalServerError, "创建文件失败")
		return
	}
	if err := sbdbx.Build(f, ex); err != nil {
		f.Close()
		c.String(http.StatusInternalServerError, "生成 docx 失败："+err.Error())
		return
	}
	f.Close()

	// 归档记录：纸质试卷线下作答，score 记为 -1 表示待批改
	e := &db.Exam{LessonKey: key, Title: title, Total: len(qs), Score: -1,
		Passed: false, Docx: name, Source: "docx"}
	id, _ := st.CreateExam(e)
	_ = st.SetState("current_lesson", key)

	c.Header("Content-Disposition", "attachment; filename*=UTF-8''"+urlEscape(name))
	c.File(out)
	if id > 0 {
		_ = id
	}
}

func urlEscape(s string) string {
	var b strings.Builder
	for _, r := range s {
		if (r >= 'a' && r <= 'z') || (r >= 'A' && r <= 'Z') || (r >= '0' && r <= '9') || r == '.' || r == '-' || r == '_' {
			b.WriteRune(r)
			continue
		}
		for _, bb := range []byte(string(r)) {
			fmt.Fprintf(&b, "%%%02X", bb)
		}
	}
	return b.String()
}

func safeName(s string) string {
	rep := strings.NewReplacer(" ", "", "·", "", "（", "", "）", "", "(", "", ")", "", "/", "_", "\\", "_")
	s = rep.Replace(s)
	if len([]rune(s)) > 24 {
		s = string([]rune(s)[:24])
	}
	return s
}

// ---- 归档 ----

func (a *App) archivePage(c *gin.Context) {
	s := auth.Current(c)
	u, _ := a.Global.ByID(s.UserID)
	st, _ := a.st(u)
	list, _ := st.ListExams(200)

	// 题型分类：choose 选择题（默认） / judge 判断题。
	// 试卷只存了 lesson_key，题型由 key 里的 choose/judge 段推断（旧记录按选择题）。
	qt := normalizeQType(c.Query("qt"))
	qtMap := map[int64]string{}
	qtCount := map[string]int{textbook.QTypeChoose: 0, textbook.QTypeJudge: 0}
	shown := make([]*db.Exam, 0, len(list))
	for _, e := range list {
		q := textbook.QTypeOfKey(e.LessonKey)
		qtMap[e.ID] = q
		qtCount[q]++
		if q == qt {
			shown = append(shown, e)
		}
	}

	a.html(c, "archive.html", gin.H{
		"Title": "试卷归档", "Exams": shown, "Session": s, "User": u,
		"QT": qt, "QTCN": textbook.QTypeCN(qt),
		"ExamQT": qtMap, "QTCount": qtCount, "AllCount": len(list),
	})
}

func (a *App) archiveView(c *gin.Context) {
	s := auth.Current(c)
	u, _ := a.Global.ByID(s.UserID)
	st, _ := a.st(u)
	id, _ := strconv.ParseInt(c.Query("id"), 10, 64)
	e, err := st.Exam(id)
	if err != nil {
		c.Redirect(http.StatusSeeOther, "/archive")
		return
	}
	as, _ := st.Answers(id)
	a.html(c, "archive_view.html", gin.H{
		"Title": "试卷详情", "Exam": e, "Ans": as, "Session": s, "Full": e.Total * 10,
		// 题型由 lesson_key 推断，用于详情页徽标与「返回归档列表」保持同一分类
		"QT": textbook.QTypeOfKey(e.LessonKey),
	})
}

func (a *App) archiveDocx(c *gin.Context) {
	s := auth.Current(c)
	u, _ := a.Global.ByID(s.UserID)
	st, _ := a.st(u)
	id, _ := strconv.ParseInt(c.Query("id"), 10, 64)
	e, err := st.Exam(id)
	if err != nil || e.Docx == "" {
		c.String(http.StatusNotFound, "该试卷没有可下载的 docx")
		return
	}
	p := filepath.Join(a.Cfg.StudentArchiveDir(u.ID), filepath.Base(e.Docx))
	if _, err := os.Stat(p); err != nil {
		c.String(http.StatusNotFound, "归档文件已不存在")
		return
	}
	c.Header("Content-Disposition", "attachment; filename*=UTF-8''"+urlEscape(e.Docx))
	c.File(p)
}

// archiveDelete 删除归档试卷（单份或批量）。
//
// 前端以 POST 表单提交 ids（可重复字段，如 ids=3&ids=5&ids=8），返回 JSON：
//
//	成功 {ok:true, deleted:N}；失败 {ok:false, error:"…"}（HTTP 4xx/5xx）
//
// 学生库本身按学号隔离，能删的只有本人试卷；docx 归档文件随记录一并清理。
func (a *App) archiveDelete(c *gin.Context) {
	s := auth.Current(c)
	u, _ := a.Global.ByID(s.UserID)
	st, _ := a.st(u)

	ids := []int64{}
	for _, v := range c.PostFormArray("ids") {
		if id, err := strconv.ParseInt(strings.TrimSpace(v), 10, 64); err == nil && id > 0 {
			ids = append(ids, id)
		}
	}
	if len(ids) == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"ok": false, "error": "未选择要删除的试卷"})
		return
	}

	// 删库前先记住关联的 docx 文件名，删完一并清理磁盘归档。
	files := []string{}
	for _, id := range ids {
		if e, err := st.Exam(id); err == nil && e.Docx != "" {
			files = append(files, filepath.Base(e.Docx))
		}
	}
	n, err := st.DeleteExams(ids)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"ok": false, "error": "删除失败，请重试"})
		return
	}
	for _, f := range files {
		_ = os.Remove(filepath.Join(a.Cfg.StudentArchiveDir(u.ID), f))
	}
	c.JSON(http.StatusOK, gin.H{"ok": true, "deleted": n})
}

// ---- 管理员 ----

func (a *App) adminPage(c *gin.Context) {
	s := auth.Current(c)
	users, _ := a.Global.ListUsers()
	invites, _ := a.Global.ListInvites()
	a.html(c, "admin.html", gin.H{
		"Title": "用户管理", "Users": users, "Invites": invites, "Session": s,
		"EditErr": c.Query("err"), "Saved": c.Query("saved") == "1",
	})
}

func (a *App) inviteCreate(c *gin.Context) {
	s := auth.Current(c)
	n := 8
	if v, err := strconv.Atoi(c.PostForm("count")); err == nil && v > 0 && v <= 50 {
		n = v
	}
	for i := 0; i < n; i++ {
		code, err := auth.RandomCode(8)
		if err != nil {
			continue
		}
		_ = a.Global.CreateInvite(code, s.UserID)
	}
	c.Redirect(http.StatusSeeOther, "/admin")
}

func (a *App) inviteRevoke(c *gin.Context) {
	_ = a.Global.RevokeInvite(c.PostForm("code"))
	c.Redirect(http.StatusSeeOther, "/admin")
}

func (a *App) userCreate(c *gin.Context) {
	s := auth.Current(c)
	username := strings.TrimSpace(c.PostForm("username"))
	password := c.PostForm("password")
	name := strings.TrimSpace(c.PostForm("name"))
	stage, grade, _, classText := parseSchoolInfo(
		c.PostForm("stage"), c.PostForm("grade"), c.PostForm("class_no"), c.PostForm("class"))
	grade = ClampGrade(stage, grade)
	role := c.PostForm("role")
	if role != "admin" {
		role = "user"
	}
	if username == "" || password == "" || name == "" {
		c.Redirect(http.StatusSeeOther, "/admin")
		return
	}
	if _, err := a.Global.ByUsername(username); err == nil {
		c.Redirect(http.StatusSeeOther, "/admin")
		return
	}
	hash, err := auth.HashPassword(password)
	if err != nil {
		c.Redirect(http.StatusSeeOther, "/admin")
		return
	}
	volume := 1
	if c.PostForm("volume") == "2" {
		volume = 2
	}
	gender := normalizeGender(c.PostForm("gender"))
	u := &db.User{Username: username, Name: name, Role: role,
		Stage: stage, Grade: grade, Volume: volume, Class: classText,
		Gender: gender, Skin: SkinForGender(gender)}
	if err := a.Global.CreateUser(u, hash); err == nil {
		_, _ = a.st(u) // 立即初始化其私有库
		_ = s
	}
	c.Redirect(http.StatusSeeOther, "/admin")
}

func (a *App) userRole(c *gin.Context) {
	id, _ := strconv.ParseInt(c.PostForm("id"), 10, 64)
	role := c.PostForm("role")
	if role != "admin" && role != "user" {
		role = "user"
	}
	_ = a.Global.SetRole(id, role)
	c.Redirect(http.StatusSeeOther, "/admin")
}

// userGender 补填/修正某账号的性别（管理员能力）。
// 只在学生自己没手动选过主题的前提下，性别才会改变其界面主题。
func (a *App) userGender(c *gin.Context) {
	id, _ := strconv.ParseInt(c.PostForm("id"), 10, 64)
	gender := normalizeGender(c.PostForm("gender"))
	if id > 0 {
		_ = a.Global.SetGender(id, gender)
	}
	c.Redirect(http.StatusSeeOther, "/admin")
}

// userUpdate 管理员修改账号资料：用户名 / 姓名 / 学段 / 年级 / 册别 / 班级 / 性别。
// 用户名唯一冲突或字段缺失时带回 err= 标记回管理页提示；成功后同步刷新该用户
// 的在途会话，学生端无需重新登录即可看到新资料。
func (a *App) userUpdate(c *gin.Context) {
	id, _ := strconv.ParseInt(c.PostForm("id"), 10, 64)
	if id <= 0 {
		c.Redirect(http.StatusSeeOther, "/admin")
		return
	}
	if _, err := a.Global.ByID(id); err != nil {
		c.Redirect(http.StatusSeeOther, "/admin")
		return
	}
	username := strings.TrimSpace(c.PostForm("username"))
	name := strings.TrimSpace(c.PostForm("name"))
	if username == "" || name == "" {
		c.Redirect(http.StatusSeeOther, "/admin?err=required")
		return
	}
	if other, err := a.Global.ByUsername(username); err == nil && other.ID != id {
		c.Redirect(http.StatusSeeOther, "/admin?err=username")
		return
	}
	stage, grade, _, classText := parseSchoolInfo(
		c.PostForm("stage"), c.PostForm("grade"), c.PostForm("class_no"), c.PostForm("class"))
	grade = ClampGrade(stage, grade)
	volume := 1
	if c.PostForm("volume") == "2" {
		volume = 2
	}
	gender := normalizeGender(c.PostForm("gender"))
	if err := a.Global.UpdateProfile(id, username, name, stage, grade, volume, classText, gender); err != nil {
		c.Redirect(http.StatusSeeOther, "/admin?err=save")
		return
	}
	a.Sess.RefreshByUser(id, func(sess *auth.Session) {
		sess.Username, sess.Name = username, name
		sess.Stage, sess.Grade, sess.Volume = stage, grade, volume
		sess.Class, sess.Gender = classText, gender
	})
	c.Redirect(http.StatusSeeOther, "/admin?saved=1")
}

// ---- 渲染 ----

func (a *App) html(c *gin.Context, name string, data gin.H) {
	if data == nil {
		data = gin.H{}
	}
	sess := auth.Current(c)
	if _, ok := data["Session"]; !ok {
		data["Session"] = sess
	}
	// 头像：没上传时不下发 <img src="/avatar/me">，避免每次刷新都在控制台记一条 404。
	if _, ok := data["HasAvatar"]; !ok {
		data["HasAvatar"] = a.hasAvatar(sess)
	}
	if _, ok := data["Title"]; !ok {
		data["Title"] = "StudyBuddy"
	}
	// 主题相关：所有页面都能拿到皮肤列表与当前生效皮肤（含登录 / 注册页）。
	gender, saved := "", ""
	if sess != nil {
		gender, saved = sess.Gender, sess.Skin
	}
	data["Skin"] = ResolveSkin(saved, gender)
	data["SkinSaved"] = saved
	data["Skins"] = Skins
	// Gender 可能已由处理函数写入（注册失败时要回填用户刚选的性别），不要覆盖。
	if _, ok := data["Gender"]; !ok {
		data["Gender"] = gender
	}
	// 学段 / 年级 / 班级：注册页与管理员建号表单共用（含年级滑动刻度）。
	data["Stages"] = StageList
	data["MaxClassNo"] = MaxClassNo
	if _, ok := data["FormStage"]; !ok {
		data["FormStage"] = textbook.StagePrimary
	}
	if _, ok := data["FormGrade"]; !ok {
		data["FormGrade"] = 1
	}
	if _, ok := data["FormClass"]; !ok {
		data["FormClass"] = 0
	}
	if _, ok := data["FormVolume"]; !ok {
		data["FormVolume"] = 1
	}
	if _, ok := data["StageJSON"]; !ok {
		data["StageJSON"] = StageJSON
	}
	// 背景壁纸：首页按「学段 + 年级」匹配年级通用图（同一张上下册共用）；课程页 / 在线自测页 /
	// 结果页带 Lesson，会按「学段 + 年级 + 册别 + 学科」精准匹配学科专属图
	// （如 g4-v1-chinese.webp），缺失则逐级退回册别图、年级图。
	// 未登录（登录 / 注册页）时为未匹配。
	var cur *textbook.Lesson
	if l, ok := data["Lesson"].(*textbook.Lesson); ok {
		cur = l
	}
	wpURL, wpName, wpWant, wpOff := a.resolveWallpaperFor(sess, cur)
	data["Wallpaper"] = wpURL
	data["WallpaperName"] = wpName
	data["WallpaperOff"] = wpOff
	data["WallpaperSubject"] = ""
	data["WallpaperSubjectCN"] = ""
	if cur != nil {
		if cn := textbook.SubjectCN(cur.Subject); cn != "" {
			data["WallpaperSubject"] = cur.Subject
			data["WallpaperSubjectCN"] = cn
		}
	}
	data["WallpaperLabel"] = wallpaperPanelLabel(wpName, data["WallpaperSubjectCN"].(string))
	if wpWant == "" {
		// 未登录时按注册表单当前选择给出「推荐文件路径」，方便注册前就去放图。
		fs, _ := data["FormStage"].(string)
		fg, _ := data["FormGrade"].(int)
		fv, _ := data["FormVolume"].(int)
		if fg < 1 {
			fg = 1
		}
		wpWant = a.WallpaperSuggest(fs, fg, fv)
	}
	data["WallpaperWant"] = wpWant
	data["Path"] = c.Request.URL.RequestURI()
	// 明暗模式：cookie 里存手动选择（dark / light），为空表示跟随系统（由 CSS 媒体查询决定）。
	data["Theme"] = themeModeFromCookie(c)
	// 顶栏高亮用：把当前路径归到「学习 / 归档 / 管理」三个分区之一。
	data["Nav"] = navSection(c.Request.URL.Path)
	if err := a.tmpl.ExecuteTemplate(c.Writer, name, data); err != nil {
		c.String(http.StatusInternalServerError, "模板渲染失败: "+err.Error())
	}
}

// navSection 把请求路径映射成顶栏分区名，供导航项高亮当前所在位置。
// 课程页 / 自测页 / 结果页都属于「学习」，所以统一归到 study。
func navSection(p string) string {
	switch {
	case p == "/study" || p == "/lesson" || p == "/quiz" || p == "/result":
		return "study"
	case p == "/textbook" || strings.HasPrefix(p, "/textbook/"):
		return "textbook" // 顶栏独立高亮「教材」
	case p == "/archive" || strings.HasPrefix(p, "/archive/"):
		return "archive"
	case p == "/admin" || strings.HasPrefix(p, "/admin/"):
		return "admin"
	}
	return ""
}
