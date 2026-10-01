package textbook

import (
	"strconv"
	"strings"
)

// 学段标识（教材目录首层目录名）。
const (
	StagePrimary = "primary" // 小学
	StageMiddle  = "middle"  // 中学（初中）
	StageHigh    = "high"    // 高中
)

// stageOrder 学段排序权重：小学 → 中学 → 高中；未知学段排在最后。
var stageOrder = map[string]int{
	StagePrimary: 1, "primary-school": 1,
	StageMiddle: 2, "middle-school": 2,
	StageHigh: 3, "high-school": 3,
}

// stageGrades 各学段的标准年级数（小学 6 个年级、中学 / 高中各 3 个）。
var stageGrades = map[string]int{
	StagePrimary: 6,
	StageMiddle:  3,
	StageHigh:    3,
}

// NormalizeStage 归一化学段标识（兼容 primary-school 等旧命名）；无法识别时原样返回小写值。
func NormalizeStage(stage string) string {
	s := strings.ToLower(strings.TrimSpace(stage))
	switch s {
	case StagePrimary, "primary-school":
		return StagePrimary
	case StageMiddle, "middle-school":
		return StageMiddle
	case StageHigh, "high-school":
		return StageHigh
	}
	return s
}

// StageOrder 返回学段排序权重；未知学段返回 99。
func StageOrder(stage string) int {
	if v, ok := stageOrder[NormalizeStage(stage)]; ok {
		return v
	}
	return 99
}

// GradeCount 返回某学段的标准年级数；未知学段返回 0（表示不限）。
func GradeCount(stage string) int { return stageGrades[NormalizeStage(stage)] }

// numToCN 把 0 ~ 19 转成中文数字；超出范围回落到阿拉伯数字。
func numToCN(n int) string {
	cn := []string{"零", "一", "二", "三", "四", "五", "六", "七", "八", "九"}
	switch {
	case n >= 0 && n < len(cn):
		return cn[n]
	case n == 10:
		return "十"
	case n > 10 && n < 20:
		return "十" + cn[n-10]
	}
	return strconv.Itoa(n)
}

// NumToCN 导出中文数字转换（班级序号等展示用）。
func NumToCN(n int) string { return numToCN(n) }

// GradeLabel 年级中文名：
//
//	小学 1~6 → 一年级 ~ 六年级
//	中学 1~3 → 七年级 ~ 九年级（学段内序号，等价于 7~9 年级）
//	高中 1~3 → 高一 ~ 高三
//
// 未知学段回落到「4 年级」这种数字形式。
func GradeLabel(stage string, grade int) string {
	if grade <= 0 {
		return ""
	}
	switch NormalizeStage(stage) {
	case StagePrimary:
		return numToCN(grade) + "年级"
	case StageMiddle:
		return numToCN(grade+6) + "年级"
	case StageHigh:
		return "高" + numToCN(grade)
	default:
		return strconv.Itoa(grade) + " 年级"
	}
}

// Label 导航树的展示名，如「小学 4 年级」。
func (g *Grade) Label() string {
	if cn, ok := stageCN[NormalizeStage(g.Stage)]; ok {
		return cn + " " + strconv.Itoa(g.No) + " 年级"
	}
	return strconv.Itoa(g.No) + " 年级"
}
