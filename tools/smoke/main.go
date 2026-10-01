// Command smoke 对核心模块做一次无依赖冒烟自检：
// 教材扫描 → 题库解析 → 出题 → 判分 → docx 生成。
//
// 用法：go run ./tools/smoke
package main

import (
	"archive/zip"
	"fmt"
	"os"
	"strings"

	"studybuddy/internal/docx"
	"studybuddy/internal/quiz"
	"studybuddy/internal/textbook"
)

func main() {
	fail := 0
	check := func(cond bool, msg string) {
		if cond {
			fmt.Println("  ✓", msg)
		} else {
			fmt.Println("  ✗", msg)
			fail++
		}
	}

	root := "content"
	if len(os.Args) > 1 {
		root = os.Args[1]
	}

	fmt.Println("[1] 扫描教材目录:", root)
	tree, err := textbook.Scan(root)
	check(err == nil, "扫描无错误")
	if err != nil {
		os.Exit(1)
	}
	total := 0
	bySubject := map[string]int{}
	for _, g := range tree.Grades {
		for _, v := range g.Volumes {
			for _, s := range v.Subjects {
				total += len(s.Lessons)
				bySubject[s.Name] += len(s.Lessons)
				fmt.Printf("      %d年级%s %s：%d 课\n", g.No,
					map[int]string{1: "上", 2: "下"}[v.No], s.Name, len(s.Lessons))
			}
		}
	}
	check(total > 0, fmt.Sprintf("识别课程 %d 门", total))
	check(len(tree.Lessons) == total, "课程键索引数量一致")

	fmt.Println("\n[2] 解析题库")
	grand := 0
	var sample, rich *textbook.Lesson // rich：单选≥6 且 多选≥4 的课，供出题自检用
	for _, g := range tree.Grades {
		for _, v := range g.Volumes {
			for _, s := range v.Subjects {
				for _, l := range s.Lessons {
					qs, err := l.Bank()
					if err != nil || len(qs) == 0 {
						fmt.Println("      ✗ 无题库:", l.Key)
						fail++
						continue
					}
					grand += len(qs)
					if sample == nil {
						sample = l
					}
					if rich == nil {
						ns, nm := 0, 0
						for _, q := range qs {
							if q.IsMulti() {
								nm++
							} else {
								ns++
							}
						}
						if ns >= 6 && nm >= 4 {
							rich = l
						}
					}
				}
			}
		}
	}
	check(grand > 500, fmt.Sprintf("累计解析题目 %d 道", grand))

	if sample != nil {
		qs, _ := sample.Bank()
		fmt.Println("      样例课:", sample.Key)
		fmt.Printf("      样例题: [%s] %s\n", qs[0].Type, qs[0].Stem)
		fmt.Println("      选项  :", strings.Join(qs[0].Options, " | "))
		fmt.Println("      答案  :", qs[0].Answers, "→ 下标", qs[0].AnswerIdx())
		check(len(qs[0].Options) == 4, "样例题为 4 个选项")
		check(len(qs[0].AnswerIdx()) >= 1, "样例题可解析出答案下标")
		ok := true
		for _, x := range qs[0].AnswerIdx() {
			if x < 0 || x >= len(qs[0].Options) {
				ok = false
			}
		}
		check(ok, "答案下标在选项范围内")
	}

	fmt.Println("\n[3] 出题（6 单选 + 4 多选）")
	quizSample := sample
	if rich != nil {
		quizSample = rich // 样例课题型不够时，改用题型齐全的课验证出题比例
	}
	paper := quiz.BuildPaper(quizSample, mustBank(quizSample), map[string]bool{}, 6, 4)
	s, m := 0, 0
	for _, q := range paper.Questions {
		if q.IsMulti() {
			m++
		} else {
			s++
		}
	}
	check(len(paper.Questions) == 10, fmt.Sprintf("生成 %d 题", len(paper.Questions)))
	check(s == 6 && m == 4, fmt.Sprintf("单选 %d 题 + 多选 %d 题", s, m))

	fmt.Println("\n[4] 判分")
	picked := map[int][]int{}
	for i, q := range paper.Questions {
		picked[i] = q.AnswerIdx()
	}
	full := quiz.Grade(paper.Questions, picked, 80)
	check(full.Score == 100 && full.Right == 10, fmt.Sprintf("全对得 %d 分（满分 %d）", full.Score, full.FullMark))
	empty := quiz.Grade(paper.Questions, map[int][]int{}, 80)
	check(empty.Score == 0 && !empty.Passed, "全空得 0 分且未达标")
	half := quiz.Grade(paper.Questions, picked, 80)
	check(half.Passed, "全对判定为达标")

	fmt.Println("\n[5] 生成 docx（含 Word 原生复选框）")
	var qs []docx.Q
	for i, q := range paper.Questions {
		t := "单选"
		if q.IsMulti() {
			t = "多选"
		}
		var ans []string
		for _, x := range q.AnswerIdx() {
			ans = append(ans, q.Options[x])
		}
		qs = append(qs, docx.Q{No: i + 1, Type: t, Stem: q.Stem, Options: q.Options, Answers: ans})
	}
	path := "smoke-test.docx"
	f, err := os.Create(path)
	if err != nil {
		fmt.Println("  ✗ 创建文件失败:", err)
		os.Exit(1)
	}
	ex := docx.Exam{
		Title: "冒烟测试卷", Student: "郭奕凡", Class: "四年级二班",
		Lesson: sample.Unit + " · " + sample.Title, BankSize: len(mustBank(sample)),
		Questions: qs,
	}
	if err := docx.Build(f, ex); err != nil {
		fmt.Println("  ✗ 生成 docx 失败:", err)
		os.Exit(1)
	}
	f.Close()
	info, err := os.Stat(path)
	check(err == nil && info.Size() > 2000, fmt.Sprintf("docx 生成成功（%d 字节）", info.Size()))

	// 注意：zip 条目是压缩存储的，必须解压后再检查 XML，直接搜原始字节会误判
	b, _ := os.ReadFile(path)
	check(string(b[:2]) == "PK", "docx 为合法 zip 包")

	zr, err := zip.OpenReader(path)
	if err != nil {
		fmt.Println("  ✗ 打开 zip 失败:", err)
		os.Exit(1)
	}
	defer zr.Close()
	names := []string{}
	docXML := ""
	for _, zf := range zr.File {
		names = append(names, zf.Name)
		if zf.Name == "word/document.xml" {
			rc, err := zf.Open()
			if err != nil {
				fmt.Println("  ✗ 读取 document.xml 失败:", err)
				os.Exit(1)
			}
			buf := make([]byte, zf.UncompressedSize64)
			_, _ = rc.Read(buf)
			rc.Close()
			docXML = string(buf)
		}
	}
	check(contains(names, "[Content_Types].xml"), "包含 [Content_Types].xml")
	check(contains(names, "_rels/.rels"), "包含 _rels/.rels")
	check(contains(names, "word/styles.xml"), "包含 word/styles.xml")
	check(docXML != "", "包含并成功解压 word/document.xml")

	nSDT := strings.Count(docXML, "<w:sdt>")
	nCB := strings.Count(docXML, "<w14:checkbox>")
	check(nSDT >= 40, fmt.Sprintf("含 %d 个复选框控件（w14:checkbox %d 个）", nSDT, nCB))
	check(strings.Contains(docXML, "uncheckedState"), "复选框含未勾选状态定义")
	check(strings.Contains(docXML, "checkedState"), "复选框含已勾选状态定义")
	check(strings.Contains(docXML, "郭奕凡"), "已预填学生姓名")
	check(strings.Contains(docXML, "参考答案"), "含参考答案段落")
	check(strings.Contains(docXML, `xmlns:w14=`), "已声明 w14 命名空间")

	fmt.Println("\n---------------------------------------------")
	if fail == 0 {
		fmt.Println("冒烟自检全部通过 ✅")
	} else {
		fmt.Printf("存在 %d 项失败 ❌\n", fail)
		os.Exit(1)
	}
}

func contains(list []string, s string) bool {
	for _, x := range list {
		if x == s {
			return true
		}
	}
	return false
}

func mustBank(l *textbook.Lesson) []textbook.Question {
	qs, _ := l.Bank()
	return qs
}
