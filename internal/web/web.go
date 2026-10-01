// Package web 路由层：登录注册、管理员、教材导航、在线刷题、试卷归档。
package web

import (
	"embed"
	"fmt"
	"html/template"
	"io/fs"
	"net/http"
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
	funcMap := template.FuncMap{
		"stageCN":     textbook.StageCN,
		"publisherCN": textbook.PublisherCN,
		"add":         func(a, b int) int { return a + b },
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
		// seq 生成 1..n，模板里用于渲染班级下拉与刻度。
		"seq": func(n int) []int {
			out := make([]int, 0, n)
			for i := 1; i <= n; i++ {
				out = append(out, i)
			}
			return out
		},
	}
	tmpl, err := template.New("").Funcs(funcMap).ParseFS(assetsFS, "templates/*.html")
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

	// 静态资源（内嵌，单文件可直接运行）
	sub, _ := fs.Sub(a.assets, "static")
	r.StaticFS("/static", http.FS(sub))
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

	auth2 := r.Group("", auth.RequireLogin())
	{
		auth2.GET("/study", a.studyPage)
		auth2.GET("/lesson", a.lessonPage)
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
	}

	admin := r.Group("/admin", auth.RequireAdmin())
	{
		admin.GET("", a.adminPage)
		admin.POST("/invite/create", a.inviteCreate)
		admin.POST("/invite/revoke", a.inviteRevoke)
		admin.POST("/user/create", a.userCreate)
		admin.POST("/user/role", a.userRole)
		admin.POST("/user/gender", a.userGender)
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

	cur := a.currentLesson(st, u)
	total, passed, avg, _ := st.Stats()
	prog, _ := st.ListProgress()
	pmap := map[string]*db.Progress{}
	for _, p := range prog {
		pmap[p.LessonKey] = p
	}
	recent, _ := st.ListExams(5)

	a.html(c, "study.html", gin.H{
		"Title":   "学习主页",
		"Tree":    a.Tree,
		"User":    u,
		"Session": s,
		"Current": cur,
		"Prog":    pmap,
		"Total":   total,
		"Passed":  passed,
		"Avg":     avg,
		"Recent":  recent,
		"Pass":    a.Cfg.PassScore,
	})
}

// currentLesson 决定当前应学的课：优先学生库中的位置，否则按其学段 + 年级 + 册别取第一课。
func (a *App) currentLesson(st *db.Student, u *db.User) *textbook.Lesson {
	if k := st.GetState("current_lesson"); k != "" {
		if l, ok := a.Tree.Lessons[k]; ok {
			return l
		}
	}
	// 三级回退：学段+年级+册别精确匹配 → 同学段第一课 → 全库第一课。
	var first, stageFirst, match *textbook.Lesson
	for _, g := range a.Tree.Grades {
		stageOK := sameStage(g.Stage, u.Stage)
		for _, v := range g.Volumes {
			for _, s := range v.Subjects {
				for _, l := range s.Lessons {
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
	if _, ok := a.Tree.Lessons[key]; ok {
		_ = st.SetState("current_lesson", key)
	}
	c.Redirect(http.StatusSeeOther, "/study")
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
					if x.Key == l.Key && i+1 < len(s.Lessons) {
						return s.Lessons[i+1]
					}
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
	a.html(c, "result.html", gin.H{
		"Title":   "自测结果",
		"Exam":    e,
		"Ans":     as,
		"Lesson":  l,
		"Next":    nxt,
		"Full":    e.Total * 10,
		"Pass":    a.Cfg.PassScore,
		"Session": s,
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
	a.html(c, "archive.html", gin.H{
		"Title": "试卷归档", "Exams": list, "Session": s, "User": u,
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

// ---- 渲染 ----

func (a *App) html(c *gin.Context, name string, data gin.H) {
	if data == nil {
		data = gin.H{}
	}
	sess := auth.Current(c)
	if _, ok := data["Session"]; !ok {
		data["Session"] = sess
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
	case p == "/archive" || strings.HasPrefix(p, "/archive/"):
		return "archive"
	case p == "/admin" || strings.HasPrefix(p, "/admin/"):
		return "admin"
	}
	return ""
}
