// Package textbook 负责扫描教材内容目录树并解析课程 HTML 中内置的题库。
//
// 标准目录结构（路径本身即元数据，新增内容只需按规则放文件，无需改代码）：
//
//	content/<stage>/<publisher>/grade<N>/volume<N>/<subject>/<NN-单元名>/<NN-课名>.html
//	content/primary/pep/grade4/volume1/chinese/01-自然之美/01-观潮.html
//
// 高考复习专题不带 volume 层，用 review 段顶替（展示为独立册别「高考复习」）：
//
//	content/<stage>/<publisher>/grade<N>/review/<subject>/<NN-专题名>.html
//	content/high/pep/grade3/review/math/01-函数与导数.html
//
// 层级为：学段 → 出版社 → 年级 → 册别 → 科目 → 单元 → 课。
// 目录与文件名以两位数字开头保证排序；不合规的路径自动忽略。
// 单元目录可省略（课程文件直接放在科目目录下），此时归入「未分单元」。
package textbook

import (
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"sync"
)

// Question 一道题。
type Question struct {
	Type    string   // "s" 单选 / "m" 多选 / "j" 判断题（选项为 正确 / 错误）
	Stem    string   // 题干
	Explain string   // 解析（判断题必带，选择题可缺省）
	Options []string // 选项文本（A/B/C/D 顺序；判断题为 正确 / 错误）
	Answers []string // 正确答案字母，如 ["A"] 或 ["A","B"]
	Key     string   // 去重键（取题干）
}

// AnswerIdx 返回正确答案对应的选项下标。
func (q Question) AnswerIdx() []int {
	out := make([]int, 0, len(q.Answers))
	for _, a := range q.Answers {
		if len(a) == 1 && a[0] >= 'A' && a[0] <= 'D' {
			out = append(out, int(a[0]-'A'))
		}
	}
	return out
}

// IsMulti 是否多选题。
func (q Question) IsMulti() bool { return q.Type == "m" }

// ---- 目录树节点 ----

// Lesson 一门课（一个 HTML 文件）。
type Lesson struct {
	Key       string // 唯一键：相对教材根的路径（/ 分隔）
	Stage     string // primary-school 等
	Publisher string // pep
	Grade     int    // 4
	Volume    int    // 1；高考复习专题为 VolReview
	Subject   string // chinese
	SubjectCN string // 语文
	QType     string // choose 选择题 / judge 判断题
	Review    bool   // 是否高考复习专题（grade<N>/review/ 目录下）
	Unit      string // 第一单元 自然之美
	UnitNo    int
	Title     string // 第1课 观潮
	LessonNo  int
	Path      string // 绝对路径
	BankSize  int    // 题库题数（首次解析后填充）
}

// Subject 科目节点（含其下所有课，已按单元/课序排序）。
type Subject struct {
	Key       string
	Name      string
	Lessons   []*Lesson
	Units     []*Unit
	Grade     int
	Volume    int
	Stage     string
	Publisher string
}

// Unit 单元节点（由课程文件名中的单元名聚合而来）。
type Unit struct {
	No      int
	Name    string
	Lessons []*Lesson
}

// Grade 年级节点（同一学段下的年级，如 小学 4 年级）。
type Grade struct {
	No      int
	Stage   string // primary / middle / high
	Volumes []*Volume
}

// Volume 册别节点。Name 为展示名：上册 / 下册 / 高考复习。
type Volume struct {
	No       int
	Name     string
	Subjects []*Subject
}

// VolReview 高考复习专题的虚拟册号：排在 volume1/2 之后（按 No 排序时靠最后），
// 展示为「高考复习」。目录形式为 grade<N>/review/<subject>/…（不带 volume 层）。
const VolReview = 9

// Tree 完整教材导航树。
type Tree struct {
	Root    string
	Grades  []*Grade
	Lessons map[string]*Lesson // key → Lesson
}

var subjectCN = map[string]string{
	"chinese":   "语文",
	"math":      "数学",
	"english":   "英语",
	"morallaw":  "道德与法治",
	"science":   "科学",
	"history":   "历史",
	"geography": "地理",
	"biology":   "生物",
	"physics":   "物理",
	"chemistry": "化学",
	"politics":  "思想政治",
}

var stageCN = map[string]string{
	"primary": "小学",
	"middle":  "初中",
	"high":    "高中",
	"junior":  "初中", // 新命名：初中（目录年级用 7~9）
	"senior":  "高中", // 新命名：高中
	// 旧命名兼容
	"primary-school": "小学",
	"middle-school":  "初中",
	"high-school":    "高中",
}

// QType 题型目录：choose = 选择题库，judge = 判断题库（两者互为镜像，目录树完全一致）。
const (
	QTypeChoose = "choose"
	QTypeJudge  = "judge"
)

// QTypeCN 题型展示名。
func QTypeCN(q string) string {
	switch strings.ToLower(strings.TrimSpace(q)) {
	case QTypeJudge:
		return "判断题"
	case QTypeChoose:
		return "选择题"
	}
	return "选择题"
}

var publisherCN = map[string]string{
	"pep":    "人教版",
	"review": "高考复习",
}

var (
	reGrade   = regexp.MustCompile(`grade(\d+)`)
	reVolume  = regexp.MustCompile(`volume(\d+)`)
	reUnit    = regexp.MustCompile(`第([^单]*)单元`)
	reLessonN = regexp.MustCompile(`第([0-9]+)课`)
	reLessonC = regexp.MustCompile(`第([^课]*)课`)
)

// cnNum 将中文数字（一 ~ 九十九）转为阿拉伯数字；非中文数字返回 0。
func cnNum(s string) int {
	digits := map[rune]int{
		'零': 0, '〇': 0, '一': 1, '二': 2, '两': 2, '三': 3,
		'四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
	}
	total, num := 0, 0
	for _, r := range s {
		if v, ok := digits[r]; ok {
			num = v
			continue
		}
		switch r {
		case '十':
			if num == 0 {
				num = 1
			}
			total += num * 10
			num = 0
		case '百':
			if num == 0 {
				num = 1
			}
			total += num * 100
			num = 0
		}
	}
	return total + num
}

// Scan 扫描目录树，构建导航。root 为空或不存在时返回空树（不报错，便于先启动后放教材）。
func Scan(root string) (*Tree, error) {
	t := &Tree{Root: root, Lessons: map[string]*Lesson{}}
	if root == "" {
		return t, nil
	}
	if _, err := os.Stat(root); err != nil {
		return t, nil
	}

	// stage → grade → volume → subject → lessons（按学段分组，避免不同学段的同名年级互相混入）
	byStage := map[string]map[int]map[int]map[string][]*Lesson{}

	_ = filepath.Walk(root, func(path string, info os.FileInfo, err error) error {
		if err != nil || info == nil || info.IsDir() {
			return nil
		}
		if !strings.EqualFold(filepath.Ext(path), ".html") {
			return nil
		}
		rel, err := filepath.Rel(root, path)
		if err != nil {
			return nil
		}
		parts := strings.Split(filepath.ToSlash(rel), "/")
		if len(parts) < 2 {
			return nil
		}

		l := parseLesson(parts)
		if l == nil {
			l = parseLessonLegacy(parts) // 兼容旧命名（如 pep-grade4-volume1-chinese/）
		}
		if l == nil {
			return nil // 不符合规范的目录自动忽略
		}
		l.Key = filepath.ToSlash(rel)
		l.Path = path

		st := NormalizeStage(l.Stage)
		if byStage[st] == nil {
			byStage[st] = map[int]map[int]map[string][]*Lesson{}
		}
		if byStage[st][l.Grade] == nil {
			byStage[st][l.Grade] = map[int]map[string][]*Lesson{}
		}
		if byStage[st][l.Grade][l.Volume] == nil {
			byStage[st][l.Grade][l.Volume] = map[string][]*Lesson{}
		}
		byStage[st][l.Grade][l.Volume][l.Subject] = append(byStage[st][l.Grade][l.Volume][l.Subject], l)
		t.Lessons[l.Key] = l
		return nil
	})

	stages := make([]string, 0, len(byStage))
	for st := range byStage {
		stages = append(stages, st)
	}
	sort.Slice(stages, func(i, j int) bool {
		oi, oj := StageOrder(stages[i]), StageOrder(stages[j])
		if oi != oj {
			return oi < oj
		}
		return stages[i] < stages[j]
	})

	for _, st := range stages {
		grades := make([]int, 0, len(byStage[st]))
		for g := range byStage[st] {
			grades = append(grades, g)
		}
		sort.Ints(grades)

		for _, g := range grades {
			gn := &Grade{No: g, Stage: st}
			vols := make([]int, 0, len(byStage[st][g]))
			for v := range byStage[st][g] {
				vols = append(vols, v)
			}
			sort.Ints(vols)
			for _, v := range vols {
				vn := &Volume{No: v, Name: volumeName(v)}
				subs := make([]string, 0, len(byStage[st][g][v]))
				for s := range byStage[st][g][v] {
					subs = append(subs, s)
				}
				sort.Strings(subs)
				for _, s := range subs {
					ls := byStage[st][g][v][s]
					sort.Slice(ls, func(i, j int) bool {
						if ls[i].UnitNo != ls[j].UnitNo {
							return ls[i].UnitNo < ls[j].UnitNo
						}
						if ls[i].LessonNo != ls[j].LessonNo {
							return ls[i].LessonNo < ls[j].LessonNo
						}
						return ls[i].Title < ls[j].Title
					})
					sn := &Subject{
						Key: s, Name: subjectCN[s], Lessons: ls,
						Grade: g, Volume: v,
						Stage:     ls[0].Stage,
						Publisher: ls[0].Publisher,
					}
					sn.buildUnits()
					vn.Subjects = append(vn.Subjects, sn)
				}
				gn.Volumes = append(gn.Volumes, vn)
			}
			t.Grades = append(t.Grades, gn)
		}
	}
	return t, nil
}

// parseLesson 按标准层级解析相对路径：
//
//	<stage>/<publisher>/<题型>/grade<N>/volume<N>/<subject>/[<NN-单元名>/]<NN-课名>.html
//	<stage>/<publisher>/<题型>/grade<N>/review/<subject>/[<NN-专题组>/]<NN-专题名>.html
//
// 其中 <题型> 为 choose（选择题）或 judge（判断题），两套目录互为镜像、文件名一致；
// 高考复习专题用 review 段顶替 volume<N>。层级为：
// 学段 → 出版社 → 题型 → 年级 → 册别 → 科目 → 单元 → 课。
// 不符合规范返回 nil（交由上层忽略或走兼容解析）。
func parseLesson(parts []string) *Lesson {
	// 题型层（choose / judge）：新结构必带，旧结构没有则按选择题处理。
	qtype, off := QTypeChoose, 0
	if len(parts) >= 3 {
		switch q := strings.ToLower(parts[2]); q {
		case QTypeChoose, QTypeJudge:
			qtype, off = q, 1
		}
	}
	if len(parts) < 6+off || len(parts) > 7+off {
		return nil
	}
	stage := strings.ToLower(parts[0])
	if _, ok := stageCN[stage]; !ok {
		return nil
	}
	publisher := strings.ToLower(parts[1])
	grade := gradeOf(parts[2+off])
	if grade == 0 {
		return nil
	}
	// 初中新命名用绝对年级 7~9，内部仍按学段内序号 1~3 记录（与旧 middle 一致）。
	if stage == "junior" && grade > 6 {
		grade -= 6
	}
	volume, review := 0, false
	if seg := strings.ToLower(parts[3+off]); seg == "review" {
		volume, review = VolReview, true // 高考复习专题：review 段顶替 volume<N>
	} else {
		volume = volumeOf(seg)
		if volume == 0 {
			return nil
		}
	}
	subject := strings.ToLower(parts[4+off])
	if _, ok := subjectCN[subject]; !ok {
		return nil
	}

	unitNo, unit := 0, ""
	lessonNo, title := 0, ""
	if len(parts) == 7+off {
		unitNo, unit = parseSeqName(parts[5+off])
		lessonNo, title = parseSeqName(baseName(parts[6+off]))
	} else {
		lessonNo, title = parseSeqName(baseName(parts[5+off]))
	}
	if title == "" {
		return nil
	}
	return &Lesson{
		Stage: NormalizeStage(stage), Publisher: publisher,
		Grade: grade, Volume: volume, Review: review,
		QType: qtype,
		Subject: subject, SubjectCN: subjectCN[subject],
		Unit: unit, UnitNo: unitNo,
		Title: title, LessonNo: lessonNo,
	}
}

// parseLessonLegacy 兼容解析旧式命名：
//
//	primary-school/pep/grade4/volume1/pep-grade4-volume1-chinese/四年级语文上册 · 第一单元 自然之美 · 第1课 观潮.html
//
// 逐段探测年级/册别/科目，单元与课名从文件名的「·」分隔中提取。
func parseLessonLegacy(parts []string) *Lesson {
	stage := strings.ToLower(parts[0])
	if _, ok := stageCN[stage]; !ok {
		return nil
	}
	publisher, grade, volume, subject := "", 0, 0, ""
	for _, p := range parts[:len(parts)-1] {
		low := strings.ToLower(p)
		if publisher == "" {
			if _, ok := publisherCN[low]; ok {
				publisher = low
			}
		}
		if g := gradeOf(p); g != 0 {
			grade = g
		}
		if v := volumeOf(p); v != 0 {
			volume = v
		}
		if i := strings.LastIndex(low, "-"); i >= 0 {
			if _, ok := subjectCN[low[i+1:]]; ok {
				subject = low[i+1:]
			}
		}
	}
	if grade == 0 || subject == "" {
		return nil
	}
	if volume == 0 {
		volume = 1
	}
	if publisher == "" {
		publisher = "pep"
	}
	unit, title := splitTitle(baseName(parts[len(parts)-1]))
	unitNo := 0
	if m := reUnit.FindStringSubmatch(unit); m != nil {
		unitNo = cnNum(m[1])
	}
	lessonNo := 0
	if m := reLessonN.FindStringSubmatch(title); m != nil {
		lessonNo, _ = strconv.Atoi(m[1])
	} else if m := reLessonC.FindStringSubmatch(title); m != nil {
		lessonNo = cnNum(m[1])
	}
	return &Lesson{
		Stage: stage, Publisher: publisher,
		Grade: grade, Volume: volume,
		Subject: subject, SubjectCN: subjectCN[subject],
		Unit: unit, UnitNo: unitNo,
		Title: title, LessonNo: lessonNo,
	}
}

// parseSeqName 解析「NN-名称」形式：返回序号与名称；无数字前缀时序号为 0。
func parseSeqName(s string) (int, string) {
	i := strings.Index(s, "-")
	if i < 0 {
		return 0, strings.TrimSpace(s)
	}
	if n, err := strconv.Atoi(strings.TrimSpace(s[:i])); err == nil {
		return n, strings.TrimSpace(s[i+1:])
	}
	return 0, strings.TrimSpace(s)
}

// baseName 去掉扩展名。
func baseName(p string) string { return strings.TrimSuffix(p, filepath.Ext(p)) }

func gradeOf(s string) int {
	if m := reGrade.FindStringSubmatch(strings.ToLower(s)); m != nil {
		n, _ := strconv.Atoi(m[1])
		return n
	}
	return 0
}

func volumeOf(s string) int {
	if m := reVolume.FindStringSubmatch(strings.ToLower(s)); m != nil {
		n, _ := strconv.Atoi(m[1])
		return n
	}
	return 0
}

// volumeName 册别展示名：1 → 上册，VolReview → 高考复习，其余 → 下册。
func volumeName(no int) string {
	switch no {
	case 1:
		return "上册"
	case VolReview:
		return "高考复习"
	}
	return "下册"
}

// UnitLabel 单元展示名，如「第1单元 自然之美」。
func (l Lesson) UnitLabel() string {
	if l.UnitNo <= 0 {
		return l.Unit
	}
	if l.Unit == "" {
		return fmt.Sprintf("第%d单元", l.UnitNo)
	}
	return fmt.Sprintf("第%d单元 %s", l.UnitNo, l.Unit)
}

// LessonLabel 课程展示名，如「第1课 观潮」。
func (l Lesson) LessonLabel() string {
	if l.LessonNo <= 0 {
		return l.Title
	}
	return fmt.Sprintf("第%d课 %s", l.LessonNo, l.Title)
}

// QTypeCN 本题型展示名（选择题 / 判断题）。
func (l Lesson) QTypeCN() string { return QTypeCN(l.QType) }

// IsJudge 是否为判断题课。
func (l Lesson) IsJudge() bool { return l.QType == QTypeJudge }

// TwinKey 返回同一门课在「另一题型」下的 key（choose ↔ judge 互切）。
// choose 与 judge 目录树完全镜像、文件名一致，所以只需替换路径里的题型段；
// 没有题型段（旧结构）时返回空串，表示没有镜像课。
func (l Lesson) TwinKey() string {
	k := l.Key
	if strings.Contains(k, "/"+QTypeChoose+"/") {
		return strings.Replace(k, "/"+QTypeChoose+"/", "/"+QTypeJudge+"/", 1)
	}
	if strings.Contains(k, "/"+QTypeJudge+"/") {
		return strings.Replace(k, "/"+QTypeJudge+"/", "/"+QTypeChoose+"/", 1)
	}
	return ""
}

// QTypeOfKey 从课程 key（相对路径）推断题型：
// 路径含 /choose/ 或 /judge/ 段则取之；旧结构没有题型段，按选择题处理。
// 用于给历史试卷记录（只存了 lesson_key）判断题型归属。
func QTypeOfKey(key string) string {
	k := strings.ToLower(strings.ReplaceAll(key, "\\", "/"))
	switch {
	case strings.Contains(k, "/"+QTypeJudge+"/"):
		return QTypeJudge
	case strings.Contains(k, "/"+QTypeChoose+"/"):
		return QTypeChoose
	}
	return QTypeChoose
}

// VolumeLabel 册别展示名：上册 / 下册；高考复习专题显示「高考复习」。
func (l Lesson) VolumeLabel() string {
	if l.Review {
		return "高考复习"
	}
	if l.Volume == 1 {
		return "上册"
	}
	return "下册"
}

// FullLabel 完整展示名，如「语文 第1单元 自然之美 · 第1课 观潮」。
func (l Lesson) FullLabel() string {
	if l.UnitLabel() == "" {
		return l.SubjectCN + " " + l.LessonLabel()
	}
	return l.SubjectCN + " " + l.UnitLabel() + " · " + l.LessonLabel()
}

func (s *Subject) buildUnits() {
	m := map[int]*Unit{}
	order := []int{}
	for _, l := range s.Lessons {
		u, ok := m[l.UnitNo]
		if !ok {
			u = &Unit{No: l.UnitNo, Name: l.Unit}
			m[l.UnitNo] = u
			order = append(order, l.UnitNo)
		}
		u.Lessons = append(u.Lessons, l)
	}
	sort.Ints(order)
	for _, n := range order {
		s.Units = append(s.Units, m[n])
	}
}

// LessonsOf 返回指定题型（choose / judge）的课；qt 为空时返回全部。
func (s *Subject) LessonsOf(qt string) []*Lesson {
	if qt == "" {
		return s.Lessons
	}
	out := make([]*Lesson, 0, len(s.Lessons))
	for _, l := range s.Lessons {
		if l.QType == qt {
			out = append(out, l)
		}
	}
	return out
}

// CountOf 指定题型的课数（用于导航里的「语文 · 24 课」）。
func (s *Subject) CountOf(qt string) int { return len(s.LessonsOf(qt)) }

// UnitsOf 返回按题型过滤后的单元列表，空单元自动剔除。
func (s *Subject) UnitsOf(qt string) []*Unit {
	if qt == "" {
		return s.Units
	}
	out := make([]*Unit, 0, len(s.Units))
	for _, u := range s.Units {
		ls := make([]*Lesson, 0, len(u.Lessons))
		for _, l := range u.Lessons {
			if l.QType == qt {
				ls = append(ls, l)
			}
		}
		if len(ls) == 0 {
			continue
		}
		out = append(out, &Unit{No: u.No, Name: u.Name, Lessons: ls})
	}
	return out
}

// splitTitle 从文件名解析单元名与课名，格式：「… · 第X单元 单元名 · 第X课 课名」。
func splitTitle(base string) (unit, title string) {
	parts := strings.Split(base, "·")
	for i := range parts {
		parts[i] = strings.TrimSpace(parts[i])
	}
	switch len(parts) {
	case 0:
		return "", base
	case 1:
		return "", parts[0]
	case 2:
		return parts[0], parts[1]
	default:
		return parts[1], parts[2]
	}
}

// StageCN / PublisherCN 返回中文展示名。
func StageCN(s string) string {
	if v, ok := stageCN[s]; ok {
		return v
	}
	return s
}

func PublisherCN(s string) string {
	if v, ok := publisherCN[s]; ok {
		return v
	}
	return s
}

// SubjectCN 返回学科（目录名）的中文展示名，如 chinese → 语文；未知则返回空串。
func SubjectCN(s string) string {
	return subjectCN[strings.ToLower(strings.TrimSpace(s))]
}

// ---- 题库解析 ----

var (
	bankMu    sync.Mutex
	bankCache = map[string][]Question{}
)

// Bank 返回某门课的题库（解析结果缓存，HTML 变更后重启即生效）。
func (l *Lesson) Bank() ([]Question, error) {
	bankMu.Lock()
	defer bankMu.Unlock()
	if qs, ok := bankCache[l.Key]; ok {
		return qs, nil
	}
	b, err := os.ReadFile(l.Path)
	if err != nil {
		return nil, err
	}
	qs := ParseBank(string(b))
	bankCache[l.Key] = qs
	l.BankSize = len(qs)
	return qs, nil
}

// ParseBank 从课程 HTML 中解析 `const ALL = [...]` 题库。
//
// 采用逐字符扫描而非正则：选项文本自身可能包含逗号（如英语 "Yes, I do."）与转义引号，
// 正则/字符串切分都会误拆，必须按引号边界读取。
func ParseBank(html string) []Question {
	const marker = "const ALL = ["
	i := strings.Index(html, marker)
	if i < 0 {
		return nil
	}
	i += len(marker)
	end := strings.Index(html[i:], "];")
	if end < 0 {
		return nil
	}
	body := html[i : i+end]

	var qs []Question
	pos := 0
	for {
		j := strings.Index(body[pos:], "{t:\"")
		if j < 0 {
			break
		}
		pos += j + 4
		if pos >= len(body) {
			break
		}
		typ := string(body[pos])
		// "s" 单选 / "m" 多选 / "j" 判断题（只有「正确 / 错误」两个选项，按单选处理）
		if typ != "s" && typ != "m" && typ != "j" {
			pos++
			continue
		}
		pos += 2 // 跳过类型字符与引号

		k := strings.Index(body[pos:], ",q:\"")
		if k < 0 {
			break
		}
		pos += k + 4
		stem, np := readQuoted(body, pos)
		pos = np

		k = strings.Index(body[pos:], ",o:[")
		if k < 0 {
			break
		}
		pos += k + 4
		opts, np := readArray(body, pos)
		pos = np

		k = strings.Index(body[pos:], ",a:[")
		if k < 0 {
			break
		}
		pos += k + 4
		ans, np := readArray(body, pos)
		pos = np

		// 可选字段：解析（判断题必备，写为 ,e:"…"），缺省为空。
		explain := ""
		if k = strings.Index(body[pos:], ",e:\""); k == 0 {
			pos += k + 4
			explain, pos = readQuoted(body, pos)
		}

		if len(opts) == 0 || len(ans) == 0 {
			continue
		}
		qs = append(qs, Question{
			Type:    typ,
			Stem:    stem,
			Options: opts,
			Answers: ans,
			Explain: explain,
			Key:     stem,
		})
	}
	return qs
}

// readQuoted 从 s[i] 开始读取一个 JS 双引号字符串，返回内容与结束位置。
func readQuoted(s string, i int) (string, int) {
	var b strings.Builder
	for i < len(s) {
		c := s[i]
		if c == '\\' && i+1 < len(s) {
			b.WriteByte(s[i+1])
			i += 2
			continue
		}
		if c == '"' {
			return b.String(), i + 1
		}
		b.WriteByte(c)
		i++
	}
	return b.String(), i
}

// readArray 从 s[i]（'[' 之后）开始读取字符串数组，支持元素内逗号。
func readArray(s string, i int) ([]string, int) {
	var out []string
	for i < len(s) {
		if s[i] == ']' {
			return out, i + 1
		}
		if s[i] == '"' {
			v, ni := readQuoted(s, i+1)
			out = append(out, v)
			i = ni
			continue
		}
		i++
	}
	return out, i
}
