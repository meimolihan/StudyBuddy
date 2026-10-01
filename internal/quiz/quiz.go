// Package quiz 实现出题、判分与达标判定。
//
// 出题规则：每套 min(题库题数, 6单选 + 4多选)，并优先抽取该生**未做过**的题，
// 未做过的题不足时才回退到已做过的题，保证「题目出尽为止」。
package quiz

import (
	"math/rand"
	"sort"
	"time"

	"studybuddy/internal/db"
	"studybuddy/internal/textbook"
)

// Paper 一套试卷。
type Paper struct {
	Lesson    *textbook.Lesson
	Questions []textbook.Question
}

// BuildPaper 生成一套试卷。seen 为该生已做过的题干集合。
func BuildPaper(l *textbook.Lesson, bank []textbook.Question, seen map[string]bool,
	nSingle, nMulti int) *Paper {

	var singles, multis []textbook.Question
	for _, q := range bank {
		if q.IsMulti() {
			multis = append(multis, q)
		} else {
			singles = append(singles, q)
		}
	}
	r := rand.New(rand.NewSource(time.Now().UnixNano()))

	take := func(pool []textbook.Question, n int) []textbook.Question {
		if n <= 0 || len(pool) == 0 {
			return nil
		}
		var fresh, used []textbook.Question
		for _, q := range pool {
			if seen[q.Key] {
				used = append(used, q)
			} else {
				fresh = append(fresh, q)
			}
		}
		r.Shuffle(len(fresh), func(i, j int) { fresh[i], fresh[j] = fresh[j], fresh[i] })
		r.Shuffle(len(used), func(i, j int) { used[i], used[j] = used[j], used[i] })
		out := append([]textbook.Question{}, fresh...)
		out = append(out, used...) // 未做过的题排在前面
		if len(out) > n {
			out = out[:n]
		}
		return out
	}

	qs := take(singles, nSingle)
	qs = append(qs, take(multis, nMulti)...)

	// 单选/多选各自不足时，用另一种题型补足，尽量凑满题数
	total := nSingle + nMulti
	if len(qs) < total {
		have := map[string]bool{}
		for _, q := range qs {
			have[q.Key] = true
		}
		var rest []textbook.Question
		for _, q := range bank {
			if !have[q.Key] {
				rest = append(rest, q)
			}
		}
		r.Shuffle(len(rest), func(i, j int) { rest[i], rest[j] = rest[j], rest[i] })
		for _, q := range rest {
			if len(qs) >= total {
				break
			}
			qs = append(qs, q)
		}
	}

	// 打乱最终题序，避免单选永远在前
	r.Shuffle(len(qs), func(i, j int) { qs[i], qs[j] = qs[j], qs[i] })
	return &Paper{Lesson: l, Questions: qs}
}

// Result 判分结果。
type Result struct {
	Answers  []db.Answer
	Score    int // 得分（每题 10 分）
	FullMark int // 满分 = 题数 × 10
	Right    int
	Total    int
	Passed   bool
}

// Grade 判分：picked 为题号 → 选中选项下标。
func Grade(questions []textbook.Question, picked map[int][]int, passScore int) Result {
	res := Result{Total: len(questions), FullMark: len(questions) * 10}
	for i, q := range questions {
		sel := append([]int{}, picked[i]...)
		sort.Ints(sel)
		correct := q.AnswerIdx()
		sort.Ints(correct)
		right := len(sel) > 0 && sameInts(sel, correct)

		a := db.Answer{
			QIndex:  i,
			QType:   q.Type,
			Stem:    q.Stem,
			Options: q.Options,
			Right:   right,
		}
		for _, x := range correct {
			if x >= 0 && x < len(q.Options) {
				a.Correct = append(a.Correct, q.Options[x])
			}
		}
		for _, x := range sel {
			if x >= 0 && x < len(q.Options) {
				a.Picked = append(a.Picked, q.Options[x])
			}
		}
		if right {
			res.Right++
			res.Score += 10
		}
		res.Answers = append(res.Answers, a)
	}
	res.Passed = res.Total > 0 && res.Score >= passScore
	return res
}

func sameInts(a, b []int) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if a[i] != b[i] {
			return false
		}
	}
	return true
}
