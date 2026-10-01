// Package config 集中管理 StudyBuddy 的运行时配置。
//
// 约定：所有路径都可通过环境变量覆盖，便于二进制直接运行与 Docker 挂载卷两种部署方式。
package config

import (
	"os"
	"path/filepath"
)

// Config 是全局配置。
type Config struct {
	Port      string // HTTP 监听端口
	BaseDir   string // 项目根目录（教材、数据、归档的默认父目录）
	Content   string // 教材内容根目录，如 <BaseDir>/content
	DataDir   string // 数据目录，含 global/ 与 students/
	Archive   string // 试卷归档目录
	PassScore int    // 小节达标分数线（满分 100）
	PerRound  int    // 每套试卷题数
	Single    int    // 其中单选题数
	Multi     int    // 其中多选题数
}

func env(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}

func atoi(s string, def int) int {
	n := 0
	for _, c := range s {
		if c < '0' || c > '9' {
			return def
		}
		n = n*10 + int(c-'0')
	}
	if n == 0 {
		return def
	}
	return n
}

// Load 读取配置，缺省值以当前工作目录为基准（单文件二进制在其所在目录运行时即项目根）。
func Load() *Config {
	base := env("STUDYBUDDY_HOME", "")
	if base == "" {
		if wd, err := os.Getwd(); err == nil {
			base = wd
		} else {
			base = "."
		}
	}
	abs, _ := filepath.Abs(base)

	c := &Config{
		Port:      env("STUDYBUDDY_PORT", "8080"),
		BaseDir:   abs,
		Content:   env("STUDYBUDDY_CONTENT", filepath.Join(abs, "content")),
		DataDir:   env("STUDYBUDDY_DATA", filepath.Join(abs, "data")),
		Archive:   env("STUDYBUDDY_ARCHIVE", filepath.Join(abs, "archive")),
		PassScore: atoi(env("STUDYBUDDY_PASS", "80"), 80),
		PerRound:  atoi(env("STUDYBUDDY_PER_ROUND", "10"), 10),
		Single:    atoi(env("STUDYBUDDY_SINGLE", "6"), 6),
		Multi:     atoi(env("STUDYBUDDY_MULTI", "4"), 4),
	}
	return c
}

// GlobalDBPath 返回全局公共库路径（仅账号/角色/邀请码）。
func (c *Config) GlobalDBPath() string {
	return filepath.Join(c.DataDir, "global", "global.db")
}

// StudentDBPath 返回指定学生的私有库路径（学习数据完全隔离）。
func (c *Config) StudentDBPath(userID int64) string {
	return filepath.Join(c.DataDir, "students", itoa(userID)+".db")
}

// StudentArchiveDir 返回指定学生的试卷归档目录。
func (c *Config) StudentArchiveDir(userID int64) string {
	return filepath.Join(c.Archive, itoa(userID))
}

func itoa(n int64) string {
	if n == 0 {
		return "0"
	}
	neg := n < 0
	if neg {
		n = -n
	}
	var b [24]byte
	i := len(b)
	for n > 0 {
		i--
		b[i] = byte('0' + n%10)
		n /= 10
	}
	if neg {
		i--
		b[i] = '-'
	}
	return string(b[i:])
}
