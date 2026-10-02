// Command unitcheck 教材单元聚合自检。
//
// 背景：content/ 里存在同序号但不同名的单元目录，例如
// primary/grade1/volume1/chinese 下的「01-我上学了」与「01-识字（一）」。
// textbook.Subject.buildUnits 曾只按单元序号聚合，把它们并成一个单元，
// 导航里只显示先遇到的那个目录名，另一目录的课挂在名不副实的标题下。
// 现已改为按「序号 + 目录名」复合键聚合（见 internal/textbook/textbook.go）。
//
// 本工具核对聚合结果本身是否自洽，覆盖三类问题：
//  1. 课挂错单元：某个 Unit 里的课，其 Lesson.Unit 与该 Unit.Name 不一致
//     （单元标题与课文内容对不上）。
//  2. 空单元：聚合出没有任何课的单元。
//  3. 课数不守恒：各单元课数之和与该学科课数总数不等（有课被丢弃或重复计数）。
//
// 它刻意不把「同序号不同名」本身判为错误——那是合法的目录现状，运行时已能正确并列展示；
// 顺带统计一份清单，便于后续整理 content/ 编号。
//
// 直接调 textbook.Scan 读线上同一份解析结果，结论与线上刷题一致；只读，不改课件。
//
// 用法：
//
//	go run ./tools/unitcheck                      # 扫 content/
//	go run ./tools/unitcheck -content data/other
//
// 退出码：0 = 聚合自洽；1 = 有挂错/空单元/课数不守恒。
package main

import (
	"flag"
	"fmt"
	"os"
	"sort"

	"studybuddy/internal/textbook"
)

type problem struct {
	kind string
	desc string
}

type sharedNo struct {
	where string
	no    int
	names []string
}

func main() {
	content := flag.String("content", "content", "教材内容根目录")
	flag.Parse()

	tree, err := textbook.Scan(*content)
	if err != nil {
		fmt.Println("扫描失败：", err)
		os.Exit(1)
	}
	if len(tree.Grades) == 0 {
		fmt.Printf("没有扫描到任何课程：%s 不存在、为空，或里面的路径都不合规。\n", *content)
		os.Exit(1)
	}

	var problems []problem
	var shared []sharedNo
	unitsTotal, lessonsTotal := 0, 0

	for _, g := range tree.Grades {
		for _, v := range g.Volumes {
			for _, s := range v.Subjects {
				where := fmt.Sprintf("%s %d年级 %s %s", g.Stage, g.No, v.Name, s.Name)
				unitsTotal += len(s.Units)
				lessonsTotal += len(s.Lessons)

				// 1) 课挂错单元：Unit.Name 必须与课自带的 Unit 一致
				for _, u := range s.Units {
					if len(u.Lessons) == 0 {
						problems = append(problems, problem{"空单元",
							fmt.Sprintf("%s 第%02d单元 %q 没有任何课", where, u.No, u.Name)})
						continue
					}
					for _, l := range u.Lessons {
						if l.Unit != u.Name {
							problems = append(problems, problem{"课挂错单元",
								fmt.Sprintf("%s 单元 %q 下的课《%s》自称单元 %q",
									where, u.Name, l.Title, l.Unit)})
						}
					}
				}

				// 2) 课数不守恒
				sum := 0
				for _, u := range s.Units {
					sum += len(u.Lessons)
				}
				if sum != len(s.Lessons) {
					problems = append(problems, problem{"课数不守恒",
						fmt.Sprintf("%s 学科共 %d 课，各单元合计 %d 课", where, len(s.Lessons), sum)})
				}

				// 3) 同序号不同名清单（仅统计，不判错）
				byNo := map[int]map[string]bool{}
				for _, l := range s.Lessons {
					if l.Unit == "" {
						continue
					}
					if byNo[l.UnitNo] == nil {
						byNo[l.UnitNo] = map[string]bool{}
					}
					byNo[l.UnitNo][l.Unit] = true
				}
				var nos []int
				for no, set := range byNo {
					if len(set) > 1 {
						nos = append(nos, no)
					}
				}
				sort.Ints(nos)
				for _, no := range nos {
					var list []string
					for n := range byNo[no] {
						list = append(list, n)
					}
					sort.Strings(list)
					shared = append(shared, sharedNo{where, no, list})
				}
			}
		}
	}

	fmt.Printf("已扫描课程 %d 门、单元 %d 个。\n", lessonsTotal, unitsTotal)

	if len(shared) > 0 {
		fmt.Printf("\n另有 %d 处「同单元序号、不同目录名」（运行时已按复合键并列展示，不影响正确性；", len(shared))
		fmt.Println("如需整理编号可参考）：")
		for _, c := range shared {
			fmt.Printf("  %s 第%02d单元 -> %v\n", c.where, c.no, c.names)
		}
	}

	if len(problems) == 0 {
		fmt.Println("\n单元聚合自洽：没有课挂错单元、没有空单元、各单元课数之和等于学科课数。")
		return
	}
	fmt.Printf("\n发现 %d 处聚合问题：\n", len(problems))
	for _, p := range problems {
		fmt.Printf("  [%s] %s\n", p.kind, p.desc)
	}
	os.Exit(1)
}
