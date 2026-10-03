package web

import (
	"html/template"
	"io"
	"strings"
	"testing"
)

// styleCSSForTest 读取随二进制内嵌的 style.css。
// CSS 是 go:embed 进来的，测试必须读同一份，否则改了样式但测试还在看旧文件。
func styleCSSForTest(t *testing.T) string {
	t.Helper()
	f, err := assetsFS.Open("static/style.css")
	if err != nil {
		t.Fatalf("读取内嵌 style.css 失败: %v", err)
	}
	defer f.Close()
	b, err := io.ReadAll(f)
	if err != nil {
		t.Fatalf("读取 style.css 内容失败: %v", err)
	}
	return string(b)
}

// cssRules 从样式表里抽出所有规则块（"选择器{声明}" 形式），
// 同时跳过 /* 注释 */——注释里会写"不要用 position:fixed"之类的说明，
// 直接搜字符串会把注释当成真规则，误报。
func cssRules(css string) []string {
	var out []string
	// 先剥注释，避免说明文字干扰
	var b strings.Builder
	for i := 0; i < len(css); {
		if s, ok := strings.CutPrefix(css[i:], "/*"); ok {
			if e := strings.Index(s, "*/"); e >= 0 {
				i += 2 + e + 2
				continue
			}
			break // 注释未闭合，后面的都是注释
		}
		b.WriteByte(css[i])
		i++
	}
	clean := b.String()

	for {
		s := strings.Index(clean, "{")
		if s < 0 {
			return out
		}
		e := strings.Index(clean[s:], "}")
		if e < 0 {
			return out
		}
		out = append(out, clean[:s+1+e])
		clean = clean[s+1+e:]
	}
}

// splitRule 把 "选择器{声明}" 拆成选择器与声明体。
func splitRule(rule string) (sel, body string) {
	s := strings.Index(rule, "{")
	if s < 0 {
		return rule, ""
	}
	return rule[:s], rule[s:]
}

// newTmplForTest 解析模板文件，供页脚文案类断言复用。
func newTmplForTest(t *testing.T, files ...string) (*template.Template, error) {
	t.Helper()
	return template.New("").Funcs(newFuncMap()).ParseFS(assetsFS, files...)
}

// TestStickyFooterLayout 锁定「sticky 页脚」的三条实现约束。
//
// 需求：页脚始终贴在页面最底部 ——
//	内容 < 视口 → 页脚落在视口底；内容 > 视口 → 页脚跟在文档末尾（不悬浮）。
//
// 这是纯 CSS 行为，Go 测不了渲染结果，但可以钉死实现方式不被改坏：
// 一旦有人把 flex 布局换掉、或把页脚改成 position:fixed，测试就会红。
func TestStickyFooterLayout(t *testing.T) {
	css := styleCSSForTest(t)

	// 1. body 必须是纵向 flex 容器 + 最小高度撑满视口，
	//    main 才能吃掉剩余空间把页脚压到底部。
	if !strings.Contains(css, "flex-direction:column") {
		t.Error("body 未设为纵向 flex 容器（缺 flex-direction:column）")
	}
	// min-height 必须有 100vh 兜底；svh 解决移动端地址栏遮挡。
	// 顺序上 100vh 必须在 100svh 之前，老浏览器不支持 svh 时逐条回退。
	idxVh := strings.Index(css, "min-height:100vh")
	idxSvh := strings.Index(css, "min-height:100svh")
	if idxVh < 0 {
		t.Error("body 缺 min-height:100vh，短页面无法撑到视口底部")
	}
	if idxSvh < 0 {
		t.Error("body 缺 min-height:100svh，移动端地址栏会把页脚顶出可视区")
	}
	if idxVh > idxSvh {
		t.Error("min-height:100vh 必须写在 100svh 之前，作老浏览器回退")
	}

	// 2. main 吃掉剩余高度 —— flex:1 0 auto。
	//    0(auto 基线) + 可增长 + 不收缩：内容短时撑满，内容长时不被压扁。
	if !strings.Contains(css, "main{flex:1 0 auto}") {
		t.Error("main 缺 flex:1 0 auto，短内容时页脚无法被压到视口底部")
	}

	// 3. 页脚必须能正常收缩盒子的高度（内容多时不塌）。
	if !strings.Contains(css, ".foot{flex-shrink:0}") {
		t.Error(".foot 缺 flex-shrink:0，内容异常时页脚可能被压扁")
	}
}

// TestFootNotPositionFixed 页脚绝不能做成 fixed 悬浮。
//
// 这是本需求最容易踩的坑：position:fixed 会让页脚永远钉在屏幕底部，
// 内容长时遮住正文且随页面滚动错位 —— 那是"固定悬浮"，不是"sticky 粘底"。
func TestFootNotPositionFixed(t *testing.T) {
	css := styleCSSForTest(t)

	// 收集所有 .foot 开头的规则块（正文规则，排除注释里的说明文字）
	for _, rule := range cssRules(css) {
		sel, body := splitRule(rule)
		if !strings.Contains(sel, ".foot") {
			continue
		}
		if strings.Contains(body, "position:fixed") ||
			strings.Contains(body, "position: fixed") {
			t.Errorf("页脚规则「%s」含 position:fixed —— 页脚会悬浮遮挡正文，"+
				"应改为 body flex + main{flex:1} 的 sticky 方案", strings.TrimSpace(sel))
		}
		if strings.Contains(body, "position:sticky") {
			t.Errorf("页脚规则「%s」含 position:sticky —— 页脚自身不需要 sticky，"+
				"粘底由 body flex 布局完成", strings.TrimSpace(sel))
		}
	}
}

// TestAuthPageNotFlex 登录 / 注册页必须保持 block 布局。
//
// auth 页走 footer_auth，body 里既没有 main 也没有 .foot，
// 若被 flex 接管，.auth-wrap 的 grid 布局会被纵向 flex 干扰。
func TestAuthPageNotFlex(t *testing.T) {
	css := styleCSSForTest(t)
	if !strings.Contains(css, "body.auth-page{display:block}") {
		t.Error("登录/注册页缺 body.auth-page{display:block} 回退，" +
			"全局 body flex 会波及 .auth-wrap 的 grid 布局")
	}
}

// TestStickyFooterKeepsCopy 页脚文案不得被这次改动弄丢。
func TestStickyFooterKeepsCopy(t *testing.T) {
	tmpl, err := newTmplForTest(t, "templates/partials.html")
	if err != nil {
		t.Fatalf("解析 partials.html 失败: %v", err)
	}
	var sb strings.Builder
	if err := tmpl.ExecuteTemplate(&sb, "footer", nil); err != nil {
		t.Fatalf("执行 footer 模板失败: %v", err)
	}
	if !strings.Contains(sb.String(), "每个学生独立数据库，学习数据完全隔离") {
		t.Error("页脚说明文案丢失")
	}
}