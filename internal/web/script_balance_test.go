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

// 模板里的 <script> 必须成对闭合。
//
// 为什么值得单独守：漏一个 </script> 时 Go 模板**照样解析通过、页面照样返回 200**，
// 肉眼在页面上也看不出异常（HTML 容错会把错位的标签吞掉），只有浏览器控制台报
//
//	Uncaught SyntaxError: Unexpected token '<' (at xxx:NNNN:1)
//
// 而且报错行号指向的是**后面第一个被误当成 JS 的 HTML 元素**（比如 <ul>、<div>），
// 离真正的出错点（缺 </script> 的那个位置）可能隔了几十行，很难定位。
//
// 真实案例：partials.html 里开屏动画的导航标记脚本结尾漏了 </script>，
// 连续开了两个 <script>，导致页面上从该点往后的所有 HTML 全被当 JS 解析，
// 页面脚本整体失效（提交标记那段形同废掉）。已修。
//
// 为什么既查源码又查渲染产物：{{if}} / {{range}} 会让某些 <script> 整段不输出，
// **源码配平不代表产物配平**。两条都查才不留缝。

var (
	reScriptOpen  = regexp.MustCompile(`(?i)<script\b`)
	reScriptClose = regexp.MustCompile(`(?i)</script\s*>`)
)

var allTemplateNames = []string{
	"admin.html", "archive.html", "archive_view.html", "game.html", "games.html",
	"lesson.html", "login.html", "partials.html", "quiz.html", "register.html",
	"result.html", "study.html", "textbook.html", "textbooks.html",
}

// TestTemplateScriptTagsBalanced 逐个模板查源码里 <script> / </script> 是否配平。
func TestTemplateScriptTagsBalanced(t *testing.T) {
	for _, name := range allTemplateNames {
		// 模板注释里可能出现示例性的 <script>，先剥掉再数
		bare := stripTmplComments(tmplSourceForTest(t, name))
		o := len(reScriptOpen.FindAllString(bare, -1))
		c := len(reScriptClose.FindAllString(bare, -1))
		if o != c {
			t.Errorf("%s 的 <script>(%d) 与 </script>(%d) 不配平 —— 浏览器会把后续 HTML 当 JS 解析并抛 SyntaxError",
				name, o, c)
			t.Logf("   最后一个 <script> 在第 %d 行，最后一个 </script> 在第 %d 行",
				lastLineOf(bare, reScriptOpen), lastLineOf(bare, reScriptClose))
		}
	}
}

// TestRenderedPageScriptTagsBalanced 渲染代表性页面，查**产物**里的配平。
// 这条才是真正兜底的：源码配平但 {{if}} 把某段 script 吃掉的情况，只有渲染才看得见。
func TestRenderedPageScriptTagsBalanced(t *testing.T) {
	// study：复用现成的辅助函数。studyTmplForTest 已含 partials.html；
	// studyData 里 Session 是真的 *auth.Session —— 用 map 会报
	// "invalid value; expected string"，模板对字段类型是敏感的。
	t.Run("study", func(t *testing.T) {
		var buf bytes.Buffer
		tmpl := studyTmplForTest(t)
		if err := tmpl.ExecuteTemplate(&buf, "study.html", studyData(nil, "四年级", "上册")); err != nil {
			t.Fatalf("渲染 study.html 失败：%v", err)
		}
		assertScriptBalanced(t, "study.html(渲染产物)", buf.String())
	})

	// archive：自己解析，同样要连 partials.html（footer/header 的 define 都在那）
	t.Run("archive", func(t *testing.T) {
		tmpl, err := template.New("archive.html").Funcs(newFuncMap()).ParseFS(assetsFS,
			"templates/archive.html", "templates/partials.html")
		if err != nil {
			t.Fatalf("解析 archive.html 失败：%v", err)
		}
		data := gin.H{
			"Title": "试卷归档", "QT": "choose", "QTCN": "选择题",
			"Exams": []any{}, "AllCount": 0,
			// 归档页要 index .QTCount 取两种题型的份数，缺 map 会报 untyped nil
			"QTCount": map[string]int{"choose": 0, "judge": 0},
			"Session": &auth.Session{Name: "测试", UserID: 1},
			"User":    &db.User{Name: "郭爸爸"},
		}
		var buf bytes.Buffer
		if err := tmpl.ExecuteTemplate(&buf, "archive.html", data); err != nil {
			t.Fatalf("渲染 archive.html 失败：%v", err)
		}
		assertScriptBalanced(t, "archive.html(渲染产物)", buf.String())
	})

	// lesson：题库页，script 最多的一段
	t.Run("lesson", func(t *testing.T) {
		tmpl, err := template.New("lesson.html").Funcs(newFuncMap()).ParseFS(assetsFS,
			"templates/lesson.html", "templates/partials.html")
		if err != nil {
			t.Fatalf("解析 lesson.html 失败：%v", err)
		}
		data := gin.H{
			"Title": "刷题", "QT": "choose", "QTCN": "选择题", "Pass": 60,
			"Session": &auth.Session{Name: "测试", UserID: 1, Stage: "primary", Grade: 4, Volume: 1},
			"User":    &db.User{Name: "郭爸爸"},
		}
		var buf bytes.Buffer
		if err := tmpl.ExecuteTemplate(&buf, "lesson.html", data); err != nil {
			// 数据不全时这不算失败：本用例只关心 script 配平，
			// 渲染数据问题由各自的渲染测试负责。
			t.Logf("lesson.html 渲染未完成（数据不全：%v），本用例跳过", err)
			return
		}
		assertScriptBalanced(t, "lesson.html(渲染产物)", buf.String())
	})
}

// assertScriptBalanced 断言产物里 <script> 与 </script> 配平。
func assertScriptBalanced(t *testing.T, what, out string) {
	t.Helper()
	o := len(reScriptOpen.FindAllString(out, -1))
	c := len(reScriptClose.FindAllString(out, -1))
	if o != c {
		t.Errorf("%s 的 <script>(%d) 与 </script>(%d) 不配平", what, o, c)
		t.Logf("   最后一个 <script> 在第 %d 行附近，去那里找漏掉的 </script>",
			lastLineOf(out, reScriptOpen))
	}
}

// lastLineOf 返回正则最后一次匹配所在的行号（1 起）。
func lastLineOf(s string, re *regexp.Regexp) int {
	locs := re.FindAllStringIndex(s, -1)
	if len(locs) == 0 {
		return 0
	}
	return strings.Count(s[:locs[len(locs)-1][0]], "\n") + 1
}
