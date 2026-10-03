package textbook

import (
	"reflect"
	"testing"
)

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

// 扁平课程顺序（nextLesson 推进下一课用的顺序）必须与页面按单元展开的顺序完全一致。
//
// 背景：content/ 里存在同序号不同名的单元目录。真实案例是小学一年级语文上册的
// 「01-我上学了」和「01-识字（一）」——两者单元序号都是 1，课程序号又都是 1，
// 排序一旦退化到只按课名比较，「天地人」会排到「我上学了」前面（「天」的码点小于「我」），
// 于是入学教育那课被推到第 2 位，达标后推进的下一课也就跟着指错。
//
// 这类错位不会让页面报错：导航按单元分组展示时看起来是对的，只有走扁平列表的
// 「推进下一课」会悄悄跳错单元，因此必须靠单元级断言守住。
func TestSortLessons_FlatOrderMatchesUnitGrouping(t *testing.T) {
	s := &Subject{Key: "chinese", Name: "语文"}
	mk := func(unit string, unitNo, lessonNo int, title string) {
		s.Lessons = append(s.Lessons, &Lesson{Unit: unit, UnitNo: unitNo, LessonNo: lessonNo, Title: title})
	}
	// 刻意打乱输入顺序，确保测试测的是排序本身而不是输入顺序。
	mk("识字（一）", 1, 2, "金木水火土")
	mk("我上学了", 1, 1, "我上学了")
	mk("识字（一）", 1, 1, "天地人")
	mk("汉语拼音（一）", 2, 1, "a o e")

	sortLessons(s.Lessons) // 复用 Scan 用的真实排序，不在测试里复刻规则
	s.buildUnits()

	var grouped, flat []string
	for _, u := range s.Units {
		for _, l := range u.Lessons {
			grouped = append(grouped, l.Title)
		}
	}
	for _, l := range s.Lessons {
		flat = append(flat, l.Title)
	}

	if !reflect.DeepEqual(grouped, flat) {
		t.Fatalf("扁平顺序与单元展开顺序不一致：\n  分组=%v\n  扁平=%v", grouped, flat)
	}
	// 同序号的两单元里，「我上学了」必须整课排在「识字（一）」之前。
	want := []string{"我上学了", "天地人", "金木水火土", "a o e"}
	if !reflect.DeepEqual(flat, want) {
		t.Fatalf("教材顺序应为 %v，实际 %v", want, flat)
	}
}

// 同序号的不同单元，各自的课不能交错混排（否则推进下一课会跨单元乱跳）。
func TestSortLessons_SameUnitNoDoesNotInterleave(t *testing.T) {
	s := &Subject{Key: "english", Name: "英语"}
	mk := func(unit string, lessonNo int, title string) {
		s.Lessons = append(s.Lessons, &Lesson{Unit: unit, UnitNo: 10, LessonNo: lessonNo, Title: title})
	}
	mk("10-Life is full of the unexpected", 1, "Life-1")
	mk("10-I remember meeting all of you in Grade 7", 1, "Remember-1")
	mk("10-Life is full of the unexpected", 2, "Life-2")
	mk("10-I remember meeting all of you in Grade 7", 2, "Remember-2")

	sortLessons(s.Lessons)

	want := []string{"Remember-1", "Remember-2", "Life-1", "Life-2"}
	got := make([]string, 0, len(s.Lessons))
	for _, l := range s.Lessons {
		got = append(got, l.Title)
	}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("同序号单元应按单元聚拢而不是按课程序号交错：\n  期望=%v\n  实际=%v", want, got)
	}
}
