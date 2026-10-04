// Command dumpjs 把真实渲染页面里的内联 <script> 抽出来落盘，供 node --check 做语法体检。
// 临时工具：模板里的 JS 写错了，浏览器只会静默不生效，Go 编译与 e2e 都发现不了。
package main

import (
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"path/filepath"
	"regexp"
	"strings"

	"studybuddy/internal/config"
	"studybuddy/internal/db"
	"studybuddy/internal/textbook"
	"studybuddy/internal/web"
)

var reScript = regexp.MustCompile(`(?s)<script(?:\s[^>]*)?>(.*?)</script>`)

func main() {
	tmp, _ := os.MkdirTemp("", "studybuddy-dumpjs")
	abs := func(p string) string { a, _ := filepath.Abs(p); return a }
	cfg := config.Load()
	cfg.Content = abs("content")
	cfg.DataDir = filepath.Join(tmp, "data")
	cfg.Archive = filepath.Join(tmp, "archive")
	if real, err := filepath.Abs(filepath.Join("data", "textbook")); err == nil {
		if st, e := os.Stat(real); e == nil && st.IsDir() {
			os.Setenv("STUDYBUDDY_TEXTBOOK_ASSETS", real)
		}
	}
	g, err := db.OpenGlobal(cfg.GlobalDBPath())
	if err != nil {
		panic(err)
	}
	defer g.Close()
	tree, err := textbook.Scan(cfg.Content)
	if err != nil {
		panic(err)
	}
	app, err := web.New(cfg, g, tree)
	if err != nil {
		panic(err)
	}
	r := app.Routes()

	do := func(method, path string, form url.Values, cookie string) (*httptest.ResponseRecorder, string) {
		var body io.Reader
		if form != nil {
			body = strings.NewReader(form.Encode())
		}
		req := httptest.NewRequest(method, path, body)
		if form != nil {
			req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
		}
		if cookie != "" {
			req.Header.Set("Cookie", cookie)
		}
		w := httptest.NewRecorder()
		r.ServeHTTP(w, req)
		return w, w.Body.String()
	}

	w, _ := do("POST", "/register", url.Values{
		"name": {"临时"}, "stage": {"primary"}, "grade": {"4"}, "class_no": {"1"},
		"username": {"dumpjs"}, "password": {"test123456"}, "volume": {"1"}, "gender": {"male"},
	}, "")
	cookie := w.Header().Get("Set-Cookie")
	ck := ""
	if i := strings.Index(cookie, "sb_session="); i >= 0 {
		rest := cookie[i+len("sb_session="):]
		if j := strings.IndexAny(rest, ";"); j >= 0 {
			ck = "sb_session=" + rest[:j]
		} else {
			ck = "sb_session=" + rest
		}
	}

	keys := make([]string, 0, len(tree.Lessons))
	for k := range tree.Lessons {
		keys = append(keys, k)
	}
	lessonKey := keys[0]

	outDir := ".tmp_js"
	_ = os.RemoveAll(outDir)
	_ = os.MkdirAll(outDir, 0o755)

	pages := []struct{ name, path string }{
		{"study", "/study"},
		{"textbook", "/textbook?key=primary-chinese-g1-v1"},
		{"quiz", "/quiz?key=" + url.QueryEscape(lessonKey)},
		{"favorites", "/favorites"},
		{"games", "/games?grade=1&volume=1"},
	}
	n := 0
	for _, p := range pages {
		_, body := do("GET", p.path, nil, ck)
		_ = os.WriteFile(filepath.Join(outDir, p.name+".html"), []byte(body), 0o644)
		for _, m := range reScript.FindAllStringSubmatch(body, -1) {
			code := m[1]
			if strings.TrimSpace(code) == "" {
				continue
			}
			n++
			fn := filepath.Join(outDir, fmt.Sprintf("%s_%02d.js", p.name, n))
			_ = os.WriteFile(fn, []byte(code), 0o644)
		}
		fmt.Println("dumped", p.name)
	}
	fmt.Println("total inline scripts:", n, "-> ", outDir)
	_ = http.StatusOK
}
