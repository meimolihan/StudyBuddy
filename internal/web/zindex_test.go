package web

import (
	"regexp"
	"strconv"
	"strings"
	"testing"
)

// 方案 B 的结构性修复测试。方案 A 修的是「看得见的 bug」，
// 方案 B 修的是「隐患」——这类问题不会立刻报错，但会慢慢吃掉可维护性，
// 所以必须用测试把住，否则下一次随手改样式就会把层级/语义弄乱。

// zOf 读某选择器最终生效的 z-index，支持 var(--z-xxx) 形式。
//
// 注意 CSS 语义：同一个选择器可以在多条规则里出现，z-index 也可能分散声明
// （本项目就有「共享基础层」+「位置参数化」两条规则）。
// 真正生效的是**最后一个含 z-index 声明的匹配规则块**，而不是最后一个匹配块。
// 所以这里要遍历所有匹配块，取最后一个带 z-index 的。
func zOf(t *testing.T, sel string) (int, bool) {
	t.Helper()
	css := styleCSSForTest(t)
	body, ok := lastZDeclBlock(t, css, sel)
	if !ok {
		return 0, false
	}
	m := regexp.MustCompile(`z-index\s*:\s*([^;}]+)`).FindStringSubmatch(body)
	if m == nil {
		return 0, false
	}
	raw := strings.TrimSpace(m[1])
	if strings.HasPrefix(raw, "var(") {
		name := strings.TrimSuffix(strings.TrimPrefix(raw, "var("), ")")
		name = strings.TrimSpace(name)
		clean := stripCSSComments(css)
		mm := regexp.MustCompile(regexp.QuoteMeta(name) + `\s*:\s*(\d+)`).FindStringSubmatch(clean)
		if mm == nil {
			t.Fatalf("z-index 引用了未定义的令牌 %s", name)
		}
		n, _ := strconv.Atoi(mm[1])
		return n, true
	}
	n, err := strconv.Atoi(raw)
	if err != nil {
		return 0, false
	}
	return n, true
}

// lastZDeclBlock 返回「最后一个既匹配 sel、又含 z-index 声明」的规则体。
func lastZDeclBlock(t *testing.T, css, sel string) (string, bool) {
	t.Helper()
	clean := stripCSSComments(css)
	// 分隔符：行首 / 逗号 / 右花括号 / 分号，确保不会把 .sw-body 误配到 .sw-body-foo
	re := regexp.MustCompile(`(?:^|[},;])\s*` + regexp.QuoteMeta(sel) + `\s*\{`)
	locs := re.FindAllStringIndex(clean, -1)
	for i := len(locs) - 1; i >= 0; i-- {
		rest := clean[locs[i][0]:]
		j := strings.Index(rest, "{")
		if j < 0 {
			continue
		}
		body := rest[j+1:]
		if k := strings.Index(body, "}"); k >= 0 {
			body = body[:k]
		}
		if strings.Contains(body, "z-index") {
			return body, true
		}
	}
	return "", false
}

// TestZTokensDefined 6 档层级令牌必须齐全且严格递增。
// 递增是硬要求：令牌最大的价值就是「新代码不会写出比遮罩还低的层级」。
func TestZTokensDefined(t *testing.T) {
	clean := stripCSSComments(styleCSSForTest(t))
	order := []string{"--z-base", "--z-panel", "--z-dock", "--z-mask", "--z-toast", "--z-splash"}
	prev := -1
	for _, name := range order {
		mm := regexp.MustCompile(regexp.QuoteMeta(name) + `\s*:\s*(\d+)`).FindStringSubmatch(clean)
		if mm == nil {
			t.Fatalf("缺少层级令牌 %s", name)
		}
		n, _ := strconv.Atoi(mm[1])
		if n <= prev {
			t.Errorf("层级令牌 %s=%d 未大于前一档 %d，层级必须严格递增", name, n, prev)
		}
		prev = n
	}
}

// TestZTokenNoRawValue 层级组件的最终 z-index 必须走令牌，不允许裸数字。
// 这是「收口」的核心：只要还有裸值，下一个人就会继续随手写。
func TestZTokenNoRawValue(t *testing.T) {
	comps := []string{
		".topbar", ".sw-body", ".setpanel", ".fab-dock",
		".sheetscrim", ".sb-modal-mask", ".sb-toast", ".qt-toast", ".splash",
	}
	css := styleCSSForTest(t)
	for _, sel := range comps {
		body, ok := lastZDeclBlock(t, css, sel)
		if !ok {
			t.Errorf("%s 没有可定位的 z-index 声明，层级未收口", sel)
			continue
		}
		if !strings.Contains(body, "z-index:var(--z-") {
			t.Errorf("%s 的最终 z-index 未使用 var(--z-*) 令牌，仍是裸值：%s",
				sel, strings.TrimSpace(body))
		}
	}
}

// TestToastAboveMask 是本轮修复的核心回归点：
// 之前 .sb-toast=90 < .sheetscrim=200，批量删除的成功提示会被遮罩吞掉。
func TestToastAboveMask(t *testing.T) {
	toast, ok1 := zOf(t, ".sb-toast")
	qt, ok2 := zOf(t, ".qt-toast")
	sheet, ok3 := zOf(t, ".sheetscrim")
	mmask, ok4 := zOf(t, ".sb-modal-mask")
	if !ok1 || !ok2 || !ok3 || !ok4 {
		t.Fatalf("关键层级缺失 sb-toast=%v qt-toast=%v sheetscrim=%v sb-modal-mask=%v", ok1, ok2, ok3, ok4)
	}
	if toast <= sheet {
		t.Errorf("sb-toast(%d) 必须高于 sheetscrim(%d)，否则提示会被抽屉遮罩吞掉", toast, sheet)
	}
	if toast <= mmask {
		t.Errorf("sb-toast(%d) 必须高于 sb-modal-mask(%d)，否则提示会被弹窗遮罩吞掉", toast, mmask)
	}
	if qt <= sheet {
		t.Errorf("qt-toast(%d) 必须高于 sheetscrim(%d)", qt, sheet)
	}
	// splash 是全屏独占层，必须压住所有轻提示
	splash, _ := zOf(t, ".splash")
	if splash <= toast {
		t.Errorf("splash(%d) 应严格高于 sb-toast(%d)，开屏期间提示不该抢在最上层", splash, toast)
	}
}

// TestToastSingleComponent 两个 Toast 共享基础层实现，
// 防止将来又长出第三套 Toast 样式。
func TestToastSingleComponent(t *testing.T) {
	css := stripCSSComments(styleCSSForTest(t))
	if !strings.Contains(css, ".sb-toast,\n.qt-toast{") {
		t.Error("两个 Toast 应有一处共享的基础层规则（.sb-toast,\\n.qt-toast{...}）")
	}
	// 位置仍应分居顶/底，这是刻意的参数化差异
	if !strings.Contains(css, ".qt-toast{top:") {
		t.Error("qt-toast 应保持顶部定位")
	}
	if !strings.Contains(css, ".sb-toast{bottom:") {
		t.Error("sb-toast 应保持底部定位")
	}
}
