// StudyBuddy —— 小学生刷题自测 Web 系统。
//
// 单文件二进制即可运行：静态资源与页面模板均已内嵌，教材目录自动扫描。
package main

import (
	"fmt"
	"log"
	"os"

	"studybuddy/internal/config"
	"studybuddy/internal/db"
	"studybuddy/internal/textbook"
	"studybuddy/internal/web"
)

// version 由发布流水线经构建参数注入（-ldflags "-X main.version=..."），
// 见 .github/workflows/release.yml；本地源码构建时显示 dev。
var version = "dev"

const usageText = `StudyBuddy - 小学生刷题自测 Web 系统

用法:
  studybuddy                 启动 Web 服务（默认）
  studybuddy version         显示版本号
  studybuddy help            显示本帮助

服务管理（安装为 systemd 服务后可用，见 scripts/install.sh）:
  studybuddy status          查看服务运行状态
  studybuddy start|stop|restart
                             启动 / 停止 / 重启服务
  studybuddy uninstall       卸载服务（-y 免确认，--purge 连数据一并删除）

环境变量:
  STUDYBUDDY_HOME            项目根目录（默认当前工作目录）
  STUDYBUDDY_PORT            监听端口（默认 8080）
  STUDYBUDDY_CONTENT         教材内容目录（默认 <HOME>/content）
  STUDYBUDDY_DATA            数据目录（默认 <HOME>/data）
  STUDYBUDDY_ARCHIVE         归档目录（默认 <HOME>/archive）
`

func main() {
	// 内置 CLI：version / help（与 fan-webssh 命令规范对齐），
	// 其余参数维持原行为——忽略并直接启动 Web 服务。
	if len(os.Args) > 1 {
		switch os.Args[1] {
		case "version", "-version", "--version", "-v":
			fmt.Println("StudyBuddy " + version)
			return
		case "help", "-h", "--help":
			fmt.Print(usageText)
			return
		}
	}

	cfg := config.Load()

	// 全局公共库：仅账号 / 角色 / 邀请码
	g, err := db.OpenGlobal(cfg.GlobalDBPath())
	if err != nil {
		log.Fatalf("打开全局库失败: %v", err)
	}
	defer g.Close()

	// 教材目录树扫描
	tree, err := textbook.Scan(cfg.Content)
	if err != nil {
		log.Fatalf("扫描教材目录失败: %v", err)
	}

	// 运行时目录
	for _, d := range []string{cfg.DataDir, cfg.Archive} {
		_ = os.MkdirAll(d, 0o755)
	}

	app, err := web.New(cfg, g, tree)
	if err != nil {
		log.Fatalf("初始化应用失败: %v", err)
	}
	r := app.Routes()

	total := 0
	for _, gr := range tree.Grades {
		for _, v := range gr.Volumes {
			for _, s := range v.Subjects {
				total += len(s.Lessons)
			}
		}
	}
	fmt.Println("==============================================")
	fmt.Println("  StudyBuddy")
	fmt.Printf("  版本     : %s\n", version)
	fmt.Println("==============================================")
	fmt.Printf("  教材目录 : %s\n", cfg.Content)
	fmt.Printf("  识别课程 : %d 门\n", total)
	fmt.Printf("  数据目录 : %s\n", cfg.DataDir)
	fmt.Printf("  归档目录 : %s\n", cfg.Archive)
	fmt.Printf("  达标线   : %d 分（每套 %d 题：%d 单选 + %d 多选）\n",
		cfg.PassScore, cfg.PerRound, cfg.Single, cfg.Multi)
	fmt.Println("----------------------------------------------")
	fmt.Printf("  访问地址 : http://localhost:%s\n", cfg.Port)
	fmt.Println("==============================================")

	if err := r.Run(":" + cfg.Port); err != nil {
		log.Fatalf("服务启动失败: %v", err)
	}
}
