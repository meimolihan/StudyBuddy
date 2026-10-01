// Package db 管理两类 SQLite 实例：
//
//   - 全局公共库 data/global/global.db：仅账号、角色、邀请码；**禁止**存放任何学习数据。
//   - 学生私有库 data/students/{user_id}.db：进度、试卷、答题历史，每生一份，物理隔离。
package db

import (
	"database/sql"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	_ "modernc.org/sqlite" // 纯 Go SQLite，无需 CGO
)

// User 全局库中的账号记录（不含任何学习数据）。
type User struct {
	ID        int64
	Username  string
	Name      string
	Role      string // admin / user
	Stage     string // 学段：primary 小学 / middle 中学 / high 高中；"" 表示未设置
	Grade     int    // 年级（学段内序号：小学 1~6，中学 / 高中 1~3）
	Volume    int    // 1 上册 / 2 下册
	Class     string // 展示用班级文本，如 四年级二班（未填班级时为 四年级）
	Gender    string // male / female / ""（未设置）
	Skin      string // 界面主题键；"" 表示从未手动选择，按性别推导
	Wallpaper string // 背景壁纸开关；"" = 显示（按年级 + 册别自动匹配），"off" = 关闭
	CreatedAt string

	passwordHash string // 仅用于鉴权比对，不对外序列化
}

// Invite 注册邀请码。
type Invite struct {
	Code      string
	CreatedBy int64
	UsedBy    int64
	UsedAt    string
	CreatedAt string
	Revoked   bool
}

// Global 全局公共库句柄。
type Global struct{ db *sql.DB }

func open(path string) (*sql.DB, error) {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return nil, err
	}
	d, err := sql.Open("sqlite", path+"?_pragma=busy_timeout(5000)&_pragma=journal_mode(WAL)")
	if err != nil {
		return nil, err
	}
	d.SetMaxOpenConns(1) // SQLite 单写者，避免锁竞争
	return d, nil
}

// OpenGlobal 打开（并初始化）全局公共库。
func OpenGlobal(path string) (*Global, error) {
	d, err := open(path)
	if err != nil {
		return nil, err
	}
	g := &Global{db: d}
	if err := g.init(); err != nil {
		return nil, err
	}
	return g, nil
}

func (g *Global) init() error {
	stmts := []string{
		`CREATE TABLE IF NOT EXISTS users (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			username TEXT NOT NULL UNIQUE,
			name TEXT NOT NULL,
			password_hash TEXT NOT NULL,
			role TEXT NOT NULL DEFAULT 'user',
			stage TEXT NOT NULL DEFAULT '',
			grade INTEGER NOT NULL DEFAULT 0,
			volume INTEGER NOT NULL DEFAULT 1,
			class TEXT NOT NULL DEFAULT '',
			gender TEXT NOT NULL DEFAULT '',
			skin TEXT NOT NULL DEFAULT '',
			wallpaper TEXT NOT NULL DEFAULT '',
			created_at TEXT NOT NULL
		)`,
		`CREATE TABLE IF NOT EXISTS invites (
			code TEXT PRIMARY KEY,
			created_by INTEGER NOT NULL,
			used_by INTEGER,
			used_at TEXT,
			created_at TEXT NOT NULL,
			revoked INTEGER NOT NULL DEFAULT 0
		)`,
	}
	for _, s := range stmts {
		if _, err := g.db.Exec(s); err != nil {
			return fmt.Errorf("初始化全局库失败: %w", err)
		}
	}
	// 兼容旧库：老版本 users 表没有 stage / gender / skin / wallpaper 列，按需补齐（列已存在时报错可忽略）。
	for _, col := range []string{
		`ALTER TABLE users ADD COLUMN stage TEXT NOT NULL DEFAULT ''`,
		`ALTER TABLE users ADD COLUMN gender TEXT NOT NULL DEFAULT ''`,
		`ALTER TABLE users ADD COLUMN skin TEXT NOT NULL DEFAULT ''`,
		`ALTER TABLE users ADD COLUMN wallpaper TEXT NOT NULL DEFAULT ''`,
	} {
		if _, err := g.db.Exec(col); err != nil && !isDupColumn(err) {
			return fmt.Errorf("升级全局库失败: %w", err)
		}
	}
	return nil
}

// isDupColumn 判断错误是否为「列已存在」（不同 SQLite 驱动文案不一致，按关键字宽松匹配）。
func isDupColumn(err error) bool {
	if err == nil {
		return false
	}
	msg := strings.ToLower(err.Error())
	return strings.Contains(msg, "duplicate column") || strings.Contains(msg, "already exists")
}

func (g *Global) Close() error { return g.db.Close() }

// CountUsers 统计用户数，用于判断系统是否处于「初始化」状态。
func (g *Global) CountUsers() (int64, error) {
	var n int64
	err := g.db.QueryRow(`SELECT COUNT(*) FROM users`).Scan(&n)
	return n, err
}

// CreateUser 新建账号。
func (g *Global) CreateUser(u *User, passwordHash string) error {
	u.CreatedAt = time.Now().Format("2006-01-02 15:04:05")
	res, err := g.db.Exec(
		`INSERT INTO users(username,name,password_hash,role,stage,grade,volume,class,gender,skin,wallpaper,created_at)
		 VALUES(?,?,?,?,?,?,?,?,?,?,?,?)`,
		u.Username, u.Name, passwordHash, u.Role, u.Stage, u.Grade, u.Volume, u.Class,
		u.Gender, u.Skin, u.Wallpaper, u.CreatedAt)
	if err != nil {
		return err
	}
	id, err := res.LastInsertId()
	if err != nil {
		return err
	}
	u.ID = id
	return nil
}

const userCols = `id,username,name,password_hash,role,stage,grade,volume,class,gender,skin,wallpaper,created_at`

func scanUser(row interface{ Scan(...interface{}) error }) (*User, error) {
	var u User
	var hash string
	err := row.Scan(&u.ID, &u.Username, &u.Name, &hash, &u.Role, &u.Stage,
		&u.Grade, &u.Volume, &u.Class, &u.Gender, &u.Skin, &u.Wallpaper, &u.CreatedAt)
	if err != nil {
		return nil, err
	}
	u.passwordHash = hash
	return &u, nil
}

// PasswordHash 返回密码哈希（仅供鉴权模块使用）。
func (u *User) PasswordHash() string { return u.passwordHash }

// ByUsername 按用户名查询。
func (g *Global) ByUsername(username string) (*User, error) {
	row := g.db.QueryRow(`SELECT `+userCols+` FROM users WHERE username=?`, username)
	u, err := scanUser(row)
	if err != nil {
		return nil, err
	}
	return u, nil
}

// ByID 按 ID 查询。
func (g *Global) ByID(id int64) (*User, error) {
	row := g.db.QueryRow(`SELECT `+userCols+` FROM users WHERE id=?`, id)
	u, err := scanUser(row)
	if err != nil {
		return nil, err
	}
	return u, nil
}

// ListUsers 列出全部账号基础信息（管理员能力）。
func (g *Global) ListUsers() ([]*User, error) {
	rows, err := g.db.Query(`SELECT ` + userCols + ` FROM users ORDER BY id`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []*User
	for rows.Next() {
		u, err := scanUser(rows)
		if err != nil {
			return nil, err
		}
		out = append(out, u)
	}
	return out, rows.Err()
}

// SetRole 修改角色（管理员能力）。
func (g *Global) SetRole(id int64, role string) error {
	_, err := g.db.Exec(`UPDATE users SET role=? WHERE id=?`, role, id)
	return err
}

// SetSkin 保存学生自选的界面主题。
func (g *Global) SetSkin(id int64, skin string) error {
	_, err := g.db.Exec(`UPDATE users SET skin=? WHERE id=?`, skin, id)
	return err
}

// SetWallpaper 保存学生的背景壁纸开关（"" = 显示，off = 关闭）。
func (g *Global) SetWallpaper(id int64, v string) error {
	if v != "off" {
		v = ""
	}
	_, err := g.db.Exec(`UPDATE users SET wallpaper=? WHERE id=?`, v, id)
	return err
}

// SetGender 保存性别（同时用于按性别推导默认主题）。
func (g *Global) SetGender(id int64, gender string) error {
	_, err := g.db.Exec(`UPDATE users SET gender=? WHERE id=?`, gender, id)
	return err
}

// ---- 邀请码 ----

// ErrInviteInvalid 邀请码无效（不存在 / 已用 / 已作废）。
var ErrInviteInvalid = errors.New("邀请码无效或已被使用")

// CreateInvite 生成邀请码。
func (g *Global) CreateInvite(code string, by int64) error {
	_, err := g.db.Exec(
		`INSERT INTO invites(code,created_by,created_at,revoked) VALUES(?,?,?,0)`,
		code, by, time.Now().Format("2006-01-02 15:04:05"))
	return err
}

// ListInvites 列出邀请码。
func (g *Global) ListInvites() ([]*Invite, error) {
	rows, err := g.db.Query(
		`SELECT code,created_by,IFNULL(used_by,0),IFNULL(used_at,''),created_at,revoked
		 FROM invites ORDER BY created_at DESC, code`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []*Invite
	for rows.Next() {
		var v Invite
		var revoked int
		if err := rows.Scan(&v.Code, &v.CreatedBy, &v.UsedBy, &v.UsedAt, &v.CreatedAt, &revoked); err != nil {
			return nil, err
		}
		v.Revoked = revoked != 0
		out = append(out, &v)
	}
	return out, rows.Err()
}

// RevokeInvite 作废邀请码（仅未使用、未作废的可作废）。
func (g *Global) RevokeInvite(code string) error {
	res, err := g.db.Exec(
		`UPDATE invites SET revoked=1 WHERE code=? AND IFNULL(used_by,0)=0 AND revoked=0`, code)
	if err != nil {
		return err
	}
	n, _ := res.RowsAffected()
	if n == 0 {
		return errors.New("邀请码不存在、已使用或已作废")
	}
	return nil
}

// UseInvite 核销邀请码；无效返回 ErrInviteInvalid。
func (g *Global) UseInvite(code string, userID int64) error {
	res, err := g.db.Exec(
		`UPDATE invites SET used_by=?, used_at=? WHERE code=? AND revoked=0 AND IFNULL(used_by,0)=0`,
		userID, time.Now().Format("2006-01-02 15:04:05"), code)
	if err != nil {
		return err
	}
	n, _ := res.RowsAffected()
	if n == 0 {
		return ErrInviteInvalid
	}
	return nil
}

// InviteValid 校验邀请码是否可用（不核销）。
func (g *Global) InviteValid(code string) bool {
	var n int
	err := g.db.QueryRow(
		`SELECT COUNT(*) FROM invites WHERE code=? AND revoked=0 AND IFNULL(used_by,0)=0`,
		code).Scan(&n)
	return err == nil && n > 0
}
