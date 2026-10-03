package web

import (
	"html/template"
	"strings"
	"testing"
)

// TestFooterRepoLink 页脚「StudyBuddy」必须链到 GitHub 仓库。
//
// 这条看着琐碎，但页脚是全站 9 个页面共用的 partial（admin / archive /
// archive_view / lesson / quiz / result / study / textbook / textbooks），
// 改一处错一处就会全站丢链接，所以在这里钉死。
func TestFooterRepoLink(t *testing.T) {
	tmpl, err := template.New("").Funcs(newFuncMap()).ParseFS(assetsFS, "templates/partials.html")
	if err != nil {
		t.Fatalf("解析 partials.html 失败: %v", err)
	}

	var sb strings.Builder
	// footer 会引用 fab_dock，这里只验页脚本身，缺 partial 时按缺省空输出处理
	if err := tmpl.ExecuteTemplate(&sb, "footer", nil); err != nil {
		t.Fatalf("执行 footer 模板失败: %v", err)
	}
	html := sb.String()

	const want = `href="https://github.com/meimolihan/StudyBuddy"`
	if !strings.Contains(html, want) {
		t.Errorf("页脚缺少仓库链接 %s\n实际输出: %s", want, html)
	}
	// 外链必须新窗口打开，且带 noopener / noreferrer：
	// noopener 防目标页反向操纵本页，noreferrer 顺带挡住 Referer 泄漏。
	for _, attr := range []string{`target="_blank"`, `rel="noopener noreferrer"`} {
		if !strings.Contains(html, attr) {
			t.Errorf("页脚外链缺少安全属性 %s", attr)
		}
	}
	// 页脚说明文案必须保留（不能因为加链接把话删了）
	if !strings.Contains(html, "每个学生独立数据库，学习数据完全隔离") {
		t.Error("页脚说明文案丢失")
	}
	// 链接只包住项目名，"·" 及后面的说明必须在链接外，否则整行都变蓝
	if !strings.Contains(html, `>StudyBuddy</a> · 每个学生`) {
		t.Errorf("链接范围有误，应只包住项目名\n实际: %s", html)
	}
}

// TestFooterRepoLinkNotInAuthFooter 登录 / 注册页走的是 footer_auth，
// 那个页脚本来就没有这句话，不要被本次改动波及。
func TestFooterRepoLinkNotInAuthFooter(t *testing.T) {
	tmpl, err := template.New("").Funcs(newFuncMap()).ParseFS(assetsFS, "templates/partials.html")
	if err != nil {
		t.Fatalf("解析 partials.html 失败: %v", err)
	}
	var sb strings.Builder
	if err := tmpl.ExecuteTemplate(&sb, "footer_auth", nil); err != nil {
		t.Fatalf("执行 footer_auth 模板失败: %v", err)
	}
	if strings.Contains(sb.String(), "foot-repo") {
		t.Error("登录页页脚不应出现仓库链接（它用的是 footer_auth）")
	}
}
