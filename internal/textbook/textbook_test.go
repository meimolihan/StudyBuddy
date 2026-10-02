package textbook

import "testing"

// 单元聚合的回归测试。
//
// 背景：content/ 里存在同序号但不同名的单元目录（例如 primary/grade1/volume1/chinese 下
// 「01-我上学了」与「01-识字（一）」）。buildUnits 曾只按 UnitNo 聚合，导致两者被并成一个
// 单元，导航里只显示先遇到的那个目录名，另一目录的课挂在名不副实的标题下——
// 页面能打开，所以这类问题不会在端到端测试里暴露，只能靠单元级断言守住。

// mkLessons 造同一学科下的若干课：(单元序号, 单元目录名, 课序号, 课名)
func mkLessons(rows ...[4]int) *Subject {
	names := []string{"甲", "乙", "丙", "丁"}
	s := &Subject{Key: "math", Name: "数学"}
	for _, r := range rows {
		s.Lessons = append(s.Lessons, &Lesson{
			UnitNo:   r[0],
			Unit:     unitNameFor(r[0], r[1]),
			LessonNo: r[2],
			Title:    names[r[3]%len(names)],
		})
	}
	return s
}

func unitNameFor(no, variant int) string {
	base := []string{"我上学了", "识字（一）", "汉语拼音（一）", "课文（一）"}[no%4]
	if variant == 0 {
		return base
	}
	return base + "·变体"
}

func TestBuildUnits_SameNoDifferentNameNotMerged(t *testing.T) {
	// 单元 01 有两个不同目录名，各带一课；单元 02 一课。
	s := mkLessons(
		[4]int{1, 0, 1, 0}, // 01 / 甲名
		[4]int{1, 1, 1, 1}, // 01 / 乙名  ← 与上一条同序号不同名
		[4]int{2, 0, 1, 2}, // 02
	)
	s.buildUnits()

	if got := len(s.Units); got != 3 {
		t.Fatalf("同序号不同名的单元不应被合并：期望 3 个单元，实际 %d 个（%+v）", got, s.Units)
	}
	seen := map[string]int{}
	for _, u := range s.Units {
		seen[u.Name] += len(u.Lessons)
	}
	if len(seen) != 3 {
		t.Fatalf("期望 3 个不同单元名，实际 %d 个：%v", len(seen), seen)
	}
	for name, n := range seen {
		if n != 1 {
			t.Errorf("单元 %q 的课数应为 1，实际 %d（课被挂到了别的单元下）", name, n)
		}
	}
	// 同序号的两单元必须相邻（序号升序），且顺序按目录名稳定。
	if s.Units[0].No != 1 || s.Units[1].No != 1 || s.Units[2].No != 2 {
		t.Errorf("单元应按序号升序排列，实际 No：%d %d %d",
			s.Units[0].No, s.Units[1].No, s.Units[2].No)
	}
	if s.Units[0].Name >= s.Units[1].Name {
		t.Errorf("同序号单元应按目录名升序稳定排列，实际 %q 在 %q 之前", s.Units[0].Name, s.Units[1].Name)
	}
}

func TestBuildUnits_NormalCaseUnchanged(t *testing.T) {
	// 常规情况：序号唯一、每单元多课 —— 聚合结果与旧行为一致。
	s := mkLessons(
		[4]int{1, 0, 1, 0},
		[4]int{1, 0, 2, 1},
		[4]int{1, 0, 3, 2},
		[4]int{2, 1, 1, 3},
		[4]int{2, 1, 2, 0},
	)
	s.buildUnits()

	if got := len(s.Units); got != 2 {
		t.Fatalf("期望 2 个单元，实际 %d", got)
	}
	if len(s.Units[0].Lessons) != 3 || len(s.Units[1].Lessons) != 2 {
		t.Errorf("课数分配错误：单元1=%d 单元2=%d，期望 3/2",
			len(s.Units[0].Lessons), len(s.Units[1].Lessons))
	}
}

func TestBuildUnits_Idempotent(t *testing.T) {
	// 重复调用不得把已有单元追加两遍（buildUnits 每次都重建 s.Units）。
	s := mkLessons([4]int{1, 0, 1, 0}, [4]int{1, 1, 1, 1}, [4]int{2, 0, 1, 2})
	s.buildUnits()
	first := len(s.Units)
	firstLessons := 0
	for _, u := range s.Units {
		firstLessons += len(u.Lessons)
	}
	s.buildUnits()
	second := 0
	for _, u := range s.Units {
		second += len(u.Lessons)
	}
	if len(s.Units) != first || second != firstLessons {
		t.Errorf("buildUnits 非幂等：单元数 %d→%d，课数 %d→%d",
			first, len(s.Units), firstLessons, second)
	}
}

func TestBuildUnits_NoUnitKeepsLesson(t *testing.T) {
	// 无单元目录的课（UnitNo=0、Unit=""）不能被丢掉。
	s := &Subject{Key: "x", Name: "X", Lessons: []*Lesson{
		{UnitNo: 0, Unit: "", LessonNo: 1, Title: "复习一"},
		{UnitNo: 0, Unit: "", LessonNo: 2, Title: "复习二"},
	}}
	s.buildUnits()
	total := 0
	for _, u := range s.Units {
		total += len(u.Lessons)
	}
	if total != 2 {
		t.Fatalf("无单元课的总量应为 2，实际 %d（单元数 %d）", total, len(s.Units))
	}
}
