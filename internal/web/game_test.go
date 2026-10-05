package web

import (
	"html/template"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"studybuddy/internal/textbook"
)

// ---------------------------------------------------------------------------
// 路径解析
// ---------------------------------------------------------------------------

// TestParseGamePath 钉住游戏目录的解析口径。
//
// 逐条列出会被误判的输入比只测 happy path 重要 —— 解析器一旦放宽，
// 就会把 choose/judge 的课程文件也当成游戏收进索引。
func TestParseGamePath(t *testing.T) {
	ok := []struct {
		rel    string
		grade  int
		vol    int
		subj   string
		unit   string
		unitNo int
		title  string
	}{
		{"primary/pep/game/grade1/volume1/chinese/01-识字（一）/01-天地人.html", 1, 1, "chinese", "识字（一）", 1, "天地人"},
		{"primary/pep/game/grade1/volume2/math/05-20以内的进位加法/凑十法师.html", 1, 2, "math", "20以内的进位加法", 5, "凑十法师"},
		{"middle/pep/game/grade7/volume1/english/01-Unit1/01-Hello.html", 7, 1, "english", "Unit1", 1, "Hello"},
		// 没有 NN- 前缀的单元目录：序号为 0，名称取整段，仍应被接受
		{"primary/pep/game/grade1/volume1/math/复习/闯关.html", 1, 1, "math", "复习", 0, "闯关"},
		// 文件名里的下划线转成空格，便于写英文游戏名
		{"primary/pep/game/grade1/volume1/english/01-U1/01-Hello_World.html", 1, 1, "english", "U1", 1, "Hello World"},
		// junior 是初中新命名，必须被接受
		{"junior/pep/game/grade7/volume1/chinese/01-识字（一）/01-天地人.html", 7, 1, "chinese", "识字（一）", 1, "天地人"},
		// 游戏名里带短横不能被误切：「数一数-比多少」剥掉的是 01- 课序，不是 - 比多少
		{"primary/pep/game/grade1/volume1/math/01-数一数/01-数一数-比多少.html", 1, 1, "math", "数一数", 1, "数一数-比多少"},
	}
	for _, c := range ok {
		g := parseGamePath(c.rel)
		if g == nil {
			t.Errorf("应解析成功却返回 nil：%s", c.rel)
			continue
		}
		if g.Grade != c.grade || g.Volume != c.vol || g.Subject != c.subj ||
			g.Unit != c.unit || g.UnitNo != c.unitNo || g.Title != c.title {
			t.Errorf("%s\n  得到 grade=%d vol=%d subj=%s unit=%q unitNo=%d title=%q\n  期望 grade=%d vol=%d subj=%s unit=%q unitNo=%d title=%q",
				c.rel, g.Grade, g.Volume, g.Subject, g.Unit, g.UnitNo, g.Title,
				c.grade, c.vol, c.subj, c.unit, c.unitNo, c.title)
		}
	}

	bad := []struct {
		rel string
		why string
	}{
		{"primary/pep/choose/grade1/volume1/chinese/01-识字（一）/01-天地人.html", "题型层是 choose，不该被当成游戏"},
		{"primary/pep/judge/grade1/volume1/chinese/01-识字（一）/01-天地人.html", "题型层是 judge，不该被当成游戏"},
		{"primary/pep/game/grade1/volume1/chinese/01-天地人.html", "少一层（没有单元目录）"},
		{"primary/pep/game/grade1/volume1/chinese/01-识字（一）/01-天地人.html/extra.html", "多一层"},
		{"primary/pep/game/gradeX/volume1/chinese/01-识字（一）/01-天地人.html", "年级段不是 gradeN"},
		{"primary/pep/game/grade0/volume1/chinese/01-识字（一）/01-天地人.html", "年级为 0"},
		{"primary/pep/game/grade1/volumeX/chinese/01-识字（一）/01-天地人.html", "册别段不是 volumeN"},
		{"primary/pep/game/grade1/volume1/xyz/01-识字（一）/01-天地人.html", "学科键不存在"},
		{"weird/pep/game/grade7/volume1/chinese/01-识字（一）/01-天地人.html", "学段不识别"},
		{"primary/pep/game/grade4x/volume1/chinese/01-识字（一）/01-天地人.html", "strconv 宽松解析会放过 grade4x，必须拒绝"},
		{"primary/pep/game/grade1/volume1/chinese/01-识字（一）/.html", "文件名为空"},
	}
	for _, c := range bad {
		if g := parseGamePath(c.rel); g != nil {
			t.Errorf("应拒绝却解析成功（%s）：%s", c.why, c.rel)
		}
	}
}

// TestGameScansRealContent 用真实 content 目录跑一遍扫描器，
// 确认一年级 31 个单元游戏全部进得来，且刷题题库没被误收。
func TestGameScansRealContent(t *testing.T) {
	root := realContentRoot(t)
	// 逐个真实文件走一遍解析器，确认一年级 31 个单元游戏全部进得来。
	// 不构造 GameStore：它带 sync.Once，测试里不好复用，而这里要验的
	// 本来就是 parseGamePath 这一个环节。
	n := 0
	err := filepath.Walk(filepath.Join(root, "primary", "pep", "game", "grade1"),
		func(p string, info os.FileInfo, err error) error {
			if err != nil || info == nil || info.IsDir() || !strings.HasSuffix(p, ".html") {
				return nil
			}
			rel, _ := filepath.Rel(root, p)
			if g := parseGamePath(filepath.ToSlash(rel)); g == nil {
				t.Errorf("真实游戏文件未被解析：%s", rel)
			} else {
				n++
			}
			return nil
		})
	if err != nil {
		t.Fatal(err)
	}
	if n < 31 {
		t.Errorf("一年级游戏只解析出 %d 个，预期至少 31 个", n)
	}
	t.Logf("一年级真实游戏文件解析成功 %d 个", n)
}

// TestGameStoreIgnoresBankFiles 确认游戏索引不会把刷题课程收进来。
// 这是「不改动原有业务逻辑」的关键保证：game 扫描是独立的一遍 Walk，
// 同一批文件不会因此在 Tree 里多出条目。
func TestGameStoreIgnoresBankFiles(t *testing.T) {
	root := realContentRoot(t)
	// choose 下随便挑一个真实课程文件，它必须被 parseGamePath 拒绝
	var sample string
	_ = filepath.Walk(filepath.Join(root, "primary", "pep", "choose", "grade1"),
		func(p string, info os.FileInfo, err error) error {
			if sample == "" && err == nil && info != nil && !info.IsDir() && strings.HasSuffix(p, ".html") {
				sample = p
			}
			return nil
		})
	if sample == "" {
		t.Skip("没找到 choose 课程样本，跳过")
	}
	rel, _ := filepath.Rel(root, sample)
	if g := parseGamePath(filepath.ToSlash(rel)); g != nil {
		t.Errorf("choose 课程被误收为游戏：%s", rel)
	}
}

// TestGameBankMatchesParseBank 是「游戏题库与现有题库格式一致」这条要求的机器验证。
//
// 这条要求曾经真实踩过三次坑，且症状都很隐蔽 —— 游戏**能正常玩**，
// 只是 ParseBank 读不出题，所以纯看页面发现不了：
//  1. 写成 `var ALL =` 而不是 `const ALL =`  → marker 匹配不上；
//  2. 注释里写了 marker 那个字面量          → strings.Index 命中注释；
//  3. 答案写成数字下标 a:[1] 而不是字母 a:["B"] → readArray 只收字符串，返回空数组。
//
// 三者都表现为「ParseBank 返回 0 题」，因此必须用真正的 ParseBank 来判定，
// 自己再实现一遍校验逻辑是重复劳动且容易漏（上面第 3 点就先漏过一次）。
func TestGameBankMatchesParseBank(t *testing.T) {
	root := realContentRoot(t)
	gameRootDir := filepath.Join(root, "primary", "pep", "game")

	// 早先手工做的两个独立游戏自带完整交互、没有题库块，不参与本用例。
	legacy := map[string]bool{"01-天地人.html": true, "01-数学游戏（数一数、比多少）.html": true}

	// ⚠️ 断言必须**按题型分支**，不能一刀切「4 选项 + 1 答案」。
	// 这条用例写于 game/ 下只有 33 页单元综合游戏（全是四选一单选）的年代；
	// 后来补进 208+216 页课文级自测卷后，判断题（2 选项）和多选题（多答案）
	// 都是**正常形态**，一刀切断言会把它们全报成错 —— 那是断言过期，不是内容坏。
	// 判据：
	//   判断题  → 2 选项（对 / 错）、恰好 1 个答案
	//   选择题  → 4 选项、答案 >=1（多选题是「（　）」型，允许多个）
	//   单元综合游戏（无题型后缀目录）→ 沿用 4 选项单选
	kindOf := func(rel string) string {
		for _, seg := range strings.Split(filepath.ToSlash(rel), "/") {
			switch {
			case strings.HasSuffix(seg, "（判断）"):
				return "judge"
			case strings.HasSuffix(seg, "（选择）"):
				return "choose"
			}
		}
		return "unit" // 旧式单元综合游戏
	}

	total, files := 0, 0
	byKind := map[string]int{}
	err := filepath.Walk(gameRootDir, func(p string, info os.FileInfo, err error) error {
		if err != nil || info == nil || info.IsDir() || !strings.HasSuffix(p, ".html") {
			return nil
		}
		rel, _ := filepath.Rel(gameRootDir, p)
		if legacy[info.Name()] {
			return nil
		}
		kind := kindOf(rel)
		files++
		byKind[kind]++
		b, rerr := os.ReadFile(p)
		if rerr != nil {
			t.Errorf("%s 读取失败：%v", rel, rerr)
			return nil
		}
		qs := textbook.ParseBank(string(b))
		if len(qs) == 0 {
			t.Errorf("%s：ParseBank 解析出 0 题（检查 const 声明、注释里是否混入 marker、答案是否为字母）", rel)
			return nil
		}
		wantOpts, wantAnsMin, wantAnsMax := 4, 1, 1
		if kind == "judge" {
			wantOpts, wantAnsMin, wantAnsMax = 2, 1, 1
		} else if kind == "choose" {
			wantAnsMax = len(qs[0].Options) // 多选题答案数不设上限
		}
		for _, q := range qs {
			total++
			if len(q.Options) != wantOpts {
				t.Errorf("%s：题干「%s」选项 %d 个（%s 题预期 %d）",
					rel, q.Stem, len(q.Options), kind, wantOpts)
			}
			if len(q.Answers) < wantAnsMin || len(q.Answers) > wantAnsMax {
				t.Errorf("%s：题干「%s」答案 %d 个（%s 题预期 %d~%d）",
					rel, q.Stem, len(q.Answers), kind, wantAnsMin, wantAnsMax)
				continue
			}
			if len(q.Answers) == 0 {
				continue
			}
			// 答案必须落在选项范围内，否则判分永远错
			for _, idx := range q.AnswerIdx() {
				if idx >= len(q.Options) {
					t.Errorf("%s：题干「%s」答案下标 %d 越界（选项 %d 个）", rel, q.Stem, idx, len(q.Options))
				}
			}
			if strings.TrimSpace(q.Explain) == "" {
				t.Errorf("%s：题干「%s」缺解析（家长靠它陪孩子复习）", rel, q.Stem)
			}
		}
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
	// 下限按现状取：grade1 既有 33 页单元综合游戏，也补了 208 页课文级自测卷。
	// 门槛只防「扫描器整体失灵」这一类回归，不卡具体页数。
	if files < 240 {
		t.Errorf("新引擎游戏只有 %d 个，预期至少 240 个（33 页单元综合 + 208 页课文级）", files)
	}
	// 题型目录都要真的被扫到，否则「按题型分支」这段等于没被测到
	for _, k := range []string{"unit", "choose", "judge"} {
		if byKind[k] == 0 {
			t.Errorf("按题型分支的断言没覆盖到 %s 类文件（分布：%v）", k, byKind)
		}
	}
	t.Logf("校验 %d 个游戏文件、%d 道题（分布 %v），题库格式与刷题题库一致", files, total, byKind)
}

// TestGameDisplayTitleFromHTMLTag 展示名必须取自 HTML 的 <title>，不是文件名。
//
// 这条约定是被真实问题逼出来的：任务要求「每个单元创建同名游戏 html」，
// 于是文件名 = 单元名，剥掉课序前缀后仍是「识字（一）」——列表页已经按单元
// 分组显示了这个名字，卡片再写一遍就是同一个名字出现两遍，而且一个单元下
// 清一色都叫「识字（一）」，完全看不出区别。
func TestGameDisplayTitleFromHTMLTag(t *testing.T) {
	root := realContentRoot(t)
	idx := gamesFor("primary", 1, 1, root)
	if idx == nil || !idx.HasAny {
		t.Fatal("一年级上册没有索引到游戏")
	}
	sameAsUnit := 0
	total := 0
	for _, s := range idx.Subject {
		for _, u := range s.Units {
			for _, g := range u.Games {
				total++
				if g.Show == "" {
					t.Errorf("%s：展示名为空", g.Key)
				}
				if g.Show == g.Unit {
					sameAsUnit++
					t.Logf("提示：%s 的展示名与单元名相同（%q）", g.Key, g.Show)
				}
			}
		}
	}
	if total == 0 {
		t.Fatal("一年级上册没有游戏")
	}
	t.Logf("共 %d 个游戏，其中 %d 个展示名与单元名相同", total, sameAsUnit)
	if sameAsUnit == total {
		t.Errorf("全部 %d 个游戏的展示名都等于单元名 —— <title> 没被用上", total)
	}
}

func realContentRoot(t *testing.T) string {
	t.Helper()
	// 仓库根的上一级是 content 的父目录；测试从 internal/web 运行，
	// 所以向上三层到仓库根。
	wd, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}
	root := filepath.Join(wd, "..", "..", "content")
	if _, err := os.Stat(root); err != nil {
		t.Skipf("找不到 content 目录（%s），跳过：%v", root, err)
	}
	abs, _ := filepath.Abs(root)
	return abs
}

// ---------------------------------------------------------------------------
// 主题注入
// ---------------------------------------------------------------------------

// TestInjectBeforeHead 桥接样式必须落在 </head> 之前，
// 否则游戏自己的 <style> 会覆盖掉变量声明。
func TestInjectBeforeHead(t *testing.T) {
	in := "<html><head><title>x</title></head><body>hi</body></html>"
	got := injectBeforeHead(in, "<style id=\"bridge\"></style>")
	i := strings.Index(got, "bridge")
	j := strings.Index(got, "</head>")
	if i < 0 || j < 0 || i > j {
		t.Errorf("桥接样式没落在 </head> 之前：\n%s", got)
	}
}

// TestInjectBeforeHeadMultipleHead 用最后一个 </head>：
// 复制的代码片段里可能有多个，替换第一个会把样式插到错误的文档结构里。
func TestInjectBeforeHeadMultipleHead(t *testing.T) {
	in := "<head></head><p>片段</p><head></head>"
	got := injectBeforeHead(in, "MARK")
	if strings.Count(got, "MARK") != 1 {
		t.Fatalf("应只注入一次：%s", got)
	}
	if strings.Index(got, "MARK") > strings.LastIndex(got, "</head>") {
		t.Errorf("应注入到最后一个 </head> 之前：%s", got)
	}
}

// TestInjectHTMLAttr data-theme 必须写到 <html> 上，
// 否则游戏里的 [data-theme="dark"] 规则永远匹配不上。
func TestInjectHTMLAttr(t *testing.T) {
	cases := []struct{ in, attr, val, want string }{
		{`<html lang="zh-CN">`, "data-theme", "dark", `<html lang="zh-CN" data-theme="dark">`},
		{`<HTML LANG="zh-CN">`, "data-theme", "dark", `data-theme="dark"`},
		{`<html>`, "data-theme", "light", `<html data-theme="light">`},
	}
	for _, c := range cases {
		got := injectHTMLAttr(c.in, c.attr, c.val)
		if !strings.Contains(got, c.val) {
			t.Errorf("未写入属性：%s → %s", c.in, got)
		}
		if c.want != "" && got != c.want && !strings.Contains(got, c.want) {
			t.Errorf("结果不符：%s → %s，期望含 %s", c.in, got, c.want)
		}
	}
	// 空值（跟随系统）不写属性，让游戏内的媒体查询自然接管
	if got := injectHTMLAttr(`<html lang="zh-CN">`, "data-theme", ""); strings.Contains(got, "data-theme") {
		t.Errorf("theme 为空时不该写属性：%s", got)
	}
	// 已有该属性时不覆盖（游戏自己写的值优先）
	in := `<html data-theme="light">`
	if got := injectHTMLAttr(in, "data-theme", "dark"); strings.Count(got, "data-theme") != 1 {
		t.Errorf("不该重复写入属性：%s", got)
	}
}

// TestGameThemeBridgeCSS 三种模式都要给出可用的变量声明。
func TestGameThemeBridgeCSS(t *testing.T) {
	for _, theme := range []string{"dark", "light", ""} {
		css := gameThemeBridgeCSS(theme)
		if css == "" {
			t.Fatalf("theme=%q 返回空 CSS", theme)
		}
		for _, v := range []string{"--g-bg", "--g-card", "--g-ink", "--g-muted", "--g-line"} {
			if !strings.Contains(css, v) {
				t.Errorf("theme=%q 缺变量 %s", theme, v)
			}
		}
	}
	// 跟随系统必须包在媒体查询里，否则会强加给浅色用户
	if css := gameThemeBridgeCSS(""); !strings.Contains(css, "prefers-color-scheme: dark") {
		t.Errorf("跟随系统时应包在媒体查询里，实际：%s", css)
	}
	// 显式深色不应再包媒体查询（用户已明确选择）
	if css := gameThemeBridgeCSS("dark"); strings.Contains(css, "prefers-color-scheme") {
		t.Errorf("显式深色不应依赖媒体查询：%s", css)
	}
}

// ---------------------------------------------------------------------------
// 模板与样式
// ---------------------------------------------------------------------------

// TestGameTemplatesParse 用与线上同一份 FuncMap 解析新模板，
// 缺函数或语法错会立刻暴露，不会假绿。
// TestSplitGameKind 钉住单元目录尾部题型后缀的剥离口径。
//
// 这个后缀是**存储层的去重手段**：choose 与 judge 两棵树的单元目录同名
// （都是 `01-识字（一）`），落盘必须靠 `01-识字（一）（选择）` 区分，
// 否则后写入的覆盖先写入的。但它是存储细节，不该出现在 UI 的单元名里。
func TestSplitGameKind(t *testing.T) {
	ok := []struct{ in, unit, kind string }{
		{"识字（一）（选择）", "识字（一）", "选择"},
		{"识字（一）（判断）", "识字（一）", "判断"},
		{"5以内数的认识和加减法（选择）", "5以内数的认识和加减法", "选择"},
		// 顺序不能反：判断不是选择的子串，HasSuffix 逐个试即可
		{"Unit1（判断）", "Unit1", "判断"},
		// 没有后缀的旧式单元综合游戏页：原样返回，题型为空
		{"识字（一）", "识字（一）", ""},
		{"20以内的进位加法", "20以内的进位加法", ""},
		// 只认尾部完整后缀：单元名里出现的括号不能被当后缀剥掉
		{"语文（精选）（选择）", "语文（精选）", "选择"},
		{"（选择）", "（选择）", ""}, // 剥完为空 -> 保留原样，交给 unit=="" 兜底
		{"", "", ""},
	}
	for _, c := range ok {
		unit, kind := splitGameKind(c.in)
		if unit != c.unit || kind != c.kind {
			t.Errorf("splitGameKind(%q) = (%q, %q)，期望 (%q, %q)",
				c.in, unit, kind, c.unit, c.kind)
		}
	}
}

// TestParseGamePathKind 题型后缀必须从 Unit 剥掉、落到 Kind 字段，
// 且不影响 UnitNo 与 Title 的解析。
func TestParseGamePathKind(t *testing.T) {
	g := parseGamePath("primary/pep/game/grade1/volume1/chinese/01-识字（一）（选择）/01-天地人.html")
	if g == nil {
		t.Fatal("带题型后缀的课文级游戏页应解析成功")
	}
	if g.Unit != "识字（一）" {
		t.Errorf("Unit 应为剥掉后缀的干净单元名，得到 %q", g.Unit)
	}
	if g.Kind != "选择" {
		t.Errorf("Kind 应为 %q，得到 %q", "选择", g.Kind)
	}
	if g.UnitNo != 1 || g.Title != "天地人" {
		t.Errorf("UnitNo/Title 受后缀影响：UnitNo=%d Title=%q", g.UnitNo, g.Title)
	}
	// 无后缀的旧式单元综合游戏页：Kind 必须为空，不能被塞进什么默认值
	g2 := parseGamePath("primary/pep/game/grade1/volume1/chinese/01-识字（一）/01-识字（一）.html")
	if g2 == nil {
		t.Fatal("无后缀的单元综合游戏页应解析成功")
	}
	if g2.Kind != "" {
		t.Errorf("无后缀时 Kind 应为空，得到 %q", g2.Kind)
	}
}

// TestGameUnitKindInGroupKey 同一个 (UnitNo, Unit) 下的选择与判断
// 必须是**两个**分组 —— 否则两类题会并进同一个卡片网格，
// 点进去分不清在做哪一类。
func TestGameUnitKindInGroupKey(t *testing.T) {
	root := t.TempDir()
	unit := "01-识字（一）"
	for _, kind := range []string{"（选择）", "（判断）"} {
		d := filepath.Join(root, "primary", "pep", "game", "grade1", "volume1",
			"chinese", unit+kind)
		if err := os.MkdirAll(d, 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(filepath.Join(d, "01-天地人.html"),
			[]byte("<title>天地人</title>"), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	s := &GameStore{root: root}
	idx := s.List("primary", 1, 1)
	if !idx.HasAny || len(idx.Subject) != 1 {
		t.Fatalf("应扫到 1 个学科，实际 %d（HasAny=%v）", len(idx.Subject), idx.HasAny)
	}
	units := idx.Subject[0].Units
	if len(units) != 2 {
		t.Fatalf("选择与判断应分成 2 个单元分组，实际 %d 个：%+v", len(units), units)
	}
	// 排序：无题型的排最前，然后选择、判断。这里两者都无「综合游戏」，
	// 所以顺序必须是 选择 → 判断。
	if units[0].Kind != "选择" || units[1].Kind != "判断" {
		t.Errorf("题型分组顺序应为 选择→判断，实际 %q→%q", units[0].Kind, units[1].Kind)
	}
	for _, u := range units {
		if u.Name != "识字（一）" {
			t.Errorf("单元名不应带题型后缀，得到 %q", u.Name)
		}
	}
}

func TestGameTemplatesParse(t *testing.T) {
	for _, name := range []string{"games.html", "game.html", "study.html"} {
		if _, err := template.New("").Funcs(newFuncMap()).ParseFS(assetsFS, "templates/"+name); err != nil {
			t.Errorf("%s 解析失败：%v", name, err)
		}
	}
}

// TestStudyHasQTypeEntry 学习主页必须有题型入口，且在官方教材模块之前。
func TestStudyHasQTypeEntry(t *testing.T) {
	s := tmplSourceForTest(t, "study.html")
	entry := strings.Index(s, "qtype-entry")
	cover := strings.Index(s, "tb-home")
	stat := strings.Index(s, "stat-grid")
	switch {
	case entry < 0:
		t.Fatal("study.html 缺少题型入口模块（qtype-entry）")
	case cover < 0:
		t.Fatal("study.html 缺少官方教材模块（tb-home）")
	case !(stat < entry && entry < cover):
		t.Errorf("题型入口位置不对：应在统计卡(%d)之后、官方教材(%d)之前，实际 %d", stat, cover, entry)
	}
	// 三个入口一个都不能少
	for _, need := range []string{"/study?qt=choose", "/study?qt=judge", "/games"} {
		if !strings.Contains(s, need) {
			t.Errorf("题型入口缺少链接 %s", need)
		}
	}
}

// TestGameCSSTokens 游戏样式只允许用变量取色，
// 硬编码色值会在深色模式下失效。
func TestGameCSSTokens(t *testing.T) {
	css := stripCSSComments(styleCSSForTest(t))
	i := strings.Index(css, "/* ---- 1) 学习主页：题型入口 ---- */")
	if i < 0 {
		// 注释已被剥掉，退而用最后一个锚点类名定位
		i = strings.Index(css, ".qtype-entry{")
	}
	if i < 0 {
		t.Fatal("style.css 里找不到游戏模块样式段")
	}
	blk := css[i:]
	// 只检查本模块自己写的三条颜色声明；沿用 --card/--brand 等令牌是允许的
	for _, bad := range []string{"#2f6fd0", "#ffffff", "#1f2937", "#e3e9f1"} {
		if strings.Contains(blk, bad) {
			t.Errorf("游戏样式里出现硬编码色值 %s，应改用 CSS 变量", bad)
		}
	}
	// 触屏热区下限
	if !strings.Contains(blk, "min-height:56px") {
		t.Error("入口卡片缺 min-height:56px 的触屏热区保障")
	}
	// 移动端降列
	if !strings.Contains(blk, "@media (max-width:900px)") || !strings.Contains(blk, "@media (max-width:560px)") {
		t.Error("入口卡片缺移动端降列断点")
	}
}
