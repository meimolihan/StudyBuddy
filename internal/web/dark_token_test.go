package web

import (
	"math"
	"regexp"
	"strconv"
	"strings"
	"testing"
)

// 方案 B-2：暗色令牌定版的守卫测试。
//
// 这批测试守的是两件容易复发的事：
//  1. 两代暗色令牌并存 —— 有人再加第三套 :root 暗色值就乱了
//  2. html:not([data-theme="light"]) 逃出 media query —— 会把暗色强加给浅色用户

// lum 计算 WCAG 相对亮度。
func lum(hex string) float64 {
	h := strings.TrimPrefix(strings.TrimSpace(hex), "#")
	if len(h) == 3 {
		h = string([]byte{h[0], h[0], h[1], h[1], h[2], h[2]})
	}
	if len(h) < 6 {
		return -1
	}
	var v [3]float64
	for i := 0; i < 3; i++ {
		n, err := strconv.ParseInt(h[i*2:i*2+2], 16, 64)
		if err != nil {
			return -1
		}
		c := float64(n) / 255
		if c <= 0.03928 {
			c = c / 12.92
		} else {
			// WCAG 定义的是 2.4 **次方**，不是乘 2.4。
			// 写成 *2.4 会把颜色整体提亮，对比度算出来偏低，
			// 表现为"明明达标却报不达标"——这个 bug 极难凭肉眼发现。
			c = math.Pow((c+0.055)/1.055, 2.4)
		}
		v[i] = c
	}
	return 0.2126*v[0] + 0.7152*v[1] + 0.0722*v[2]
}

// contrast 返回两色对比度。
func contrast(a, b string) float64 {
	la, lb := lum(a), lum(b)
	if la < 0 || lb < 0 {
		return -1
	}
	hi, lo := la, lb
	if hi < lo {
		hi, lo = lo, hi
	}
	return (hi + 0.05) / (lo + 0.05)
}

// darkTokenVal 读定版暗色段里某个令牌的值。
func darkTokenVal(t *testing.T, name string) (string, bool) {
	t.Helper()
	css := stripCSSComments(styleCSSForTest(t))
	// 取最后一次出现的定义（定版段在文件末尾）
	re := regexp.MustCompile(regexp.QuoteMeta(name) + `\s*:\s*(#[0-9a-fA-F]{3,8})`)
	locs := re.FindAllStringSubmatchIndex(css, -1)
	if len(locs) == 0 {
		return "", false
	}
	last := locs[len(locs)-1]
	return css[last[2]:last[3]], true
}

// TestDarkTokenSingleGeneration 暗色中性色令牌只能有一套定版值。
//
// 修复前文件里有两代：#0e1621/#182231（第一代，位置靠前被覆盖）
// 与 #151a21/#1c222b（第二代，位置靠后胜出）。定版后末尾统一为第二代，
// 这里断言末尾的最终值就是定版值，防止有人再引入第三套。
func TestDarkTokenSingleGeneration(t *testing.T) {
	want := map[string]string{
		"--bg":    "#151a21",
		"--card":  "#1c222b",
		"--ink":   "#e7ecf3",
		"--muted": "#9aa7b6",
		"--line":  "#2a323d",
	}
	for name, exp := range want {
		got, ok := darkTokenVal(t, name)
		if !ok {
			t.Errorf("定版段缺令牌 %s", name)
			continue
		}
		if !strings.EqualFold(got, exp) {
			t.Errorf("%s 定版值应为 %s，实际 %s（暗色基底不能出现第二个版本）", name, exp, got)
		}
	}
}

// TestSurfaceTokensExist 语义面令牌必须定义，
// 且暗色下有值 —— 第一代那些硬编码表面色全靠它替代。
func TestSurfaceTokensExist(t *testing.T) {
	css := stripCSSComments(styleCSSForTest(t))
	for _, name := range []string{"--surface-sunken", "--surface-inset"} {
		if !strings.Contains(css, name+":") {
			t.Errorf("缺少语义面令牌 %s", name)
		}
	}
	for _, name := range []string{"--surface-sunken", "--surface-inset"} {
		if _, ok := darkTokenVal(t, name); !ok {
			t.Errorf("%s 在定版暗色段里没有赋值，暗色下会退化成透明", name)
		}
	}
}

// TestDarkNotLightInsideMedia 关键守卫：html:not([data-theme="light"]) 必须
// 待在 @media (prefers-color-scheme: dark) 内部。
//
// 这条是本轮真实踩到的坑：写定时把它和 html[data-theme="dark"] 用逗号并列，
// 提到了 media 之外。后果是浅色系统下、且用户从未手动选过主题时
// （html 上无 data-theme 属性）not([data-theme=light]) 同样成立，
// 暗色被强加给浅色用户 —— 整站配色错乱且难以自查。
func TestDarkNotLightInsideMedia(t *testing.T) {
	clean := stripCSSComments(styleCSSForTest(t))

	// 找出所有 html:not([data-theme="light"]) 出现处，
	// 判断它是否落在某个 @media (prefers-color-scheme: dark) 的花括号内。
	needle := `html:not([data-theme="light"])`
	idx := 0
	for {
		i := strings.Index(clean[idx:], needle)
		if i < 0 {
			break
		}
		pos := idx + i
		idx = pos + len(needle)

		if !insideDarkMedia(clean, pos) {
			// 找出所在行，方便定位
			line := 1 + strings.Count(clean[:pos], "\n")
			t.Errorf("第 %d 行的 html:not([data-theme=\"light\"]) 不在 "+
				"@media (prefers-color-scheme: dark) 内，会把暗色强加给浅色系统用户", line)
		}
	}
}

// insideDarkMedia 用花括号配平判断 pos 是否位于 @media (prefers-color-scheme: dark) 内。
//
// 做法：从头扫到 pos，遇到 '@media' 且其条件含 prefers-color-scheme: dark 时
// 记下一个待闭合标记；每遇一个 '{' 入栈、'}' 出栈。扫完后若栈里还留着
// dark media 标记，说明 pos 落在某个尚未闭合的 dark media 内。
// 纯字符扫描，不依赖任何 CSS 解析库。
func insideDarkMedia(css string, pos int) bool {
	const tok = "@media"
	stack := []bool{} // 每层是否为 dark media
	i := 0
	for i < pos {
		// 只关心 @media 与花括号
		if strings.HasPrefix(css[i:], tok) {
			// 取该 @media 到下一个 '{' 之间的条件文本
			j := i + len(tok)
			depth := 0
			for j < pos {
				if css[j] == '{' {
					break
				}
				if css[j] == '}' {
					depth--
				}
				j++
			}
			cond := css[i:min(j, pos)]
			if depth == 0 {
				stack = append(stack, strings.Contains(cond, "prefers-color-scheme: dark"))
			}
			i = j
			continue
		}
		switch css[i] {
		case '{':
			stack = append(stack, false)
		case '}':
			if len(stack) > 0 {
				stack = stack[:len(stack)-1]
			}
		}
		i++
	}
	for _, isDark := range stack {
		if isDark {
			return true
		}
	}
	return false
}

// TestContrastFuncSelfCheck 是 lum/contrast 的自校验。
//
// 为什么必须有：把 WCAG 公式抄错（比如 2.4 次方写成 *2.4）时，
// 对比度会整体偏低，表现为"本来达标的配色报不达标"。
// 这种错误不会让测试变绿，而是让**所有**对比度断言都不可信 ——
// 更糟的是如果公式偏高的方向写错，真实的不达标会被判为达标。
// 所以用WCAG 官方给出的已知值钉死实现。
func TestContrastFuncSelfCheck(t *testing.T) {
	cases := []struct {
		a, b string
		want float64
	}{
		{"#000000", "#ffffff", 21.0},  // 对比度上限
		{"#ffffff", "#ffffff", 1.0},   // 同色
		{"#777777", "#ffffff", 4.48},  // WCAG 示例值
		{"#e7ecf3", "#1c222b", 13.47}, // 本项目暗色 ink/card 实测
	}
	for _, c := range cases {
		got := contrast(c.a, c.b)
		if math.Abs(got-c.want) > 0.05 {
			t.Errorf("contrast(%s,%s)=%.2f，应为 %.2f —— lum 公式可能写错了",
				c.a, c.b, got, c.want)
		}
	}
}

// TestDarkContrastAA 暗色定版后的核心对比度必须过 WCAG AA。
// 实测值：ink/card 13.47、muted/card 6.53、muted/bg 7.14，均远高于 4.5。
// 这条把测量固化成断言，将来谁改了基底色会立刻被拦下。
func TestDarkContrastAA(t *testing.T) {
	bg, _ := darkTokenVal(t, "--bg")
	card, _ := darkTokenVal(t, "--card")
	ink, _ := darkTokenVal(t, "--ink")
	muted, _ := darkTokenVal(t, "--muted")
	sunken, _ := darkTokenVal(t, "--surface-sunken")
	inset, _ := darkTokenVal(t, "--surface-inset")
	if bg == "" || card == "" || ink == "" {
		t.Fatal("暗色定版令牌读取失败")
	}

	cases := []struct {
		name   string
		fg, bg string
		min    float64
	}{
		{"正文 ink/card", ink, card, 4.5},
		{"次要文字 muted/card", muted, card, 4.5},
		{"次要文字 muted/bg", muted, bg, 4.5},
		{"表头 sunken 上的 ink", ink, sunken, 4.5},
		{"输入框 inset 上的 ink", ink, inset, 4.5},
		{"表头 sunken 上的 muted", muted, sunken, 3.0}, // 大字/次要，3:1
	}
	for _, c := range cases {
		got := contrast(c.fg, c.bg)
		if got < c.min {
			t.Errorf("%s 对比度 %.2f < 门槛 %.1f（AA 不达标）", c.name, got, c.min)
		}
	}
}

// lastSkinDarkBody 返回该皮肤「手动暗色入口」最后一次出现时的规则体。
//
// 必须取最后一次：第 659-780 行原本就有 5 套皮肤的暗色规则（只覆盖 --bg），
// 方案 B-2 在文件末尾又追加了一份补齐中性色的版本。
// 用 strings.Index 会拿到前面那份旧的，测试就会误判"皮肤缺令牌"。
func lastSkinDarkBody(t *testing.T, css, skin string) (string, bool) {
	t.Helper()
	sel := `html[data-theme="dark"][data-skin="` + skin + `"]`
	last := strings.LastIndex(css, sel)
	if last < 0 {
		return "", false
	}
	body := css[last:]
	j := strings.Index(body, "{")
	if j < 0 {
		return "", false
	}
	body = body[j+1:]
	if e := strings.Index(body, "}"); e >= 0 {
		body = body[:e]
	}
	return body, true
}

// TestSkinDarkTokensComplete 5 套皮肤的暗色态必须补齐中性色，
// 否则就是「第一代底 + 第二代卡」的混合代配色。
func TestSkinTokensComplete(t *testing.T) {
	css := stripCSSComments(styleCSSForTest(t))
	skins := []string{"boy", "girl", "forest", "sunset", "starry"}
	for _, s := range skins {
		body, ok := lastSkinDarkBody(t, css, s)
		if !ok {
			t.Errorf("皮肤 %s 缺手动暗色入口 html[data-theme=\"dark\"][data-skin=\"%s\"]", s, s)
			continue
		}
		for _, tok := range []string{"--bg", "--card", "--ink", "--muted", "--line"} {
			if !strings.Contains(body, tok+":") {
				t.Errorf("皮肤 %s 暗色态缺中性色令牌 %s（混合代配色），规则体=%s", s, tok, strings.TrimSpace(body))
			}
		}
	}
}

// TestSkinDarkUsesFinalTokens 皮肤暗色的 --card 必须是定版后的值，
// 而不是第一代的 #182231。
func TestSkinDarkUsesFinalTokens(t *testing.T) {
	css := stripCSSComments(styleCSSForTest(t))
	card, _ := darkTokenVal(t, "--card")
	for _, s := range []string{"boy", "girl", "forest", "sunset", "starry"} {
		body, ok := lastSkinDarkBody(t, css, s)
		if !ok {
			continue
		}
		m := regexp.MustCompile(`--card\s*:\s*(#[0-9a-fA-F]{3,8})`).FindStringSubmatch(body)
		if m == nil {
			t.Errorf("皮肤 %s 暗色态未声明 --card，规则体=%s", s, strings.TrimSpace(body))
			continue
		}
		if !strings.EqualFold(m[1], card) {
			t.Errorf("皮肤 %s 暗色 --card=%s，应与定版一致为 %s", s, m[1], card)
		}
	}
}
