package web

import (
	"bytes"
	"html/template"
	"regexp"
	"strings"
	"testing"
)

// lessonStatRe 匹配课程页统计卡里的单个 .stat 卡片。
// 捕获 num 与 cap 两段文字，用来验证 DOM 结构与文案没被动过。
var lessonStatRe = regexp.MustCompile(`<div class="stat"><div class="num">([^<]*)</div><div class="cap">([^<]*)</div></div>`)

// lessonTmplForTest 解析真实的 lesson.html + partials.html。
// 复用 newFuncMap()——与线上同一份函数集，缺函数会立刻暴露。
func lessonTmplForTest(t *testing.T) *template.Template {
	t.Helper()
	tmpl, err := template.New("").Funcs(newFuncMap()).ParseFS(assetsFS,
		"templates/lesson.html", "templates/partials.html")
	if err != nil {
		t.Fatalf("模板解析失败: %v", err)
	}
	return tmpl
}

// TestLessonStatGridDesktopFourColumns 桌面端必须单行 4 列。
//
// 需求要求「一行横向 4 列、均分宽度」。这里显式写死 repeat(4,1fr)，
// 而不是 auto-fit——auto-fit 在 200px 下限下宽屏可能退化成 3 列，列数不确定。
func TestLessonStatGridDesktopFourColumns(t *testing.T) {
	css := styleCSSForTest(t)

	if !strings.Contains(css, "grid-template-columns:repeat(4,1fr)") {
		t.Error(".stat-grid 缺桌面端 repeat(4,1fr)，宽屏不会排成一行 4 列")
	}
	// 4 列必须是 .stat-grid 上的，且 .grid 全局不能被改成固定 4 列
	for _, rule := range cssRules(css) {
		sel, body := splitRule(rule)
		sel = strings.TrimSpace(sel)
		if sel != ".stat-grid" {
			continue
		}
		if strings.Contains(body, "repeat(4,1fr)") &&
			strings.Contains(sel, "auto-fit") {
			t.Error(".stat-grid 不应再叠加 auto-fit，会让列数不确定")
		}
	}
}

// TestLessonStatGridMobileTwoColumns 移动端必须切 2×2。
//
// 需求写明「两行两列」，所以列数必须是 2 而不是 1——
// 手机竖屏排 1 列会让卡片过于瘦长，且与"移动端 2×2"要求不符。
func TestLessonStatGridMobileTwoColumns(t *testing.T) {
	css := styleCSSForTest(t)

	// 全站有十几个 @media (max-width:640px)，不能只找第一个——
	// 必须定位「声明了 .stat-grid 的那个断点」，否则会读到别的模块的窄屏规则。
	// 在「剥掉注释」的文本上找，避免命中注释里写的 .stat-grid 字样。
	clean := stripCSSComments(css)
	idx := strings.Index(clean, ".stat-grid{grid-template-columns:repeat(2,1fr)")
	if idx < 0 {
		t.Fatal("找不到声明 .stat-grid 两列的窄屏媒体查询")
	}
	// 从该下标往前找最近的 @media 起点
	mediaStart := strings.LastIndex(clean[:idx], "@media")
	if mediaStart < 0 {
		t.Fatal(".stat-grid 两列规则不在任何 @media 内，桌面端也会变两列")
	}
	block := mediaBlock(clean, mediaStart)
	if !strings.Contains(block, "repeat(2,1fr)") {
		t.Error("窄屏断点内缺 repeat(2,1fr)，移动端未切成 2 列（2×2）")
	}
	if !strings.Contains(clean[mediaStart:idx], "max-width:640px") {
		t.Error("2 列规则应挂在 max-width:640px 断点下")
	}

	// 极窄屏仍须保持 2 列（只有 <380px 一个额外断点，不允许再降到单列）
	if i380 := strings.Index(clean, "@media (max-width:380px)"); i380 >= 0 {
		block380 := mediaBlock(clean, i380)
		if strings.Contains(block380, "grid-template-columns:repeat(1") {
			t.Error("极窄屏把统计卡降到单列了，需求要求全程 2×2")
		}
	}
}

// stripCSSComments 剥掉 /* */ 注释，保留其余字符与大致位置关系。
// 用于在「真实规则」而非「说明文字」上做定位。
//
// 同时把 CRLF 归一化成 LF。原因是仓库 core.autocrlf=true，Windows 上
// checkout 出来的工作区文件是 CRLF、git 仓库里是 LF，同一份断言在
// 两边跑结果不同——TestToastSingleComponent 就这么假红过一次。
// CSS 语义与换行符无关，测试也不该关心，所以在这里一次性收口。
func stripCSSComments(css string) string {
	var b strings.Builder
	for i := 0; i < len(css); {
		if s, ok := strings.CutPrefix(css[i:], "/*"); ok {
			if e := strings.Index(s, "*/"); e >= 0 {
				i += 2 + e + 2
				continue
			}
			break
		}
		// CRLF 只留 LF，否则跨行断言（形如 "a,\nb{"）会因平台而失效
		if css[i] == '\r' && i+1 < len(css) && css[i+1] == '\n' {
			b.WriteByte('\n')
			i += 2
			continue
		}
		b.WriteByte(css[i])
		i++
	}
	return b.String()
}

// TestLessonStatGridDoesNotBreakGlobalGrid .stat-grid 不能污染全站 .grid。
//
// .grid 被 admin.html 的「新建账号」表单共用（里面是 label 表单域）。
// 若把 .grid 全局改成固定 4 列，那个表单会被挤成四列排版。
func TestLessonStatGridDoesNotBreakGlobalGrid(t *testing.T) {
	css := styleCSSForTest(t)

	// 原始 .grid 规则必须还在，且仍是 auto-fit 形态
	if !strings.Contains(css, ".grid{display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr))") {
		t.Error("全局 .grid 定义被改动或删除，admin 新建账号表单会受影响")
	}

	// admin.html 的表单仍应挂 .grid（而不是被误改成 .stat-grid）。
	// 直接断言模板源码里的类名 —— 这才是要防的东西（类名被改）。
	// 不用渲染整个 admin.html：它依赖 Invites/Users/Stages 等一整套结构，
	// 为了查一个 class 名构造这些数据不划算。
	b, err := assetsFS.ReadFile("templates/admin.html")
	if err != nil {
		t.Fatalf("读取 admin.html 失败: %v", err)
	}
	adminHTML := string(b)
	if !strings.Contains(adminHTML, `class="grid" id="admin-create"`) {
		t.Error("admin.html 的新建账号表单类名被改了，应保持 class=\"grid\"")
	}
	if strings.Contains(adminHTML, "stat-grid") {
		t.Error("admin.html 表单不应挂 .stat-grid，那是课程页统计卡专用类")
	}
}

// TestLessonStatGridDOMUnchanged DOM 结构与文字内容必须原样保留。
//
// 需求第 2、3 条：不改内部 html，文字数字排版保持原样。
func TestLessonStatGridDOMUnchanged(t *testing.T) {
	tmpl := lessonTmplForTest(t)

	data := map[string]any{
		"Title": "课程详情",
		"Lesson": map[string]any{
			"SubjectCN": "语文", "Title": "观潮",
			"Grade": "四年级", "VolumeLabel": "上册",
			"UnitLabel": "第一单元", "LessonLabel": "01 观潮",
		},
		"Bank":     152618,
		"Progress": map[string]any{"Attempts": 0, "BestScore": 0, "Status": "new"},
		"Pass":     80,
		"Session":  nil,
		"User":     nil,
	}

	var buf bytes.Buffer
	if err := tmpl.ExecuteTemplate(&buf, "lesson.html", data); err != nil {
		t.Fatalf("渲染 lesson.html 失败: %v", err)
	}
	html := buf.String()

	// 必须挂上专用类
	if !strings.Contains(html, `class="grid stat-grid"`) {
		t.Error("统计卡容器缺少 stat-grid 专用类，响应式规则不会生效")
	}

	// 四个 stat 卡片都在，且 num / cap 文案一字未改
	got := lessonStatRe.FindAllStringSubmatch(html, -1)
	if len(got) != 4 {
		t.Fatalf("统计卡数量应恒为 4，实际 %d", len(got))
	}
	want := [][2]string{
		{"152618", "本题库题数"},
		{"0", "已自测次数"},
		{"0", "历史最高分"},
		{"80", "达标分数线"},
	}
	for i, w := range want {
		if got[i][1] != w[0] {
			t.Errorf("第 %d 张卡数值被改：期望 %s，实际 %s", i+1, w[0], got[i][1])
		}
		if got[i][2] != w[1] {
			t.Errorf("第 %d 张卡标签被改：期望 %s，实际 %s", i+1, w[1], got[i][2])
		}
	}

	// 底部外边距 14px 保留
	if !strings.Contains(html, `class="grid stat-grid" style="margin-bottom:14px"`) {
		t.Error("统计卡容器丢了 margin-bottom:14px")
	}
}

// mediaBlock 从某个 @media 起点开始，取出该媒体查询区块的花括号内容。
func mediaBlock(css string, start int) string {
	open := strings.Index(css[start:], "{")
	if open < 0 {
		return ""
	}
	open += start
	depth, i := 0, open
	for ; i < len(css); i++ {
		switch css[i] {
		case '{':
			depth++
		case '}':
			depth--
			if depth == 0 {
				return css[open : i+1]
			}
		}
	}
	return css[open:]
}

// unionMediaBlocks 把所有以 at 开头的媒体查询区块的花括号内容拼起来。
//
// 为什么需要它：媒体查询段会随新功能不断追加，「取最后一个段」这种定位
// 假设必然随文件增长而失效（TestUICoarseHitAreaFallback 就这么假红过）。
// 凡是"这些选择器在触屏/打印等条件下有没有被处理到"的断言，都该在这里
// 联合查找，而不是赌某一段。
func unionMediaBlocks(css, at string) string {
	var b strings.Builder
	for i := 0; ; {
		j := strings.Index(css[i:], at)
		if j < 0 {
			return b.String()
		}
		j += i
		// 避免 "@media (pointer:coarse)" 命中 "@media (pointer:coarse-x)" 这类前缀重叠
		if k := j + len(at); k < len(css) && css[k] == '-' {
			i = k
			continue
		}
		b.WriteString(mediaBlock(css, j))
		b.WriteByte('\n')
		i = j + len(at)
	}
}
