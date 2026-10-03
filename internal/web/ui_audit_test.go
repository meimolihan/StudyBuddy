package web

import (
	"strings"
	"testing"
)

// TestUIHiddenAttrNotBroken hidden 属性必须仍然生效。
//
// 这是本项目反复踩的同一个坑：给元素加了 display（flex/grid/block）之后，
// 作者样式的优先级会顶掉 UA 的 [hidden]{display:none}，
// 于是 JS 设的 el.hidden = true 失效，元素永久显示在页面上。
// 已经踩过四处：.sheetscrim / .sb-modal-mask / .sb-toast / .fab，
// 本轮又发现 .tb-thumbs 漏了，而我自己给 .tb-loading 加 display:flex 时也险些重蹈。
func TestUIHiddenAttrNotBroken(t *testing.T) {
	css := styleCSSForTest(t)

	// 凡是自己设了 display 的，都必须同时有 [hidden] 兜底
	cases := []struct{ sel, why string }{
		{".tb-thumbs", "教材详情页缩略图条，textbook.html:80 初始带 hidden；缺兜底时首屏渲染出一条空条带"},
		{".tb-loading", "教材阅读器加载态，JS 靠 loading.hidden=true 收起；缺兜底时骨架屏永久盖住教材"},
	}
	for _, c := range cases {
		if !strings.Contains(css, c.sel+"[hidden]") {
			t.Errorf("%s 缺 [hidden] 兜底规则 —— %s", c.sel, c.why)
		}
	}

	// 反向检查：不能给带 [hidden] 语义的元素又加 display 而不兜底。
	// 规则太宽会误报，这里只针对本轮动过的两个选择器做精确检查。
	for _, sel := range []string{".tb-thumbs", ".tb-loading"} {
		for _, rule := range cssRules(css) {
			s, body := splitRule(rule)
			s = strings.TrimSpace(s)
			if s != sel { // 只看基础规则（无后缀）
				continue
			}
			for _, disp := range []string{"display:flex", "display:grid", "display:block"} {
				if strings.Contains(body, disp) && !strings.Contains(css, sel+"[hidden]") {
					t.Errorf("%s 声明了 %s 但没有 [hidden] 兜底", sel, disp)
				}
			}
		}
	}
}

// TestUIReaderSkeleton 教材阅读器必须有骨架屏且尊重 reduced-motion。
func TestUIReaderSkeleton(t *testing.T) {
	css := styleCSSForTest(t)

	b, err := assetsFS.ReadFile("templates/textbook.html")
	if err != nil {
		t.Fatalf("读取 textbook.html 失败: %v", err)
	}
	html := string(b)

	// 骨架节点
	if !strings.Contains(html, `class="tb-skel"`) {
		t.Error("阅读器缺骨架屏节点 .tb-skel")
	}
	// 加载态需要无障碍播报，否则读屏器在图片到位时不提示
	if !strings.Contains(html, `role="status"`) || !strings.Contains(html, `aria-live="polite"`) {
		t.Error("加载态缺 role=status / aria-live，读屏器无法感知加载完成")
	}
	// 低清底图要有 onerror：LoReady 与 HasAssets 是两个独立判据，
	// 可能出现「标记有图集但低清文件缺失」，此时会留下破图
	if !strings.Contains(html, `id="tb-lo"`) ||
		!strings.Contains(html, `this.style.visibility='hidden'`) {
		t.Error("#tb-lo 缺 onerror 兜底，图集不完整时会显示破图")
	}

	// 微光动画必须能被 reduced-motion 关掉
	if !strings.Contains(css, "@keyframes tb-skel-pulse") {
		t.Error("缺 tb-skel-pulse 微光动画定义")
	}
	if !strings.Contains(css, ".tb-skel{animation:none") {
		t.Error("骨架微光未响应 prefers-reduced-motion，前庭敏感用户无法关闭")
	}
}

// TestUIAnimationTokens 动画令牌必须存在且落在 0.2~0.3s。
//
// 需求：统一使用 0.2~0.3s ease 缓动。此前全站时长从 .15s 到 .9s 共 16 种、
// 缓动 6 种，本轮用令牌收口，后续新代码只允许引用变量。
func TestUIAnimationTokens(t *testing.T) {
	css := styleCSSForTest(t)

	for _, v := range []string{"--dur:.25s", "--dur-fast:.2s", "--dur-slow:.3s", "--ease:ease"} {
		if !strings.Contains(css, v) {
			t.Errorf("缺动画令牌 %s", v)
		}
	}
	// 令牌值本身必须在区间内，防止有人把 --dur 改成 .9s
	for _, bad := range []string{"--dur:.9s", "--dur:1s", "--dur-fast:.5s", "--dur-slow:.8s"} {
		if strings.Contains(css, bad) {
			t.Errorf("动画令牌越界：%s（应落在 0.2~0.3s）", bad)
		}
	}
}

// TestUICoarseHitAreaFallback 触屏热区兜底必须用能压过基础规则的选择器。
//
// 修复前的 bug：@media(pointer:coarse) 段写 .tnav{min-height:44px}（0,1,0），
// 而基础规则是 .topbar nav .tnav{min-height:34px}（0,2,1），
// 0,2,1 胜出 → 兜底形同虚设，触屏下顶栏导航实际只有 34px。
func TestUICoarseHitAreaFallback(t *testing.T) {
	css := stripCSSComments(styleCSSForTest(t))

	// 必须存在与基础规则同等特异性的声明
	for _, want := range []string{
		".topbar nav .tnav{min-height:44px}",
		".topbar .setpick>summary{min-height:44px}",
	} {
		if !strings.Contains(css, want) {
			t.Errorf("缺触屏热区兜底「%s」—— 它必须与基础规则同等特异性才能生效", want)
		}
	}

	// pointer:coarse 段有 6 处，必须定位到**最后一个**（本轮新增的那个），
	// 用 strings.Index 会取到 1292 行那处，拿不到新加的兜底项。
	last := strings.LastIndex(css, "@media (pointer:coarse)")
	if last < 0 {
		t.Fatal("缺 @media (pointer:coarse) 段")
	}
	block := mediaBlock(css, last)
	for _, sel := range []string{".topbar .who", ".tb-chip", ".sw-vol", ".mini-select", ".toggle-password"} {
		if !strings.Contains(block, sel) {
			t.Errorf("触屏兜底段缺 %s 的 44px 声明", sel)
		}
	}
}