package web

import (
	"bytes"
	"html/template"
	"strings"
	"testing"

	"github.com/gin-gonic/gin"
	"studybuddy/internal/auth"
)

// TestArchivePathAdminOnly 「归档目录：archive/<uid>/」这行是磁盘路径，属于运维/排查信息，
// 只应对管理员可见；普通学生看到自己的 uid 目录没有意义，还容易让人误以为能翻目录。
//
// 断言方式：先剥掉 {{/* */}} 注释（说明文字里也提到"归档目录"四个字，不剥会匹配到注释里），
// 再要求这行紧跟在 {{if .Session.IsAdmin}} 之后。仅断言"这行存在"会假绿——整行删掉也能通过。
func TestArchivePathAdminOnly(t *testing.T) {
	body := stripTmplComments(tmplSourceForTest(t, "archive.html"))

	idx := strings.Index(body, "归档目录")
	if idx < 0 {
		t.Fatal("archive.html 里找不到「归档目录」这行，页面头部被改动过？")
	}

	// 往前找最近一个 {{if：必须是 .Session.IsAdmin，而不是别的条件。
	openIdx := strings.LastIndex(body[:idx], "{{if")
	if openIdx < 0 {
		t.Fatal("「归档目录」这行前面没有 {{if}}，等于对所有用户无条件显示")
	}
	guard := body[openIdx : openIdx+strings.Index(body[openIdx:], "}}")+2]
	if !strings.Contains(guard, "Session.IsAdmin") {
		t.Errorf("「归档目录」这行受的条件是 %q，不是 .Session.IsAdmin", strings.TrimSpace(guard))
	}

	// 往后找 {{end：必须在这行之后、且中间不跨越第二个"归档目录"（防止 if 体里套了别的东西）。
	closeIdx := strings.Index(body[idx:], "{{end")
	if closeIdx < 0 {
		t.Fatal("「归档目录」这行后面没有 {{end}}，if 体没闭合，模板会渲染报错")
	}
	if closeIdx += idx; strings.Count(body[idx:closeIdx], "归档目录") != 1 {
		t.Error("「归档目录」与 {{end}} 之间夹了别的内容，权限块可能包错了范围")
	}
}

// archiveTmplForTest 解析真实的 archive.html 及其依赖模板。
// 复用 newFuncMap()——与线上同一份函数集，缺函数会立刻暴露，不会假绿。
func archiveTmplForTest(t *testing.T) *template.Template {
	t.Helper()
	tmpl, err := template.New("").Funcs(newFuncMap()).ParseFS(assetsFS,
		"templates/archive.html", "templates/partials.html")
	if err != nil {
		t.Fatalf("模板解析失败（多半是 archive.html 语法错误）: %v", err)
	}
	return tmpl
}

// archiveData 组一份够 archive.html 渲染的空归档数据。
func archiveData(role string) gin.H {
	return gin.H{
		"Title": "试卷归档", "QT": "choose", "QTCN": "选择题",
		"Exams": []gin.H{}, "AllCount": 0, "QTCount": map[string]int{"choose": 0, "judge": 0},
		"ExamQT":    map[int64]string{},
		"Session":   &auth.Session{Name: "郭奕凡", UserID: 3, Role: role},
		"User":      &auth.Session{Name: "郭奕凡"},
		"HasAvatar": false,
	}
}

// TestArchivePathRenderByRole 用**真实模板**分别以管理员和普通学生身份渲染：
// 管理员能看到归档目录行，普通学生看不到。这是本条需求真正要保证的行为，
// 文本断言（TestArchivePathAdminOnly）只钉住模板结构，两者互补。
func TestArchivePathRenderByRole(t *testing.T) {
	tmpl := archiveTmplForTest(t)
	const marker = "仅可查看本人试卷"

	for _, tc := range []struct {
		role string
		want bool
	}{
		{"admin", true},
		{"user", false},
		{"", false}, // 角色未赋值时按普通用户处理，绝不能默认泄露
	} {
		t.Run("role="+tc.role, func(t *testing.T) {
			var buf bytes.Buffer
			if err := tmpl.ExecuteTemplate(&buf, "archive.html", archiveData(tc.role)); err != nil {
				t.Fatalf("模板执行失败: %v", err)
			}
			html := buf.String()
			if got := strings.Contains(html, marker); got != tc.want {
				if tc.want {
					t.Errorf("管理员应看到「%s」这行，实际未渲染", marker)
				} else {
					t.Errorf("普通用户（role=%q）不应看到「%s」这行，实际渲染出来了", tc.role, marker)
				}
			}
		})
	}
}
