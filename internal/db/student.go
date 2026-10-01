package db

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"strings"
	"time"
)

// Progress 学生在某一课的学习进度。
type Progress struct {
	LessonKey string
	Subject   string
	Unit      string
	Title     string
	Status    string // new / learning / passed
	BestScore int
	Attempts  int
	LastAt    string
}

// Exam 一次自测（在线答题或 docx 试卷）的记录。
type Exam struct {
	ID        int64
	LessonKey string
	Title     string
	CreatedAt string
	Total     int // 题数
	Score     int // 得分（满分 = 题数 × 10）
	Passed    bool
	Docx      string // 归档的 docx 文件名（可为空）
	Source    string // online / docx
}

// Answer 单题作答记录。
type Answer struct {
	QIndex  int
	QType   string
	Stem    string
	Options []string
	Correct []string
	Picked  []string
	Right   bool
}

// Student 学生私有库句柄。
type Student struct {
	db     *sql.DB
	UserID int64
}

// OpenStudent 打开（并初始化）某学生的私有库，每生独立一个 SQLite 实例。
func OpenStudent(path string, userID int64) (*Student, error) {
	d, err := open(path)
	if err != nil {
		return nil, err
	}
	s := &Student{db: d, UserID: userID}
	if err := s.init(); err != nil {
		return nil, err
	}
	return s, nil
}

func (s *Student) init() error {
	stmts := []string{
		`CREATE TABLE IF NOT EXISTS state (k TEXT PRIMARY KEY, v TEXT)`,
		`CREATE TABLE IF NOT EXISTS progress (
			lesson_key TEXT PRIMARY KEY,
			subject TEXT, unit TEXT, title TEXT,
			status TEXT NOT NULL DEFAULT 'new',
			best_score INTEGER NOT NULL DEFAULT 0,
			attempts INTEGER NOT NULL DEFAULT 0,
			last_at TEXT
		)`,
		`CREATE TABLE IF NOT EXISTS exams (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			lesson_key TEXT, title TEXT, created_at TEXT,
			total INTEGER, score INTEGER, passed INTEGER,
			docx TEXT, source TEXT
		)`,
		`CREATE TABLE IF NOT EXISTS answers (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			exam_id INTEGER NOT NULL,
			lesson_key TEXT, q_index INTEGER,
			q_type TEXT, stem TEXT,
			options TEXT, correct TEXT, picked TEXT,
			right INTEGER
		)`,
		`CREATE INDEX IF NOT EXISTS idx_answers_lesson ON answers(lesson_key)`,
		`CREATE INDEX IF NOT EXISTS idx_answers_exam ON answers(exam_id)`,
	}
	for _, q := range stmts {
		if _, err := s.db.Exec(q); err != nil {
			return fmt.Errorf("初始化学生库失败: %w", err)
		}
	}
	return nil
}

func (s *Student) Close() error { return s.db.Close() }

// ---- 状态（当前学习位置等）----

func (s *Student) GetState(k string) string {
	var v string
	_ = s.db.QueryRow(`SELECT v FROM state WHERE k=?`, k).Scan(&v)
	return v
}

func (s *Student) SetState(k, v string) error {
	_, err := s.db.Exec(`INSERT INTO state(k,v) VALUES(?,?)
		ON CONFLICT(k) DO UPDATE SET v=excluded.v`, k, v)
	return err
}

// ---- 进度 ----

func (s *Student) GetProgress(lessonKey string) *Progress {
	p := &Progress{LessonKey: lessonKey, Status: "new"}
	var subject, unit, title, status, lastAt sql.NullString
	var best, att int
	err := s.db.QueryRow(
		`SELECT subject,unit,title,status,best_score,attempts,last_at FROM progress WHERE lesson_key=?`,
		lessonKey).Scan(&subject, &unit, &title, &status, &best, &att, &lastAt)
	if err != nil {
		return p
	}
	p.Subject, p.Unit, p.Title = subject.String, unit.String, title.String
	p.Status, p.BestScore, p.Attempts = status.String, best, att
	p.LastAt = lastAt.String
	return p
}

// ListProgress 返回全部进度记录。
func (s *Student) ListProgress() ([]*Progress, error) {
	rows, err := s.db.Query(`SELECT lesson_key,subject,unit,title,status,best_score,attempts,last_at FROM progress`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := []*Progress{}
	for rows.Next() {
		var p Progress
		var subject, unit, title, lastAt sql.NullString
		if err := rows.Scan(&p.LessonKey, &subject, &unit, &title, &p.Status,
			&p.BestScore, &p.Attempts, &lastAt); err != nil {
			return nil, err
		}
		p.Subject, p.Unit, p.Title, p.LastAt = subject.String, unit.String, title.String, lastAt.String
		out = append(out, &p)
	}
	return out, rows.Err()
}

// SaveProgress 写入（或更新）某课进度。
func (s *Student) SaveProgress(p *Progress) error {
	if p.LastAt == "" {
		p.LastAt = time.Now().Format("2006-01-02 15:04:05")
	}
	_, err := s.db.Exec(
		`INSERT INTO progress(lesson_key,subject,unit,title,status,best_score,attempts,last_at)
		 VALUES(?,?,?,?,?,?,?,?)
		 ON CONFLICT(lesson_key) DO UPDATE SET
		   subject=excluded.subject, unit=excluded.unit, title=excluded.title,
		   status=excluded.status, best_score=excluded.best_score,
		   attempts=excluded.attempts, last_at=excluded.last_at`,
		p.LessonKey, p.Subject, p.Unit, p.Title, p.Status, p.BestScore, p.Attempts, p.LastAt)
	return err
}

// ---- 试卷与作答 ----

// CreateExam 新建一次自测记录，返回其 ID。
func (s *Student) CreateExam(e *Exam) (int64, error) {
	if e.CreatedAt == "" {
		e.CreatedAt = time.Now().Format("2006-01-02 15:04:05")
	}
	passed := 0
	if e.Passed {
		passed = 1
	}
	res, err := s.db.Exec(
		`INSERT INTO exams(lesson_key,title,created_at,total,score,passed,docx,source)
		 VALUES(?,?,?,?,?,?,?,?)`,
		e.LessonKey, e.Title, e.CreatedAt, e.Total, e.Score, passed, e.Docx, e.Source)
	if err != nil {
		return 0, err
	}
	id, err := res.LastInsertId()
	if err != nil {
		return 0, err
	}
	e.ID = id
	return id, nil
}

// SetExamDocx 回填归档文件名。
func (s *Student) SetExamDocx(id int64, name string) error {
	_, err := s.db.Exec(`UPDATE exams SET docx=? WHERE id=?`, name, id)
	return err
}

// DeleteExams 删除指定 id 的自测记录（连同作答明细），返回实际删除的记录数。
// 只删不存在的 id 会被静默跳过；调用方（web 层）负责清理对应的 docx 归档文件。
func (s *Student) DeleteExams(ids []int64) (int64, error) {
	if len(ids) == 0 {
		return 0, nil
	}
	tx, err := s.db.Begin()
	if err != nil {
		return 0, err
	}
	defer tx.Rollback()
	var n int64
	for _, id := range ids {
		if _, err := tx.Exec(`DELETE FROM answers WHERE exam_id=?`, id); err != nil {
			return 0, err
		}
		r, err := tx.Exec(`DELETE FROM exams WHERE id=?`, id)
		if err != nil {
			return 0, err
		}
		if c, err := r.RowsAffected(); err == nil {
			n += c
		}
	}
	return n, tx.Commit()
}

// AddAnswers 批量写入作答明细。
func (s *Student) AddAnswers(examID int64, lessonKey string, as []Answer) error {
	tx, err := s.db.Begin()
	if err != nil {
		return err
	}
	defer tx.Rollback()
	stmt, err := tx.Prepare(
		`INSERT INTO answers(exam_id,lesson_key,q_index,q_type,stem,options,correct,picked,right)
		 VALUES(?,?,?,?,?,?,?,?,?)`)
	if err != nil {
		return err
	}
	defer stmt.Close()
	for _, a := range as {
		opts, _ := json.Marshal(a.Options)
		cor, _ := json.Marshal(a.Correct)
		pick, _ := json.Marshal(a.Picked)
		r := 0
		if a.Right {
			r = 1
		}
		if _, err := stmt.Exec(examID, lessonKey, a.QIndex, a.QType, a.Stem,
			string(opts), string(cor), string(pick), r); err != nil {
			return err
		}
	}
	return tx.Commit()
}

// Exam 查询单次自测。
func (s *Student) Exam(id int64) (*Exam, error) {
	e := &Exam{}
	var passed int
	var docx sql.NullString
	err := s.db.QueryRow(
		`SELECT id,lesson_key,title,created_at,total,score,passed,docx,source FROM exams WHERE id=?`,
		id).Scan(&e.ID, &e.LessonKey, &e.Title, &e.CreatedAt, &e.Total, &e.Score,
		&passed, &docx, &e.Source)
	if err != nil {
		return nil, err
	}
	e.Passed = passed != 0
	e.Docx = docx.String
	return e, nil
}

// ListExams 列出全部自测记录（倒序）。
func (s *Student) ListExams(limit int) ([]*Exam, error) {
	q := `SELECT id,lesson_key,title,created_at,total,score,passed,docx,source
	      FROM exams ORDER BY id DESC`
	if limit > 0 {
		q += fmt.Sprintf(" LIMIT %d", limit)
	}
	rows, err := s.db.Query(q)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := []*Exam{}
	for rows.Next() {
		e := &Exam{}
		var passed int
		var docx sql.NullString
		if err := rows.Scan(&e.ID, &e.LessonKey, &e.Title, &e.CreatedAt, &e.Total,
			&e.Score, &passed, &docx, &e.Source); err != nil {
			return nil, err
		}
		e.Passed = passed != 0
		e.Docx = docx.String
		out = append(out, e)
	}
	return out, rows.Err()
}

// Answers 取某次自测的作答明细。
func (s *Student) Answers(examID int64) ([]Answer, error) {
	rows, err := s.db.Query(
		`SELECT q_index,q_type,stem,options,correct,picked,right FROM answers WHERE exam_id=? ORDER BY q_index`,
		examID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := []Answer{}
	for rows.Next() {
		var a Answer
		var opts, cor, pick string
		var r int
		if err := rows.Scan(&a.QIndex, &a.QType, &a.Stem, &opts, &cor, &pick, &r); err != nil {
			return nil, err
		}
		_ = json.Unmarshal([]byte(opts), &a.Options)
		_ = json.Unmarshal([]byte(cor), &a.Correct)
		_ = json.Unmarshal([]byte(pick), &a.Picked)
		a.Right = r != 0
		out = append(out, a)
	}
	return out, rows.Err()
}

// SeenStems 返回该学生在某课**已经做过**的题干集合，用于出题时优先出未做过的题。
func (s *Student) SeenStems(lessonKey string) map[string]bool {
	m := map[string]bool{}
	rows, err := s.db.Query(`SELECT DISTINCT stem FROM answers WHERE lesson_key=?`, lessonKey)
	if err != nil {
		return m
	}
	defer rows.Close()
	for rows.Next() {
		var s2 string
		if err := rows.Scan(&s2); err == nil {
			m[s2] = true
		}
	}
	return m
}

// Stats 汇总学习概况。纸质卷（score = -1，待批改）不计入统计。
func (s *Student) Stats() (total, passed int, avg float64, err error) {
	if err = s.db.QueryRow(
		`SELECT COUNT(*), IFNULL(SUM(passed),0), IFNULL(AVG(score),0) FROM exams WHERE score >= 0`).
		Scan(&total, &passed, &avg); err != nil {
		return
	}
	return
}

// LessonTitleOf 便于展示：取某课最近一次记录的标题。
func (s *Student) LessonTitleOf(lessonKey string) string {
	var t string
	_ = s.db.QueryRow(`SELECT title FROM progress WHERE lesson_key=?`, lessonKey).Scan(&t)
	return strings.TrimSpace(t)
}
