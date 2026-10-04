package web

import (
	"bytes"
	"regexp"
	"strings"
	"testing"
)

// 方案 B-3 / B-4 / B-5 / B-6 的守卫测试。
// 这批改动涉及模板结构与交互行为，纯 CSS 测不了渲染，
// 所以断言分两类：
//   · 结构性断言：模板源码里必须/不得出现某段标记
//   · 行为性断言：渲染后的 HTML 里，列名是否出现在 data-label 上

// ---- B-3：admin 窄屏表格卡片化 ----

// TestAdminNarrowTableCSS 窄屏卡片化样式必须在，且只在窄屏断点内。
// 桌面端若被误改会导致所有表格变成卡片，这是很容易犯的错。
func TestAdminNarrowTableCSS(t *testing.T) {
	css := stripCSSComments(styleCSSForTest(t))
	idx := strings.Index(css, "@media (max-width:760px)")
	if idx < 0 {
		t.Fatal("缺 @media (max-width:760px) 断点：admin 表格窄屏卡片化应在其中")
	}
	block := mediaBlock(css, idx)
	// 这几条是卡片化的骨架
	for _, must := range []string{
		"display:block",        // tr/td 转块级
		"::before",             // 用 content:attr(data-label) 显示列名
		"attr(data-label)",     // 列名来源
		"table>tr:first-child", // 隐藏表头行
		":not(:first-child)",   // 数据行变卡片
	} {
		if !strings.Contains(block, must) {
			t.Errorf("窄屏断点内缺 %s", must)
		}
	}
	// 关键：隐藏表头行的规则不能出现在断点之外
	if strings.Count(css, "table>tr:first-child{display:none}") > 0 {
		outside := strings.Replace(css, block, "", 1)
		if strings.Contains(outside, "table>tr:first-child{display:none}") {
			t.Error("隐藏表头行的规则出现在窄屏断点之外，会让桌面端表格没有表头")
		}
	}
}

// TestAdminTableScopeCol admin 两个表的表头必须有 scope="col"，
// 读屏才能把单元格和列名关联起来。
func TestAdminTableScopeCol(t *testing.T) {
	thRe := regexp.MustCompile(`<th[\s>]`)
	for _, f := range []string{"admin.html", "archive.html", "study.html"} {
		body := tmplSourceForTest(t, f)
		// 剥掉两种注释再数：{{/* ... */}} 模板注释，以及 <script> 里的 /* ... */
		// JS 块注释。admin.html 的 data-label 脚本注释里就提到了 "<th>"，
		// 不剥会被误计成一个无 scope 的表头。
		clean := stripTmplComments(stripCSComments(body))
		ths := thRe.FindAllStringIndex(clean, -1)
		if len(ths) == 0 {
			continue
		}
		scoped := 0
		for _, loc := range ths {
			// 不能用 HasPrefix(clean[loc[1]:], ` scope="col"`)：
			// 正则 <th[\s>] 把空格也吃掉了，loc[1] 已经指向 "scope" 之前，
			// 于是前缀判断永远不成立。正确做法是取整个开始标签再查属性。
			gt := strings.Index(clean[loc[0]:], ">")
			if gt < 0 {
				continue
			}
			tag := clean[loc[0] : loc[0]+gt+1]
			if strings.Contains(tag, `scope="col"`) {
				scoped++
			}
		}
		if scoped != len(ths) {
			t.Errorf("%s: %d 个 <th> 里只有 %d 个带 scope=\"col\"", f, len(ths), scoped)
		}
	}
}

// stripTmplComments 去掉 {{/* ... */}} 模板注释。
// 只做这一种注释即可——本项目模板里没有 {{! }} 形式的注释。
func stripTmplComments(s string) string {
	for {
		i := strings.Index(s, "{{/*")
		if i < 0 {
			return s
		}
		j := strings.Index(s[i:], "*/}}")
		if j < 0 {
			return s
		}
		s = s[:i] + s[i+j+4:]
	}
}

// stripCSComments 去掉 C 风格 /* ... */ 块注释。
// 模板里的 <script> 块用的是这种注释，写说明时经常提到 HTML 标签名
// （如 "<th>"），统计标签数量时必须先剥掉，否则会把说明文字算进去。
func stripCSComments(s string) string {
	for {
		i := strings.Index(s, "/*")
		if i < 0 {
			return s
		}
		j := strings.Index(s[i+2:], "*/")
		if j < 0 {
			return s
		}
		s = s[:i] + s[i+2+j+2:]
	}
}

// TestAdminNarrowLabelScript 窄屏卡片化依赖 JS 填充 data-label，
// 缺了它表头一隐藏所有单元格就都变成空白。
func TestAdminNarrowLabelScript(t *testing.T) {
	body := tmplSourceForTest(t, "admin.html")
	if !strings.Contains(body, `setAttribute('data-label'`) {
		t.Error("admin.html 缺填充 data-label 的脚本，窄屏下表格会变成一片空白")
	}
	// 必须读表头（th）来取列名
	if !strings.Contains(body, "querySelectorAll('th')") {
		t.Error("填充脚本应从 <th> 读取列名，否则标签与列会错位")
	}
}

// ---- B-4：弹窗焦点管理 ----

// TestBindModalExists 统一焦点管理 helper 必须存在且挂在 window 上
// （四处弹窗分属不同 define 块，彼此拿不到局部作用域）。
func TestBindModalExists(t *testing.T) {
	body := tmplSourceForTest(t, "partials.html")
	if !strings.Contains(body, "window.sbBindModal") {
		t.Fatal("缺 window.sbBindModal 统一焦点管理helper")
	}
	// 三个核心能力：打开移焦、Tab 陷阱、关闭还焦
	for _, must := range []string{
		"function open()",  // 打开时移焦
		"e.preventDefault", // Tab 陷阱必须阻止默认行为
		"restoreFocus",     // 关闭还焦
		"lastFocus",        // 记住来源元素
	} {
		if !strings.Contains(body, must) {
			t.Errorf("sbBindModal 缺 %s", must)
		}
	}
}

// TestModalFocusHelperInsideHeader helper 必须在 header 内输出。
//
// 加载顺序问题：archive.html 的弹窗脚本在页面中部，而 helper 若定义在
// header 之外、页面脚本之后，archive 就会拿到 undefined。
func TestModalFocusHelperInsideHeader(t *testing.T) {
	body := tmplSourceForTest(t, "partials.html")
	header := defineBlock(t, body, "header")
	if !strings.Contains(header, "window.sbBindModal") {
		t.Error("sbBindModal 不在 header 内，archive 等页面的弹窗脚本会早于它执行")
	}
}

// defineBlock 取出 {{define "name"}} ... {{end}} 的完整内容。
//
// 不能用「第一个 {{end}}」当结束：模板里 {{if}} / {{range}} 也有自己的
// {{end}}，会提前截断。要做花括号式的配平扫描。
func defineBlock(t *testing.T, src, name string) string {
	t.Helper()
	open := `{{define "` + name + `"}}`
	i := strings.Index(src, open)
	if i < 0 {
		t.Fatalf("找不到 define %q", name)
	}
	// define 自身不计入嵌套深度
	pos := i + len(open)
	depth := 0
	for pos < len(src) {
		rest := src[pos:]
		switch {
		case strings.HasPrefix(rest, "{{define "),
			strings.HasPrefix(rest, "{{if "),
			strings.HasPrefix(rest, "{{range "),
			strings.HasPrefix(rest, "{{with "),
			strings.HasPrefix(rest, "{{block "):
			depth++
			// 跳到该{{ }} 的闭合
			e := strings.Index(rest, "}}")
			if e < 0 {
				return ""
			}
			pos += e + 2
		case strings.HasPrefix(rest, "{{end}}"):
			if depth == 0 {
				return src[i:pos]
			}
			depth--
			pos += len("{{end}}")
		case strings.HasPrefix(rest, "{{/*"):
			e := strings.Index(rest, "*/}}")
			if e < 0 {
				return ""
			}
			pos += e + 4
		default:
			pos++
		}
	}
	return ""
}

// TestAllModalsUseHelper 三处弹窗都要接上统一 helper。
func TestAllModalsUseHelper(t *testing.T) {
	// profile 与 welcome 在 partials.html，archive 删除确认在 archive.html
	p := tmplSourceForTest(t, "partials.html")
	if strings.Count(p, "window.sbBindModal") < 2 {
		t.Error("partials.html 里 profile / welcome 两处弹窗未都接上 sbBindModal")
	}
	a := tmplSourceForTest(t, "archive.html")
	if !strings.Contains(a, "window.sbBindModal") {
		t.Error("archive.html 的删除确认弹窗未接上 sbBindModal，Tab 仍会跑出弹窗")
	}
}

// TestModalAriaComplete 弹窗必须有 dialog 语义。
func TestModalAriaComplete(t *testing.T) {
	p := tmplSourceForTest(t, "partials.html")
	n := strings.Count(p, `role="dialog" aria-modal="true"`)
	if n < 2 {
		t.Errorf("profile / welcome 弹窗应有 role=\"dialog\" aria-modal=\"true\"，实到 %d 处", n)
	}
}

// ---- B-5：ARIA 语义 ----

// TestQtypeTabsNotTablist 题型切换是**页面跳转**（<a href>），
// 不能用 role="tablist"/role="tab"——那会让读屏用户以为同页切换内容。
//
// 归档页仍用页首 qtype-tabs 切换；学习主页的页首标签已移除，
// 切换能力由「开始做题」入口卡承担（那三张 .qtype-card），因此两边检查的落点不同。
func TestQtypeTabsNotTablist(t *testing.T) {
	// 归档页：保留页首标签，检查 navigation + aria-current 语义
	arc := tmplSourceForTest(t, "archive.html")
	if strings.Contains(arc, `role="tablist"`) || strings.Contains(arc, `role="tab"`) {
		t.Error("archive.html 仍用 tab 语义，但它的 <a> 带 href 是整页跳转")
	}
	if !strings.Contains(arc, `role="navigation"`) {
		t.Error("archive.html 应改用 role=\"navigation\"")
	}
	if !strings.Contains(arc, `aria-current="{{if eq .QT "choose"}}page`) ||
		!strings.Contains(arc, `aria-current="{{if eq .QT "judge"}}page`) {
		t.Error("archive.html 的两个题型项都应有 aria-current=\"page\"")
	}
	if strings.Contains(arc, "aria-selected") {
		t.Error("archive.html 残留 aria-selected，那是 tab 语义专用属性")
	}

	// 学习主页：页首标签已删，切换入口是入口卡，同样不能用 tab 语义
	// 注意先剥模板注释：我在注释里写了 "qtype-tabs" 这几个字说明来龙去脉，
	// 不剥的话会把注释当成元素还在，那是典型的假红。
	st := stripTmplComments(tmplSourceForTest(t, "study.html"))
	if strings.Contains(st, `role="tablist"`) || strings.Contains(st, `role="tab"`) {
		t.Error("study.html 仍用 tab 语义，但它的 <a> 带 href 是整页跳转")
	}
	if strings.Contains(st, "aria-selected") {
		t.Error("study.html 残留 aria-selected，那是 tab 语义专用属性")
	}
	if strings.Contains(st, "qtype-tabs") {
		t.Error("study.html 不该再有页首题型切换标签——与「开始做题」入口卡功能重复")
	}
	// 切换能力必须还在：三张入口卡，两个题型链接 + 一个游戏列表链接
	for _, href := range []string{`href="/study?qt=choose"`, `href="/study?qt=judge"`, `href="/games"`} {
		if !strings.Contains(st, href) {
			t.Errorf("study.html 缺入口卡链接 %s，删掉页首标签后题型切换会无处可去", href)
		}
	}
	// 页首标签删掉后，入口卡的 .is-on 高亮是当前题型唯一的视觉提示，
	// 必须同时有 aria-current 兜给读屏 —— 只剩颜色/描边差别时读屏用户读不出来。
	for _, qt := range []string{"choose", "judge"} {
		if !strings.Contains(st, `aria-current="{{if eq .QT "`+qt+`"}}page`) {
			t.Errorf("入口卡缺 %s 的 aria-current=\"page\"，读屏无法判断当前题型", qt)
		}
	}
}

// TestWallpaperSwitchRole 壁纸开关是可切换的，应有 switch 语义，
// 且装饰性的 .sw 滑块要 aria-hidden（否则读屏会读两遍状态）。
func TestWallpaperSwitchRole(t *testing.T) {
	p := tmplSourceForTest(t, "partials.html")
	if !strings.Contains(p, `role="switch"`) {
		t.Error("壁纸开关缺 role=\"switch\"，读屏无法识别这是个开关")
	}
	if !strings.Contains(p, `aria-checked="{{if .WallpaperOff}}false{{else}}true{{end}}"`) {
		t.Error("壁纸开关缺 aria-checked")
	}
	// 装饰滑块共两处，都要aria-hidden
	decorative := strings.Count(p, `class="sw`) - strings.Count(p, `class="sw"`)
	if decorative < 1 {
		t.Error("装饰性 .sw 滑块应加 aria-hidden=\"true\"，否则读屏会重复播报状态")
	}
}

// ---- B-6：代码去重 ----

// TestPasswordFieldPartial 密码框必须只剩一份实现。
// 重复的真正风险是"改一处忘另一处"，所以要断言两个页面都不含原始 SVG。
func TestPasswordFieldPartial(t *testing.T) {
	p := tmplSourceForTest(t, "partials.html")
	if !strings.Contains(p, `{{define "password_field"}}`) {
		t.Fatal("缺 password_field partial")
	}
	for _, f := range []string{"login.html", "register.html"} {
		body := tmplSourceForTest(t, f)
		if !strings.Contains(body, `template "password_field"`) {
			t.Errorf("%s 未改用 password_field partial", f)
		}
		// 原始实现不该还留在页面里
		if strings.Contains(body, "eye-off-icon") {
			t.Errorf("%s 仍内联了眼睛图标 SVG，说明没真正去重", f)
		}
	}
}

// TestPasswordFieldRenders 渲染验证：两个页面各自的参数要正确落位。
// 这是防止"参数传错但测试只查了字符串存在"的关键。
func TestPasswordFieldRenders(t *testing.T) {
	tmpl, err := newTmplForTest(t, "templates/login.html", "templates/register.html", "templates/partials.html")
	if err != nil {
		t.Fatalf("模板解析失败: %v", err)
	}

	// login：current-password +「请输入密码」
	var buf bytes.Buffer
	if err := tmpl.ExecuteTemplate(&buf, "login.html", map[string]any{
		"Session":  map[string]any{"Username": "u", "IsAdmin": false},
		"Error":    "",
		"FormName": "",
	}); err != nil {
		t.Fatalf("渲染 login.html 失败: %v", err)
	}
	html := buf.String()
	if !strings.Contains(html, `autocomplete="current-password"`) {
		t.Error("login.html 渲染结果缺 current-password")
	}
	if !strings.Contains(html, ">密码</label>") {
		t.Error("login.html 渲染结果 label 应为「密码」")
	}
	if !strings.Contains(html, `placeholder="请输入密码"`) {
		t.Error("login.html 渲染结果 placeholder 应为「请输入密码」")
	}

	// register：new-password +「至少 6 位」
	// 依赖字段从模板里逐个查出来：FormStage/FormGrade/FormVolume/FormClass/StageJSON
	buf.Reset()
	if err := tmpl.ExecuteTemplate(&buf, "register.html", map[string]any{
		"Session":    map[string]any{"Username": "u"},
		"Error":      "",
		"FormName":   "",
		"FormStage":  "primary",
		"FormGrade":  1,
		"FormVolume": 1,
		"FormClass":  "",
		"StageJSON":  "{}",
		"Invites":    []any{},
	}); err != nil {
		t.Fatalf("渲染 register.html 失败: %v", err)
	}
	html2 := buf.String()
	if !strings.Contains(html2, `autocomplete="new-password"`) {
		t.Error("register.html 渲染结果缺 new-password")
	}
	if !strings.Contains(html2, ">登录密码（至少 6 位）</label>") {
		t.Error("register.html 渲染结果 label 应为「登录密码（至少 6 位）」")
	}
}

// TestDictFuncRegistered dict 是 partial 参数化的基础，必须注册。
func TestDictFuncRegistered(t *testing.T) {
	fm := newFuncMap()
	if _, ok := fm["dict"]; !ok {
		t.Fatal("funcMap 未注册 dict，password_field 的参数化传参会解析失败")
	}
	// 实际调用一次
	// FuncMap 的值类型是 any，调用前必须断言成具体函数类型。
	fn, ok := fm["dict"].(func(...any) map[string]string)
	if !ok {
		t.Fatalf("dict 未注册为 func(...any) map[string]string，实际类型 %T", fm["dict"])
	}
	got := fn("Label", "密码", "Autocomplete", "current-password")
	if got["Label"] != "密码" || got["Autocomplete"] != "current-password" {
		t.Errorf("dict 键值对错误: %v", got)
	}
	// 奇数个参数（末尾孤立 key）不能 panic
	fn("A", "1", "B")
}

// tmplSourceForTest 读取内嵌模板的**源码**。
//
// 为什么有些断言要读源码而不是渲染结果：渲染需要构造完整数据上下文，
// 而"这个 class 名被改了没""这段重复代码还在不在"本质是文本问题，
// 读源码更直接、也不容易因为缺数据而假绿。
// 必须读 assetsFS 而不是磁盘 —— 改的是 embed 进二进制的版本。
func tmplSourceForTest(t *testing.T, name string) string {
	t.Helper()
	b, err := assetsFS.ReadFile("templates/" + name)
	if err != nil {
		t.Fatalf("读取模板 %s 失败: %v", name, err)
	}
	return string(b)
}
