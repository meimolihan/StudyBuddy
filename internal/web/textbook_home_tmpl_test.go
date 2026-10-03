package web

import (
	"bytes"
	"html/template"
	"regexp"
	"strings"
	"testing"

	"github.com/gin-gonic/gin"
	"studybuddy/internal/auth"
	"studybuddy/internal/db"
)

// studyTmplForTest 解析真实的 study.html 及其依赖模板。
// 直接复用 newFuncMap()——与线上同一份函数集，缺函数会立刻暴露，不会假绿。
func studyTmplForTest(t *testing.T) *template.Template {
	t.Helper()
	tmpl, err := template.New("").Funcs(newFuncMap()).ParseFS(assetsFS, "templates/study.html", "templates/partials.html")
	if err != nil {
		t.Fatalf("模板解析失败（多半是 study.html 语法错误）: %v", err)
	}
	return tmpl
}

var coverRe = regexp.MustCompile(`<a class="tb-cover-card" href="/textbook\?key=([a-z0-9\-]+)"`)

// studyData 组一份够 study.html 整条渲染链用的最小数据。
// Session 必须给——welcome_modal 会取 .Session.Name，缺字段直接模板执行报错。
func studyData(cards []gin.H, grade, volume string) gin.H {
	return gin.H{
		"Title": "学习主页", "QT": "choose", "QTCN": "选择题", "Pass": 60,
		"TbCards": cards, "TbGrade": grade, "TbVolume": volume,
		"Session":   &auth.Session{Name: "郭奕凡", Stage: "primary", Grade: 4, Volume: 1, Class: "1班"},
		"User":      &db.User{Name: "郭爸爸"},
		"HasAvatar": false,
	}
}

// TestStudyTemplateCoversWall 用真实模板渲染，验证：有图集时输出封面墙，
// 每张卡都是「封面图 + 名称小字」且链接指向详情页，封面图带懒加载属性。
func TestStudyTemplateCoversWall(t *testing.T) {
	tmpl := studyTmplForTest(t)
	a := newTBTestApp(t, tbTestManifest, true) // 图集已预渲染 → 走 <img> 分支
	cards := a.tbHomeCards("primary", 4, 0)

	var buf bytes.Buffer
	if err := tmpl.ExecuteTemplate(&buf, "study.html", studyData(cards, "四年级", "上册")); err != nil {
		t.Fatalf("模板执行失败: %v", err)
	}
	html := buf.String()

	keys := coverRe.FindAllStringSubmatch(html, -1)
	if len(keys) != len(cards) {
		t.Fatalf("封面卡数量不符：模板 %d 张，数据 %d 张", len(keys), len(cards))
	}
	if !strings.Contains(html, `<div class="tb-covers">`) {
		t.Error("缺少封面墙容器 .tb-covers")
	}
	// 封面图必须懒加载 + 异步解码，保证首屏不被几十张封面拖住
	if n := strings.Count(html, `loading="lazy"`); n != len(cards) {
		t.Errorf("懒加载封面应为 %d 张，实际 %d", len(cards), n)
	}
	if n := strings.Count(html, `decoding="async"`); n != len(cards) {
		t.Errorf("async 解码应为 %d 张，实际 %d", len(cards), n)
	}
	// 带宽高占位，图片到达前不跳版
	if n := strings.Count(html, `width="120"`); n != len(cards) {
		t.Errorf("封面应带 width 占位 %d 处，实际 %d", len(cards), n)
	}
	// 旧横版详情卡的痕迹必须清干净
	for _, dead := range []string{"tb-book-desc", "tb-book-foot", "tb-home-grid", "tb-go"} {
		if strings.Contains(html, dead) {
			t.Errorf("主页仍残留旧教材卡结构: %s", dead)
		}
	}
	// 名称小字保留
	if !strings.Contains(html, "语文 · 上册") {
		t.Error("封面卡未渲染教材名称小字")
	}
	// 头部标注当前年级 + 当前学期（不再是笼统的「上册 / 下册」）
	if !strings.Contains(html, "四年级 · 上册 · 共") {
		t.Error("卡片区头部未标注当前年级与当前学期")
	}
	if strings.Contains(html, "上册 / 下册") {
		t.Error("头部不应再出现「上册 / 下册」，必须只显示当前学期")
	}
}

// 教材墙必须沉到页面最底部：项目定位以刷题为主，刷题模块（当前进度 /
// 最近自测 / 教材导航）全部在上方，教材阅读作为辅助查阅排末尾。
// 用真实模板渲染后比较各区块下标，防止以后又被调回上面。
func TestStudyTemplateProgressBeforeTextbooks(t *testing.T) {
	tmpl := studyTmplForTest(t)
	a := newTBTestApp(t, tbTestManifest, true)
	cards := a.tbHomeCards("primary", 4, 0)

	data := studyData(cards, "四年级", "上册")
	// SubjectCards 非空才会渲染「当前进度」整块，这里给一张最小学科卡
	data["SubjectCards"] = []gin.H{{
		"Name": "语文", "Status": "learning", "Done": 3, "Total": 20,
		"Lesson": map[string]any{
			"Key": "primary/pep/choose/grade4/volume1/chinese/01.html",
			"UnitLabel": "第一单元", "LessonLabel": "01 观潮", "Title": "观潮",
		},
	}}

	var buf bytes.Buffer
	if err := tmpl.ExecuteTemplate(&buf, "study.html", data); err != nil {
		t.Fatalf("模板执行失败: %v", err)
	}
	html := buf.String()

	prog := strings.Index(html, "<h2>当前进度</h2>")
	tb := strings.Index(html, "<h2>官方教材</h2>")
	nav := strings.Index(html, `class="card nav-card"`)
	foot := strings.Index(html, `<footer class="foot">`)
	if prog < 0 || tb < 0 || nav < 0 {
		t.Fatalf("区块应都存在：当前进度=%d 官方教材=%d 导航卡=%d", prog, tb, nav)
	}
	if prog > tb {
		t.Errorf("区块顺序错：「当前进度」(idx %d) 应排在「官方教材」(idx %d) 之前", prog, tb)
	}
	// 项目定位以刷题为主：教材墙必须沉到导航卡之后、footer 之前，即页面最底部
	if tb < nav {
		t.Errorf("「官方教材」(idx %d) 应排在教材导航卡( idx %d) 之后", tb, nav)
	}
	if foot >= 0 && tb > foot {
		t.Errorf("「官方教材」(idx %d) 排到了 footer(idx %d) 之后，应在 footer 之前", tb, foot)
	}
}

// 「最近自测」也是刷题模块，即使有数据也不能被排到教材墙后面。
func TestStudyTemplateRecentBeforeTextbooks(t *testing.T) {
	tmpl := studyTmplForTest(t)
	a := newTBTestApp(t, tbTestManifest, true)
	cards := a.tbHomeCards("primary", 4, 0)

	data := studyData(cards, "四年级", "上册")
	data["Recent"] = []gin.H{{
		"CreatedAt": "2026-10-03 20:30", "Title": "观潮", "Score": 90, "Passed": true,
	}}

	var buf bytes.Buffer
	if err := tmpl.ExecuteTemplate(&buf, "study.html", data); err != nil {
		t.Fatalf("模板执行失败: %v", err)
	}
	html := buf.String()

	recent := strings.Index(html, "<h2>最近自测</h2>")
	tb := strings.Index(html, "<h2>官方教材</h2>")
	if recent < 0 || tb < 0 {
		t.Fatalf("区块应都存在：最近自测=%d 官方教材=%d", recent, tb)
	}
	if recent > tb {
		t.Errorf("「最近自测」(idx %d) 是刷题模块，应排在「官方教材」(idx %d) 之前", recent, tb)
	}
}

// 图集未预渲染时降级为占位块，且**不能**发出图片请求（否则一排 404）。
func TestStudyTemplateCoversNoAssets(t *testing.T) {
	tmpl := studyTmplForTest(t)
	a := newTBTestApp(t, tbTestManifest, false) // 无 meta.json
	cards := a.tbHomeCards("primary", 4, 0)

	var buf bytes.Buffer
	if err := tmpl.ExecuteTemplate(&buf, "study.html", studyData(cards, "四年级", "上册")); err != nil {
		t.Fatalf("模板执行失败: %v", err)
	}
	html := buf.String()

	if n := len(coverRe.FindAllStringSubmatch(html, -1)); n != len(cards) {
		t.Fatalf("降级时封面卡仍应有 %d 张，实际 %d", len(cards), n)
	}
	if strings.Contains(html, "/textbook/asset/") {
		t.Error("图集缺失时不应下发封面图片 URL（会全部 404）")
	}
	if !strings.Contains(html, "tb-cover-ph") {
		t.Error("图集缺失时应渲染占位块")
	}
}

// 空状态：没教材时给友好提示，且不残留空网格。
func TestStudyTemplateCoversEmpty(t *testing.T) {
	tmpl := studyTmplForTest(t)
	for _, tc := range []struct {
		name    string
		cards   []gin.H
		grade   string
		wantTip string
	}{
		{"该年级无教材", nil, "六年级", "暂未收录"},
		{"年级未定", nil, "", "还没能识别到你的年级"},
	} {
		t.Run(tc.name, func(t *testing.T) {
			var buf bytes.Buffer
			if err := tmpl.ExecuteTemplate(&buf, "study.html", studyData(tc.cards, tc.grade, "上册")); err != nil {
				t.Fatalf("模板执行失败: %v", err)
			}
			html := buf.String()
			if strings.Contains(html, `<div class="tb-covers">`) {
				t.Error("空状态不应渲染空封面墙")
			}
			if !strings.Contains(html, tc.wantTip) {
				t.Errorf("缺少空状态提示 %q", tc.wantTip)
			}
			// 卡片区本身仍要保留（标题可见），不能整块消失
			if !strings.Contains(html, "官方教材") {
				t.Error("空状态下「官方教材」标题应保留")
			}
		})
	}
}
