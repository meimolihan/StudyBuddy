package web

import (
	"encoding/json"
	"strconv"
	"strings"

	"studybuddy/internal/textbook"
)

// StageOption 注册 / 建号时可选的学段；同时用于驱动前端的年级滑动选择器。
type StageOption struct {
	Key    string   `json:"key"`    // primary / middle / high
	Name   string   `json:"name"`   // 小学 / 中学 / 高中
	Hint   string   `json:"hint"`   // 年级范围提示
	Grades int      `json:"grades"` // 该学段的年级数量
	Labels []string `json:"labels"` // 每个年级的中文名（滑动刻度用）
}

// StageList 学段选项，顺序即界面展示顺序。
var StageList = buildStageList()

func buildStageList() []StageOption {
	defs := []struct {
		key, name, hint string
	}{
		{textbook.StagePrimary, "小学", "1 ~ 6 年级"},
		{textbook.StageMiddle, "中学", "七 ~ 九年级"},
		{textbook.StageHigh, "高中", "高一 ~ 高三"},
	}
	out := make([]StageOption, 0, len(defs))
	for _, d := range defs {
		n := textbook.GradeCount(d.key)
		labels := make([]string, 0, n)
		for g := 1; g <= n; g++ {
			labels = append(labels, textbook.GradeLabel(d.key, g))
		}
		out = append(out, StageOption{Key: d.key, Name: d.name, Hint: d.hint, Grades: n, Labels: labels})
	}
	return out
}

// StageJSON 学段配置的 JSON 文本，**以学段键为键**（前端按 key 直取）：
//
//	{"primary":{"key":"primary","name":"小学","grades":6,"labels":["一年级",...]}, ...}
//
// 注意：必须是对象而不是数组，否则前端 stages["middle"] 取不到值。
var StageJSON = mustStageJSON()

func mustStageJSON() string {
	m := make(map[string]StageOption, len(StageList))
	for _, o := range StageList {
		m[o.Key] = o
	}
	b, err := json.Marshal(m)
	if err != nil {
		return "{}"
	}
	return string(b)
}

// MaxClassNo 班级可选上限；0 表示不填班级。
const MaxClassNo = 12

// NormalizeStage 归一化学段；不在可选范围内的值返回 ""（视为未填写）。
func NormalizeStage(v string) string {
	s := textbook.NormalizeStage(v)
	for _, o := range StageList {
		if o.Key == s {
			return s
		}
	}
	return ""
}

// StageNameCN 学段中文名（未设置返回空串）。
func StageNameCN(key string) string {
	for _, o := range StageList {
		if o.Key == textbook.NormalizeStage(key) {
			return o.Name
		}
	}
	return ""
}

// ClampGrade 把年级限制在学段范围内：
//   - 小于 1 视为未填，返回 0；
//   - 中学允许用 7~9 表示，自动折算为 1~3；
//   - 超过学段上限则取上限。
func ClampGrade(stage string, g int) int {
	if g < 1 {
		return 0
	}
	n := textbook.GradeCount(stage)
	if n == 0 {
		return g
	}
	if textbook.NormalizeStage(stage) == textbook.StageMiddle && g > n && g <= n+6 {
		g -= 6
	}
	if g > n {
		return n
	}
	return g
}

// ClampClassNo 把班级序号限制在 0 ~ MaxClassNo。
func ClampClassNo(n int) int {
	if n < 0 {
		return 0
	}
	if n > MaxClassNo {
		return MaxClassNo
	}
	return n
}

// ClassNoLabel 班级序号的展示名：1 → 一班，13 → 13 班。
func ClassNoLabel(n int) string {
	if n <= 0 {
		return ""
	}
	if n <= 10 {
		return textbook.NumToCN(n) + "班"
	}
	return strconv.Itoa(n) + "班"
}

// BuildClassText 生成展示用班级文本：四年级二班；未填班级时退化为 四年级。
func BuildClassText(stage string, grade, classNo int) string {
	label := textbook.GradeLabel(stage, grade)
	if label == "" {
		return ""
	}
	return label + ClassNoLabel(classNo)
}

// ParseClassNo 从班级展示文本中反解班级序号（四年级二班 → 2；七年级11班 → 11）。
// 解析不出（含「四年级」这类未填班级的文本）返回 0，供编辑表单回选班级下拉。
func ParseClassNo(classText string) int {
	s := strings.TrimSpace(classText)
	if s == "" {
		return 0
	}
	for _, o := range StageList {
		for g := 1; g <= o.Grades; g++ {
			lbl := textbook.GradeLabel(o.Key, g)
			if lbl != "" && strings.HasPrefix(s, lbl) {
				rest := strings.TrimPrefix(s, lbl)
				for n := 1; n <= MaxClassNo; n++ {
					if ClassNoLabel(n) == rest {
						return n
					}
				}
				return 0
			}
		}
	}
	return 0
}

// guessStage 按年级推断学段：1~6 → 小学，7~9 → 中学；其它返回 ""。
func guessStage(grade int) string {
	switch {
	case grade >= 1 && grade <= 6:
		return textbook.StagePrimary
	case grade >= 7 && grade <= 9:
		return textbook.StageMiddle
	}
	return ""
}

// atoiSafe 宽松取整：非法或空串返回 0。
func atoiSafe(s string) int {
	n, err := strconv.Atoi(strings.TrimSpace(s))
	if err != nil {
		return 0
	}
	return n
}

// parseSchoolInfo 解析提交的学段 / 年级 / 班级：
//
//  1. 新表单：stage + grade + class_no（前端弹窗滚轮选择或直接填数字），年级不做裁剪，交由调用方校验；
//  2. 旧格式兜底：只有一段自由文本 class（如「四年级二班」）时，尽力提取年级并保留原文。
//
// 返回值 classText 为可直接展示的班级文本。
func parseSchoolInfo(stage, gradeRaw, classNoRaw, classRaw string) (string, int, int, string) {
	stageKey := NormalizeStage(stage)
	grade := atoiSafe(gradeRaw)
	classNo := ClampClassNo(atoiSafe(classNoRaw))
	raw := strings.TrimSpace(classRaw)

	if grade == 0 && classNo == 0 && raw != "" {
		// 旧格式：从「四年级二班」里提取年级，原文直接作为展示文本。
		g := extractGrade(raw)
		return guessStage(g), g, 0, raw
	}
	// 新格式：年级合法时按学段拼出展示文本（如 四年级二班 / 四年级）。
	if classText := BuildClassText(stageKey, grade, classNo); classText != "" {
		return stageKey, grade, classNo, classText
	}
	return stageKey, grade, classNo, raw
}
