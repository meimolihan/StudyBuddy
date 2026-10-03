package web

// 用户头像：裁剪由前端完成（canvas 输出 256×256 正方形 PNG dataURL），
// 服务端只做校验与落盘：<DataDir>/avatars/u<uid>.png；未上传时返回 404，
// 前端回退显示姓名首字的圆形徽标。

import (
	"bytes"
	"encoding/base64"
	"image"
	"image/png"
	_ "image/jpeg" // 注册 JPEG 解码器，允许前端偶尔直接回传原始 jpg
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"strings"

	"github.com/gin-gonic/gin"

	"studybuddy/internal/auth"
)

// avatarMaxBytes 上传数据上限：裁剪输出为 256×256 PNG（通常几十 KB），留足余量。
const avatarMaxBytes = 6 << 20

func (a *App) avatarFile(uid int64) string {
	return filepath.Join(a.Cfg.DataDir, "avatars", "u"+strconv.FormatInt(uid, 10)+".png")
}

// hasAvatar 当前用户是否已上传头像。
// 模板据此决定是否输出 <img src="/avatar/me">：没头像时干脆不发这个请求，
// 免得浏览器控制台每条页面都记一次 404（onerror 只是兜底，不该当正常路径）。
func (a *App) hasAvatar(s *auth.Session) bool {
	if s == nil {
		return false
	}
	fi, err := os.Stat(a.avatarFile(s.UserID))
	return err == nil && !fi.IsDir()
}

// avatarMe GET /avatar/me：输出当前用户头像（no-store，上传后立即生效）。
func (a *App) avatarMe(c *gin.Context) {
	s := auth.Current(c)
	if s == nil {
		c.Status(http.StatusNotFound)
		return
	}
	p := a.avatarFile(s.UserID)
	fi, err := os.Stat(p)
	if err != nil || fi.IsDir() {
		c.Status(http.StatusNotFound) // 尚未上传：前端回退为首字徽标
		return
	}
	f, err := os.Open(p)
	if err != nil {
		c.Status(http.StatusNotFound)
		return
	}
	defer f.Close()
	c.Header("Cache-Control", "no-store")
	c.DataFromReader(http.StatusOK, fi.Size(), "image/png", f, nil)
}

// avatarUpload POST /profile/avatar：接收前端裁剪后的正方形图片（dataURL JSON）。
func (a *App) avatarUpload(c *gin.Context) {
	s := auth.Current(c)
	if s == nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "请先登录"})
		return
	}
	var req struct {
		Image string `json:"image"`
	}
	if err := c.ShouldBindJSON(&req); err != nil || req.Image == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "请求格式错误"})
		return
	}

	// 剥掉 dataURL 前缀，解码 base64
	b64 := req.Image
	if strings.HasPrefix(b64, "data:image/") {
		if i := strings.IndexByte(b64, ','); i >= 0 {
			b64 = b64[i+1:]
		}
	}
	raw, err := base64.StdEncoding.DecodeString(b64)
	if err != nil || len(raw) == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "图片数据无效"})
		return
	}
	if len(raw) > avatarMaxBytes {
		c.JSON(http.StatusBadRequest, gin.H{"error": "图片过大，请重新裁剪后上传"})
		return
	}

	img, _, err := image.Decode(bytes.NewReader(raw))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "无法解析图片，请换一张试试"})
		return
	}
	b := img.Bounds()
	if b.Dx() != b.Dy() {
		c.JSON(http.StatusBadRequest, gin.H{"error": "头像必须为正方形（请使用裁剪框）"})
		return
	}
	if b.Dx() < 64 || b.Dx() > 1024 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "头像尺寸需在 64~1024 像素之间"})
		return
	}

	var buf bytes.Buffer
	if err := png.Encode(&buf, img); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "头像编码失败"})
		return
	}
	if err := os.MkdirAll(filepath.Dir(a.avatarFile(s.UserID)), 0o755); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "存储目录创建失败"})
		return
	}
	// 先写临时文件再改名，避免半截文件被当作有效头像
	tmp := a.avatarFile(s.UserID) + ".tmp"
	if err := os.WriteFile(tmp, buf.Bytes(), 0o644); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "头像保存失败"})
		return
	}
	if err := os.Rename(tmp, a.avatarFile(s.UserID)); err != nil {
		_ = os.Remove(tmp)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "头像保存失败"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"ok": true, "url": "/avatar/me"})
}
