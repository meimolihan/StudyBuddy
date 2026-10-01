// Command bankcheck 教材题库自检：用系统自己的解析器核对 content/ 里的课程与题库。
//
// 它回答两个问题：
//  1. 我放进 content/ 的课，系统真的认了吗？—— 路径不合规会被静默忽略，导航里根本不会出现。
//  2. 每课的题库解析出多少题？有没有解析不出、题量过少、答案不合法、题干重复的？
//
// 之所以不复用脚本另写一套解析：本工具直接调 textbook.Scan + textbook.ParseBank，
// 与线上刷题走的是同一套代码，结论不会有偏差。
//
// 用法：
//
//	go run ./tools/bankcheck                      # 扫 content/
//	go run ./tools/bankcheck -content content -min 10
//
// 退出码：0 = 只有提示或全好；1 = 有必须修的问题（解析不出题库、题数为 0、文件读不了）。
package main

import (
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"studybuddy/internal/textbook"
)

var stageOrder = map[string]int{"primary": 0, "middle": 1, "high": 2}
var stageCN = map[string]string{"primary": "小学", "middle": "初中", "high": "高中"}

var subjectOrder = map[string]int{"chinese": 0, "math": 1, "english": 2, "morallaw": 3, "science": 4}

type group struct {
	stage   string
	grade   int
	volume  int
	subject string
}

func main() {
	content := flag.String("content", "content", "教材内容根目录")
	minQ := flag.Int("min", 10, "每课题量下限，低于此值给提示")
	flag.Parse()

	tree, err := textbook.Scan(*content)
	if err != nil {
		fmt.Println("扫描失败：", err)
		os.Exit(1)
	}
	if len(tree.Lessons) == 0 {
		fmt.Printf("没有扫描到任何课程：%s 不存在、为空，或里面的路径都不合规。\n", *content)
		os.Exit(1)
	}

	// 磁盘上所有 HTML —— 用来找出「存在但被忽略」的文件。
	onDisk := map[string]bool{}
	_ = filepath.Walk(*content, func(p string, info os.FileInfo, err error) error {
		if err != nil || info == nil || info.IsDir() {
			return nil
		}
		if strings.EqualFold(filepath.Ext(p), ".html") {
			onDisk[filepath.ToSlash(p)] = true
		}
		return nil
	})

	// 逐课读文件 + 解析题库，按「学段 / 年级 / 册别 / 科目」分组统计。
	type stat struct{ lessons, questions, min, max int }
	stats := map[group]*stat{}
	var problems, hints []string
	totalQ, emptyLessons, dupLessons := 0, 0, 0

	keys := make([]string, 0, len(tree.Lessons))
	for k := range tree.Lessons {
		keys = append(keys, k)
	}
	sort.Strings(keys)

	for _, k := range keys {
		l := tree.Lessons[k]
		delete(onDisk, filepath.ToSlash(l.Path))

		st := textbook.NormalizeStage(l.Stage)
		g := group{stage: st, grade: l.Grade, volume: l.Volume, subject: l.Subject}
		if stats[g] == nil {
			stats[g] = &stat{min: -1}
		}
		s := stats[g]
		s.lessons++

		raw, err := os.ReadFile(l.Path)
		if err != nil {
			problems = append(problems, fmt.Sprintf("读不了文件 %s：%v", k, err))
			continue
		}
		qs := textbook.ParseBank(string(raw))
		n := len(qs)
		s.questions += n
		totalQ += n
		if s.min < 0 || n < s.min {
			s.min = n
		}
		if n > s.max {
			s.max = n
		}

		if n == 0 {
			emptyLessons++
			problems = append(problems, fmt.Sprintf("解析不出题库（HTML 里没有合法的 const ALL = [ … ];）：%s", k))
			continue
		}
		if n < *minQ {
			hints = append(hints, fmt.Sprintf("题量偏少：%2d 题 —— %s", n, k))
		}

		seen := map[string]int{}
		dup := 0
		for _, q := range qs {
			if q.Stem == "" {
				hints = append(hints, fmt.Sprintf("有题干为空的题 —— %s", k))
			}
			seen[q.Stem]++
			if seen[q.Stem] == 2 {
				dup++
			}
			if q.Type == "j" {
				// 判断题：固定「正确 / 错误」两个选项，答案 1 个，且必须带解析
				if len(q.Options) != 2 {
					hints = append(hints, fmt.Sprintf("判断题选项不是 2 个（%d 个）—— %s：%s", len(q.Options), k, clip(q.Stem)))
				}
				if len(q.Answers) != 1 {
					hints = append(hints, fmt.Sprintf("判断题答案不是 1 个 —— %s：%s", k, clip(q.Stem)))
				}
				if q.Explain == "" {
					hints = append(hints, fmt.Sprintf("判断题缺少解析 —— %s：%s", k, clip(q.Stem)))
				}
			} else if len(q.Options) != 4 {
				hints = append(hints, fmt.Sprintf("选项不是 4 个（%d 个）—— %s：%s", len(q.Options), k, clip(q.Stem)))
			}
			if q.Type == "s" && len(q.Answers) != 1 {
				hints = append(hints, fmt.Sprintf("单选答案不是 1 个 —— %s：%s", k, clip(q.Stem)))
			}
			if q.Type == "m" && len(q.Answers) < 2 {
				hints = append(hints, fmt.Sprintf("多选答案少于 2 个 —— %s：%s", k, clip(q.Stem)))
			}
			for _, a := range q.Answers {
				if len(a) != 1 || a[0] < 'A' || a[0] > 'D' {
					hints = append(hints, fmt.Sprintf("答案字母越界（%q）—— %s：%s", a, k, clip(q.Stem)))
				}
			}
		}
		if dup > 0 {
			dupLessons++
			hints = append(hints, fmt.Sprintf("同课内题干重复 %d 处 —— %s", dup, k))
		}
	}

	// 输出：分组总览
	groups := make([]group, 0, len(stats))
	for g := range stats {
		groups = append(groups, g)
	}
	sort.Slice(groups, func(i, j int) bool {
		a, b := groups[i], groups[j]
		if stageOrder[a.stage] != stageOrder[b.stage] {
			return stageOrder[a.stage] < stageOrder[b.stage]
		}
		if a.grade != b.grade {
			return a.grade < b.grade
		}
		if a.volume != b.volume {
			return a.volume < b.volume
		}
		if subjectOrder[a.subject] != subjectOrder[b.subject] {
			return subjectOrder[a.subject] < subjectOrder[b.subject]
		}
		return a.subject < b.subject
	})

	fmt.Println("== 内容总览（系统实际识别到的课程）==")
	cur := ""
	for _, g := range groups {
		head := fmt.Sprintf("%s %d 年级 %s", cn(stageCN, g.stage, g.stage), g.grade, volumeCN(g.volume))
		if head != cur {
			fmt.Println(" " + head)
			cur = head
		}
		s := stats[g]
		subCN := textbook.SubjectCN(g.subject)
		if subCN == "" {
			subCN = g.subject
		}
		fmt.Printf("   %-12s %2d 课 / %4d 题（每课 %d~%d）\n",
			subCN, s.lessons, s.questions, s.min, s.max)
	}

	// 输出：被忽略的 HTML
	if len(onDisk) > 0 {
		paths := make([]string, 0, len(onDisk))
		for p := range onDisk {
			paths = append(paths, p)
		}
		sort.Strings(paths)
		fmt.Printf("\n== 被忽略的 HTML（存在但不会出现在导航里，共 %d 个）==\n", len(paths))
		for _, p := range paths {
			rel, _ := filepath.Rel(*content, p)
			fmt.Printf("   %s   ← 路径不符合 content/<stage>/<publisher>/grade<N>/volume<N>/<subject>/…\n",
				filepath.ToSlash(rel))
		}
		hints = append(hints, fmt.Sprintf("有 %d 个 HTML 因路径不合规被忽略（见上）", len(paths)))
	}

	// 输出：问题与提示
	if len(problems) > 0 {
		fmt.Printf("\n== 必须修的问题（%d）==\n", len(problems))
		for _, p := range problems {
			fmt.Println("   ✗ " + p)
		}
	}
	if len(hints) > 0 {
		fmt.Printf("\n== 提示（%d）==\n", len(hints))
		for _, h := range hints {
			fmt.Println("   ⚠ " + h)
		}
	}

	fmt.Printf("\n== 汇总 ==\n课程 %d 门 · 题目 %d 道 · 解析不出 %d 门 · 有重复题 %d 门 · 问题 %d · 提示 %d\n",
		len(tree.Lessons), totalQ, emptyLessons, dupLessons, len(problems), len(hints))

	if len(problems) > 0 {
		os.Exit(1)
	}
}

// cn 取映射里的中文名，缺失时回退原值，避免打印空字符串。
func cn(m map[string]string, key, fallback string) string {
	if v, ok := m[key]; ok && v != "" {
		return v
	}
	return fallback
}

func volumeCN(v int) string {
	if v == 2 {
		return "下册"
	}
	return "上册"
}

// clip 截断长题干，保证一行提示不至于太长。
func clip(s string) string {
	r := []rune(s)
	if len(r) <= 24 {
		return s
	}
	return string(r[:24]) + "…"
}
