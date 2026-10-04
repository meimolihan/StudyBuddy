// Command e2e 在进程内跑一遍完整 HTTP 链路：注册 → 登录 → 学习主页 → 刷题 → 判分 → 归档 → 管理员页 → 导出 docx。
//
// 目的：验证所有页面模板可正常渲染（模板错误只会在真实请求时暴露）。
// 数据写入临时目录，不污染项目的 data/ 与 archive/。
//
// 用法：go run ./tools/e2e
package main

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"studybuddy/internal/config"
	"studybuddy/internal/db"
	"studybuddy/internal/textbook"
	"studybuddy/internal/web"
)

var fail int

func check(cond bool, msg string) {
	if cond {
		fmt.Println("  ✓", msg)
	} else {
		fmt.Println("  ✗", msg)
		fail++
	}
}

// sliceTBHome 从整页 HTML 中切出「官方教材」横幅卡（.tb-home）区块。
// 找不到时返回空串，让调用方的断言失败而不是假绿。
func sliceTBHome(page string) string {
	i := strings.Index(page, `<div class="card tb-home">`)
	if i < 0 {
		return ""
	}
	rest := page[i:]
	// 卡片是平级结构，遇到下一个 card 起始即为终点
	if j := strings.Index(rest[1:], `<div class="card `); j >= 0 {
		return rest[:j+1]
	}
	return rest
}

// sliceTBLib 切出教材库页的**教材卡片网格**区块。
// 必须切区块再断言：学段筛选条本身就会渲染「小学/初中/高中」三个可点 chip，
// 直接在整页里搜「小学」必然命中筛选项，而不是教材内容。
func sliceTBLib(page string) string {
	i := strings.Index(page, `<div class="tb-lib-grid`)
	if i < 0 {
		return ""
	}
	rest := page[i:]
	if j := strings.Index(rest[1:], `<div class="tb-lib-grid`); j >= 0 {
		return rest[:j+1]
	}
	if j := strings.Index(rest[1:], `<script`); j >= 0 {
		return rest[:j+1]
	}
	return rest
}

func main() {
	tmp, err := os.MkdirTemp("", "studybuddy-e2e")
	if err != nil {
		panic(err)
	}
	abs := func(p string) string { a, _ := filepath.Abs(p); return a }

	cfg := config.Load()
	cfg.Content = abs("content")
	cfg.DataDir = filepath.Join(tmp, "data")
	cfg.Archive = filepath.Join(tmp, "archive")

	// 教材图集：项目里已生成预渲染产物就指过去，跑「图集可用」的正常路径；
	// 没生成则留在临时目录，自动走「图集未生成」的降级路径。两条分支都要验证。
	tbAssets := os.Getenv("STUDYBUDDY_TEXTBOOK_ASSETS")
	if tbAssets == "" {
		real := abs(filepath.Join("data", "textbook"))
		if st, err := os.Stat(real); err == nil && st.IsDir() {
			os.Setenv("STUDYBUDDY_TEXTBOOK_ASSETS", real)
			tbAssets = real
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

	// 取一个课程 key 备用：优先挑单选 ≥6 且多选 ≥4 的课，以便严格校验「6 单选 + 4 多选」
	// （部分课程如英语句型课多选题只有 2 道，程序会按设计回退补单选，属正常行为）
	keys := make([]string, 0, len(tree.Lessons))
	for k := range tree.Lessons {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	sampleKey := keys[0]
	for _, k := range keys {
		qs, _ := tree.Lessons[k].Bank()
		s, m := 0, 0
		for _, q := range qs {
			if q.IsMulti() {
				m++
			} else {
				s++
			}
		}
		if s >= 6 && m >= 4 {
			sampleKey = k
			break
		}
	}

	fmt.Println("[1] 注册页与首位注册（应免邀请码、自动管理员）")
	w, body := do("GET", "/register", nil, "")
	check(w.Code == 200, fmt.Sprintf("GET /register -> %d", w.Code))
	check(strings.Contains(body, "首位注册者将自动成为管理员"), "提示首位注册者为管理员（无需邀请码）")
	check(strings.Contains(body, `name="gender"`), "注册页含性别选择")
	check(strings.Contains(body, "我是男生") && strings.Contains(body, "我是女生"),
		"性别文案为「我是男生 / 我是女生」")
	check(!strings.Contains(body, "g-emoji"), "性别选项已去掉前置 emoji")
	// 性别模块必须排在「学生姓名」之前。
	if gi, ni := strings.Index(body, "fg-gender"), strings.Index(body, `name="name"`); gi >= 0 && ni >= 0 {
		check(gi < ni, "性别选择排在学生姓名上方")
	}
	check(strings.Count(body, `type="radio" name="stage"`) == 3, "注册页含小学/中学/高中三选一学段")
	check(strings.Contains(body, `id="grade-field"`) && strings.Contains(body, `id="grade-value"`),
		"注册页年级为点击弹窗选择（含 hidden 提交字段）")
	check(strings.Contains(body, `id="class-field"`) && strings.Contains(body, `name="class_no"`),
		"注册页班级为点击弹窗选择（含 hidden 提交字段）")
	check(strings.Contains(body, `id="pick-scrim"`) && strings.Contains(body, `id="pick-wheel"`),
		"注册页含滚轮弹窗骨架（遮罩 + 滚轮容器）")
	check(strings.Contains(body, `id="pick-cancel"`) && strings.Contains(body, `id="pick-ok"`),
		"弹窗含取消 / 确定按钮")
	check(strings.Contains(body, `id="pick-num"`), "弹窗内保留手动输入数字的兜底")
	check(strings.Contains(body, "data-stages="), "注册页注入学段配置（驱动年级滚轮）")
	check(strings.Contains(body, "data-max-class="), "注册页注入班级上限")
	check(!strings.Contains(body, `id="grade-range"`) && !strings.Contains(body, `class="slider"`),
		"注册页已移除旧的滑轨选择器")
	// 「滑得太快、停不准」的修复核心：自己接管 wheel 事件，一档滚轮只走一行；
	// 再配方向键逐行微调与鼠标拖拽两条精确路径。缺任何一条手感都会退化，这里锁住。
	check(strings.Contains(body, "{ passive: false }"), "注册页接管了 wheel 事件（否则一档跳好几行）")
	check(strings.Contains(body, "STEP_PX") && strings.Contains(body, "Math.abs(dy) >= 90"),
		"滚轮按「一整档 = 一行」换算，触摸板按累积像素换行")
	check(strings.Contains(body, "ArrowDown") && strings.Contains(body, "ArrowUp") &&
		strings.Contains(body, "KEY_GAP"), "弹窗支持方向键逐行微调（长按限速）")
	check(strings.Contains(body, "pointerdown") && strings.Contains(body, "setPointerCapture") &&
		strings.Contains(body, "endDrag"), "弹窗支持鼠标拖拽换行、松手吸附")
	_, regCSS := do("GET", "/static/style.css", nil, "")
	check(strings.Contains(regCSS, ".wheel.is-drag,.wheel.is-anim{scroll-snap-type:none}"),
		"拖拽 / 补间期间关闭 scroll-snap（否则位移被吸附拽住，拖不动也补不动）")
	check(strings.Contains(regCSS, "user-select:none"), "滚轮区禁掉文字选中（拖拽时不会选中文字）")
	// scroll-snap 只留给触摸屏：鼠标侧的滚动 / 拖拽 / 补间都是脚本自己定位，
	// 开着吸附会在恢复的那一帧把程序化写入的位置顶回去。
	check(strings.Contains(regCSS, "@media (hover:none),(pointer:coarse)") &&
		strings.Contains(regCSS, "scroll-snap-type:y mandatory"),
		"scroll-snap 只对触摸设备生效（鼠标侧避免与脚本定位打架）")
	// 位置更新必须自己用 rAF 补间：带 scroll-snap 的嵌套容器上浏览器可能忽略
	// scrollTo({behavior:'smooth'})，那样高亮动了列表却不动 —— 这条也锁住。
	check(strings.Contains(body, "requestAnimationFrame") && strings.Contains(body, "animToken"),
		"滚轮定位用自写 rAF 补间（不依赖浏览器的平滑滚动）")
	// 学段配置必须是「对象」（以学段键为键），否则前端 stages["middle"] 取不到值，
	// 会静默退回小学的 6 个年级刻度——这里锁死形状。
	if i := strings.Index(body, `data-stages="`); i >= 0 {
		rest := body[i+len(`data-stages="`):]
		check(strings.HasPrefix(rest, "{"), "学段配置为对象形状（前端可按学段键直取）")
		check(strings.Contains(rest, "primary") && strings.Contains(rest, "middle") && strings.Contains(rest, "high"),
			"学段配置含小学/中学/高中三种")
	}
	check(!strings.Contains(body, `name="class"`), "注册页已移除「xx年级xx班」自由文本输入")

	// 未选性别必须被拦下（不建号）
	w, body = do("POST", "/register", url.Values{
		"name": {"郭奕凡"}, "stage": {"primary"}, "grade": {"4"}, "class_no": {"2"},
		"username": {"guoyifan"}, "password": {"test123456"}, "volume": {"1"},
	}, "")
	check(strings.Contains(body, "请选择性别"), "未选择性别时注册被拒绝")
	if n, _ := g.CountUsers(); n != 0 {
		check(false, "未选性别不应建号")
	}

	// 学段非法 / 年级超出学段范围，都必须被拦下
	w, body = do("POST", "/register", url.Values{
		"name": {"郭奕凡"}, "stage": {"__bad__"}, "grade": {"1"},
		"username": {"guoyifan"}, "password": {"test123456"}, "gender": {"male"},
	}, "")
	check(strings.Contains(body, "请选择学段"), "非法学段被拒绝")
	w, body = do("POST", "/register", url.Values{
		"name": {"郭奕凡"}, "stage": {"primary"}, "grade": {"9"},
		"username": {"guoyifan"}, "password": {"test123456"}, "gender": {"male"},
	}, "")
	check(strings.Contains(body, "请选择年级"), "小学 9 年级被拒绝（超出学段范围）")
	if n, _ := g.CountUsers(); n != 0 {
		check(false, "校验失败不应建号")
	}

	n0, _ := g.CountUsers()
	w, _ = do("POST", "/register", url.Values{
		"name": {"郭奕凡"}, "stage": {"primary"}, "grade": {"4"}, "class_no": {"2"},
		"username": {"guoyifan"}, "password": {"test123456"}, "volume": {"1"},
		"gender": {"male"},
	}, "")
	cookie := w.Header().Get("Set-Cookie")
	tok := ""
	if i := strings.Index(cookie, "sb_session="); i >= 0 {
		rest := cookie[i+len("sb_session="):]
		if j := strings.IndexAny(rest, ";"); j >= 0 {
			tok = rest[:j]
		} else {
			tok = rest
		}
	}
	check(w.Code == 303 && tok != "", "注册成功并下发会话 Cookie")
	u, err := g.ByUsername("guoyifan")
	check(err == nil && u != nil && u.Role == "admin", "首位用户角色为 admin")
	check(err == nil && u != nil && u.Stage == "primary", "学段 primary（小学）已入库")
	check(err == nil && u != nil && u.Grade == 4, "滑动选择年级 4 已入库")
	check(err == nil && u != nil && u.Class == "四年级二班", "学段+年级+班级拼出「四年级二班」")
	check(err == nil && u != nil && u.Gender == "male", "性别 male 已入库")
	check(err == nil && u != nil && u.Skin == "boy", "首位男生注册者自动匹配「男生主题」")
	check(n0 == 0, "注册前系统无用户")

	ck := "sb_session=" + tok

	fmt.Println("\n[2] 受保护页面")
	w, body = do("GET", "/study", nil, ck)
	check(w.Code == 200, fmt.Sprintf("GET /study -> %d", w.Code))
	check(!strings.Contains(body, "模板渲染失败"), "学习主页模板渲染正常")
	check(strings.Contains(body, `data-skin="boy"`), "男生用户页面按性别渲染 data-skin=boy")
	check(strings.Contains(body, "当前进度"), "学习主页显示当前进度")
	check(strings.Contains(body, "教材导航") || strings.Contains(body, "四年级 · 上册"),
		"学习主页显示教材导航（动态标题）")
	check(strings.Contains(body, "grade-switcher") && strings.Contains(body, "切换年级"),
		"教材导航含「切换年级」菜单")
	check(strings.Contains(body, "道德与法治"), "导航树识别出道德与法治科目")

	w, body = do("GET", "/lesson?key="+url.QueryEscape(sampleKey), nil, ck)
	check(w.Code == 200 && !strings.Contains(body, "模板渲染失败"), "课程页渲染正常")
	check(strings.Contains(body, "开始在线自测"), "课程页有开始自测入口")

	// 2.1 题型切换：choose（选择题）↔ judge（判断题）镜像题库
	var judgeKey, chooseKey string
	for k, l := range tree.Lessons {
		if l.QType == "judge" && judgeKey == "" {
			judgeKey = k
			if tw, ok := tree.Lessons[l.TwinKey()]; ok {
				chooseKey = tw.Key
			}
			break
		}
	}
	check(judgeKey != "" && strings.Contains(judgeKey, "/judge/"),
		"扫描到判断题镜像题库（judge 目录）")
	check(chooseKey != "" && strings.Contains(chooseKey, "/choose/"),
		"判断题课能取到同课的选择题镜像（choose 目录）")

	w, body = do("GET", "/study?qt=judge", nil, ck)
	check(w.Code == 200 && !strings.Contains(body, "模板渲染失败"), "学习主页（判断题）渲染正常")
	check(strings.Contains(body, `href="/study?qt=choose"`) && strings.Contains(body, `href="/study?qt=judge"`),
		"学习主页含选择题 / 判断题切换入口")
	// 页首 qtype-tabs 已移除，切换入口只有「开始做题」三张 qtype-card。
	// 当前题型（qt=judge）由判断题那张卡的 .is-on 表达。
	check(strings.Contains(body, `class="qtype-card is-on"`) &&
		strings.Contains(body, `href="/study?qt=judge"`), "当前题型入口卡高亮")
	// 回归保护：页首不应再出现那组重复控件
	check(!strings.Contains(body, "qtype-tabs"), "学习主页已无页首题型切换标签（避免与入口卡重复）")
	// 教材导航重构后主树只渲染当前视图（用户档案 primary/g4/v1）这一个年级册别，
	// 所以这里改用「该视图内」的 judge 课来断言，而不是全库第一门 judge 课。
	viewJudge, viewChoose := "", ""
	for k, l := range tree.Lessons {
		if l.Stage != "primary" || l.Grade != 4 || l.Volume != 1 {
			continue
		}
		if l.QType == "judge" && viewJudge == "" {
			viewJudge = k
		}
		if l.QType == "choose" && viewChoose == "" {
			viewChoose = k
		}
	}
	check(viewJudge != "", "primary/g4/v1 视图下存在 judge 课")
	// 注：目录名可能含空格，html/template 的 urlquery 会把空格转成 %20（而非 +），
	// 所以这里用原始 key 匹配（课程链接与「设为当前」表单里都有）。
	check(strings.Contains(body, viewJudge), "判断题模式下目录列出当前视图的 judge 课程")
	check(strings.Count(body, "/judge/") > 20, "判断题目录渲染出当前视图的题库")

	w, body = do("GET", "/study?qt=choose", nil, ck)
	check(w.Code == 200 && strings.Contains(body, viewChoose),
		"选择题模式下目录列出当前视图的 choose 课程")

	w, body = do("GET", "/lesson?key="+url.QueryEscape(judgeKey), nil, ck)
	check(w.Code == 200 && !strings.Contains(body, "模板渲染失败"), "判断题课程页渲染正常")
	check(strings.Contains(body, "切换到选择题"), "判断题课程页有切换到选择题的互跳入口")
	w, body = do("GET", "/lesson?key="+url.QueryEscape(chooseKey), nil, ck)
	check(strings.Contains(body, "切换到判断题"), "选择题课程页有切换到判断题的互跳入口")

	fmt.Println("\n[3] 刷题与判分")
	w, body = do("GET", "/quiz?key="+url.QueryEscape(sampleKey), nil, ck)
	check(w.Code == 200 && !strings.Contains(body, "模板渲染失败"), "刷题页渲染正常")
	nQ := strings.Count(body, `class="q"`)
	check(nQ == 10, fmt.Sprintf("刷题页显示 %d 道题", nQ))
	nRadio := strings.Count(body, `type="radio"`)
	nCheck := strings.Count(body, `type="checkbox"`)
	check(nRadio == 24 && nCheck == 16, fmt.Sprintf("单选 6 题×4 选项=%d，多选 4 题×4 选项=%d", nRadio, nCheck))

	form := url.Values{"key": {sampleKey}}
	for i := 0; i < 10; i++ {
		form.Set(fmt.Sprintf("q%d", i), "0") // 全部选 A，用于验证判分链路
	}
	w, _ = do("POST", "/quiz/submit", form, ck)
	loc := w.Header().Get("Location")
	check(w.Code == 303 && strings.Contains(loc, "/result?id="), "提交后跳转到结果页")

	if strings.Contains(loc, "/result?id=") {
		w, body = do("GET", loc, nil, ck)
		check(w.Code == 200 && !strings.Contains(body, "模板渲染失败"), "结果页渲染正常")
		check(strings.Contains(body, "逐题解析"), "结果页含逐题解析")
		check(strings.Contains(body, "得分"), "结果页显示得分")
	}

	fmt.Println("\n[4] 归档")
	w, body = do("GET", "/archive", nil, ck)
	check(w.Code == 200 && !strings.Contains(body, "模板渲染失败"), "归档列表页渲染正常")
	check(strings.Contains(body, "#1"), "归档列表包含第 1 条记录")

	// 4.1 归档页新增组件：复选框 / 批量删除 / 单行删除 / 确认弹窗 / Toast / 开屏动画脚本
	check(strings.Contains(body, "sb-row-check") && strings.Contains(body, "sb-check-all"),
		"归档列表含行复选框与全选复选框")
	check(strings.Contains(body, "sb-batch-del"), "归档列表含批量删除按钮")
	check(strings.Contains(body, "sb-del-btn"), "归档列表含单行删除按钮")
	check(strings.Contains(body, "sb-modal") && strings.Contains(body, "确认删除该试卷？删除后数据无法恢复。"),
		"归档页含删除确认弹窗及固定文案")
	check(strings.Contains(body, "sb-toast"), "归档页含 Toast 提示容器")
	check(strings.Contains(body, "/static/vendor/sal.js") && strings.Contains(body, "sb-intro-played"),
		"开屏动画引入 Sal.js 并带会话标记（页面间跳转不重播）")
	w, body = do("GET", "/static/style.css", nil, ck)
	check(w.Code == 200 && strings.Contains(body, ".sb-modal-mask[hidden]{display:none}"),
		"弹窗遮罩 hidden 态显式 display:none（防 display:flex 顶掉 hidden 常驻盖页）")

	// 4.2 归档页题型分类：选择题 / 判断题筛选（qt=choose|judge，默认选择题）
	w, body = do("GET", "/archive", nil, ck)
	check(w.Code == 200 && strings.Contains(body, "qtype-tabs") &&
		strings.Contains(body, "/archive?qt=choose") && strings.Contains(body, "/archive?qt=judge"),
		"归档页含选择题/判断题切换选项卡")
	check(strings.Contains(body, "选择题 1") && strings.Contains(body, "判断题 0"),
		"归档页题型计数正确（本次自测为选择题）")
	w, body = do("GET", "/archive?qt=judge", nil, ck)
	check(w.Code == 200 && !strings.Contains(body, "模板渲染失败"), "判断题归档视图渲染正常")
	w, body = do("GET", "/archive/view?id=1", nil, ck)
	check(w.Code == 200 && strings.Contains(body, "badge") && strings.Contains(body, "/archive?qt="),
		"归档详情页带题型徽标并按题型返回列表")

	// 4.4 排版优化：方案 1「单栏聚焦流」（纯 CSS 追加段，全尺寸单列）
	w, body = do("GET", "/static/style.css", nil, ck) // 上面题型用例改写了 body，这里重新取 CSS
	check(strings.Contains(body, "main:has(.unitname){max-width:960px}"),
		"学习主页单栏聚焦流（960px 居中，不切双栏）")
	check(strings.Contains(body, "main > .card:first-of-type{margin-bottom:12px}") &&
		strings.Contains(body, "main > .card{margin-bottom:24px}"),
		"Hero 与数据条成组：首卡 12px、其余 24px")
	check(strings.Contains(body, "max-height:min(56vh,520px)"),
		"仅教材导航卡片内部滚动（单一滚动区）")
	check(!strings.Contains(body, "grid-template-columns:300px minmax(0,1fr)"),
		"已移除左栏工作台双栏栅格")
	check(strings.Contains(body, "@media (pointer:coarse)") && strings.Contains(body, "min-height:44px"),
		"触屏热区 ≥44px")
	check(strings.Contains(body, "@media (hover:hover)") &&
		strings.Contains(body, "transition:box-shadow .25s ease, transform .25s ease"),
		"hover 动效 0.25s ease 且仅在精确指针设备生效")

	// 4.5 视觉升级：悬浮球（左下明暗切换 / 右下返回顶部）、线性 SVG 图标、双主题令牌
	check(strings.Contains(body, ".fab-dock{") && strings.Contains(body, ".fab[hidden]{display:none"),
		"悬浮球容器与 hidden 兜底规则（防作者 display 顶掉 hidden）")
	check(strings.Contains(body, "--bg:#151a21") && strings.Contains(body, "html[data-theme=\"dark\"]"),
		"深色令牌为深灰基底且支持手动 data-theme")
	w, body = do("GET", "/study", nil, ck)
	check(strings.Contains(body, "fab-dock") && strings.Contains(body, "sb-fab-theme") &&
		strings.Contains(body, "sb-fab-top"), "页面含左下明暗切换与右下返回顶部悬浮球")
	check(strings.Contains(body, `<svg class="ico"`) && strings.Contains(body, "ico-when-dark"),
		"顶栏/悬浮球使用线性 SVG 图标并随主题切换图标")

	// 4.6 明暗模式一键切换：cookie 持久化 + 模板带出 data-theme（无闪烁）
	w, _ = do("GET", "/theme/mode?mode=dark&back=/study", nil, ck)
	check(w.Code == 303 && strings.Contains(w.Header().Get("Set-Cookie"), "sb_theme=dark"),
		"切换深色写入 sb_theme cookie 并回跳")
	w, body = do("GET", "/study", nil, ck+"; sb_theme=dark")
	check(strings.Contains(body, `data-theme="dark"`), "带深色 cookie 时页面渲染 data-theme=dark")
	w, _ = do("GET", "/theme/mode?mode=auto&back=/study", nil, ck)
	check(w.Code == 303, "切回跟随系统（auto）正常回跳")

	w, body = do("GET", "/archive/view?id=1", nil, ck)
	check(w.Code == 200 && !strings.Contains(body, "模板渲染失败"), "归档详情页渲染正常")

	// 4.2 单行删除：JSON 成功、列表刷新后不再包含
	w, body = do("POST", "/archive/delete", url.Values{"ids": {"1"}}, ck)
	check(w.Code == 200 && strings.Contains(body, `"ok":true`) && strings.Contains(body, `"deleted":1`),
		"单行删除接口返回 ok:true deleted:1")
	w, body = do("GET", "/archive", nil, ck)
	check(!strings.Contains(body, `value="1"`), "删除后归档列表不再包含该试卷")

	// 4.3 批量删除：再造两条记录后一次删两份；空选择返回 400
	w, _ = do("POST", "/quiz/submit", form, ck) // 第二份
	w, _ = do("POST", "/quiz/submit", form, ck) // 第三份
	w, body = do("POST", "/archive/delete", url.Values{"ids": {"2", "3"}}, ck)
	check(w.Code == 200 && strings.Contains(body, `"deleted":2`), "批量删除接口一次删除 2 份")
	w, _ = do("POST", "/archive/delete", url.Values{}, ck)
	check(w.Code == 400, "未选择试卷时批量删除返回 400")
	w, body = do("POST", "/archive/delete", url.Values{"ids": {"999"}}, ck)
	check(w.Code == 200 && strings.Contains(body, `"deleted":0`), "删除不存在的 id 返回 deleted:0")

	fmt.Println("\n[5] 管理员页与邀请码")
	w, body = do("GET", "/admin", nil, ck)
	check(w.Code == 200 && !strings.Contains(body, "模板渲染失败"), "管理员页渲染正常")
	check(strings.Contains(body, "生成邀请码"), "管理员页含邀请码功能")
	w, _ = do("POST", "/admin/invite/create", url.Values{"count": {"3"}}, ck)
	check(w.Code == 303, "生成邀请码成功")
	invites, _ := g.ListInvites()
	check(len(invites) == 3, fmt.Sprintf("已生成 %d 个邀请码", len(invites)))
	if len(invites) > 0 {
		w, _ = do("POST", "/admin/invite/revoke", url.Values{"code": {invites[0].Code}}, ck)
		check(w.Code == 303, "作废邀请码成功")
		check(!g.InviteValid(invites[0].Code), "被作废的邀请码不再有效")
	}
	// 关键：列表中已有邀请码（含「可用」「已作废」两种状态）时重新渲染管理员页。
	// 空列表时 range 不执行，模板错误不会暴露——必须在此断言。
	w, body = do("GET", "/admin", nil, ck)
	check(w.Code == 200 && !strings.Contains(body, "模板渲染失败"), "有邀请码时管理员页渲染正常")
	check(strings.Contains(body, invites[0].Code), "页面列出邀请码")
	check(strings.Contains(body, "已作废") && strings.Contains(body, "可用"), "同时渲染「已作废」与「可用」状态")
	check(strings.Contains(body, "作废</button>"), "可用状态显示作废按钮")

	fmt.Println("\n[6] 第二位注册必须邀请码")
	w, body = do("POST", "/register", url.Values{
		"name": {"同学甲"}, "class": {"三年级一班"},
		"username": {"user2"}, "password": {"test123456"}, "volume": {"1"},
		"gender": {"female"},
	}, "")
	check(strings.Contains(body, "系统已启用邀请码注册"), "无邀请码注册被拒绝")
	valid := ""
	for _, v := range invites {
		if g.InviteValid(v.Code) {
			valid = v.Code
			break
		}
	}
	if valid != "" {
		w, _ = do("POST", "/register", url.Values{
			"name": {"同学甲"}, "class": {"三年级一班"},
			"username": {"user2"}, "password": {"test123456"},
			"volume": {"1"}, "invite": {valid}, "gender": {"female"},
		}, "")
		u2, err := g.ByUsername("user2")
		check(err == nil && u2 != nil && u2.Role == "user", "持有效邀请码可注册，且角色为普通用户")
		// 旧格式（只提交一段「三年级一班」自由文本）必须继续可用：提取年级 + 按年级猜学段。
		check(err == nil && u2 != nil && u2.Grade == 3, "旧格式仍可从「三年级一班」提取年级 3")
		check(err == nil && u2 != nil && u2.Stage == "primary", "旧格式按年级推断学段为小学")
		check(err == nil && u2 != nil && u2.Class == "三年级一班", "旧格式班级文本原样保留")
		check(err == nil && u2 != nil && u2.Skin == "girl", "女生注册者自动匹配「女生主题」")
		// 邀请码被使用后重新渲染（覆盖 UsedBy != 0 的「已使用」分支，UsedBy 为 int64）
		w, body = do("GET", "/admin", nil, ck)
		check(w.Code == 200 && !strings.Contains(body, "模板渲染失败"), "邀请码被使用后管理员页仍渲染正常")
		check(strings.Contains(body, "已使用"), "页面显示「已使用」状态")
	}

	fmt.Println("\n[7] 导出 Word 试卷并归档")
	w, _ = do("POST", "/lesson/docx", url.Values{"key": {sampleKey}}, ck)
	ct := w.Header().Get("Content-Type")
	sz := len(w.Body.Bytes())
	check(w.Code == 200 && sz > 2000, fmt.Sprintf("docx 下载成功（%d 字节, %s）", sz, ct))
	check(string(w.Body.Bytes()[:2]) == "PK", "下载内容为合法 zip/docx")
	files, _ := os.ReadDir(filepath.Join(cfg.Archive, "1"))
	check(len(files) == 1, fmt.Sprintf("已归档到 archive/1/ 共 %d 个文件", len(files)))

	fmt.Println("\n[8] 权限隔离")
	w2, _ := do("GET", "/admin", nil, "") // 未登录
	check(w2.Code == 303, "未登录访问 /admin 被重定向到登录")

	fmt.Println("\n[9] 顶栏设置面板 / 主题切换")
	w, body = do("GET", "/study", nil, ck)
	check(strings.Contains(body, `class="setpick"`), "顶栏含「设置」入口")
	check(strings.Contains(body, `<span class="settxt">设置</span>`), "入口文案为「设置」")
	check(strings.Contains(body, "外观主题") && strings.Contains(body, "背景壁纸") &&
		strings.Contains(body, "账号"), "设置面板按「外观主题 / 背景壁纸 / 账号」分区")
	check(strings.Contains(body, "男生主题") && strings.Contains(body, "女生主题"), "主题列表含男生/女生主题")
	check(strings.Count(body, "skinchip") >= 7, "主题色卡列出全部主题（6 套皮肤 + 按性别自动）")
	check(strings.Contains(body, "退出登录"), "「退出」已收进设置面板")
	check(strings.Contains(body, `href="/admin"`), "「用户管理」已收进设置面板")
	check(!strings.Contains(body, "themepick") && !strings.Contains(body, "themeopt"),
		"旧的主题下拉入口已移除（不出现两处重复的设置入口）")
	check(!strings.Contains(body, `>用户管理</a>`), "顶栏导航里不再直接摆着「用户管理」")
	// 「退出」不再是顶栏上单摆的按钮，而是落在设置面板内部（DOM 顺序上晚于面板开始标签）。
	ip := strings.Index(body, `class="setpanel"`)
	il := strings.Index(body, `action="/logout"`)
	check(ip >= 0 && il > ip, "「退出」已收进设置面板内部（不再是顶栏上单摆的按钮）")
	check(strings.Contains(body, `class="tnav is-on"`), "顶栏高亮当前所在分区")
	check(strings.Contains(body, `class="avatar"`), "顶栏显示当前登录者头像")
	check(strings.Contains(body, "data-menu"), "下拉挂了 data-menu，供脚本做「点外面关闭」")

	// 回归锁：全站 details{overflow:hidden} 会把绝对定位的面板整块裁掉，
	// 表现就是「点了没反应」，所以 .setpick 必须复位 overflow。
	_, css := do("GET", "/static/style.css", nil, "")
	if i := strings.Index(css, ".topbar .setpick{"); i >= 0 {
		tail := css[i:]
		if len(tail) > 400 {
			tail = tail[:400]
		}
		check(strings.Contains(tail, "overflow:visible"), "设置面板已复位 overflow（不会被裁掉）")
	} else {
		check(false, "样式表缺少 .topbar .setpick 规则")
	}
	check(strings.Contains(css, ".setpick[open]>summary::before{content:none}"),
		"展开时不会多出一个「▾」箭头（summary::before 已清掉）")

	w, _ = do("GET", "/theme?skin=girl&back=%2Fstudy", nil, ck)
	loc2 := w.Header().Get("Location")
	check(w.Code == 303 && loc2 == "/study", "切换主题后返回原页面")
	if uu, err2 := g.ByUsername("guoyifan"); err2 == nil {
		check(uu.Skin == "girl", "自选主题已写入 users.skin")
	}
	w, body = do("GET", "/study", nil, ck)
	check(strings.Contains(body, `data-skin="girl"`), "手动选择后页面主题为 girl（覆盖性别默认值）")

	// 非法主题值回落到默认，不应写入脏数据
	w, _ = do("GET", "/theme?skin=__evil__&back=%2Fstudy", nil, ck)
	if uu, err2 := g.ByUsername("guoyifan"); err2 == nil {
		check(uu.Skin == "default", "非法主题键回落为默认主题")
	}
	// 开放重定向防护：站外 back 必须被丢弃
	w, _ = do("GET", "/theme?skin=boy&back=https%3A%2F%2Fevil.example", nil, ck)
	check(strings.HasPrefix(w.Header().Get("Location"), "/") &&
		!strings.HasPrefix(w.Header().Get("Location"), "//"), "拒绝站外 back 跳转（防开放重定向）")

	// 「按性别自动」清空自选值，重新按性别推导
	w, _ = do("GET", "/theme?skin=auto&back=%2Fstudy", nil, ck)
	if uu, err2 := g.ByUsername("guoyifan"); err2 == nil {
		check(uu.Skin == "", "「按性别自动」清空自选主题")
	}
	w, body = do("GET", "/study", nil, ck)
	check(strings.Contains(body, `data-skin="boy"`), "清空自选后按性别回落到 boy")

	fmt.Println("\n[10] 学段 / 年级 / 班级")
	// 管理员建号：中学 1 年级（七年级）3 班
	w, _ = do("POST", "/admin/user/create", url.Values{
		"name": {"中学生"}, "stage": {"middle"}, "grade": {"1"}, "class_no": {"3"},
		"username": {"middleschooler"}, "password": {"test123456"},
		"volume": {"1"}, "gender": {"female"}, "role": {"user"},
	}, ck)
	check(w.Code == 303, "管理员按学段/年级/班级建号成功")
	u3, err3 := g.ByUsername("middleschooler")
	check(err3 == nil && u3 != nil && u3.Stage == "middle", "学段 middle（中学）已入库")
	check(err3 == nil && u3 != nil && u3.Grade == 1 && u3.Class == "七年级三班",
		"中学 1 年级 → 展示为「七年级三班」")

	w, body = do("GET", "/admin", nil, ck)
	check(w.Code == 200 && !strings.Contains(body, "模板渲染失败"), "含中学用户时管理员页渲染正常")
	check(strings.Contains(body, "七年级三班"), "用户表展示中学班级")
	check(strings.Contains(body, ">中学</span>"), "用户表展示学段徽章")

	// 教材导航按学段展示年级名：切换年级菜单用 GradeLabel（四年级）+ 学段分组（小学）
	w, body = do("GET", "/study", nil, ck)
	check(strings.Contains(body, "四年级") && strings.Contains(body, "小学"),
		"切换年级菜单按学段分组展示年级（小学 / 四年级）")

	// 中学学生登录：当前只有小学教材，应优雅回退而不是报错
	w, _ = do("POST", "/login", url.Values{
		"username": {"middleschooler"}, "password": {"test123456"},
	}, "")
	ck3 := ""
	if sc := w.Header().Get("Set-Cookie"); strings.Contains(sc, "sb_session=") {
		rest := sc[strings.Index(sc, "sb_session=")+len("sb_session="):]
		if j := strings.IndexAny(rest, ";"); j >= 0 {
			ck3 = "sb_session=" + rest[:j]
		} else {
			ck3 = "sb_session=" + rest
		}
	}
	check(ck3 != "", "中学学生登录成功")
	if ck3 != "" {
		w, body = do("GET", "/study", nil, ck3)
		check(w.Code == 200 && !strings.Contains(body, "模板渲染失败"), "中学学生学习主页渲染正常（无中学教材时回退）")
	}

	fmt.Println("\n[11] 背景壁纸（目录结构与 content/ 同构，按学段 + 年级 + 册别自动匹配）")

	// 用户真实放进项目的壁纸：只做提示性检查，不作为测试前提（他可能换成别的名字）。
	const realWPName = "wallpapers/primary/pep/grade4/volume1/wallpaper.webp"
	if b, err := os.ReadFile(abs(realWPName)); err == nil && len(b) >= 12 {
		check(string(b[:4]) == "RIFF" && string(b[8:12]) == "WEBP", "项目内 "+realWPName+" 是合法 WebP")
	} else {
		fmt.Println("  · 提示：项目里暂无 " + realWPName + "，跳过该文件格式检查")
	}

	// 壁纸目录挂在项目根下；测试里换成临时目录，保证结果不受真实 wallpapers/ 里放了什么影响。
	wpDir := filepath.Join(tmp, "wallpapers")
	if err := os.MkdirAll(wpDir, 0o755); err != nil {
		panic(err)
	}
	cfg.BaseDir = tmp // app 持有同一个 cfg 指针，下一个请求即生效
	realWP, errWP := os.ReadFile(abs(realWPName))
	if errWP != nil {
		realWP = []byte("RIFF\x00\x00\x00\x00WEBPVP8 ")
	}
	writeWP := func(name string, data []byte) {
		p := filepath.Join(wpDir, filepath.FromSlash(name))
		if err := os.MkdirAll(filepath.Dir(p), 0o755); err != nil {
			panic(err)
		}
		if err := os.WriteFile(p, data, 0o644); err != nil {
			panic(err)
		}
	}
	rmWP := func(name string) {
		if err := os.Remove(filepath.Join(wpDir, filepath.FromSlash(name))); err != nil {
			panic(err)
		}
	}
	// 壁纸树里「有哪些出版社目录」是按目录扫出来的：只删文件会留下空目录，
	// 推荐路径就会少一层。需要回到干净状态时用整棵子树删。
	rmTree := func(dir string) {
		_ = os.RemoveAll(filepath.Join(wpDir, filepath.FromSlash(dir)))
	}

	lookup := func(stage string, grade, volume int) map[string]interface{} {
		_, b := do("GET", fmt.Sprintf("/api/wallpaper?stage=%s&grade=%d&volume=%d", stage, grade, volume), nil, "")
		var m map[string]interface{}
		_ = json.Unmarshal([]byte(b), &m)
		return m
	}
	lookupSub := func(stage string, grade, volume int, subject string) map[string]interface{} {
		_, b := do("GET", fmt.Sprintf("/api/wallpaper?stage=%s&grade=%d&volume=%d&subject=%s",
			stage, grade, volume, subject), nil, "")
		var m map[string]interface{}
		_ = json.Unmarshal([]byte(b), &m)
		return m
	}
	jstr := func(m map[string]interface{}, k string) string {
		if s, ok := m[k].(string); ok {
			return s
		}
		return ""
	}

	// A. 一个壁纸文件都没有：应报告未匹配，并给出「与 content/ 同构」的推荐路径。
	m := lookup("primary", 4, 1)
	check(m["matched"] == false, "目录为空时 matched=false")
	check(jstr(m, "want") == "primary/pep/grade4/wallpaper.webp",
		"首页推荐路径只到年级层：primary/pep/grade4/wallpaper.webp（上下册共用）")
	check(jstr(m, "url") == "", "未匹配时不返回 url")
	_, body = do("GET", "/study", nil, ck)
	check(!strings.Contains(body, "wp-layer") && !strings.Contains(body, "data-wallpaper"),
		"未匹配到壁纸时页面不输出壁纸层（对原页面零影响）")

	// B. 按新目录结构放入 → 立即生效（无需重启服务），URL 带完整相对路径。
	const nested = "primary/pep/grade4/volume1/wallpaper.webp"
	writeWP(nested, realWP)
	m = lookup("primary", 4, 1)
	check(m["matched"] == true && jstr(m, "name") == nested, "按新目录结构放入即匹配四年级上册")
	check(jstr(m, "url") == "/wallpapers/"+nested, "URL 为 /wallpapers/"+nested)

	w, img := do("GET", "/wallpapers/"+nested, nil, "")
	check(w.Code == 200 && w.Header().Get("Content-Type") == "image/webp",
		"多级路径的图片可访问，Content-Type 为 image/webp")
	check(strings.HasPrefix(img, "RIFF"), "壁纸内容原样返回")

	w, body = do("GET", "/study", nil, ck)
	check(strings.Contains(body, `data-wallpaper="`+nested+`"`), "学习主页按学籍注入 data-wallpaper（完整相对路径）")
	check(strings.Contains(body, `<img class="wp-layer" src="/wallpapers/`+nested+`"`),
		"学习主页渲染出壁纸层图片")

	// C. 同一层目录内：推荐的 wallpaper.webp 优先于各种别名。
	writeWP("primary/pep/grade4/volume1/g4-v1.webp", realWP)
	m = lookup("primary", 4, 1)
	check(jstr(m, "name") == nested, "同目录内 wallpaper.webp 优先于别名 g4-v1.webp")
	rmWP("primary/pep/grade4/volume1/g4-v1.webp")
	writeWP("primary/pep/grade4/volume1/primary-g4-v1.png", realWP)
	m = lookup("primary", 4, 1)
	check(jstr(m, "name") == nested, "同目录内 wallpaper.webp 仍优先于学段精确别名")
	rmWP("primary/pep/grade4/volume1/primary-g4-v1.png")

	// D. 新目录结构优先于老式平铺写法；删掉新结构后回落到平铺。
	writeWP("g4-v1.webp", realWP)
	m = lookup("primary", 4, 1)
	check(jstr(m, "name") == nested, "新目录结构优先于老式平铺的 g4-v1.webp")
	rmWP(nested)
	m = lookup("primary", 4, 1)
	check(jstr(m, "name") == "g4-v1.webp", "删掉新结构后回落到平铺的 g4-v1.webp")
	writeWP(nested, realWP)

	// E. 出版社这一层可以省略；首页只认「年级」这一层，同一张图上下册共用。
	writeWP("primary/grade4/volume1/wallpaper.webp", realWP)
	rmWP(nested)
	m = lookup("primary", 4, 1)
	check(jstr(m, "name") == "primary/grade4/volume1/wallpaper.webp",
		"省略出版社层（primary/grade4/volume1/）同样能匹配")
	check(jstr(m, "want") == "primary/grade4/wallpaper.webp",
		"存在多个出版社目录时推荐路径省略出版社这一层，且只到年级层（实际 "+jstr(m, "want")+"）")
	rmWP("primary/grade4/volume1/wallpaper.webp")
	rmTree("primary/grade4") // 让出版社目录回到只有一个（pep），推荐路径才会显示出版社层
	writeWP("primary/pep/grade4/wallpaper.webp", realWP)
	m = lookup("primary", 4, 1)
	check(jstr(m, "name") == "primary/pep/grade4/wallpaper.webp",
		"首页命中 grade4 目录下的 wallpaper.webp")
	check(jstr(m, "want") == "primary/pep/grade4/wallpaper.webp",
		"首页推荐路径为 …/grade4/wallpaper.webp（不带 volume）")
	writeWP("primary/pep/grade4/volume2/wallpaper.webp", realWP)
	m = lookup("primary", 4, 2)
	check(jstr(m, "name") == "primary/pep/grade4/wallpaper.webp",
		"四年级下册首页用同一张 grade4/wallpaper.webp（上下册共用，不再区分册别）")
	_, body = do("GET", "/study", nil, ck)
	check(strings.Contains(body, `data-wallpaper="primary/pep/grade4/wallpaper.webp"`),
		"学习主页注入年级通用壁纸")
	check(strings.Contains(body, "点击关闭背景壁纸 · primary/pep/grade4 · 上下册共用"),
		"开关行的悬停提示里标注「上下册共用」，一眼看出首页图不分上下册")
	check(!strings.Contains(body, ">primary/pep/grade4 · 上下册共用<"),
		"开关行不再显示命中目录那行副标题（面板只留「背景壁纸已开启」一行）")
	m = lookup("primary", 5, 1)
	check(m["matched"] == false, "年级之间不会串号（五年级上册拿不到四年级的图）")
	// 年级图缺失 → 回退册别图：只放了册别图的旧部署不会突然没有背景。
	rmWP("primary/pep/grade4/wallpaper.webp")
	m = lookup("primary", 4, 2)
	check(jstr(m, "name") == "primary/pep/grade4/volume2/wallpaper.webp",
		"年级图缺失时首页回退到册别图（上下册各自回退到自己的册别图）")
	rmWP("primary/pep/grade4/volume2/wallpaper.webp")
	writeWP(nested, realWP)

	// F. 上册 / 下册分开匹配，扩展名也认。
	writeWP("primary/pep/grade4/volume2/wallpaper.png", realWP)
	m = lookup("primary", 4, 2)
	check(jstr(m, "name") == "primary/pep/grade4/volume2/wallpaper.png",
		"四年级下册匹配 primary/pep/grade4/volume2/wallpaper.png（.png 同样支持）")
	m = lookup("primary", 4, 1)
	check(jstr(m, "name") == nested, "上册仍匹配自己的图，册别互不干扰")

	// G. 老式平铺写法的五级回退链保持兼容。
	rmWP(nested)
	writeWP("primary-v1.webp", realWP)
	m = lookup("primary", 6, 1)
	check(jstr(m, "name") == "primary-v1.webp", "六年级上册没有专属图时用学段通用图兜底")
	writeWP("g6-v1.webp", realWP)
	m = lookup("primary", 6, 1)
	check(jstr(m, "name") == "g6-v1.webp", "更具体的年级图优先，不被学段通用图抢走")
	rmWP("g6-v1.webp")
	rmWP("primary-v1.webp")
	writeWP("v1.webp", realWP)
	m = lookup("middle", 2, 1)
	check(jstr(m, "name") == "v1.webp", "跨学段时回落到全年级通用图 v1.webp")
	rmWP("v1.webp")
	writeWP("default.webp", realWP)
	m = lookup("primary", 3, 2)
	check(jstr(m, "name") == "default.webp", "都没有时用 default.webp 兜底")
	rmWP("default.webp")
	rmWP("g4-v1.webp")

	// G2. 高考复习专题（content 里 grade{N}/review/ 的课 → volume=9）与高中 h{N} 简写命名。
	writeWP("high/pep/grade3/review/h3-chinese.webp", realWP)
	m = lookupSub("high", 3, 9, "chinese")
	check(jstr(m, "name") == "high/pep/grade3/review/h3-chinese.webp",
		"高考复习语文名匹配 review 目录里的 h3-chinese.webp")
	check(jstr(m, "want") == "high/pep/grade3/review/h3-chinese.webp",
		"高考复习学科图的推荐路径为 …/grade3/review/h3-chinese.webp")
	check(strings.Contains(jstr(m, "label"), "高考复习"), "复习册别的可读描述含「高考复习」")
	m = lookupSub("high", 3, 9, "politics")
	check(jstr(m, "name") == "", "review 目录里没放的学科不串用别的学科图")
	writeWP("high/pep/grade3/wallpaper.webp", realWP)
	m = lookupSub("high", 3, 9, "politics")
	check(jstr(m, "name") == "high/pep/grade3/wallpaper.webp",
		"复习学科图缺失时回退到年级通用图 grade3/wallpaper.webp")
	m = lookup("high", 3, 9)
	check(jstr(m, "name") == "high/pep/grade3/wallpaper.webp", "复习册别（无学科）也用年级通用图")
	rmWP("high/pep/grade3/wallpaper.webp")
	rmTree("high")
	writeWP("high/pep/grade1/volume1/h1-v1-chinese.webp", realWP)
	m = lookupSub("high", 1, 1, "chinese")
	check(jstr(m, "name") == "high/pep/grade1/volume1/h1-v1-chinese.webp",
		"高中学科图支持 h{N} 简写：h1-v1-chinese.webp")
	rmTree("high")

	// H. 开关：关掉后能再打开（回归：曾经关掉后开关行就消失、回不来了），且持久化到 users.wallpaper。
	writeWP(nested, realWP)
	_, body = do("GET", "/study", nil, ck)
	check(strings.Contains(body, "/wallpaper/toggle?on=0"),
		"壁纸开着时，设置面板里的开关指向「关闭」（on=0）")
	w, _ = do("GET", "/wallpaper/toggle?on=0&back=%2Fstudy", nil, ck)
	check(w.Code == 303 && w.Header().Get("Location") == "/study", "关闭壁纸后返回原页面")
	_, body = do("GET", "/study", nil, ck)
	check(!strings.Contains(body, "wp-layer"), "关闭后学习主页不再输出壁纸层")
	// 回归重点：关掉后 Wallpaper（图片 URL）为空，但开关行必须还在，且指向「开启」（on=1）。
	check(!strings.Contains(body, "data-wallpaper"), "关闭后 html 标签上也不再带 data-wallpaper")
	check(strings.Contains(body, "/wallpaper/toggle?on=1"),
		"关闭后设置面板里仍有开关，且指向「开启」（on=1）——关掉还能再打开")
	check(strings.Contains(body, ">背景壁纸已关闭<"), "关闭后开关文案显示「背景壁纸已关闭」")
	check(strings.Contains(body, "点击开启背景壁纸 · primary/pep/grade4/volume1"),
		"关闭后悬停提示里仍带命中的壁纸目录（而不是退化成「未匹配」）")
	check(!strings.Contains(body, "背景壁纸未匹配"), "关闭 ≠ 未匹配：不显示「未匹配」那一行")
	if uu, err2 := g.ByUsername("guoyifan"); err2 == nil {
		check(uu.Wallpaper == "off", "壁纸开关已写入 users.wallpaper")
	}
	_, _ = do("GET", "/wallpaper/toggle?on=1&back=%2Fstudy", nil, ck)
	_, body = do("GET", "/study", nil, ck)
	check(strings.Contains(body, "wp-layer"), "重新打开后壁纸恢复")
	check(strings.Contains(body, ">背景壁纸已开启<") && strings.Contains(body, "/wallpaper/toggle?on=0"),
		"重新打开后开关文案与方向都回到「已开启 → 点击关闭」")
	w, _ = do("GET", "/wallpaper/toggle?on=0&back=https%3A%2F%2Fevil.example", nil, ck)
	check(w.Code == 303 && w.Header().Get("Location") == "/study", "壁纸开关同样拒绝站外 back 跳转")
	_, _ = do("GET", "/wallpaper/toggle?on=1&back=%2Fstudy", nil, ck)

	// H2. 未登录点开关：跳登录页，不能 500（开关现在挂在需要登录的路由组里）。
	w, _ = do("GET", "/wallpaper/toggle?on=0&back=%2Fstudy", nil, "")
	check(w.Code == 303 && w.Header().Get("Location") == "/login", "未登录访问壁纸开关跳登录页（不是 500）")
	writeWP(nested, realWP)

	// H3. 一张图都没有时：面板显示「未匹配」的静态行（没有点了没反应的开关），
	//     并给出建议放置路径，跟新规则（首页到年级层）一致。
	rmWP(nested)
	_, body = do("GET", "/study", nil, ck)
	check(strings.Contains(body, "背景壁纸未匹配"), "没有可用壁纸时显示「未匹配」静态行")
	check(!strings.Contains(body, "/wallpaper/toggle"), "没有可用壁纸时不给点了没反应的开关")
	check(strings.Contains(body, `title="建议放置：wallpapers/primary/pep/grade4/wallpaper.webp"`),
		"未匹配行给出建议放置路径（首页图在年级层）")
	writeWP(nested, realWP)

	// I. 非法 / 越权访问一律 404。
	writeWP("primary/pep/grade4/volume1/notes.txt", realWP)
	w, _ = do("GET", "/wallpapers/global.db", nil, "")
	check(w.Code == 404, "不在壁纸目录里的文件名一律 404")
	w, _ = do("GET", "/wallpapers/%2E%2E", nil, "")
	check(w.Code == 404, "路径穿越尝试被拒绝")
	w, _ = do("GET", "/wallpapers/primary/pep/grade4/volume1/%2E%2E%2F%2E%2E%2F%2E%2E%2Fglobal.db", nil, "")
	check(w.Code == 404, "多级路径里的穿越尝试同样被拒绝")
	w, _ = do("GET", "/wallpapers/primary/pep/grade4/volume1/notes.txt", nil, "")
	check(w.Code == 404, "目录里真正存在的非图片文件也不会被提供")
	w, _ = do("GET", "/wallpapers/v9.webp", nil, "")
	check(w.Code == 404, "不存在的壁纸返回 404")

	// J. 注册页的壁纸预览骨架与提示。
	_, body = do("GET", "/register", nil, "")
	check(strings.Contains(body, `id="wp-card"`) && strings.Contains(body, `id="wp-thumb"`), "注册页含壁纸预览卡")
	check(strings.Contains(body, "/api/wallpaper"), "注册页预览会向后端查询匹配结果")
	check(strings.Contains(body, "wallpapers/"), "注册页提示壁纸该放在哪个目录")
	check(strings.Contains(body, "grade' + gradeNo() + '/wallpaper.webp'"),
		"注册页本地兜底推荐路径为年级层 …/gradeN/wallpaper.webp")

	// K. 设置面板里的壁纸开关入口：这一行只留「背景壁纸已开启」，命中位置挪进悬停提示。
	_, body = do("GET", "/study", nil, ck)
	check(strings.Contains(body, "/wallpaper/toggle"), "设置面板含背景壁纸开关")
	check(strings.Contains(body, "背景壁纸"), "开关文字说明为「背景壁纸」")
	check(strings.Contains(body, "点击关闭背景壁纸 · primary/pep/grade4/volume1"),
		"命中位置放在悬停提示里（鼠标悬停即知是哪一册）")
	check(!strings.Contains(body, ">primary/pep/grade4/volume1<"),
		"开关行不再单独占一行显示命中目录（面板只留「背景壁纸已开启」）")
	check(strings.Contains(body, `class="sw is-on"`), "壁纸开着时开关显示为打开态")

	// L. 回归锁：.topbar nav a{color:#fff}（0,1,2）会把设置面板里的链接一起染白，
	//    面板是浅色底，不拉回来就是白底白字、看着像面板是空的。
	check(strings.Contains(css, ".topbar nav .setpanel a{color:var(--ink)"),
		"设置面板文字颜色已显式拉回主题变量（防止白底白字）")
	check(strings.Contains(css, ".topbar nav .tnav.is-on"),
		"顶栏导航项有当前分区高亮样式")

	// M. 学科壁纸：进入某学科（课程页 / 在线自测页）时优先匹配学科图，
	//    缺失时逐级回退：学科图 → 册别通用图 → 全局兜底。
	fmt.Println("\n[12] 学科壁纸（自测页按学科匹配，缺失逐级回退）")

	var cnLesson, mathLesson *textbook.Lesson
	for _, k := range keys {
		l := tree.Lessons[k]
		if l == nil || textbook.NormalizeStage(l.Stage) != textbook.StagePrimary || l.Grade != 4 || l.Volume != 1 {
			continue
		}
		if l.Subject == "chinese" && cnLesson == nil {
			cnLesson = l
		}
		if l.Subject == "math" && mathLesson == nil {
			mathLesson = l
		}
	}
	if cnLesson == nil || mathLesson == nil {
		fmt.Println("  · 提示：内容树缺少四年级上册语文 / 数学，跳过学科壁纸用例")
	} else {
		const cnWP = "primary/pep/grade4/volume1/g4-v1-chinese.webp"
		const mathWP = "primary/pep/grade4/volume1/g4-v1-math.webp"

		// 只放册别通用图时：首页回退到它，自测页本来就用它。
		writeWP(nested, realWP)
		_, body = do("GET", "/study", nil, ck)
		check(strings.Contains(body, `data-wallpaper="`+nested+`"`),
			"年级图缺失时学习主页回退到册别通用图 wallpaper.webp")
		_, body = do("GET", "/quiz?key="+url.QueryEscape(cnLesson.Key), nil, ck)
		check(strings.Contains(body, `data-wallpaper="`+nested+`"`), "没有学科图时自测页回退到册别通用图")

		// 自测页比首页更精确：页面自带册别信息时，册别图优先于首页的年级通用图。
		writeWP("primary/pep/grade4/wallpaper.webp", realWP)
		_, body = do("GET", "/quiz?key="+url.QueryEscape(cnLesson.Key), nil, ck)
		check(strings.Contains(body, `data-wallpaper="`+nested+`"`),
			"自测页仍优先册别图，不会被首页的年级通用图顶掉")
		rmWP("primary/pep/grade4/wallpaper.webp")

		writeWP(cnWP, realWP)
		writeWP(mathWP, realWP)

		// 学科图只在对应学科页面生效。
		w, body = do("GET", "/quiz?key="+url.QueryEscape(cnLesson.Key), nil, ck)
		check(w.Code == 200 && strings.Contains(body, "在线自测"), "四年级上册语文自测页可打开")
		check(strings.Contains(body, `data-wallpaper="`+cnWP+`"`), "语文自测页自动匹配 g4-v1-chinese.webp")
		check(strings.Contains(body, `<img class="wp-layer" src="/wallpapers/`+cnWP+`"`),
			"语文自测页渲染出学科壁纸层")
		check(strings.Contains(body, "语文 · primary/pep/grade4/volume1"),
			"设置面板显示「学科 · 册别目录」（一眼看出是哪一册哪个学科）")
		_, body = do("GET", "/lesson?key="+url.QueryEscape(cnLesson.Key), nil, ck)
		check(strings.Contains(body, `data-wallpaper="`+cnWP+`"`), "课程页同样按学科匹配壁纸")
		_, body = do("GET", "/quiz?key="+url.QueryEscape(mathLesson.Key), nil, ck)
		check(strings.Contains(body, `data-wallpaper="`+mathWP+`"`), "数学自测页自动匹配 g4-v1-math.webp")
		check(!strings.Contains(body, "g4-v1-chinese"), "数学页面不会串到语文的壁纸")

		// 学科图缺失 → 册别通用图；都缺失 → 全局兜底。
		rmWP(cnWP)
		_, body = do("GET", "/quiz?key="+url.QueryEscape(cnLesson.Key), nil, ck)
		check(strings.Contains(body, `data-wallpaper="`+nested+`"`),
			"学科图缺失时回退到册别通用图 wallpaper.webp")
		rmWP(nested)
		writeWP("default.webp", realWP)
		_, body = do("GET", "/quiz?key="+url.QueryEscape(cnLesson.Key), nil, ck)
		check(strings.Contains(body, `data-wallpaper="default.webp"`),
			"册别通用图也缺失时走全局兜底 default.webp")
		rmWP("default.webp")
		writeWP(nested, realWP)
		writeWP(cnWP, realWP)

		// 学科名合法但该学科没有图 → 不误用别的学科。
		m = lookupSub("primary", 4, 1, "english")
		check(jstr(m, "name") == nested, "英语没有专属图时回退到册别通用图，不会借用语文的图")
		m = lookupSub("primary", 4, 1, "chinese")
		check(jstr(m, "name") == cnWP, "/api/wallpaper?subject=chinese 命中语文学科图")
		check(strings.HasSuffix(jstr(m, "want"), "grade4/volume1/g4-v1-chinese.webp"),
			"带学科时推荐路径为 …/grade4/volume1/g4-v1-chinese.webp")
		check(jstr(m, "subject") == "chinese", "响应里回显 subject")
		// 四年级下册没放语文学科图 → 应回退到下册自己的通用图，不串到上册。
		m = lookupSub("primary", 4, 2, "chinese")
		check(jstr(m, "name") == "primary/pep/grade4/volume2/wallpaper.png",
			"下册语文没有专属图时用下册通用图，不串用上册的学科图")
		m = lookupSub("primary", 5, 1, "chinese")
		check(m["matched"] == false, "别的年级不会串用四年级的学科图")

		// 学科图优先于册别通用图，哪怕学科图放在更宽泛的目录层。
		rmWP(cnWP)
		writeWP("primary/pep/grade4/g4-v1-chinese.webp", realWP)
		m = lookupSub("primary", 4, 1, "chinese")
		check(jstr(m, "name") == "primary/pep/grade4/g4-v1-chinese.webp",
			"学科图放在「年级」层也优先于「册别」层的通用图")
		rmWP("primary/pep/grade4/g4-v1-chinese.webp")
		// 老式平铺的学科名（g4-v1-chinese.webp 放根目录）同样兼容。
		writeWP("g4-v1-chinese.webp", realWP)
		m = lookupSub("primary", 4, 1, "chinese")
		check(jstr(m, "name") == "g4-v1-chinese.webp",
			"学科图优先于册别通用图，平铺的 g4-v1-chinese.webp 也在 wallpaper.webp 之前")
		// 但裸学科名不进根目录，避免「全局语文图」这种歧义写法。
		rmWP("g4-v1-chinese.webp")
		writeWP("chinese.webp", realWP)
		m = lookupSub("primary", 4, 1, "chinese")
		check(jstr(m, "name") == nested, "根目录的裸学科名 chinese.webp 不被采纳（全局兜底只认 default）")
		rmWP("chinese.webp")

		// 非法学科名不会拼出奇怪的路径，行为等同于不带学科。
		m = lookupSub("primary", 4, 1, "..%2F..%2Fetc")
		check(jstr(m, "subject") == "" && jstr(m, "name") == nested, "非法学科名被忽略，退化为册别匹配")

		rmWP(mathWP)
	}


	// ---- 官方教材模块（/textbook）----
	fmt.Println("\n[G] 官方教材模块：教材库、详情页、图集分发与越权防护")

	// 未登录一律跳登录
	tbNoAuth, _ := do("GET", "/textbook", nil, "")
	check(tbNoAuth.Code == 303, fmt.Sprintf("未登录访问 /textbook 跳登录页（得到 %d）", tbNoAuth.Code))

	// 教材库页：全学段全年级全学科
	lw, lbody := do("GET", "/textbook", nil, ck)
	check(lw.Code == 200, fmt.Sprintf("GET /textbook 教材库 -> %d", lw.Code))
	check(strings.Contains(lbody, "教材库"), "教材库页渲染标题")
	check(strings.Contains(lbody, "tb-lib-grid") && strings.Contains(lbody, "tb-lb"), "教材库页渲染教材卡片网格")
	check(strings.Contains(lbody, `class="tb-chip is-on"`), "教材库页筛选条有选中态")
	check(!strings.Contains(lbody, "tb-arrow-prev"), "教材库页不渲染阅读器（阅读器只在详情页）")

	// 筛选：初中 + 数学，卡片网格里不该再出现小学 / 语文教材。
	// 只切 tb-lib-grid 区块——学段筛选 chip 本身就写着「小学」，整页搜索会误判。
	fw, fbody := do("GET", "/textbook?stage=middle&subject=math", nil, ck)
	check(fw.Code == 200, fmt.Sprintf("GET /textbook?stage=middle&subject=math -> %d", fw.Code))
	fLib := sliceTBLib(fbody)
	check(fLib != "", "教材库页可正确定位卡片网格区块")
	check(!strings.Contains(fLib, "小学"), "按学段筛选后卡片网格不再出现小学教材")
	check(!strings.Contains(fLib, "语文"), "按学科筛选后卡片网格不再出现语文教材")
	check(strings.Contains(fLib, "数学"), "筛选后仍能看到目标学科教材")

	// 非法学段 / 年级参数要被忽略，不能进到查询里
	sw, _ := do("GET", "/textbook?stage=../../etc&grade=abc", nil, ck)
	check(sw.Code == 200, "非法学段/年级参数被忽略，页面仍 200")

	// 未登记的 key 一律 404，不能悄悄落到某一本书上
	for _, bad := range []string{"primary-chinese-g1-v1-x", "no-such-book", "PRIMARY-CHINESE-G1-V1"} {
		bw, _ := do("GET", "/textbook?key="+bad, nil, ck)
		check(bw.Code == 404, fmt.Sprintf("未登记 key %s -> %d 期望 404", bad, bw.Code))
	}

	// 详情页（小学语文一年级上册，key 来自清单）
	const tbKey = "primary-chinese-g1-v1"
	tbPage, tbBody := do("GET", "/textbook?key="+tbKey, nil, ck)
	check(tbPage.Code == 200, fmt.Sprintf("GET /textbook?key=%s -> %d", tbKey, tbPage.Code))
	check(strings.Contains(tbBody, "语文"), "详情页渲染书名")
	check(strings.Contains(tbBody, "教材介绍"), "详情页含教材介绍区块")
	check(strings.Contains(tbBody, "目录"), "详情页含目录区块")

	// 教材介绍与目录补全：介绍要真出内容，目录容器要带懒加载所需属性
	check(strings.Contains(tbBody, `class="tb-intro"`), "教材介绍有正文内容")
	check(strings.Contains(tbBody, `id="tb-toc"`), "目录容器存在")
	check(strings.Contains(tbBody, `data-src="/textbook/toc?key=`),
		"目录容器带懒加载数据源")
	check(strings.Contains(tbBody, `data-key="`), "目录容器带教材 key")

	// 目录接口：已登记 key 返回 200 + 结构化单元；非法 key 与缺 key 分别 404/400，
	// 不能让这个接口变成任意 key 的探测入口。
	tocResp, tocBody := do("GET", "/textbook/toc?key="+tbKey, nil, ck)
	check(tocResp.Code == 200, "目录接口对已登记教材返回 200")
	check(strings.Contains(tocBody, `"units"`), "目录接口返回 units 字段")
	check(strings.Contains(tocBody, `"page"`), "目录条目含页码字段")
	badToc, _ := do("GET", "/textbook/toc?key=not-a-real-key", nil, ck)
	check(badToc.Code == 404, "目录接口对未登记 key -> 404")
	noKey, _ := do("GET", "/textbook/toc", nil, ck)
	check(noKey.Code == 400, "目录接口缺 key -> 400")

	// 悬浮翻页键：左右各一个，且必须排在 tb-stage 内、图片之后（保证浮在上层）
	check(strings.Contains(tbBody, `id="tb-arrow-prev"`), "阅读区含左侧悬浮上一页按钮")
	check(strings.Contains(tbBody, `id="tb-arrow-next"`), "阅读区含右侧悬浮下一页按钮")
	si := strings.Index(tbBody, `id="tb-stage"`)
	li := strings.Index(tbBody, `id="tb-loading"`)
	pi := strings.Index(tbBody, `id="tb-arrow-prev"`)
	ni := strings.Index(tbBody, `id="tb-arrow-next"`)
	check(si >= 0 && li > si && pi > li && ni > pi, "两个悬浮翻页键位于 tb-stage 内且排在图与提示层之后")
	check(strings.Contains(tbBody, "arrPrev") && strings.Contains(tbBody, "updateNav"), "翻页键接入现有翻页方法与边界置灰逻辑")
	check(strings.Contains(tbBody, `id="tb-input"`), "详情页含页码输入框")

	if tbAssets != "" {
		check(strings.Contains(tbBody, "tb-reader"), "图集可用时渲染阅读器")
		check(!strings.Contains(tbBody, "图集未生成"), "图集可用时不出现降级提示")

		// 图集分发：封面 / 低清都应 200，且带一年强缓存（二次打开零请求）
		for _, name := range []string{"cover.webp", "lo/p001.webp"} {
			aw, _ := do("GET", "/textbook/asset/"+tbKey+"/"+name, nil, ck)
			check(aw.Code == 200, fmt.Sprintf("图集 %s -> %d", name, aw.Code))
			cc := aw.Header().Get("Cache-Control")
			check(strings.Contains(cc, "immutable"), fmt.Sprintf("图集 %s 带强缓存头（%s）", name, cc))
		}

		// 目录跳转：带 p 参数时起始页跟着走
		tw, tbody := do("GET", "/textbook?key="+tbKey+"&p=59", nil, ck)
		check(tw.Code == 200 && strings.Contains(tbody, `value="59"`), "目录跳转参数 p=59 生效")

		// 越权与非法路径：一律 404，不能读到图集目录之外的任何文件
		for _, bad := range []string{
			"/textbook/asset/" + tbKey + "/../../go.mod",
			"/textbook/asset/" + tbKey + "/meta.json", // meta 不在白名单内，不对外暴露
			"/textbook/asset/not-a-key/cover.webp",
			"/textbook/asset/" + tbKey + "/hi/p999.webp",
		} {
			bw, _ := do("GET", bad, nil, ck)
			check(bw.Code == 404, fmt.Sprintf("越权路径 %s -> %d 期望 404", bad, bw.Code))
		}

		// 主页封面墙：只给「当前年级 + 当前学期」的教材（本次请求 volume=1 即上册），
		// 不跨年级、不跨学期、不铺全库
		pw, pbody := do("GET", "/study?grade=4&volume=1", nil, ck+"; tbp_"+tbKey+"=12")
		check(pw.Code == 200, "带进度 cookie 访问学习主页正常")
		check(strings.Contains(pbody, "官方教材"), "学习主页出现「官方教材」封面墙")

		// 页脚仓库链接：真实 HTTP 渲染验证，不只靠模板单测。
		// footer 是 9 个页面共用的 partial，任一页渲染出来都应带这个链接。
		check(strings.Contains(pbody, `href="https://github.com/meimolihan/StudyBuddy"`),
			"页脚「StudyBuddy」链到 GitHub 仓库")
		check(strings.Contains(pbody, `rel="noopener noreferrer"`),
			"页脚外链带 noopener noreferrer")
		check(strings.Contains(pbody, ">StudyBuddy</a> · 每个学生"),
			"页脚链接只包住项目名，说明文案保持在链接外")
		check(strings.Contains(pbody, `href="/textbook`), "顶栏出现教材入口")
		check(!strings.Contains(pbody, `src="/avatar/me"`), "未上传头像时不下发头像请求")
		// 主页是当前年级 + 当前学期视图，卡片里只该出现该年级该学期的教材。
		// 注意：必须只切 tb-home 区块再断言——整页 HTML 里「一年级上册」是存在的，
		// 但它来自顶栏「切换年级」菜单（grade-switcher），与教材卡无关。
		tbHome := sliceTBHome(pbody)
		check(strings.Contains(tbHome, "四年级"), "封面墙标注当前年级（四年级）")
		check(strings.Contains(tbHome, "上册"), "封面墙标注当前学期（上册）")
		check(!strings.Contains(tbHome, "上册 / 下册"), "封面墙不再同时标注上下册")
		check(!strings.Contains(tbHome, "一年级上册"), "封面墙不混入其它年级教材")
		// 学期过滤的关键回归：volume=1 时下册教材（下册封面 alt 里的「下册」）不得出现。
		// 封面名小字形如「语文 · 上册」，只要出现「· 下册」就是漏了另一学期。
		check(!strings.Contains(tbHome, "· 下册"), "上册视图不混入下册教材")
		// 只渲染封面卡，不留旧横版详情卡的痕迹
		check(strings.Contains(tbHome, `class="tb-cover-card"`), "封面墙渲染封面卡片")
		check(strings.Contains(tbHome, `href="/textbook?key=`), "封面卡链接指向教材详情页")
		for _, dead := range []string{"tb-book-desc", "tb-book-foot", "tb-home-grid"} {
			check(!strings.Contains(tbHome, dead), "封面墙不再渲染旧横版教材卡: "+dead)
		}
		// 回归护栏：切出的区块不能为空，否则上面的断言会假绿
		check(len(tbHome) > 200, "封面墙区块可被正确定位")
	} else {
		// 图集缺失时详情页降级为「下载原书 PDF」，不能白屏也不能 500
		check(strings.Contains(tbBody, "分页图集还没生成"), "图集缺失时详情页给出降级说明")
		check(strings.Contains(tbBody, "/textbook/raw?key="), "图集缺失时提供原书 PDF 入口")
		rr, _ := do("GET", "/textbook/raw?key=../../go.mod", nil, ck)
		check(rr.Code == 404, "原书 PDF 越权路径 -> 404")
	}

	// 清理测试壁纸，避免影响真实使用（BaseDir 已指向临时目录，真实 wallpapers/ 未被触碰）。
	_ = os.RemoveAll(wpDir)

	fmt.Println("\n[13] 小功能增强：教材书签 / 笔记 / 只看错题 / 收藏 / 计时 / 字体档位")

	// 学习主页：新增控件与容器都在 HTML 里（具体内容由前端按 localStorage 填）
	sp, sbody := do("GET", "/study", nil, ck)
	check(sp.Code == 200, fmt.Sprintf("GET /study -> %d", sp.Code))
	// 「只看错题」已从 checkbox+label 改为 <button>（教材导航区要三元素同行）。
	// 断言随之改为查按钮本体 + 其无障碍状态载体，不能再查旧的 checkbox id。
	check(strings.Contains(sbody, `id="sb-wrong-box"`) &&
		strings.Contains(sbody, `aria-pressed="false"`) &&
		strings.Contains(sbody, `id="sb-wrong-n"`),
		"学习主页含「只看错题」按钮（button + aria-pressed + 计数）")
	check(strings.Contains(sbody, `data-wrong="`), "课程列表项带错题数 data-wrong")
	check(strings.Contains(sbody, `id="tb-resume"`), "学习主页含「继续阅读 / 书签」卡容器")
	check(strings.Contains(sbody, `href="/favorites"`) && strings.Contains(sbody, `id="sb-fav-n"`),
		"学习主页含「我的收藏」入口")
	check(strings.Contains(sbody, `id="wip-mask"`), "学习主页含「火速开发中」弹窗骨架")
	check(strings.Contains(sbody, `class="fontbtn"`), "设置面板含字体档位按钮")


	// 教材详情页：阅读器就绪时才断言书签 / 笔记 / 快速跳转
	if strings.Contains(tbBody, `id="tb-reader"`) {
		check(strings.Contains(tbBody, `id="tb-markpick"`), "教材详情页含书签下拉")
		check(strings.Contains(tbBody, `id="tb-note"`) && strings.Contains(tbBody, `id="tb-note-t"`),
			"教材详情页含单页笔记面板")
		check(strings.Contains(tbBody, `id="tb-go"`), "阅读器含「前往」快速跳转按钮")
		check(strings.Contains(tbBody, `data-catlabel="`), "阅读器带年级/学科/学期分类标签（书签分类用）")
		check(strings.Contains(tbBody, "sb_tbmk") && strings.Contains(tbBody, "sb_tbnote"),
			"书签与笔记写本机存储（sb_tbmk / sb_tbnote）")
	}

	// 刷题页：计时器 + 收藏 + 耗时字段
	_, qbody := do("GET", "/quiz?key="+url.QueryEscape(sampleKey), nil, ck)
	check(strings.Contains(qbody, `id="q-timer"`), "刷题页含答题计时器")
	check(strings.Contains(qbody, `id="q-timer-toggle"`), "计时器可关闭（含隐藏开关）")
	check(strings.Contains(qbody, `name="elapsed"`), "刷题页带耗时隐藏字段")
	check(strings.Count(qbody, `class="q-fav"`) == 10, "刷题页每题都有收藏按钮")
	check(strings.Contains(qbody, `data-stem="`), "题目带 data-stem（收藏按题干去重）")

	// 收藏题库页：登录可进，未登录跳登录
	fv, fvbody := do("GET", "/favorites", nil, ck)
	check(fv.Code == 200 && strings.Contains(fvbody, `id="fav-body"`),
		fmt.Sprintf("GET /favorites -> %d 且含列表容器", fv.Code))
	fvNA, _ := do("GET", "/favorites", nil, "")
	check(fvNA.Code == 303, fmt.Sprintf("未登录访问 /favorites 跳登录（得到 %d）", fvNA.Code))

	// 耗时链路：带 elapsed 提交 → 存进 state → 课程页显示「上次用时」
	form2 := url.Values{"key": {sampleKey}, "elapsed": {"95"}}
	for i := 0; i < 10; i++ {
		form2.Set(fmt.Sprintf("q%d", i), "0")
	}
	wElapsed, _ := do("POST", "/quiz/submit", form2, ck)
	check(wElapsed.Code == 303, "带耗时的提交正常判分")
	_, lessonBody := do("GET", "/lesson?key="+url.QueryEscape(sampleKey), nil, ck)
	check(strings.Contains(lessonBody, "上次用时 1 分 35 秒"), "课程页显示上次用时（mmss 格式化）")

	/* 错题聚合：这次「全选 A」的提交刚写进 answers，聚合后该课应是非零。
	   两个坑都在断言里堵住：
	     ① 必须切到 sampleKey 所在的年级册别看 —— 学习主页默认渲染学生档案的
	        年级（四年级），那里根本不显示 sampleKey（二年级）；
	     ② 必须在提交**之后**查 —— [4] 归档段把前三份试卷连同作答明细全删了，
	        放在前面查到的是一张空表。 */
	_, sbody2 := do("GET", "/study?grade=2&volume=1", nil, ck)
	wrongHit := false
	segs := strings.Split(sbody2, `data-wrong="`)
	for i := 1; i < len(segs); i++ {
		if j := strings.Index(segs[i], `"`); j > 0 && segs[i][:j] != "0" {
			wrongHit = true
			break
		}
	}
	check(wrongHit, "错题已按课程聚合到列表（存在 data-wrong 非零的课程）")

	// 字体档位：变量与换算规则都要在 CSS 里（缺任一档位按钮就只是个摆设）
	_, cssBody := do("GET", "/static/style.css", nil, "")
	check(strings.Contains(cssBody, `html[data-font="sm"]{--sb-fz:.88}`), "CSS 含「小」档位变量")
	check(strings.Contains(cssBody, `html[data-font="lg"]{--sb-fz:1.15}`), "CSS 含「大」档位变量")
	check(strings.Contains(cssBody, "font-size:calc(15px * var(--sb-fz,1))"),
		"CSS 按 --sb-fz 换算字号（px 写死处也跟着缩放）")

	// 游戏宿主页：战绩条（一年级游戏才有；列表页取不到 key 就跳过，不算失败）
	gw, gbody := do("GET", "/games?grade=1&volume=1", nil, ck)
	if gw.Code == 200 {
		if i := strings.Index(gbody, `href="/game?key=`); i >= 0 {
			rest := gbody[i+len(`href="/game?key=`):]
			if j := strings.Index(rest, `"`); j > 0 {
				gk := rest[:j]
				gp, gpbody := do("GET", "/game?key="+gk, nil, ck)
				check(gp.Code == 200 && strings.Contains(gpbody, `id="gm-score"`),
					"游戏宿主页含答对/答错战绩条")
				check(strings.Contains(gpbody, `data-key="`), "宿主页带游戏 key（战绩按游戏分别累计）")
			}
		} else {
			fmt.Println("  · 提示：一年级上册暂无游戏，跳过游戏战绩条用例")
		}
	}

	fmt.Println("\n---------------------------------------------")
	if fail == 0 {
		fmt.Println("端到端测试全部通过 ✅")
	} else {
		fmt.Printf("存在 %d 项失败 ❌\n", fail)
		os.Exit(1)
	}
	_ = http.StatusOK
}
