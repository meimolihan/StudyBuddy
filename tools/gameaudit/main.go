// Command gameaudit 互动游戏页全量审计：逐页核对「是不是一个合格的互动游戏题」。
//
// 为什么不用 Python 正则去数 `t:` / `o:` / `a:`：那是**重新实现**解析器。
// 实测教训 —— 正则版探针对 216 页全报「题干为空」「t: 44 条但 o: 40 条」，
// 而这些页面在浏览器里跑得好好的：
//   - `t:` 还会命中 JS 里非题库的用法（模板串、变量名）→ 数量虚高
//   - 中文数字「二年级」被按「2年级」找 → 误报「title 缺 2年级」
//
// 本工具直接调 textbook.ParseBank，与线上刷题、与 TestGameBankMatchesParseBank
// 走的是同一套代码，结论不会有偏差。
//
// 七道独立闸门（一个页面可以过便宜的那几道、同时在贵的那道上坏掉）：
//
//	G1 结构   <title> + 增强层哨兵 CSS/JS 都在；标签配对；无嵌套包装；哨兵各一次
//	G2 题库   ParseBank 解析出 >=1 题
//	G3 题量   每题选项数与题型匹配（判断 2 / 选择 4）；答案非空、不越界；缺解析
//	G4 引擎   grade / pickRound / resetAll / toggleTheme / #submit 都在
//	G5 增强层 .sbk2-bg / .sbk2-dock / 44px 热区 / AudioContext；暗色选择器必须复合式
//	G6 身份   页面自述的年级/册别/学科/题型/单元与路径逐项一致（防张冠李戴）
//	G7 配对   同一课的「选择」与「判断」两个目录必须成对存在
//
// 用法:
//
//	go run ./tools/gameaudit                                  # 审计全部 game/
//	go run ./tools/gameaudit -root content/primary/pep/game/grade2 -grade 2
//	go run ./tools/gameaudit -root <path> -json
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"

	"studybuddy/internal/textbook"
)

var (
	rootFlag  = flag.String("root", "content/primary/pep/game", "要审计的游戏目录根")
	gradeFlag = flag.Int("grade", 0, "期望的年级（0 = 不校验年级）")
	jsonFlag  = flag.Bool("json", false, "以 JSON 输出")
	// 只审课文级产物：单元目录名以（选择）/（判断）结尾。
	//
	// 为什么要这个开关：`game/` 下**并存两种结构**的页面 ——
	//   ① 课文级自测卷：<NN-单元>（选择）/NN-课.html，用 sbk2 增强层
	//   ② 单元级综合游戏：<NN-单元>/<NN-单元>.html，早期手工产物，用旧 sbk 增强层
	// ② 没有 grade/pickRound/#submit 也没有 sbk2 哨兵，G4/G5 必然全报 —— 那是
	// **预期内**的差异，不是缺陷。不加这个开关，全库审计会被 31 页旧页淹没，
	// 真正的新问题反而看不见。
	// → 审计产物时务必带 -products-only（默认 true）。
	productsOnly = flag.Bool("products-only", true, "只审课文级产物（单元目录带题型后缀）")
	allPages     = flag.Bool("all", false, "审计全部页面，含旧式单元综合游戏（预期会报 G4/G5）")
)

var (
	reTitle       = regexp.MustCompile(`(?is)<title[^>]*>(.*?)</title>`)
	reNested      = regexp.MustCompile(`(?is)<style[^>]*id="__SBK2_CSS__"[^>]*>\s*<style`)
	reDescendant  = regexp.MustCompile(`html\[data-theme="dark"\]\s+\.sbk2`)
	reStyleOpen   = regexp.MustCompile(`(?i)<style\b`)
	reStyleClose  = regexp.MustCompile(`(?i)</style>`)
	reScriptOpen  = regexp.MustCompile(`(?i)<script\b`)
	reScriptClose = regexp.MustCompile(`(?i)</script>`)
	reKindSuffix  = regexp.MustCompile(`（(选择|判断)）$`)
	reLeadingNum  = regexp.MustCompile(`^(\d+)-`)
)

// page 单页审计结论。
type page struct {
	Rel    string   `json:"rel"`
	File   string   `json:"file"`
	Title  string   `json:"title"`
	Kind   string   `json:"kind"`
	Qs     int      `json:"qs"`
	Issues []string `json:"issues,omitempty"`
}

var (
	volCN  = map[int]string{1: "上册", 2: "下册"}
	subjCN = map[string]string{"chinese": "语文", "math": "数学", "english": "英语"}
	// 中文数字年级：title 里写的是「二年级」而不是「2年级」
	gradeCN = map[int]string{1: "一", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六",
		7: "七", 8: "八", 9: "九"}
)

func main() {
	flag.Parse()
	if *allPages {
		*productsOnly = false
	}
	if _, err := os.Stat(*rootFlag); err != nil {
		fmt.Fprintf(os.Stderr, "目录不存在：%s\n", *rootFlag)
		os.Exit(2)
	}
	files, err := collect(*rootFlag)
	if err != nil {
		fmt.Fprintln(os.Stderr, "扫描失败：", err)
		os.Exit(2)
	}
	sort.Strings(files)

	// 只保留课文级产物：路径里必须有一段以（选择）/（判断）结尾。
	// 这是注入器的**产物特征**，也是区分同目录下两种页面结构的唯一依据
	// —— 见 productsOnly 的注释。
	all := len(files)
	if *productsOnly {
		var kept []string
		for _, f := range files {
			rel, _ := filepath.Rel(*rootFlag, f)
			if isProduct(rel) {
				kept = append(kept, f)
			}
		}
		files = kept
		skipped := all - len(files)
		if !*jsonFlag {
			fmt.Printf("（跳过 %d 页旧式单元综合游戏；要看它们请加 -all）\n\n", skipped)
		}
	}

	pages := make([]*page, 0, len(files))
	totalQs, badFiles := 0, 0
	for _, f := range files {
		p := audit(f, *rootFlag, *gradeFlag)
		totalQs += p.Qs
		if len(p.Issues) > 0 {
			badFiles++
		}
		pages = append(pages, p)
	}

	// G7 配对：同一课的「选择」/「判断」必须成对存在。
	// 同样从末尾倒推取 unit，且**必须用紧邻父目录**（isProduct 的教训）。
	pair := map[string]map[string]bool{}
	for _, p := range pages {
		if !isProduct(p.Rel) {
			continue
		}
		segs := strings.Split(p.Rel, "/")
		if len(segs) < 3 {
			continue
		}
		unit := reKindSuffix.ReplaceAllString(segs[len(segs)-2], "")
		key := unit + "/" + segs[len(segs)-1]
		if pair[key] == nil {
			pair[key] = map[string]bool{}
		}
		pair[key][p.Kind] = true
	}
	keys := make([]string, 0, len(pair))
	for k := range pair {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	var unpaired []string
	for _, k := range keys {
		v := pair[k]
		if v["选择"] && v["判断"] {
			continue
		}
		missing := "判断"
		if v["判断"] {
			missing = "选择"
		}
		unpaired = append(unpaired, k+"  缺 "+missing)
	}

	if *jsonFlag {
		enc := json.NewEncoder(os.Stdout)
		enc.SetIndent("", "  ")
		_ = enc.Encode(map[string]any{
			"root": *rootFlag, "files": len(files), "totalQs": totalQs,
			"badFiles": badFiles, "unpaired": unpaired, "detail": pages,
		})
		if badFiles > 0 || len(unpaired) > 0 {
			os.Exit(1)
		}
		return
	}

	fmt.Printf("审计 %s 下 %d 个 html\n\n", *rootFlag, len(files))
	fmt.Printf("题库总题量：%d 题\n", totalQs)
	fmt.Printf("配对键：%d 个，未配对：%d 个\n", len(keys), len(unpaired))
	for _, u := range unpaired {
		fmt.Printf("  [G7 未配对] %s\n", u)
	}
	fmt.Printf("\n=== 逐页审计 ===\n有问题文件：%d / %d\n", badFiles, len(files))
	n := 0
	for _, p := range pages {
		for _, s := range p.Issues {
			n++
			if n <= 60 {
				fmt.Printf("  [%s] %s\n", filepath.Base(p.Rel), s)
			}
		}
	}
	if n > 60 {
		fmt.Printf("  ...（另 %d 条）\n", n-60)
	}
	fmt.Println()
	ok := badFiles == 0 && len(unpaired) == 0
	if ok {
		fmt.Println("RESULT: PASS")
		return
	}
	fmt.Println("RESULT: FAIL")
	os.Exit(1)
}

func collect(root string) ([]string, error) {
	var out []string
	err := filepath.Walk(root, func(p string, info os.FileInfo, err error) error {
		if err != nil || info == nil || info.IsDir() {
			return nil
		}
		if strings.EqualFold(filepath.Ext(p), ".html") {
			out = append(out, p)
		}
		return nil
	})
	return out, err
}

// isProduct 判断这个页面是不是课文级产物：**紧邻文件的上一级目录名**以（选择）/（判断）结尾。
//
// ⚠️⚠️ 这里必须看「紧邻的上一级」而不是「路径里任意一段」。实测踩过：
// `game/grade1/volume1/chinese/01-识字（一）（选择）/01-天地人.html`（课文级，选择题）
// 与
// `game/grade1/volume1/chinese/01-识字（一）/01-天地人.html`（旧式单元综合游戏）
// **文件名完全相同**，且旧页所在目录 `01-识字（一）` 的**前缀**恰好是带后缀目录
// `01-识字（一）（选择）` 的前缀 —— 于是任何「路径中 contains（选择）」的判据都会
// 把旧页误判成产物，审计里表现为「选择目录但 title 含判断题」「选项 2 个（选择题应 4）」
// 这种自相矛盾的报错，还一次冒出近万条。
//
// → 判据必须是 segments[len-2]（紧邻父目录）精确匹配后缀。
func isProduct(rel string) bool {
	segs := strings.Split(filepath.ToSlash(rel), "/")
	if len(segs) < 2 {
		return false
	}
	parent := segs[len(segs)-2]
	return strings.HasSuffix(parent, "（选择）") || strings.HasSuffix(parent, "（判断）")
}

func audit(path, root string, wantGrade int) *page {
	rel, _ := filepath.Rel(root, path)
	p := &page{Rel: filepath.ToSlash(rel), Kind: "选择"}
	parts := strings.Split(p.Rel, "/")

	b, err := os.ReadFile(path)
	if err != nil {
		p.Issues = append(p.Issues, "读取失败："+err.Error())
		return p
	}
	raw := string(b)

	// ---------- G1 结构 ----------
	for _, need := range []string{"<title>", `id="__SBK2_CSS__"`, `id="__SBK2_JS__"`} {
		if !strings.Contains(raw, need) {
			p.Issues = append(p.Issues, "G1 缺 "+need)
		}
	}
	if o, c := len(reStyleOpen.FindAllString(raw, -1)), len(reStyleClose.FindAllString(raw, -1)); o != c {
		p.Issues = append(p.Issues, fmt.Sprintf("G1 <style> 标签不配对 %d/%d", o, c))
	}
	if o, c := len(reScriptOpen.FindAllString(raw, -1)), len(reScriptClose.FindAllString(raw, -1)); o != c {
		p.Issues = append(p.Issues, fmt.Sprintf("G1 <script> 标签不配对 %d/%d", o, c))
	}
	if reNested.MatchString(raw) {
		p.Issues = append(p.Issues, "G1 增强层标签嵌套（二次包装）")
	}
	for _, s := range []string{"__SBK2_CSS__", "__SBK2_JS__"} {
		if n := strings.Count(raw, s); n != 1 {
			p.Issues = append(p.Issues, fmt.Sprintf("G1 哨兵 %s 出现 %d 次（应 1 次）", s, n))
		}
	}

	// ---------- G6 身份 ----------
	title := ""
	if m := reTitle.FindStringSubmatch(raw); m == nil {
		p.Issues = append(p.Issues, "G6 无 <title>")
	} else {
		title = strings.TrimSpace(m[1])
		p.Title = title
	}
	// 从路径**末尾倒推**定位字段，不依赖 root 层级。
	// ⚠️ 不能写 parts[0]=vol / parts[1]=subj / parts[2]=unit：`-root` 可能是
	// `game/`（相对路径多一层学段/出版社），也可能是 `game/grade2/`，固定下标
	// 在其中一种下会整体错位 —— 实测报出「title 缺单元名chinese」这种
	// 明显荒谬的结果（chinese 是学科，却被当成单元名）。
	// 约定结构（从文件往上）：文件 / <NN-单元>（题型） / <学科> / volume<N> / …
	if len(parts) >= 4 {
		file := parts[len(parts)-1]
		unit := parts[len(parts)-2]
		subj := parts[len(parts)-3]
		vol := parts[len(parts)-4]
		p.File = file
		if strings.HasSuffix(unit, "（判断）") {
			p.Kind = "判断"
		}
		if wantGrade > 0 {
			if cn := gradeCN[wantGrade]; cn != "" && !strings.Contains(title, cn+"年级") {
				p.Issues = append(p.Issues, fmt.Sprintf("G6 title 缺 %s年级：%q", cn, trunc(title, 46)))
			}
		}
		if n, err := strconv.Atoi(strings.TrimPrefix(vol, "volume")); err == nil && volCN[n] != "" {
			if !strings.Contains(title, volCN[n]) {
				p.Issues = append(p.Issues, fmt.Sprintf("G6 title 缺%s：%q", volCN[n], trunc(title, 46)))
			}
		}
		if s := subjCN[subj]; s != "" && !strings.Contains(title, s) {
			p.Issues = append(p.Issues, fmt.Sprintf("G6 title 缺学科%s：%q", s, trunc(title, 46)))
		}
		if p.Kind == "判断" && !strings.Contains(title, "判断") {
			p.Issues = append(p.Issues, fmt.Sprintf("G6 判断目录但 title 无「判断」：%q", trunc(title, 46)))
		}
		if p.Kind == "选择" && strings.Contains(title, "判断题") {
			p.Issues = append(p.Issues, fmt.Sprintf("G6 选择目录但 title 含「判断题」：%q", trunc(title, 46)))
		}
		// 单元名（去题型后缀、去课序前缀）应出现在 title 里
		clean := reKindSuffix.ReplaceAllString(unit, "")
		if m := reLeadingNum.FindStringSubmatch(clean); m != nil {
			clean = clean[len(m[0]):]
		}
		if clean != "" && !strings.Contains(title, clean) {
			p.Issues = append(p.Issues, fmt.Sprintf("G6 title 缺单元名%s：%q", clean, trunc(title, 46)))
		}
		// 课名（去课序前缀）应出现在 title 里 —— 防「标题与文件名张冠李戴」
		if m := reLeadingNum.FindStringSubmatch(file); m != nil {
			cn := file[len(m[0]):]
			cn = strings.TrimSuffix(cn, ".html")
			if cn != "" && !strings.Contains(title, cn) {
				p.Issues = append(p.Issues, fmt.Sprintf("G6 title 缺课名%s：%q", cn, trunc(title, 46)))
			}
		}
	}

	// ---------- G2/G3 题库（权威口径：系统自己的解析器） ----------
	qs := textbook.ParseBank(raw)
	p.Qs = len(qs)
	if len(qs) == 0 {
		p.Issues = append(p.Issues, "G2 ParseBank 解析出 0 题")
		return p
	}
	wantOpts := 4
	if p.Kind == "判断" {
		wantOpts = 2
	}
	for i, q := range qs {
		stem := strings.TrimSpace(q.Stem)
		if stem == "" {
			p.Issues = append(p.Issues, fmt.Sprintf("G3 第%d题题干为空", i+1))
		}
		if len(q.Options) != wantOpts {
			p.Issues = append(p.Issues, fmt.Sprintf("G3 第%d题「%s」选项 %d 个（%s题应 %d）",
				i+1, trunc(stem, 22), len(q.Options), p.Kind, wantOpts))
		}
		if len(q.Answers) == 0 {
			p.Issues = append(p.Issues, fmt.Sprintf("G3 第%d题「%s」答案为空", i+1, trunc(stem, 22)))
			continue
		}
		if p.Kind == "判断" && len(q.Answers) != 1 {
			p.Issues = append(p.Issues, fmt.Sprintf("G3 第%d题「%s」判断题答案 %d 个（应 1）",
				i+1, trunc(stem, 22), len(q.Answers)))
		}
		for _, idx := range q.AnswerIdx() {
			if idx < 0 || idx >= len(q.Options) {
				p.Issues = append(p.Issues, fmt.Sprintf("G3 第%d题「%s」答案下标 %d 越界（选项 %d 个）",
					i+1, trunc(stem, 22), idx, len(q.Options)))
			}
		}
		if strings.TrimSpace(q.Explain) == "" {
			p.Issues = append(p.Issues, fmt.Sprintf("G3 第%d题「%s」缺解析", i+1, trunc(stem, 22)))
		}
	}

	// ---------- G4 引擎 ----------
	for _, fn := range []string{"function grade", "pickRound", "resetAll", "toggleTheme", `id="submit"`} {
		if !strings.Contains(raw, fn) {
			p.Issues = append(p.Issues, "G4 缺引擎符号 "+fn)
		}
	}

	// ---------- G5 增强层 ----------
	for _, k := range []string{"sbk2-bg", "sbk2-dock", "sbk2-in", "min-width:44px", "AudioContext"} {
		if !strings.Contains(raw, k) {
			p.Issues = append(p.Issues, "G5 缺增强层特征 "+k)
		}
	}
	if !strings.Contains(raw, `html.sbk2[data-theme="dark"]`) {
		p.Issues = append(p.Issues, `G5 缺复合式暗色选择器 html.sbk2[data-theme="dark"]`)
	}
	if reDescendant.MatchString(raw) {
		p.Issues = append(p.Issues, "G5 出现后代式暗色选择器（永不命中）")
	}
	return p
}

func trunc(s string, n int) string {
	r := []rune(s)
	if len(r) <= n {
		return s
	}
	return string(r[:n]) + "…"
}
