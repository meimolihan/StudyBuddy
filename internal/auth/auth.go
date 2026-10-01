// Package auth 提供密码哈希（bcrypt）、会话管理与 Gin 鉴权中间件。
package auth

import (
	"crypto/rand"
	"encoding/hex"
	"net/http"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"golang.org/x/crypto/bcrypt"
)

// CookieName 会话 Cookie 名称。
const CookieName = "sb_session"

// Session 登录会话（仅内存保存，重启后需重新登录）。
type Session struct {
	Token     string
	UserID    int64
	Username  string
	Name      string
	Role      string // admin / user
	Stage     string // primary 小学 / middle 中学 / high 高中 / ""
	Grade     int
	Volume    int
	Class     string
	Gender    string // male / female / ""
	Skin      string // 用户自选主题；"" 表示按性别推导
	Wallpaper string // 背景壁纸开关；"" = 显示，off = 关闭
	ExpiresAt time.Time
}

// IsAdmin 是否管理员。
func (s *Session) IsAdmin() bool { return s != nil && s.Role == "admin" }

// Store 线程安全的会话存储。
type Store struct {
	mu   sync.RWMutex
	m    map[string]*Session
	ttl  time.Duration
	stop chan struct{}
}

// NewStore 创建会话存储并启动过期清理协程。
func NewStore(ttl time.Duration) *Store {
	if ttl <= 0 {
		ttl = 12 * time.Hour
	}
	s := &Store{m: map[string]*Session{}, ttl: ttl, stop: make(chan struct{})}
	go s.gc()
	return s
}

func (s *Store) gc() {
	t := time.NewTicker(10 * time.Minute)
	defer t.Stop()
	for {
		select {
		case <-s.stop:
			return
		case now := <-t.C:
			s.mu.Lock()
			for k, v := range s.m {
				if now.After(v.ExpiresAt) {
					delete(s.m, k)
				}
			}
			s.mu.Unlock()
		}
	}
}

// Create 建立会话并返回 token。
func (s *Store) Create(sess *Session) (string, error) {
	b := make([]byte, 32)
	if _, err := rand.Read(b); err != nil {
		return "", err
	}
	tok := hex.EncodeToString(b)
	sess.Token = tok
	sess.ExpiresAt = time.Now().Add(s.ttl)
	s.mu.Lock()
	s.m[tok] = sess
	s.mu.Unlock()
	return tok, nil
}

// Get 取会话。
func (s *Store) Get(token string) (*Session, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	v, ok := s.m[token]
	if !ok || time.Now().After(v.ExpiresAt) {
		return nil, false
	}
	return v, true
}

// Delete 注销会话。
func (s *Store) Delete(token string) {
	s.mu.Lock()
	delete(s.m, token)
	s.mu.Unlock()
}

// ---- 密码 ----

// HashPassword 使用 bcrypt 生成密码哈希（严禁明文存储）。
func HashPassword(p string) (string, error) {
	b, err := bcrypt.GenerateFromPassword([]byte(p), bcrypt.DefaultCost)
	return string(b), err
}

// CheckPassword 校验密码。
func CheckPassword(hash, p string) bool {
	return bcrypt.CompareHashAndPassword([]byte(hash), []byte(p)) == nil
}

// RandomCode 生成随机邀请码（大写字母与数字，去掉易混淆字符）。
func RandomCode(n int) (string, error) {
	const alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
	b := make([]byte, n)
	if _, err := rand.Read(b); err != nil {
		return "", err
	}
	for i := range b {
		b[i] = alphabet[int(b[i])%len(alphabet)]
	}
	return string(b), nil
}

// ---- Gin 中间件 ----

// Mount 把当前会话注入上下文（未登录则为空）。
func Mount(store *Store) gin.HandlerFunc {
	return func(c *gin.Context) {
		if tok, err := c.Cookie(CookieName); err == nil && tok != "" {
			if s, ok := store.Get(tok); ok {
				c.Set("session", s)
			}
		}
		c.Next()
	}
}

// Current 取当前会话，未登录返回 nil。
func Current(c *gin.Context) *Session {
	v, ok := c.Get("session")
	if !ok {
		return nil
	}
	s, _ := v.(*Session)
	return s
}

// SetCookie 下发会话 Cookie。
func SetCookie(c *gin.Context, token string, maxAge int) {
	c.SetSameSite(http.SameSiteLaxMode)
	c.SetCookie(CookieName, token, maxAge, "/", "", false, true)
}

// RequireLogin 未登录跳转登录页。
func RequireLogin() gin.HandlerFunc {
	return func(c *gin.Context) {
		if Current(c) == nil {
			c.Redirect(http.StatusSeeOther, "/login")
			c.Abort()
			return
		}
		c.Next()
	}
}

// RequireAdmin 非管理员拒绝访问。
func RequireAdmin() gin.HandlerFunc {
	return func(c *gin.Context) {
		s := Current(c)
		if s == nil {
			c.Redirect(http.StatusSeeOther, "/login")
			c.Abort()
			return
		}
		if !s.IsAdmin() {
			c.String(http.StatusForbidden, "无权访问：仅管理员可进入该页面")
			c.Abort()
			return
		}
		c.Next()
	}
}
