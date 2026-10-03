package web

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"studybuddy/internal/config"
)

// resetTBCache 清掉包级教材清单缓存，让每个用例都从自己的临时 manifest.json 起算，
// 避免受真实 data/textbook 目录影响。
func resetTBCache() {
	tbMu.Lock()
	defer tbMu.Unlock()
	tbCache, tbCacheMod, tbCacheOK = nil, time.Time{}, false
}

// newTBTestApp 造一个只读教材清单的 App，绕过 New（不需要 db / 登录态）。
// withAssets=true 时给每册补一份 meta.json，模拟图集已预渲染的正常情况。
func newTBTestApp(t *testing.T, manifest string, withAssets bool) *App {
	t.Helper()
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "manifest.json"), []byte(manifest), 0o644); err != nil {
		t.Fatalf("写临时清单失败: %v", err)
	}
	if withAssets {
		for _, b := range parseTBTestKeys(manifest) {
			sub := filepath.Join(dir, b)
			if err := os.MkdirAll(sub, 0o755); err != nil {
				t.Fatalf("建册目录失败: %v", err)
			}
			meta := `{"pages":100,"ratio":1.414,"hiWidth":1400,"loWidth":240,"coverWidth":600,"hiReady":true,"loReady":true}`
			if err := os.WriteFile(filepath.Join(sub, "meta.json"), []byte(meta), 0o644); err != nil {
				t.Fatalf("写 meta.json 失败: %v", err)
			}
		}
	}
	t.Setenv("STUDYBUDDY_TEXTBOOK_ASSETS", dir)
	resetTBCache()
	t.Cleanup(resetTBCache)
	return &App{Cfg: &config.Config{DataDir: dir}}
}

// parseTBTestKeys 从测试清单里取出所有 key，用于批量补 meta.json。
func parseTBTestKeys(manifest string) []string {
	var mf struct {
		Books []struct{ Key string } `json:"books"`
	}
	if err := json.Unmarshal([]byte(manifest), &mf); err != nil {
		return nil
	}
	out := make([]string, 0, len(mf.Books))
	for _, b := range mf.Books {
		out = append(out, b.Key)
	}
	return out
}

// 三册假数据：语文上/下、数学上、英语下，另加一册别的一年级语文（不该出现）。
const tbTestManifest = `{
  "generatedAt": "2026-10-03T00:00:00Z",
  "root": "ChinaTextbook",
  "stageNames": {"primary": "小学"},
  "books": [
    {"stage":"primary","grade":4,"bankGrade":4,"volume":2,"subject":"chinese","subjectCN":"语文","version":"统编版","title":"义务教育教科书·语文四年级下册","subTitle":"四年级 下册","key":"primary-chinese-g4-v2","pages":151},
    {"stage":"primary","grade":4,"bankGrade":4,"volume":1,"subject":"math","subjectCN":"数学","version":"人教版","title":"义务教育教科书·数学四年级上册","subTitle":"四年级 上册","key":"primary-math-g4-v1","pages":126},
    {"stage":"primary","grade":4,"bankGrade":4,"volume":1,"subject":"chinese","subjectCN":"语文","version":"统编版","title":"义务教育教科书·语文四年级上册","subTitle":"四年级 上册","key":"primary-chinese-g4-v1","pages":138},
    {"stage":"primary","grade":1,"bankGrade":1,"volume":1,"subject":"chinese","subjectCN":"语文","version":"统编版","title":"义务教育教科书·语文一年级上册","subTitle":"一年级 上册","key":"primary-chinese-g1-v1","pages":120},
    {"stage":"primary","grade":5,"bankGrade":5,"volume":1,"subject":"chinese","subjectCN":"语文","version":"统编版","title":"义务教育教科书·语文五年级上册","subTitle":"五年级 上册","key":"primary-chinese-g5-v1","pages":130},
    {"stage":"primary","grade":4,"bankGrade":4,"volume":1,"subject":"english","subjectCN":"英语","version":"人教版","title":"义务教育教科书·英语（PEP）（三年级起点）四年级上册","subTitle":"四年级 上册","key":"primary-english-g4-v1","pages":82},
    {"stage":"primary","grade":4,"bankGrade":4,"volume":1,"subject":"english","subjectCN":"英语","version":"人教版","title":"义务教育教科书·英语（精通）（三年级起点）四年级上册","subTitle":"四年级 上册","key":"primary-english-g4-v1-2","pages":98},
    {"stage":"primary","grade":4,"bankGrade":4,"volume":2,"subject":"english","subjectCN":"英语","version":"人教版","title":"义务教育教科书·英语（三年级起点）四年级下册","subTitle":"四年级 下册","src":"小学/英语/人教版（PEP）（三年级起点）（主编：吴欣）/义务教育教科书·英语（三年级起点）四年级下册.pdf","key":"primary-english-g4-v2","pages":83},
    {"stage":"primary","grade":4,"bankGrade":4,"volume":2,"subject":"english","subjectCN":"英语","version":"人教版","title":"义务教育教科书·英语（三年级起点）四年级下册","subTitle":"四年级 下册","src":"小学/英语/人教版（精通）（三年级起点）（主编：郝建平）/义务教育教科书·英语（三年级起点）四年级下册.pdf","key":"primary-english-g4-v2-3","pages":98}
  ]
}`

func cardKeys(cards []gin.H) []string {
	out := make([]string, 0, len(cards))
	for _, c := range cards {
		out = append(out, c["Key"].(string))
	}
	return out
}

func TestTBHomeCardsScope(t *testing.T) {
	a := newTBTestApp(t, tbTestManifest, false)
	cards := a.tbHomeCards("primary", 4, 0)

	// 期望口径：只留四年级（一年级 / 五年级那两册必须被滤掉），
	// 按学科中学习惯排序，同科内上册在前、下册在后。
	got := strings.Join(cardKeys(cards), ",")
	want := "primary-chinese-g4-v1,primary-chinese-g4-v2,primary-math-g4-v1," +
		"primary-english-g4-v1,primary-english-g4-v1-2," +
		"primary-english-g4-v2,primary-english-g4-v2-3"
	if got != want {
		t.Fatalf("筛选或排序不符\n得到: %s\n期望: %s", got, want)
	}
	for _, c := range cards {
		if c["Cover"] != "/textbook/asset/"+c["Key"].(string)+"/cover.webp" {
			t.Errorf("封面 URL 与 key 不匹配: %+v", c["Cover"])
		}
		if c["Name"] == "" || c["Alt"] == "" {
			t.Errorf("缺少名称文案: %+v", c)
		}
	}
	// 名称必须是「学科 · 册别」，且不含年级字样（年级已在卡片区标题上，避免每张卡重复）
	if n := cards[0]["Name"].(string); n != "语文 · 上册" {
		t.Errorf("教材名格式不符: %q", n)
	}
}

// 学期过滤是本次改造的核心口径：学生读上册就只能看到上册，读下册就只能看到下册，
// 另一学期的教材必须被滤掉。同时 volume=0（档案缺学期）要退化为该年级全部，
// 不能因为学期未知就整块空掉。
func TestTBHomeCardsFilterByVolume(t *testing.T) {
	a := newTBTestApp(t, tbTestManifest, false)

	up := strings.Join(cardKeys(a.tbHomeCards("primary", 4, 1)), ",")
	wantUp := "primary-chinese-g4-v1,primary-math-g4-v1," +
		"primary-english-g4-v1,primary-english-g4-v1-2"
	if up != wantUp {
		t.Errorf("上册筛选不符\n得到: %s\n期望: %s", up, wantUp)
	}

	down := strings.Join(cardKeys(a.tbHomeCards("primary", 4, 2)), ",")
	wantDown := "primary-chinese-g4-v2,primary-english-g4-v2,primary-english-g4-v2-3"
	if down != wantDown {
		t.Errorf("下册筛选不符\n得到: %s\n期望: %s", down, wantDown)
	}

	// 学期未知（volume=0）→ 该年级全部册别都要（上册 4 + 下册 3 = 7），不能空
	if all := a.tbHomeCards("primary", 4, 0); len(all) != 7 {
		t.Errorf("volume=0 应退化为该年级全部 7 册，实际 %d", len(all))
	}
}

// 「全一册 / 必修」类教材（Volume==0，如初高中教材）不受学期过滤影响，
// 否则初中高中学生的主页会整块空掉——booksFor 对 Volume==0 本就放行。
func TestTBHomeCardsKeepsVolumeless(t *testing.T) {
	const m = `{
  "books": [
    {"stage":"junior","grade":7,"bankGrade":7,"volume":0,"subject":"math","subjectCN":"数学","title":"义务教育教科书·数学七年级","key":"junior-math-g7","pages":120},
    {"stage":"junior","grade":7,"bankGrade":7,"volume":1,"subject":"chinese","subjectCN":"语文","title":"义务教育教科书·语文七年级上册","key":"junior-chinese-g7-v1","pages":130}
  ]
}`
	a := newTBTestApp(t, m, false)
	got := strings.Join(cardKeys(a.tbHomeCards("junior", 7, 2)), ",")
	if got != "junior-math-g7" {
		t.Errorf("全一册教材应保留在任意学期下，实际: %s", got)
	}
}

// 该年级一册教材都没有时返回空切片（模板据此渲染空状态），不能 panic。
func TestTBHomeCardsEmptyGrade(t *testing.T) {
	a := newTBTestApp(t, tbTestManifest, false)
	if cards := a.tbHomeCards("primary", 6, 1); len(cards) != 0 {
		t.Fatalf("无教材年级应返回空切片，实际 %d 条", len(cards))
	}
	if cards := a.tbHomeCards("high", 1, 1); len(cards) != 0 {
		t.Fatalf("错学段应返回空切片，实际 %d 条", len(cards))
	}
}

// 排序不得污染全局缓存：教材库页依赖 books() 原有的 grade/subject 字母序。
func TestTBHomeCardsNoCachePollution(t *testing.T) {
	a := newTBTestApp(t, tbTestManifest, false)

	before := make([]string, 0, 8)
	for _, b := range a.books() {
		before = append(before, b.Key)
	}
	_ = a.tbHomeCards("primary", 4, 0) // 触发中学习惯重排
	after := make([]string, 0, 8)
	for _, b := range a.books() {
		after = append(after, b.Key)
	}

	if strings.Join(before, ",") != strings.Join(after, ",") {
		t.Fatalf("books() 顺序被封面墙排序污染\n前: %v\n后: %v", before, after)
	}
	// books() 本身按 grade 优先，一年级应仍在最前
	if after[0] != "primary-chinese-g1-v1" {
		t.Errorf("books() 首项应为 grade 最小的册，实际 %s", after[0])
	}
}

// 同学科同册别有多册时（英语 PEP / 精通），名字必须带版本差异，否则用户分不清；
// 只有一册时保持「学科 · 册别」的干净短名。
func TestTBHomeCardNameDedup(t *testing.T) {
	a := newTBTestApp(t, tbTestManifest, false)
	names := map[string]string{}
	for _, c := range a.tbHomeCards("primary", 4, 0) {
		names[c["Key"].(string)] = c["Name"].(string)
	}

	if got := names["primary-english-g4-v1"]; got != "英语 · 上册（PEP）" {
		t.Errorf("英语 PEP 册名应带版本后缀，实际 %q", got)
	}
	if got := names["primary-english-g4-v1-2"]; got != "英语 · 上册（精通）" {
		t.Errorf("英语精通册名应带版本后缀，实际 %q", got)
	}
	// 唯一一册不加后缀
	if got := names["primary-math-g4-v1"]; got != "数学 · 上册" {
		t.Errorf("唯一册不应加后缀，实际 %q", got)
	}
	// 标题完全相同的两册（下册 PEP / 精通），必须靠源目录版本区分开
	if got := names["primary-english-g4-v2"]; got != "英语 · 下册（PEP）" {
		t.Errorf("同标题册应退回用源目录版本区分，实际 %q", got)
	}
	if got := names["primary-english-g4-v2-3"]; got != "英语 · 下册（精通）" {
		t.Errorf("同标题册应退回用源目录版本区分，实际 %q", got)
	}
	// 加了后缀后仍不能重名
	seen := map[string]string{}
	for k, n := range names {
		if prev, ok := seen[n]; ok {
			t.Errorf("封面卡重名 %q：%s 与 %s", n, prev, k)
		}
		seen[n] = k
	}
}

// tbSrcNote 应跳过「主编」这类无区分度的括注，取真正的版本说明。
func TestTBSrcNote(t *testing.T) {
	cases := []struct{ src, want string }{
		{"小学/英语/人教版（PEP）（三年级起点）（主编：吴欣）/x.pdf", "PEP"},
		{"小学/音乐/人教版（简谱）/x.pdf", "简谱"},
		{"小学/语文/统编版/x.pdf", ""},
		{"", ""},
	}
	for _, c := range cases {
		if got := tbSrcNote(c.src); got != c.want {
			t.Errorf("tbSrcNote(%q) = %q，期望 %q", c.src, got, c.want)
		}
	}
}
